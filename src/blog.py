import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, session, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from PIL import Image
from extensions import db
from models import User, Page, Post, Media, LinkPreview, Tag, Poll, PollOption, PostVersion, Notification, Group, GroupMembership, GroupFile, Reaction, Bookmark, Comment, CommentReaction, Follow
from content_utils import process_link_preview, extract_urls, render_markdown, get_embed_html, extract_mentions

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


def _get_app_timezone():
    tz_name = (os.environ.get('TZ') or '').strip()
    if tz_name and ZoneInfo:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return timezone.utc
    return timezone.utc


def _normalize_to_utc_naive(dt: datetime) -> datetime:
    """Convert a datetime to naive UTC for storage/comparisons.

    - If dt is naive, interpret it as app/server local timezone (TZ env if provided),
      then convert to UTC.
    - If dt is aware, convert to UTC.
    """
    if dt.tzinfo is None:
        tz = _get_app_timezone()
        dt = dt.replace(tzinfo=tz)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.replace(tzinfo=None)


def format_datetime_i18n(dt):
    """Format datetime with i18n support for API responses"""
    if dt is None:
        return ''
    dt_local = dt
    try:
        dt_local = dt.replace(tzinfo=timezone.utc).astimezone(_get_app_timezone())
    except Exception:
        dt_local = dt
    # Check language from session or user preference
    lang = session.get('language', 'de')
    if current_user.is_authenticated and current_user.language:
        lang = current_user.language
    if lang == 'en':
        return dt_local.strftime('%m/%d/%Y at %H:%M')
    else:
        return dt_local.strftime('%d.%m.%Y um %H:%M')

