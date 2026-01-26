# Configuration Gunicorn pour Budgee Family

import multiprocessing

# Adresse et port
bind = "127.0.0.1:8000"

# Nombre de workers (2-4 x CPU cores)
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker
worker_class = "sync"

# Timeout (5 minutes pour traitement OCR)
timeout = 300

# Logs
accesslog = "/opt/budgeefamily/logs/gunicorn_access.log"
errorlog = "/opt/budgeefamily/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "budgeefamily"

# Reload on code changes (désactiver en production)
reload = False
