from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import analyze, pr_analyze, webhook
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"


def _startup_diagnostics():
    """Print runtime limits once at boot so Render logs show what is active.

    Helps diagnose container-level fork failures (cgroup pids.max, memory)
    without needing shell access to the instance."""
    import shutil
    import sys
    import threading

    print("STARTUP DIAGNOSTICS")
    print(f"  python: {sys.version.split()[0]}  platform: {sys.platform}")
    print(f"  prlimit: {'yes' if shutil.which('prlimit') else 'no'}  unshare: {'yes' if shutil.which('unshare') else 'no'}")
    print(f"  threads: {threading.active_count()}")
    for path in (
        "/proc/self/limits",
        "/sys/fs/cgroup/pids.max",
        "/sys/fs/cgroup/pids/pids.max",
        "/sys/fs/cgroup/memory.max",
    ):
        try:
            with open(path) as f:
                content = f.read().strip()
            if path.endswith("limits"):
                nproc_lines = [ln for ln in content.splitlines() if "processes" in ln]
                print(f"  {path}: {' | '.join(nproc_lines)}")
            else:
                print(f"  {path}: {content}")
        except OSError:
            pass

    from app.services.sandbox import SANDBOX_MAX_PROCS, SANDBOX_MEMORY_MB
    print(f"  sandbox: max_procs={SANDBOX_MAX_PROCS} memory_mb={SANDBOX_MEMORY_MB}")


def _cap_threadpool():
    """Cap anyio's worker-thread pool (default 40) — a 512MB instance never
    needs that many, and every extra thread counts against RLIMIT_NPROC."""
    try:
        from anyio.to_thread import current_default_thread_limiter
        limiter = current_default_thread_limiter()
        limiter.total_tokens = 16
        print(f"STARTUP: anyio threadpool capped at {limiter.total_tokens}")
    except Exception as e:
        print("STARTUP: could not cap anyio threadpool:", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup_diagnostics()
    _cap_threadpool()
    yield


app = FastAPI(title="AI-CodeReview-Assistant", version="1.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-code-review-assistant-nine.vercel.app",
        "http://localhost:5174",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(pr_analyze.router)
app.include_router(webhook.router)

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    from app.services.sandbox import SANDBOX_MAX_PROCS
    from app.db import db_enabled
    return {"status": "ok", "sandbox_max_procs": SANDBOX_MAX_PROCS,
            "database": db_enabled()}
