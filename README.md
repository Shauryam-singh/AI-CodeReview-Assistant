# 🚀 AI Code Review Assistant

An automated security-focused code review tool that scans public GitHub repositories for:

- 🔍 Security vulnerabilities (via Semgrep)
- 🐍 Dangerous Python patterns (AST analysis)
- 🔐 Hardcoded secrets & exposed credentials
- ⚠️ Risk classification with explanations

Built with **FastAPI + Python + Semgrep**  
Frontend deployed on **Vercel**  
Backend deployed on **Render**

---

## 🌐 Live Demo

Frontend:  
https://ai-code-review-assistant-nine.vercel.app

Backend API:  
https://ai-codereview-assistant.onrender.com

---

# ✨ Features

### 🔎 Repository Analysis
- Clone public GitHub repositories (shallow `--depth 1`)
- Scan entire project structure or only the files changed in a PR
- Count total files scanned

### 🛡 Security Scanning
- Semgrep rule-based vulnerability detection (skipped automatically on native Windows)
- Python AST dangerous call detection (`eval`, `exec`)
- Regex-based secret detection (AWS keys, private keys, API tokens)

### 🛡 Input Validation & Abuse Protection
- **URL allow-list**: only `github.com` repo URLs are accepted (blocks SSRF to internal hosts, `file://`, `ssh://`, etc.)
- **Repo size limiter**: repos larger than `MAX_REPO_SIZE_MB` are rejected with `413` before or after clone
- **Clone timeout**: clones slower than `CLONE_TIMEOUT_SECONDS` are killed and returned as `504`
- **Scan caps**: file-count, per-file-size and wall-clock budget limits prevent runaway scans

### 🔒 Sandboxed Subprocesses
`git` and `semgrep` run in a resource-limited sandbox:
- **Linux (Render)**: `prlimit`/`ulimit` caps (memory, file size, processes), optional network namespace (`SANDBOX_NO_NETWORK=1`)
- **Windows (PC)**: Job Objects with memory/process caps
- Hard wall-clock timeout with process-**tree** kill on both platforms

### 🤖 GitHub App Webhook + Job Queue
- `POST /webhook/github` with `X-Hub-Signature-256` HMAC verification (constant-time)
- PR events (`opened`/`synchronize`/`reopened`) are enqueued to **Redis via arq**; the endpoint returns `202` immediately
- An `arq` worker fetches the PR diff from the GitHub API, scans **only the changed files**, and posts the findings as an **inline PR review** (one comment per issue, anchored to the exact diff line) using the GitHub App installation token. Issues on lines outside the diff are listed in the review summary; if the review is rejected, it falls back to a single plain PR comment

### 📊 Intelligent Risk Mapping
Each issue includes:
- File name
- Line number
- Severity
- Risk explanation
- Suggested fix

---

# 🏗 Tech Stack

## Backend
- FastAPI
- Uvicorn
- Semgrep (Linux/macOS only)
- Python AST
- Regex secret scanning
- `subprocess` + OS sandbox (Job Objects / prlimit)
- Redis + arq (webhook job queue)
- PyJWT (GitHub App authentication)
- PostgreSQL + SQLAlchemy 2.0 (scan history: repos, PRs, jobs, findings, reviews)
- Alembic (schema migrations)

## Frontend
- React
- TypeScript
- Vite
- Deployed on Vercel

## Deployment
- Backend: Render
- Frontend: Vercel

---

# ⚙️ Backend Setup (Local Development)

## 1️⃣ Clone the repository

```bash
git clone https://github.com/Shauryam-singh/AI-CodeReview-Assistant.git
cd AI-CodeReview-Assistant/backend
```

---

## 2️⃣ Create virtual environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

To run tests, also install the dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Make sure `requirements.txt` includes:

```
fastapi
uvicorn
semgrep; sys_platform != "win32"
```

> **Note:** Semgrep runs on Linux/macOS/Docker; on native Windows it's skipped automatically (the AST and secret scans still run).

---

## 4️⃣ Run the server

```bash
uvicorn app.main:app --reload
```

