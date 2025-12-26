"""
Gunicorn configuration file
"""
import multiprocessing
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"  # Use gthread for Flask-SocketIO with threading mode
threads = int(os.getenv("GUNICORN_THREADS", 4))  # Number of threads per worker
timeout = 30
keepalive = 2

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

