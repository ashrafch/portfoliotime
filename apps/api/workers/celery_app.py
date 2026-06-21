"""
Celery — worker per simulazioni asincrone pesanti (R5: > 2s → Celery).

Avvio worker in locale:
    cd apps/api && celery -A workers.celery_app worker --loglevel=info
"""

from celery import Celery
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "portfoliotime",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # i risultati scadono dopo 1 ora
)
