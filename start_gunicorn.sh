#!/bin/bash
# Script to start the application with Gunicorn
# Usage: ./start_gunicorn.sh

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start Gunicorn with the configuration file
gunicorn --config gunicorn_config.py wsgi:application