blog_bp = Blueprint('blog', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_RESOLUTION = 1920  # Max width/height in pixels (configurable)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_folder(*subfolders: str):
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', *[str(s) for s in subfolders if str(s).strip()])
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def resize_and_compress_image(file, max_size=MAX_IMAGE_RESOLUTION, quality=85):
    """Resize and compress image for optimal web delivery."""
    img = Image.open(file)
    
    # Handle EXIF orientation
    try:
        from PIL import ExifTags
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = img._getexif()
        if exif:
            orientation_value = exif.get(orientation)
            if orientation_value == 3:
                img = img.rotate(180, expand=True)
            elif orientation_value == 6:
                img = img.rotate(270, expand=True)
            elif orientation_value == 8:
                img = img.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass
    
    # Convert RGBA to RGB for JPEG
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Resize if needed
    width, height = img.size
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return img, quality


def save_compressed_image(img, filepath, quality=85):
    """Save image with compression optimization."""
    # Save with optimized settings
    img.save(filepath, 'JPEG', quality=quality, optimize=True, progressive=True)
    
    # If file is still too large (>500KB), reduce quality further
    file_size = os.path.getsize(filepath)
    if file_size > 500 * 1024 and quality > 60:
        new_quality = max(60, quality - 15)
        img.save(filepath, 'JPEG', quality=new_quality, optimize=True, progressive=True)


def resize_image(file, max_size=MAX_IMAGE_RESOLUTION):
    """Convenience wrapper for resize_and_compress_image, returns only the image."""
    img, _ = resize_and_compress_image(file, max_size)
    return img


def is_safe_next(next_url: str | None) -> bool:
    if not next_url:
        return False
    if next_url in ('/service-worker.js', '/sw.js'):
        return False
    if next_url.startswith('/static/'):
        return False
    if next_url.endswith(('.js', '.css', '.map')):
        return False
    if next_url.startswith('/') and not next_url.startswith('//'):
        return True
    return False


POSTS_PER_PAGE = 10


def get_user_group_ids(user_id):
    """Get list of group IDs the user is a member of."""
    return [m.group_id for m in GroupMembership.query.filter_by(user_id=user_id).all()]


def build_feed_query(user_id, search_query='', tag_filter='', author_filter='', 
                     date_from='', date_to='', group_filter=''):
    """Build the feed query with all filters applied. Returns (query, user_groups)."""
    user_group_ids = get_user_group_ids(user_id)

    filters_active = any([
        bool(search_query),
        bool(tag_filter),
        bool(author_filter),
        bool(date_from),
        bool(date_to),
        bool(group_filter),
    ])
    
    posts_query = Post.query.filter_by(is_published=True)

    # Only show posts hidden from the feed when the user is actively filtering/searching.
    if not filters_active:
        posts_query = posts_query.filter(
            db.or_(
                Post.show_in_feed.is_(None),
                Post.show_in_feed.is_(True)
            )
        )
    
    # Exclude scheduled posts that haven't reached their publish time yet
    posts_query = posts_query.filter(
        db.or_(
            Post.scheduled_at.is_(None),
            Post.scheduled_at <= db.func.now()
        )
    )
    
    # Filter by group visibility: show public posts (no group) OR posts from user's groups
    posts_query = posts_query.filter(
        db.or_(
            Post.group_id.is_(None),
            Post.group_id.in_(user_group_ids) if user_group_ids else False
        )
    )
    
    # Join author for search and filter
    posts_query = posts_query.join(Post.author)
    
    # Apply search filter
    if search_query:
        search_term = f'%{search_query}%'
        posts_query = posts_query.filter(
            db.or_(
                Post.content.ilike(search_term),
                Post.title.ilike(search_term),
                User.username.ilike(search_term),
                User.display_name.ilike(search_term)
            )
        )
    
    # Apply tag filter
    if tag_filter:
        posts_query = posts_query.join(Post.tags).filter(Tag.slug == tag_filter)
    
    # Apply author filter
    if author_filter:
        posts_query = posts_query.filter(User.username == author_filter)
    
    # Apply group filter
    if group_filter:
        posts_query = posts_query.join(Group, Post.group_id == Group.id).filter(Group.slug == group_filter)
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            posts_query = posts_query.filter(Post.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            posts_query = posts_query.filter(Post.created_at < date_to_obj)
        except ValueError:
            pass
    
    # Order by effective publish date descending
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    
    # Get user's groups for sidebar display
    user_groups = [m.group for m in GroupMembership.query.filter_by(user_id=user_id).all()]
    
    return posts_query, user_groups


@blog_bp.route('/feed')
@login_required
def feed():
    """News feed showing all posts from all users with search (login required)."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    tag_filter = request.args.get('tag', '').strip()
    author_filter = request.args.get('author', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    group_filter = request.args.get('group', '').strip()
    
    posts_query, user_groups = build_feed_query(
        current_user.id, search_query, tag_filter, author_filter, 
        date_from, date_to, group_filter
    )
    
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    return render_template('feed.html', 
                          posts=posts, 
                          current_page=page, 
                          has_more=has_more, 
                          search_query=search_query,
                          tag_filter=tag_filter,
                          author_filter=author_filter,
                          date_from=date_from,
                          date_to=date_to,
                          group_filter=group_filter,
                          user_groups=user_groups,
                          )


@blog_bp.route('/feed/api')
@login_required
def feed_api():
    """API endpoint for loading more posts in the feed."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    tag_filter = request.args.get('tag', '').strip()
    author_filter = request.args.get('author', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    group_filter = request.args.get('group', '').strip()
    
    posts_query, _ = build_feed_query(
        current_user.id, search_query, tag_filter, author_filter, 
        date_from, date_to, group_filter
    )
    
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    posts_data = []
    for post in posts:
        author = post.author
        author_is_deleted = bool(getattr(author, 'is_deleted', False))

        author_payload = {
            'id': author.id,
            'is_deleted': author_is_deleted,
            'username': author.username,
            'display_name': author.display_name,
            'avatar_url': author.avatar_url,
            'theme_color': author.theme_color or '#4da9a4'
        }

        if author_is_deleted:
            # Keep stable JSON shape, but do not leak profile-identifying fields into UI.
            author_payload.update({
                'username': None,
                'display_name': None,
                'avatar_url': None,
                'theme_color': '#6b7280'
            })

        # Get poll data if exists
        poll_data = None
        if post.poll:
            poll = post.poll
            total_votes = sum(opt.votes.count() for opt in poll.options)
            poll_data = {
                'id': poll.id,
                'question': poll.question,
                'allows_multiple': poll.allows_multiple,
                'total_votes': total_votes,
                'options': [{
                    'id': opt.id,
                    'text': opt.text,
                    'votes': opt.votes.count(),
                    'percentage': round((opt.votes.count() / total_votes * 100) if total_votes > 0 else 0, 1)
                } for opt in poll.options.order_by('order')]
            }
        
        group_payload = None
        if post.group:
            group_payload = {
                'id': post.group.id,
                'slug': post.group.slug,
                'name': post.group.name,
                'color': post.group.color or '#6366f1'
            }

        posts_data.append({
            'id': post.id,
            'content': post.content,
            'content_html': render_markdown(post.content) if post.content else '',
            'created_at': format_datetime_i18n(post.scheduled_at or post.created_at),
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_edited': bool(post.updated_at and post.created_at and post.updated_at > post.created_at),
            'is_owner': current_user.is_authenticated and current_user.id == post.user_id,
            'author': author_payload,
            'media': [{'url': m.file_path, 'file_type': m.file_type, 'alt_text': m.alt_text} for m in post.media_items.order_by('order').all()],
            'tags': [{'name': t.name, 'slug': t.slug, 'color': t.color} for t in post.tags],
            'poll': poll_data,
            'group': group_payload,
            'link_previews': [{
                'embed_type': lp.embed_type,
                'embed_id': lp.embed_id,
                'url': lp.url,
                'title': lp.title,
                'description': lp.description,
                'image_url': lp.image_url,
                'site_name': lp.site_name
            } for lp in post.link_previews]
        })
    
    return jsonify({
        'posts': posts_data,
        'has_more': has_more,
        'page': page
    })


@blog_bp.route('/post/<public_id>')
@login_required
def view_post(public_id):
    """View a single post by public_id."""
    post = Post.query.filter_by(public_id=public_id).first_or_404()
    now = datetime.utcnow()
    
    # Only show published posts (and not scheduled for the future) or own posts
    if (not post.is_published or (post.scheduled_at and post.scheduled_at > now)) and (
        not current_user.is_authenticated or current_user.id != post.user_id
    ):
        return redirect(url_for('blog.feed'))
    
    # Check group membership for group posts
    if post.group_id:
        membership = GroupMembership.query.filter_by(group_id=post.group_id, user_id=current_user.id).first()
        if not membership:
            abort(404)
    
    is_own_post = current_user.is_authenticated and current_user.id == post.user_id
    
    return render_template('single_post.html', post=post, is_own_post=is_own_post)


@blog_bp.route('/u/<username>')
@login_required
def public_profile(username):
    """Profile page for any user (login required)."""
    user = User.query.filter_by(username=username).first_or_404()
    if getattr(user, 'is_deleted', False):
        abort(404)
    page = request.args.get('page', 1, type=int)
    pages = Page.query.filter_by(user_id=user.id, is_visible=True).order_by(Page.order).all()
    
    posts_query = Post.query.filter_by(user_id=user.id, is_published=True)
    # Hide scheduled posts until publish time for non-owners
    if not (current_user.is_authenticated and current_user.id == user.id):
        posts_query = posts_query.filter(
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= db.func.now()
            )
        )
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    # Check if viewing own profile
    is_own_profile = current_user.is_authenticated and current_user.id == user.id
    
    return render_template('public_profile.html', profile_user=user, pages=pages, posts=posts, 
                          current_page=page, has_more=has_more, is_own_profile=is_own_profile)


@blog_bp.route('/u/<username>/api')
@login_required
def public_profile_api(username):
    """API endpoint for loading more posts on public profile."""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    posts_query = Post.query.filter_by(user_id=user.id, is_published=True)
    # Hide scheduled posts until publish time for non-owners
    if not (current_user.is_authenticated and current_user.id == user.id):
        posts_query = posts_query.filter(
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= db.func.now()
            )
        )
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    is_own_profile = current_user.is_authenticated and current_user.id == user.id
    
    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'content_html': render_markdown(post.content) if post.content else '',
            'created_at': format_datetime_i18n(post.scheduled_at or post.published_at or post.created_at),
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_edited': bool(post.updated_at and post.created_at and post.updated_at > post.created_at),
            'is_owner': is_own_profile,
            'page_title': post.page.title if post.page else None,
            'page_slug': post.page.slug if post.page else None,
            'media': [{'url': m.file_path, 'alt_text': m.alt_text} for m in post.media_items.order_by('order').all()],
            'tags': [{'name': t.name, 'slug': t.slug, 'color': t.color} for t in post.tags]
        })
    
    return jsonify({
        'posts': posts_data,
        'has_more': has_more,
        'page': page,
        'theme_color': user.theme_color or '#4da9a4'
    })


