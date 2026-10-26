from unittest.mock import patch

import requests

from app.services.errors import RetryableScanError
from app.services.webhook_service import format_scan_comment, process_pr_event

DIFF = """\
diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -10,3 +10,4 @@
 context
-old
+new
+new2
"""

PAYLOAD = {
    "action": "opened",
    "pull_request": {"number": 7},
    "repository": {"full_name": "a/b"},
}

PIPELINE = {
    "repo_path": "/tmp/repo",
    "metadata": {},
    "context": {"diff": {"app.py": ["+new"]}, "diff_text": DIFF, "commits": []},
}


def _run(issues, review_result=(True, 201, 987), review_side_effect=None):
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo",
               return_value="tok") as mock_token, \
         patch("app.services.webhook_service.post_pr_review",
               return_value=review_result, side_effect=review_side_effect) as mock_review, \
         patch("app.services.webhook_service.post_pr_comment",
               return_value=True) as mock_comment:
        process_pr_event(PAYLOAD)
    return mock_review, mock_comment, mock_token


def test_process_pr_event_posts_inline_review():
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    mock_review, mock_comment, _ = _run(issues)

    assert mock_review.call_count == 1
    args = mock_review.call_args.args
    assert args[0] == "a/b"
    assert args[1] == "7"
    assert args[2] == "tok"
    comments = args[4]
    assert len(comments) == 1
    assert comments[0]["path"] == "app.py"
    assert comments[0]["line"] == 11
    assert comments[0]["side"] == "RIGHT"
    assert "bad call" in comments[0]["body"]
    assert mock_comment.call_count == 0


def test_process_pr_event_falls_back_to_plain_comment_when_review_rejected():
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    mock_review, mock_comment, _ = _run(issues, review_result=(False, 422, None))

    assert mock_review.call_count == 1
    assert mock_comment.call_count == 1
    body = mock_comment.call_args.args[3]
    assert "bad call" in body


def test_process_pr_event_plain_comment_when_nothing_is_anchored():
    issues = [{"file": "app.py", "line": 999, "severity": "LOW",
               "tool": "python-ast", "message": "elsewhere"}]
    mock_review, mock_comment, _ = _run(issues)

    assert mock_review.call_count == 0
    assert mock_comment.call_count == 1
    body = mock_comment.call_args.args[3]
    assert "elsewhere" in body


def test_process_pr_event_no_changed_files_posts_nothing():
    pipeline = dict(PIPELINE, context={"diff": {}, "diff_text": ""})
    with patch("app.services.webhook_service.run_pipeline", return_value=pipeline), \
         patch("app.services.webhook_service.scan_pr_changes") as mock_scan, \
         patch("app.services.webhook_service.post_pr_review") as mock_review, \
         patch("app.services.webhook_service.post_pr_comment") as mock_comment:
        process_pr_event(PAYLOAD)
    assert mock_scan.call_count == 0
    assert mock_review.call_count == 0
    assert mock_comment.call_count == 0


def test_process_pr_event_missing_pr_number_is_noop():
    with patch("app.services.webhook_service.run_pipeline") as mock_pipeline:
        process_pr_event({"repository": {"full_name": "a/b"}})
    assert mock_pipeline.call_count == 0


def test_process_pr_event_passes_retry_marker():
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo", return_value="tok"), \
         patch("app.services.webhook_service.post_pr_review",
               return_value=(True, 201, 987)) as mock_review:
        process_pr_event(PAYLOAD, job_id="job-9")
    assert mock_review.call_args.kwargs["marker"] == "<!-- ai-review:job-9 -->"


def test_process_pr_event_no_marker_without_job_id():
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo", return_value="tok"), \
         patch("app.services.webhook_service.post_pr_review",
               return_value=(True, 201, 987)) as mock_review:
        process_pr_event(PAYLOAD)
    assert mock_review.call_args.kwargs["marker"] is None


def test_process_pr_event_retries_on_transient_review_status():
    """5xx/429 from the review API must raise RetryableScanError, not fall back."""
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo", return_value="tok"), \
         patch("app.services.webhook_service.post_pr_review",
               return_value=(False, 502, None)) as mock_review, \
         patch("app.services.webhook_service.post_pr_comment") as mock_comment:
        try:
            process_pr_event(PAYLOAD)
            raise AssertionError("expected RetryableScanError")
        except RetryableScanError as e:
            assert "502" in str(e)
    assert mock_review.call_count == 1
    assert mock_comment.call_count == 0  # no fallback on transient status


def test_process_pr_event_retries_on_review_network_error():
    issues = [{"file": "app.py", "line": 11, "severity": "HIGH",
               "tool": "semgrep", "message": "bad call"}]
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo", return_value="tok"), \
         patch("app.services.webhook_service.post_pr_review",
               return_value=(False, 0, None)):
        try:
            process_pr_event(PAYLOAD)
            raise AssertionError("expected RetryableScanError")
        except RetryableScanError:
            pass


def test_process_pr_event_retries_on_clone_timeout():
    with patch("app.services.webhook_service.run_pipeline",
               side_effect=TimeoutError("Clone timed out after 120s.")):
        try:
            process_pr_event(PAYLOAD)
            raise AssertionError("expected RetryableScanError")
        except RetryableScanError as e:
            assert "timed out" in str(e)


def test_process_pr_event_retries_on_transient_clone_runtimeerror():
    with patch("app.services.webhook_service.run_pipeline",
               side_effect=RuntimeError(
                   "git clone failed: fatal: Could not resolve host: github.com")):
        try:
            process_pr_event(PAYLOAD)
            raise AssertionError("expected RetryableScanError")
        except RetryableScanError:
            pass


def test_process_pr_event_permanent_clone_error_does_not_retry():
    with patch("app.services.webhook_service.run_pipeline",
               side_effect=RuntimeError(
                   "git clone failed: Repository not found")):
        process_pr_event(PAYLOAD)  # must not raise


def test_process_pr_event_retries_on_comment_network_error():
    issues = [{"file": "app.py", "line": 999, "severity": "LOW",
               "tool": "python-ast", "message": "elsewhere"}]
    with patch("app.services.webhook_service.run_pipeline", return_value=PIPELINE), \
         patch("app.services.webhook_service.scan_pr_changes",
               return_value={"issues": issues, "total_files": 1}), \
         patch("app.services.webhook_service.get_token_for_repo", return_value="tok"), \
         patch("app.services.webhook_service.post_pr_comment",
               side_effect=requests.ConnectionError("connection refused")):
        try:
            process_pr_event(PAYLOAD)
            raise AssertionError("expected RetryableScanError")
        except RetryableScanError:
            pass


def test_format_scan_comment_all_inline():
    body = format_scan_comment([], 3, inline_count=2, total_issues=2)
    assert "2** issue(s)" in body or "**2** issue(s)" in body
    assert "inline comments" in body
    assert "All findings are attached" in body


def test_format_scan_comment_mixed_inline_and_listed():
    listed = [{"file": "a.py", "line": 1, "message": "m", "severity": "S", "tool": "t"}]
    body = format_scan_comment(listed, 3, inline_count=1, total_issues=3)
    assert "1 of 3" in body
    assert "`a.py:1`" in body


def test_format_scan_comment_no_issues():
    assert "No security issues" in format_scan_comment([], 4)
