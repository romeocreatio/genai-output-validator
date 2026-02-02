from __future__ import annotations

from datetime import datetime, timezone

from src.validator import validate_output


def test_valid_output_accepted():
    raw = {
        "request_id": "req_ok_001",
        "prediction": "OK",
        "probability": 0.12,
        "reason": "No significant fraud indicators were detected.",
        "model_version": "v1.2.3",
        "created_at": datetime(2026, 2, 2, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
    }

    result = validate_output(raw)

    assert result["status"] == "accepted"
    assert "data" in result
    assert result["data"].request_id == "req_ok_001"
    assert result["data"].prediction == "OK"
    assert 0.0 <= result["data"].probability <= 1.0


def test_sanitized_output_accepted():
    # Mechanical issues only:
    # - probability as "87%" should become 0.87
    # - prediction casing/whitespace normalized to "Fraude"
    # - created_at "Z" normalized to "+00:00"
    raw = {
        "request_id": "  req_fix_001  ",
        "prediction": "  FRAUDE ",
        "probability": "87%",
        "reason": "Multiple anomalies detected in transaction velocity and metadata.",
        "model_version": "v1.0.0",
        "created_at": "2026-02-02T00:10:00Z",
    }

    result = validate_output(raw)

    assert result["status"] == "accepted"
    model = result["data"]
    assert model.request_id == "req_fix_001"
    assert model.prediction == "Fraude"
    assert abs(model.probability - 0.87) < 1e-9


def test_invalid_output_rejected():
    # Semantic/contract violations:
    # - invalid prediction label (translation)
    # - unexpected field (debug) forbidden
    raw = {
        "request_id": "req_bad_001",
        "prediction": "Fraud",
        "probability": 0.91,
        "reason": "Transaction matches patterns linked to previously confirmed fraud cases.",
        "model_version": "v1.0.0",
        "created_at": "2026-02-02T00:12:00Z",
        "debug": {"trace": "should not be here"},
    }

    result = validate_output(raw)

    assert result["status"] == "rejected"
    assert "errors" in result
    assert isinstance(result["errors"], list)
    assert len(result["errors"]) >= 1
