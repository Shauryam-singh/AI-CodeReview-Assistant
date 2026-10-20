import logging

import requests

logger = logging.getLogger(__name__)

# GitHub caps review comments; keep well under the API limit so one bad
# line cannot fail the whole review.
MAX_INLINE_COMMENTS = 50


def format_inline_body(issue: dict) -> str:
    sev = issue.get("severity", "UNKNOWN")
    tool = issue.get("tool", "?")
    msg = issue.get("message", "Issue detected")
    parts = [f"**{sev}** ({tool})", "", msg]
    if issue.get("risk"):
        parts += ["", f"**Risk:** {issue['risk']}"]
    if issue.get("suggestion"):
        parts += [f"**Suggestion:** {issue['suggestion']}"]
    snippet = (issue.get("code_snippet") or "").strip()
    if snippet:
        parts += ["", "```", snippet[:500], "```"]
    return "\n".join(parts)


def build_review_comments(issues: list, commentable_lines: dict, limit: int = MAX_INLINE_COMMENTS):
    """Split issues into (inline_comments, remaining_issues).

    An issue becomes an inline comment only when its line is present in the
    PR diff (otherwise GitHub rejects the review with 422). Everything else
    is returned so the caller can list it in the review summary instead.
    """
    inline = []
    remaining = []
    for issue in issues:
        path = issue.get("file")
        if isinstance(path, str):
            # scanners may emit OS-native separators; GitHub wants "/"
            path = path.replace("\\", "/")
        line = issue.get("line")
        sides = commentable_lines.get(path)
        if sides and isinstance(line, int) and line > 0:
            if line in sides["RIGHT"]:
                side = "RIGHT"
            elif line in sides["LEFT"]:
                side = "LEFT"
            else:
                side = None
            if side and len(inline) < limit:
                inline.append({
                    "path": path,
                    "line": line,
                    "side": side,
                    "body": format_inline_body(issue),
                })
                continue
        remaining.append(issue)
    return inline, remaining


def post_pr_review(repo_slug: str, pr_number, token: str, body: str, comments: list):
    """Create a COMMENT review with inline comments anchored to the diff.

    Returns (ok, status_code, github_review_id). Falls back to a plain PR
    comment upstream when GitHub rejects the review payload.
    """
    url = f"https://api.github.com/repos/{repo_slug}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"body": body, "event": "COMMENT", "comments": comments}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
    except requests.RequestException as e:
        logger.error("Failed to post PR review: %s", e)
        return False, 0, None
    if r.status_code != 201:
        logger.error("GitHub review error: %s - %s", r.status_code, r.text[:500])
        return False, r.status_code, None
    try:
        github_id = r.json().get("id")
    except ValueError:
        github_id = None
    return True, r.status_code, github_id
