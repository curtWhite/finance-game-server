@echo off
REM Script to start the application with Gunicorn on Windows
REM Usage: start_gunicorn.bat

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Start Gunicorn with the configuration file
gunicorn --config gunicorn_config.py wsgi:application

