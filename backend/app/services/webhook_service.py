import os

import requests

from app.services.context.diff_parser import parse_commentable_lines
from app.services.errors import RetryableScanError
from app.services.existing.scan_service import scan_pr_changes
from app.services.github.app_auth import AppAuthError, get_token_for_repo
from app.services.github.comment_service import post_pr_comment
from app.services.github.review_service import build_review_comments, post_pr_review
from app.services.limits import RepoTooLargeError
from app.services.llm.review_service import review_with_llm
from app.services.llm.schema import LLMFinding
from app.services.merging import merge_findings
from app.services.pipeline_service import run_pipeline
from app.services.recording import (
    KIND_COMMENT,
    KIND_REVIEW,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUCCEEDED,
    finish_job,
    mark_job_running,
    record_findings,
    record_review,
)
from app.services.url_validator import InvalidRepoUrlError, validate_github_repo_url

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# git/network failure signatures worth retrying (clone failures surface as
# RuntimeError with git's stderr, not as ConnectionError).
_TRANSIENT_MARKERS = (
    "could not resolve host",
    "unable to access",
    "connection refused",
    "connection timed out",
    "connection reset",
    "network is unreachable",
    "no route to host",
    "failed to connect",
    "operation timed out",
    "early eof",
    "rpc failed",
    "gnutls",
    "ssl connection",
    "tls handshake",
    "temporary failure in name resolution",
)


def _looks_transient(message: str) -> bool:
    s = (message or "").lower()
    return any(marker in s for marker in _TRANSIENT_MARKERS)


def _is_transient_github_status(status: int | None) -> bool:
    """GitHub API statuses worth retrying: network error (0), 429, 5xx."""
    return status == 0 or status == 429 or (status is not None and status >= 500)


def format_scan_comment(issues: list, total_files: int, inline_count: int = 0,
                        total_issues: int | None = None) -> str:
    total = len(issues) if total_issues is None else total_issues
    if total == 0:
        return f"✅ No issues found in {total_files} changed file(s)."
    has_llm = any(isinstance(i, dict) and i.get("tool") == "llm" for i in issues)
    lines = [
        f"🔍 Found **{total}** issue(s) in {total_files} changed file(s):\n",
    ]
    if has_llm:
        lines.append("⚠️ Some findings are AI-generated; verify before applying.\n")
    if inline_count:
        note = inline_count if inline_count == total else f"{inline_count} of {total}"
        lines.append(f"📍 {note} posted as inline comment(s); the rest are listed below:\n")
        if not issues:
            lines.append("All findings are attached as inline comments on the diff.")
    for i in issues:
        file = i.get("file", "?")
        line = i.get("line", "?")
        msg = i.get("message", "")
        sev = i.get("severity", "?")
        tool = i.get("tool", "?")
        lines.append(f"- `{file}:{line}` — {msg} ({sev}, {tool})")
    return "\n".join(lines)


def _get_token(repo_slug: str) -> str:
    try:
        return get_token_for_repo(repo_slug)
    except AppAuthError:
        return GITHUB_TOKEN


