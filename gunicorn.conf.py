import multiprocessing
import os

# Bind to 0.0.0.0:5000
bind = "0.0.0.0:5000"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
worker_tmp_dir = "/dev/shm"
forwarded_allow_ips = "*"

# Startup
preload_app = True
reload = False

# SSL (if needed)
# keyfile = ''
# certfile = ''

# Process naming
proc_name = "tinnito_gunicorn"

# Server mechanics
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

def when_ready(server):
    """Log when server is ready."""
    server.log.info("Server is ready. Spawning workers")
