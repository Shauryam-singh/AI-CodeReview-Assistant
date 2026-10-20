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
| `SANDBOX_MAX_PROCS` | `64` | Process cap for sandboxed subprocesses |
| `SANDBOX_NO_NETWORK` | `0` | Set `1` to block network in sandbox (Linux only) |
| `GITHUB_TOKEN` | _(empty)_ | Optional; raises GitHub API rate limits |

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
