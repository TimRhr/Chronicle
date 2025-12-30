import os
import secrets
import uuid
from datetime import datetime, timezone
from datetime import timedelta
from urllib.parse import quote_plus
from flask import Flask, render_template, redirect, url_for
from flask_login import login_required, current_user
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from extensions import db, login_manager, cache, limiter, babel, migrate
from flask import request, session
from flask_babel import gettext as _

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

csrf = CSRFProtect()

# Load .env file from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def _normalize_locale_code(value: str | None) -> str | None:
    if not value:
        return None

    v = value.strip()
    if not v:
        return None
    v = v.replace('-', '_')
    return v.split('_', 1)[0].lower()


def _get_app_timezone():
    tz_name = _get_timezone_name()
    if tz_name and ZoneInfo:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return timezone.utc
    return timezone.utc


def _utc_naive_to_local(dt: datetime) -> datetime:
    """Convert naive UTC datetime (as stored in DB) to timezone-aware local datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_get_app_timezone())


def _get_timezone_name() -> str | None:
    tz = os.environ.get('TZ')
    if tz:
        return tz.strip()

    # Linux containers often have /etc/timezone, or /etc/localtime symlink
    try:
        if os.path.exists('/etc/timezone'):
            content = open('/etc/timezone', 'r', encoding='utf-8').read().strip()
            if content:
                return content
    except Exception:
        pass

    try:
        if os.path.islink('/etc/localtime'):
            target = os.readlink('/etc/localtime')
            marker = 'zoneinfo/'
            if marker in target:
                return target.split(marker, 1)[1]
    except Exception:
        pass

    return None


def _locale_from_timezone(tz_name: str | None, supported_locales: list[str]) -> str | None:
    if not tz_name:
        return None

    tz = tz_name.strip()
    tz_lower = tz.lower()

    # Minimal mapping. Extend as needed.
    de_zones = {
        'europe/berlin',
        'europe/vienna',
        'europe/zurich',
    }
    fr_zones = {
        'europe/paris',
    }
    es_zones = {
        'europe/madrid',
        'atlantic/canary',
    }

    if tz_lower in de_zones and 'de' in supported_locales:
        return 'de'
    if tz_lower in fr_zones and 'fr' in supported_locales:
        return 'fr'
    if tz_lower in es_zones and 'es' in supported_locales:
        return 'es'
    return None


def _determine_default_locale(supported_locales: list[str]) -> str:
    env_locale = _normalize_locale_code(os.environ.get('CHRONICLE_DEFAULT_LOCALE'))
    if env_locale and env_locale in supported_locales:
        return env_locale

    tz_locale = _locale_from_timezone(_get_timezone_name(), supported_locales)
    if tz_locale:
        return tz_locale

    return 'en' if 'en' in supported_locales else (supported_locales[0] if supported_locales else 'en')


def _build_database_url() -> str:
    existing = os.getenv('DATABASE_URL')
    if existing:
        return existing

    driver = (os.getenv('DB_DRIVER') or 'psycopg').strip()
    scheme = f"postgresql+{driver}" if driver else "postgresql"

    host = os.getenv('DB_HOST', 'db')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME', 'chronicle')
    user = os.getenv('DB_USER', 'chronicle')
    password = os.getenv('DB_PASSWORD', 'chronicle')

    user_q = quote_plus(user)
    password_q = quote_plus(password)
    return f"{scheme}://{user_q}:{password_q}@{host}:{port}/{name}"


def _load_or_create_secret_key(instance_path: str) -> str:
    existing = os.getenv("SECRET_KEY")
    if existing:
        return existing
    secret_file = os.path.join(instance_path, "flask_secret_key")
    os.makedirs(instance_path, exist_ok=True)
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as fh:
                key = fh.read().strip()
                if key:
                    return key
        except Exception:
            pass
    secret_key = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as fh:
            fh.write(secret_key)
    except Exception:
        # As a fallback we still return the generated key even if writing fails
        pass
    return secret_key


def create_app(config: dict | None = None):
    """Application factory with optional configuration overrides."""
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Configuration
    env = os.getenv("FLASK_ENV", "development")

    if env == "production":
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["REMEMBER_COOKIE_SECURE"] = True
        app.config["REMEMBER_COOKIE_HTTPONLY"] = True
        app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

    instance_path = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_path, exist_ok=True)

    if env == "production":
        app.config["SQLALCHEMY_DATABASE_URI"] = _build_database_url()
    else:
        # Development: SQLite in instance folder
        db_path = os.path.join(instance_path, "db.sqlite")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # SECRET_KEY - required in production
    app.config["SECRET_KEY"] = _load_or_create_secret_key(instance_path)
    
    # Registration config
    app.config["REGISTRATION_ENABLED"] = os.getenv("REGISTRATION_ENABLED", "true").lower() == "true"

    # Public base URL (used for emails/invites when no request context is available)
    app.config["PUBLIC_BASE_URL"] = (os.getenv("PUBLIC_BASE_URL", "") or "").rstrip('/')

    # Password reset config
    try:
        app.config["PASSWORD_RESET_TOKEN_TTL_MINUTES"] = int(os.getenv("PASSWORD_RESET_TOKEN_TTL_MINUTES", "30"))
    except ValueError:
        app.config["PASSWORD_RESET_TOKEN_TTL_MINUTES"] = 30
    
    # Keycloak SSO config
    app.config["KEYCLOAK_ENABLED"] = os.getenv("KEYCLOAK_ENABLED", "false").lower() == "true"
    app.config["KEYCLOAK_SERVER_URL"] = os.getenv("KEYCLOAK_SERVER_URL", "")
    app.config["KEYCLOAK_REALM"] = os.getenv("KEYCLOAK_REALM", "")
    app.config["KEYCLOAK_CLIENT_ID"] = os.getenv("KEYCLOAK_CLIENT_ID", "")
    app.config["KEYCLOAK_CLIENT_SECRET"] = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
    app.config["VAPID_PUBLIC_KEY"] = os.getenv("VAPID_PUBLIC_KEY")
    app.config["VAPID_PRIVATE_KEY"] = os.getenv("VAPID_PRIVATE_KEY")
    app.config["VAPID_SUBJECT"] = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
    
    # Cache configuration - disable in development
    redis_url = os.getenv("REDIS_URL", None)
    
    # Force local development mode on Windows (no Docker/Redis)
    is_windows = os.name == 'nt'

    if env == "development" or is_windows:
        app.config["CACHE_TYPE"] = "SimpleCache"  # Use SimpleCache for local dev
        app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    elif redis_url:
        app.config["CACHE_TYPE"] = "RedisCache"
        app.config["CACHE_REDIS_URL"] = redis_url
        app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    else:
        app.config["CACHE_TYPE"] = "SimpleCache"
        app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    
    # CDN configuration
    app.config["CDN_DOMAIN"] = os.getenv("CDN_DOMAIN", None)
    
    # Rate limiter storage
    # In development (local run without Docker), force memory storage to avoid connection errors
    if redis_url and env != "development" and not is_windows:
        app.config["RATELIMIT_STORAGE_URL"] = redis_url
        app.config["RATELIMIT_STORAGE_URI"] = redis_url
    else:
        app.config["RATELIMIT_STORAGE_URL"] = "memory://"

    db.init_app(app)
    csrf.init_app(app)
    if cache:
        cache.init_app(app)
    if limiter:
        limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Babel i18n configuration
    app.config['BABEL_SUPPORTED_LOCALES'] = ['de', 'en', 'es', 'fr']
    default_locale = _determine_default_locale(app.config['BABEL_SUPPORTED_LOCALES'])
    app.config['BABEL_DEFAULT_LOCALE'] = default_locale
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(os.path.dirname(__file__), 'translations')
    
    if config:
        app.config.update(config)
    
    def get_locale():
        supported = app.config.get('BABEL_SUPPORTED_LOCALES', [])

        # 1. Check if user is logged in and has a language preference
        if current_user.is_authenticated and hasattr(current_user, 'language') and current_user.language:
            normalized = _normalize_locale_code(current_user.language)
            if normalized and normalized in supported:
                return normalized
        # 2. Check session
        if 'language' in session:
            normalized = _normalize_locale_code(session.get('language'))
            if normalized and normalized in supported:
                return normalized
        # 3. Default to startup-determined locale (env > timezone > fallback)
        return default_locale
    
    babel.init_app(app, locale_selector=get_locale)
    register_cli_commands(app)
    
    # Login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'error'
    
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask_babel import gettext as _
        from flask import flash
        flash(_('Please log in to view this page.'), 'error')
        return redirect(url_for('auth.login'))

    @app.route('/service-worker.js')
    @app.route('/sw.js')
    def service_worker():
        return app.send_static_file('service-worker.js')

    # Import models and create tables
    with app.app_context():
        from models import User, PasswordResetToken, Invite, Page, Post, Media, LinkPreview, Tag, Category, Reaction, Bookmark, Comment, CommentReaction, Notification, Follow, Poll, PollOption, PollVote, PostVersion, Group, GroupMembership, GroupFile
        db.create_all()
        
        # Migration: Add new columns if they don't exist
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name
        bool_default_true = 'TRUE' if dialect == 'postgresql' else '1'
        bool_default_false = 'FALSE' if dialect == 'postgresql' else '0'
        
        # Check Media table columns
        media_columns = [col['name'] for col in inspector.get_columns('media')]
        if 'caption' not in media_columns:
            db.session.execute(text('ALTER TABLE media ADD COLUMN caption TEXT'))
        if 'order' not in media_columns:
            db.session.execute(text('ALTER TABLE media ADD COLUMN "order" INTEGER DEFAULT 0'))
        
        # Check User table columns for new theme/layout fields
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        new_user_cols = {
            'cover_image_url': 'VARCHAR(500)',
            'bg_color': 'VARCHAR(7)',
            'text_color': 'VARCHAR(7)',
            'font_family': "VARCHAR(50) DEFAULT 'default'",
            'layout_style': "VARCHAR(20) DEFAULT 'list'",
            'show_about_widget': f'BOOLEAN DEFAULT {bool_default_true}',
            'show_recent_posts': f'BOOLEAN DEFAULT {bool_default_true}',
            'show_popular_posts': f'BOOLEAN DEFAULT {bool_default_false}',
            'language': f"VARCHAR(5) DEFAULT '{default_locale}'",
            'session_token': 'VARCHAR(64)',
            'is_deleted': f'BOOLEAN DEFAULT {bool_default_false}',
            'deleted_at': 'TIMESTAMP'
        }
        for col, col_type in new_user_cols.items():
            if col not in user_columns:
                db.session.execute(text(f'ALTER TABLE users ADD COLUMN {col} {col_type}'))
        
        # Check Post table columns
        post_columns = [col['name'] for col in inspector.get_columns('posts')]
        if 'cover_image_url' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN cover_image_url VARCHAR(500)'))
        if 'view_count' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN view_count INTEGER DEFAULT 0'))
        if 'group_id' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN group_id INTEGER REFERENCES groups(id)'))
        if 'public_id' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN public_id VARCHAR(16)'))
            # Generate public_ids for existing posts
            import secrets
            existing_posts = db.session.execute(text('SELECT id FROM posts WHERE public_id IS NULL')).fetchall()
            for (post_id,) in existing_posts:
                public_id = secrets.token_urlsafe(8)
                db.session.execute(text('UPDATE posts SET public_id = :pid WHERE id = :id'), {'pid': public_id, 'id': post_id})
            # Create unique index after populating
            try:
                db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_posts_public_id ON posts(public_id)'))
            except:
                pass  # Index might already exist
        if 'is_pinned' not in post_columns:
            db.session.execute(text(f'ALTER TABLE posts ADD COLUMN is_pinned BOOLEAN DEFAULT {bool_default_false}'))
        if 'is_announcement' not in post_columns:
            db.session.execute(text(f'ALTER TABLE posts ADD COLUMN is_announcement BOOLEAN DEFAULT {bool_default_false}'))
        if 'scheduled_at' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN scheduled_at TIMESTAMP'))

        if 'show_in_feed' not in post_columns:
            db.session.execute(text(f'ALTER TABLE posts ADD COLUMN show_in_feed BOOLEAN DEFAULT {bool_default_true}'))

        if 'published_at' not in post_columns:
            db.session.execute(text('ALTER TABLE posts ADD COLUMN published_at TIMESTAMP'))
        
        # Check Group table columns
        if 'groups' in inspector.get_table_names():
            group_columns = [col['name'] for col in inspector.get_columns('groups')]
            if 'cover_image_url' not in group_columns:
                db.session.execute(text('ALTER TABLE groups ADD COLUMN cover_image_url VARCHAR(500)'))
            if 'icon_url' not in group_columns:
                db.session.execute(text('ALTER TABLE groups ADD COLUMN icon_url VARCHAR(500)'))

        # Create comment_reactions table if not exists
        if 'comment_reactions' not in inspector.get_table_names():
            db.create_all()
        
        # Create link_previews table if not exists
        if 'link_previews' not in inspector.get_table_names():
            db.create_all()
        
        # Create group_announcements table if not exists
        if 'group_announcements' not in inspector.get_table_names():
            db.create_all()

        # Invites migration/backfill
        if 'invites' in inspector.get_table_names():
            invite_columns = [col['name'] for col in inspector.get_columns('invites')]
            if 'expires_at' not in invite_columns:
                db.session.execute(text('ALTER TABLE invites ADD COLUMN expires_at TIMESTAMP'))
            # Backfill missing expires_at
            try:
                db.session.execute(text("UPDATE invites SET expires_at = DATETIME(created_at, '+7 day') WHERE expires_at IS NULL"))
            except Exception:
                try:
                    db.session.execute(text("UPDATE invites SET expires_at = created_at + INTERVAL '7 days' WHERE expires_at IS NULL"))
                except Exception:
                    pass
        
        db.session.commit()

        # Process invitation list (invites.txt) on startup
        try:
            from flask_babel import force_locale, gettext as _
            from mail import send_mail

            # invites.txt is stored in the project root (one level above /src)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            invites_path = os.path.join(project_root, 'invites.txt')

            if os.path.exists(invites_path):
                with open(invites_path, 'r', encoding='utf-8') as f:
                    raw_lines = f.read().splitlines()

                emails = []
                for line in raw_lines:
                    s = (line or '').strip()
                    if not s or s.startswith('#'):
                        continue
                    if '@' not in s:
                        continue
                    emails.append(s.lower())

                emails = sorted(set(emails))

                default_locale_for_mail = app.config.get('BABEL_DEFAULT_LOCALE')
                base_url = (app.config.get('PUBLIC_BASE_URL') or '').rstrip('/')

                if not base_url:
                    app.logger.error('PUBLIC_BASE_URL is not configured; cannot send invite emails without SERVER_NAME / request context')
                    raise RuntimeError('PUBLIC_BASE_URL is required for invite emails')

                for email in emails:
                    # Skip if user already exists
                    if User.query.filter_by(email=email).first():
                        continue

                    invite = Invite.query.filter_by(email=email).first()
                    now = datetime.now(timezone.utc)
                    expires_at = now + timedelta(days=7)

                    # Skip already used invites
                    if invite and invite.used_at:
                        continue

                    # If already sent and still valid -> skip
                    if invite and invite.sent_at and (invite.expires_at and invite.is_usable()):
                        continue

                    # Create or refresh (expired / not sent)
                    if not invite:
                        invite = Invite(
                            email=email,
                            token=Invite.generate_token(),
                            code_hash='',
                            created_at=now,
                            expires_at=expires_at,
                        )
                        db.session.add(invite)
                    else:
                        # refresh token/code/expiry
                        invite.token = Invite.generate_token()
                        invite.created_at = now
                        invite.expires_at = expires_at
                        invite.sent_at = None

                    code = Invite.generate_code()
                    invite.set_code(code)
                    db.session.commit()

                    invite_url = base_url + '/auth/register/' + invite.token
                    logo_url = base_url + '/static/assets/logo.png'

                    with force_locale(default_locale_for_mail):
                        subject = _('You are invited to Chronicle')
                        html_body = render_template(
                            'emails/invite.html',
                            invite_url=invite_url,
                            invite_code=code,
                            logo_url=logo_url,
                        )
                        text_body = render_template(
                            'emails/invite.txt',
                            invite_url=invite_url,
                            invite_code=code,
                        )

                    try:
                        send_mail(to_email=email, subject=subject, text_body=text_body, html_body=html_body)
                        invite.sent_at = datetime.now(timezone.utc)
                        db.session.commit()
                    except Exception as e:
                        app.logger.error(f'Error sending invite email to {email}: {e}')
        except Exception as e:
            app.logger.error(f'Error processing invites.txt: {e}')
        
        @login_manager.user_loader
        def load_user(user_id):
            try:
                raw = (user_id or '').strip()
                if ':' in raw:
                    uid_raw, token = raw.split(':', 1)
                    uid = int(uid_raw)
                    user = User.query.get(uid)
                    if not user:
                        return None
                    if not getattr(user, 'session_token', None):
                        return None
                    return user if user.session_token == token else None
                # Reject legacy cookies that only contain a numeric ID.
                # This prevents DB-reset / ID-reuse from logging into a different user.
                return None
            except Exception:
                return None
    
    # Auto-publish scheduled posts whose time has passed
    def autopublish_due_posts():
        from models import Post
        updated = Post.query.filter(
            Post.scheduled_at.isnot(None),
            Post.scheduled_at <= db.func.now()
        ).update(
            {
                Post.is_published: True,
                Post.published_at: Post.scheduled_at,
                Post.scheduled_at: None
            },
            synchronize_session=False
        )
        if updated:
            db.session.commit()
            try:
                app.logger.info('Auto-published %s scheduled posts', updated)
            except Exception:
                pass

    @app.before_request
    def handle_autopublish():
        autopublish_due_posts()

    # Register blueprints
    from auth import auth_bp, init_oauth
    app.register_blueprint(auth_bp)
    init_oauth(app)

    # Context processor for current year, CDN, and i18n
    @app.context_processor
    def inject_globals():
        from flask_babel import get_locale, gettext as _
        cdn_domain = app.config.get('CDN_DOMAIN')
        now = datetime.now()
        locale = get_locale()
        current_lang = str(locale) if locale else 'de'
        
        # i18n strings for JavaScript
        js_translations = {
            'loading': _('Loading...'),
            'no_notifications': _('No notifications'),
            'mark_all_read': _('Mark all as read'),
            'refresh': _('Refresh'),
            'mark_as_read': _('Mark as read'),
            'mark_as_unread': _('Mark as unread'),
            'notification_settings': _('Notification settings'),
            'new_posts': _('New posts'),
            'new_comments': _('New comments'),
            'mentions': _('Mentions'),
            'follows': _('Follows'),
            'group_invites': _('Group invites'),
            'edit': _('Edit'),
            'cancel': _('Cancel'),
            'save': _('Save'),
            'confirm': _('Confirm'),
            'close': _('Close'),
            'delete': _('Delete'),
            'delete_post': _('Delete post'),
            'delete_post_confirm': _('Do you really want to delete this post? This action cannot be undone.'),
            'delete_page': _('Delete page'),
            'delete_page_confirm': _('Do you really want to delete the page "{title}" and all related posts?'),
            'delete_file': _('Delete file'),
            'delete_file_confirm': _('Do you really want to delete this file?'),
            'delete_announcement': _('Delete announcement'),
            'delete_announcement_confirm': _('Do you really want to delete this announcement? This action cannot be undone.'),
            'no_more_posts': _('No more posts'),
            'load_more': _('Load more'),
            'bookmark': _('Bookmark'),
            'remove_bookmark': _('Remove bookmark'),
            'write_comment': _('Write a comment...'),
            'reply': _('Reply'),
            'send': _('Send'),
            'edited': _('edited'),
            'more': _('more'),
            'show_more': _('Show more'),
            'show_less': _('Show less'),
            'react': _('React'),
            'remove_reaction': _('Remove reaction'),
            'anonymous': _('Anonymous'),
            'delete_comment': _('Delete comment'),
            'delete_comment_confirm': _('Do you really want to delete this comment? This action cannot be undone.'),
            'no_comments': _('No comments yet.'),
            'no_trending_tags': _('No trending tags'),
            'error_loading': _('Error loading'),
            'older_comments': _('older comments'),
            'show_replies': _('Show replies'),
            'hide_replies': _('Hide replies'),
            'reply_singular': _('reply'),
            'replies_plural': _('replies'),
            'click_to_change': _('Click to change'),
            'login_to_react': _('Please log in to react.'),
            # Group settings
            'leave': _('Leave'),
            'leave_group_confirm': _('Do you really want to leave this group?'),
            'invite_all': _('Invite all'),
            'invite_all_confirm': _('Do you really want to invite all portal users to this group? This cannot be undone.'),
            'remove_member': _('Remove member'),
            'remove_member_confirm': _('Do you really want to remove {name} from the group?'),
            'remove': _('Remove'),
            'no_users_found': _('No users found'),
            'delete_group': _('Delete group'),
            'delete_group_confirm_text': _('Type the group name <b>{name}</b> to confirm deletion.'),
            'delete_permanently': _('Delete permanently'),
            'delete_account': _('Delete account'),
            'delete_account_confirm': _('This will delete your account. Depending on your selection, your posts may also be deleted. This cannot be undone.'),
            'deleted_user': _('Deleted user'),
            # Post editing
            'delete_image': _('Delete image'),
            'delete_image_confirm': _('Really delete image?'),
            'select_destination': _('Please select whether the post should appear on your profile or in a group.'),
            'remove_image': _('Remove image'),
            'remove_image_confirm': _('Remove this image from the selection?'),
            'add_poll': _('+ Add poll'),
            'hide_poll': _('− Hide poll'),
            'set_time': _('+ Set time'),
            'hide_schedule': _('− Hide schedule'),
            'option_1': _('Option 1'),
            'option_2': _('Option 2'),
            'option_n': _('Option {n}'),
            'toolbar_placeholder_bold': _('bold text'),
            'toolbar_placeholder_italic': _('italic text'),
            'toolbar_placeholder_strikethrough': _('strikethrough'),
            'toolbar_placeholder_heading': _('Heading'),
            'toolbar_placeholder_quote': _('Quote'),
            'toolbar_placeholder_code': _('code'),
            'toolbar_placeholder_list_item': _('List item'),
            'toolbar_placeholder_link_text': _('Link text'),
            'toolbar_placeholder_injection': _('HTML/JS Code'),
            'toolbar_code_here': _('code here'),
            'create_tag': _('Create tag'),
            'error_creating': _('Error creating.'),
            'error_creating_tag': _('Error creating tag.'),
            'error': _('Error'),
            # Edit page
            'edit_page': _('Edit page'),
            'show_in_menu': _('Show in menu'),
            # Tags
            'delete_tag': _('Delete tag'),
            'delete_tag_confirm': _('Really delete tag?'),
            # Preview
            'preview': _('Preview'),
            'no_preview': _('No preview available'),
            'preview_appears_here': _('Preview appears here...'),
            'select_group': _('Please select a group.'),
        }
        
        return {
            'current_year': now.year,
            'now': now,
            'cdn_url': f'https://{cdn_domain}' if cdn_domain else '',
            'current_lang': current_lang,
            'supported_languages': app.config['BABEL_SUPPORTED_LOCALES'],
            'js_translations': js_translations,
            'push_public_key': app.config.get("VAPID_PUBLIC_KEY"),
            'is_authenticated': current_user.is_authenticated
        }
    
    # Language change route
    @app.route('/set-language/<lang>')
    def set_language(lang):
        if lang in app.config['BABEL_SUPPORTED_LOCALES']:
            session['language'] = lang
            if current_user.is_authenticated:
                current_user.language = lang
                db.session.commit()
        # Get referrer, but filter out service-worker and invalid URLs
        referrer = request.referrer
        if referrer:
            # Exclude service-worker.js and other non-page URLs
            if 'service-worker' in referrer or referrer.endswith('.js'):
                referrer = None
        return redirect(referrer or url_for('blog.feed'))
    
    # Add custom Jinja2 filters
    from content_utils import highlight_search_terms, generate_toc, render_markdown
    app.jinja_env.filters['highlight'] = highlight_search_terms
    app.jinja_env.filters['generate_toc'] = generate_toc
    app.jinja_env.filters['markdown'] = render_markdown
    
    # i18n date formatting filter
    def format_datetime_i18n(dt, include_time=True):
        """Format datetime with i18n support"""
        if dt is None:
            return ''
        dt_local = _utc_naive_to_local(dt)
        lang = get_locale()
        if include_time:
            if str(lang) == 'en':
                return dt_local.strftime('%m/%d/%Y at %H:%M')
            else:
                return dt_local.strftime('%d.%m.%Y um %H:%M')
        else:
            if str(lang) == 'en':
                return dt_local.strftime('%m/%d/%Y')
            else:
                return dt_local.strftime('%d.%m.%Y')
    
    app.jinja_env.filters['format_dt'] = format_datetime_i18n

    # Register blog blueprint
    from blog import blog_bp
    app.register_blueprint(blog_bp)
    
    # Register social blueprint
    from social import social_bp
    app.register_blueprint(social_bp)
    
    # Register admin/analytics blueprint
    from admin import admin_bp
    app.register_blueprint(admin_bp)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Routes
    @app.route("/")
    def index():
        return redirect(url_for('blog.feed'))

    return app


def register_cli_commands(app):
    import click

    translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
    project_root = os.path.dirname(__file__)

    def _ensure_babel():
        try:
            subprocess.check_call(['pybabel', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError as exc:
            raise click.ClickException(
                "The 'pybabel' executable was not found. Install Babel via 'pip install Babel'."
            ) from exc

    def _run_babel_command(args):
        _ensure_babel()
        try:
            subprocess.check_call(args, cwd=project_root)
        except subprocess.CalledProcessError as exc:
            raise click.ClickException(f"Babel command failed with exit code {exc.returncode}.") from exc

    @app.cli.group()
    def translate():
        """Translation and localization helpers."""
        pass

    @translate.command()
    def compile():
        """Compile all .po files into .mo binaries."""
        if not os.path.isdir(translations_dir):
            raise click.ClickException(f"Translations directory not found at {translations_dir}.")
        _run_babel_command(['pybabel', 'compile', '-d', 'translations', '-f'])
        click.echo("Translations compiled successfully.")

if __name__ == "__main__":
    app = create_app()
    
    # Use SocketIO if available, otherwise regular Flask
    try:
        from websocket import init_socketio
        socketio = init_socketio(app)
        socketio.run(app, debug=True, host="0.0.0.0", port=5000)
    except ImportError:
        app.run(debug=True, host="0.0.0.0", port=5000)
