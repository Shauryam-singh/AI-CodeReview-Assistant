from unittest.mock import MagicMock

import pytest
import requests

from app.services.llm import client as client_module
from app.services.llm.client import GeminiClient, build_client, parse_json_payload
from app.services.llm.config import LLMSettings


def _settings(**overrides):
    values = {
        "enabled": True,
        "provider": "gemini",
        "api_key": "test-key",
        "model": "gemini-3.8-flash",
        "timeout_seconds": 5.0,
        "max_input_chars": 120_000,
        "max_output_tokens": 4_096,
        "max_findings": 10,
        "min_confidence": 0.6,
        "allow_private_repos": False,
    }
    values.update(overrides)
    return LLMSettings(**values)


def _response(status=200, payload=None, text="", headers=None):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = text
    response.headers = headers or {}
    return response


def _envelope(text):
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": "STOP",
            }
        ]
    }


def test_parse_json_payload_handles_fences_and_prose():
    assert parse_json_payload('```json\n{"findings": []}\n```') == {"findings": []}
    assert parse_json_payload(
        'Here is the result:\n```json\n{"findings": [{"file": "a.py"}]}\n```\n'
    ) == {"findings": [{"file": "a.py"}]}
    assert parse_json_payload("not json") is None


def test_generate_json_sends_json_mode_schema_and_timeout(monkeypatch):
    post = MagicMock(
        return_value=_response(payload=_envelope('{"findings": []}'))
    )
    monkeypatch.setattr(client_module.requests, "post", post)

    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    result = client.generate_json("review this")

    assert result == {"findings": []}
    assert post.call_count == 1
    call = post.call_args
    assert call.kwargs["timeout"] == 5.0
    assert call.kwargs["headers"]["x-goog-api-key"] == "test-key"
    assert "test-key" not in call.args[0]
    generation = call.kwargs["json"]["generationConfig"]
    assert generation["responseMimeType"] == "application/json"
    assert "responseSchema" in generation
    assert generation["maxOutputTokens"] == 1_024


def test_generate_json_parses_fenced_candidate_text(monkeypatch):
    post = MagicMock(
        return_value=_response(
            payload=_envelope('```json\n{"findings": [{"file": "a.py"}]}\n```')
        )
    )
    monkeypatch.setattr(client_module.requests, "post", post)

    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") == {"findings": [{"file": "a.py"}]}


def test_429_retries_once_after_retry_after(monkeypatch):
    post = MagicMock(
        side_effect=[
            _response(429, headers={"Retry-After": "2"}),
            _response(payload=_envelope('{"findings": []}')),
        ]
    )
    sleep = MagicMock()
    monkeypatch.setattr(client_module.requests, "post", post)
    monkeypatch.setattr(client_module.time, "sleep", sleep)

    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") == {"findings": []}
    assert post.call_count == 2
    sleep.assert_called_once_with(2.0)


def test_429_twice_skips_after_one_retry(monkeypatch):
    post = MagicMock(
        side_effect=[
            _response(429, headers={}),
            _response(429, headers={}),
        ]
    )
    sleep = MagicMock()
    monkeypatch.setattr(client_module.requests, "post", post)
    monkeypatch.setattr(client_module.time, "sleep", sleep)

    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") is None
    assert post.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_request_exception_returns_none(monkeypatch):
    monkeypatch.setattr(
        client_module.requests,
        "post",
        MagicMock(side_effect=requests.Timeout("slow")),
    )
    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") is None


def test_non_200_returns_none(monkeypatch):
    monkeypatch.setattr(
        client_module.requests,
        "post",
        MagicMock(return_value=_response(500, text="server error")),
    )
    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") is None


def test_missing_candidate_returns_none(monkeypatch):
    monkeypatch.setattr(
        client_module.requests,
        "post",
        MagicMock(return_value=_response(payload={})),
    )
    client = GeminiClient("test-key", "gemini-3.8-flash", 5.0, 1_024)
    assert client.generate_json("prompt") is None


def test_build_client_rejects_unsupported_provider():
    assert build_client(_settings(provider="openai")) is None


def test_build_client_requires_api_key():
    assert build_client(_settings(api_key="")) is None


def test_build_client_normalizes_model_prefix():
    client = build_client(_settings(model="models/gemini-3.8-flash"))
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-3.8-flash"
    assert "models/models/" not in client.url
