import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import (
    Base,
    get_engine,
    normalize_database_url,
    reset_engine,
    session_scope,
)
from app.main import app
from app.models.tables import Finding, Job, PullRequest, Repo, Review
from app.services.recording import (
    KIND_REVIEW,
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_RETRYING,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STATUS_SUCCEEDED,
    STATUS_FAILED,
    finish_job,
    is_duplicate_delivery,
    mark_job_running,
    record_findings,
    record_job_queued,
    record_job_retry,
    record_review,
)
from app.services.webhook_service import process_pr_event

SECRET = "db-test-secret"

PAYLOAD = {
    "action": "opened",
    "pull_request": {
        "number": 7,
        "title": "Fix bug",
        "state": "open",
        "html_url": "https://github.com/a/b/pull/7",
        "head": {"sha": "aaa111"},
        "base": {"sha": "bbb222"},
    },
    "repository": {"full_name": "a/b", "html_url": "https://github.com/a/b"},
}

PIPELINE = {
    "repo_path": "/tmp/repo",
    "metadata": {},
    "context": {
        "diff": {"app.py": ["+new"]},
        "diff_text": (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -10,2 +10,3 @@\n"
            " context\n"
            "-old\n"
            "+new\n"
        ),
        "commits": [],
    },
}


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    reset_engine()
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(engine)
    yield engine
    reset_engine()


