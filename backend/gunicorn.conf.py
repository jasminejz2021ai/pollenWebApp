"""Gunicorn configuration for Render deployment.

preload_app imports the Flask app ONCE in the master process, then forks
workers. This guarantees every worker has the identical, fully-registered
route table (fixing intermittent 404s from a half-initialized worker) and
halves memory use by loading NumPy/SciPy a single time before forking, which
matters on Render's 512MB free tier.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"

preload_app = True

workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"

timeout = 120
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
