"""Social features: reactions, comments, bookmarks, tags, search, archive."""
import uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import func, extract
from slugify import slugify
from extensions import db, limiter
from models import (
    Post,
    Tag,
    Reaction,
    Bookmark,
    Comment,
    CommentReaction,
    Notification,
    Follow,
    User,
    Page,
    Poll,
    PollOption,
    PollVote,
    PostVersion,
    Group,
    GroupMembership,
    GroupFile,
    GroupAnnouncement,
    PushSubscription,
)
import os
import shutil
from werkzeug.utils import secure_filename
from content_utils import extract_mentions
from push import send_push_notification

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


def format_datetime_i18n(dt):
    """Format datetime with i18n support for API responses"""
    if dt is None:
        return ''
    dt_local = dt
    try:
        dt_local = dt.replace(tzinfo=timezone.utc).astimezone(_get_app_timezone())
    except Exception:
        dt_local = dt
    lang = session.get('language', 'de')
    if current_user.is_authenticated and current_user.language:
        lang = current_user.language
    if lang == 'en':
        return dt_local.strftime('%m/%d/%Y at %H:%M')
    else:
        return dt_local.strftime('%d.%m.%Y um %H:%M')


def optional_limit(limit_string):
    """Create a no-op decorator if limiter is not available."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_string)(f)
        return f
    return decorator


def exempt_from_limiter(f):
    """Exempt a route from rate limiting."""
    if limiter:
        return limiter.exempt(f)
    return f

social_bp = Blueprint('social', __name__)


def get_user_group_ids(user_id: int) -> list[int]:
    """Return IDs of groups the given user belongs to."""
    return [m.group_id for m in GroupMembership.query.filter_by(user_id=user_id).all()]


def _delete_static_file(static_url: str | None):
    if not static_url:
        return
    rel = None
    if static_url.startswith('/static/'):
        rel = static_url[len('/static/'):]
    elif '/static/' in static_url:
        rel = static_url.split('/static/', 1)[1]
    if not rel:
        return
    abs_path = os.path.join(current_app.root_path, 'static', rel)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception:
        pass


def _delete_group_and_related(group: Group):
    _delete_static_file(group.cover_image_url)
    _delete_static_file(group.icon_url)

    group_files = GroupFile.query.filter_by(group_id=group.id).all()
    for gf in group_files:
        try:
            file_abs = os.path.join(current_app.root_path, 'static', gf.file_path)
            if os.path.exists(file_abs):
                os.remove(file_abs)
        except Exception:
            pass
        db.session.delete(gf)

    try:
        group_upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'groups', str(group.id))
        if os.path.exists(group_upload_dir):
            shutil.rmtree(group_upload_dir, ignore_errors=True)
    except Exception:
        pass

    group_posts = Post.query.filter_by(group_id=group.id).all()
    for post in group_posts:
        for media in post.media_items.all() if hasattr(post.media_items, 'all') else list(post.media_items):
            try:
                media_abs = os.path.join(current_app.root_path, 'static', media.file_path)
                if os.path.exists(media_abs):
                    os.remove(media_abs)
            except Exception:
                pass
            try:
                db.session.delete(media)
            except Exception:
                pass

        try:
            Notification.query.filter_by(post_id=post.id).delete(synchronize_session=False)
        except Exception:
            pass

        db.session.delete(post)

    db.session.delete(group)
    db.session.commit()


# ============== Reactions ==============

ALLOWED_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🎉']

@social_bp.route('/api/posts/<int:post_id>/reactions', methods=['GET'])
@exempt_from_limiter
def get_reactions(post_id):
    """Get reaction counts for a post with user details for owner view."""
    post = Post.query.get_or_404(post_id)
    
    # Get all reactions with user info
    all_reactions = Reaction.query.filter_by(post_id=post_id).all()
    
    result = {emoji: {'count': 0, 'users': []} for emoji in ALLOWED_EMOJIS}
    for reaction in all_reactions:
        if reaction.emoji in result:
            result[reaction.emoji]['count'] += 1
            if reaction.user_id:
                user = User.query.get(reaction.user_id)
                if user:
                    result[reaction.emoji]['users'].append(user.display_name or user.username)
    
    # Check if current user has reacted
    user_reactions = []
    is_owner = current_user.is_authenticated and post.user_id == current_user.id
    if current_user.is_authenticated:
        user_reacts = Reaction.query.filter_by(post_id=post_id, user_id=current_user.id).all()
        user_reactions = [r.emoji for r in user_reacts]
    
    total = sum(r['count'] for r in result.values())
    
    return jsonify({
        'reactions': result,
        'user_reactions': user_reactions,
        'total': total,
        'is_owner': is_owner
    })


@social_bp.route('/api/posts/<int:post_id>/reactions', methods=['POST'])
@optional_limit("30 per minute")
@login_required
def toggle_reaction(post_id):
    """Toggle a reaction on a post. Users cannot react to their own posts."""
    post = Post.query.get_or_404(post_id)
    
    # Prevent users from reacting to their own posts
    if post.user_id == current_user.id:
        return jsonify({'error': 'Du kannst nicht auf deine eigenen Posts reagieren'}), 403
    
    data = request.get_json()
    emoji = data.get('emoji')
    
    if emoji not in ALLOWED_EMOJIS:
        return jsonify({'error': 'Invalid emoji'}), 400
    
    # Check if user already reacted with this emoji
    existing = Reaction.query.filter_by(
        post_id=post_id, user_id=current_user.id, emoji=emoji
    ).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'action': 'removed', 'emoji': emoji})
    else:
        reaction = Reaction(post_id=post_id, user_id=current_user.id, emoji=emoji)
        db.session.add(reaction)
        db.session.commit()
        
        # Create notification for post owner
        create_notification(
            user_id=post.user_id,
            type='reaction',
            title=_('{name} reacted with {emoji}').format(name=(current_user.display_name or current_user.username), emoji=emoji),
            link=f'/post/{post.public_id}',
            actor_id=current_user.id,
            post_id=post_id
        )
        
        return jsonify({'action': 'added', 'emoji': emoji})


# ============== Comment Reactions ==============

@social_bp.route('/api/comments/<int:comment_id>/reactions', methods=['GET'])
@exempt_from_limiter
def get_comment_reactions(comment_id):
    """Get reaction counts for a comment."""
    comment = Comment.query.get_or_404(comment_id)
    all_reactions = CommentReaction.query.filter_by(comment_id=comment_id).all()

    result = {emoji: {'count': 0, 'users': []} for emoji in ALLOWED_EMOJIS}
    for r in all_reactions:
        if r.emoji in result:
            result[r.emoji]['count'] += 1
            if r.user_id:
                u = User.query.get(r.user_id)
                if u:
                    result[r.emoji]['users'].append(u.display_name or u.username)

    user_reaction = None
    if current_user.is_authenticated:
        existing = CommentReaction.query.filter_by(comment_id=comment_id, user_id=current_user.id).first()
        user_reaction = existing.emoji if existing else None

    total = sum(info['count'] for info in result.values())
    return jsonify({'reactions': result, 'user_reaction': user_reaction, 'total': total})


@social_bp.route('/api/comments/<int:comment_id>/reactions', methods=['POST'])
@optional_limit("30 per minute")
@login_required
def toggle_comment_reaction(comment_id):
    """Toggle/change a reaction on a comment. One reaction per user per comment."""
    comment = Comment.query.get_or_404(comment_id)
    data = request.get_json() or {}
    emoji = data.get('emoji')

    if emoji not in ALLOWED_EMOJIS:
        return jsonify({'error': 'Invalid emoji'}), 400

    existing = CommentReaction.query.filter_by(comment_id=comment_id, user_id=current_user.id).first()

    # Same emoji => remove
    if existing and existing.emoji == emoji:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'action': 'removed', 'emoji': emoji})

    # Different emoji => change
    if existing:
        existing.emoji = emoji
        db.session.commit()
        return jsonify({'action': 'changed', 'emoji': emoji})

    # None => add
    r = CommentReaction(comment_id=comment_id, user_id=current_user.id, emoji=emoji)
    db.session.add(r)
    db.session.commit()

    # Optional notification for comment author
    if comment.user_id != current_user.id:
        try:
            create_notification(
                user_id=comment.user_id,
                type='reaction',
                title=_('{name} reacted with {emoji} to your comment').format(name=(current_user.display_name or current_user.username), emoji=emoji),
                link=f'/post/{comment.post.public_id}',
                actor_id=current_user.id,
                post_id=comment.post_id,
                comment_id=comment.id
            )
        except Exception:
            pass

    return jsonify({'action': 'added', 'emoji': emoji})


# ============== Bookmarks ==============

@social_bp.route('/api/posts/<int:post_id>/bookmark', methods=['GET'])
@login_required
@exempt_from_limiter
def get_bookmark_status(post_id):
    """Check if post is bookmarked by current user."""
    existing = Bookmark.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    return jsonify({'bookmarked': existing is not None})


@social_bp.route('/api/posts/<int:post_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(post_id):
    """Toggle bookmark on a post."""
    post = Post.query.get_or_404(post_id)
    
    existing = Bookmark.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'bookmarked': False})
    else:
        bookmark = Bookmark(post_id=post_id, user_id=current_user.id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({'bookmarked': True})


@social_bp.route('/me/bookmarks')
@login_required
def my_bookmarks():
    """View user's bookmarked posts."""
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
    posts = [b.post for b in bookmarks]
    return render_template('me/bookmarks.html', posts=posts)




