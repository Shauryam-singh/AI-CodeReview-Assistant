# 🚀 Automated Code Review Assistant

An automated security-focused code review tool that scans public GitHub repositories for:

- 🔍 Security vulnerabilities (via Semgrep)
- 🐍 Dangerous Python patterns (AST analysis)
- 🔐 Hardcoded secrets & exposed credentials
- ⚠️ Risk classification with explanations

Built with **FastAPI + Python + Semgrep**  
Frontend deployed on **Vercel**  
Backend deployed on **Render**

> **Naming note:** the repository is called `AI-CodeReview-Assistant`, but the current
> webhook pipeline is deterministic static analysis. An optional Gemini review module
> exists behind `LLM_ENABLED=false`, but it is not wired into the webhook path yet
> (see “Optional LLM review” below).

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
- Optional Gemini review module (`LLM_ENABLED=false`; not wired into the webhook yet)
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
- Backend: Render (`render.yaml` blueprint: web service + worker + Redis + Postgres)
- Frontend: Vercel
- Local full stack: Docker Compose (API + worker + Redis + Postgres)

---

# 🏛 Architecture

```
 GitHub PR event (opened / synchronize / reopened)
        │
        │  HMAC-SHA256 signed webhook
        ▼
 FastAPI  POST /webhook/github
        │  verify signature
        │  dedupe X-GitHub-Delivery (unique jobs.delivery_id)
        ▼
 Redis queue (arq)  ── arq job id = delivery id (collapses concurrent redeliveries)
        │
        ▼
 arq worker
        ├─ fetch PR diff + metadata (GitHub API, App installation token)
        ├─ shallow clone into a resource-limited sandbox
        ├─ scan changed files only: Semgrep + Python AST + secret regexes
        ├─ risk-map and rank findings
        ├─ record job / findings / reviews (Postgres, best-effort)
        └─ post an inline PR review (fallback: one summary comment)
                 │
                 ▼
        Postgres: repos · pull_requests · jobs · findings · reviews
```

### Webhook request flow (what runs today)

1. GitHub sends a signed `pull_request` webhook (`opened`, `synchronize`, or `reopened`).
2. FastAPI verifies `X-Hub-Signature-256`, checks `X-GitHub-Delivery`, records a `jobs` row in `queued`, and enqueues an arq job using the delivery id as the arq job id. It returns `202` immediately.
3. The arq worker fetches PR metadata and the diff with the GitHub App installation token, then shallow-clones the repo into the sandbox.
4. It runs **Semgrep + Python AST + secret regexes** on the changed files only.
5. Findings are anchored to diff lines; the worker records `findings`/`reviews` in Postgres and posts one inline PR review. Issues outside the diff are listed in the summary; a rejected review falls back to one plain PR comment.
6. A retry reuses the same job id and marker, so rows are replaced/upserted and GitHub comments are not duplicated.

**The LLM stage is not wired into this flow yet.** `backend/app/services/llm/`
contains an opt-in Gemini review module (`LLM_ENABLED=false` by default) with a
standalone smoke script. The webhook pipeline remains deterministic static analysis.

The `/analyze` and `/analyze-pr` HTTP endpoints use the same scan pipeline
synchronously and return the findings as JSON.

## Design decisions & tradeoffs

- **Async webhook + queue instead of scanning inside the request.** GitHub expects a
  webhook response within ~10 seconds, while a clone + scan can take minutes. The API
  verifies, persists, and enqueues (`202`), and the worker scans. Tradeoff: more moving
  parts (Redis + a worker process), and the worker must be deployed alongside the API.
- **Diff-only scanning for PRs.** Only files changed in the PR are scanned, which keeps
  runs fast and comments relevant. Tradeoff: cross-file/architectural issues that do not
  touch a changed line are missed.
- **GitHub App installation tokens.** Short-lived (1 hour), scoped to the repositories the
  app is installed on, and able to comment as a bot; a personal `GITHUB_TOKEN` is only a
  local-dev fallback. Tradeoff: extra one-time setup (App registration + private key).
- **Delivery-id idempotency at two layers.** `X-GitHub-Delivery` is both a unique DB
  column and the arq job id. The DB check catches redeliveries across worker restarts;
  the queue-level id collapses concurrent redeliveries even before the first row is
  committed. Tradeoff: the DB layer requires `DATABASE_URL`; without it only the
  queue-level window applies.
- **Retry only transient failures.** Network errors/timeouts and GitHub `429`/`5xx` are
  retried with bounded exponential backoff + jitter; auth errors, invalid payloads and
  oversized repos fail once. Exhausted jobs become `dead_letter` rows instead of
  disappearing. Tradeoff: no automatic requeue — recovering a dead letter is a manual
  DB inspection/decision.
