from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Tuple


_PERCENT_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*%\s*$")
_NUMBER_RE = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*$")


@dataclass(frozen=True)
class SanitizeResult:
    sanitized: Dict[str, Any]
    actions: List[str]


def _trim_str(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_prediction(value: Any) -> Tuple[Any, List[str]]:
    actions: List[str] = []
    if not isinstance(value, str):
        return value, actions

    raw = value.strip()
    lowered = raw.lower()

    if lowered == "ok":
        if raw != "OK":
            actions.append('normalized prediction to "OK"')
        return "OK", actions

    # Accept only variations of "Fraude" (case/space)
    if lowered == "fraude":
        if raw != "Fraude":
            actions.append('normalized prediction to "Fraude"')
        return "Fraude", actions

    # Anything else is semantic ambiguity, leave untouched (validator will reject)
    return value, actions


def _normalize_probability(value: Any) -> Tuple[Any, List[str]]:
    """
    Controlled mechanical fixes:
    - "0.87" -> 0.87
    - "0,87" -> 0.87
    - "87%"  -> 0.87 (only if strictly percent pattern and within 0..100)
    No fuzzy heuristics beyond that.
    """
    actions: List[str] = []

    if isinstance(value, (int, float)):
        return float(value), actions

    if not isinstance(value, str):
        return value, actions

    s = value.strip()

    # Percent form "87%" or "87,5%"
    m = _PERCENT_RE.match(s)
    if m:
        num_str = m.group(1).replace(",", ".")
        try:
            num = float(num_str)
        except ValueError:
            return value, actions
        if 0.0 <= num <= 100.0:
            actions.append('converted probability from percent string to float in [0,1]')
            return num / 100.0, actions
        return value, actions

    # Plain numeric string "0.87" or "0,87"
    if _NUMBER_RE.match(s):
        num_str = s.replace(",", ".")
        try:
            num = float(num_str)
        except ValueError:
            return value, actions
        actions.append("converted probability from numeric string to float")
        return num, actions

    return value, actions


def _normalize_model_version(value: Any) -> Tuple[Any, List[str]]:
    """
    Very conservative: only trim.
    No adding missing 'v' prefix because that changes semantics/versioning rules.
    """
    actions: List[str] = []
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed != value:
            actions.append("trimmed model_version")
        return trimmed, actions
    return value, actions


def _normalize_reason(value: Any) -> Tuple[Any, List[str]]:
    """
    Only trim. Never invent content.
    """
    actions: List[str] = []
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed != value:
            actions.append("trimmed reason")
        return trimmed, actions
    return value, actions


def _normalize_created_at(value: Any) -> Tuple[Any, List[str]]:
    """
    Controlled mechanical fix:
    - Convert trailing 'Z' to '+00:00' (ISO 8601).
    No parsing of regional formats, no 'yesterday', no guessing.
    """
    actions: List[str] = []
    if not isinstance(value, str):
        return value, actions

    s = value.strip()
    if s.endswith("Z"):
        # 2026-02-02T00:10:00Z -> 2026-02-02T00:10:00+00:00
        actions.append("normalized created_at Z suffix to +00:00")
        return s[:-1] + "+00:00", actions

    if s != value:
        actions.append("trimmed created_at")
    return s, actions


def sanitize_output(data: Dict[str, Any]) -> SanitizeResult:
    """
    Apply controlled, non-ambiguous sanitization.
    Never raises: returns original data if anything unexpected happens.

    Note: unknown fields are NOT removed here. They should cause rejection
    at validation time (extra='forbid').
    """
    actions: List[str] = []
    sanitized: Dict[str, Any] = {}

    try:
        # Shallow copy with controlled normalization on known keys
        for k, v in data.items():
            sanitized[k] = _trim_str(v)

        if "prediction" in sanitized:
            sanitized["prediction"], a = _normalize_prediction(sanitized["prediction"])
            actions.extend(a)

        if "probability" in sanitized:
            sanitized["probability"], a = _normalize_probability(sanitized["probability"])
            actions.extend(a)

        if "reason" in sanitized:
            sanitized["reason"], a = _normalize_reason(sanitized["reason"])
            actions.extend(a)

        if "model_version" in sanitized:
            sanitized["model_version"], a = _normalize_model_version(sanitized["model_version"])
            actions.extend(a)

        if "created_at" in sanitized:
            sanitized["created_at"], a = _normalize_created_at(sanitized["created_at"])
            actions.extend(a)

        if "request_id" in sanitized and isinstance(sanitized["request_id"], str):
            rid = sanitized["request_id"].strip()
            if rid != sanitized["request_id"]:
                sanitized["request_id"] = rid
                actions.append("trimmed request_id")

    except Exception as e:
        # Absolute safety net: never crash the process
        return SanitizeResult(sanitized=data, actions=[f"sanitizer_error: {type(e).__name__}: {e}"])

    return SanitizeResult(sanitized=sanitized, actions=actions)
