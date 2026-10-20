import os

from app.services.pipeline_service import run_pipeline
from app.services.existing.scan_service import scan_pr_changes
from app.services.github.app_auth import get_token_for_repo, AppAuthError
from app.services.github.comment_service import post_pr_comment
from app.services.limits import RepoTooLargeError
from app.services.url_validator import validate_github_repo_url, InvalidRepoUrlError

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def format_scan_comment(issues: list, total_files: int) -> str:
    if not issues:
        return f"✅ No security issues found in {total_files} changed file(s)."
    lines = [
        f"🔍 Found **{len(issues)}** issue(s) in {total_files} changed file(s):\n",
    ]
    for i in issues:
        file = i.get("file", "?")
        line = i.get("line", "?")
        msg = i.get("message", "")
        sev = i.get("severity", "?")
        tool = i.get("tool", "?")
        lines.append(f"- `{file}:{line}` — {msg} ({sev}, {tool})")
    return "\n".join(lines)


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

        diff_dict = pipeline_data.get("context", {}).get("diff", {})
        changed_files = list(diff_dict.keys())
        if not changed_files:
            print(f"WEBHOOK: no changed files for {repo_slug}#{pr_number}")
            return

        scan_results = scan_pr_changes(pipeline_data["repo_path"], changed_files)
        comment = format_scan_comment(scan_results["issues"], len(changed_files))

        # Post via App installation token, fall back to PAT
        try:
            token = get_token_for_repo(repo_slug)
        except AppAuthError:
            token = GITHUB_TOKEN
        if not token:
            print(f"WEBHOOK: no token available to comment on {repo_slug}#{pr_number}")
            return
        ok = post_pr_comment(repo_slug, str(pr_number), token, comment)
        print(f"WEBHOOK: comment posted={ok} for {repo_slug}#{pr_number}")

    except (RepoTooLargeError, InvalidRepoUrlError) as e:
        print(f"WEBHOOK: skipped {repo_slug}#{pr_number}: {e}")
    except Exception as e:
        print(f"WEBHOOK: scan failed for {repo_slug}#{pr_number}: {e}")