- **Retry safety.** A retry replaces the job's `findings` rows, upserts its `reviews`
  row per kind, and embeds `<!-- ai-review:<job_id> -->` (job id = delivery id) in posted
  review/comment bodies. Before posting, the worker lists existing reviews/comments and
  skips when the marker is present, so a timeout that actually succeeded server-side
  cannot produce a duplicate comment.
- **Optional persistence.** `DATABASE_URL` is optional: recording and dedupe are
  best-effort and never break the webhook or the scan. Tradeoff: without a database,
  history and the DB-level dedupe are unavailable.
- **Sandboxed subprocesses.** `git` and `semgrep` run under memory/process/file limits and
  hard timeouts (`prlimit`/`ulimit` on Linux, Job Objects on Windows), with an optional
  network namespace. Tradeoff: conservative limits reject very large or slow repos.

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

Dependencies are pinned to exact versions in `requirements.txt` (and
`requirements-dev.txt` for tests), so installs are reproducible.

> **Note:** Semgrep runs on Linux/macOS/Docker; on native Windows it's skipped automatically via the
> `semgrep==...; sys_platform != "win32"` platform marker (the AST and secret scans still run).

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

The suite covers the AST scanner, secret scanner, risk mapper, scan orchestration,
inline review rendering, webhook signature verification, delivery-id idempotency,
retry/backoff/dead-letter handling, DB recording, mocked GitHub API calls, and the
optional LLM review (mocked Gemini client, redaction, validation, and fail-open
behavior). No network is required.

The real-stack path (Postgres + Redis + worker) is exercised by the Docker smoke test
described below.

---

## Optional LLM review (Phase 1–2)

`backend/app/services/llm/` contains an opt-in Gemini review module:

| File | Purpose |
|---|---|
| `config.py` | Environment settings, defaults and safe parsing |
| `schema.py` | `LLMFinding` / `LLMReview` Pydantic models |
| `prompt.py` | Versioned prompt (`PROMPT_VERSION = "1.0.0"`) |
| `client.py` | Gemini REST client (`responseMimeType: application/json`, timeout, one 429 retry) |
| `review_service.py` | Redaction, validation, filtering, sanitization, fail-open wrapper |

It is **off by default and not wired into the webhook yet**. It returns `[]` when
`LLM_ENABLED=false`, when no `LLM_API_KEY` is set, for private repositories unless
`LLM_ALLOW_PRIVATE_REPOS=true`, or on any request/parse/validation failure. It never
raises `RetryableScanError`, so it cannot fail a webhook job.

Set `LLM_ENABLED=true` and `LLM_API_KEY=...` in the gitignored `.env`, then try it on the
built-in SQL-injection sample (or pass `--diff path/to/file.diff`):

```bash
cd backend
./venv/bin/python scripts/llm_smoke.py
```

The script prints validated findings as JSON. With the feature disabled it prints an
empty result; it never prints the API key. If Gemini is temporarily unavailable for
`gemini-3.8-flash` (HTTP 503), try the free fallback with
`LLM_MODEL=gemini-3.5-flash-lite ./venv/bin/python scripts/llm_smoke.py`.

Safety behavior includes: secret-scanner line hits plus generic token/private-key
redaction before the diff leaves the process, file/line validation against the diff,
low-confidence and style-only filtering, a findings cap, and HTML/@mention/link
sanitization before any output could be posted.

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

### Reliability: idempotency, retries, dead letters

**Idempotency**

- Duplicate deliveries (same `X-GitHub-Delivery` header) are deduplicated at two layers: `jobs.delivery_id` is unique, and the delivery id is used as the arq job id so concurrent redeliveries collapse before a row is committed. Later deliveries get `200 {"status": "duplicate"}` and never re-scan.
- The DB check is best-effort: without `DATABASE_URL`, only the arq-level window applies.

**Failure classification**

| Class | Examples | Handling |
|---|---|---|
| Transient | clone DNS/timeout/reset/network errors; GitHub `429`/`5xx`/network errors when posting | retry with backoff |
| Permanent | invalid payload, missing PR number, auth/installation errors, invalid repo URL, oversized repo | one-shot `failed`/`skipped`; no retry |
| Exhausted | all `WEBHOOK_MAX_TRIES` attempts used | park in `dead_letter` with the last error |

**Backoff**

`delay = min(WEBHOOK_RETRY_BASE_SECONDS * 2^(attempt - 1), WEBHOOK_RETRY_MAX_SECONDS)` with ±20% jitter. Defaults: 5 total attempts, 30 s base, 1 h cap. The worker sets the job to `retrying` and records the attempt/error before raising `Retry(defer=...)`.