def process_pr_event(payload: dict, job_id: str | None = None):
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    repo_slug = repo.get("full_name", "")
    pr_number = pr.get("number")

    if not repo_slug or not pr_number:
        print("WEBHOOK: missing repository or PR number in payload")
        finish_job(job_id, STATUS_FAILED, "missing repository or PR number in payload")
        return

    print(f"WEBHOOK: scanning {repo_slug}#{pr_number} ...")
    mark_job_running(job_id)
    try:
        validate_github_repo_url(f"https://github.com/{repo_slug}")
        repo_full_url = f"https://github.com/{repo_slug}.git"

        try:
            pipeline_data = run_pipeline(repo_full_url, repo_slug, str(pr_number), GITHUB_TOKEN)
        except (RepoTooLargeError, InvalidRepoUrlError, RetryableScanError):
            raise
        except (TimeoutError, ConnectionError, OSError) as e:
            raise RetryableScanError(str(e)) from e
        except RuntimeError as e:
            # git clone failures are raised as RuntimeError with stderr text;
            # retry only when the message looks like a network problem.
            if _looks_transient(str(e)):
                raise RetryableScanError(str(e)) from e
            raise

        context = pipeline_data.get("context", {})
        diff_dict = context.get("diff", {})
        changed_files = list(diff_dict.keys())
        if not changed_files:
            print(f"WEBHOOK: no changed files for {repo_slug}#{pr_number}")
            finish_job(job_id, STATUS_SKIPPED, "no changed files in PR diff")
            return

        scan_results = scan_pr_changes(pipeline_data["repo_path"], changed_files)
        issues = scan_results["issues"]

        diff_text = context.get("diff_text", "") or ""
        secret_findings = scan_results.get("secret_findings", []) or []

        llm_results = review_with_llm(
            diff_text,
            changed_files,
            repo_slug=repo_slug,
            repo_private=bool((repo or {}).get("private")),
            secret_findings=secret_findings,
        )
        llm_issues = []
        for finding in llm_results:
            if isinstance(finding, LLMFinding):
                llm_issues.append(finding.as_issue())
            elif isinstance(finding, dict):
                llm_issues.append(finding)

        issues = merge_findings(issues, llm_issues)

        # GitHub only accepts inline comments on lines that appear in the
        # PR diff, so map the diff hunks first and split the findings.
        commentable = parse_commentable_lines(diff_text)
        inline, remaining = build_review_comments(issues, commentable)

        record_findings(job_id, repo_slug, pr_number, issues, inline, pr_info=pr)

        # Stable across retries (arq reuses the job id), so a retry that
        # already reached GitHub can detect its own previous review/comment.
        marker = f"<!-- ai-review:{job_id} -->" if job_id else None

        # Post via App installation token, fall back to PAT
        token = _get_token(repo_slug)
        if not token:
            print(f"WEBHOOK: no token available to comment on {repo_slug}#{pr_number}")
            finish_job(job_id, STATUS_SKIPPED, "no token available to post comments")
            return

        if inline:
            body = format_scan_comment(remaining, len(changed_files),
                                       inline_count=len(inline), total_issues=len(issues))
            ok, status, github_id = post_pr_review(
                repo_slug, str(pr_number), token, body, inline, marker=marker
            )
            record_review(job_id, repo_slug, pr_number, KIND_REVIEW, status, body,
                          inline_count=len(inline), pr_info=pr, github_id=github_id)
            if not ok:
                if _is_transient_github_status(status):
                    # Rate limit / server error / network: retry the whole job
                    # rather than falling back (the fallback would likely fail
                    # the same way and burn the delivery for good).
                    raise RetryableScanError(
                        f"GitHub review post failed with status {status}"
                    )
                print(f"WEBHOOK: review rejected ({status}), falling back to plain comment")
                fallback = format_scan_comment(issues, len(changed_files))
                ok = _post_comment_or_raise(
                    repo_slug, pr_number, token, fallback, marker=marker
                )
                record_review(job_id, repo_slug, pr_number, KIND_COMMENT,
                              201 if ok else None, fallback, pr_info=pr)
        else:
            body = format_scan_comment(issues, len(changed_files))
            ok = _post_comment_or_raise(repo_slug, pr_number, token, body, marker=marker)
            record_review(job_id, repo_slug, pr_number, KIND_COMMENT,
                          201 if ok else None, body, pr_info=pr)
        print(
            f"WEBHOOK: posted={ok} inline={len(inline)} "
            f"listed={len(remaining)} for {repo_slug}#{pr_number}"
        )
        if ok:
            finish_job(job_id, STATUS_SUCCEEDED)
        else:
            finish_job(job_id, STATUS_FAILED, "failed to post comment to GitHub")

    except RetryableScanError:
        # Propagate to the arq worker, which retries with backoff (and
        # dead-letters the job once the attempts are exhausted).
        raise
    except (RepoTooLargeError, InvalidRepoUrlError) as e:
        print(f"WEBHOOK: skipped {repo_slug}#{pr_number}: {e}")
        finish_job(job_id, STATUS_SKIPPED, str(e))
    except Exception as e:
        print(f"WEBHOOK: scan failed for {repo_slug}#{pr_number}: {e}")
        finish_job(job_id, STATUS_FAILED, str(e))


def _post_comment_or_raise(repo_slug: str, pr_number, token: str, body: str,
                           marker: str | None = None) -> bool:
    """Plain PR comment; network errors become RetryableScanError."""
    try:
        return post_pr_comment(repo_slug, str(pr_number), token, body, marker=marker)
    except requests.RequestException as e:
        raise RetryableScanError(f"GitHub comment post failed: {e}") from e
