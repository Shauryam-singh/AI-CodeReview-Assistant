import tempfile
from git import Repo

def clone_repo(repo_url: str):
    path = tempfile.mkdtemp()
    Repo.clone_from(repo_url, path)
    return path