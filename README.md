# AI Code Review Assistant

Automated security-focused code review for GitHub PRs. Runs Semgrep, Python AST checks, and secret scanning; optionally adds Gemini-powered findings. Posts inline PR comments via GitHub App.

**Live:** [Frontend](https://ai-code-review-assistant-nine.vercel.app) | [API](https://ai-codereview-assistant.onrender.com)

## Features
- **PR scanning**: Only changed files scanned from diff
- **Detectors**: Semgrep rules, Python AST (`eval`/`exec`), regex secret scanning
- **GitHub App webhook**: Async via Redis/arq, inline comments, idempotent retries
- **Persistence**: Postgres tracks repos/PRs/jobs/findings/reviews
- **Sandboxing**: Resource limits on git/semgrep (Linux prlimit/Job Objects on Windows)
- **Optional LLM**: Gemini findings merged with static results, cached in Redis, fail-open

## Quick Start (local)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # configure
uvicorn app.main:app --reload

# Worker (separate terminal)
arq app.worker.WorkerSettings

# Full stack
docker compose up -d --build
```

## API
- `GET /` - health
- `POST /analyze/` - scan repo URL
- `GET /analyze-pr?pr_url=...` - scan PR files
- `POST /webhook/github` - GitHub App webhook (HMAC verified)

## LLM Setup (optional)
Add to `.env`:
```env
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_API_KEY=your_key
LLM_MODEL=gemini-3.5-flash-lite  # fallback if 3.8-flash busy
LLM_CACHE_TTL_SECONDS=604800
```

Test: `cd backend && ./venv/bin/python scripts/llm_smoke.py`

## Using Google Gemini to analyze codebase/PRs better

### Get API key
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create API key, add to `.env` as `LLM_API_KEY`

### Improve detection
- **Prompt tuning**: Edit `backend/app/services/llm/prompt.py`, bump `PROMPT_VERSION` on changes
- **Model selection**: Try `gemini-2.5-flash`, `gemini-2.5-pro` for deeper analysis (watch rate limits/cost)
- **Context**: Pass more files via custom script or extend `review_with_llm` to include related files
- **Caching**: Already cached by `provider:model:prompt_version:head_sha` (7-day TTL)
- **Evaluation**: Use `eval/` scripts to measure precision/recall on labelled cases

### Tips
- Keep `LLM_MIN_CONFIDENCE=0.6` to reduce noise
- Enable only on PRs you care about; private repos blocked by default
- Use the smoke script on diffs before enabling in webhook
- Monitor logs for `cache_hit/miss`, latency, model

## Testing
```bash
cd backend && pytest tests -v
```

## Deploy
- **Render**: Use `render.yaml` (API + worker + Redis + Postgres)
- **Vercel**: Frontend deploys separately

## License
MIT
