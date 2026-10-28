import pytest
from pydantic import ValidationError

from app.services.context.diff_parser import parse_commentable_lines
from app.services.errors import RetryableScanError
from app.services.llm.config import LLMSettings, get_settings
from app.services.llm.review_service import (
    redact_secrets,
    review_with_llm,
    sanitize_text,
)
from app.services.llm.schema import LLMFinding

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,4 @@
 import os
-old = 1
+query = "SELECT * FROM users WHERE name = '" + name + "'"
+return db.execute(query)
+do_something()
"""

MANY_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -0,0 +1,20 @@\n"
    + "\n".join(f"+line {i}" for i in range(1, 21))
    + "\n"
)


class FakeClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.payload


def _settings(**overrides):
    values = {
        "enabled": True,
        "provider": "gemini",
        "api_key": "test-key",
        "model": "gemini-3.8-flash",
        "timeout_seconds": 5.0,
        "max_input_chars": 120_000,
        "max_output_tokens": 4_096,
        "max_findings": 10,
        "min_confidence": 0.6,
        "allow_private_repos": False,
    }
    values.update(overrides)
    return LLMSettings(**values)


def _finding(**overrides):
    values = {
        "file": "app.py",
        "line": 2,
        "severity": "HIGH",
        "category": "sql-injection",
        "message": "User input is concatenated into SQL.",
        "suggestion": "Use a parameterized query.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return values


def _review(payload, **kwargs):
    client = kwargs.pop("client", None) or FakeClient(payload)
    settings = kwargs.pop("settings", None) or _settings()
    return (
        review_with_llm(
            kwargs.pop("diff", DIFF),
            kwargs.pop("changed_files", ["app.py"]),
            client=client,
            settings=settings,
            **kwargs,
        ),
        client,
    )


def test_settings_default_to_disabled_and_safe(monkeypatch):
    for name in (
        "LLM_ENABLED",
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_INPUT_CHARS",
        "LLM_MAX_OUTPUT_TOKENS",
        "LLM_MAX_FINDINGS",
        "LLM_MIN_CONFIDENCE",
        "LLM_ALLOW_PRIVATE_REPOS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()
    assert settings.enabled is False
    assert settings.provider == "gemini"
    assert settings.api_key == ""
    assert settings.model == "gemini-3.8-flash"
    assert settings.timeout_seconds == 45.0
    assert settings.max_input_chars == 120_000
    assert settings.max_output_tokens == 4_096
    assert settings.max_findings == 10
    assert settings.min_confidence == 0.6
    assert settings.allow_private_repos is False


def test_settings_parse_env_and_clamp_values(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "GEMINI")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MAX_FINDINGS", "3")
    monkeypatch.setenv("LLM_MIN_CONFIDENCE", "2")
    monkeypatch.setenv("LLM_ALLOW_PRIVATE_REPOS", "1")

    settings = get_settings()
    assert settings.enabled is True
    assert settings.provider == "gemini"
    assert settings.api_key == "test-key"
    assert settings.max_findings == 3
    assert settings.min_confidence == 1.0
    assert settings.allow_private_repos is True


def test_schema_normalizes_windows_path_severity_and_percent_confidence():
    finding = LLMFinding.model_validate(
        _finding(file="src\\app.py", severity="warning", confidence="85%")
    )
    assert finding.file == "src/app.py"
    assert finding.severity == "MEDIUM"
    assert finding.confidence == 0.85
    assert finding.as_issue()["tool"] == "llm"


def test_schema_rejects_non_positive_line():
    with pytest.raises(ValidationError):
        LLMFinding.model_validate(_finding(line=0))


def test_review_returns_empty_when_disabled():
    result, client = _review(
        {"findings": [_finding()]}, settings=_settings(enabled=False)
    )
    assert result == []
    assert client.prompts == []


def test_review_returns_empty_without_api_key():
    result, client = _review({"findings": [_finding()]}, settings=_settings(api_key=""))
    assert result == []
    assert client.prompts == []


def test_review_skips_private_repo_by_default():
    result, client = _review(
        {"findings": [_finding()]},
        settings=_settings(allow_private_repos=False),
        repo_private=True,
    )
    assert result == []
    assert client.prompts == []


def test_review_allows_private_repo_when_configured():
    result, _ = _review(
        {"findings": [_finding()]},
        settings=_settings(allow_private_repos=True),
        repo_private=True,
    )
    assert len(result) == 1


def test_review_accepts_valid_finding():
    result, _ = _review({"findings": [_finding()]})
    assert len(result) == 1
    assert result[0].file == "app.py"
    assert result[0].line == 2
    assert result[0].category == "sql-injection"


def test_review_parses_markdown_fenced_string_payload():
    result, _ = _review('```json\n{"findings": [' + __import__("json").dumps(_finding()) + "]}\n```")
    assert len(result) == 1


def test_review_normalizes_backslashes_in_changed_file_paths():
    result, _ = _review(
        {"findings": [_finding(file="dir\\app.py"), _finding(file="other.py")]},
        changed_files=["dir/app.py"],
        commentable_lines={"dir/app.py": {"RIGHT": {2}, "LEFT": set()}},
    )
    assert len(result) == 1
    assert result[0].file == "dir/app.py"


def test_review_drops_left_only_line():
    result, _ = _review(
        {"findings": [_finding(line=2), _finding(line=3)]},
        commentable_lines={"app.py": {"RIGHT": {2}, "LEFT": {3}}},
    )
    assert [finding.line for finding in result] == [2]


def test_review_drops_low_confidence_findings():
    result, _ = _review(
        {
            "findings": [
                _finding(line=2, confidence=0.59),
                _finding(line=3, confidence=0.6),
            ]
        }
    )
    assert [finding.line for finding in result] == [3]


def test_review_filters_style_only_findings():
    result, _ = _review(
        {
            "findings": [
                _finding(
                    line=2,
                    category="style",
                    message="Line too long; reformat this line.",
                    confidence=0.99,
                ),
                _finding(line=3, category="security", message="SQL injection in query."),
            ]
        }
    )
    assert [finding.line for finding in result] == [3]


def test_review_caps_findings():
    findings = [_finding(line=line) for line in range(1, 16)]
    result, _ = _review(
        {"findings": findings},
        diff=MANY_DIFF,
        settings=_settings(max_findings=10),
    )
    assert len(result) == 10


def test_review_dedupes_and_keeps_highest_confidence():
    result, _ = _review(
        {
            "findings": [
                _finding(confidence=0.7),
                _finding(confidence=0.9),
            ]
        }
    )
    assert len(result) == 1
    assert result[0].confidence == 0.9


def test_review_drops_invalid_finding_but_keeps_valid_one():
    result, _ = _review(
        {
            "findings": [
                {"file": "app.py", "line": 2},
                _finding(line=2),
            ]
        }
    )
    assert len(result) == 1


def test_review_sanitizes_html_mentions_and_links():
    result, _ = _review(
        {
            "findings": [
                _finding(
                    message="<b>Bad</b> @octocat. See https://evil.example/x",
                    suggestion="Use <script>alert(1)</script> [docs](https://evil.example)",
                )
            ]
        }
    )
    assert len(result) == 1
    assert "<b>" not in result[0].message
    assert "@octocat" not in result[0].message
    assert "evil.example" not in result[0].message
    assert "<script>" not in result[0].suggestion
    assert "@" not in result[0].suggestion


def test_review_redacts_generic_secret_and_secret_scan_hit_before_prompt():
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,1 +1,3 @@
 x = 1
+api_key = "supersecret12345"
+value = "hunter2"
"""
    _, client = _review(
        {"findings": []},
        diff=diff,
        secret_findings=[{"file": "app.py", "line": 3, "tool": "secret-scanner"}],
    )
    prompt = client.prompts[0]
    assert "supersecret12345" not in prompt
    assert "hunter2" not in prompt
    assert "[REDACTED]" in prompt
    assert "[REDACTED_SECRET]" in prompt