# ============== Comments ==============

@social_bp.route('/api/posts/<int:post_id>/comments', methods=['GET'])
@exempt_from_limiter
def get_comments(post_id):
    """Get comments for a post."""
    post = Post.query.get_or_404(post_id)
    
    # Get top-level comments only (oldest first, newest at bottom)
    comments = Comment.query.filter_by(
        post_id=post_id, parent_id=None, is_approved=True
    ).order_by(Comment.created_at.asc()).all()
    
    def serialize_comment(comment):
        replies = Comment.query.filter_by(parent_id=comment.id, is_approved=True).order_by(Comment.created_at.asc()).all()
        is_edited = comment.updated_at and comment.created_at and comment.updated_at > comment.created_at
        author = comment.author
        author_is_deleted = bool(getattr(author, 'is_deleted', False))
        return {
            'id': comment.id,
            'content': comment.content,
            'author': {
                'id': author.id,
                'is_deleted': author_is_deleted,
                'username': None if author_is_deleted else author.username,
                'display_name': None if author_is_deleted else author.display_name,
                'avatar_url': None if author_is_deleted else author.avatar_url,
                'theme_color': '#6b7280' if author_is_deleted else author.theme_color
            },
            'created_at': format_datetime_i18n(comment.created_at),
            'is_edited': is_edited,
            'replies': [serialize_comment(r) for r in replies]
        }
    
    return jsonify({
        'comments': [serialize_comment(c) for c in comments],
        'total': Comment.query.filter_by(post_id=post_id, is_approved=True).count()
    })


@social_bp.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@optional_limit("20 per minute")
@login_required
def add_comment(post_id):
    """Add a comment to a post."""
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')
    
    if not content:
        return jsonify({'error': 'Kommentar darf nicht leer sein'}), 400
    
    if len(content) > 2000:
        return jsonify({'error': 'Kommentar ist zu lang (max. 2000 Zeichen)'}), 400

    if parent_id:
        parent = Comment.query.filter_by(id=parent_id, post_id=post_id, is_approved=True).first()
        if not parent:
            return jsonify({'error': 'Antwort-Kommentar nicht gefunden'}), 400

        # Enforce max nesting depth (top-level=0, reply=1, ...). Allow depth up to 3.
        depth = 0
        current = parent
        # Walk up the chain (guard against cycles)
        while current and current.parent_id:
            depth += 1
            if depth >= 50:
                break
            current = current.parent
        # parent depth == depth; new reply depth == parent depth + 1
        if depth >= 3:
            return jsonify({'error': 'Maximale Verschachtelungstiefe erreicht (3)'}), 400
    
    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        parent_id=parent_id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()
    
    # Create notification for post owner
    if post.user_id != current_user.id:
        create_notification(
            user_id=post.user_id,
            type='comment',
            title=_('{name} commented on your post').format(name=(current_user.display_name or current_user.username)),
            message=content[:100] + ('...' if len(content) > 100 else ''),
            link=f'/post/{post.public_id}',
            actor_id=current_user.id,
            post_id=post_id,
            comment_id=comment.id
        )
    
    # If replying to a comment, notify the parent comment author
    if parent_id:
        parent_comment = Comment.query.get(parent_id)
        if parent_comment and parent_comment.user_id != current_user.id:
            create_notification(
                user_id=parent_comment.user_id,
                type='comment',
                title=_('{name} replied to your comment').format(name=(current_user.display_name or current_user.username)),
                message=content[:100] + ('...' if len(content) > 100 else ''),
                link=f'/post/{post.public_id}',
                actor_id=current_user.id,
                post_id=post_id,
                comment_id=comment.id
            )

    mentioned_usernames = extract_mentions(content)
    if mentioned_usernames:
        mentioned_users = User.query.filter(User.username.in_(mentioned_usernames)).all()
        for u in mentioned_users:
            create_notification(
                user_id=u.id,
                type='mention',
                title=_('{name} mentioned you in a comment').format(name=(current_user.display_name or current_user.username)),
                message=content[:100] + ('...' if len(content) > 100 else ''),
                link=f'/post/{post.public_id}',
                actor_id=current_user.id,
                post_id=post.id,
                comment_id=comment.id
            )
    
    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author': {
                'id': current_user.id,
                'username': current_user.username,
                'display_name': current_user.display_name,
                'avatar_url': current_user.avatar_url,
                'theme_color': current_user.theme_color
            },
            'parent_id': comment.parent_id,
            'created_at': format_datetime_i18n(comment.created_at)
        }
    })


