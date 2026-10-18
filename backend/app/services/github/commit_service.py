import requests

def get_commits(repo, pr_number, token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    return requests.get(url, headers=headers, timeout=15).json()