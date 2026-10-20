from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.limits import RepoTooLargeError

client = TestClient(app)


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "running"}


def test_analyze_rejects_non_github_url():
    r = client.post("/analyze/", json={"repo_url": "https://evil.com/owner/repo"})
    assert r.status_code == 400
    assert "github.com" in r.json()["detail"]


def test_analyze_rejects_bad_scheme():
    r = client.post("/analyze/", json={"repo_url": "file:///etc/passwd"})
    assert r.status_code == 400


def test_analyze_returns_413_for_oversized_repo():
    with patch("app.routes.analyze.clone_repo",
               side_effect=RepoTooLargeError("too big")):
        r = client.post("/analyze/", json={"repo_url": "https://github.com/a/b"})
    assert r.status_code == 413
    assert r.json()["detail"] == "too big"


def test_analyze_returns_504_for_clone_timeout():
    with patch("app.routes.analyze.clone_repo",
               side_effect=TimeoutError("slow")):
        r = client.post("/analyze/", json={"repo_url": "https://github.com/a/b"})
    assert r.status_code == 504
    assert "slow" in r.json()["detail"]


def test_analyze_happy_path_mocked():
    fake_scan = {
        "status": "success",
        "total_files_found": 2,
        "total_files_scanned": 2,
        "issues": [{"file": "app.py", "line": 1, "tool": "python-ast",
                    "severity": "HIGH", "risk": "r", "message": "m"}],
    }
    with patch("app.routes.analyze.clone_repo", return_value="C:\\tmp\\repo"), \
         patch("app.routes.analyze.build_repo_context",
               return_value={"diff": {}, "commits": [], "repo_path": "C:\\tmp\\repo"}), \
         patch("app.routes.analyze.scan_repository", return_value=fake_scan):
        r = client.post("/analyze/", json={"repo_url": "https://github.com/octocat/Spoon-Knife"})

    assert r.status_code == 200
    body = r.json()
    assert body["scan_results"]["total_files_found"] == 2
    assert body["scan_results"]["issues"][0]["tool"] == "python-ast"
    assert body["semgrep"] == []
    assert body["context"]["repo_path"] == "C:\\tmp\\repo"


def test_analyze_pr_rejects_non_github_url():
    r = client.get("/analyze-pr", params={"pr_url": "https://gitlab.com/a/b/-/pull/1"})
    assert r.status_code == 400
    assert "github.com" in r.json()["detail"]


def test_analyze_pr_rejects_url_without_pull_path():
    r = client.get("/analyze-pr", params={"pr_url": "https://github.com/a/b"})
    assert r.status_code == 400
    assert "pull" in r.json()["detail"]


def test_analyze_pr_happy_path_mocked():
    fake_pipeline = {
        "repo_path": "/tmp/repo",
        "metadata": {"title": "Fix bug", "description": "d", "author": "octocat"},
        "context": {"diff": {"app.py": ["+x = 1"]}, "commits": [], "repo_path": "/tmp/repo"},
    }
    fake_scan = {"issues": [{"file": "app.py", "tool": "python-ast"}], "total_files": 1}
    with patch("app.routes.pr_analyze.run_pipeline", return_value=fake_pipeline), \
         patch("app.routes.pr_analyze.scan_pr_changes", return_value=fake_scan):
        r = client.get("/analyze-pr",
                       params={"pr_url": "https://github.com/octocat/Spoon-Knife/pull/41788"})

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["metadata"]["title"] == "Fix bug"
    assert body["total_files_found"] == 1
    assert body["issues"][0]["file"] == "app.py"


def test_analyze_pr_returns_413_for_oversized_repo():
    with patch("app.routes.pr_analyze.run_pipeline",
               side_effect=RepoTooLargeError("repo too large")):
        r = client.get("/analyze-pr",
                       params={"pr_url": "https://github.com/a/b/pull/1"})
    assert r.status_code == 413
    assert r.json()["detail"] == "repo too large"