@social_bp.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (only by author or post owner)."""
    comment = Comment.query.get_or_404(comment_id)
    post = comment.post
    
    if comment.user_id != current_user.id and post.user_id != current_user.id:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    def delete_comment_tree(root_comment):
        replies = Comment.query.filter_by(parent_id=root_comment.id).all()
        for r in replies:
            delete_comment_tree(r)
        db.session.delete(root_comment)

    delete_comment_tree(comment)
    db.session.commit()
    return jsonify({'success': True})


@social_bp.route('/api/comments/<int:comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    """Edit a comment (only by author)."""
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Kommentar darf nicht leer sein'}), 400
    
    if len(content) > 2000:
        return jsonify({'error': 'Kommentar ist zu lang (max. 2000 Zeichen)'}), 400
    
    comment.content = content
    comment.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'updated_at': format_datetime_i18n(comment.updated_at)
        }
    })


# ============== Tags ==============

@social_bp.route('/me/tags')
@login_required
def manage_tags():
    """Manage user's tags."""
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    return render_template('me/tags.html', tags=tags)


@social_bp.route('/me/tags/create', methods=['POST'])
@login_required
def create_tag():
    """Create a new tag."""
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#4da9a4')
    want_json = request.args.get('format') == 'json' or request.headers.get('Accept', '').find('application/json') != -1
    
    if not name:
        if want_json:
            return jsonify({'success': False, 'error': 'Tag-Name ist erforderlich.'})
        flash(_('Tag name is required.'), 'error')
        return redirect(url_for('social.manage_tags'))
    
    slug = slugify(name)
    
    existing = Tag.query.filter_by(user_id=current_user.id, slug=slug).first()
    if existing:
        if want_json:
            return jsonify({'success': False, 'error': 'Ein Tag mit diesem Namen existiert bereits.'})
        flash(_('A tag with this name already exists.'), 'error')
        return redirect(url_for('social.manage_tags'))
    
    tag = Tag(user_id=current_user.id, name=name, slug=slug, color=color)
    db.session.add(tag)
    db.session.commit()
    
    # Return JSON for AJAX requests
    if want_json:
        return jsonify({
            'success': True,
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'slug': tag.slug,
                'color': tag.color
            }
        })
    
    flash(_('Tag created.'), 'success')
    return redirect(url_for('social.manage_tags'))


@social_bp.route('/me/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    """Delete a tag."""
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
    db.session.delete(tag)
    db.session.commit()
    flash(_('Tag deleted.'), 'success')
    return redirect(url_for('social.manage_tags'))


@social_bp.route('/me/tag/<slug>')
@login_required
def view_tag(slug):
    """View posts with a specific tag."""
    tag = Tag.query.filter_by(user_id=current_user.id, slug=slug).first_or_404()
    posts = tag.posts
    return render_template('me/tag_posts.html', tag=tag, posts=posts)


# ============== Search ==============

@social_bp.route('/me/search')
@login_required
def search():
    """Search posts."""
    query = request.args.get('q', '').strip()
    tag_filter = request.args.get('tag', '')
    page_filter = request.args.get('page_id', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    posts_query = Post.query.filter_by(user_id=current_user.id, is_published=True)
    
    # Text search
    if query:
        search_term = f'%{query}%'
        posts_query = posts_query.filter(
            db.or_(
                Post.title.ilike(search_term),
                Post.content.ilike(search_term)
            )
        )
    
    # Tag filter
    if tag_filter:
        tag = Tag.query.filter_by(user_id=current_user.id, slug=tag_filter).first()
        if tag:
            posts_query = posts_query.filter(Post.tags.contains(tag))
    
    # Page filter
    if page_filter:
        posts_query = posts_query.filter(Post.page_id == page_filter)
    
    # Date filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            posts_query = posts_query.filter(Post.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            posts_query = posts_query.filter(Post.created_at <= to_date)
        except ValueError:
            pass
    
    posts = posts_query.order_by(Post.created_at.desc()).limit(50).all()
    
    # Get all tags and pages for filters
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    pages = Page.query.filter_by(user_id=current_user.id, is_visible=True).order_by(Page.order).all()
    
    return render_template('me/search.html', 
                           posts=posts, 
                           query=query, 
                           tags=tags, 
                           pages=pages,
                           selected_tag=tag_filter,
                           selected_page=page_filter,
                           date_from=date_from,
                           date_to=date_to)


# ============== Archive ==============

def _archive_posts_query():
    user_group_ids = [m.group_id for m in GroupMembership.query.filter_by(user_id=current_user.id).all()]
    posts_query = Post.query.filter(
        db.or_(
            Post.user_id == current_user.id,
            db.and_(
                Post.is_published == True,
                Post.group_id.in_(user_group_ids) if user_group_ids else False
            )
        )
    )
    return posts_query.order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc())

@social_bp.route('/me/archive')
@login_required
def archive():
    """Show archive overview."""
    # Get posts grouped by year and month
    posts = _archive_posts_query().all()
     
    archive_data = {}
    for post in posts:
        archive_dt = post.scheduled_at or post.created_at
        year = archive_dt.year
        month = archive_dt.month
        
        if year not in archive_data:
            archive_data[year] = {}
        if month not in archive_data[year]:
            archive_data[year][month] = []
        archive_data[year][month].append(post)
    
    return render_template('me/archive.html', archive_data=archive_data)


@social_bp.route('/me/archive/<int:year>')
@login_required
def archive_year(year):
    """Show posts from a specific year."""
    posts = _archive_posts_query().filter(
        extract('year', db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at)) == year
    ).order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc()).all()
     
    return render_template('me/archive_year.html', year=year, posts=posts)


