import pytest

from app.services.merging import merge_findings


def test_merge_findings_empty():
    assert merge_findings([], []) == []


def test_merge_findings_static_only():
    static = [
        {"file": "app.py", "line": 10, "severity": "HIGH", "message": "SQL injection", "tool": "semgrep", "risk": "sql-injection"}
    ]
    result = merge_findings(static, [])
    assert len(result) == 1
    assert result[0]["file"] == "app.py"
    assert result[0]["tool"] == "semgrep"


def test_merge_findings_llm_only():
    llm = [
        {"file": "test.py", "line": 5, "severity": "CRITICAL", "message": "XSS vuln", "tool": "llm", "risk": "xss"}
    ]
    result = merge_findings([], llm)
    assert len(result) == 1
    assert result[0]["tool"] == "llm"


def test_merge_findings_dedup_by_file_line_message():
    static = [
        {"file": "app.py", "line": 10, "severity": "HIGH", "message": "SQL injection risk", "tool": "ast"}
    ]
    llm = [
        {"file": "app.py", "line": 10, "severity": "CRITICAL", "message": "SQL injection risk", "tool": "llm", "category": "sql"}
    ]
    result = merge_findings(static, llm)
    assert len(result) == 1  # duplicate deduplicated
    assert result[0]["tool"] == "ast"  # static kept


def test_merge_findings_same_line_different_message_appends_suggestion():
    static = [
        {"file": "app.py", "line": 10, "severity": "HIGH", "message": "SQL injection", "tool": "semgrep", "risk": "sql-injection", "suggestion": "Use parameterized queries"}
    ]
    llm = [
        {"file": "app.py", "line": 10, "severity": "CRITICAL", "message": "Different SQL issue", "tool": "llm", "category": "sql", "suggestion": "Also consider ORM"}
    ]
    result = merge_findings(static, llm)
    assert len(result) == 1
    assert "AI suggestion" in result[0]["suggestion"]
    assert "Use parameterized queries" in result[0]["suggestion"]
    assert "Also consider ORM" in result[0]["suggestion"]


def test_merge_findings_normalize_paths():
    static = [
        {"file": "src\\app.py", "line": 10, "severity": "HIGH", "message": "Issue", "tool": "ast"}
    ]
    llm = []
    result = merge_findings(static, llm)
    assert result[0]["file"] == "src/app.py"


def test_merge_findings_sort_by_severity():
    static = [
        {"file": "a.py", "line": 1, "severity": "LOW", "message": "Low issue", "tool": "ast"},
        {"file": "b.py", "line": 2, "severity": "CRITICAL", "message": "Critical issue", "tool": "ast"},
    ]
    llm = [
        {"file": "c.py", "line": 3, "severity": "HIGH", "message": "High issue", "tool": "llm"}
    ]
    result = merge_findings(static, llm)
    assert result[0]["severity"] == "CRITICAL"
    assert result[1]["severity"] == "HIGH"
    assert result[2]["severity"] == "LOW"


def test_merge_findings_llm_sets_risk_from_category():
    llm = [
        {"file": "app.py", "line": 5, "severity": "MEDIUM", "message": "Issue", "tool": "llm", "category": "xss"}
    ]
    result = merge_findings([], llm)
    assert result[0]["risk"] == "xss"
    assert result[0]["tool"] == "llm"


def test_merge_findings_case_insensitive_message_dedup():
    static = [
        {"file": "app.py", "line": 10, "severity": "HIGH", "message": "SQL INJECTION", "tool": "ast"}
    ]
    llm = [
        {"file": "app.py", "line": 10, "severity": "HIGH", "message": "sql injection", "tool": "llm"}
    ]
    result = merge_findings(static, llm)
    assert len(result) == 1
