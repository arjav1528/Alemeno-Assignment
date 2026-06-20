from lib.env import REDIS_URL
from celery import Celery

celery = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)

celery.autodiscover_tasks(["tasks"])