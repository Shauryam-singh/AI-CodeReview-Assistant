import os
import re
from app.services.limits import MAX_FILE_SIZE_BYTES, MAX_SCAN_FILES

# Refined patterns for common secrets
PATTERNS = {
    "AWS Key": r"AKIA[0-9A-Z]{16}",
    "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    "Generic Secret": r"(?i)(password|secret|api_key|passwd|auth_token)\s*[:=]\s*['\"](?![^'\"]*example)[^'\"]{8,}['\"]"
}

def _scan_content(content, rel_path, source):
    findings = []
    for label, pattern in PATTERNS.items():
        for match in re.finditer(pattern, content):
            line_no = content.count('\n', 0, match.start()) + 1
            findings.append({
                "file": rel_path,
                "line": line_no,
                "message": f"Potential {label} exposed{source}.",
                "severity": "CRITICAL",
                "tool": "secret-scanner"
            })
    return findings

def scan_single_file_secrets(repo_path, rel_path):
    findings = []
    full_path = os.path.join(repo_path, rel_path)

    if not os.path.exists(full_path):
        return []

    if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
        return []

    try:
        with open(full_path, "r", errors="ignore") as file:
            findings = _scan_content(file.read(), rel_path, "")
    except Exception:
        pass
    return findings

def scan_secrets(path):
    findings = []
    scanned = 0
    for root, _, files in os.walk(path):
        if scanned >= MAX_SCAN_FILES:
            print(f"Secret scan capped at {MAX_SCAN_FILES} files.")
            return findings
        for f in files:
            if scanned >= MAX_SCAN_FILES:
                break
            scanned += 1
            full_path = os.path.join(root, f)
            relative_path = os.path.relpath(full_path, path)
            try:
                if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                    continue
                with open(full_path, "r", errors="ignore") as file:
                    findings.extend(_scan_content(file.read(), relative_path, " in source code"))
            except Exception:
                continue
    return findings