def test_review_redacts_private_key_block_before_prompt():
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,1 +1,4 @@
 x = 1
+key = "-----BEGIN RSA PRIVATE KEY-----
+abc
+-----END RSA PRIVATE KEY-----"
"""
    _, client = _review({"findings": []}, diff=diff)
    assert "BEGIN RSA PRIVATE KEY" not in client.prompts[0]
    assert "[REDACTED_PRIVATE_KEY]" in client.prompts[0]


def test_review_truncates_large_diff_before_prompt():
    lines = "\n".join(f"+padding line {i}" for i in range(1, 60))
    tail_diff = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -0,0 +1,60 @@\n"
        f"{lines}\n"
        "+TAIL_MARKER\n"
    )
    _, client = _review(
        {"findings": []},
        diff=tail_diff,
        settings=_settings(max_input_chars=300),
    )
    prompt = client.prompts[0]
    assert "TAIL_MARKER" not in prompt
    assert "[... diff truncated ...]" in prompt


@pytest.mark.parametrize(
    "error",
    [RetryableScanError("transient"), RuntimeError("boom"), ValueError("bad")],
)
def test_review_failures_never_escape(error):
    result, _ = _review(None, client=FakeClient(error=error))
    assert result == []


def test_review_returns_empty_for_unparseable_payload():
    result, _ = _review("not json")
    assert result == []


def test_review_returns_empty_for_empty_diff_or_changed_files():
    assert _review({"findings": [_finding()]}, diff="")[0] == []
    assert _review({"findings": [_finding()]}, changed_files=[])[0] == []


def test_review_uses_commentable_lines_from_diff_by_default():
    result, _ = _review({"findings": [_finding(line=4)]})
    assert len(result) == 1
    assert 4 in parse_commentable_lines(DIFF)["app.py"]["RIGHT"]


def test_sanitize_text_preserves_code_spans_and_decorators():
    cleaned = sanitize_text(
        'Use `@app.route("/x")` and `@staticmethod`; @octocat please review.'
    )
    assert '`@app.route("/x")`' in cleaned
    assert "`@staticmethod`" in cleaned
    assert "@octocat" not in cleaned


def test_sanitize_and_redact_helpers_are_safe_for_non_strings():
    assert sanitize_text(None) == ""
    assert redact_secrets(None) == ""
