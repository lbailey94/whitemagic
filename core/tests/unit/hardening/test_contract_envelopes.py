"""Slice 1 — Contract tests for canonical tool envelopes and pipeline identity.

Tests that:
- ok() and err() produce stable envelope shapes with all required keys
- normalize_raw() converts legacy shapes correctly
- is_enveloped() detects envelopes reliably
- DispatchContext carries tool_name, kwargs, agent_id
- DispatchPipeline preserves middleware ordering
- Envelope version and tool contract version are stable
"""
from __future__ import annotations

import json

from whitemagic.tools.contract import ENVELOPE_VERSION, TOOL_CONTRACT_VERSION
from whitemagic.tools.envelope import (
    coerce_jsonable,
    err,
    is_enveloped,
    normalize_raw,
    ok,
)


class TestEnvelopeShape:
    """Every envelope must have the same stable top-level keys."""

    REQUIRED_KEYS = {
        "status", "tool", "request_id", "idempotency_key", "message",
        "error_code", "details", "retryable", "writes", "artifacts",
        "metrics", "side_effects", "warnings", "timestamp",
        "envelope_version", "tool_contract_version",
    }

    def test_ok_has_all_required_keys(self):
        env = ok(tool="test.tool", request_id="req-1")
        assert set(env.keys()) == self.REQUIRED_KEYS

    def test_err_has_all_required_keys(self):
        env = err(tool="test.tool", request_id="req-1", error_code="e_code", message="fail")
        assert set(env.keys()) == self.REQUIRED_KEYS

    def test_ok_status_is_success(self):
        env = ok(tool="t", request_id="r")
        assert env["status"] == "success"

    def test_err_status_is_error(self):
        env = err(tool="t", request_id="r", error_code="e", message="m")
        assert env["status"] == "error"

    def test_envelope_version_stable(self):
        assert ENVELOPE_VERSION == "1.0"
        env = ok(tool="t", request_id="r")
        assert env["envelope_version"] == ENVELOPE_VERSION

    def test_tool_contract_version_stable(self):
        env = ok(tool="t", request_id="r")
        assert env["tool_contract_version"] == TOOL_CONTRACT_VERSION

    def test_envelope_is_json_serializable(self):
        env = ok(tool="t", request_id="r", details={"nested": [1, 2, {"a": True}]})
        s = json.dumps(env)
        parsed = json.loads(s)
        assert parsed["status"] == "success"

    def test_err_with_details(self):
        env = err(tool="t", request_id="r", error_code="e", message="m", details={"x": 1})
        assert env["details"] == {"x": 1}

    def test_ok_default_details_empty_dict(self):
        env = ok(tool="t", request_id="r")
        assert env["details"] == {}

    def test_ok_with_writes_and_artifacts(self):
        env = ok(
            tool="t", request_id="r",
            writes=[{"path": "/tmp/test"}],
            artifacts=[{"type": "log"}],
        )
        assert len(env["writes"]) == 1
        assert len(env["artifacts"]) == 1


class TestIsEnveloped:
    def test_detects_envelope(self):
        env = ok(tool="t", request_id="r")
        assert is_enveloped(env) is True

    def test_rejects_plain_dict(self):
        assert is_enveloped({"foo": "bar"}) is False

    def test_rejects_non_dict(self):
        assert is_enveloped("not a dict") is False
        assert is_enveloped(None) is False
        assert is_enveloped([]) is False