Server will start at:

```
http://127.0.0.1:8000
```

Swagger docs:

```
http://127.0.0.1:8000/docs
```

---

# ✅ Running Tests

```bash
cd backend
pytest tests -v
```

The suite covers the AST scanner, secret scanner, risk mapper, scan orchestration, and mocked API endpoint tests (no network required).

---

# 📡 API Endpoints

## Root
```
GET /
```

Response:
```json
{
  "status": "running"
}
```

---

## Analyze Repository

```
POST /analyze/
```

### Request Body:
```json
{
  "repo_url": "https://github.com/user/repository"
}
```

Only `github.com` repository URLs are accepted. Invalid URLs return `400`.

### Response:
```json
{
  "scan_results": {
    "status": "success",
    "total_files_found": 120,
    "total_files_scanned": 120,
    "issues": [
      {
        "file": "app.py",
        "line": 45,
        "message": "Dangerous function 'eval' can lead to Remote Code Execution.",
        "severity": "HIGH",
        "risk": "Remote code execution vulnerability.",
        "tool": "python-ast",
        "suggestion": "Avoid dangerous dynamic execution."
      }
    ]
  },
  "semgrep": [],
  "context": {}
}
```

### Error Codes:
| Code | Meaning |
|------|---------|
| `400` | Invalid or non-GitHub URL |
| `413` | Repository exceeds `MAX_REPO_SIZE_MB` |
| `504` | Clone timed out |
| `500` | Unexpected server error |

---

## Analyze PR

```
GET /analyze-pr?pr_url=https://github.com/owner/repo/pull/<number>
```

Scans **only the files changed in the PR**. Returns `400` for invalid PR URLs, `413` for oversized repos, `504` for clone timeouts.

---

## GitHub App Webhook

```
POST /webhook/github
```

Receives GitHub App events. Every request must carry a valid `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with `GITHUB_WEBHOOK_SECRET`); invalid or missing signatures return `401`, and an unconfigured secret returns `503`.

- `ping` → `{"status": "pong"}`
- `pull_request` with action `opened` / `synchronize` / `reopened` → job enqueued to Redis (arq); responds `202` with a `job_id`. A worker picks it up, fetches the PR diff via the GitHub API (`Accept: application/vnd.github.v3.diff`), scans only the changed files, and posts a `COMMENT` review with inline comments on the exact diff lines (plus a summary listing anything that could not be anchored). Auth uses the App installation token, falling back to `GITHUB_TOKEN`; if the review API rejects the payload the worker falls back to a plain PR comment
- Other events → acknowledged and ignored

The endpoint responds immediately; scanning happens in the worker. If Redis is unreachable the endpoint returns `503` (GitHub will retry the delivery).

### Running the worker

```
cd backend
arq app.worker.WorkerSettings
```

Requires a Redis server (`REDIS_URL`, default `redis://localhost:6379/0`). On Windows use Memurai or WSL; on macOS/Linux `redis-server` works out of the box.

### GitHub App registration (manual, once)

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set **Webhook URL** to `https://<your-backend-host>/webhook/github`
3. Set **Webhook secret** to a strong random value: `python -c "import secrets; print(secrets.token_hex(32))"`
4. Grant repository permissions: **Contents: Read-only**, **Pull requests: Read & write** (to post comments), **Metadata: Read-only**
5. Subscribe to events: **Pull requests**
6. Create the app, note the **App ID**
7. Under **Generate a private key**, download the `.pem` file
8. Install the app on the target repositories
9. Configure backend env vars (see `backend/.env.example`):

```
GITHUB_WEBHOOK_SECRET=<same secret as step 3>
GITHUB_APP_ID=<App ID from step 6>
GITHUB_APP_PRIVATE_KEY=<PEM contents, newlines escaped as \n>
```

---

# 🗄 PostgreSQL + SQLAlchemy + Alembic

Scan history is persisted to PostgreSQL with **SQLAlchemy 2.0** and migrated with **Alembic**. Persistence is **optional**: when `DATABASE_URL` is unset the app and webhook worker run exactly as before and recording is skipped (no-op).

