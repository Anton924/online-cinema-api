from datetime import timedelta

from celery import Celery

app = Celery("online_cinema", broker="redis://redis:6379/0")
app.conf.update(
    result_backend="redis://redis:6379/0",
    beat_schedule={
        "clean-data-from-expired-tokens": {
            "task": "tasks.celery_tasks.clean_data_from_expired_tokens",
            "schedule": timedelta(hours=1),
        },
    },
    include=["tasks.celery_tasks"]
)
