import hashlib
import hmac
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.queue import enqueue_pr_scan
from app.services.recording import is_duplicate_delivery, record_job_queued

router = APIRouter()


def verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    if not secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhook/github")
async def github_webhook(request: Request):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Webhook secret not configured. Set GITHUB_WEBHOOK_SECRET.",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event == "ping":
        return {"status": "pong"}

    if event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            if delivery_id and is_duplicate_delivery(delivery_id):
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "duplicate",
                        "delivery": delivery_id,
                        "action": action,
                    },
                )
            try:
                job_id = await enqueue_pr_scan(payload, job_id=delivery_id or None)
            except Exception as e:
                print(f"WEBHOOK: enqueue failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Job queue unavailable. Start Redis and the arq worker.",
                )
            if job_id is None:
                # arq already has a job with this id: a concurrent duplicate
                # delivery won the race (or the result is still retained).
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "duplicate",
                        "delivery": delivery_id,
                        "action": action,
                    },
                )
            record_job_queued(
                job_id,
                payload.get("repository", {}).get("full_name", ""),
                payload.get("pull_request", {}).get("number"),
                action=action,
                pr_info=payload.get("pull_request"),
                repo_html_url=payload.get("repository", {}).get("html_url"),
                delivery_id=delivery_id or None,
            )
            return JSONResponse(
                status_code=202,
                content={
                    "status": "queued",
                    "job_id": job_id,
                    "delivery": delivery_id,
                    "action": action,
                },
            )
        return {"status": "ignored", "action": action}

    if event == "installation":
        return {"status": "installation_event", "action": payload.get("action", "")}

    return {"status": "ignored", "event": event}
