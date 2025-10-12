from fastapi import APIRouter
from app.services.codeql_service import run_codeql_analysis

router = APIRouter(prefix="/analyze", tags=["Analyze"])

@router.get("")
def analyze_repo(repo_url: str):
    result = run_codeql_analysis(repo_url)
    return {"repo": repo_url, "issues": result}
