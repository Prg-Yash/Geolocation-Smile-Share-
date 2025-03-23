# Gunicorn configuration file
workers = 4  # Number of worker processes
worker_class = 'uvicorn.workers.UvicornWorker'  # Use Uvicorn's worker class
timeout = 120  # Increase timeout to 120 seconds
keepalive = 5  # Keep-alive timeout
worker_connections = 1000  # Maximum number of simultaneous connections
max_requests = 1000  # Restart workers after handling this many requests
max_requests_jitter = 50  # Add random jitter to max_requests 