def test_normalize_database_url():
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("postgresql+psycopg2://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
    assert normalize_database_url("  sqlite://  ") == "sqlite://"


def test_recording_is_noop_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_engine()
    record_job_queued("job-x", "a/b", 1, action="opened")
    mark_job_running("job-x")
    finish_job("job-x", STATUS_SUCCEEDED)
    record_findings("job-x", "a/b", 1, [{"file": "a.py", "message": "m"}], [])
    record_review("job-x", "a/b", 1, KIND_REVIEW, 201, "body")
    assert get_engine() is None
    with session_scope() as session:
        assert session is None


def test_record_job_queued_creates_repo_pr_job(db):
    record_job_queued(
        "job-1", "a/b", 5, action="opened",
        pr_info=PAYLOAD["pull_request"],
        repo_html_url=PAYLOAD["repository"]["html_url"],
    )
    with session_scope() as s:
        repo = s.query(Repo).one()
        assert repo.full_name == "a/b"
        assert repo.html_url == "https://github.com/a/b"

        pr = s.query(PullRequest).one()
        assert pr.repo_id == repo.id
        assert pr.number == 5
        assert pr.title == "Fix bug"
        assert pr.head_sha == "aaa111"
        assert pr.base_sha == "bbb222"

        job = s.query(Job).one()
        assert job.arq_job_id == "job-1"
        assert job.status == STATUS_QUEUED
        assert job.action == "opened"
        assert job.repo_id == repo.id
        assert job.pull_request_id == pr.id
        assert job.enqueued_at is not None


def test_record_job_queued_is_idempotent(db):
    record_job_queued("job-1", "a/b", 5, action="opened")
    record_job_queued("job-1", "a/b", 5, action="opened")
    with session_scope() as s:
        assert s.query(Job).count() == 1
        assert s.query(Repo).count() == 1
        assert s.query(PullRequest).count() == 1


def test_job_lifecycle(db):
    record_job_queued("job-2", "a/b", 7, action="synchronize")
    mark_job_running("job-2")
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_RUNNING
        assert job.started_at is not None
        assert job.finished_at is None

    finish_job("job-2", STATUS_SUCCEEDED)
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_SUCCEEDED
        assert job.finished_at is not None
        assert job.error is None

    finish_job("does-not-exist", STATUS_FAILED, "nope")  # no-op, must not raise
    with session_scope() as s:
        assert s.query(Job).count() == 1


def test_record_findings_marks_inlined(db):
    record_job_queued("job-3", "a/b", 9)
    issues = [
        {"file": "app.py", "line": 11, "severity": "HIGH", "message": "m1",
         "tool": "semgrep", "risk": "rce", "suggestion": "avoid",
         "code_snippet": "eval(x)"},
        {"file": "app.py", "line": 99, "severity": "LOW", "message": "m2",
         "tool": "python-ast"},
    ]
    inline = [{"path": "app.py", "line": 11, "side": "RIGHT", "body": "..."}]
    record_findings("job-3", "a/b", 9, issues, inline)

    with session_scope() as s:
        findings = s.query(Finding).order_by(Finding.id).all()
        assert len(findings) == 2
        job = s.query(Job).one()
        pr = s.query(PullRequest).one()
        assert findings[0].inlined is True
        assert findings[0].job_id == job.id
        assert findings[0].pull_request_id == pr.id
        assert findings[0].risk == "rce"
        assert findings[1].inlined is False
        assert findings[1].line == 99


def test_record_findings_replaces_previous_attempt(db):
    record_job_queued("job-3b", "a/b", 9)
    issues = [
        {"file": "app.py", "line": 11, "message": "m1"},
        {"file": "app.py", "line": 12, "message": "m2"},
    ]
    record_findings("job-3b", "a/b", 9, issues, [])
    record_findings("job-3b", "a/b", 9, issues[:1], [])  # retry, fewer findings
    with session_scope() as s:
        findings = s.query(Finding).all()
        assert len(findings) == 1  # replaced, not appended
        assert findings[0].message == "m1"


def test_record_review_upserts_per_job_and_kind(db):
    record_job_queued("job-4b", "a/b", 3)
    record_review("job-4b", "a/b", 3, KIND_REVIEW, 0, "body", inline_count=1)
    record_review("job-4b", "a/b", 3, KIND_REVIEW, 200, "body", inline_count=1,
                  github_id=777)
    with session_scope() as s:
        reviews = s.query(Review).all()
        assert len(reviews) == 1
        assert reviews[0].status_code == 200
        assert reviews[0].github_id == 777


def test_record_review_cleans_up_legacy_duplicates(db):
    record_job_queued("job-5b", "a/b", 4)
    with session_scope() as s:
        job = s.query(Job).filter_by(arq_job_id="job-5b").one()
        pr = s.query(PullRequest).one()
        for status in (0, 502):
            s.add(Review(
                pull_request_id=pr.id, job_id=job.id, kind=KIND_REVIEW,
                status_code=status, body="old", inline_count=0,
            ))
    record_review("job-5b", "a/b", 4, KIND_REVIEW, 200, "new",
                  inline_count=2, github_id=9)
    with session_scope() as s:
        reviews = s.query(Review).all()
        assert len(reviews) == 1
        assert reviews[0].status_code == 200
        assert reviews[0].github_id == 9


def test_record_review(db):
    record_job_queued("job-4", "a/b", 3)
    record_review("job-4", "a/b", 3, KIND_REVIEW, 201, "summary body",
                  inline_count=2, github_id=12345)

    with session_scope() as s:
        review = s.query(Review).one()
        assert review.kind == KIND_REVIEW
        assert review.status_code == 201
        assert review.inline_count == 2
        assert review.github_id == 12345
        assert review.body == "summary body"
        assert review.job_id == s.query(Job).one().id
        assert review.pull_request_id == s.query(PullRequest).one().id


def test_webhook_route_records_queued_job(db, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    body = json.dumps(PAYLOAD).encode()
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "d-1",
        "X-Hub-Signature-256": "sha256=" + hmac.new(
            SECRET.encode(), body, hashlib.sha256).hexdigest(),
    }
    with patch("app.routes.webhook.enqueue_pr_scan", return_value="job-abc"):
        client = TestClient(app)
        r = client.post("/webhook/github", content=body, headers=headers)

    assert r.status_code == 202
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.arq_job_id == "job-abc"
        assert job.status == STATUS_QUEUED
        assert job.action == "opened"
        assert job.pull_request_id is not None
        pr = s.query(PullRequest).one()
        assert pr.number == 7
        assert pr.title == "Fix bug"
        assert s.query(Repo).one().full_name == "a/b"


def _mock_pipeline_patches(issues, review_result=(True, 201, 555)):
    return (
        patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE),
        patch("app.services.webhook_service.scan_pr_changes",
              return_value={"issues": issues, "total_files": 1}),
        patch("app.services.webhook_service.get_token_for_repo", return_value="tok"),
        patch("app.services.webhook_service.post_pr_review",
              return_value=review_result),
        patch("app.services.webhook_service.post_pr_comment", return_value=True),
    )


