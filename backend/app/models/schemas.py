from pydantic import BaseModel
from typing import List, Dict, Any

class RepoAnalyzeRequest(BaseModel):
    repo_url: str

class RepoAnalyzeResponse(BaseModel):
    status: str
    total_files_found: int
    total_files_scanned: int
    issues: List[Dict[str, Any]]