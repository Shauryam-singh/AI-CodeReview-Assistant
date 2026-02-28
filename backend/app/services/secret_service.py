import os
import re

# Refined patterns for common secrets
PATTERNS = {
    "AWS Key": r"AKIA[0-9A-Z]{16}",
    "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    "Generic Secret": r"(?i)(password|secret|api_key|passwd|auth_token)\s*[:=]\s*['\"](?![^'\"]*example)[^'\"]{8,}['\"]"
}

def scan_secrets(path):
    findings = []
    for root, _, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root, f)
            relative_path = os.path.relpath(full_path, path)
            try:
                with open(full_path, "r", errors="ignore") as file:
                    content = file.read()
                    for label, pattern in PATTERNS.items():
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            # Calculate line number
                            line_no = content.count('\n', 0, match.start()) + 1
                            findings.append({
                                "file": relative_path,
                                "line": line_no,
                                "message": f"Potential {label} exposed in source code.",
                                "severity": "CRITICAL",
                                "tool": "secret-scanner"
                            })
            except Exception:
                continue
    return findings