@social_bp.route('/me/archive/<int:year>/<int:month>')
@login_required
def archive_month(year, month):
    """Show posts from a specific month."""
    posts = _archive_posts_query().filter(
        extract('year', db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at)) == year,
        extract('month', db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at)) == month
    ).order_by(db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc()).all()
     
    month_names = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 
                   'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    
    return render_template('me/archive_month.html', 
                           year=year, 
                           month=month, 
                           month_name=month_names[month],
                           posts=posts)


# ============== Notifications ==============

@social_bp.route('/api/notifications')
@exempt_from_limiter
@login_required
def get_notifications():
    """Get notifications for the current user."""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(20).all()
    
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            'actor': {
                'username': n.actor.username if n.actor else None,
                'display_name': n.actor.display_name if n.actor else None,
                'avatar_url': n.actor.avatar_url if n.actor else None
            } if n.actor else None
        } for n in notifications],
        'unread_count': unread_count
    })


@social_bp.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@social_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a single notification as read."""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@social_bp.route('/api/push/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    if not current_app.config.get("VAPID_PUBLIC_KEY") or not current_app.config.get("VAPID_PRIVATE_KEY"):
        return jsonify({'error': 'Push not configured'}), 400
    payload = request.get_json(silent=True) or {}
    subscription = payload.get('subscription') or {}
    endpoint = subscription.get('endpoint')
    keys = subscription.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth_key = keys.get('auth')
    if not endpoint or not p256dh or not auth_key:
        return jsonify({'error': 'Invalid subscription'}), 400
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth_key
    else:
        db.session.add(PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth_key
        ))
    db.session.commit()
    return jsonify({'success': True})


@social_bp.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def unsubscribe_push():
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get('endpoint')
    if not endpoint:
        return jsonify({'error': 'Endpoint required'}), 400
    subscription = PushSubscription.query.filter_by(user_id=current_user.id, endpoint=endpoint).first()
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
    return jsonify({'success': True})


def create_notification(user_id, type, title, message=None, link=None, actor_id=None, post_id=None, comment_id=None):
    """Helper function to create a notification."""
    # Don't notify yourself
    if actor_id and actor_id == user_id:
        return None
    
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
        actor_id=actor_id,
        post_id=post_id,
        comment_id=comment_id
    )
    db.session.add(notification)
    db.session.commit()
    try:
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        send_push_notification(
            user_id,
            {
                "title": title,
                "message": message,
                "type": type,
                "link": link,
                "unread_count": unread_count,
            },
        )
    except Exception:
        current_app.logger.exception("Error sending push notification")
    return notification


# ============== Follows ==============

@social_bp.route('/api/users/<int:user_id>/follow', methods=['POST'])
@optional_limit("30 per minute")
@login_required
def follow_user(user_id):
    """Follow a user."""
    if user_id == current_user.id:
        return jsonify({'error': 'Du kannst dir nicht selbst folgen'}), 400
    
    user = User.query.get_or_404(user_id)
    existing = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()
    
    if existing:
        return jsonify({'error': 'Du folgst diesem Benutzer bereits'}), 400
    
    follow = Follow(follower_id=current_user.id, followed_id=user_id)
    db.session.add(follow)
    db.session.commit()
    
    # Create notification
    create_notification(
        user_id=user_id,
        type='follow',
        title=_('{name} is now following you').format(name=(current_user.display_name or current_user.username)),
        link=url_for('blog.public_profile', username=current_user.username),
        actor_id=current_user.id
    )
    
    return jsonify({'success': True, 'following': True})


@social_bp.route('/api/users/<int:user_id>/unfollow', methods=['POST'])
@login_required
def unfollow_user(user_id):
    """Unfollow a user."""
    follow = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first()
    
    if not follow:
        return jsonify({'error': 'Du folgst diesem Benutzer nicht'}), 400
    
    db.session.delete(follow)
    db.session.commit()
    
    return jsonify({'success': True, 'following': False})


@social_bp.route('/api/users/<int:user_id>/is-following')
@login_required
def is_following(user_id):
    """Check if current user is following a user."""
    following = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first() is not None
    return jsonify({'following': following})


# ============== User Search (for @mentions) ==============

@social_bp.route('/api/users/search')
def search_users():
    """Search users for @mention autocomplete."""
    query = request.args.get('q', '').strip()
    
    if len(query) < 1:
        return jsonify({'users': []})
    
    users = User.query.filter(
        User.is_deleted.is_(False),
        User.is_active.is_(True),
        db.or_(
            User.username.ilike(f'%{query}%'),
            User.display_name.ilike(f'%{query}%')
        )
    ).limit(5).all()
    
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'display_name': u.display_name,
            'avatar_url': u.avatar_url,
            'theme_color': u.theme_color
        } for u in users]
    })


@social_bp.route('/api/tags/search')
def search_tags():
    query = request.args.get('q', '').strip()

    if len(query) < 1:
        return jsonify({'tags': []})

    tags = Tag.query.filter(
        db.or_(
            Tag.name.ilike(f'%{query}%'),
            Tag.slug.ilike(f'%{query}%')
        )
    ).order_by(Tag.name.asc()).limit(5).all()

    return jsonify({
        'tags': [{
            'id': t.id,
            'name': t.name,
            'slug': t.slug,
            'color': t.color
        } for t in tags]
    })


# ============== Polls ==============

@social_bp.route('/api/polls/<int:poll_id>')
def get_poll(poll_id):
    """Get poll data with vote counts."""
    poll = Poll.query.get_or_404(poll_id)
    
    # Check if user has voted
    user_votes = []
    if current_user.is_authenticated:
        user_votes = [v.option_id for v in PollVote.query.filter_by(user_id=current_user.id).join(PollOption).filter(PollOption.poll_id == poll_id).all()]
    else:
        session_id = request.cookies.get('session_id')
        if session_id:
            user_votes = [v.option_id for v in PollVote.query.filter_by(session_id=session_id).join(PollOption).filter(PollOption.poll_id == poll_id).all()]
    
    total_votes = sum(opt.votes.count() for opt in poll.options)
    
    is_ended = poll.ends_at < datetime.utcnow() if poll.ends_at else False
    
    return jsonify({
        'id': poll.id,
        'question': poll.question,
        'allows_multiple': poll.allows_multiple,
        'ends_at': poll.ends_at.isoformat() if poll.ends_at else None,
        'is_ended': is_ended,
        'total_votes': total_votes,
        'user_votes': user_votes,
        'options': [{
            'id': opt.id,
            'text': opt.text,
            'votes': opt.votes.count(),
            'percentage': round((opt.votes.count() / total_votes * 100) if total_votes > 0 else 0, 1)
        } for opt in poll.options.order_by(PollOption.order)]
    })


@social_bp.route('/api/polls/<int:poll_id>/vote', methods=['POST'])
def vote_poll(poll_id):
    """Vote on a poll option."""
    poll = Poll.query.get_or_404(poll_id)
    data = request.get_json()
    option_ids = data.get('option_ids', [])
    
    if not option_ids:
        return jsonify({'error': 'Keine Option ausgewählt'}), 400
    
    if not poll.allows_multiple and len(option_ids) > 1:
        return jsonify({'error': 'Nur eine Option erlaubt'}), 400
    
    # Check if poll has ended
    if poll.ends_at and poll.ends_at < datetime.utcnow():
        return jsonify({'error': 'Umfrage ist beendet'}), 400
    
    # Get or create session ID for anonymous users
    session_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
        # Remove existing votes
        existing = PollVote.query.filter_by(user_id=user_id).join(PollOption).filter(PollOption.poll_id == poll_id).all()
        for v in existing:
            db.session.delete(v)
    else:
        user_id = None
        session_id = request.cookies.get('session_id') or str(uuid.uuid4())
        # Remove existing votes
        existing = PollVote.query.filter_by(session_id=session_id).join(PollOption).filter(PollOption.poll_id == poll_id).all()
        for v in existing:
            db.session.delete(v)
    
    # Add new votes
    is_new_vote = len(existing) == 0  # Track if this is a new vote (not a change)
    for opt_id in option_ids:
        option = PollOption.query.filter_by(id=opt_id, poll_id=poll_id).first()
        if option:
            vote = PollVote(option_id=opt_id, user_id=user_id, session_id=session_id)
            db.session.add(vote)
    
    db.session.commit()
    
    # Send notification to post owner (only for new votes from authenticated users)
    if is_new_vote and user_id and poll.post.user_id != user_id:
        notification = Notification(
            user_id=poll.post.user_id,
            type='poll_vote',
            title=_('New vote'),
            message=_('{name} voted in your poll').format(name=(current_user.display_name or current_user.username)),
            link=f'/post/{poll.post.public_id}',
            actor_id=user_id,
            post_id=poll.post.id
        )
        db.session.add(notification)
        db.session.commit()
    
    response = jsonify({'success': True})
    if session_id and not request.cookies.get('session_id'):
        response.set_cookie('session_id', session_id, max_age=365*24*60*60)
    
    return response


# ============== Trending Tags ==============

@social_bp.route('/api/tags/trending')
@login_required
def trending_tags():
    """Return trending tags, falling back to all-time popular tags if needed."""
    from models import post_tags
    
    def query_tags(count_only_recent: bool):
        now = datetime.utcnow()
        base_query = db.session.query(
            Tag.id, Tag.name, Tag.slug, Tag.color,
            db.func.count(post_tags.c.post_id).label('post_count')
        ).join(post_tags).join(Post).filter(
            Post.is_published == True,
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= now
            ),
            group_visibility_filter
        )
        if count_only_recent:
            week_ago = now - timedelta(days=7)
            base_query = base_query.filter(Post.created_at >= week_ago)
        return base_query.group_by(Tag.id).all()
    
    def aggregate(rows):
        aggregated = {}
        for tag in rows:
            normalized = (tag.slug or tag.name or '').strip().lower()
            if not normalized:
                continue
            entry = aggregated.setdefault(normalized, {
                'name': tag.name,
                'slug': tag.slug or slugify(tag.name or ''),
                'color': tag.color,
                'post_count': 0,
                '_top_count': 0,
            })
            entry['post_count'] += tag.post_count
            if tag.post_count > entry['_top_count']:
                entry['_top_count'] = tag.post_count
                entry['color'] = tag.color
        return aggregated
    
    user_group_ids = get_user_group_ids(current_user.id)
    group_visibility_filter = db.or_(
        Post.group_id.is_(None),
        Post.group_id.in_(user_group_ids) if user_group_ids else False
    )
    
    aggregated = aggregate(query_tags(count_only_recent=True))
    if not aggregated:
        aggregated = aggregate(query_tags(count_only_recent=False))
    
    top_tags = sorted(aggregated.values(), key=lambda t: t['post_count'], reverse=True)[:7]
    for tag in top_tags:
        tag.pop('_top_count', None)
    
    return jsonify({
        'tags': [{
            'name': t['name'],
            'slug': t['slug'],
            'color': t['color'],
            'post_count': t['post_count']
        } for t in top_tags]
    })


# ============== Post Version History ==============

@social_bp.route('/api/posts/<int:post_id>/versions')
@login_required
def get_post_versions(post_id):
    """Get version history for a post."""
    post = Post.query.get_or_404(post_id)
    
    # Only post owner can view versions
    if post.user_id != current_user.id:
        return jsonify({'error': 'Nicht berechtigt'}), 403
    
    versions = PostVersion.query.filter_by(post_id=post_id).order_by(PostVersion.version_number.desc()).all()
    
    return jsonify({
        'versions': [{
            'id': v.id,
            'version_number': v.version_number,
            'title': v.title,
            'content': v.content,
            'edited_by': v.editor.username if v.editor else None,
            'created_at': v.created_at.strftime('%d.%m.%Y %H:%M')
        } for v in versions]
    })


@social_bp.route('/api/posts/<int:post_id>/versions/<int:version_id>')
@login_required
def get_post_version(post_id, version_id):
    """Get a specific version of a post."""
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Nicht berechtigt'}), 403
    
    version = PostVersion.query.filter_by(id=version_id, post_id=post_id).first_or_404()
    
    return jsonify({
        'id': version.id,
        'version_number': version.version_number,
        'title': version.title,
        'content': version.content,
        'edited_by': version.editor.username if version.editor else None,
        'created_at': version.created_at.strftime('%d.%m.%Y %H:%M')
    })


@social_bp.route('/api/posts/<int:post_id>/versions/<int:version_id>/restore', methods=['POST'])
@login_required
def restore_post_version(post_id, version_id):
    """Restore a post to a previous version."""
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Nicht berechtigt'}), 403
    
    version = PostVersion.query.filter_by(id=version_id, post_id=post_id).first_or_404()
    
    # Save current state as new version before restoring
    current_version_num = PostVersion.query.filter_by(post_id=post_id).count() + 1
    current_version = PostVersion(
        post_id=post_id,
        version_number=current_version_num,
        title=post.title,
        content=post.content,
        edited_by=current_user.id
    )
    db.session.add(current_version)
    
    # Restore old version
    post.title = version.title
    post.content = version.content
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Version {version.version_number} wiederhergestellt'})


# ============== Groups ==============

@social_bp.route('/groups')
@login_required
def groups_list():
    """List all groups the user is a member of."""
    memberships = GroupMembership.query.filter_by(user_id=current_user.id).all()
    groups = [m.group for m in memberships]
    return render_template('groups/list.html', groups=groups)


@social_bp.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    """Create a new group."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#6366f1')
        
        if not name:
            flash(_('Group name is required.'), 'error')
            return redirect(url_for('social.create_group'))
        
        slug = slugify(name)
        base_slug = slug
        counter = 1
        while Group.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        group = Group(
            name=name,
            slug=slug,
            description=description,
            color=color,
            created_by=current_user.id
        )
        db.session.add(group)
        db.session.commit()
        
        # Creator automatically becomes admin member
        membership = GroupMembership(
            group_id=group.id,
            user_id=current_user.id,
            role='admin'
        )
        db.session.add(membership)
        db.session.commit()
        
        flash(_('Group "{name}" created.').format(name=name), 'success')
        return redirect(url_for('social.group_detail', slug=group.slug))
    
    return render_template('groups/create.html')


