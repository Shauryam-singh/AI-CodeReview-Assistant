"""Send a signed GitHub-style webhook to a running API.

Used by scripts/smoke_test.sh and handy for manual testing:

    python3 scripts/send_webhook.py --delivery manual-1 --secret dev-webhook-secret

Prints one JSON line: {"status_code": 202, "body": {...}}.
"""

import argparse
import hashlib
import hmac
import json
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--delivery", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--repo", default="smoke-test/nonexistent-repo")
    parser.add_argument("--action", default="opened")
    parser.add_argument("--pr", type=int, default=1)
    args = parser.parse_args()

    payload = {
        "action": args.action,
        "pull_request": {"number": args.pr, "title": "smoke test"},
        "repository": {
            "full_name": args.repo,
            "html_url": f"https://github.com/{args.repo}",
        },
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(
        args.secret.encode(), body, hashlib.sha256
    ).hexdigest()

    request = urllib.request.Request(
        f"{args.url.rstrip('/')}/webhook/github",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": args.delivery,
            "X-Hub-Signature-256": signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(json.dumps({
                "status_code": response.status,
                "body": json.loads(response.read()),
            }))
    except urllib.error.HTTPError as e:
        print(json.dumps({"status_code": e.code, "body": e.read().decode()}))


if __name__ == "__main__":
    main()
