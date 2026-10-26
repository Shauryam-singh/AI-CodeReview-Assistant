#!/usr/bin/env python3
"""Call the optional LLM review against a sample diff.

Examples:
    cd backend
    ./venv/bin/python scripts/llm_smoke.py

    LLM_ENABLED=true LLM_API_KEY=... ./venv/bin/python scripts/llm_smoke.py

The script prints validated findings as JSON. It never prints the API key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.context.diff_parser import parse_commentable_lines  # noqa: E402
from app.services.llm.config import get_settings  # noqa: E402
from app.services.llm.prompt import PROMPT_VERSION  # noqa: E402
from app.services.llm.review_service import review_with_llm  # noqa: E402

SAMPLE_DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,5 @@
 import sqlite3
 
 def get_user(db, name):
-    return db.execute("SELECT * FROM users WHERE name = ?", (name,))
+    query = "SELECT * FROM users WHERE name = '" + name + "'"
+    return db.execute(query)
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff",
        type=Path,
        help="Unified diff file to review (defaults to a small SQL-injection sample).",
    )
    parser.add_argument("--repo", default="sample/repo", help="Repository slug for logging.")
    parser.add_argument(
        "--repo-private",
        action="store_true",
        help="Exercise the private-repository skip unless LLM_ALLOW_PRIVATE_REPOS=true.",
    )
    args = parser.parse_args()

    if args.diff is not None:
        if not args.diff.is_file():
            parser.error(f"diff file not found: {args.diff}")
        diff_text = args.diff.read_text(encoding="utf-8", errors="replace")
    else:
        diff_text = SAMPLE_DIFF

    commentable = parse_commentable_lines(diff_text)
    changed_files = list(commentable)
    if not changed_files:
        print("No changed files found in the diff.", file=sys.stderr)
        return 2

    settings = get_settings()
    print(f"LLM enabled: {settings.enabled}")
    print(f"Provider: {settings.provider}")
    print(f"Model: {settings.model}")
    print(f"Prompt version: {PROMPT_VERSION}")
    print(f"Private repo: {args.repo_private}")
    print(f"Changed files: {', '.join(changed_files)}")
    print()

    findings = review_with_llm(
        diff_text,
        changed_files,
        repo_slug=args.repo,
        repo_private=args.repo_private,
        commentable_lines=commentable,
    )

    if not findings:
        print("No validated LLM findings (disabled, skipped, or no high-signal issues).")
        return 0

    print(f"Validated findings: {len(findings)}")
    print(json.dumps([finding.model_dump() for finding in findings], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
