import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "UNKNOWN": 4,
}


def _normalize_path(path: Any) -> str:
    if path is None:
        return ""
    normalized = str(path).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _normalize_message(message: Any) -> str:
    if message is None:
        return ""
    # Normalize whitespace and strip
    normalized = re.sub(r"\s+", " ", str(message))
    return normalized.strip().lower()


def merge_findings(static_findings: list[dict], llm_findings: list[dict]) -> list[dict]:
    """Merge static and LLM findings with deduplication and prioritization.
    
    - Normalize paths
    - Dedupe by (file, line, normalized_message)
    - If LLM and static share same (file, line), keep the static one and append LLM suggestion
    - Sort by severity and confidence
    - LLM findings have tool="llm" with category in risk
    """
    if not static_findings and not llm_findings:
        return []
    
    # Normalize all findings
    merged = []
    seen_keys = set()
    
    # Process static findings first (higher priority)
    for finding in static_findings:
        if not isinstance(finding, dict):
            continue
        
        normalized_finding = dict(finding)
        file_path = _normalize_path(normalized_finding.get("file", ""))
        normalized_finding["file"] = file_path
        
        line = normalized_finding.get("line")
        if isinstance(line, bool):
            line = None
        elif line is not None:
            try:
                line = int(line)
            except (TypeError, ValueError):
                line = None
        
        message_norm = _normalize_message(normalized_finding.get("message", ""))
        key = (file_path, line, message_norm)
        seen_keys.add(key)
        merged.append(normalized_finding)
    
    # Process LLM findings
    for llm_finding in llm_findings:
        if not isinstance(llm_finding, dict):
            continue
        
        normalized_finding = dict(llm_finding)
        file_path = _normalize_path(normalized_finding.get("file", ""))
        normalized_finding["file"] = file_path
        
        line = normalized_finding.get("line")
        if isinstance(line, bool):
            line = None
        elif line is not None:
            try:
                line = int(line)
            except (TypeError, ValueError):
                line = None
        normalized_finding["line"] = line
        
        message_norm = _normalize_message(normalized_finding.get("message", ""))
        key = (file_path, line, message_norm)
        
        # Check if exact duplicate exists
        if key in seen_keys:
            continue
        
        # Check if same file/line as a static finding - merge
        file_line_key = (file_path, line)
        merged_with_static = False
        
        for i, existing in enumerate(merged):
            if _normalize_path(existing.get("file", "")) == file_path and existing.get("line") == line:
                # Same file/line - keep static, optionally append LLM suggestion
                existing_suggestion = existing.get("suggestion") or ""
                llm_suggestion = normalized_finding.get("suggestion") or ""
                
                if llm_suggestion and llm_suggestion not in existing_suggestion:
                    if existing_suggestion:
                        existing["suggestion"] = f"{existing_suggestion}\n\n**AI suggestion:** {llm_suggestion}"
                    else:
                        existing["suggestion"] = f"**AI suggestion:** {llm_suggestion}"
                
                merged_with_static = True
                break
        
        if not merged_with_static:
            # Ensure tool is llm and category in risk
            if normalized_finding.get("tool") != "llm":
                normalized_finding["tool"] = "llm"
            
            # Put category in risk if not present
            if not normalized_finding.get("risk") and normalized_finding.get("category"):
                normalized_finding["risk"] = normalized_finding.get("category")
            
            merged.append(normalized_finding)
            seen_keys.add(key)
    
    # Sort by severity and confidence
    def sort_key(item):
        severity = str(item.get("severity", "UNKNOWN")).upper()
        severity_score = SEVERITY_ORDER.get(severity, 4)
        confidence = item.get("confidence")
        try:
            conf_score = -float(confidence) if confidence is not None else 0
        except (TypeError, ValueError):
            conf_score = 0
        return (severity_score, conf_score)
    
    merged.sort(key=sort_key)
    
    return merged
