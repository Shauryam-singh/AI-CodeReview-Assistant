from app.services.existing import scan_service


def test_count_files_skips_git_directory(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / ".git").joinpath("config").write_text("[core]\n")
    assert scan_service.count_files(str(tmp_path)) == 1


def test_scan_pr_changes_only_scans_given_files(tmp_path, monkeypatch):
    (tmp_path / "changed.py").write_text("eval('x')\n", encoding="utf-8")
    (tmp_path / "untouched.py").write_text("eval('y')\n", encoding="utf-8")

    monkeypatch.setattr(scan_service, "run_semgrep_targeted", lambda repo, files: [])
    result = scan_service.scan_pr_changes(str(tmp_path), ["changed.py"])

    assert result["total_files"] == 1
    files_flagged = {i["file"] for i in result["issues"]}
    assert files_flagged == {"changed.py"}


def test_scan_repository_includes_risk_and_language(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("eval('boom')\n", encoding="utf-8")

    fake_semgrep = [{
        "file": "app.py", "line": 1, "message": "SQL injection",
        "severity": "ERROR", "risk": "x", "tool": "semgrep", "code_snippet": "",
    }]
    monkeypatch.setattr(scan_service, "run_semgrep", lambda path: fake_semgrep)

    result = scan_service.scan_repository(str(tmp_path))
    assert result["status"] == "success"
    assert result["total_files_found"] == 1
    assert result["total_files_scanned"] == 1

    tools = {i["tool"] for i in result["issues"]}
    assert tools == {"semgrep", "python-ast"}

    ast_issue = next(i for i in result["issues"] if i["tool"] == "python-ast")
    assert ast_issue["language"] == "python"
    assert ast_issue["risk"] == "Remote code execution vulnerability."
    assert ast_issue["suggestion"] == "Avoid dangerous dynamic execution."
