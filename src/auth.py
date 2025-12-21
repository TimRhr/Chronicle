import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _, force_locale
from authlib.integrations.flask_client import OAuth
from extensions import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

oauth = OAuth()


def is_safe_next(next_url: str | None) -> bool:
    if not next_url:
        return False
    if next_url.startswith(('http://', 'https://')):
        try:
            parsed = urlparse(next_url)
            return parsed.netloc == ''
        except Exception:
            return False
    return next_url.startswith('/') and not next_url.startswith('//')


def init_oauth(app):
    oauth.init_app(app)
    
    # Configure Keycloak if enabled
    if app.config.get('KEYCLOAK_ENABLED'):
        oauth.register(
            name='keycloak',
            client_id=app.config['KEYCLOAK_CLIENT_ID'],
            client_secret=app.config['KEYCLOAK_CLIENT_SECRET'],
            server_metadata_url=f"{app.config['KEYCLOAK_SERVER_URL']}/realms/{app.config['KEYCLOAK_REALM']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid email profile'},
        )


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('10 per hour') if limiter else (lambda f: f)
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    from models import User, PasswordResetToken
    from extensions import db

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        if not email or '@' not in email:
            flash(_('Please enter a valid email address.'), 'error')
            return render_template('auth/forgot_password.html')

        user = User.query.filter_by(email=email).first()

        # Always show the same message to avoid account enumeration.
        flash(_('If an account exists for this email address, you will receive a password reset link shortly.'), 'success')

        if user and user.password_hash:
            ttl_minutes = int(current_app.config.get('PASSWORD_RESET_TOKEN_TTL_MINUTES', 30))
            now = datetime.now(timezone.utc)
            token = PasswordResetToken(
                user_id=user.id,
                token=PasswordResetToken.generate_token(),
                created_at=now,
                expires_at=now + timedelta(minutes=ttl_minutes),
            )
            db.session.add(token)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token.token, _external=True)
            logo_url = url_for('static', filename='assets/logo.png', _external=True)

            locale = getattr(user, 'language', None) or current_app.config.get('BABEL_DEFAULT_LOCALE')
            with force_locale(locale):
                subject = _('Password reset')
                html_body = render_template(
                    'emails/password_reset.html',
                    reset_url=reset_url,
                    ttl_minutes=ttl_minutes,
                    logo_url=logo_url,
                )
                text_body = render_template(
                    'emails/password_reset.txt',
                    reset_url=reset_url,
                    ttl_minutes=ttl_minutes,
                )

            try:
                from mail import send_mail
                send_mail(to_email=user.email, subject=subject, text_body=text_body, html_body=html_body)
            except Exception as e:
                current_app.logger.error(f'Error sending password reset email: {e}')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per hour') if limiter else (lambda f: f)
