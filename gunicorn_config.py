"""
Gunicorn configuration file
"""
import multiprocessing
import os

# Server socket
# Railway provides PORT environment variable, fallback to 5000 for local development
port = os.getenv("PORT", os.getenv("GUNICORN_PORT", "5000"))
bind = os.getenv("GUNICORN_BIND", f"0.0.0.0:{port}")
backlog = 2048

# Worker processes
# Default to 2 workers to prevent memory issues on Railway and similar platforms
# Railway typically has 512MB-1GB RAM, so fewer workers are safer
# Override with GUNICORN_WORKERS environment variable if you have more resources
default_workers = 2  # Safe default for Railway
workers = int(os.getenv("GUNICORN_WORKERS", default_workers))
worker_class = "gthread"  # Use gthread for Flask-SocketIO with threading mode
threads = int(os.getenv("GUNICORN_THREADS", 2))  # Number of threads per worker
timeout = 30
keepalive = 2
# Max requests per worker to prevent memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 50))

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" means stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # "-" means stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "finance-game-backend"

# Server mechanics
daemon = False
pidfile = os.getenv("GUNICORN_PIDFILE", None)
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if using HTTPS)
# keyfile = None
# certfile = None

