import hashlib
import json
import logging
import os
from typing import Any

from arq.connections import RedisSettings, create_pool

from app.services.llm.config import LLMSettings
from app.services.queue import REDIS_URL

logger = logging.getLogger(__name__)

DEFAULT_LLM_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

_pool = None


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name) or default)
        return max(0, value)
    except (TypeError, ValueError):
        return default


def get_cache_ttl() -> int:
    return _env_int("LLM_CACHE_TTL_SECONDS", DEFAULT_LLM_CACHE_TTL_SECONDS)


def _get_cache_key(settings: LLMSettings, head_sha: str | None) -> str:
    """Cache key: llm:{provider}:{model}:{prompt_version}:{head_sha}"""
    from app.services.llm.prompt import PROMPT_VERSION
    
    provider = (settings.provider or "gemini").strip().lower()
    model = (settings.model or "").strip()
    prompt_version = PROMPT_VERSION
    sha = (head_sha or "none").strip()
    
    # Hash to keep key short and safe
    raw = f"{provider}:{model}:{prompt_version}:{sha}"
    return f"llm:{provider}:{model}:{prompt_version}:{sha}"


async def _get_redis_pool():
    global _pool
    if _pool is None:
        try:
            _pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
        except Exception:
            logger.debug("Failed to create Redis pool for LLM cache")
            return None
    return _pool


async def get_cached_result(key: str) -> list | None:
    try:
        pool = await _get_redis_pool()
        if pool is None:
            return None
        cached = await pool.get(key)
        if cached:
            logger.debug("LLM cache hit for key %s", key)
            return json.loads(cached)
    except Exception:
        logger.debug("LLM cache get failed")
    return None


async def set_cached_result(key: str, result: list, ttl: int) -> bool:
    try:
        pool = await _get_redis_pool()
        if pool is None:
            return False
        value = json.dumps(result)
        await pool.set(key, value, ex=ttl)
        logger.debug("LLM cache set for key %s (ttl=%s)", key, ttl)
        return True
    except Exception:
        logger.debug("LLM cache set failed")
        return False
