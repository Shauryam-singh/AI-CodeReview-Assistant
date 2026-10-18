from fastapi import APIRouter, HTTPException
import os
import re
from app.services.pipeline_service import run_pipeline
from app.services.existing.scan_service import scan_pr_changes
from app.services.limits import RepoTooLargeError
from app.services.url_validator import validate_github_repo_url, InvalidRepoUrlError

router = APIRouter()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def parse_github_url(url: str):
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError("Invalid GitHub PR URL.")
    return match.group(1), match.group(2), match.group(3)

@router.get("/analyze-pr")
def analyze_pr(pr_url: str):
    try:
        try:
            validate_github_repo_url(pr_url)
        except InvalidRepoUrlError as e:
            raise HTTPException(status_code=400, detail=e.message)

        owner, repo_name, pr_number = parse_github_url(pr_url)
        repo_slug = f"{owner}/{repo_name}"
        repo_full_url = f"https://github.com/{repo_slug}.git"

        # Step 1: Clone and Build Context
        pipeline_data = run_pipeline(repo_full_url, repo_slug, pr_number, GITHUB_TOKEN)
        
        # Step 2: Extract changed files from the parsed diff
        # pipeline_data['context']['diff'] is the dict from parse_diff
        context = pipeline_data.get("context", {})
        diff_dict = context.get("diff", {})
        changed_files = list(diff_dict.keys())

        if not changed_files:
            return {
                "status": "success",
                "message": "No files were detected in the PR diff.",
                "issues": [],
                "total_files_found": 0,
                "total_files_scanned": 0
            }

        # Step 3: Run targeted scans
        repo_path = pipeline_data["repo_path"]
        scan_results = scan_pr_changes(repo_path, changed_files)

        return {
            "status": "success",
            "metadata": pipeline_data.get("metadata"),
            "issues": scan_results["issues"],
            "total_files_found": len(changed_files),
            "total_files_scanned": len(changed_files)
        }

    except InvalidRepoUrlError as e:
        print("INVALID URL:", e)
        raise HTTPException(status_code=400, detail=e.message)

    except HTTPException:
        raise

    except RepoTooLargeError as e:
        print("REJECTED:", e)
        raise HTTPException(status_code=413, detail=e.message)

    except TimeoutError as e:
        print("TIMEOUT:", e)
        raise HTTPException(status_code=504, detail=str(e))

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))