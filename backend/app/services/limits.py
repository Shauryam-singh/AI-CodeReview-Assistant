import os
import re
import requests

MAX_REPO_SIZE_MB = int(os.getenv("MAX_REPO_SIZE_MB", "200"))
CLONE_TIMEOUT_SECONDS = int(os.getenv("CLONE_TIMEOUT_SECONDS", "120"))
MAX_SCAN_FILES = int(os.getenv("MAX_SCAN_FILES", "3000"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "2"))
SCAN_TIME_BUDGET_SECONDS = int(os.getenv("SCAN_TIME_BUDGET_SECONDS", "300"))

MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class RepoTooLargeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def parse_repo_slug(repo_url: str):
    match = re.search(r"github\.com/([^/]+)/([^/#?]+?)(?:\.git)?(?:/|$)", repo_url)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def github_repo_size_mb(repo_url: str, token: str = ""):
    """GitHub API 'size' field is in KB. Returns None when unknown (rate limit, no network)."""
    slug = parse_repo_slug(repo_url)
    if not slug:
        return None
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"token {token}"
        response = requests.get(f"https://api.github.com/repos/{slug}", headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        size_kb = response.json().get("size")
        return None if size_kb is None else size_kb / 1024
    except Exception:
        return None


def dir_size_mb(path: str) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total / (1024 * 1024)


def budget_exceeded(started_at: float) -> bool:
    import time
    return (time.time() - started_at) > SCAN_TIME_BUDGET_SECONDS
