import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from app.services.github.repo_service import _is_fork_error, clone_repo


def test_is_fork_error_markers():
    assert _is_fork_error("error: cannot fork() for remote-https: Resource temporarily unavailable")
    assert _is_fork_error("fork: Resource temporarily unavailable")
    assert _is_fork_error("unable to fork")
    assert _is_fork_error("posix_spawn error")
    assert _is_fork_error("fatal: unable to fork")
    assert not _is_fork_error("remote: Repository not found")
    assert not _is_fork_error("")
    assert not _is_fork_error(None)


def test_clone_retries_without_limits_on_fork_failure(monkeypatch, tmp_path):
    calls = []

    def fake_sandboxed_run(cmd, timeout, cwd=None, network=True, limits=True):
        calls.append(limits)
        if limits:
            return subprocess.CompletedProcess(
                cmd, 128, "",
                "error: cannot fork() for remote-https: Resource temporarily unavailable",
            )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("app.services.github.repo_service.sandboxed_run", fake_sandboxed_run)
    with patch("app.services.github.repo_service.github_repo_size_mb", return_value=1), \
         patch("app.services.github.repo_service.tempfile.mkdtemp", return_value=str(tmp_path)), \
         patch("app.services.github.repo_service.dir_size_mb", return_value=1):
        result = clone_repo("https://github.com/a/b")

    assert result == str(tmp_path)
    assert calls == [True, False]


def test_clone_does_not_retry_on_non_fork_failure(monkeypatch, tmp_path):
    calls = []

    def fake_sandboxed_run(cmd, timeout, cwd=None, network=True, limits=True):
        calls.append(limits)
        return subprocess.CompletedProcess(cmd, 128, "", "remote: Repository not found")

    monkeypatch.setattr("app.services.github.repo_service.sandboxed_run", fake_sandboxed_run)
    with patch("app.services.github.repo_service.github_repo_size_mb", return_value=1), \
         patch("app.services.github.repo_service.tempfile.mkdtemp", return_value=str(tmp_path)):
        try:
            clone_repo("https://github.com/a/b")
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "Repository not found" in str(e)

    assert calls == [True]


def test_clone_raises_if_retry_also_fails(monkeypatch, tmp_path):
    def fake_sandboxed_run(cmd, timeout, cwd=None, network=True, limits=True):
        return subprocess.CompletedProcess(
            cmd, 128, "", "error: cannot fork() for remote-https: Resource temporarily unavailable"
        )

    monkeypatch.setattr("app.services.github.repo_service.sandboxed_run", fake_sandboxed_run)
    with patch("app.services.github.repo_service.github_repo_size_mb", return_value=1), \
         patch("app.services.github.repo_service.tempfile.mkdtemp", return_value=str(tmp_path)), \
         patch("app.services.github.repo_service._cleanup"):
        try:
            clone_repo("https://github.com/a/b")
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "cannot fork" in str(e)


def test_sandboxed_run_respects_limits_flag(monkeypatch, tmp_path):
    """limits=False must invoke git directly (no prlimit/ulimit wrapper)."""
    import sys
    if sys.platform == "win32":
        return  # wrapper-building is Linux-only

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(
            pid=1, returncode=0,
            communicate=lambda timeout=None: ("", ""),
            kill=lambda: None,
        )

    monkeypatch.setattr("app.services.sandbox.subprocess.Popen", fake_popen)
    monkeypatch.setattr("app.services.sandbox.shutil.which", lambda name: "/usr/bin/" + name)

    from app.services.sandbox import sandboxed_run

    sandboxed_run(["git", "version"], timeout=5, network=True, limits=False)
    assert captured["cmd"][0] == "git"

    sandboxed_run(["git", "version"], timeout=5, network=True, limits=True)
    assert captured["cmd"][0] in ("prlimit", "sh", "unshare")
