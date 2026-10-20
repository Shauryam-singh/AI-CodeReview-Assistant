import asyncio
from unittest.mock import patch

from arq.worker import Retry

from app.services.errors import RetryableScanError
from app.worker import DEFAULT_MAX_TRIES, _backoff_delay, max_tries, process_pr_event


def _run_worker(ctx, side_effect=None, return_value=None):
    """Run the worker coroutine once; returns (raised_retry, mocks...)."""
    with patch("app.worker._process_pr_event", side_effect=side_effect,
               return_value=return_value), \
         patch("app.worker.record_job_retry") as mock_record_retry, \
         patch("app.worker.finish_job") as mock_finish:
        raised = None
        try:
            asyncio.run(process_pr_event(ctx, {"n": 1}))
        except Retry as e:
            raised = e
    return raised, mock_record_retry, mock_finish


def test_transient_error_schedules_retry(monkeypatch):
    monkeypatch.setenv("WEBHOOK_RETRY_BASE_SECONDS", "10")
    raised, mock_record_retry, mock_finish = _run_worker(
        {"job_id": "job-1", "job_try": 1},
        side_effect=RetryableScanError("GitHub review post failed with status 502"),
    )
    assert isinstance(raised, Retry)
    assert 8000 <= raised.defer_score <= 12000  # ~10s +-20% jitter, in ms
    mock_record_retry.assert_called_once_with(
        "job-1", 1, "GitHub review post failed with status 502"
    )
    assert mock_finish.call_count == 0


def test_retry_delay_grows_exponentially(monkeypatch):
    monkeypatch.setenv("WEBHOOK_RETRY_BASE_SECONDS", "10")
    raised, _, _ = _run_worker(
        {"job_id": "job-1", "job_try": 3},
        side_effect=RetryableScanError("boom"),
    )
    assert 32000 <= raised.defer_score <= 48000  # ~40s +-20%


def test_retry_delay_is_capped(monkeypatch):
    monkeypatch.setenv("WEBHOOK_RETRY_BASE_SECONDS", "10")
    monkeypatch.setenv("WEBHOOK_RETRY_MAX_SECONDS", "25")
    raised, _, _ = _run_worker(
        {"job_id": "job-1", "job_try": 4},
        side_effect=RetryableScanError("boom"),
    )
    assert 20000 <= raised.defer_score <= 30000  # capped at ~25s


def test_final_try_dead_letters(monkeypatch):
    monkeypatch.setenv("WEBHOOK_MAX_TRIES", "3")
    raised, mock_record_retry, mock_finish = _run_worker(
        {"job_id": "job-1", "job_try": 3},
        side_effect=RetryableScanError("boom"),
    )
    assert raised is None  # no further retry
    mock_record_retry.assert_called_once_with("job-1", 3, "boom")
    mock_finish.assert_called_once_with("job-1", "dead_letter", "boom")


def test_success_does_not_retry():
    raised, mock_record_retry, mock_finish = _run_worker(
        {"job_id": "job-1", "job_try": 1}, return_value=None
    )
    assert raised is None
    assert mock_record_retry.call_count == 0
    assert mock_finish.call_count == 0


def test_permanent_error_propagates():
    """Only RetryableScanError is retried; anything else must propagate to
    arq (which marks the job failed without retrying)."""
    with patch("app.worker._process_pr_event", side_effect=RuntimeError("boom")), \
         patch("app.worker.record_job_retry") as mock_record_retry, \
         patch("app.worker.finish_job") as mock_finish:
        try:
            asyncio.run(process_pr_event({"job_id": "j", "job_try": 1}, {}))
            raise AssertionError("expected RuntimeError")
        except RuntimeError as e:
            assert str(e) == "boom"
        assert mock_record_retry.call_count == 0
        assert mock_finish.call_count == 0


def test_backoff_delay_bounds(monkeypatch):
    monkeypatch.delenv("WEBHOOK_RETRY_BASE_SECONDS", raising=False)
    monkeypatch.delenv("WEBHOOK_RETRY_MAX_SECONDS", raising=False)
    d1 = _backoff_delay(1)
    assert 24.0 <= d1 <= 36.0  # 30s +-20%
    d2 = _backoff_delay(2)
    assert 48.0 <= d2 <= 72.0  # 60s +-20%
    d5 = _backoff_delay(5)
    assert 384.0 <= d5 <= 576.0  # 30*16 = 480s +-20%
    d8 = _backoff_delay(8)
    assert 2880.0 <= d8 <= 4320.0  # capped at 3600s


def test_backoff_delay_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("WEBHOOK_RETRY_BASE_SECONDS", "not-a-number")
    monkeypatch.delenv("WEBHOOK_RETRY_MAX_SECONDS", raising=False)
    d1 = _backoff_delay(1)
    assert 24.0 <= d1 <= 36.0


def test_max_tries_reads_env(monkeypatch):
    monkeypatch.setenv("WEBHOOK_MAX_TRIES", "2")
    assert max_tries() == 2
    monkeypatch.setenv("WEBHOOK_MAX_TRIES", "bogus")
    assert max_tries() == DEFAULT_MAX_TRIES
