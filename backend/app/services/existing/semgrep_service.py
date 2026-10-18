import os
import subprocess
import sys
import json
import functools
from app.services.existing.risk_service import infer_risk

@functools.lru_cache(maxsize=1)
def semgrep_available() -> bool:
    # Windows only ever gets the wrapper wheel (no semgrep-core engine),
    # so shutil.which would find a script that crashes at runtime.
    if sys.platform == "win32":
        return False
    try:
        r = subprocess.run(["semgrep", "--version"], capture_output=True, timeout=15)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def run_semgrep_targeted(repo_path, file_list):
    if not file_list:
        return []

    if not semgrep_available():
        return []

    target_files = [os.path.join(repo_path, f) for f in file_list if os.path.exists(os.path.join(repo_path, f))]
    
    if not target_files:
        return []

    try:
        process = subprocess.run(
            [
                "semgrep",
                "--config", "auto",
                "--json",
                "--no-git-ignore",
            ] + target_files,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=300
        )

        if process.returncode not in [0, 1] or not process.stdout.strip():
            return []

        data = json.loads(process.stdout)
        findings = []

        for r in data.get("results", []):
            # Convert absolute path back to relative for the UI
            full_path = r.get("path")
            rel_path = os.path.relpath(full_path, repo_path)
            
            severity = r.get("extra", {}).get("severity", "UNKNOWN")
            findings.append({
                "file": rel_path,
                "line": r.get("start", {}).get("line"),
                "message": r.get("extra", {}).get("message", "Issue detected"),
                "severity": severity,
                "risk": infer_risk(severity),
                "tool": "semgrep",
                "code_snippet": r.get("extra", {}).get("lines", "").strip()
            })
        return findings
    except Exception as e:
        print(f"Semgrep Error: {e}")
        return []

def run_semgrep(path: str):
    if not semgrep_available():
        return []
    try:
        process = subprocess.run(
            [
                "semgrep",
                "--config", "auto",
                "--json",
                "--no-git-ignore",
                path
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=600
        )

        # semgrep returns:
        # 0 = no findings
        # 1 = findings found
        # >1 = error

        if process.returncode not in [0, 1]:
            print("Semgrep error:", process.stderr)
            return []

        if not process.stdout.strip():
            return []

        data = json.loads(process.stdout)

        findings = []

        for r in data.get("results", []):
            file_path = r.get("path")
            line = r.get("start", {}).get("line")
            message = r.get("extra", {}).get("message", "Issue detected")
            severity = r.get("extra", {}).get("severity", "UNKNOWN")
            snippet = r.get("extra", {}).get("lines", "").strip()

            risk = infer_risk(severity)

            findings.append({
                "file": file_path,
                "line": line,
                "message": message,
                "severity": severity,
                "risk": risk,
                "tool": "semgrep",
                "code_snippet": snippet
            })

        return findings

    except subprocess.TimeoutExpired:
        print("Semgrep timed out")
        return []

    except Exception as e:
        print("Semgrep crashed:", e)
        return []