**State machine**

```text
queued ──▶ running ──▶ succeeded
                 ├──▶ failed
                 ├──▶ skipped
                 └──▶ retrying ──▶ running
                          └──▶ dead_letter  (attempts exhausted)
```

**Dead letters**

Once attempts are exhausted, the job stays in `jobs` with `status = 'dead_letter'`, the attempt count, and the last error. There is no automatic requeue API; inspect with:

```sql
SELECT id, delivery_id, action, attempts, error, finished_at
FROM jobs
WHERE status = 'dead_letter'
ORDER BY finished_at DESC;
```

**Retry safety**

- A retry replaces the job's `findings` rows and upserts its `reviews` row per `(job_id, kind)` (application-level, with legacy duplicates cleaned up).
- Posted reviews/comments carry `<!-- ai-review:<job_id> -->`; before posting, the worker lists existing reviews/comments and skips if the marker is present. This covers the "timeout but GitHub actually succeeded" case.

### Running the worker

```
cd backend
arq app.worker.WorkerSettings
```

Requires a Redis server (`REDIS_URL`, default `redis://localhost:6379/0`). On Windows use Memurai or WSL; on macOS/Linux `redis-server` works out of the box.

Or run the API, worker, Redis, and Postgres together with Docker Compose (next section).

---

# 🐳 Full Stack with Docker Compose

The repository ships a `docker-compose.yml` with four services:

| Service | Purpose |
|---------|---------|
| `api` | FastAPI; runs `alembic upgrade head` on start, then serves on port `8000` |
| `worker` | `arq app.worker.WorkerSettings`; picks up queued scans |
| `redis` | arq job queue |
| `postgres` | scan history + delivery-id idempotency |

```bash
docker compose up -d --build
docker compose logs -f api worker      # watch it work
```

Run the end-to-end smoke test (builds the stack, verifies the Alembic migration against
real Postgres, sends a signed webhook, waits for the worker to pick the job up, and
checks that a redelivery is deduped):

```bash
./scripts/smoke_test.sh
```

Send a manual signed webhook:

```bash
python3 scripts/send_webhook.py --delivery manual-1 --secret dev-webhook-secret
```

Override defaults (webhook secret, GitHub App credentials, retry limits) with a `.env`
file at the repo root or exported environment variables — see `docker-compose.yml`.

---

# ☁️ Deploying on Render

`render.yaml` is a Render Blueprint that provisions:

- a **web** service running the API (`preDeployCommand` runs `alembic upgrade head`)
- a **worker** service running `arq app.worker.WorkerSettings` — scans do not run without it
- a **Redis** instance (arq queue) and a **Postgres** database, wired in via `REDIS_URL` / `DATABASE_URL`

Background workers have no free tier on Render, so the worker uses the smallest paid
plan; the API/Postgres/Key Value can stay on free tiers for a demo (the free web
service sleeps when idle).

In the Render dashboard: **New → Blueprint**, select this repository, then fill in the
`GITHUB_WEBHOOK_SECRET`, `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and optional
`GITHUB_TOKEN` secrets when prompted. The health check is `GET /health`.

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

### Schema

| Table | Purpose |
|-------|---------|
| `repos` | GitHub repositories seen by the webhook (unique `full_name`) |
| `pull_requests` | PRs, unique per `(repo_id, number)`; title/state/sha captured from the webhook payload |
| `jobs` | arq scan-job lifecycle: `queued → running → succeeded/failed/skipped`, plus `retrying`/`dead_letter` for retried and exhausted jobs; GitHub `delivery_id` (unique, dedupes redeliveries), attempt count, error text and timestamps |
| `findings` | One row per scan issue (file, line, severity, tool, risk, suggestion, snippet); `inlined` marks findings that became an inline review comment |
| `reviews` | Every review/comment posted back to GitHub: kind (`review`/`comment`), GitHub id, HTTP status, inline count, body |

Key columns and constraints:

```text
repos
  id PK · full_name UNIQUE · html_url · created_at · updated_at

pull_requests
  id PK · repo_id FK → repos.id (ON DELETE CASCADE)
  number · title · state · html_url · head_sha · base_sha
  created_at · updated_at
  UNIQUE (repo_id, number)

jobs
  id PK · arq_job_id UNIQUE · delivery_id UNIQUE
  repo_id FK → repos.id (CASCADE) · pull_request_id FK → pull_requests.id (CASCADE)
  action · status · attempts · error
  enqueued_at · started_at · finished_at

