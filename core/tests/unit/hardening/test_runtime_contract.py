"""Phase 1 — Contract parity tests for the canonical ToolRuntime.

Tests that:
- ToolRuntime.execute() produces equivalent envelopes to call_tool()
- Request and agent IDs survive every adapter
- Aliases resolve to one canonical tool
- Unknown tools produce one stable error contract
- ExecutionMode enum has all required values
- ToolRequest and ToolResult have required fields
- Feature flag controls runtime delegation
"""
from __future__ import annotations

import os

import pytest

from whitemagic.tools.runtime import (
    ExecutionMode,
    ToolRequest,
    ToolResult,
    ToolRuntime,
    execute,
    is_runtime_enabled,
)


class TestExecutionMode:
    def test_has_full(self):
        assert ExecutionMode.FULL == "full"

    def test_has_read_only_audited(self):
        assert ExecutionMode.READ_ONLY_AUDITED == "read_only_audited"

    def test_has_internal(self):
        assert ExecutionMode.INTERNAL == "internal"

    def test_has_maintenance(self):
        assert ExecutionMode.MAINTENANCE == "maintenance"

    def test_all_modes_distinct(self):
        modes = {ExecutionMode.FULL, ExecutionMode.READ_ONLY_AUDITED,
                 ExecutionMode.INTERNAL, ExecutionMode.MAINTENANCE}
        assert len(modes) == 4


class TestToolRequest:
    def test_default_values(self):
        req = ToolRequest(tool_name="health.check")
        assert req.tool_name == "health.check"
        assert req.arguments == {}
        assert req.user_id == "local"
        assert req.agent_id == "default"
        assert req.requested_mode == ExecutionMode.FULL
        assert req.policy_profile == "default"
        assert req.galaxy == "default"
        assert req.idempotency_key is None
        assert req.dry_run is False

    def test_custom_values(self):
        req = ToolRequest(
            tool_name="memory_create",
            arguments={"content": "test"},
            request_id="req-123",
            user_id="alice",
            agent_id="agent_1",
            requested_mode=ExecutionMode.INTERNAL,
            policy_profile="strict",
            galaxy="codex",
            idempotency_key="idem-1",
            dry_run=True,
        )
        assert req.tool_name == "memory_create"
        assert req.arguments == {"content": "test"}
        assert req.request_id == "req-123"
        assert req.user_id == "alice"
        assert req.agent_id == "agent_1"
        assert req.requested_mode == ExecutionMode.INTERNAL
        assert req.policy_profile == "strict"
        assert req.galaxy == "codex"
        assert req.idempotency_key == "idem-1"
        assert req.dry_run is True

    def test_resolved_request_id_auto_generates(self):
        req = ToolRequest(tool_name="t")
        rid = req.resolved_request_id()
        assert len(rid) > 0
        assert rid != ""

    def test_resolved_request_id_preserves_existing(self):
        req = ToolRequest(tool_name="t", request_id="existing-id")
        assert req.resolved_request_id() == "existing-id"

    def test_to_kwargs_includes_common_fields(self):
        req = ToolRequest(
            tool_name="t",
            arguments={"x": 1},
            request_id="r1",
            idempotency_key="ik1",
            dry_run=True,
        )
        kwargs = req.to_kwargs()
        assert kwargs["x"] == 1
        assert kwargs["request_id"] == "r1"
        assert kwargs["idempotency_key"] == "ik1"
        assert kwargs["dry_run"] is True

    def test_to_kwargs_omits_none_idempotency(self):
        req = ToolRequest(tool_name="t", arguments={"x": 1})
        kwargs = req.to_kwargs()
        assert "idempotency_key" not in kwargs

    def test_is_frozen(self):
        req = ToolRequest(tool_name="t")
        with pytest.raises((AttributeError, Exception)):
            req.tool_name = "other"