def reset_password(token: str):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    from models import User, PasswordResetToken
    from extensions import db

    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    if not reset_token or not reset_token.is_usable():
        flash(_('This password reset link is invalid or has expired.'), 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.get(reset_token.user_id)
    if not user or not user.password_hash:
        flash(_('This password reset link is invalid or has expired.'), 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        errors = []
        if not password or len(password) < 12:
            errors.append(_('Password must be at least 12 characters long.'))
        elif not any(c.isupper() for c in password):
            errors.append(_('Password must contain at least one uppercase letter.'))
        elif not any(c.islower() for c in password):
            errors.append(_('Password must contain at least one lowercase letter.'))
        elif not any(c.isdigit() for c in password):
            errors.append(_('Password must contain at least one number.'))
        elif not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password):
            errors.append(_('Password must contain at least one special character.'))

        if password != password_confirm:
            errors.append(_('Passwords do not match.'))

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user.set_password(password)
            user.rotate_session_token()
            reset_token.used_at = datetime.now(timezone.utc)
            db.session.commit()

            flash(_('Your password has been updated. You can now log in.'), 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per hour') if limiter else (lambda f: f)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    from models import User
    from extensions import db
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.check_password(password):
            user.rotate_session_token()
            db.session.commit()
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_next(next_page) else url_for('index'))
        
        flash(_('Invalid credentials.'), 'error')
    
    keycloak_enabled = current_app.config.get('KEYCLOAK_ENABLED', False)
    next_page = request.args.get('next')
    return render_template('auth/login.html', keycloak_enabled=keycloak_enabled, next_page=next_page)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per hour') if limiter else (lambda f: f)
def register():
    if not current_app.config.get('REGISTRATION_ENABLED', True):
        flash(_('Registration is disabled.'), 'error')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    from models import User
    from extensions import db
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        errors = []
        
        if not username or len(username) < 3:
            errors.append(_('Username must be at least 3 characters long.'))
        
        if not email or '@' not in email:
            errors.append(_('Please enter a valid email address.'))
        
        # Password validation: 12+ chars, uppercase, lowercase, number, special char
        if not password or len(password) < 12:
            errors.append(_('Password must be at least 12 characters long.'))
        elif not any(c.isupper() for c in password):
            errors.append(_('Password must contain at least one uppercase letter.'))
        elif not any(c.islower() for c in password):
            errors.append(_('Password must contain at least one lowercase letter.'))
        elif not any(c.isdigit() for c in password):
            errors.append(_('Password must contain at least one number.'))
        elif not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password):
            errors.append(_('Password must contain at least one special character.'))
        
        if password != password_confirm:
            errors.append(_('Passwords do not match.'))
        
        if User.query.filter_by(username=username).first():
            errors.append(_('Username is already taken.'))
        
        if User.query.filter_by(email=email).first():
            errors.append(_('Email address is already registered.'))
        
        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            user.language = session.get('language') or current_app.config.get('BABEL_DEFAULT_LOCALE')
            db.session.add(user)
            db.session.commit()
            
            flash(_('Registration successful! You can now log in.'), 'success')
            user.rotate_session_token()
            db.session.commit()
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_next(next_page) else url_for('index'))
    
    return render_template('auth/register.html')


@auth_bp.route('/register/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per hour') if limiter else (lambda f: f)
def invite_register(token: str):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    from models import User, Invite
    from extensions import db

    invite = Invite.query.filter_by(token=token).first()
    if not invite or not invite.is_usable():
        flash(_('This invitation link is invalid or has expired.'), 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        invite_code = (request.form.get('invite_code') or '').strip()

        errors = []

        if not invite_code or not invite.check_code(invite_code):
            errors.append(_('Invalid invitation code.'))

        if not username or len(username) < 3:
            errors.append(_('Username must be at least 3 characters long.'))

        # Password validation: 12+ chars, uppercase, lowercase, number, special char
        if not password or len(password) < 12:
            errors.append(_('Password must be at least 12 characters long.'))
        elif not any(c.isupper() for c in password):
            errors.append(_('Password must contain at least one uppercase letter.'))
        elif not any(c.islower() for c in password):
            errors.append(_('Password must contain at least one lowercase letter.'))
        elif not any(c.isdigit() for c in password):
            errors.append(_('Password must contain at least one number.'))
        elif not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password):
            errors.append(_('Password must contain at least one special character.'))

        if password != password_confirm:
            errors.append(_('Passwords do not match.'))

        if User.query.filter_by(username=username).first():
            errors.append(_('Username is already taken.'))

        if User.query.filter_by(email=invite.email).first():
            errors.append(_('Email address is already registered.'))

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user = User(username=username, email=invite.email)
            user.set_password(password)
            user.language = session.get('language') or current_app.config.get('BABEL_DEFAULT_LOCALE')
            db.session.add(user)

            invite.used_at = datetime.now(timezone.utc)
            db.session.commit()

            flash(_('Registration successful! You can now log in.'), 'success')
            user.rotate_session_token()
            db.session.commit()
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_next(next_page) else url_for('index'))

    return render_template('auth/invite_register.html', invite_email=invite.email)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('You have been logged out.'), 'success')
    return redirect(url_for('index'))


# Keycloak SSO routes
@auth_bp.route('/login/keycloak')
def login_keycloak():
    if not current_app.config.get('KEYCLOAK_ENABLED'):
        flash(_('Keycloak SSO is not enabled.'), 'error')
        return redirect(url_for('auth.login'))

    next_page = request.args.get('next')
    if is_safe_next(next_page):
        session['keycloak_next'] = next_page
    else:
        session.pop('keycloak_next', None)

    redirect_uri = url_for('auth.keycloak_callback', _external=True)
    return oauth.keycloak.authorize_redirect(redirect_uri)


