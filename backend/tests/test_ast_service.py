from app.services.existing import ast_service


def _write(tmp_path, name, content):
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return str(tmp_path)


def test_ast_detects_eval_with_line_number(tmp_path):
    _write(tmp_path, "bad.py", "x = 1\nresult = eval('2 + 2')\n")
    findings = ast_service.scan_single_file_ast(str(tmp_path), "bad.py")
    assert len(findings) == 1
    assert findings[0]["line"] == 2
    assert "eval" in findings[0]["message"]
    assert findings[0]["severity"] == "HIGH"
    assert findings[0]["tool"] == "python-ast"


def test_ast_detects_exec(tmp_path):
    _write(tmp_path, "bad.py", "exec('print(1)')\n")
    findings = ast_service.scan_single_file_ast(str(tmp_path), "bad.py")
    assert len(findings) == 1
    assert "exec" in findings[0]["message"]


def test_ast_skips_non_python_and_missing_files(tmp_path):
    _write(tmp_path, "notes.txt", "eval('nope')\n")
    assert ast_service.scan_single_file_ast(str(tmp_path), "notes.txt") == []
    assert ast_service.scan_single_file_ast(str(tmp_path), "missing.py") == []


def test_ast_skips_oversized_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ast_service, "MAX_FILE_SIZE_BYTES", 10)
    _write(tmp_path, "big.py", "eval('x')\n" + "#" * 100)
    assert ast_service.scan_single_file_ast(str(tmp_path), "big.py") == []


def test_ast_handles_syntax_errors_and_safe_code(tmp_path):
    _write(tmp_path, "broken.py", "def ??? not valid python !!!\n")
    _write(tmp_path, "safe.py", "print('hello')\nresult = 2 + 2\n")
    assert ast_service.scan_single_file_ast(str(tmp_path), "broken.py") == []
    assert ast_service.scan_single_file_ast(str(tmp_path), "safe.py") == []


def test_scan_python_ast_walks_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    _write(tmp_path, "a.py", "eval('a')\n")
    _write(tmp_path, "sub/b.py", "exec('b')\n")
    _write(tmp_path, "c.txt", "eval('ignored')\n")
    findings = ast_service.scan_python_ast(str(tmp_path))
    assert len(findings) == 2
    files = {f["file"].replace("\\", "/") for f in findings}
    assert files == {"a.py", "sub/b.py"}
