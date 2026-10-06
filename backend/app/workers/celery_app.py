from celery import Celery

from app.config import settings


celery_app = Celery("docflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_acks_late = True
