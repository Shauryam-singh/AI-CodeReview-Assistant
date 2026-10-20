from app.services.existing import secret_service


def _write(tmp_path, name, content):
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return str(tmp_path)


def test_detects_aws_key(tmp_path):
    _write(tmp_path, "conf.py", 'AWS_KEY = "AKIA1234567890ABCDEF"\n')
    findings = secret_service.scan_single_file_secrets(str(tmp_path), "conf.py")
    assert len(findings) == 1
    assert "AWS Key" in findings[0]["message"]
    assert findings[0]["severity"] == "CRITICAL"
    assert findings[0]["tool"] == "secret-scanner"


def test_detects_private_key(tmp_path):
    _write(tmp_path, "id_rsa", "-----BEGIN RSA PRIVATE KEY-----\nabc\n")
    findings = secret_service.scan_single_file_secrets(str(tmp_path), "id_rsa")
    assert len(findings) == 1
    assert "Private Key" in findings[0]["message"]


def test_detects_generic_secret_with_line_number(tmp_path):
    _write(tmp_path, "config.py", 'DEBUG = True\nPASSWORD = "hunter2secret"\n')
    findings = secret_service.scan_single_file_secrets(str(tmp_path), "config.py")
    assert len(findings) == 1
    assert findings[0]["line"] == 2
    assert "Generic Secret" in findings[0]["message"]


def test_example_placeholders_are_not_flagged(tmp_path):
    _write(tmp_path, "readme.py", 'password = "example"\napi_key = "myexamplevalue"\n')
    assert secret_service.scan_single_file_secrets(str(tmp_path), "readme.py") == []


def test_scan_secrets_walks_directory_with_correct_lines(tmp_path):
    (tmp_path / "sub").mkdir()
    _write(tmp_path, "app.py", "x = 1\nAKIA1234567890ABCDEF\n")
    _write(tmp_path, "sub/cfg.yml", "password: \"real_secret_123\"\n")
    findings = secret_service.scan_secrets(str(tmp_path))
    by_file = {}
    for f in findings:
        by_file.setdefault(f["file"].replace("\\", "/"), []).append(f)
    assert "app.py" in by_file
    assert by_file["app.py"][0]["line"] == 2
    assert "sub/cfg.yml" in by_file
    assert by_file["sub/cfg.yml"][0]["line"] == 1


def test_missing_file_returns_empty(tmp_path):
    assert secret_service.scan_single_file_secrets(str(tmp_path), "nope.py") == []
