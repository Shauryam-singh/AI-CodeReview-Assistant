"""Minimal Gemini REST client for the optional LLM review stage.

The client never raises on network/API errors. It returns ``None`` so the
review service can log the failure and continue with the deterministic scan
results. A single 429 is retried after ``Retry-After`` (capped to keep the
optional stage bounded).
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import quote

import requests

from app.services.llm.config import LLMSettings

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_RETRY_AFTER_SECONDS = 1.0
MAX_RETRY_AFTER_SECONDS = 30.0

REVIEW_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "findings": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "file": {"type": "STRING"},
                    "line": {"type": "INTEGER"},
                    "severity": {
                        "type": "STRING",
                        "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    },
                    "category": {"type": "STRING"},
                    "message": {"type": "STRING"},
                    "suggestion": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": [
                    "file",
                    "line",
                    "severity",
                    "category",
                    "message",
                    "suggestion",
                    "confidence",
                ],
            },
        }
    },
    "required": ["findings"],
}


class LLMClient(Protocol):
    def generate_json(self, prompt: str) -> Any | None:  # pragma: no cover - protocol
        ...


def parse_json_payload(text: str) -> Any | None:
    """Parse a JSON response, tolerating markdown fences and extra prose."""
    if not isinstance(text, str):
        return None

    cleaned = text.strip().lstrip("\ufeff")
    if not cleaned:
        return None

    fenced = re.match(
        r"^```(?:json|jsonc)?\s*(.*?)\s*```\s*$", cleaned, flags=re.IGNORECASE | re.DOTALL
    )
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    starts = [index for index in (cleaned.find("{"), cleaned.find("[")) if index != -1]
    if not starts:
        return None
    start = min(starts)
    end = max(cleaned.rfind("}"), cleaned.rfind("]"))
    if end <= start:
        return None

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse LLM JSON response: %s", exc)
        return None


def _retry_after_seconds(response: requests.Response) -> float:
    headers = getattr(response, "headers", {}) or {}
    raw = headers.get("Retry-After")
    if raw is None:
        return DEFAULT_RETRY_AFTER_SECONDS

    seconds: float | None = None
    try:
        seconds = float(str(raw).strip())
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(str(raw))
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            seconds = DEFAULT_RETRY_AFTER_SECONDS

    return max(0.0, min(float(seconds), MAX_RETRY_AFTER_SECONDS))


def _response_preview(response: requests.Response) -> str:
    try:
        text = response.text or ""
    except Exception:
        return ""
    return text[:500].replace("\n", " ")


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> None:
        normalized_model = (model or "").strip()
        if normalized_model.startswith("models/"):
            normalized_model = normalized_model[len("models/") :]
        self.api_key = api_key
        self.model = normalized_model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.url = f"{GEMINI_API_BASE}/{quote(normalized_model, safe='')}:generateContent"

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": REVIEW_RESPONSE_SCHEMA,
            },
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        for attempt in range(2):
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                logger.warning("Gemini request failed: %s", exc)
                return None

            if response.status_code == 429 and attempt == 0:
                delay = _retry_after_seconds(response)
                logger.warning("Gemini rate-limited; retrying in %.1fs", delay)
                time.sleep(delay)
                continue

            if response.status_code != 200:
                logger.warning(
                    "Gemini API returned HTTP %s: %s",
                    response.status_code,
                    _response_preview(response),
                )
                return None

            try:
                data = response.json()
            except (TypeError, ValueError) as exc:
                logger.warning("Gemini returned an invalid JSON envelope: %s", exc)
                return None

            if not isinstance(data, dict):
                logger.warning("Gemini returned an unexpected JSON type: %s", type(data).__name__)
                return None
            return data

        return None

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            feedback = data.get("promptFeedback") or {}
            reason = feedback.get("blockReason") if isinstance(feedback, dict) else None
            logger.warning("Gemini returned no candidates (blockReason=%s)", reason)
            return ""

        candidate = candidates[0]
        if not isinstance(candidate, dict):
            return ""

        content = candidate.get("content") or {}
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            parts = []

        texts: list[str] = []
        for part in parts:
            if not isinstance(part, dict) or part.get("thought") is True:
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                texts.append(text)

        if not texts:
            logger.warning(
                "Gemini returned no text (finishReason=%s)",
                candidate.get("finishReason"),
            )
        return "".join(texts)

    def generate_json(self, prompt: str) -> Any | None:
        if not self.api_key:
            logger.info("Gemini client has no API key")
            return None

        response = self._post(self._build_payload(prompt))
        if response is None:
            return None

        text = self._extract_text(response)
        if not text:
            return None
        return parse_json_payload(text)


def build_client(settings: LLMSettings) -> LLMClient | None:
    provider = (settings.provider or "").strip().lower()
    if provider not in {"gemini", "google", "google-gemini"}:
        logger.warning(
            "Unsupported LLM_PROVIDER=%r; only Gemini is implemented", settings.provider
        )
        return None
    if not settings.api_key:
        logger.info("LLM review skipped: LLM_API_KEY is not set")
        return None
    return GeminiClient(
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=settings.max_output_tokens,
    )


__all__ = [
    "GEMINI_API_BASE",
    "GeminiClient",
    "LLMClient",
    "REVIEW_RESPONSE_SCHEMA",
    "build_client",
    "parse_json_payload",
]
