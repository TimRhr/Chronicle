import eventlet

eventlet.monkey_patch()

from app import create_app
from websocket import init_socketio
from socketio import WSGIApp

flask_app = create_app()

socketio = init_socketio(flask_app)

app = WSGIApp(socketio.server, flask_app)
