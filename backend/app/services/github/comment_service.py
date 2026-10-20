import requests


def post_pr_comment(repo_slug: str, pr_number: str, token: str, body: str) -> bool:
    url = f"https://api.github.com/repos/{repo_slug}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.post(url, json={"body": body}, headers=headers, timeout=15)
    return r.status_code == 201
