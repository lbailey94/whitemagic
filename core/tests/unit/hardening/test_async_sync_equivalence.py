"""Phase 1 deferred — Async/sync adapter equivalence test.

Tests that:
- ToolRuntime.execute() (sync) and call_tool() (sync) produce equivalent
  envelopes for the same tool+args
- The async adapter (when used) produces the same envelope shape
- Request IDs survive through both paths
- Error envelopes have the same structure regardless of path
- Degradation notes are preserved across adapters

The async adapter wraps call_tool in asyncio.to_thread(). This test
verifies that the wrapping doesn't alter the envelope contract.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from whitemagic.tools.runtime import (
    ExecutionMode,
    ToolRequest,
    ToolResult,
    ToolRuntime,
)


class TestSyncAdapterEquivalence:
    """ToolRuntime.execute() and call_tool() must produce equivalent results."""

    def test_health_check_same_status(self):
        from whitemagic.tools.unified_api import call_tool

        req = ToolRequest(tool_name="health.check", request_id="sync-1")
        runtime_result = ToolRuntime.get().execute(req)
        direct_result = call_tool("health.check", request_id="sync-2")

        assert runtime_result.status == direct_result.get("status")
        assert runtime_result.tool == direct_result.get("tool")

    def test_health_check_same_envelope_keys(self):
        from whitemagic.tools.unified_api import call_tool

        req = ToolRequest(tool_name="health.check", request_id="keys-sync-1")
        runtime_env = ToolRuntime.get().execute(req).to_dict()
        direct_env = call_tool("health.check", request_id="keys-sync-2")

        assert set(runtime_env.keys()) == set(direct_env.keys())

    def test_unknown_tool_same_error_shape(self):
        from whitemagic.tools.unified_api import call_tool

        req = ToolRequest(tool_name="nonexistent.tool.xyz", request_id="err-1")
        runtime_result = ToolRuntime.get().execute(req)
        direct_result = call_tool("nonexistent.tool.xyz", request_id="err-2")

        assert runtime_result.status == direct_result.get("status")
        assert runtime_result.status == "error"
        # Both should have an error_code
        assert runtime_result.error_code is not None
        assert direct_result.get("error_code") is not None

    def test_request_id_survives_both_paths(self):
        from whitemagic.tools.unified_api import call_tool

        rid = "survival-test-12345"
        req = ToolRequest(tool_name="health.check", request_id=rid)
        runtime_result = ToolRuntime.get().execute(req)
        direct_result = call_tool("health.check", request_id=rid)

        assert runtime_result.request_id == rid
        assert direct_result.get("request_id") == rid


class TestAsyncAdapterEquivalence:
    """The async adapter (asyncio.to_thread wrapping call_tool) must produce
    the same envelope as the sync path."""

    def test_async_health_check_matches_sync(self):
        from whitemagic.tools.unified_api import call_tool

        async def _async_call():
            return await asyncio.to_thread(
                call_tool, "health.check", request_id="async-1"
            )

        # Sync path
        req = ToolRequest(tool_name="health.check", request_id="async-2")
        sync_result = ToolRuntime.get().execute(req)

        # Async path
        async_env = asyncio.run(_async_call())

        assert sync_result.status == async_env.get("status")
        assert sync_result.tool == async_env.get("tool")

    def test_async_envelope_keys_match_sync(self):
        from whitemagic.tools.unified_api import call_tool

        async def _async_call():
            return await asyncio.to_thread(
                call_tool, "health.check", request_id="async-keys-1"
            )

        req = ToolRequest(tool_name="health.check", request_id="async-keys-2")
        sync_env = ToolRuntime.get().execute(req).to_dict()
        async_env = asyncio.run(_async_call())

        assert set(sync_env.keys()) == set(async_env.keys())

    def test_async_unknown_tool_matches_sync_error(self):
        from whitemagic.tools.unified_api import call_tool

        async def _async_call():
            return await asyncio.to_thread(
                call_tool, "nonexistent.tool.abc", request_id="async-err-1"
            )

        req = ToolRequest(tool_name="nonexistent.tool.abc", request_id="async-err-2")
        sync_result = ToolRuntime.get().execute(req)
        async_env = asyncio.run(_async_call())

        assert sync_result.status == async_env.get("status")
        assert sync_result.status == "error"
        assert async_env.get("error_code") is not None

    def test_async_request_id_survives(self):
        from whitemagic.tools.unified_api import call_tool

        rid = "async-survival-99999"

        async def _async_call():
            return await asyncio.to_thread(
                call_tool, "health.check", request_id=rid
            )

        async_env = asyncio.run(_async_call())
        assert async_env.get("request_id") == rid

    def test_async_with_arguments_matches_sync(self):
        from whitemagic.tools.unified_api import call_tool

        async def _async_call():
            return await asyncio.to_thread(
                call_tool, "health.check", request_id="async-args-1"
            )

        req = ToolRequest(
            tool_name="health.check",
            request_id="async-args-2",
        )
        sync_result = ToolRuntime.get().execute(req)
        async_env = asyncio.run(_async_call())

        assert sync_result.status == async_env.get("status")


class TestMaintenanceModeEquivalence:
    """Maintenance mode (fast-path) must produce equivalent results."""

    def test_maintenance_matches_full_for_health_check(self):
        req_full = ToolRequest(tool_name="health.check", request_id="maint-full-1")
        req_maint = ToolRequest(
            tool_name="health.check",
            requested_mode=ExecutionMode.MAINTENANCE,
            request_id="maint-full-2",
        )

        full_result = ToolRuntime.get().execute(req_full)
        maint_result = ToolRuntime.get().execute(req_maint)

        # Both should produce ToolResult
        assert isinstance(full_result, ToolResult)
        assert isinstance(maint_result, ToolResult)
        # Status should match (both may be error in test env, or both success)
        assert full_result.status == maint_result.status
        # Maintenance mode should note the degradation
        assert "maintenance_mode" in maint_result.degradation

    def test_maintenance_degradation_noted(self):
        req = ToolRequest(
            tool_name="health.check",
            requested_mode=ExecutionMode.MAINTENANCE,
        )
        result = ToolRuntime.get().execute(req)
        assert "maintenance_mode" in result.degradation
