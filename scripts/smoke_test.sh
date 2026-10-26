#!/usr/bin/env bash
# End-to-end smoke test against the real stack (Postgres + Redis + API + worker).
#
#   docker compose up -d --build
#   ./scripts/smoke_test.sh
#
# Verifies:
#   1. the Alembic migration applied against real Postgres
#   2. a signed webhook is accepted (202) and recorded in Postgres
#   3. the arq worker picks the job up (status leaves "queued")
#   4. a redelivery with the same X-GitHub-Delivery is deduped (200, one row)

set -euo pipefail

cd "$(dirname "$0")/.."

SECRET="${GITHUB_WEBHOOK_SECRET:-dev-webhook-secret}"
BASE_URL="${BASE_URL:-http://localhost:8000}"
DELIVERY="smoke-$(date +%s)"
COMPOSE=(docker compose)

log() { printf '\n[smoke] %s\n' "$*"; }

on_error() {
  log "FAILED — recent API/worker logs:"
  "${COMPOSE[@]}" logs --tail=80 api worker || true
}
trap on_error ERR

sql() {
  "${COMPOSE[@]}" exec -T postgres \
    psql -U postgres -d ai_code_review -tAc "$1" | tr -d '[:space:]'
}

json_get() {
  python3 -c "import json,sys; print(json.load(sys.stdin)$1)"
}

log "building and starting the stack (api, worker, redis, postgres)"
"${COMPOSE[@]}" up -d --build --wait --wait-timeout 240

log "waiting for API health"
for _ in $(seq 1 60); do
  curl -fsS "$BASE_URL/health" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS "$BASE_URL/health" || { log "API is not healthy"; exit 1; }
printf '\n'

log "checking the Alembic revision against Postgres"
CURRENT=$("${COMPOSE[@]}" exec -T api alembic current 2>/dev/null | tr -d '\r')
printf '%s\n' "$CURRENT"
printf '%s' "$CURRENT" | grep -q "0002_webhook_reliability" \
  || { log "migration 0002_webhook_reliability is not applied"; exit 1; }

log "sending signed webhook (delivery=$DELIVERY)"
RESP=$(python3 scripts/send_webhook.py \
  --url "$BASE_URL" --delivery "$DELIVERY" --secret "$SECRET")
printf '%s\n' "$RESP"
CODE=$(printf '%s' "$RESP" | json_get '["status_code"]')
[ "$CODE" = "202" ] || { log "expected 202, got $CODE"; exit 1; }
JOB_ID=$(printf '%s' "$RESP" | json_get '["body"]["job_id"]')
log "job id: $JOB_ID"

log "waiting for the worker to pick the job up (leaves 'queued')"
STATUS=""
for _ in $(seq 1 60); do
  STATUS=$(sql "select status from jobs where delivery_id = '$DELIVERY';" || true)
  if [ -n "$STATUS" ] && [ "$STATUS" != "queued" ]; then break; fi
  sleep 2
done
log "job status: ${STATUS:-<missing>}"
[ -n "$STATUS" ] || { log "job row was not recorded in Postgres"; exit 1; }
[ "$STATUS" != "queued" ] || { log "worker never picked up the job"; exit 1; }

log "re-sending the same delivery (idempotency)"
DUP=$(python3 scripts/send_webhook.py \
  --url "$BASE_URL" --delivery "$DELIVERY" --secret "$SECRET")
printf '%s\n' "$DUP"
DUP_CODE=$(printf '%s' "$DUP" | json_get '["status_code"]')
[ "$DUP_CODE" = "200" ] || { log "expected 200 duplicate, got $DUP_CODE"; exit 1; }
DUP_STATUS=$(printf '%s' "$DUP" | json_get '["body"]["status"]')
[ "$DUP_STATUS" = "duplicate" ] || { log "expected duplicate status, got $DUP_STATUS"; exit 1; }
COUNT=$(sql "select count(*) from jobs where delivery_id = '$DELIVERY';")
[ "$COUNT" = "1" ] || { log "expected 1 job row, got $COUNT"; exit 1; }

log "PASS: Postgres migration, webhook enqueue, worker pickup, and delivery-id dedupe all work"
