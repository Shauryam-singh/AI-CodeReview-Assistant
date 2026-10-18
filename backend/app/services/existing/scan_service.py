import os
import time
from app.services.existing.semgrep_service import run_semgrep, run_semgrep_targeted
from app.services.existing.ast_service import scan_python_ast, scan_single_file_ast
from app.services.existing.secret_service import scan_secrets, scan_single_file_secrets
from app.services.existing.risk_service import infer_risk
from app.services.limits import MAX_SCAN_FILES, budget_exceeded

def count_files(path):
    total = 0
    for root, _, files in os.walk(path):
        if ".git" in root:
            continue
        total += len(files)
    return total

def scan_pr_changes(repo_path: str, changed_files: list):
    all_issues = []

    # 1. Run Semgrep only on the changed files
    semgrep_findings = run_semgrep_targeted(repo_path, changed_files)
    all_issues.extend(semgrep_findings)

    # 2. Run targeted AST and Secret scans
    for rel_path in changed_files:
        # Note: scan_single_file_ast usually filters for .py files internally
        ast_issues = scan_single_file_ast(repo_path, rel_path)
        all_issues.extend(ast_issues)
        
        secret_issues = scan_single_file_secrets(repo_path, rel_path)
        all_issues.extend(secret_issues)

    return {
        "issues": all_issues,
        "total_files": len(changed_files)
    }

def scan_repository(path):
    issues = []
    started = time.time()

    total_files_found = count_files(path)

    semgrep_issues = run_semgrep(path)
    issues.extend(semgrep_issues)

    ast_issues = []
    if budget_exceeded(started):
        print("Scan budget exceeded, skipping AST scan.")
    else:
        ast_issues = scan_python_ast(path)

    secret_issues = []
    if budget_exceeded(started):
        print("Scan budget exceeded, skipping secret scan.")
    else:
        secret_issues = scan_secrets(path)

    for issue in ast_issues:
        issue["language"] = "python"
        issue["risk"] = infer_risk(issue["message"])
        issue["suggestion"] = "Avoid dangerous dynamic execution."
        issues.append(issue)

    for issue in secret_issues:
        issue["language"] = "unknown"
        issue["risk"] = "Credentials leak risk."
        issue["suggestion"] = "Move secrets to environment variables."
        issues.append(issue)

    return {
        "status": "success",
        "total_files_found": total_files_found,
        "total_files_scanned": min(total_files_found, MAX_SCAN_FILES),
        "issues": issues
    }