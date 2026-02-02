from __future__ import annotations

from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictStr, field_validator


_VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


class FraudPredictionOutput(BaseModel):
    """
    Strict output contract for LLM-driven fraud prediction.
    Intentionally strict to protect downstream systems.
    """

    model_config = ConfigDict(
        extra="forbid",            # reject unknown fields
        validate_default=True,
    )

    request_id: StrictStr = Field(..., min_length=1, description="Non-empty unique request identifier.")
    prediction: Literal["Fraude", "OK"] = Field(..., description='Allowed labels: "Fraude" or "OK".')
    probability: StrictFloat = Field(..., ge=0.0, le=1.0, description="Probability score between 0 and 1.")
    reason: StrictStr = Field(..., min_length=10, description="Human-readable reason, minimum 10 characters.")
    model_version: StrictStr = Field(..., description='Model version format "vMAJOR.MINOR.PATCH".')
    created_at: datetime = Field(..., description="UTC timestamp (ISO 8601 recommended).")

    @field_validator("model_version")
    @classmethod
    def validate_model_version(cls, v: str) -> str:
        if not _VERSION_PATTERN.match(v):
            raise ValueError('model_version must match pattern "vMAJOR.MINOR.PATCH" (e.g., v1.2.3)')
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        """
        Controlled parsing:
        - accept datetime directly
        - accept ISO 8601 strings
        - normalize trailing 'Z' to '+00:00'
        Reject anything else (no "yesterday", no regional formats).
        """
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            s = v.strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except ValueError as e:
                raise ValueError(f"created_at must be ISO 8601 datetime string: {e}") from e

        raise TypeError("created_at must be a datetime or ISO 8601 string")