class TestToolResult:
    def test_from_envelope_success(self):
        from whitemagic.tools.envelope import ok
        env = ok(tool="test.tool", request_id="r1")
        result = ToolResult.from_envelope(env, duration_s=0.5)
        assert result.status == "success"
        assert result.tool == "test.tool"
        assert result.request_id == "r1"
        assert result.is_success
        assert not result.is_error
        assert result.duration_s == 0.5

    def test_from_envelope_error(self):
        from whitemagic.tools.envelope import err
        env = err(tool="test.tool", request_id="r1", error_code="internal_error", message="fail")
        result = ToolResult.from_envelope(env)
        assert result.status == "error"
        assert result.error_code == "internal_error"
        assert result.message == "fail"
        assert result.is_error
        assert not result.is_success

    def test_to_dict_returns_envelope(self):
        from whitemagic.tools.envelope import ok
        env = ok(tool="t", request_id="r")
        result = ToolResult.from_envelope(env)
        d = result.to_dict()
        assert d["status"] == "success"
        assert d["tool"] == "t"
        assert d is env  # Same dict

    def test_degradation_list(self):
        from whitemagic.tools.envelope import ok
        env = ok(tool="t", request_id="r")
        result = ToolResult.from_envelope(env, degradation=["fallback_used"])
        assert result.degradation == ["fallback_used"]


class TestToolRuntimeExecute:
    """Integration tests for ToolRuntime.execute()."""

    def test_execute_returns_tool_result(self):
        req = ToolRequest(tool_name="health.check")
        result = ToolRuntime.get().execute(req)
        assert isinstance(result, ToolResult)
        assert result.tool == "health.check"
        assert result.request_id  # Should have a request_id

    def test_execute_preserves_request_id(self):
        req = ToolRequest(tool_name="health.check", request_id="test-rid-12345")
        result = ToolRuntime.get().execute(req)
        assert result.request_id == "test-rid-12345"

    def test_execute_unknown_tool_produces_error(self):
        req = ToolRequest(tool_name="nonexistent.tool.xyz")
        result = ToolRuntime.get().execute(req)
        assert result.is_error
        assert result.error_code is not None

    def test_execute_envelope_has_required_keys(self):
        req = ToolRequest(tool_name="health.check")
        result = ToolRuntime.get().execute(req)
        env = result.to_dict()
        required = {"status", "tool", "request_id", "details", "message"}
        assert required.issubset(env.keys())

    def test_execute_with_arguments(self):
        req = ToolRequest(
            tool_name="health.check",
            arguments={"verbose": True},
        )
        result = ToolRuntime.get().execute(req)
        assert isinstance(result, ToolResult)

    def test_module_level_execute(self):
        req = ToolRequest(tool_name="health.check")
        result = execute(req)
        assert isinstance(result, ToolResult)

    def test_maintenance_mode_uses_fast_path(self):
        req = ToolRequest(
            tool_name="health.check",
            requested_mode=ExecutionMode.MAINTENANCE,
        )
        result = ToolRuntime.get().execute(req)
        assert isinstance(result, ToolResult)
        assert "maintenance_mode" in result.degradation

    def test_duration_is_positive(self):
        req = ToolRequest(tool_name="health.check")
        result = ToolRuntime.get().execute(req)
        assert result.duration_s >= 0.0


class TestFeatureFlag:
    def test_disabled_by_default(self):
        old = os.environ.get("WM_TOOL_RUNTIME")
        os.environ.pop("WM_TOOL_RUNTIME", None)
        try:
            assert not is_runtime_enabled()
        finally:
            if old is not None:
                os.environ["WM_TOOL_RUNTIME"] = old

    def test_enabled_when_set(self):
        old = os.environ.get("WM_TOOL_RUNTIME")
        os.environ["WM_TOOL_RUNTIME"] = "1"
        try:
            assert is_runtime_enabled()
        finally:
            if old is not None:
                os.environ["WM_TOOL_RUNTIME"] = old
            else:
                os.environ.pop("WM_TOOL_RUNTIME", None)


class TestEnvelopeEquivalence:
    """Verify that ToolRuntime produces envelopes equivalent to call_tool()."""

    def test_runtime_and_call_tool_produce_same_status(self):
        from whitemagic.tools.unified_api import call_tool

        # Via runtime
        req = ToolRequest(tool_name="health.check", request_id="equiv-1")
        runtime_result = ToolRuntime.get().execute(req)

        # Via call_tool directly
        direct_result = call_tool("health.check", request_id="equiv-2")

        assert runtime_result.status == direct_result.get("status")
        assert runtime_result.tool == direct_result.get("tool")

    def test_runtime_and_call_tool_same_envelope_keys(self):
        from whitemagic.tools.unified_api import call_tool

        req = ToolRequest(tool_name="health.check", request_id="keys-1")
        runtime_env = ToolRuntime.get().execute(req).to_dict()
        direct_env = call_tool("health.check", request_id="keys-2")

        runtime_keys = set(runtime_env.keys())
        direct_keys = set(direct_env.keys())
        assert runtime_keys == direct_keys


