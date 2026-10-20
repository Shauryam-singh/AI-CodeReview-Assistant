import os
import shutil
import stat
import subprocess
import tempfile
import time
from app.services.limits import (
    CLONE_TIMEOUT_SECONDS,
    MAX_REPO_SIZE_MB,
    RepoTooLargeError,
    dir_size_mb,
    github_repo_size_mb,
)
from app.services.sandbox import sandboxed_run

_FORK_ERROR_MARKERS = (
    "cannot fork",
    "resource temporarily unavailable",
    "fork: ",
    "unable to fork",
    "posix_spawn",
    "vfork",
)


def _is_fork_error(stderr: str) -> bool:
    """True when git failed because the OS refused to create a new process
    (RLIMIT_NPROC, cgroup pids.max, or memory pressure) — not a git error."""
    s = (stderr or "").lower()
    return any(marker in s for marker in _FORK_ERROR_MARKERS)


def _cleanup(path: str):
    # git for Windows marks pack files read-only; rmtree can't delete them
    # unless the attribute is cleared first. Killed clones may also briefly
    # hold locks, so retry a few times before forcing.
    for _ in range(5):
        for root, dirs, files in os.walk(path):
            for name in dirs + files:
                try:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE)
                except OSError:
                    pass
        try:
            shutil.rmtree(path)
            return
        except OSError:
            time.sleep(0.5)
    shutil.rmtree(path, ignore_errors=True)


def clone_repo(repo_url: str):
    try:
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        size_mb = github_repo_size_mb(repo_url)
        if size_mb is not None and size_mb > MAX_REPO_SIZE_MB:
            raise RepoTooLargeError(
                f"Repository is ~{size_mb:.0f}MB which exceeds the {MAX_REPO_SIZE_MB}MB limit."
            )

        temp_dir = tempfile.mkdtemp(prefix="repo_")
        started = time.time()
        try:
            clone_cmd = ["git", "clone", "--depth", "1", "--single-branch", "--", repo_url, temp_dir]
            process = sandboxed_run(
                clone_cmd,
                timeout=CLONE_TIMEOUT_SECONDS,
                network=True,
            )
            if process.returncode != 0 and _is_fork_error(process.stderr):
                # The container refused a fork (cgroup pids / RLIMIT_NPROC /
                # memory). Retry once without resource caps — timeout and
                # tree-kill still apply, so this is not an unbounded risk.
                print(
                    "CLONE: sandbox hit a fork error; retrying without resource limits:",
                    (process.stderr or "").strip()[:200],
                )
                process = sandboxed_run(
                    clone_cmd,
                    timeout=CLONE_TIMEOUT_SECONDS,
                    network=True,
                    limits=False,
                )
            if process.returncode != 0:
                raise RuntimeError(f"git clone failed: {(process.stderr or '').strip()[:300]}")
        except subprocess.TimeoutExpired:
            _cleanup(temp_dir)
            raise TimeoutError(
                f"Clone timed out after {CLONE_TIMEOUT_SECONDS}s. The repository is too large or too slow to clone."
            )
        except Exception:
            _cleanup(temp_dir)
            raise

        print(f"CLONE OK in {time.time() - started:.1f}s")

        used_mb = dir_size_mb(temp_dir)
        if used_mb > MAX_REPO_SIZE_MB:
            _cleanup(temp_dir)
            raise RepoTooLargeError(
                f"Cloned repository is ~{used_mb:.0f}MB which exceeds the {MAX_REPO_SIZE_MB}MB limit."
            )

        return temp_dir

    except RepoTooLargeError:
        raise
    except TimeoutError:
        raise
    except Exception as e:
        print("CLONE ERROR:", e)
        raise
