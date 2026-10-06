import ssl

from celery import Celery

from app.config import log_missing_env_vars, settings

# Startup check for missing environment variables
log_missing_env_vars()

celery_app = Celery(
    "docflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

if settings.redis_url.startswith("rediss://"):
    if "ssl_cert_reqs" not in settings.redis_url:
        ssl_options = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    else:
        ssl_options = True

    celery_app.conf.broker_use_ssl = ssl_options
    celery_app.conf.redis_backend_use_ssl = ssl_options