@blog_bp.route('/u/<username>/page/<slug>')
@login_required
def public_profile_page(username, slug):
    """Profile page view for a specific page (login required)."""
    user = User.query.filter_by(username=username).first_or_404()
    page = Page.query.filter_by(user_id=user.id, slug=slug, is_visible=True).first_or_404()
    page_num = request.args.get('page', 1, type=int)
    posts_query = Post.query.filter_by(page_id=page.id, is_published=True)
    # Hide scheduled posts until publish time for non-owners
    if not (current_user.is_authenticated and current_user.id == user.id):
        posts_query = posts_query.filter(
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= db.func.now()
            )
        )
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page_num - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page_num * POSTS_PER_PAGE) < total_posts
    pages = Page.query.filter_by(user_id=user.id, is_visible=True).order_by(Page.order).all()
    
    is_own_profile = current_user.is_authenticated and current_user.id == user.id
    
    return render_template(
        'public_profile_page.html',
        profile_user=user,
        page=page,
        posts=posts,
        pages=pages,
        is_own_profile=is_own_profile,
        current_page=page_num,
        has_more=has_more,
    )


@blog_bp.route('/u/<username>/page/<slug>/api')
@login_required
def public_profile_page_api(username, slug):
    """API endpoint for loading more posts on public profile page subview."""
    user = User.query.filter_by(username=username).first_or_404()
    page_obj = Page.query.filter_by(user_id=user.id, slug=slug, is_visible=True).first_or_404()
    page_num = request.args.get('page', 1, type=int)

    posts_query = Post.query.filter_by(page_id=page_obj.id, is_published=True)
    if not (current_user.is_authenticated and current_user.id == user.id):
        posts_query = posts_query.filter(
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= db.func.now()
            )
        )
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page_num - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page_num * POSTS_PER_PAGE) < total_posts

    is_own_profile = current_user.is_authenticated and current_user.id == user.id
    html = render_template(
        'components/public_profile_page_posts_fragment.html',
        profile_user=user,
        page=page_obj,
        posts=posts,
        is_own_profile=is_own_profile,
    )

    return jsonify({'html': html, 'has_more': has_more, 'page': page_num})


@blog_bp.route('/me')
@login_required
def me():
    page = request.args.get('page', 1, type=int)
    pages = Page.query.filter_by(user_id=current_user.id, is_visible=True).order_by(Page.order).all()
    
    # Show ALL own posts (including unpublished and scheduled)
    posts_query = Post.query.filter_by(user_id=current_user.id)
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    return render_template('me/me.html', pages=pages, posts=posts, current_page=page, has_more=has_more)


@blog_bp.route('/me/page/<slug>')
@login_required
def view_page(slug):
    page = Page.query.filter_by(user_id=current_user.id, slug=slug).first_or_404()
    page_num = request.args.get('page', 1, type=int)
    posts_query = Post.query.filter_by(page_id=page.id, is_published=True).order_by(Post.created_at.desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page_num - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page_num * POSTS_PER_PAGE) < total_posts
    pages = Page.query.filter_by(user_id=current_user.id, is_visible=True).order_by(Page.order).all()
    return render_template('me/page.html', page=page, posts=posts, pages=pages, current_page=page_num, has_more=has_more)


