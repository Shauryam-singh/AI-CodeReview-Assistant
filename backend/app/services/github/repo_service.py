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
            process = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", "--", repo_url, temp_dir],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=CLONE_TIMEOUT_SECONDS,
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
