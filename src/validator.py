from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from .schemas import FraudPredictionOutput
from .sanitizer import sanitize_output


logger = logging.getLogger(__name__)


def _format_validation_error(err: ValidationError) -> List[str]:
    """
    Convert Pydantic ValidationError into stable, readable strings.
    Example: "probability: Input should be less than or equal to 1"
    """
    messages: List[str] = []
    for e in err.errors():
        loc = ".".join(str(x) for x in e.get("loc", [])) or "root"
        msg = e.get("msg", "validation error")
        typ = e.get("type", "unknown")
        messages.append(f"{loc}: {msg} ({typ})")
    return messages


def _parse_raw_output(raw_output: Any) -> Union[Dict[str, Any], None]:
    """
    Returns a dict if parsing is successful, else None.
    Never raises.
    """
    try:
        if isinstance(raw_output, dict):
            return raw_output

        if isinstance(raw_output, str):
            return json.loads(raw_output)

        # Unsupported type (e.g. list, int, None)
        return None
    except Exception as e:
        logger.warning("Failed to parse raw output: %s: %s", type(e).__name__, e)
        return None


def validate_output(raw_output: Any) -> Dict[str, Any]:
    """
    Fail-fast validation wrapper.

    Steps:
    - Parse JSON if needed
    - Controlled sanitization
    - Strict Pydantic validation

    Contract:
    - Never raises
    - Always returns a structured verdict
    """
    try:
        parsed = _parse_raw_output(raw_output)
        if parsed is None:
            return {
                "status": "rejected",
                "errors": ["raw_output: unable to parse input (expected dict or JSON string)"],
            }

        # Sanitize (controlled, traceable)
        sanitize_result = sanitize_output(parsed)

        # If sanitizer hit an internal exception, it reports it as an action
        if any(a.startswith("sanitizer_error:") for a in sanitize_result.actions):
            logger.error("Sanitizer internal error: %s", sanitize_result.actions)
            return {
                "status": "rejected",
                "errors": sanitize_result.actions,
            }

        # Validate strict contract
        model = FraudPredictionOutput.model_validate(sanitize_result.sanitized)

        # Optional: log sanitization actions for observability (no crash, no silent fix)
        if sanitize_result.actions:
            logger.info("Sanitization applied: %s", sanitize_result.actions)

        return {
            "status": "accepted",
            "data": model,
        }

    except ValidationError as ve:
        errors = _format_validation_error(ve)
        logger.info("Validation rejected output: %s", errors)
        return {
            "status": "rejected",
            "errors": errors,
        }

    except Exception as e:
        # Absolute safety net: nothing escapes
        logger.exception("Unexpected validator error: %s: %s", type(e).__name__, e)
        return {
            "status": "rejected",
            "errors": [f"validator_error: {type(e).__name__}: {e}"],
        }
