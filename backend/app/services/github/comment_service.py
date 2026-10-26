import logging

import requests

logger = logging.getLogger(__name__)


def find_existing_comment(repo_slug: str, pr_number: str, token: str,
                          marker: str) -> bool:
    """True when a PR issue comment already contains ``marker``."""
    url = f"https://api.github.com/repos/{repo_slug}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        for page in range(1, 21):  # up to 2000 comments; stop early in practice
            r = requests.get(
                url,
                params={"per_page": 100, "page": page},
                headers=headers,
                timeout=15,
            )
            if r.status_code != 200:
                return False
            comments = r.json()
            if any(marker in (comment.get("body") or "") for comment in comments):
                return True
            if len(comments) < 100:
                break
    except (requests.RequestException, ValueError) as e:
        # Best effort: if we cannot check, post rather than silently skip.
        logger.warning("Failed to list existing PR comments: %s", e)
        return False
    return False


def post_pr_comment(repo_slug: str, pr_number: str, token: str, body: str,
                    marker: str | None = None) -> bool:
    """Post a plain PR comment.

    ``marker`` is an HTML comment embedded in the body; when given, an
    existing comment carrying it is reused instead of posting a duplicate.
    """
    if marker:
        if find_existing_comment(repo_slug, pr_number, token, marker):
            logger.info("Comment with marker already exists; skipping")
            return True
        body = f"{marker}\n{body}"

    url = f"https://api.github.com/repos/{repo_slug}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.post(url, json={"body": body}, headers=headers, timeout=15)
    return r.status_code == 201
