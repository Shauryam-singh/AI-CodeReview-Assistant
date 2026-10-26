"""Best-effort persistence for the webhook scan pipeline.

Every helper no-ops when DATABASE_URL is unset and swallows (but logs) its
own errors: a Postgres outage must never break the scan or the webhook.
"""

import logging
from datetime import datetime, timezone

from app.db import db_enabled, session_scope
from app.models.tables import Finding, Job, PullRequest, Repo, Review

logger = logging.getLogger(__name__)

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_RETRYING = "retrying"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_DEAD_LETTER = "dead_letter"

KIND_REVIEW = "review"
KIND_COMMENT = "comment"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _upsert_repo(session, repo_slug: str, html_url: str | None = None) -> Repo:
    repo = session.query(Repo).filter_by(full_name=repo_slug).one_or_none()
    if repo is None:
        repo = Repo(full_name=repo_slug, html_url=html_url)
        session.add(repo)
        session.flush()
    elif html_url:
        repo.html_url = html_url
    return repo


def _upsert_pull_request(session, repo: Repo, pr_number, pr_info: dict | None = None) -> PullRequest:
    number = int(pr_number)
    pr = (
        session.query(PullRequest)
        .filter_by(repo_id=repo.id, number=number)
        .one_or_none()
    )
    if pr is None:
        pr = PullRequest(repo_id=repo.id, number=number)
        session.add(pr)
        session.flush()
    if pr_info:
        pr.title = pr_info.get("title") or pr.title
        pr.state = pr_info.get("state") or pr.state
        pr.html_url = pr_info.get("html_url") or pr.html_url
        head = (pr_info.get("head") or {}).get("sha")
        base = (pr_info.get("base") or {}).get("sha")
        pr.head_sha = head or pr.head_sha
        pr.base_sha = base or pr.base_sha
    return pr


def _resolve(session, repo_slug: str, pr_number, pr_info: dict | None = None):
    repo = _upsert_repo(session, repo_slug)
    pr = _upsert_pull_request(session, repo, pr_number, pr_info)
    return repo, pr


def record_job_queued(arq_job_id: str | None, repo_slug: str, pr_number,
                      action: str | None = None, pr_info: dict | None = None,
                      repo_html_url: str | None = None,
                      delivery_id: str | None = None) -> None:
    if not db_enabled() or not arq_job_id:
        return
    try:
        with session_scope() as session:
            repo, pr = _resolve(session, repo_slug, pr_number, pr_info)
            if repo_html_url:
                repo.html_url = repo_html_url
            existing = session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
            if existing is None:
                session.add(Job(
                    arq_job_id=arq_job_id,
                    delivery_id=delivery_id or None,
                    repo_id=repo.id,
                    pull_request_id=pr.id,
                    action=action,
                    status=STATUS_QUEUED,
                ))
    except Exception as e:
        logger.exception("record_job_queued failed: %s", e)


def is_duplicate_delivery(delivery_id: str | None) -> bool:
    """True when a job was already recorded for this GitHub delivery id."""
    if not db_enabled() or not delivery_id:
        return False
    try:
        with session_scope() as session:
            existing = (
                session.query(Job).filter_by(delivery_id=delivery_id).first()
            )
            return existing is not None
    except Exception as e:
        logger.exception("is_duplicate_delivery failed: %s", e)
        return False


def mark_job_running(arq_job_id: str | None) -> None:
    if not db_enabled() or not arq_job_id:
        return
    try:
        with session_scope() as session:
            job = session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
            if job is not None and job.status in (STATUS_QUEUED, STATUS_RETRYING):
                job.status = STATUS_RUNNING
                if job.started_at is None:
                    job.started_at = _now()
    except Exception as e:
        logger.exception("mark_job_running failed: %s", e)


def record_job_retry(arq_job_id: str | None, attempt: int,
                     error: str | None = None) -> None:
    """Mark a job as waiting for its next retry (transient failure)."""
    if not db_enabled() or not arq_job_id:
        return
    try:
        with session_scope() as session:
            job = session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
            if job is None:
                return
            job.status = STATUS_RETRYING
            job.attempts = attempt
            job.error = (str(error)[:4000] if error else None)
    except Exception as e:
        logger.exception("record_job_retry failed: %s", e)


def finish_job(arq_job_id: str | None, status: str, error: str | None = None) -> None:
    if not db_enabled() or not arq_job_id:
        return
    try:
        with session_scope() as session:
            job = session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
            if job is None:
                return
            job.status = status
            job.error = (str(error)[:4000] if error else None)
            job.finished_at = _now()
            if job.started_at is None:
                job.started_at = job.finished_at
    except Exception as e:
        logger.exception("finish_job failed: %s", e)


def record_findings(arq_job_id: str | None, repo_slug: str, pr_number, issues: list,
                    inline_comments: list, pr_info: dict | None = None) -> None:
    if not db_enabled():
        return
    try:
        with session_scope() as session:
            repo, pr = _resolve(session, repo_slug, pr_number, pr_info)
            job = (
                session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
                if arq_job_id else None
            )
            if job is not None:
                # A retried job rescans and records again; replace the rows
                # from the previous attempt instead of duplicating them.
                session.query(Finding).filter_by(job_id=job.id).delete(
                    synchronize_session=False
                )
            inlined = {
                (c.get("path"), c.get("line"))
                for c in inline_comments
            }
            for issue in issues:
                session.add(Finding(
                    job_id=job.id if job else None,
                    pull_request_id=pr.id,
                    file=str(issue.get("file", "")),
                    line=issue.get("line") if isinstance(issue.get("line"), int) else None,
                    severity=issue.get("severity"),
                    message=str(issue.get("message", "")),
                    tool=issue.get("tool"),
                    risk=issue.get("risk"),
                    suggestion=issue.get("suggestion"),
                    code_snippet=issue.get("code_snippet"),
                    inlined=(issue.get("file"), issue.get("line")) in inlined,
                ))
    except Exception as e:
        logger.exception("record_findings failed: %s", e)


def record_review(arq_job_id: str | None, repo_slug: str, pr_number, kind: str,
                  status_code: int | None, body: str | None, inline_count: int = 0,
                  pr_info: dict | None = None, github_id: int | None = None) -> None:
    if not db_enabled():
        return
    try:
        with session_scope() as session:
            _, pr = _resolve(session, repo_slug, pr_number, pr_info)
            job = (
                session.query(Job).filter_by(arq_job_id=arq_job_id).one_or_none()
                if arq_job_id else None
            )
            existing_rows = (
                session.query(Review)
                .filter_by(job_id=job.id, kind=kind)
                .order_by(Review.id)
                .all()
                if job is not None else []
            )
            if existing_rows:
                # Upsert per (job, kind): a retry must not add a second row,
                # and duplicates left over from older retried jobs are cleaned up.
                existing = existing_rows[0]
                for duplicate in existing_rows[1:]:
                    session.delete(duplicate)
                existing.pull_request_id = pr.id
                existing.github_id = github_id
                existing.status_code = status_code
                existing.inline_count = inline_count
                existing.body = body
                return
            session.add(Review(
                pull_request_id=pr.id,
                job_id=job.id if job else None,
                kind=kind,
                github_id=github_id,
                status_code=status_code,
                inline_count=inline_count,
                body=body,
            ))
    except Exception as e:
        logger.exception("record_review failed: %s", e)