class TestNormalizeRaw:
    def test_normalizes_legacy_success_dict(self):
        raw = {"status": "success", "data": [1, 2, 3]}
        env = normalize_raw(tool="test.tool", request_id="r1", raw=raw)
        assert env["status"] == "success"
        assert env["tool"] == "test.tool"
        assert env["request_id"] == "r1"
        assert env["details"]["data"] == [1, 2, 3]

    def test_normalizes_legacy_error_dict(self):
        raw = {"status": "error", "message": "something broke"}
        env = normalize_raw(tool="test.tool", request_id="r1", raw=raw)
        assert env["status"] == "error"
        assert env["error_code"] == "internal_error"
        assert "broke" in env["message"]

    def test_normalizes_success_bool(self):
        raw = {"success": True, "value": 42}
        env = normalize_raw(tool="t", request_id="r", raw=raw)
        assert env["status"] == "success"

    def test_normalizes_failure_bool(self):
        raw = {"success": False, "error": "denied"}
        env = normalize_raw(tool="t", request_id="r", raw=raw)
        assert env["status"] == "error"
        assert env["error_code"] == "internal_error"

    def test_normalizes_non_dict(self):
        env = normalize_raw(tool="t", request_id="r", raw="just a string")
        assert env["status"] == "success"
        assert env["details"]["value"] == "just a string"

    def test_preserves_already_enveloped(self):
        original = ok(tool="t", request_id="r", message="custom")
        env = normalize_raw(tool="t", request_id="r", raw=original)
        assert env["message"] == "custom"
        assert env["status"] == "success"

    def test_error_code_from_legacy_code(self):
        raw = {"status": "error", "code": "custom_error"}
        env = normalize_raw(tool="t", request_id="r", raw=raw)
        assert env["error_code"] == "custom_error"


class TestCoerceJsonable:
    def test_primitives_passthrough(self):
        assert coerce_jsonable(42) == 42
        assert coerce_jsonable("hello") == "hello"
        assert coerce_jsonable(True) is True
        assert coerce_jsonable(None) is None

    def test_datetime_to_iso(self):
        from datetime import datetime
        dt = datetime(2026, 7, 13, 1, 30, 0)
        assert coerce_jsonable(dt) == "2026-07-13T01:30:00"

    def test_path_to_str(self):
        from pathlib import Path
        assert coerce_jsonable(Path("/tmp/foo")) == "/tmp/foo"

    def test_bytes_to_b64(self):
        result = coerce_jsonable(b"hello")
        assert result["_type"] == "bytes"
        assert "b64" in result

    def test_set_to_sorted_list(self):
        result = coerce_jsonable({3, 1, 2})
        assert result == [1, 2, 3]


class TestPipelineIdentity:
    """Verify DispatchContext and DispatchPipeline have stable identity."""

    def test_dispatch_context_has_required_fields(self):
        from whitemagic.tools.middleware import DispatchContext
        ctx = DispatchContext(tool_name="test.tool", kwargs={"x": 1})
        assert ctx.tool_name == "test.tool"
        assert ctx.kwargs == {"x": 1}
        assert ctx.agent_id == "default"
        assert ctx.zig_prevalidated is False
        assert ctx.meta == {}

    def test_dispatch_context_agent_id(self):
        from whitemagic.tools.middleware import DispatchContext
        ctx = DispatchContext(tool_name="t", kwargs={}, agent_id="agent_42")
        assert ctx.agent_id == "agent_42"

    def test_pipeline_order_preserved(self):
        from whitemagic.tools.middleware import DispatchPipeline

        order: list[str] = []

        def mw_a(ctx, next_fn):
            order.append("a_before")
            r = next_fn(ctx)
            order.append("a_after")
            return r

        def mw_b(ctx, next_fn):
            order.append("b_before")
            r = next_fn(ctx)
            order.append("b_after")
            return r

        pipe = DispatchPipeline()
        pipe.use("a", mw_a).use("b", mw_b)
        pipe.execute("test", x=1)

        assert order == ["a_before", "b_before", "b_after", "a_after"]

    def test_pipeline_short_circuit(self):
        from whitemagic.tools.middleware import DispatchPipeline

        called: list[str] = []

        def mw_block(ctx, next_fn):
            called.append("block")
            return {"status": "success", "blocked": True}

        def mw_never(ctx, next_fn):
            called.append("never")
            return next_fn(ctx)

        pipe = DispatchPipeline()
        pipe.use("block", mw_block).use("never", mw_never)
        result = pipe.execute("test")

        assert "never" not in called
        assert result["blocked"] is True