@social_bp.route('/groups/<slug>')
@login_required
def group_detail(slug):
    """View a group and its posts."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    
    # Check membership
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not membership:
        flash(_('You are not a member of this group.'), 'error')
        return redirect(url_for('social.groups_list'))
    
    # Get group announcements (newest first)
    announcements = GroupAnnouncement.query.filter_by(group_id=group.id).order_by(
        GroupAnnouncement.created_at.desc()
    ).all()
    
    # Get posts ordered by scheduled publish time (fallback created_at) descending
    # For admins: show all posts (including unpublished)
    # For regular members: show published posts + own unpublished posts
    if membership.role == 'admin':
        posts = Post.query.filter_by(group_id=group.id)
    else:
        posts = Post.query.filter_by(group_id=group.id).filter(
            db.or_(
                Post.is_published == True,
                Post.user_id == current_user.id,
            )
        )
        # Also hide scheduled posts that haven't reached their publish time yet
        posts = posts.filter(
            db.or_(
                Post.scheduled_at.is_(None),
                Post.scheduled_at <= db.func.now(),
                Post.user_id == current_user.id,
            )
        )

    posts = posts.order_by(
        db.func.coalesce(Post.scheduled_at, Post.published_at, Post.created_at).desc()
    ).all()
    members = GroupMembership.query.filter_by(group_id=group.id).all()
    is_admin = membership.role == 'admin'
    
    return render_template('groups/detail.html', group=group, posts=posts, members=members, is_admin=is_admin, announcements=announcements, now=datetime.utcnow())


@social_bp.route('/groups/<slug>/settings', methods=['GET', 'POST'])
@login_required
def group_settings(slug):
    """Edit group settings (admin only)."""
    from blog import allowed_file, resize_image, get_upload_folder
    import os
    
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        flash(_('Only admins can edit group settings.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))
    
    if request.method == 'POST':
        group.name = request.form.get('name', group.name).strip()
        group.description = request.form.get('description', '').strip()
        group.color = request.form.get('color', group.color)
        
        # Handle cover image upload
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename and allowed_file(file.filename):
                filename = f"group_cover_{group.id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(get_upload_folder('groups', str(group.id)), filename)
                img = resize_image(file, max_size=1920)
                img.save(filepath, 'JPEG', quality=85)
                group.cover_image_url = url_for('static', filename=f'uploads/groups/{group.id}/{filename}')
        
        # Handle cover image removal
        if request.form.get('remove_cover') == '1':
            group.cover_image_url = None
        
        # Handle icon/avatar upload
        if 'icon_image' in request.files:
            file = request.files['icon_image']
            if file and file.filename and allowed_file(file.filename):
                filename = f"group_icon_{group.id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(get_upload_folder('groups', str(group.id)), filename)
                img = resize_image(file, max_size=256)
                img.save(filepath, 'JPEG', quality=90)
                group.icon_url = url_for('static', filename=f'uploads/groups/{group.id}/{filename}')
        
        # Handle icon removal
        if request.form.get('remove_icon') == '1':
            group.icon_url = None
        
        db.session.commit()
        flash(_('Group settings saved.'), 'success')
        return redirect(url_for('social.group_detail', slug=slug))
    
    return render_template('groups/settings.html', group=group)


@social_bp.route('/groups/<slug>/delete', methods=['POST'])
@login_required
def delete_group(slug):
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()

    if not membership or membership.role != 'admin':
        flash(_('Only admins can delete groups.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))

    confirm_name = (request.form.get('confirm_group_name') or '').strip()
    if confirm_name != group.name:
        flash(_('Group name does not match. Group was not deleted.'), 'error')
        return redirect(url_for('social.group_settings', slug=slug))

    _delete_group_and_related(group)

    flash(_('Group "{name}" was deleted.').format(name=group.name), 'success')
    return redirect(url_for('social.groups_list'))


@social_bp.route('/groups/<slug>/invite', methods=['POST'])
@login_required
def invite_to_group(slug):
    """Invite a user to a group."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Nur Admins können Mitglieder einladen.'}), 403
    
    username = request.form.get('username', '').strip()
    user = User.query.filter_by(username=username).first()
    
    if not user or getattr(user, 'is_deleted', False) or not getattr(user, 'is_active', True):
        flash(_('User not found.'), 'error')
        return redirect(url_for('social.group_settings', slug=slug))
    
    existing = GroupMembership.query.filter_by(group_id=group.id, user_id=user.id).first()
    if existing:
        flash(_('User is already a member.'), 'error')
        return redirect(url_for('social.group_settings', slug=slug))
    
    new_membership = GroupMembership(group_id=group.id, user_id=user.id, role='member')
    db.session.add(new_membership)
    db.session.commit()
    
    # Notify the invited user
    create_notification(
        user_id=user.id,
        type='group_invite',
        title=_('{name} added you to the group "{group}"').format(name=(current_user.display_name or current_user.username), group=group.name),
        link=f'/groups/{group.slug}',
        actor_id=current_user.id
    )
    
    flash(_('{user} was added to the group.').format(user=(user.display_name or user.username)), 'success')
    return redirect(url_for('social.group_settings', slug=slug))