class TestAliasResolution:
    """Aliases must resolve to one canonical tool."""

    def test_read_memory_alias_resolves(self):
        from whitemagic.tools.unified_api import _canonical_tool_name, _TOOL_ALIASES

        assert "read_memory" in _TOOL_ALIASES
        assert _canonical_tool_name("read_memory") == "memory_read"

    def test_galaxy_status_alias_resolves(self):
        from whitemagic.tools.unified_api import _canonical_tool_name, _TOOL_ALIASES

        assert "galaxy_status" in _TOOL_ALIASES
        assert _canonical_tool_name("galaxy_status") == "galaxy.status"

    def test_runtime_resolves_alias(self):
        """Runtime should resolve aliases via call_tool() delegation."""
        req = ToolRequest(tool_name="galaxy_list")
        result = ToolRuntime.get().execute(req)
        # The tool name in the result should be the canonical form
        assert result.tool in ("galaxy.list", "galaxy_list")


class TestCanonicalNameNormalization:
    """The runtime must normalize aliases before dispatch."""

    def test_alias_resolved_in_degradation(self):
        """When an alias is used, degradation notes record the mapping."""
        req = ToolRequest(tool_name="galaxy_list")
        result = ToolRuntime.get().execute(req)
        # galaxy_list -> galaxy.list is an alias
        assert any("alias" in d for d in result.degradation)

    def test_canonical_name_not_in_degradation(self):
        """When a canonical name is used, no alias degradation is recorded."""
        req = ToolRequest(tool_name="health.check")
        result = ToolRuntime.get().execute(req)
        assert not any("alias" in d for d in result.degradation)

    def test_canonical_module_importable(self):
        """The canonical module must be importable independently."""
        from whitemagic.tools.canonical import canonical_tool_name, is_alias
        assert canonical_tool_name("health.check") == "health.check"
        assert canonical_tool_name("galaxy_list") == "galaxy.list"
        assert is_alias("galaxy_list") is True
        assert is_alias("health.check") is False

    def test_unified_api_uses_shared_canonical(self):
        """unified_api.py must import from canonical.py, not define its own."""
        from whitemagic.tools.unified_api import _canonical_tool_name, _TOOL_ALIASES
        from whitemagic.tools.canonical import _TOOL_ALIASES as shared_aliases
        # The dict should be the same object (imported, not copied)
        assert _TOOL_ALIASES is shared_aliases


class TestCanonicalNameNormalization:
    """The runtime must normalize aliases before dispatch."""

    def test_alias_resolved_in_degradation(self):
        """When an alias is used, degradation notes record the mapping."""
        req = ToolRequest(tool_name="galaxy_list")
        result = ToolRuntime.get().execute(req)
        assert any("alias" in d for d in result.degradation)

    def test_canonical_name_not_in_degradation(self):
        """When a canonical name is used, no alias degradation is recorded."""
        req = ToolRequest(tool_name="health.check")
        result = ToolRuntime.get().execute(req)
        assert not any("alias" in d for d in result.degradation)

    def test_canonical_module_importable(self):
        """The canonical module must be importable independently."""
        from whitemagic.tools.canonical import canonical_tool_name, is_alias
        assert canonical_tool_name("health.check") == "health.check"
        assert canonical_tool_name("galaxy_list") == "galaxy.list"
        assert is_alias("galaxy_list") is True
        assert is_alias("health.check") is False

    def test_unified_api_uses_shared_canonical(self):
        """unified_api.py must import from canonical.py, not define its own."""
        from whitemagic.tools.unified_api import _canonical_tool_name, _TOOL_ALIASES
        from whitemagic.tools.canonical import _TOOL_ALIASES as shared_aliases
        assert _TOOL_ALIASES is shared_aliases
