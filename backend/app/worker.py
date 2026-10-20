import asyncio

from arq.connections import RedisSettings

from app.services.queue import REDIS_URL
from app.services.webhook_service import process_pr_event as _process_pr_event


async def process_pr_event(ctx, payload: dict):
    await asyncio.to_thread(_process_pr_event, payload, ctx.get("job_id"))


class WorkerSettings:
    functions = [process_pr_event]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 600
