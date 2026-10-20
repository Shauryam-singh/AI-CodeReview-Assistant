import os

from arq.connections import ArqRedis, RedisSettings, create_pool

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    return _pool


async def enqueue_pr_scan(payload: dict) -> str | None:
    pool = await get_pool()
    job = await pool.enqueue_job("process_pr_event", payload)
    return job.job_id if job else None