findings
  id PK · job_id FK → jobs.id (CASCADE) · pull_request_id FK → pull_requests.id (CASCADE)
  file · line · severity · message · tool · risk · suggestion · code_snippet
  inlined · created_at

reviews
  id PK · pull_request_id FK → pull_requests.id (CASCADE) · job_id FK → jobs.id (CASCADE)
  kind ("review" | "comment") · github_id · status_code · inline_count · body · created_at
```

- `jobs.delivery_id` is the DB-level idempotency key; `jobs.arq_job_id` is also
  unique and is reused across retries.
- Foreign keys use `ON DELETE CASCADE`; `findings.job_id` and `reviews.job_id`
  are nullable for scans recorded without a queued job.
- `reviews` has no DB-level unique constraint on `(job_id, kind)`; the
  application upserts that row and cleans up legacy duplicates during retries.
- Alembic migrations: `0001_initial` creates the tables,
  `0002_webhook_reliability` adds `delivery_id` and `attempts`.

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

## Synchronous endpoints (`/analyze`, `/analyze-pr`)

1. Validate the repo URL against the GitHub allow-list
2. Check repo size via the GitHub API (reject if over limit)
3. Shallow-clone (`--depth 1`) into a temp dir inside a sandboxed subprocess
4. For `/analyze-pr`: parse the PR diff to get the changed file list
5. Run scanners (Semgrep, AST, secret detection) — only on changed files for PRs
6. Aggregate results and return structured JSON
7. Clean up the temp clone

The asynchronous webhook path is documented in
[Webhook request flow](#webhook-request-flow-what-runs-today) above.

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
| `WEBHOOK_MAX_TRIES` | `5` | Attempts per webhook job before it is dead-lettered |
| `WEBHOOK_RETRY_BASE_SECONDS` | `30` | Base delay for exponential retry backoff |
| `WEBHOOK_RETRY_MAX_SECONDS` | `3600` | Cap for the retry backoff delay |
| `DATABASE_URL` | _(unset)_ | PostgreSQL URL; when set, scan history is persisted (see the PostgreSQL section) |
| `LLM_ENABLED` | `false` | Enable the optional Gemini review module |
| `LLM_PROVIDER` | `gemini` | LLM provider (Gemini is implemented) |
| `LLM_API_KEY` | _(empty)_ | Gemini API key; set in the gitignored `.env` only |
| `LLM_MODEL` | `gemini-3.8-flash` | Gemini model name |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-request timeout |
| `LLM_MAX_INPUT_CHARS` | `120000` | Truncate the redacted diff to this size |
| `LLM_MAX_OUTPUT_TOKENS` | `4096` | Gemini output cap |
| `LLM_MAX_FINDINGS` | `10` | Cap after validation/dedupe |
| `LLM_MIN_CONFIDENCE` | `0.6` | Drop findings below this confidence |
| `LLM_ALLOW_PRIVATE_REPOS` | `false` | Allow sending private-repo diffs to Gemini |

For production usage:
- Upgrade to a paid Render instance (the free instance sleeps and has 512MB RAM)
- Or run the Docker Compose stack on any VPS; the API and worker are separate processes
- The async queue/worker architecture is already in place — see the Architecture section

---

# 🔒 Security Note

This tool scans **public repositories only**.  
Private repositories require authentication integration.

**SSRF protection**: repo URLs are validated against a strict `github.com` allow-list before any network call or clone, so the service cannot be used to clone internal or arbitrary hosts.

**Sandboxed execution**: `git` and `semgrep` subprocesses run with resource limits (memory, file size, hard timeouts, process-tree kill). On Linux the limits are enforced via `prlimit`/`ulimit` and optionally a network namespace (`SANDBOX_NO_NETWORK=1`); on Windows via Job Objects — so it works both on Render and on a local PC.

---

# 🚀 Future Improvements

- **Wire the opt-in LLM review into the webhook**: merge/dedupe LLM findings with static
  findings, add Redis caching keyed by `head_sha + prompt version + model`, a daily
  request budget, and a 30–50 PR evaluation; keep graceful degradation to static-only
  results when the provider is unavailable
- **History & metrics**: API + dashboard over the existing `jobs`/`findings`/`reviews`
  tables (per-repo trends, finding counts, scan/review latency)
- **Evaluation harness**: a labelled set of PRs with precision/recall measured with and
  without the LLM step
- **CI**: lint (ruff), type-check (mypy), backend tests, frontend build, and the Docker
  smoke test on every PR
- **Rate limiting** per repository/installation and **structured logging** with request
  and job ids
- **PDF report export**

---

# 👨‍💻 Author

Built with ❤️ Shauryam Singh

---

# 📜 License

MIT License

---
