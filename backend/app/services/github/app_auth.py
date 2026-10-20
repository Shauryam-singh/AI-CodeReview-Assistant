import os
import time

import jwt
import requests

APP_ID = os.getenv("GITHUB_APP_ID", "")
PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY", "")


class AppAuthError(Exception):
    pass


def _private_key() -> str:
    key = PRIVATE_KEY.replace("\\n", "\n") if "\\n" in PRIVATE_KEY else PRIVATE_KEY
    return key.strip()


def generate_jwt() -> str:
    if not APP_ID or not _private_key():
        raise AppAuthError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY must be set.")
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": APP_ID,
    }
    return jwt.encode(payload, _private_key(), algorithm="RS256")


def get_installation_id(repo_slug: str) -> int | None:
    token = generate_jwt()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.get(
        f"https://api.github.com/repos/{repo_slug}/installation",
        headers=headers,
        timeout=10,
    )
    if r.status_code == 200:
        return r.json().get("id")
    return None


def get_installation_token(installation_id: int) -> str | None:
    token = generate_jwt()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
        timeout=10,
    )
    if r.status_code == 201:
        return r.json().get("token")
    return None


def get_token_for_repo(repo_slug: str) -> str:
    """Return an installation token for the repo, or raise AppAuthError."""
    inst_id = get_installation_id(repo_slug)
    if inst_id is None:
        raise AppAuthError(f"No installation found for {repo_slug}.")
    token = get_installation_token(inst_id)
    if token is None:
        raise AppAuthError(f"Failed to get installation token for {repo_slug}.")
    return token
