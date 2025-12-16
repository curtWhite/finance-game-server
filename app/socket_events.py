"""
Socket.IO event handlers for real-time communication
"""
from app import socketio
from flask_socketio import emit, join_room, leave_room
from flask import request


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to server', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')


@socketio.on('join_room')
def handle_join_room(data):
    """Allow clients to join a room for targeted messaging"""
    room = data.get('room')
    if room:
        join_room(room)
        emit('joined_room', {'room': room, 'message': f'Joined room: {room}'}, room=room)
        print(f'Client {request.sid} joined room: {room}')


@socketio.on('leave_room')
def handle_leave_room(data):
    """Allow clients to leave a room"""
    room = data.get('room')
    if room:
        leave_room(room)
        emit('left_room', {'room': room, 'message': f'Left room: {room}'})
        print(f'Client {request.sid} left room: {room}')


@socketio.on('message')
def handle_message(data):
    """Handle generic message event"""
    message = data.get('message', '')
    room = data.get('room')
    
    response = {
        'message': message,
        'from': request.sid,
        'timestamp': data.get('timestamp')
    }
    
    if room:
        # Send to specific room
        emit('message', response, room=room)
    else:
        # Broadcast to all connected clients
        emit('message', response, broadcast=True)


# Example: Game-specific events
@socketio.on('player_update')
def handle_player_update(data):
    """Handle player state updates"""
    username = data.get('username')
    room = f'player_{username}' if username else None
    
    if room:
        emit('player_update', data, room=room)
    else:
        emit('player_update', data, broadcast=True)


@socketio.on('game_event')
def handle_game_event(data):
    """Handle game-specific events"""
    event_type = data.get('type')
    room = data.get('room', 'game_lobby')
    
    emit('game_event', data, room=room)

