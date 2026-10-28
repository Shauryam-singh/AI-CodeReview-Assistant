"""Pydantic models for the optional LLM review output.

The model is intentionally strict about the fields that affect GitHub review
posting (file, line, severity) and lenient about aliases the model may use
(``error``/``warning``/percentage confidence).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}

_SEVERITY_ALIASES = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "ERROR": "HIGH",
    "MEDIUM": "MEDIUM",
    "WARNING": "MEDIUM",
    "WARN": "MEDIUM",
    "LOW": "LOW",
    "INFO": "LOW",
    "INFORMATIONAL": "LOW",
}


class LLMFinding(BaseModel):
    """One validated issue returned by the LLM."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    file: str = Field(..., min_length=1, max_length=512)
    line: int = Field(..., gt=0)
    severity: Severity
    category: str = Field(..., min_length=1, max_length=80)
    message: str = Field(..., min_length=1, max_length=4_000)
    suggestion: str = Field(default="", max_length=4_000)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("file", mode="before")
    @classmethod
    def _normalize_file(cls, value):
        if not isinstance(value, str):
            raise ValueError("file must be a string")
        normalized = value.strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized

    @field_validator("line", mode="before")
    @classmethod
    def _normalize_line(cls, value):
        if isinstance(value, str):
            match = re.match(r"^\s*(\d+)", value)
            if match:
                return int(match.group(1))
        return value

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value):
        if value is None:
            return "MEDIUM"
        normalized = str(value).strip().upper()
        return _SEVERITY_ALIASES.get(normalized, "MEDIUM")

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value):
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned.endswith("%"):
                return float(cleaned[:-1]) / 100.0
            return float(cleaned)
        return value

    def as_issue(self) -> dict:
        """Convert to the dict shape used by the existing scan/review pipeline."""
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "tool": "llm",
            # The findings table has no category column; keep the LLM category
            # in ``risk`` so it is still visible to the existing formatter.
            "risk": self.category,
            "code_snippet": "",
        }


class LLMReview(BaseModel):
    """Top-level JSON response contract."""

    model_config = ConfigDict(extra="ignore")

    findings: list[LLMFinding] = Field(default_factory=list)


__all__ = ["LLMFinding", "LLMReview", "SEVERITY_ORDER", "Severity"]
