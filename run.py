from app import app, socketio

if __name__ == '__main__':
    # Use socketio.run() instead of app.run() to enable Socket.IO
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)

