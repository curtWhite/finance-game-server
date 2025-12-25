"""
WSGI entry point for Gunicorn
This file is used by Gunicorn to serve the Flask-SocketIO application

When using Gunicorn with eventlet workers, the monkey patching is handled
automatically by the worker class. The application object is what Gunicorn
will use to serve requests.
"""
from app import app, socketio

# This is the application object that Gunicorn will use
# Gunicorn with eventlet workers will handle SocketIO properly
application = app

