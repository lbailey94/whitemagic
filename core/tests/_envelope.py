"""Test helpers for envelope shape validation.

Imported by integration tests that need to assert a tool response has
the correct envelope shape. Lives outside conftest.py so it can be
imported as a regular Python module (pytest's conftest.py is
auto-loaded by pytest but not importable as `from tests.conftest
import`).
"""

ENVELOPE_KEYS = {
    "status",
    "tool",
    "request_id",
    "idempotency_key",
    "message",
    "error_code",
    "details",
    "retryable",
    "writes",
    "artifacts",
    "metrics",
    "side_effects",
    "warnings",
    "timestamp",
    "envelope_version",
    "tool_contract_version",
}


def assert_envelope_shape(out: dict) -> None:
    """Assert that a tool response has the correct envelope shape.

    Validates that the response has every key in ENVELOPE_KEYS, that the
    common fields are typed correctly, and that the whole dict is
    JSON-serializable (a common subtle bug source).
    """
    import json

    missing = ENVELOPE_KEYS.difference(out.keys())
    assert not missing, f"missing envelope keys: {sorted(missing)}"
    assert isinstance(out["status"], str)
    assert isinstance(out["tool"], str)
    assert isinstance(out["request_id"], str)
    assert isinstance(out["details"], dict)
    json.dumps(out)
