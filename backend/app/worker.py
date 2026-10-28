import asyncio
import os
import random

from arq.connections import RedisSettings
from arq.worker import Retry

from app.services.errors import RetryableScanError
from app.services.queue import REDIS_URL
from app.services.recording import (
    STATUS_DEAD_LETTER,
    finish_job,
    record_job_retry,
)
from app.services.webhook_service import process_pr_event as _process_pr_event

DEFAULT_MAX_TRIES = 5
DEFAULT_RETRY_BASE_SECONDS = 30
DEFAULT_RETRY_MAX_SECONDS = 3600


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name) or default))
    except (TypeError, ValueError):
        return default


def max_tries() -> int:
    return _env_int("WEBHOOK_MAX_TRIES", DEFAULT_MAX_TRIES)


def _backoff_delay(job_try: int) -> float:
    """Exponential backoff with +-20% jitter, capped by config.

    try 1 -> ~base, try 2 -> ~2*base, ... up to WEBHOOK_RETRY_MAX_SECONDS.
    """
    base = _env_int("WEBHOOK_RETRY_BASE_SECONDS", DEFAULT_RETRY_BASE_SECONDS)
    cap = max(base, _env_int("WEBHOOK_RETRY_MAX_SECONDS", DEFAULT_RETRY_MAX_SECONDS))
    delay = min(base * (2 ** max(0, job_try - 1)), cap)
    return delay * random.uniform(0.8, 1.2)


async def process_pr_event(ctx, payload: dict):
    job_id = ctx.get("job_id")
    job_try = ctx.get("job_try", 1)
    try:
        await asyncio.to_thread(_process_pr_event, payload, job_id)
    except RetryableScanError as e:
        await asyncio.to_thread(record_job_retry, job_id, job_try, str(e))
        if job_try >= max_tries():
            # Attempts exhausted: park the job in the dead-letter state
            # instead of raising Retry (arq would only mark it failed).
            await asyncio.to_thread(
                finish_job, job_id, STATUS_DEAD_LETTER, str(e)
            )
            return
        raise Retry(defer=_backoff_delay(job_try))


class WorkerSettings:
    functions = [process_pr_event]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 600
    max_tries = max_tries()
    max_jobs = 2
