import os

from arq.connections import ArqRedis, RedisSettings, create_pool

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    return _pool


async def enqueue_pr_scan(payload: dict, job_id: str | None = None) -> str | None:
    """Enqueue a PR scan.

    When ``job_id`` is given it is used as the arq job id, so re-enqueueing
    the same id (e.g. a GitHub delivery redelivery) is a no-op and returns
    None instead of creating a duplicate job.
    """
    pool = await get_pool()
    job = await pool.enqueue_job("process_pr_event", payload, _job_id=job_id)
    return job.job_id if job else None