@blog_bp.route('/me/page/<slug>/api')
@login_required
def me_page_api(slug):
    """API endpoint for loading more posts on the private profile page subview."""
    page_obj = Page.query.filter_by(user_id=current_user.id, slug=slug).first_or_404()
    page_num = request.args.get('page', 1, type=int)

    posts_query = Post.query.filter_by(page_id=page_obj.id, is_published=True).order_by(Post.created_at.desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page_num - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page_num * POSTS_PER_PAGE) < total_posts

    html = render_template('components/me_page_posts_fragment.html', posts=posts)
    return jsonify({'html': html, 'has_more': has_more, 'page': page_num})


@blog_bp.route('/me/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.display_name = request.form.get('display_name', '').strip() or None
        current_user.bio = request.form.get('bio', '').strip() or None
        current_user.theme_color = request.form.get('theme_color', '#4da9a4')

        # Background/text color customization removed; ensure no persisted overrides remain
        current_user.bg_color = None
        current_user.text_color = None
        
        current_user.font_family = request.form.get('font_family', 'default')
        current_user.layout_style = request.form.get('layout_style', 'list')
        
        # Handle avatar upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(get_upload_folder('users', str(current_user.id)), filename)
                img = resize_image(file, max_size=512)
                img.save(filepath, 'JPEG', quality=85)
                current_user.avatar_url = url_for('static', filename=f'uploads/users/{current_user.id}/{filename}')
        
        # Handle cover image upload
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename and allowed_file(file.filename):
                filename = f"cover_{current_user.id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(get_upload_folder('users', str(current_user.id)), filename)
                img = resize_image(file, max_size=1920)
                img.save(filepath, 'JPEG', quality=85)
                current_user.cover_image_url = url_for('static', filename=f'uploads/users/{current_user.id}/{filename}')
        
        db.session.commit()
        flash(_('Profile updated successfully.'), 'success')
        return redirect(url_for('blog.me'))
    
    pages = Page.query.filter_by(user_id=current_user.id).order_by(Page.order).all()
    return render_template('me/settings.html', pages=pages)


@blog_bp.route('/me/pages', methods=['GET', 'POST'])
@login_required
def manage_pages():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash(_('Title is required.'), 'error')
            return redirect(url_for('blog.manage_pages'))
        
        # Generate slug
        slug = title.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Check for duplicate slug
        existing = Page.query.filter_by(user_id=current_user.id, slug=slug).first()
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        
        max_order = db.session.query(db.func.max(Page.order)).filter_by(user_id=current_user.id).scalar() or 0
        
        page = Page(
            user_id=current_user.id,
            title=title,
            slug=slug,
            description=request.form.get('description', '').strip() or None,
            icon=request.form.get('icon', 'file-text'),
            order=max_order + 1
        )
        db.session.add(page)
        db.session.commit()
        
        flash(_('Page "{title}" was created.').format(title=title), 'success')
        return redirect(url_for('blog.manage_pages'))
    
    pages = Page.query.filter_by(user_id=current_user.id).order_by(Page.order).all()
    return render_template('me/manage_pages.html', pages=pages)


@blog_bp.route('/me/pages/<int:page_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_page(page_id):
    page = Page.query.filter_by(id=page_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        page.title = request.form.get('title', '').strip() or page.title
        page.description = request.form.get('description', '').strip() or None
        page.icon = request.form.get('icon', 'file-text')
        page.is_visible = request.form.get('is_visible') == 'on'
        
        db.session.commit()
        flash(_('Page updated.'), 'success')
        return redirect(url_for('blog.manage_pages'))
    
    return render_template('me/edit_page.html', page=page)


@blog_bp.route('/me/pages/<int:page_id>/delete', methods=['POST'])
@login_required
def delete_page(page_id):
    page = Page.query.filter_by(id=page_id, user_id=current_user.id).first_or_404()
    db.session.delete(page)
    db.session.commit()
    flash(_('Page deleted.'), 'success')
    return redirect(url_for('blog.manage_pages'))


@blog_bp.route('/me/pages/<int:page_id>/reorder', methods=['POST'])
@login_required
def reorder_page(page_id):
    page = Page.query.filter_by(id=page_id, user_id=current_user.id).first_or_404()
    direction = request.form.get('direction')
    
    if direction == 'up' and page.order > 0:
        swap_page = Page.query.filter_by(user_id=current_user.id, order=page.order - 1).first()
        if swap_page:
            swap_page.order, page.order = page.order, swap_page.order
            db.session.commit()
    elif direction == 'down':
        swap_page = Page.query.filter_by(user_id=current_user.id, order=page.order + 1).first()
        if swap_page:
            swap_page.order, page.order = page.order, swap_page.order
            db.session.commit()
    
    return redirect(url_for('blog.manage_pages'))


@blog_bp.route('/me/posts/new', methods=['GET', 'POST'])
@login_required
def new_post():
    next_url = request.args.get('next')
    if request.method == 'GET' and not next_url:
        next_url = request.referrer
    if request.method == 'POST':
        next_url = request.form.get('next') or next_url
    if next_url and next_url.startswith(('http://', 'https://')):
        try:
            parsed = urlparse(next_url)
            if parsed.netloc == request.host:
                next_url = parsed.path + (('?' + parsed.query) if parsed.query else '')
        except Exception:
            pass
    if not is_safe_next(next_url):
        next_url = url_for('blog.me')

    if request.method == 'POST':
        title = request.form.get('title', '').strip() or None
        content = request.form.get('content', '').strip() or None
        page_id = request.form.get('page_id') or None
        group_id = request.form.get('group_id') or None
        post_type = request.form.get('post_type', 'text')
        show_in_feed = 'show_in_feed' in request.form
        destination = (request.form.get('destination') or '').strip()

        if page_id:
            try:
                page_id = int(page_id)
            except (TypeError, ValueError):
                page_id = None

        if group_id:
            try:
                group_id = int(group_id)
            except (TypeError, ValueError):
                group_id = None
        
        # Parse scheduled publish time
        scheduled_at = None
        scheduled_str = request.form.get('scheduled_at', '').strip()
        if scheduled_str:
            try:
                scheduled_at = _normalize_to_utc_naive(datetime.fromisoformat(scheduled_str))
            except ValueError:
                pass
        
        if page_id:
            page = Page.query.filter_by(id=page_id, user_id=current_user.id).first()
            if not page:
                page_id = None
        
        # Verify user is member of the group
        if group_id:
            membership = GroupMembership.query.filter_by(group_id=group_id, user_id=current_user.id).first()
            if not membership:
                group_id = None

        # Enforce that a destination is selected: profile OR group.
        # If destination is group, a valid group_id must be provided.
        if destination == 'group' and not group_id:
            flash(_('Please select a group.'), 'error')
            return redirect(request.url)
        if destination == 'profile':
            group_id = None

        # Pages don't apply to group posts
        if group_id:
            page_id = None
        
        post = Post(
            user_id=current_user.id,
            page_id=page_id,
            group_id=group_id,
            title=title,
            content=content,
            post_type=post_type,
            show_in_feed=show_in_feed,
            scheduled_at=scheduled_at
        )

        if scheduled_at and scheduled_at > datetime.utcnow():
            post.is_published = False
            post.published_at = None
        else:
            post.published_at = datetime.utcnow()
        db.session.add(post)
        db.session.commit()

        mentioned_usernames = extract_mentions(content or '')
        if mentioned_usernames:
            mentioned_users = User.query.filter(User.username.in_(mentioned_usernames)).all()
            for u in mentioned_users:
                if u.id == current_user.id:
                    continue
                notification = Notification(
                    user_id=u.id,
                    type='mention',
                    title=f'{current_user.display_name or current_user.username} hat dich in einem Beitrag erwähnt',
                    message=(content or '')[:100] + ('...' if content and len(content) > 100 else ''),
                    link=f'/post/{post.public_id}',
                    actor_id=current_user.id,
                    post_id=post.id
                )
                db.session.add(notification)
            db.session.commit()
        
        # Handle image uploads
        if 'images' in request.files:
            files = request.files.getlist('images')
            order = 0
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    original_filename = secure_filename(file.filename)
                    filename = f"{uuid.uuid4().hex}.jpg"
                    if post.group_id:
                        rel_dir = f"uploads/groups/{post.group_id}/posts/{post.id}"
                        filepath = os.path.join(get_upload_folder('groups', str(post.group_id), 'posts', str(post.id)), filename)
                    else:
                        rel_dir = f"uploads/users/{current_user.id}/posts/{post.id}"
                        filepath = os.path.join(get_upload_folder('users', str(current_user.id), 'posts', str(post.id)), filename)
                    img = resize_image(file)
                    img.save(filepath, 'JPEG', quality=85)
                    file_size = os.path.getsize(filepath)
                    
                    media = Media(
                        user_id=current_user.id,
                        post_id=post.id,
                        filename=filename,
                        original_filename=original_filename,
                        file_path=f'{rel_dir}/{filename}',
                        file_type='image/jpeg',
                        file_size=file_size,
                        alt_text=request.form.get('alt_text', '').strip() or None,
                        order=order
                    )
                    db.session.add(media)
                    order += 1
            db.session.commit()
        
        # Handle link previews - extract URLs from content
        if content:
            urls = extract_urls(content)
            for url in urls[:5]:  # Limit to 5 link previews per post
                preview_data = process_link_preview(url)
                if preview_data and (preview_data.get('title') or preview_data.get('embed_type')):
                    link_preview = LinkPreview(
                        post_id=post.id,
                        url=preview_data['url'],
                        title=preview_data.get('title'),
                        description=preview_data.get('description'),
                        image_url=preview_data.get('image_url'),
                        site_name=preview_data.get('site_name'),
                        embed_type=preview_data.get('embed_type'),
                        embed_id=preview_data.get('embed_id')
                    )
                    db.session.add(link_preview)
            db.session.commit()
        
        # Handle tags
        raw_tag_ids = request.form.getlist('tags')
        if raw_tag_ids:
            normalized_tag_ids = []
            for tag_id in raw_tag_ids:
                if tag_id is None:
                    continue
                try:
                    normalized_tag_ids.append(int(str(tag_id).strip()))
                except (TypeError, ValueError):
                    continue

            if normalized_tag_ids:
                for tag_id in normalized_tag_ids:
                    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
                    if tag:
                        post.tags.append(tag)
                db.session.commit()
        
        # Handle poll creation
        poll_question = request.form.get('poll_question', '').strip()
        poll_options = request.form.getlist('poll_options[]')
        poll_options = [opt.strip() for opt in poll_options if opt.strip()]
        
        if poll_question and len(poll_options) >= 2:
            poll_ends_at = request.form.get('poll_ends_at')
            ends_at = None
            if poll_ends_at:
                try:
                    ends_at = datetime.fromisoformat(poll_ends_at)
                except:
                    pass
            
            poll = Poll(
                post_id=post.id,
                question=poll_question,
                allows_multiple=request.form.get('poll_multiple') == 'on',
                ends_at=ends_at
            )
            db.session.add(poll)
            db.session.commit()
            
            for i, opt_text in enumerate(poll_options):
                option = PollOption(
                    poll_id=poll.id,
                    text=opt_text,
                    order=i
                )
                db.session.add(option)
            db.session.commit()
        
        flash(_('Post created.'), 'success')
        return redirect(next_url)
    
    pages = Page.query.filter_by(user_id=current_user.id, is_visible=True).order_by(Page.order).all()
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    user_groups = [m.group for m in GroupMembership.query.filter_by(user_id=current_user.id).all()]
    
    # Check for pre-selected group from URL param
    preselect_group_slug = request.args.get('group', '')
    preselect_group = None
    if preselect_group_slug:
        preselect_group = Group.query.filter_by(slug=preselect_group_slug).first()
        if preselect_group and preselect_group not in user_groups:
            preselect_group = None
    return render_template('me/new_post.html', pages=pages, tags=tags, user_groups=user_groups, preselect_group=preselect_group, next_url=next_url)


@blog_bp.route('/me/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first_or_404()

    # If schedule time has passed, publish the post immediately
    if post.scheduled_at and post.scheduled_at <= datetime.utcnow():
        post.is_published = True
        post.published_at = post.scheduled_at
        post.scheduled_at = None
        db.session.commit()

    next_url = request.args.get('next')
    if request.method == 'POST':
        next_url = request.form.get('next') or next_url
    if not is_safe_next(next_url):
        next_url = url_for('blog.me')
    
    if request.method == 'POST':
        old_title = post.title
        old_content = post.content
        old_is_published = post.is_published
        old_show_in_feed = getattr(post, 'show_in_feed', True)
        old_scheduled_at = post.scheduled_at
        old_group_id = post.group_id
        old_page_id = post.page_id

        new_title = request.form.get('title', '').strip() or None
        new_content = request.form.get('content', '').strip() or None
        old_mentions = set(extract_mentions(post.content or ''))
        new_mentions = set(extract_mentions(new_content or ''))
        newly_mentioned_usernames = list(new_mentions - old_mentions)
        
        # Save version if content changed
        if post.title != new_title or post.content != new_content:
            version_num = PostVersion.query.filter_by(post_id=post_id).count() + 1
            version = PostVersion(
                post_id=post_id,
                version_number=version_num,
                title=post.title,
                content=post.content,
                edited_by=current_user.id
            )
        post.title = new_title
        post.content = new_content
        post.is_published = request.form.get('is_published') == 'on'

        post.show_in_feed = 'show_in_feed' in request.form

        # Handle scheduled publishing
        scheduled_str = request.form.get('scheduled_at', '').strip()
        if scheduled_str:
            try:
                parsed = datetime.fromisoformat(scheduled_str)
                parsed_utc = _normalize_to_utc_naive(parsed)
                if parsed_utc > datetime.utcnow():
                    post.scheduled_at = parsed_utc
                else:
                    post.scheduled_at = old_scheduled_at if (old_scheduled_at and old_scheduled_at > datetime.utcnow()) else None
            except ValueError:
                post.scheduled_at = old_scheduled_at if (old_scheduled_at and old_scheduled_at > datetime.utcnow()) else None
        else:
            # Empty input means user explicitly removed the schedule
            post.scheduled_at = None

        if post.scheduled_at and post.scheduled_at > datetime.utcnow():
            post.is_published = False
            post.published_at = None
        else:
            # If the post is published (and not scheduled), ensure it has a publication timestamp
            if post.is_published and not post.published_at:
                post.published_at = datetime.utcnow()
        
        # Handle group assignment
        new_group_id = request.form.get('group_id') or None
        if new_group_id:
            membership = GroupMembership.query.filter_by(group_id=new_group_id, user_id=current_user.id).first()
            post.group_id = new_group_id if membership else None
        else:
            post.group_id = None

        # Pages don't apply to group posts
        if post.group_id:
            post.page_id = None
        else:
            post.page_id = request.form.get('page_id') or None

        # Mark as edited (used for '(bearbeitet)' badge in UI) - only when something changed
        if (
            post.title != old_title or
            post.content != old_content or
            post.is_published != old_is_published or
            getattr(post, 'show_in_feed', True) != old_show_in_feed or
            post.scheduled_at != old_scheduled_at or
            post.group_id != old_group_id or
            post.page_id != old_page_id
        ):
            post.updated_at = datetime.utcnow()
        
        # Handle new image uploads
        files = request.files.getlist('images')
        new_images_count = 0
        for file in files:
            if file and file.filename and file.filename.strip() and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4().hex}.jpg"
                if post.group_id:
                    rel_dir = f"uploads/groups/{post.group_id}/posts/{post.id}"
                    filepath = os.path.join(get_upload_folder('groups', str(post.group_id), 'posts', str(post.id)), filename)
                else:
                    rel_dir = f"uploads/users/{current_user.id}/posts/{post.id}"
                    filepath = os.path.join(get_upload_folder('users', str(current_user.id), 'posts', str(post.id)), filename)
                # Resize image to max resolution
                img = resize_image(file)
                img.save(filepath, 'JPEG', quality=85)
                file_size = os.path.getsize(filepath)
                
                media = Media(
                    user_id=current_user.id,
                    post_id=post.id,
                    filename=filename,
                    original_filename=original_filename,
                    file_path=f'{rel_dir}/{filename}',
                    file_type='image/jpeg',
                    file_size=file_size
                )
                db.session.add(media)
                new_images_count += 1
        
        # Handle tags
        raw_tag_ids = request.form.getlist('tags')
        post.tags = []
        normalized_tag_ids = []
        for tag_id in raw_tag_ids:
            if tag_id is None:
                continue
            try:
                normalized_tag_ids.append(int(str(tag_id).strip()))
            except (TypeError, ValueError):
                continue

        for tag_id in normalized_tag_ids:
            tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()
            if tag:
                post.tags.append(tag)
        
        db.session.commit()

        if newly_mentioned_usernames:
            mentioned_users = User.query.filter(User.username.in_(newly_mentioned_usernames)).all()
            for u in mentioned_users:
                if u.id == current_user.id:
                    continue
                notification = Notification(
                    user_id=u.id,
                    type='mention',
                    title=f'{current_user.display_name or current_user.username} hat dich in einem Beitrag erwähnt',
                    message=(new_content or '')[:100] + ('...' if new_content and len(new_content) > 100 else ''),
                    link=f'/post/{post.public_id}',
                    actor_id=current_user.id,
                    post_id=post.id
                )
                db.session.add(notification)
            db.session.commit()
        
        if new_images_count > 0:
            flash(_('Post updated. {n} new images added.').format(n=new_images_count), 'success')
        else:
            flash(_('Post updated.'), 'success')
        return redirect(next_url)
    
    pages = Page.query.filter_by(user_id=current_user.id, is_visible=True).order_by(Page.order).all()
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    user_groups = [m.group for m in GroupMembership.query.filter_by(user_id=current_user.id).all()]
    return render_template('me/edit_post.html', post=post, pages=pages, tags=tags, user_groups=user_groups, next_url=next_url)


@blog_bp.route('/me/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first_or_404()

    next_url = request.form.get('next') or request.args.get('next')
    if not is_safe_next(next_url):
        next_url = url_for('blog.me')
    
    # Delete associated media files
    for media in post.media_items:
        try:
            filepath = os.path.join(current_app.root_path, 'static', media.file_path)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    
    db.session.delete(post)
    db.session.commit()
    flash(_('Post deleted.'), 'success')
    return redirect(next_url)


@blog_bp.route('/me/media/<int:media_id>/delete', methods=['POST'])
@login_required
def delete_media(media_id):
    media = Media.query.filter_by(id=media_id, user_id=current_user.id).first_or_404()
    
    try:
        filepath = os.path.join(current_app.root_path, 'static', media.file_path)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass
    
    db.session.delete(media)
    db.session.commit()
    
    return jsonify({'success': True})


@blog_bp.route('/me/media/reorder', methods=['POST'])
@login_required
def reorder_media():
    """Reorder media items for a post."""
    data = request.get_json()
    order_data = data.get('order', [])
    
    for item in order_data:
        media = Media.query.filter_by(id=item['id'], user_id=current_user.id).first()
        if media:
            media.order = item['order']
    
    db.session.commit()
    return jsonify({'success': True})


# ============== API Endpoints ==============

@blog_bp.route('/api/link-preview', methods=['POST'])
@login_required
def api_link_preview():
    """Fetch link preview data for a URL."""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    preview_data = process_link_preview(url)
    
    if preview_data:
        return jsonify(preview_data)
    else:
        return jsonify({'error': 'Could not fetch preview'}), 404


@blog_bp.route('/api/render-markdown', methods=['POST'])
@login_required
def api_render_markdown():
    """Render markdown content to HTML."""
    data = request.get_json()
    content = data.get('content', '')
    
    html = render_markdown(content)
    return jsonify({'html': html})


@blog_bp.route('/api/posts')
@login_required
def api_posts():
    """Get paginated posts as JSON for AJAX loading."""
    page = request.args.get('page', 1, type=int)
    now = datetime.utcnow()
    
    # Show ALL own posts (including unpublished and scheduled)
    posts_query = Post.query.filter_by(user_id=current_user.id)
    posts_query = posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())
    total_posts = posts_query.count()
    posts = posts_query.offset((page - 1) * POSTS_PER_PAGE).limit(POSTS_PER_PAGE).all()
    has_more = (page * POSTS_PER_PAGE) < total_posts
    
    posts_data = []
    for post in posts:
        media_items = []
        for media in post.media_items.order_by('order').all():
            media_items.append({
                'file_path': media.file_path,
                'alt_text': media.alt_text or _('Image')
            })
        
        link_previews = []
        for preview in post.link_previews:
            link_previews.append({
                'embed_type': preview.embed_type,
                'embed_id': preview.embed_id,
                'url': preview.url,
                'title': preview.title,
                'description': preview.description,
                'image_url': preview.image_url,
                'site_name': preview.site_name
            })
        
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': render_markdown(post.content) if post.content else '',
            'created_at': format_datetime_i18n(post.scheduled_at or post.published_at or post.created_at),
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'scheduled_at': (post.scheduled_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z') if post.scheduled_at else None),
            'published_at': (post.published_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z') if post.published_at else None),
            'is_scheduled_future': bool(post.scheduled_at and post.scheduled_at > now),
            'is_published': post.is_published,
            'is_unpublished': not post.is_published,
            'is_edited': bool(post.updated_at and post.created_at and post.updated_at > post.created_at),
            'page_title': post.page.title if post.page else None,
            'page_slug': post.page.slug if post.page else None,
            'group_name': post.group.name if post.group else None,
            'group_slug': post.group.slug if post.group else None,
            'group_color': post.group.color if post.group else None,
            'media_items': media_items,
            'link_previews': link_previews
        })
    
    return jsonify({
        'posts': posts_data,
        'has_more': has_more,
        'current_page': page
    })


@blog_bp.route('/me/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account.

    Modes:
    - delete_all: delete all user-owned content, then anonymize account record.
    - keep_posts: keep posts, but anonymize user and remove personal data.
    """
    password = (request.form.get('password') or '').strip()
    mode = (request.form.get('mode') or '').strip()

    if not password or not current_user.check_password(password):
        flash(_('Invalid password.'), 'error')
        return redirect(url_for('blog.settings'))

    if mode not in ('delete_all', 'keep_posts'):
        flash(_('Please choose how your account should be deleted.'), 'error')
        return redirect(url_for('blog.settings'))

    user = User.query.get(current_user.id)
    if not user:
        flash(_('Invalid credentials.'), 'error')
        return redirect(url_for('auth.logout'))

    def _delete_user_non_post_data(*, delete_media: bool):
        if delete_media:
            try:
                for media in Media.query.filter_by(user_id=user.id).all():
                    try:
                        filepath = os.path.join(current_app.root_path, 'static', media.file_path)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                    except Exception:
                        pass
                    db.session.delete(media)
            except Exception:
                pass

        try:
            CommentReaction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass
        try:
            Comment.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass
        try:
            Bookmark.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass
        try:
            Follow.query.filter(db.or_(Follow.follower_id == user.id, Follow.followed_id == user.id)).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            Reaction.query.filter_by(user_id=user.id).update({Reaction.user_id: None}, synchronize_session=False)
        except Exception:
            pass

        try:
            Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass
        try:
            Notification.query.filter_by(actor_id=user.id).update({Notification.actor_id: None}, synchronize_session=False)
        except Exception:
            pass

        try:
            GroupMembership.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            group_files = GroupFile.query.filter_by(uploaded_by=user.id).all()
            for gf in group_files:
                try:
                    file_abs = os.path.join(current_app.root_path, 'static', gf.file_path)
                    if os.path.exists(file_abs):
                        os.remove(file_abs)
                except Exception:
                    pass
                db.session.delete(gf)
        except Exception:
            pass

        try:
            Tag.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            for page in Page.query.filter_by(user_id=user.id).all():
                db.session.delete(page)
        except Exception:
            pass

    if mode == 'delete_all':
        _delete_user_non_post_data(delete_media=True)
        try:
            for post in Post.query.filter_by(user_id=user.id).all():
                db.session.delete(post)
        except Exception:
            pass
    else:
        # keep_posts: remove everything except posts (+ their media)
        _delete_user_non_post_data(delete_media=False)

    # Always anonymize the user record (so FK constraints stay valid if posts are kept)
    user.is_deleted = True
    from datetime import datetime as _dt
    user.deleted_at = _dt.utcnow()
    user.is_active = False

    # Remove personal data
    user.display_name = None
    user.bio = None
    user.avatar_url = None
    user.cover_image_url = None

    # Make username/email unusable and unique
    anon_suffix = uuid.uuid4().hex[:12]
    user.username = f"deleted_{anon_suffix}"
    user.email = f"deleted_{anon_suffix}@example.invalid"
    user.password_hash = None

    # Invalidate sessions
    user.rotate_session_token()

    db.session.commit()

    from flask_login import logout_user
    logout_user()
    flash(_('Your account has been deleted.'), 'success')
    return redirect(url_for('index'))


# ============== Template Filters ==============

@blog_bp.app_template_filter('markdown')
def markdown_filter(text):
    """Jinja2 filter for rendering markdown."""
    return render_markdown(text)


@blog_bp.app_template_filter('embed_html')
def embed_html_filter(link_preview):
    """Jinja2 filter for generating embed HTML."""
    if link_preview.embed_type and link_preview.embed_type != 'link':
        return get_embed_html(link_preview.embed_type, link_preview.embed_id)
    return ''
