import requests

def get_pr(repo, pr_number, token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    return requests.get(url, headers=headers, timeout=15).json()