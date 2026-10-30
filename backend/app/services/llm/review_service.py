"""Optional, fail-open LLM code review.

This module deliberately has no dependency on the job/worker layer. It never
raises for expected LLM failures: the public entry point catches everything
and returns an empty list, so a Gemini outage or malformed response cannot
fail a webhook job or trigger the transient-retry path.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from pydantic import ValidationError

from app.services.context.diff_parser import parse_commentable_lines
from app.services.existing.secret_service import PATTERNS as SECRET_SCAN_PATTERNS
from app.services.llm.client import LLMClient, build_client, parse_json_payload
from app.services.llm.config import LLMSettings, get_settings
from app.services.llm.prompt import PROMPT_VERSION, build_prompt
from app.services.llm.schema import LLMFinding, LLMReview, SEVERITY_ORDER

logger = logging.getLogger(__name__)

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)\s*$")

_PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----.*?"
    r"-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----",
    flags=re.IGNORECASE | re.DOTALL,
)
_GENERIC_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|api[_-]?token|access[_-]?key|private[_-]?key|"
    r"client[_-]?secret|secret|token|password|passwd|auth[_-]?token|"
    r"authorization|bearer)\b\s*[:=]\s*['\"]?)"
    r"([A-Za-z0-9_\-./+=%]{8,})(['\"]?)"
)
_BEARER_RE = re.compile(r"(?i)(\bBearer\s+)([A-Za-z0-9._~+/=-]{8,})")
_KNOWN_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,})\b"
)

# Reuse the deterministic scanner's AWS/private-key patterns
_SECRET_SCAN_RE = tuple(
    re.compile(pattern)
    for label, pattern in SECRET_SCAN_PATTERNS.items()
    if label != "Generic Secret"
)

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>", flags=re.IGNORECASE | re.DOTALL
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_HTML_TAG_RE = re.compile(
    r"</?(?:script|style|iframe|object|embed|img|a|b|i|u|em|strong|p|div|span|"
    r"br|hr|table|thead|tbody|tr|td|th|ul|ol|li|code|pre|blockquote|svg|math|"
    r"link|meta|form|input|button|textarea|select|option|details|summary|"
    r"marquee|video|audio|source|picture|figure|figcaption|h[1-6])\b[^>]*>",
    flags=re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_BARE_URL_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>()\[\]{}\"']+"
)
_SUSPICIOUS_SCHEME_RE = re.compile(r"(?i)\b(?:javascript|data|vbscript):[^\s]+")
_MENTION_RE = re.compile(r"(?<![\w./])@([A-Za-z0-9][A-Za-z0-9-]{0,38})")
_CODE_SPAN_RE = re.compile(r"(```.*?```|`[^`\n]*`)", flags=re.DOTALL)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_SECURITY_TERM_RE = re.compile(
    r"\b(?:injection|sql|xss|csrf|ssrf|xxe|rce|vulnerab\w*|secret\w*|"
    r"credential\w*|password\w*|auth|authentication|authorization|permission\w*|"
    r"deserial\w*|traversal|command|eval|exec|sanitize|validate|encrypt\w*|"
    r"crypto\w*|leak\w*|race|overflow|unsafe|cors|idor|tls|certificate\w*|"
    r"redirect|prototype pollution|denial of service|insecure|exploit\w*|"
    r"attack\w*|signature|jwt|session\w*|cookie\w*|regex|resource)\b",
    flags=re.IGNORECASE,
)

_STYLE_CATEGORY_TOKENS = frozenset(
    {"style", "formatting", "format", "lint", "linting", "naming", "whitespace", "pep8"}
)
_STYLE_MESSAGE_PHRASES = (
    "line too long",
    "trailing whitespace",
    "missing newline",
    "indentation",
    "spacing",
    "formatting",
    "naming convention",
    "camelcase",
    "snake_case",
    "pep8",
    "pep 8",
    "import order",
    "blank line",
    "semicolon",
    "quote style",
    "prettier",
    "eslint",
    "code style",
    "variable name",
    "function name",
)


def _normalize_path(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _coerce_line(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        line = int(value)
    except (TypeError, ValueError):
        return None
    return line if line > 0 else None


def _secret_hits_by_file(secret_findings: Any) -> dict[str, set[int]]:
    if isinstance(secret_findings, dict):
        secret_findings = [secret_findings]

    hits: dict[str, set[int]] = {}
    for item in secret_findings or []:
        if isinstance(item, dict):
            tool = item.get("tool")
            path = item.get("file")
            line = item.get("line")
        else:
            tool = getattr(item, "tool", None)
            path = getattr(item, "file", None)
            line = getattr(item, "line", None)

        tool_name = str(tool or "").lower()
        if tool_name and tool_name not in {"secret-scanner", "secret_scanner", "secrets"}:
            continue

        normalized = _normalize_path(path)
        line_no = _coerce_line(line)
        if normalized and line_no is not None:
            hits.setdefault(normalized, set()).add(line_no)
    return hits


def _redacted_line(prefix: str, original: str) -> str:
    if original.endswith("\r\n"):
        newline = "\r\n"
    elif original.endswith("\n"):
        newline = "\n"
    else:
        newline = ""
    return f"{prefix}[REDACTED_SECRET]{newline}"


def _redact_lines_by_number(diff_text: str, hits: dict[str, set[int]]) -> str:
    if not hits:
        return diff_text

    out: list[str] = []
    current_file: str | None = None
    in_hunk = False
    old_no = 0
    new_no = 0

    for line in diff_text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")

        match = _DIFF_GIT_RE.match(raw)
        if match:
            current_file = _normalize_path(match.group(2))
            in_hunk = False
            out.append(line)
            continue

        if not in_hunk and raw.startswith("+++ "):
            path = raw[4:].strip()
            if path == "/dev/null":
                current_file = None
            else:
                if path.startswith("b/"):
                    path = path[2:]
                current_file = _normalize_path(path)
            out.append(line)
            continue

        if not in_hunk and raw.startswith("--- "):
            out.append(line)
            continue

        hunk = _HUNK_RE.match(raw)
        if hunk:
            old_no = int(hunk.group(1))
            new_no = int(hunk.group(2))
            in_hunk = True
            out.append(line)
            continue

        if not in_hunk or current_file is None:
            out.append(line)
            continue

        hit_lines = hits.get(current_file, set())

        if raw.startswith("+"):
            if new_no in hit_lines:
                out.append(_redacted_line("+", line))
            else:
                out.append(line)
            new_no += 1
            continue

        if raw.startswith("-"):
            old_no += 1
            out.append(line)
            continue

        if raw.startswith("\\"):
            out.append(line)
            continue

        if raw.startswith(" ") or raw == "":
            if new_no in hit_lines:
                out.append(_redacted_line(" ", line))
            else:
                out.append(line)
            old_no += 1
            new_no += 1
            continue

        in_hunk = False
        out.append(line)

    return "".join(out)


def redact_secrets(diff_text: str, secret_findings: Any = None) -> str:
    """Redact secret values before the diff leaves the process."""
    if not isinstance(diff_text, str) or not diff_text:
        return ""

    redacted = _PRIVATE_KEY_BLOCK_RE.sub("[REDACTED_PRIVATE_KEY]", diff_text)
    for pattern in _SECRET_SCAN_RE:
        redacted = pattern.sub("[REDACTED]", redacted)

    redacted = _GENERIC_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}", redacted
    )
    redacted = _BEARER_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]", redacted
    )
    redacted = _KNOWN_TOKEN_RE.sub("[REDACTED]", redacted)

    return _redact_lines_by_number(redacted, _secret_hits_by_file(secret_findings))


def _truncate_diff(diff_text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(diff_text) <= max_chars:
        return diff_text

    cut = diff_text.rfind("\n", 0, max_chars)
    if cut < max_chars // 2:
        cut = max_chars
    return diff_text[:cut].rstrip() + "\n[... diff truncated ...]"


def _replace_markdown_link(match: re.Match) -> str:
    label = match.group(1).strip()
    return label or "[link removed]"


def _replace_mention(match: re.Match) -> str:
    """Remove GitHub-style mentions while keeping decorators/package scopes."""
    original = match.string
    end = match.end()
    following = original[end : end + 1]

    if following in {"(", "/", "_"}:
        return match.group(0)
    if following == ".":
        after = original[end + 1 : end + 2]
        if after and (after.isalnum() or after == "_"):
            return match.group(0)
    return "[mention removed]"


def _sanitize_prose(text: str) -> str:
    text = _SCRIPT_STYLE_RE.sub("", text)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    text = _MARKDOWN_LINK_RE.sub(_replace_markdown_link, text)
    text = _BARE_URL_RE.sub("[link removed]", text)
    text = _SUSPICIOUS_SCHEME_RE.sub("[link removed]", text)
    text = _MENTION_RE.sub(_replace_mention, text)
    return re.sub(r"[ \t]+", " ", text)


def sanitize_text(value: Any, max_chars: int = 2_000) -> str:
    if not isinstance(value, str):
        return ""

    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub("", text)

    parts = _CODE_SPAN_RE.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = _sanitize_prose(parts[index])
    text = "".join(parts)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def _candidate_findings(payload: Any) -> list:
    if isinstance(payload, LLMReview):
        return list(payload.findings)
    if isinstance(payload, LLMFinding):
        return [payload]
    if isinstance(payload, str):
        payload = parse_json_payload(payload)

    if isinstance(payload, dict):
        findings = payload.get("findings")
        if isinstance(findings, list):
            return findings
        if "file" in payload and "line" in payload:
            return [payload]
        return []

    if isinstance(payload, list):
        return payload
    return []


def _safe_validation_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        errors = exc.errors(include_url=False, include_input=False)
        return "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', ()))}: {error.get('msg')}"
            for error in errors
        )
    return type(exc).__name__


def _parse_findings(payload: Any) -> list[LLMFinding]:
    findings: list[LLMFinding] = []
    for index, raw in enumerate(_candidate_findings(payload)):
        if isinstance(raw, LLMFinding):
            findings.append(raw)
            continue
        try:
            findings.append(LLMFinding.model_validate(raw))
        except (ValidationError, TypeError, ValueError) as exc:
            logger.warning(
                "Dropping invalid LLM finding #%d: %s",
                index,
                _safe_validation_error(exc),
            )
    return findings


def _normalize_commentable(commentable: Any) -> dict[str, dict[str, set[int]]]:
    normalized: dict[str, dict[str, set[int]]] = {}
    if not isinstance(commentable, dict):
        return normalized

    for path, sides in commentable.items():
        if not isinstance(sides, dict):
            continue
        right = {
            line
            for value in (sides.get("RIGHT") or [])
            if (line := _coerce_line(value)) is not None
        }
        left = {
            line
            for value in (sides.get("LEFT") or [])
            if (line := _coerce_line(value)) is not None
        }
        normalized[_normalize_path(path)] = {"RIGHT": right, "LEFT": left}
    return normalized


def _is_style_nit(finding: LLMFinding) -> bool:
    category_tokens = set(re.split(r"[^a-z0-9]+", finding.category.lower()))
    message = finding.message.lower()
    has_security_term = bool(_SECURITY_TERM_RE.search(message))

    if category_tokens & _STYLE_CATEGORY_TOKENS:
        return not has_security_term

    return (
        any(phrase in message for phrase in _STYLE_MESSAGE_PHRASES)
        and not has_security_term
    )


def _validate_and_filter(
    findings: list[LLMFinding],
    changed_files: list[str],
    commentable: dict[str, dict[str, set[int]]],
    settings: LLMSettings,
) -> list[LLMFinding]:
    changed = {_normalize_path(path) for path in changed_files if _normalize_path(path)}
    kept: dict[tuple, LLMFinding] = {}

    for finding in findings:
        if finding.file not in changed:
            logger.debug("Dropping LLM finding for unknown file: %s", finding.file)
            continue

        right_lines = commentable.get(finding.file, {}).get("RIGHT", set())
        if finding.line not in right_lines:
            logger.debug(
                "Dropping LLM finding for un-commentable line: %s:%s",
                finding.file,
                finding.line,
            )
            continue

        if finding.confidence < settings.min_confidence:
            logger.debug(
                "Dropping low-confidence LLM finding: %s:%s (%.2f < %.2f)",
                finding.file,
                finding.line,
                finding.confidence,
                settings.min_confidence,
            )
            continue

        if _is_style_nit(finding):
            logger.debug("Dropping style-only LLM finding: %s:%s", finding.file, finding.line)
            continue

        message = sanitize_text(finding.message, 2_000)
        if not message:
            continue
        suggestion = sanitize_text(finding.suggestion, 2_000)
        category = sanitize_text(finding.category, 80) or "general"

        clean = finding.model_copy(
            update={
                "message": message,
                "suggestion": suggestion,
                "category": category,
            }
        )
        key = (clean.file, clean.line, clean.category.lower(), clean.message.lower())
        existing = kept.get(key)
        if existing is None or clean.confidence > existing.confidence:
            kept[key] = clean

    ordered = sorted(
        kept.values(),
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            -item.confidence,
            item.file,
            item.line,
        ),
    )
    return ordered[: settings.max_findings]


def _review_with_llm(
    diff_text: str,
    changed_files: list[str],
    *,
    repo_slug: str,
    repo_private: bool,
    secret_findings: Any,
    commentable_lines: dict | None,
    settings: LLMSettings,
    client: LLMClient | None,
    head_sha: str | None = None,
) -> list[LLMFinding]:
    if not isinstance(diff_text, str) or not diff_text.strip():
        return []
    if not settings.enabled:
        logger.debug("LLM review skipped: LLM_ENABLED=false")
        return []
    if not settings.api_key:
        logger.info("LLM review skipped: LLM_API_KEY is not set")
        return []
    if repo_private and not settings.allow_private_repos:
        logger.info("LLM review skipped: private repository and LLM_ALLOW_PRIVATE_REPOS=false")
        return []

    normalized_changed: list[str] = []
    seen: set[str] = set()
    for path in changed_files or []:
        normalized = _normalize_path(path)
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_changed.append(normalized)
    if not normalized_changed:
        return []

    redacted = redact_secrets(diff_text, secret_findings)
    truncated = _truncate_diff(redacted, settings.max_input_chars)
    if not truncated.strip():
        return []

    # Cache key: llm:{provider}:{model}:{prompt_version}:{head_sha}
    cache_key = f"llm:{(settings.provider or 'gemini').strip().lower()}:{(settings.model or '').strip()}:{PROMPT_VERSION}:{(head_sha or 'none').strip()}"
    
    # Try cache first (sync wrapper) - skip if client is passed (likely in tests)
    if client is None:
        try:
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, skip cache
            except RuntimeError:
                # No running loop, we can use asyncio with timeout
                try:
                    cached_result = asyncio.run(asyncio.wait_for(_async_get_cache(cache_key), timeout=0.5))
                    if cached_result is not None:
                        logger.info("LLM cache hit for %s (model=%s, prompt=%s)", repo_slug or "<unknown>", settings.model, PROMPT_VERSION)
                        # Reconstruct LLMFinding objects
                        findings = []
                        for item in cached_result:
                            try:
                                findings.append(LLMFinding.model_validate(item))
                            except Exception:
                                pass
                        return findings
                except Exception:
                    pass
        except Exception:
            logger.debug("Cache lookup failed, proceeding without cache")

    start_time = time.time()
    
    if client is None:
        client = build_client(settings)
    if client is None:
        return []

    commentable = (
        _normalize_commentable(commentable_lines)
        if commentable_lines is not None
        else parse_commentable_lines(truncated)
    )

    prompt = build_prompt(truncated, normalized_changed)
    payload = client.generate_json(prompt)
    
    latency = time.time() - start_time
    cache_hit = False
    
    if payload is None:
        logger.info("LLM review skipped: no usable response (prompt=%s, model=%s, latency=%.2fs)", PROMPT_VERSION, settings.model, latency)
        return []

    parsed = _parse_findings(payload)
    if not parsed:
        logger.info("LLM review returned no valid findings (prompt=%s, model=%s, latency=%.2fs)", PROMPT_VERSION, settings.model, latency)
        return []

    result = _validate_and_filter(parsed, normalized_changed, commentable, settings)
    logger.info(
        "LLM review %s: raw=%d valid=%d (prompt=%s, model=%s, latency=%.2fs, cache_hit=%s)",
        repo_slug or "<unknown>",
        len(parsed),
        len(result),
        PROMPT_VERSION,
        settings.model,
        latency,
        cache_hit,
    )
    
    # Cache the result
    if client is None:
        try:
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
                # In async context, skip cache
            except RuntimeError:
                cached_data = [f.model_dump() for f in result]
                from app.services.llm.cache import get_cache_ttl
                try:
                    asyncio.run(asyncio.wait_for(_async_set_cache(cache_key, cached_data, get_cache_ttl()), timeout=0.5))
                except Exception:
                    pass
        except Exception:
            logger.debug("Cache set failed")
    
    return result


async def _async_get_cache(key: str):
    from app.services.llm.cache import get_cached_result
    return await get_cached_result(key)


async def _async_set_cache(key: str, result: list, ttl: int):
    from app.services.llm.cache import set_cached_result
    return await set_cached_result(key, result, ttl)


def review_with_llm(
    diff_text: str,
    changed_files: list[str],
    *,
    repo_slug: str = "",
    repo_private: bool = False,
    secret_findings: Any = None,
    commentable_lines: dict | None = None,
    settings: LLMSettings | None = None,
    client: LLMClient | None = None,
    head_sha: str | None = None,
) -> list[LLMFinding]:
    """Review a diff with the configured LLM provider."""
    try:
        return _review_with_llm(
            diff_text,
            changed_files,
            repo_slug=repo_slug,
            repo_private=repo_private,
            secret_findings=secret_findings,
            commentable_lines=commentable_lines,
            settings=settings or get_settings(),
            client=client,
            head_sha=head_sha,
        )
    except Exception:
        logger.exception("LLM review failed; continuing without LLM findings")
        return []


__all__ = ["redact_secrets", "review_with_llm", "sanitize_text"]