@social_bp.route('/groups/<slug>/invite-all', methods=['POST'])
@login_required
def invite_all_to_group(slug):
    """Invite all portal users to a group (admin only)."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        flash(_('Only admins can invite all users.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))
    
    # Get all users who are not already members
    existing_member_ids = [m.user_id for m in GroupMembership.query.filter_by(group_id=group.id).all()]
    users_to_invite = User.query.filter(
        User.is_deleted.is_(False),
        User.is_active.is_(True),
        ~User.id.in_(existing_member_ids)
    ).all()
    
    added_count = 0
    for user in users_to_invite:
        new_membership = GroupMembership(group_id=group.id, user_id=user.id, role='member')
        db.session.add(new_membership)
        
        # Notify each invited user
        create_notification(
            user_id=user.id,
            type='group_invite',
            title=_('{name} added you to the group "{group}"').format(name=(current_user.display_name or current_user.username), group=group.name),
            link=f'/groups/{group.slug}',
            actor_id=current_user.id
        )
        added_count += 1
    
    db.session.commit()
    flash(_('{n} users were added to the group.').format(n=added_count), 'success')
    return redirect(url_for('social.group_settings', slug=slug))


@social_bp.route('/groups/<slug>/leave', methods=['POST'])
@login_required
def leave_group(slug):
    """Leave a group."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership:
        flash(_('You are not a member of this group.'), 'error')
        return redirect(url_for('social.groups_list'))

    member_count = GroupMembership.query.filter_by(group_id=group.id).count()
    is_last_member = member_count == 1

    if is_last_member:
        confirm_name = (request.form.get('confirm_group_name') or '').strip()
        if confirm_name != group.name:
            flash(_('Group name does not match. Group was not deleted.'), 'error')
            return redirect(url_for('social.group_detail', slug=slug))
    
    # Check if user is the only admin
    if membership.role == 'admin':
        admin_count = GroupMembership.query.filter_by(group_id=group.id, role='admin').count()
        if admin_count == 1 and member_count > 1:
            new_admin_id_raw = (request.form.get('new_admin_id') or '').strip()
            if not new_admin_id_raw:
                flash(_('You are the only admin. Transfer the admin role before leaving the group.'), 'error')
                return redirect(url_for('social.group_detail', slug=slug))

            try:
                new_admin_id = int(new_admin_id_raw)
            except Exception:
                flash(_('You are the only admin. Transfer the admin role before leaving the group.'), 'error')
                return redirect(url_for('social.group_detail', slug=slug))

            if new_admin_id == current_user.id:
                flash(_('You are the only admin. Transfer the admin role before leaving the group.'), 'error')
                return redirect(url_for('social.group_detail', slug=slug))

            new_admin_membership = GroupMembership.query.filter_by(group_id=group.id, user_id=new_admin_id).first()
            if not new_admin_membership:
                flash(_('You are the only admin. Transfer the admin role before leaving the group.'), 'error')
                return redirect(url_for('social.group_detail', slug=slug))

            new_admin_membership.role = 'admin'
            db.session.commit()
    
    db.session.delete(membership)
    db.session.commit()

    remaining = GroupMembership.query.filter_by(group_id=group.id).count()
    if remaining == 0:
        _delete_group_and_related(group)
        flash(_('Group "{name}" was deleted.').format(name=group.name), 'success')
        return redirect(url_for('social.groups_list'))

    flash(_('You left the group "{name}".').format(name=group.name), 'success')
    return redirect(url_for('social.groups_list'))


