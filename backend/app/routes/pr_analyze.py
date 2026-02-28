from fastapi import APIRouter, Query, HTTPException
import requests
import tempfile
import os
from app.services.scan_service import scan_repository

router = APIRouter()

@router.get("/analyze-pr")
def analyze_pr(pr_url: str = Query(...)):

    parts = pr_url.rstrip("/").split("/")
    if len(parts) < 7:
        raise HTTPException(status_code=400, detail="Invalid PR URL")

    owner, repo, pr_number = parts[-4], parts[-3], parts[-1]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-CodeReview-Assistant"
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    r = requests.get(api_url, headers=headers, timeout=15)

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    files = r.json()

    if not isinstance(files, list):
        raise HTTPException(status_code=500, detail="Unexpected GitHub API response")

    temp_dir = tempfile.mkdtemp()

    for f in files:
        raw_url = f.get("raw_url")
        filename = f.get("filename")

        if not raw_url or not filename:
            continue

        raw_response = requests.get(raw_url, headers=headers, timeout=15)
        if raw_response.status_code != 200:
            continue

        file_path = os.path.join(temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(raw_response.text)

    return scan_repository(temp_dir)