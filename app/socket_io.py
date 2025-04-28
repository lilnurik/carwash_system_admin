from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from datetime import datetime
from flask_socketio import SocketIO


from app import migrate, db
from config import Config

# Initialize SocketIO
socketio = SocketIO()


def init_app(app):
    """Initialize the Socket.IO extension with the app."""
    socketio.init_app(app,
                      cors_allowed_origins="*",
                      async_mode="threading")  # Changed from eventlet to threading

    # Register event handlers
    register_handlers()

    return socketio


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*")

    return app


def register_handlers():
    """Register Socket.IO event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        user = os.environ.get('CURRENT_USER', 'unknown')
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Socket.IO: Client connected - User: {user}, Time: {current_time}")
        emit('server_message', {
            'message': f'Connected to Carwash Management System',
            'timestamp': current_time
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        print("Socket.IO: Client disconnected")

    @socketio.on('join')
    def on_join(data):
        """Handle room joining."""
        username = data.get('username', 'anonymous')
        room = data.get('room', 'general')
        join_room(room)
        emit('server_message', {
            'message': f'{username} has joined the {room} room.',
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, to=room)

    @socketio.on('leave')
    def on_leave(data):
        """Handle room leaving."""
        username = data.get('username', 'anonymous')
        room = data.get('room', 'general')
        leave_room(room)
        emit('server_message', {
            'message': f'{username} has left the {room} room.',
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, to=room)

    @socketio.on('message')
    def handle_message(data):
        """Handle messages from clients."""
        print(f"Socket.IO: Received message: {data}")
        room = data.get('room', 'general')
        emit('message', {
            'user': data.get('username', 'anonymous'),
            'message': data.get('message', ''),
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, to=room)

    # Event for balance updates - this will broadcast to all clients or specific rooms
    @socketio.on('balance_update')
    def handle_balance_update(data):
        """Handle balance update events."""
        emit('balance_update', {
            'user_id': data.get('user_id'),
            'rfid_card_number': data.get('rfid_card_number'),
            'new_balance': data.get('new_balance'),
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)


# Function to broadcast balance updates from anywhere in the application
def broadcast_balance_update(user_id, rfid_card_number, new_balance):
    """Broadcast a balance update to all connected clients."""
    socketio.emit('balance_update', {
        'user_id': user_id,
        'rfid_card_number': rfid_card_number,
        'new_balance': new_balance,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }, broadcast=True)