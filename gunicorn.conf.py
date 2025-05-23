# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = 4  # Good default for most cases
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'ngo-connect-api'

# SSL config
keyfile = None
certfile = None

# Reload code when changed (development only)
reload = False

# Maximum requests before worker restart
max_requests = 1000
max_requests_jitter = 50

