RISK_MAP = {
    "sql injection": "Attackers can read or modify database data.",
    "command injection": "Attackers can execute arbitrary system commands.",
    "hardcoded secret": "Credentials may be stolen and abused.",
    "eval": "Remote code execution vulnerability.",
    "exec": "Remote code execution vulnerability.",
    "insecure deserialization": "Attackers can run malicious payloads.",
}

def infer_risk(message: str):
    msg = message.lower()
    for key, risk in RISK_MAP.items():
        if key in msg:
            return risk
    return "Potential security or reliability issue."