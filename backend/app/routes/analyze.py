from fastapi import APIRouter, HTTPException
from app.models.schemas import RepoAnalyzeRequest

from app.services.github.repo_service import clone_repo
from app.services.context.context_builder import build_repo_context
from app.services.existing.scan_service import scan_repository

router = APIRouter(prefix="/analyze")

@router.post("/")
def analyze_repo(data: RepoAnalyzeRequest):
    try:
        print("STEP 1: Cloning repo...")
        repo_path = clone_repo(data.repo_url)

        print("USING PATH:", repo_path)

        print("STEP 2: Building context...")
        context = build_repo_context(
            repo_path=repo_path,
            diff_text="",
            commits=[]
        )

        print("STEP 3: Running scan (AST + secrets + semgrep)...")
        scan_results = scan_repository(repo_path)

        # Semgrep findings are already inside scan_results.issues
        # (scan_repository runs semgrep), so don't run it a second time.
        semgrep_results = [
            issue for issue in scan_results.get("issues", [])
            if issue.get("tool") == "semgrep"
        ]

        return {
            "scan_results": scan_results,
            "semgrep": semgrep_results,
            "context": context
        }

    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=str(e))