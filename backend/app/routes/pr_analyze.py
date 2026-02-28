from fastapi import APIRouter, Query
import requests
import tempfile
import os
from app.services.scan_service import scan_repository

router = APIRouter()

@router.get("/analyze-pr")
def analyze_pr(pr_url: str = Query(...)):
    parts = pr_url.rstrip("/").split("/")
    owner, repo, pr_number = parts[-4], parts[-3], parts[-1]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    r = requests.get(api_url)
    files = r.json()

    temp_dir = tempfile.mkdtemp()

    for f in files:
        raw = requests.get(f["raw_url"]).text
        file_path = os.path.join(temp_dir, f["filename"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(raw)

    return scan_repository(temp_dir)