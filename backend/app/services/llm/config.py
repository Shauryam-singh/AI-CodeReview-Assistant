"""Environment-backed settings for the optional LLM review stage.

The LLM stage is deliberately opt-in: ``LLM_ENABLED`` defaults to ``false``
and every failure path in the review service degrades to an empty finding
list, so the deterministic static-analysis pipeline keeps working.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

try:  # python-dotenv is pinned in requirements.txt
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only relevant in a broken install
    load_dotenv = None


DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_TIMEOUT_SECONDS = 45.0
DEFAULT_MAX_INPUT_CHARS = 120_000
DEFAULT_MAX_OUTPUT_TOKENS = 4_096
DEFAULT_MAX_FINDINGS = 10
DEFAULT_MIN_CONFIDENCE = 0.6


def _load_local_env() -> None:
    """Load the repo-root .env without overriding real environment variables."""
    if load_dotenv is None:
        return

    candidates: list[Path] = []
    try:
        # backend/app/services/llm/config.py -> repo root
        candidates.append(Path(__file__).resolve().parents[4] / ".env")
    except IndexError:
        pass
    candidates.append(Path.cwd() / ".env")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


_load_local_env()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid integer for %s=%r; using %s", name, raw, default)
        return default
    if minimum is not None and value < minimum:
        logger.warning("Ignoring %s=%s (minimum %s); using %s", name, value, minimum, default)
        return default
    return value


def _env_float(
    name: str,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid float for %s=%r; using %s", name, raw, default)
        return default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


@dataclass(frozen=True)
class LLMSettings:
    enabled: bool
    provider: str
    api_key: str
    model: str
    timeout_seconds: float
    max_input_chars: int
    max_output_tokens: int
    max_findings: int
    min_confidence: float
    allow_private_repos: bool

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.api_key)


def get_settings() -> LLMSettings:
    """Read settings from the environment on every call (easy to test)."""
    return LLMSettings(
        enabled=_env_bool("LLM_ENABLED", False),
        provider=_env_str("LLM_PROVIDER", DEFAULT_PROVIDER).lower(),
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        model=_env_str("LLM_MODEL", DEFAULT_MODEL),
        timeout_seconds=_env_float(
            "LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, minimum=1.0
        ),
        max_input_chars=_env_int(
            "LLM_MAX_INPUT_CHARS", DEFAULT_MAX_INPUT_CHARS, minimum=1_000
        ),
        max_output_tokens=_env_int(
            "LLM_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS, minimum=128
        ),
        max_findings=_env_int("LLM_MAX_FINDINGS", DEFAULT_MAX_FINDINGS, minimum=1),
        min_confidence=_env_float(
            "LLM_MIN_CONFIDENCE", DEFAULT_MIN_CONFIDENCE, minimum=0.0, maximum=1.0
        ),
        allow_private_repos=_env_bool("LLM_ALLOW_PRIVATE_REPOS", False),
    )


__all__ = [
    "DEFAULT_MAX_FINDINGS",
    "DEFAULT_MAX_INPUT_CHARS",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_MIN_CONFIDENCE",
    "DEFAULT_MODEL",
    "DEFAULT_PROVIDER",
    "DEFAULT_TIMEOUT_SECONDS",
    "LLMSettings",
    "get_settings",
]
