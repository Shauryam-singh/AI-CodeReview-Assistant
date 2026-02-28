import os
from app.services.semgrep_service import run_semgrep
from app.services.ast_service import scan_python_ast
from app.services.secret_service import scan_secrets
from app.services.risk_service import infer_risk

def count_files(path):
    total = 0
    for root, _, files in os.walk(path):
        if ".git" in root:
            continue
        total += len(files)
    return total

def scan_repository(path):
    issues = []

    total_files_found = count_files(path)

    semgrep_issues = run_semgrep(path)
    ast_issues = scan_python_ast(path)
    secret_issues = scan_secrets(path)

    issues.extend(semgrep_issues)

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
        "total_files_scanned": total_files_found,
        "issues": issues
    }