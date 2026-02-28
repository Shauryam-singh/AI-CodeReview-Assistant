from fastapi import APIRouter, HTTPException
from app.models.schemas import RepoAnalyzeRequest
from app.services.repo_service import clone_repo
from app.services.scan_service import scan_repository

router = APIRouter(prefix="/analyze")

@router.post("/")
def analyze_repo(data: RepoAnalyzeRequest):
    try:
        path = clone_repo(data.repo_url)
        return scan_repository(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))