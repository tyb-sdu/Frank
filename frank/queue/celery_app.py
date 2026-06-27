"""Celery application configuration."""

from __future__ import annotations

from celery import Celery

from ..config import get_broker_url, get_result_backend_url

celery_app = Celery(
    "frank",
    broker=get_broker_url(),
    backend=get_result_backend_url(),
    include=["frank.queue.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
