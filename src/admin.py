"""Analytics Dashboard - Admin-only access via .env credentials."""
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from flask_babel import gettext as _
from sqlalchemy import func, desc, extract, case, distinct
from extensions import db
from models import (
    User, Post, Comment, Reaction, Bookmark, 
    Notification, Tag, Group, GroupMembership, GroupFile,
    Poll, PollVote, Media, post_tags
)

admin_bp = Blueprint('admin', __name__, url_prefix='/analytics')


def get_admin_credentials():
    """Get admin credentials from environment variables."""
    username = os.environ.get('ANALYTICS_ADMIN_USERNAME', 'admin')
    password = os.environ.get('ANALYTICS_ADMIN_PASSWORD')
    return username, password


def admin_required(f):
    """Decorator to require analytics admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('analytics_admin_authenticated'):
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Analytics admin login."""
    if session.get('analytics_admin_authenticated'):
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        admin_username, admin_password = get_admin_credentials()
        
        if not admin_password:
            flash(_('Analytics admin is not configured. Please set ANALYTICS_ADMIN_PASSWORD in .env.'), 'error')
            return render_template('admin/login.html')
        
        if username == admin_username and password == admin_password:
            session['analytics_admin_authenticated'] = True
            session['analytics_admin_login_time'] = datetime.now().isoformat()
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        
        flash(_('Invalid credentials.'), 'error')
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Analytics admin logout."""
    session.pop('analytics_admin_authenticated', None)
    session.pop('analytics_admin_login_time', None)
    flash(_('You have been logged out.'), 'success')
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    """Main analytics dashboard."""
    # Time ranges
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # === OVERVIEW KPIs ===
    kpis = {
        'users': {
            'total': User.query.count(),
            'active': User.query.filter_by(is_active=True).count(),
            'new_today': User.query.filter(User.created_at >= today).count(),
            'new_week': User.query.filter(User.created_at >= week_ago).count(),
            'new_month': User.query.filter(User.created_at >= month_ago).count(),
        },
        'posts': {
            'total': Post.query.count(),
            'published': Post.query.filter_by(is_published=True).count(),
            'new_today': Post.query.filter(Post.created_at >= today).count(),
            'new_week': Post.query.filter(Post.created_at >= week_ago).count(),
            'new_month': Post.query.filter(Post.created_at >= month_ago).count(),
        },
        'comments': {
            'total': Comment.query.count(),
            'new_today': Comment.query.filter(Comment.created_at >= today).count(),
            'new_week': Comment.query.filter(Comment.created_at >= week_ago).count(),
            'new_month': Comment.query.filter(Comment.created_at >= month_ago).count(),
        },
        'reactions': {
            'total': Reaction.query.count(),
            'new_today': Reaction.query.filter(Reaction.created_at >= today).count(),
            'new_week': Reaction.query.filter(Reaction.created_at >= week_ago).count(),
            'new_month': Reaction.query.filter(Reaction.created_at >= month_ago).count(),
        },
        'groups': {
            'total': Group.query.count(),
            'members_total': GroupMembership.query.count(),
            'new_week': Group.query.filter(Group.created_at >= week_ago).count(),
        },
        'bookmarks': {
            'total': Bookmark.query.count(),
            'new_week': Bookmark.query.filter(Bookmark.created_at >= week_ago).count(),
        },
        'media': {
            'total': Media.query.count(),
            'total_size': db.session.query(func.coalesce(func.sum(Media.file_size), 0)).scalar() or 0,
        },
        'group_files': {
            'total': GroupFile.query.count(),
            'total_size': db.session.query(func.coalesce(func.sum(GroupFile.file_size), 0)).scalar() or 0,
        },
    }
    
    # === ENGAGEMENT METRICS ===
    # Reactions by emoji
    emoji_stats = db.session.query(
        Reaction.emoji,
        func.count(Reaction.id).label('count')
    ).group_by(Reaction.emoji).order_by(desc('count')).all()
    
    # === TOP CONTENT ===
    # Intentionally not returning post/comment contents in analytics dashboard
    
    # === TOP USERS ===
    # Most active posters
    top_posters = db.session.query(
        User,
        func.count(Post.id).label('post_count')
    ).outerjoin(Post).group_by(User.id).order_by(desc('post_count')).limit(10).all()
    
    # === TOP TAGS ===
    top_tags = db.session.query(
        Tag.name,
        Tag.color,
        func.count(post_tags.c.post_id).label('usage_count')
    ).outerjoin(post_tags).group_by(Tag.id).order_by(desc('usage_count')).limit(15).all()
    
    # === TOP GROUPS ===
    top_groups = db.session.query(
        Group,
        func.count(distinct(GroupMembership.id)).label('member_count'),
        func.count(distinct(Post.id)).label('post_count')
    ).outerjoin(GroupMembership).outerjoin(Post).group_by(Group.id).order_by(desc('member_count')).limit(10).all()
    
    # === RECENT ACTIVITY ===
    recent_users = User.query.order_by(desc(User.created_at)).limit(12).all()
    
    # === NOTIFICATIONS STATS ===
    notification_stats = db.session.query(
        Notification.type,
        func.count(Notification.id).label('count')
    ).group_by(Notification.type).all()
    
    unread_notifications = Notification.query.filter_by(is_read=False).count()
    
    return render_template('admin/dashboard.html',
        kpis=kpis,
        emoji_stats=emoji_stats,
        top_posters=top_posters,
        top_tags=top_tags,
        top_groups=top_groups,
        recent_users=recent_users,
        notification_stats=notification_stats,
        unread_notifications=unread_notifications,
        now=now
    )


@admin_bp.route('/api/charts/activity')
@admin_required
def charts_activity():
    """API endpoint for activity charts data."""
    days = int(request.args.get('days', 30))
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # Generate date range
    dates = []
    current = start_date
    while current <= now:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    # Posts per day
    posts_data = db.session.query(
        func.date(Post.created_at).label('date'),
        func.count(Post.id).label('count')
    ).filter(
        Post.created_at >= start_date
    ).group_by(func.date(Post.created_at)).all()
    posts_dict = {str(d.date): d.count for d in posts_data}
    
    # Comments per day
    comments_data = db.session.query(
        func.date(Comment.created_at).label('date'),
        func.count(Comment.id).label('count')
    ).filter(
        Comment.created_at >= start_date
    ).group_by(func.date(Comment.created_at)).all()
    comments_dict = {str(d.date): d.count for d in comments_data}
    
    # Reactions per day
    reactions_data = db.session.query(
        func.date(Reaction.created_at).label('date'),
        func.count(Reaction.id).label('count')
    ).filter(
        Reaction.created_at >= start_date
    ).group_by(func.date(Reaction.created_at)).all()
    reactions_dict = {str(d.date): d.count for d in reactions_data}
    
    # Users per day
    users_data = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(func.date(User.created_at)).all()
    users_dict = {str(d.date): d.count for d in users_data}
    
    return jsonify({
        'labels': dates,
        'posts': [posts_dict.get(d, 0) for d in dates],
        'comments': [comments_dict.get(d, 0) for d in dates],
        'reactions': [reactions_dict.get(d, 0) for d in dates],
        'users': [users_dict.get(d, 0) for d in dates],
    })


@admin_bp.route('/api/charts/engagement')
@admin_required
def charts_engagement():
    """API endpoint for engagement breakdown."""
    # Reactions by emoji
    emoji_data = db.session.query(
        Reaction.emoji,
        func.count(Reaction.id).label('count')
    ).group_by(Reaction.emoji).order_by(desc('count')).all()
    
    # Post types
    post_types = db.session.query(
        Post.post_type,
        func.count(Post.id).label('count')
    ).group_by(Post.post_type).all()
    
    # Notification types
    notif_types = db.session.query(
        Notification.type,
        func.count(Notification.id).label('count')
    ).group_by(Notification.type).all()
    
    return jsonify({
        'emojis': {
            'labels': [e.emoji for e in emoji_data],
            'data': [e.count for e in emoji_data]
        },
        'post_types': {
            'labels': [p.post_type or 'text' for p in post_types],
            'data': [p.count for p in post_types]
        },
        'notification_types': {
            'labels': [n.type for n in notif_types],
            'data': [n.count for n in notif_types]
        }
    })


@admin_bp.route('/api/charts/growth')
@admin_required
def charts_growth():
    """API endpoint for cumulative growth data."""
    days = int(request.args.get('days', 30))
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # Get cumulative counts
    dates = []
    users_cumulative = []
    posts_cumulative = []
    
    current = start_date
    while current <= now:
        date_str = current.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        users_count = User.query.filter(User.created_at <= current + timedelta(days=1)).count()
        posts_count = Post.query.filter(Post.created_at <= current + timedelta(days=1)).count()
        
        users_cumulative.append(users_count)
        posts_cumulative.append(posts_count)
        
        current += timedelta(days=1)
    
    return jsonify({
        'labels': dates,
        'users': users_cumulative,
        'posts': posts_cumulative
    })


@admin_bp.route('/api/stats/realtime')
@admin_required
def stats_realtime():
    """API endpoint for real-time stats (for live updates)."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)
    
    return jsonify({
        'users_total': User.query.count(),
        'users_today': User.query.filter(User.created_at >= today).count(),
        'posts_total': Post.query.count(),
        'posts_today': Post.query.filter(Post.created_at >= today).count(),
        'comments_today': Comment.query.filter(Comment.created_at >= today).count(),
        'reactions_today': Reaction.query.filter(Reaction.created_at >= today).count(),
        'reactions_hour': Reaction.query.filter(Reaction.created_at >= hour_ago).count(),
        'active_users_today': db.session.query(func.count(distinct(Post.user_id))).filter(
            Post.created_at >= today
        ).scalar() or 0,
        'timestamp': now.isoformat()
    })


def format_bytes(size):
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


# Register template filter
@admin_bp.app_template_filter('format_bytes')
def format_bytes_filter(size):
    return format_bytes(size or 0)