def test_process_pr_event_records_success(db):
    record_job_queued("job-5", "a/b", 7, action="opened")
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH", "message": "bad",
               "tool": "semgrep"}]
    patches = _mock_pipeline_patches(issues)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        process_pr_event(PAYLOAD, job_id="job-5")

    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_SUCCEEDED
        assert job.started_at is not None
        assert job.finished_at is not None

        finding = s.query(Finding).one()
        assert finding.inlined is True

        review = s.query(Review).one()
        assert review.kind == KIND_REVIEW
        assert review.status_code == 201
        assert review.github_id == 555
        assert review.inline_count == 1


def test_process_pr_event_records_failure(db):
    record_job_queued("job-6", "a/b", 7, action="opened")
    with patch("app.services.webhook_service.run_pipeline",
               side_effect=RuntimeError("boom")):
        process_pr_event(PAYLOAD, job_id="job-6")

    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_FAILED
        assert "boom" in job.error
        assert job.finished_at is not None
        assert s.query(Review).count() == 0


def test_process_pr_event_records_skipped_when_no_changed_files(db):
    record_job_queued("job-7", "a/b", 7, action="opened")
    pipeline = dict(PIPELINE, context={"diff": {}, "diff_text": ""})
    with patch("app.services.webhook_service.run_pipeline", return_value=pipeline):
        process_pr_event(PAYLOAD, job_id="job-7")

    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_SKIPPED
        assert "no changed files" in job.error


def test_record_job_queued_stores_delivery_id(db):
    record_job_queued("job-10", "a/b", 5, action="opened", delivery_id="deliv-1")
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.delivery_id == "deliv-1"
        assert job.attempts == 1


def test_is_duplicate_delivery(db):
    assert is_duplicate_delivery("nope") is False
    assert is_duplicate_delivery(None) is False
    record_job_queued("job-11", "a/b", 5, action="opened", delivery_id="deliv-2")
    assert is_duplicate_delivery("deliv-2") is True
    assert is_duplicate_delivery("deliv-3") is False


def test_job_retry_lifecycle(db):
    record_job_queued("job-12", "a/b", 7, action="opened")
    mark_job_running("job-12")
    with session_scope() as s:
        started = s.query(Job).one().started_at
        assert started is not None

    record_job_retry("job-12", 2, "GitHub review post failed with status 502")
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_RETRYING
        assert job.attempts == 2
        assert "502" in job.error
        assert job.finished_at is None

    # a retried job goes back to running, keeping its original start time
    mark_job_running("job-12")
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_RUNNING
        assert job.started_at == started

    finish_job("job-12", STATUS_SUCCEEDED)
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_SUCCEEDED


def test_job_dead_letter_state(db):
    record_job_queued("job-13", "a/b", 7, action="opened")
    record_job_retry("job-13", 5, "Clone timed out after 120s.")
    finish_job("job-13", STATUS_DEAD_LETTER, "Clone timed out after 120s.")
    with session_scope() as s:
        job = s.query(Job).one()
        assert job.status == STATUS_DEAD_LETTER
        assert job.attempts == 5
        assert "timed out" in job.error
        assert job.finished_at is not None


def test_webhook_redelivery_is_deduped_end_to_end(db, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    body = json.dumps(PAYLOAD).encode()
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "same-delivery",
        "X-Hub-Signature-256": "sha256=" + hmac.new(
            SECRET.encode(), body, hashlib.sha256).hexdigest(),
    }
    with patch("app.routes.webhook.enqueue_pr_scan", return_value="job-dup"):
        client = TestClient(app)
        r1 = client.post("/webhook/github", content=body, headers=headers)
        r2 = client.post("/webhook/github", content=body, headers=headers)

    assert r1.status_code == 202
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"
    with session_scope() as s:
        assert s.query(Job).count() == 1
        assert s.query(Job).one().delivery_id == "same-delivery"