@auth_bp.route('/callback/keycloak')
def keycloak_callback():
    if not current_app.config.get('KEYCLOAK_ENABLED'):
        return redirect(url_for('auth.login'))
    
    from models import User
    from extensions import db
    
    try:
        token = oauth.keycloak.authorize_access_token()
        userinfo = token.get('userinfo')
        
        if not userinfo:
            flash(_('Error during Keycloak login.'), 'error')
            return redirect(url_for('auth.login'))
        
        # Find or create user
        sso_id = userinfo.get('sub')
        email = userinfo.get('email')
        username = userinfo.get('preferred_username', email.split('@')[0])

        if not sso_id:
            flash(_('Keycloak profile is incomplete (missing sub).'), 'error')
            return redirect(url_for('auth.login'))

        if not email:
            flash(_('Keycloak profile has no email address. Please allow email in Keycloak.'), 'error')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(sso_provider='keycloak', sso_id=sso_id).first()
        
        if not user:
            # Check if user with same email exists
            user = User.query.filter_by(email=email).first()
            if user:
                # Link existing account to Keycloak
                user.sso_provider = 'keycloak'
                user.sso_id = sso_id
            else:
                session['keycloak_pending'] = {
                    'sso_id': sso_id,
                    'email': email,
                    'suggested_username': username,
                }
                return redirect(url_for('auth.keycloak_register'))

            db.session.commit()

        session.pop('keycloak_pending', None)
        login_user(user)
        next_page = session.pop('keycloak_next', None)
        return redirect(next_page if is_safe_next(next_page) else url_for('index'))
        
    except Exception as e:
        current_app.logger.error(f'Keycloak callback error: {e}')
        flash(_('Error during Keycloak login.'), 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/register/keycloak', methods=['GET', 'POST'])
def keycloak_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    pending = session.get('keycloak_pending') or {}
    sso_id = pending.get('sso_id')
    email = pending.get('email')
    suggested_username = pending.get('suggested_username')

    if not sso_id or not email:
        flash(_('Keycloak registration was canceled. Please log in again.'), 'error')
        return redirect(url_for('auth.login'))

    from models import User
    from extensions import db

    existing_by_email = User.query.filter_by(email=email).first()
    if existing_by_email:
        if existing_by_email.sso_provider and (
            existing_by_email.sso_provider != 'keycloak' or (existing_by_email.sso_id and existing_by_email.sso_id != sso_id)
        ):
            flash(_('This account is already linked to another login provider.'), 'error')
            return redirect(url_for('auth.login'))

        existing_by_email.sso_provider = 'keycloak'
        existing_by_email.sso_id = sso_id
        db.session.commit()

        session.pop('keycloak_pending', None)
        login_user(existing_by_email)

        next_page = session.pop('keycloak_next', None)
        return redirect(next_page if is_safe_next(next_page) else url_for('index'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()

        errors = []
        if not username or len(username) < 3:
            errors.append(_('Username must be at least 3 characters long.'))
        if username and not re.match(r'^[A-Za-z0-9_.-]+$', username):
            errors.append(_('Username may only contain letters, numbers and _ . -'))
        if username and User.query.filter_by(username=username).first():
            errors.append(_('Username is already taken.'))
        if User.query.filter_by(sso_provider='keycloak', sso_id=sso_id).first():
            errors.append(_('This Keycloak account is already linked.'))

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user = User(
                username=username,
                email=email,
                sso_provider='keycloak',
                sso_id=sso_id,
            )
            user.language = session.get('language') or current_app.config.get('BABEL_DEFAULT_LOCALE')
            db.session.add(user)
            db.session.commit()

            session.pop('keycloak_pending', None)
            login_user(user)

            next_page = session.pop('keycloak_next', None)
            return redirect(next_page if is_safe_next(next_page) else url_for('index'))

    return render_template('auth/keycloak_register.html', email=email, suggested_username=suggested_username)


@auth_bp.route('/cancel/keycloak')
def cancel_keycloak_register():
    session.pop('keycloak_pending', None)
    session.pop('keycloak_next', None)
    flash(_('Keycloak registration canceled.'), 'success')
    return redirect(url_for('auth.login'))