@social_bp.route('/groups/<slug>/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_from_group(slug, user_id):
    """Remove a user from a group (admin only)."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    admin_membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not admin_membership or admin_membership.role != 'admin':
        flash(_('Only admins can remove members.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))
    
    if user_id == current_user.id:
        flash(_('You cannot remove yourself.'), 'error')
        return redirect(url_for('social.group_settings', slug=slug))
    
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=user_id).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()
        flash(_('Member removed.'), 'success')

    remaining = GroupMembership.query.filter_by(group_id=group.id).count()
    if remaining == 0:
        _delete_group_and_related(group)
        flash(_('Group "{name}" was deleted.').format(name=group.name), 'success')
        return redirect(url_for('social.groups_list'))
    
    return redirect(url_for('social.group_settings', slug=slug))


@social_bp.route('/groups/<slug>/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin_role(slug, user_id):
    """Toggle admin role for a member (admin only)."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    admin_membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not admin_membership or admin_membership.role != 'admin':
        flash(_('Only admins can change roles.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))
    
    if user_id == current_user.id:
        flash(_('You cannot change your own role.'), 'error')
        return redirect(url_for('social.group_settings', slug=slug))
    
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=user_id).first()
    if membership:
        if membership.role == 'admin':
            membership.role = 'member'
            flash(_('{user} is now a regular member.').format(user=(membership.user.display_name or membership.user.username)), 'success')
        else:
            membership.role = 'admin'
            flash(_('{user} is now an admin.').format(user=(membership.user.display_name or membership.user.username)), 'success')
        db.session.commit()
    
    return redirect(url_for('social.group_settings', slug=slug))


@social_bp.route('/api/groups/search')
@login_required
def search_groups():
    """Search groups the user is a member of."""
    query = request.args.get('q', '').strip()
    
    if len(query) < 1:
        return jsonify({'groups': []})
    
    user_group_ids = [m.group_id for m in GroupMembership.query.filter_by(user_id=current_user.id).all()]
    
    groups = Group.query.filter(
        Group.id.in_(user_group_ids),
        db.or_(
            Group.name.ilike(f'%{query}%'),
            Group.slug.ilike(f'%{query}%')
        )
    ).limit(5).all()
    
    return jsonify({
        'groups': [{
            'id': g.id,
            'name': g.name,
            'slug': g.slug,
            'color': g.color
        } for g in groups]
    })


@social_bp.route('/api/groups/my')
@login_required
def my_groups():
    """Get all groups the current user is a member of."""
    memberships = GroupMembership.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'groups': [{
            'id': m.group.id,
            'name': m.group.name,
            'slug': m.group.slug,
            'color': m.group.color,
            'role': m.role,
            'post_count': Post.query.filter_by(group_id=m.group.id, is_published=True).count()
        } for m in memberships]
    })