### Tables

| Table | Purpose |
|-------|---------|
| `repos` | GitHub repositories seen by the webhook (unique `full_name`) |
| `pull_requests` | PRs, unique per `(repo_id, number)`; title/state/sha captured from the webhook payload |
| `jobs` | arq scan-job lifecycle: `queued → running → succeeded/failed/skipped`, with error text and timestamps |
| `findings` | One row per scan issue (file, line, severity, tool, risk, suggestion, snippet); `inlined` marks findings that became an inline review comment |
| `reviews` | Every review/comment posted back to GitHub: kind (`review`/`comment`), GitHub id, HTTP status, inline count, body |

### Setup

```bash
cd backend
pip install -r requirements.txt          # includes sqlalchemy, psycopg, alembic
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
alembic upgrade head                     # apply migrations
```

- Render-style `postgres://` URLs are normalized automatically (routed through psycopg 3)
- `GET /health` reports `"database": true/false`
- After changing models in `app/models/tables.py`:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Recording is best-effort: a Postgres outage is logged but never breaks the scan or the webhook response.

---

# 🧠 How It Works

1. Validate the repo URL against the GitHub allow-list
2. Check repo size via the GitHub API (reject if over limit)
3. Shallow-clone (`--depth 1`) into a temp dir inside a sandboxed subprocess
4. For `/analyze-pr`: parse the PR diff to get the changed file list
5. Run scanners (Semgrep, AST, secret detection) — only on changed files for PRs
6. Aggregate results and return structured JSON
7. Clean up the temp clone

---

# ⚠️ Limitations (Free Hosting)

If deployed on **Render Free Plan**:
- 512MB RAM limit
- Repositories are limited to 200MB (clone size) with a 120s clone timeout; larger/slower repos are rejected with HTTP 413/504 instead of crashing the instance
- Scans are capped (max 3000 files, max 2MB per file, 300s scan budget)
- Semgrep can be resource intensive

Limits are configurable via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_REPO_SIZE_MB` | `200` | Reject repos larger than this |
| `CLONE_TIMEOUT_SECONDS` | `120` | Kill clones that take longer |
| `MAX_SCAN_FILES` | `3000` | Cap files scanned per run |
| `MAX_FILE_SIZE_MB` | `2` | Skip files larger than this |
| `SCAN_TIME_BUDGET_SECONDS` | `300` | Total wall-clock budget for all scanners |
| `SANDBOX_MEMORY_MB` | `1024` | Memory cap for git/semgrep subprocesses |
| `SANDBOX_MAX_PROCS` | `256` | Process/thread cap for sandboxed subprocesses (RLIMIT_NPROC counts threads) |
| `SANDBOX_NO_NETWORK` | `0` | Set `1` to block network in sandbox (Linux only) |
| `GITHUB_TOKEN` | _(empty)_ | Optional; raises GitHub API rate limits |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for the arq webhook job queue |
| `DATABASE_URL` | _(unset)_ | PostgreSQL URL; when set, scan history is persisted (see the PostgreSQL section) |

For production usage:
- Upgrade to Render Starter plan
- Or move to background job architecture

---

# 🔒 Security Note

This tool scans **public repositories only**.  
Private repositories require authentication integration.

**SSRF protection**: repo URLs are validated against a strict `github.com` allow-list before any network call or clone, so the service cannot be used to clone internal or arbitrary hosts.

**Sandboxed execution**: `git` and `semgrep` subprocesses run with resource limits (memory, file size, hard timeouts, process-tree kill). On Linux the limits are enforced via `prlimit`/`ulimit` and optionally a network namespace (`SANDBOX_NO_NETWORK=1`); on Windows via Job Objects — so it works both on Render and on a local PC.

---

# 🚀 Future Improvements

- Background job processing
- GitHub OAuth integration
- PR auto-commenting
- PDF report export
- Severity score calculation
- Async scanning

---

# 👨‍💻 Author

Built with ❤️ Shauryam Singh

---

# 📜 License

MIT License

---
