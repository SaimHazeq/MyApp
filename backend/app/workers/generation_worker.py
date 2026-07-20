"""
Generation Worker
=================
Runs `MoviePipeline.run()` off the request thread so `POST /generation/{id}/start`
returns immediately and the frontend polls `GET /generation/{id}/status` for
progress.

Ships with a zero-infrastructure `ThreadPoolExecutor` backend so the whole
app works out of the box on a single machine. For real production scale
(many concurrent renders, multiple worker machines, retries/backoff), flip
`USE_CELERY=true` in `.env` and swap the two functions below for
`generation_task.delay(project_id)` / `app.control.revoke(...)` against a
Celery app - a minimal example is sketched in the comment block at the
bottom of this file, left commented out since Celery requires a running
Redis broker that isn't guaranteed to exist in every environment.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings
from app.services.pipeline import MoviePipeline
from app.utils.logger import logger

settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="movie-gen")
_cancel_flags: dict[str, bool] = {}
_lock = threading.Lock()


def enqueue_generation(project_id: str) -> None:
    with _lock:
        _cancel_flags[project_id] = False
    _executor.submit(_run_job, project_id)
    logger.info("Enqueued generation job for project {}", project_id)


def cancel_generation(project_id: str) -> None:
    with _lock:
        _cancel_flags[project_id] = True


def _is_cancelled(project_id: str) -> bool:
    with _lock:
        return _cancel_flags.get(project_id, False)


def _run_job(project_id: str) -> None:
    pipeline = MoviePipeline()
    try:
        pipeline.run(project_id, is_cancelled=lambda: _is_cancelled(project_id))
    finally:
        pipeline.cleanup_temp(project_id)
        with _lock:
            _cancel_flags.pop(project_id, None)


# ---------------------------------------------------------------------------
# Celery upgrade path (optional, for multi-machine production deployments)
# ---------------------------------------------------------------------------
# from celery import Celery
#
# celery_app = Celery("ai_cartoon_movie_maker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
#
# @celery_app.task(bind=True)
# def generation_task(self, project_id: str):
#     pipeline = MoviePipeline()
#     pipeline.run(project_id, is_cancelled=lambda: False)  # use task.AsyncResult(...).state == "REVOKED"
#
# # in enqueue_generation(): generation_task.delay(project_id)
# # in cancel_generation():  celery_app.control.revoke(task_id, terminate=True)
