import re

ALLOWED_HOSTS = ("github.com", "www.github.com")


class InvalidRepoUrlError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_github_repo_url(repo_url: str) -> str:
    if not repo_url or not repo_url.strip():
        raise InvalidRepoUrlError("Repository URL is required.")

    url = repo_url.strip()
    # Accept bare github.com/owner/repo
    if re.match(r"^github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/|$|\?|#)", url, re.I):
        host = "github.com"
        path = "/" + re.sub(r"^github\.com/", "", url, flags=re.I)
    elif not (url.startswith("http://") or url.startswith("https://")):
        raise InvalidRepoUrlError("Repository URL must start with http:// or https://.")
    else:
        m = re.match(r"https?://([^/]+)(/.*)?$", url)
        if not m:
            raise InvalidRepoUrlError("Invalid repository URL format.")
        host = m.group(1).lower()
        path = m.group(2) or "/"

    if host not in ALLOWED_HOSTS:
        raise InvalidRepoUrlError("Only GitHub repositories (github.com) are allowed.")

    # Must be a repo path: owner/repo with optional .git and trailing slashes
    # Also reject deep paths like /owner/repo/issues/...
    repo_match = re.match(r"/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)", path)
    if not repo_match:
        raise InvalidRepoUrlError(
            "Repository URL must be of the form https://github.com/owner/repo"
        )

    owner, repo = repo_match.group(1), repo_match.group(2)
    if not owner or not repo:
        raise InvalidRepoUrlError("Invalid owner or repository name.")

    # Disallow query/fragment at repo root? GitHub clones need no query/fragment.
    # If they exist beyond repo, reject.
    if "?" in path or "#" in path:
        # allow only if at end? easier to rebuild clean URL
        clean_path = re.sub(r"[?#].*$", "", path)
        repo_match = re.match(r"/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)", clean_path)
        if not repo_match:
            raise InvalidRepoUrlError("Invalid repository URL.")

    # Return canonical https URL
    canonical = f"https://{ALLOWED_HOSTS[0]}/{owner}/{repo}.git"
    return canonical
