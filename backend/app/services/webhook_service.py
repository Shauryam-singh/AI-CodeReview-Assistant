import os

from app.services.pipeline_service import run_pipeline
from app.services.existing.scan_service import scan_pr_changes
from app.services.context.diff_parser import parse_commentable_lines
from app.services.github.app_auth import get_token_for_repo, AppAuthError
from app.services.github.comment_service import post_pr_comment
from app.services.github.review_service import build_review_comments, post_pr_review
from app.services.limits import RepoTooLargeError
from app.services.url_validator import validate_github_repo_url, InvalidRepoUrlError

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def format_scan_comment(issues: list, total_files: int, inline_count: int = 0,
                        total_issues: int | None = None) -> str:
    total = len(issues) if total_issues is None else total_issues
    if total == 0:
        return f"✅ No security issues found in {total_files} changed file(s)."
    lines = [
        f"🔍 Found **{total}** issue(s) in {total_files} changed file(s):\n",
    ]
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


def process_pr_event(payload: dict):
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    repo_slug = repo.get("full_name", "")
    pr_number = pr.get("number")

    if not repo_slug or not pr_number:
        print("WEBHOOK: missing repository or PR number in payload")
        return

    print(f"WEBHOOK: scanning {repo_slug}#{pr_number} ...")
    try:
        validate_github_repo_url(f"https://github.com/{repo_slug}")
        repo_full_url = f"https://github.com/{repo_slug}.git"

        pipeline_data = run_pipeline(repo_full_url, repo_slug, str(pr_number), GITHUB_TOKEN)

        context = pipeline_data.get("context", {})
        diff_dict = context.get("diff", {})
        changed_files = list(diff_dict.keys())
        if not changed_files:
            print(f"WEBHOOK: no changed files for {repo_slug}#{pr_number}")
            return

        scan_results = scan_pr_changes(pipeline_data["repo_path"], changed_files)
        issues = scan_results["issues"]

        # GitHub only accepts inline comments on lines that appear in the
        # PR diff, so map the diff hunks first and split the findings.
        commentable = parse_commentable_lines(context.get("diff_text", ""))
        inline, remaining = build_review_comments(issues, commentable)

        # Post via App installation token, fall back to PAT
        token = _get_token(repo_slug)
        if not token:
            print(f"WEBHOOK: no token available to comment on {repo_slug}#{pr_number}")
            return

        if inline:
            body = format_scan_comment(remaining, len(changed_files),
                                       inline_count=len(inline), total_issues=len(issues))
            ok, status = post_pr_review(repo_slug, str(pr_number), token, body, inline)
            if not ok:
                print(f"WEBHOOK: review rejected ({status}), falling back to plain comment")
                ok = post_pr_comment(
                    repo_slug, str(pr_number), token,
                    format_scan_comment(issues, len(changed_files)),
                )
        else:
            ok = post_pr_comment(
                repo_slug, str(pr_number), token,
                format_scan_comment(issues, len(changed_files)),
            )
        print(
            f"WEBHOOK: posted={ok} inline={len(inline)} "
            f"listed={len(remaining)} for {repo_slug}#{pr_number}"
        )

    except (RepoTooLargeError, InvalidRepoUrlError) as e:
        print(f"WEBHOOK: skipped {repo_slug}#{pr_number}: {e}")
    except Exception as e:
        print(f"WEBHOOK: scan failed for {repo_slug}#{pr_number}: {e}")
