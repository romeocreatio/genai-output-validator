"""
Catalogue of intentionally bad LLM outputs.

Constraints:
- mix of dicts and JSON strings
- realistic failure modes seen in production
- used by demo.py and tests
"""

BAD_OUTPUTS = [
    {
        "case_id": "case_01_json_non_parseable",
        "raw_output": """{
            "request_id": "req_001",
            "prediction": "OK",
            "probability": 0.12,
            "reason": "Everything looks normal",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:10:00Z",   // comment not allowed in JSON
        }""",
        "why_real": "LLM mixes JSON with human-style comments or trailing commas; parsers reject it.",
    },
    {
        "case_id": "case_02_missing_required_field",
        "raw_output": {
            # request_id missing
            "prediction": "Fraude",
            "probability": 0.91,
            "reason": "Multiple anomalies detected in transaction patterns.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:12:00Z",
        },
        "why_real": "LLM forgets fields when summarizing or when context is long.",
    },
    {
        "case_id": "case_03_bad_type_probability_comma_decimal",
        "raw_output": {
            "request_id": "req_003",
            "prediction": "Fraude",
            "probability": "0,87",  # comma decimal
            "reason": "High-risk indicators matched known fraud signatures.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:14:00Z",
        },
        "why_real": "Locale formatting leaks into output (French decimal comma) instead of machine float.",
    },
    {
        "case_id": "case_04_invalid_label_translation",
        "raw_output": {
            "request_id": "req_004",
            "prediction": "Fraud",  # invalid (should be Fraude/OK)
            "probability": 0.82,
            "reason": "Transaction resembles previously confirmed fraudulent activity.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:16:00Z",
        },
        "why_real": "LLM translates or varies casing/wording even when label set must be strict.",
    },
    {
        "case_id": "case_05_probability_out_of_range",
        "raw_output": {
            "request_id": "req_005",
            "prediction": "Fraude",
            "probability": 1.2,  # out of range
            "reason": "Extremely suspicious behavior detected across multiple features.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:18:00Z",
        },
        "why_real": "LLM confuses probability vs percent or produces exaggerated numeric values.",
    },
    {
        "case_id": "case_06_reason_too_short",
        "raw_output": {
            "request_id": "req_006",
            "prediction": "OK",
            "probability": 0.07,
            "reason": "OK",  # too short (< 10 chars)
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:20:00Z",
        },
        "why_real": "LLM optimizes for brevity and drops required explanation length.",
    },
    {
        "case_id": "case_07_invalid_version_format",
        "raw_output": {
            "request_id": "req_007",
            "prediction": "OK",
            "probability": 0.22,
            "reason": "No significant risk signals found in the available features.",
            "model_version": "1.0.0",  # missing leading 'v'
            "created_at": "2026-02-02T00:22:00Z",
        },
        "why_real": "LLM outputs 'nice-looking' version strings but not the exact required pattern.",
    },
    {
        "case_id": "case_08_unexpected_field_debug",
        "raw_output": {
            "request_id": "req_008",
            "prediction": "Fraude",
            "probability": 0.88,
            "reason": "Unusual merchant category and velocity anomalies detected in recent activity.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:24:00Z",
            "debug": {"token_usage": 1234, "trace": "internal stuff"},  # forbidden extra
        },
        "why_real": "LLM adds 'helpful' internal fields; in prod this can leak sensitive info or break consumers.",
    },
    {
        "case_id": "case_09_created_at_invalid_format",
        "raw_output": """{
            "request_id": "req_009",
            "prediction": "OK",
            "probability": 0.15,
            "reason": "No strong indicators of fraud were detected for this request.",
            "model_version": "v1.0.0",
            "created_at": "02/02/2026 01:00"
        }""",
        "why_real": "LLM emits regional date formats instead of ISO 8601; parsing becomes inconsistent.",
    },
    {
        "case_id": "case_10_format_drift_wrong_keys",
        "raw_output": {
            "requestId": "req_010",          # wrong key
            "predicted_label": "OK",         # wrong key
            "prob": 0.33,                    # wrong key
            "reason": "Signals are weak and do not justify a fraud classification.",
            "model_version": "v1.0.0",
            "created_at": "2026-02-02T00:26:00Z",
        },
        "why_real": "LLM renames keys for clarity or due to training bias; downstream expects exact names.",
    },
]
