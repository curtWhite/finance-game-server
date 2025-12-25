# Gunicorn Deployment Guide

This guide explains how to deploy your Flask-SocketIO application using Gunicorn.

## Prerequisites

1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure you have a `.env` file with your environment variables (especially `MONGO_DB_CONNECTION_STRING`)

## Quick Start

### Using the Configuration File (Recommended)

**Linux/macOS:**
```bash
chmod +x start_gunicorn.sh
./start_gunicorn.sh
```

**Windows:**
```cmd
start_gunicorn.bat
```

### Manual Start

**Basic command:**
```bash
gunicorn --config gunicorn_config.py wsgi:application
```

**With custom settings:**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class eventlet wsgi:application
```

## Configuration

The `gunicorn_config.py` file contains all the configuration settings. You can customize it or override settings using environment variables:

- `GUNICORN_BIND`: Server bind address (default: `0.0.0.0:5000`)
- `GUNICORN_WORKERS`: Number of worker processes (default: CPU count * 2 + 1)
- `GUNICORN_ACCESS_LOG`: Access log file path (default: stdout)
- `GUNICORN_ERROR_LOG`: Error log file path (default: stderr)
- `GUNICORN_LOG_LEVEL`: Log level (default: `info`)
- `GUNICORN_PIDFILE`: PID file path (optional)

Example:
```bash
export GUNICORN_WORKERS=8
export GUNICORN_BIND=0.0.0.0:8000
gunicorn --config gunicorn_config.py wsgi:application
```

## Important Notes

1. **Worker Class**: This application uses `eventlet` workers, which is required for Flask-SocketIO to work properly with Gunicorn.

2. **SocketIO Async Mode**: The application is configured to use `eventlet` async mode when running with Gunicorn. This is set via the `SOCKETIO_ASYNC_MODE` environment variable (defaults to `eventlet`).

3. **Development vs Production**: 
   - For development, continue using `run.py` with `socketio.run()`
   - For production, use Gunicorn as described above

4. **Reverse Proxy**: If you're using a reverse proxy (nginx, Apache), make sure to:
   - Configure WebSocket support
   - Set appropriate timeouts
   - Forward the necessary headers

## Nginx Configuration Example

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Systemd Service (Linux)

Create `/etc/systemd/system/finance-game-backend.service`:

```ini
[Unit]
Description=Finance Game Backend Gunicorn Service
After=network.target

[Service]
User=your-user
Group=your-group
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn --config gunicorn_config.py wsgi:application

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-game-backend
sudo systemctl start finance-game-backend
```

## Monitoring

- Check logs: `tail -f /var/log/gunicorn/access.log` (or wherever you configured logs)
- Check process: `ps aux | grep gunicorn`
- Restart service: `sudo systemctl restart finance-game-backend`

