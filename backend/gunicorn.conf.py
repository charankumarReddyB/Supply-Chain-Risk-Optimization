import os

# Gunicorn configuration for Render deployment
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
threads = int(os.environ.get("PYTHON_THREADS", 2))
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
