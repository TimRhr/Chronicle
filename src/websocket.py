"""WebSocket support for real-time updates."""
import os
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user

socketio = SocketIO()


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    cors_env = (os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS') or '').strip()
    if cors_env:
        cors_allowed = '*' if cors_env == '*' else [o.strip() for o in cors_env.split(',') if o.strip()]
    else:
        cors_allowed = None

    # In development, don't use Redis message queue (local run)
    # Check for Windows (nt) specifically as user runs locally without Docker
    if os.getenv('FLASK_ENV') == 'development' or os.name == 'nt':
        message_queue = None
    else:
        message_queue = os.getenv('REDIS_URL') or None

    socketio.init_app(
        app,
        cors_allowed_origins=cors_allowed,
        message_queue=message_queue,
    )
    return socketio


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    if current_user.is_authenticated:
        emit('connected', {'user_id': current_user.id})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    pass


@socketio.on('join_post')
def handle_join_post(data):
    """Join a post room for real-time comment updates."""
    post_id = data.get('post_id')
    if post_id:
        join_room(f'post_{post_id}')
        emit('joined', {'post_id': post_id})


@socketio.on('leave_post')
def handle_leave_post(data):
    """Leave a post room."""
    post_id = data.get('post_id')
    if post_id:
        leave_room(f'post_{post_id}')


def emit_new_comment(post_id, comment_data):
    """Emit a new comment to all clients watching the post."""
    socketio.emit('new_comment', comment_data, room=f'post_{post_id}')


def emit_comment_deleted(post_id, comment_id):
    """Emit comment deletion to all clients watching the post."""
    socketio.emit('comment_deleted', {'comment_id': comment_id}, room=f'post_{post_id}')


def emit_reaction_update(post_id, reaction_data):
    """Emit reaction update to all clients watching the post."""
    socketio.emit('reaction_update', reaction_data, room=f'post_{post_id}')
