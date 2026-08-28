from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "careerpilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.job_sync", "app.tasks.resume_processing"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 10,
)

celery_app.conf.beat_schedule = {
    "sync-all-companies": {
        "task": "app.tasks.job_sync.sync_all_companies",
        "schedule": crontab(minute=0),  # hourly; tune via JOB_SYNC_INTERVAL_MINUTES in a real deployment
    },
}
