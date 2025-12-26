"""
WSGI entry point for Gunicorn
This file is used by Gunicorn to serve the Flask-SocketIO application

When using Gunicorn with gthread workers, SocketIO will use threading mode
for handling concurrent connections.
"""
from app import app

# This is the application object that Gunicorn will use
# Gunicorn with gthread workers will handle SocketIO properly
application = app

