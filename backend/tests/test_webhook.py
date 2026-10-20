import hashlib
import hmac
import json
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

SECRET = "test-webhook-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(client, payload, event="pull_request", secret=SECRET, sign=True,
          delivery="abc-123"):
    body = json.dumps(payload).encode()
    headers = {"X-GitHub-Event": event, "X-GitHub-Delivery": delivery}
    if sign:
        headers["X-Hub-Signature-256"] = _sign(body, secret)
    return client.post("/webhook/github", content=body, headers=headers)


def test_webhook_disabled_without_secret(monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    client = TestClient(app)
    r = _post(client, {"zen": "hi"}, event="ping", sign=False)
    assert r.status_code == 503


def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    client = TestClient(app)
    r = _post(client, {"zen": "hi"}, event="ping", secret="wrong-secret")
    assert r.status_code == 401


def test_webhook_rejects_missing_signature(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    client = TestClient(app)
    r = _post(client, {"zen": "hi"}, event="ping", sign=False)
    assert r.status_code == 401


def test_webhook_ping_returns_pong(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    client = TestClient(app)
    r = _post(client, {"zen": "Keep it logically awesome."}, event="ping")
    assert r.status_code == 200
    assert r.json() == {"status": "pong"}


def test_webhook_pr_opened_enqueues_scan(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    payload = {
        "action": "opened",
        "pull_request": {"number": 5, "html_url": "https://github.com/a/b/pull/5"},
        "repository": {"full_name": "a/b"},
    }
    with patch("app.routes.webhook.enqueue_pr_scan", return_value="job-123") as mock_enqueue:
        client = TestClient(app)
        r = _post(client, payload, event="pull_request")
    assert r.status_code == 202
    assert r.json()["status"] == "queued"
    assert r.json()["job_id"] == "job-123"
    assert r.json()["action"] == "opened"
    assert mock_enqueue.call_count == 1


def test_webhook_enqueue_failure_returns_503(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    payload = {
        "action": "opened",
        "pull_request": {"number": 5},
        "repository": {"full_name": "a/b"},
    }
    with patch("app.routes.webhook.enqueue_pr_scan", side_effect=ConnectionError("no redis")):
        client = TestClient(app)
        r = _post(client, payload, event="pull_request")
    assert r.status_code == 503


def test_webhook_pr_closed_is_ignored(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    payload = {"action": "closed", "pull_request": {"number": 5}}
    with patch("app.routes.webhook.enqueue_pr_scan") as mock_enqueue:
        client = TestClient(app)
        r = _post(client, payload, event="pull_request")
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    assert mock_enqueue.call_count == 0


def test_webhook_unknown_event_ignored(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    client = TestClient(app)
    r = _post(client, {"ref": "refs/heads/main"}, event="push")
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_webhook_invalid_json_returns_400(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    body = b"not-json"
    headers = {
        "X-GitHub-Event": "ping",
        "X-Hub-Signature-256": _sign(body),
    }
    client = TestClient(app)
    r = client.post("/webhook/github", content=body, headers=headers)
    assert r.status_code == 400
