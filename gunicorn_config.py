# Configuration Gunicorn pour Subly Cloud

import multiprocessing

# Adresse et port
bind = "127.0.0.1:8000"

# Nombre de workers (2-4 x CPU cores)
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker
worker_class = "sync"

# Timeout
timeout = 120

# Logs
accesslog = "/opt/subly.cloud/logs/gunicorn_access.log"
errorlog = "/opt/subly.cloud/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "subly_cloud"

# Reload on code changes (désactiver en production)
reload = False
