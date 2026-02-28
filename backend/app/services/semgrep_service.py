import subprocess
import json
from app.services.risk_service import infer_risk


def run_semgrep(path: str):
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