# ============== Group Files ==============

ALLOWED_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv',
                           'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'zip', 'rar', '7z'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS


@social_bp.route('/groups/<slug>/files')
@login_required
def group_files(slug):
    """View group files library."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not membership:
        flash(_('You are not a member of this group.'), 'error')
        return redirect(url_for('social.groups_list'))
    
    is_admin = membership.role == 'admin'
    files = GroupFile.query.filter_by(group_id=group.id).order_by(GroupFile.created_at.desc()).all()
    
    return render_template('groups/files.html',
                          group=group,
                          files=files,
                          is_admin=is_admin,
                          allowed_extensions=ALLOWED_FILE_EXTENSIONS)


@social_bp.route('/groups/<slug>/files/upload', methods=['POST'])
@login_required
def upload_group_file(slug):
    """Upload a file to a group."""
    from flask import current_app
    from blog import get_upload_folder
    
    group = Group.query.filter_by(slug=slug).first_or_404()
    
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not membership:
        flash(_('You are not a member of this group.'), 'error')
        return redirect(url_for('social.groups_list'))
    
    if 'file' not in request.files:
        flash(_('No file selected.'), 'error')
        return redirect(url_for('social.group_files', slug=slug))
    
    file = request.files['file']
    
    if file.filename == '':
        flash(_('No file selected.'), 'error')
        return redirect(url_for('social.group_files', slug=slug))
    
    if not allowed_file(file.filename):
        flash(_('File type not allowed. Allowed types: {types}').format(types=", ".join(sorted(ALLOWED_FILE_EXTENSIONS))), 'error')
        return redirect(url_for('social.group_files', slug=slug))
    
    # Check file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        flash(_('File is too large. Maximum size: 50MB'), 'error')
        return redirect(url_for('social.group_files', slug=slug))
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}" if ext else f"{uuid.uuid4().hex}"
    
    # Create group files directory
    upload_dir = get_upload_folder('groups', str(group.id))
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)
    
    # Get file MIME type
    import mimetypes
    file_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
    
    # Create database entry
    group_file = GroupFile(
        group_id=group.id,
        uploaded_by=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=f"uploads/groups/{group.id}/{unique_filename}",
        file_type=file_type,
        file_size=file_size,
        description=request.form.get('description', '')
    )
    
    db.session.add(group_file)
    db.session.commit()
    
    flash(_('File "{name}" uploaded successfully.').format(name=file.filename), 'success')
    return redirect(url_for('social.group_files', slug=slug))


@social_bp.route('/groups/<slug>/files/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_group_file(slug, file_id):
    """Delete a file from a group (uploader or admin only)."""
    from flask import current_app
    
    group = Group.query.filter_by(slug=slug).first_or_404()
    group_file = GroupFile.query.filter_by(id=file_id, group_id=group.id).first_or_404()
    
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not membership:
        flash(_('You are not a member of this group.'), 'error')
        return redirect(url_for('social.groups_list'))
    
    # Check permission: only uploader or admin can delete
    is_admin = membership.role == 'admin'
    is_uploader = group_file.uploaded_by == current_user.id
    
    if not is_admin and not is_uploader:
        flash(_('You do not have permission to delete this file.'), 'error')
        return redirect(url_for('social.group_files', slug=slug))
    
    # Delete physical file
    file_path = os.path.join(current_app.root_path, 'static', group_file.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete database entry
    db.session.delete(group_file)
    db.session.commit()
    
    flash(_('File deleted.'), 'success')
    return redirect(url_for('social.group_files', slug=slug))


# ============== Group Announcements ==============

@social_bp.route('/groups/<slug>/announcements/new', methods=['GET', 'POST'])
@login_required
def create_group_announcement(slug):
    """Create a new group announcement (admin only)."""
    group = Group.query.filter_by(slug=slug).first_or_404()
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        flash(_('Only group admins can create announcements.'), 'error')
        return redirect(url_for('social.group_detail', slug=slug))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        border_color = request.form.get('border_color', '#f59e0b')
        
        if not content:
            flash(_('Please enter content.'), 'error')
            return render_template('groups/announcement_form.html', group=group, announcement=None)
        
        announcement = GroupAnnouncement(
            group_id=group.id,
            user_id=current_user.id,
            content=content,
            border_color=border_color
        )
        db.session.add(announcement)
        db.session.commit()
        
        flash(_('Announcement created.'), 'success')
        return redirect(url_for('social.group_detail', slug=slug))
    
    return render_template('groups/announcement_form.html', group=group, announcement=None)


@social_bp.route('/groups/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group_announcement(announcement_id):
    """Edit a group announcement (admin only)."""
    announcement = GroupAnnouncement.query.get_or_404(announcement_id)
    group = announcement.group
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        flash(_('Only group admins can edit announcements.'), 'error')
        return redirect(url_for('social.group_detail', slug=group.slug))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        border_color = request.form.get('border_color', '#f59e0b')
        
        if not content:
            flash(_('Please enter content.'), 'error')
            return render_template('groups/announcement_form.html', group=group, announcement=announcement)
        
        announcement.content = content
        announcement.border_color = border_color
        db.session.commit()
        
        flash(_('Announcement updated.'), 'success')
        return redirect(url_for('social.group_detail', slug=group.slug))
    
    return render_template('groups/announcement_form.html', group=group, announcement=announcement)


@social_bp.route('/groups/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_group_announcement(announcement_id):
    """Delete a group announcement (admin only)."""
    announcement = GroupAnnouncement.query.get_or_404(announcement_id)
    group = announcement.group
    membership = GroupMembership.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    
    if not membership or membership.role != 'admin':
        flash(_('Only group admins can delete announcements.'), 'error')
        return redirect(url_for('social.group_detail', slug=group.slug))
    
    db.session.delete(announcement)
    db.session.commit()
    
    flash(_('Announcement deleted.'), 'success')
    return redirect(url_for('social.group_detail', slug=group.slug))
