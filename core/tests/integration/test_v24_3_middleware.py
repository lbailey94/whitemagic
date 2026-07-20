# ruff: noqa: BLE001
"""Integration tests for v24.3 middleware: Transaction Firewall + WASM Verify.

These tests exercise the full dispatch pipeline with the new middleware
inserted, verifying that:
1. Transaction Firewall blocks economic tool calls that violate policy
2. Transaction Firewall allows valid economic tool calls through
3. WASM Verify middleware is non-blocking (opt-in, off by default)
4. Pipeline order is correct (firewall runs after governor, before semantic_cache)
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from whitemagic.security.transaction_firewall import (
    TransactionPolicy,
)
from whitemagic.tools.middleware import (
    DispatchContext,
    DispatchPipeline,
    mw_transaction_firewall,
)


@pytest.fixture
def fresh_firewall(tmp_path, monkeypatch):
    """Reset firewall singleton with temp state."""
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    import importlib

    import whitemagic.config.paths as paths_mod
    importlib.reload(paths_mod)
    import whitemagic.security.transaction_firewall as fw_mod
    importlib.reload(fw_mod)
    fw_mod._firewall = None
    fw = fw_mod.get_transaction_firewall()
    yield fw
    fw_mod._firewall = None


class TestTransactionFirewallMiddleware:
    """Test mw_transaction_firewall in a real pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Build a minimal pipeline with just the firewall middleware."""
        p = DispatchPipeline()
        p.use("transaction_firewall", mw_transaction_firewall)

        # Terminal handler that simulates a successful tool call
        def mock_handler(ctx: DispatchContext, next_fn=None) -> dict:
            return {"status": "success", "tool": ctx.tool_name}

        p.use("core_router", mock_handler)
        return p

    def test_non_economic_tool_passes_through(self, pipeline):
        """Non-economic tools should pass through the firewall unchanged."""
        result = pipeline.execute("memory_search", query="test")
        assert result["status"] == "success"
        assert result["tool"] == "memory_search"

    def test_economic_tool_blocked_by_firewall(self, pipeline, fresh_firewall):
        """Economic tool call exceeding limits should be blocked."""
        fresh_firewall.set_policy("default", TransactionPolicy(
            max_single_transaction=5.0,
            dharma_check_required=False,
        ))
        result = pipeline.execute(
            "bounty.create",
            amount=100.0,
            currency="XRP",
            recipient="rTestAddr",
            task="Test bounty",
        )
        assert result["status"] == "error"
        assert result["error_code"] == "transaction_firewall_blocked"
        assert "exceeds limit" in result["message"]

    def test_economic_tool_allowed_within_limits(self, pipeline, fresh_firewall):
        """Economic tool call within limits should pass through."""
        fresh_firewall.set_policy("default", TransactionPolicy(
            max_single_transaction=200.0,
            daily_limit=1000.0,
            dharma_check_required=False,
        ))
        result = pipeline.execute(
            "bounty.create",
            amount=50.0,
            currency="XRP",
            recipient="rTestAddr",
            task="Test bounty",
        )
        assert result["status"] == "success"
        assert result["tool"] == "bounty.create"

    def test_firewall_disabled_via_env(self, pipeline, fresh_firewall, monkeypatch):
        """When WM_TRANSACTION_FIREWALL=0, all calls pass through."""
        monkeypatch.setenv("WM_TRANSACTION_FIREWALL", "0")
        fresh_firewall.set_policy("default", TransactionPolicy(
            max_single_transaction=1.0,
            dharma_check_required=False,
        ))
        result = pipeline.execute(
            "bounty.create",
            amount=100.0,
            currency="XRP",
            recipient="rTestAddr",
        )
        # Should pass through since firewall is disabled
        assert result["status"] == "success"

    def test_rate_limit_blocks_rapid_calls(self, pipeline, fresh_firewall):
        """Rapid economic calls should hit rate limit."""
        fresh_firewall.set_policy("default", TransactionPolicy(
            rate_limit_per_minute=2,
            max_single_transaction=100.0,
            daily_limit=10000.0,
            dharma_check_required=False,
        ))
        # First two should pass
        for i in range(2):
            r = pipeline.execute(
                "bounty.create",
                amount=1.0,
                currency="XRP",
                recipient="rAddr",
                task=f"task_{i}",
            )
            assert r["status"] == "success"

        # Third should be blocked
        r3 = pipeline.execute(
            "bounty.create",
            amount=1.0,
            currency="XRP",
            recipient="rAddr",
            task="task_3",
        )
        assert r3["status"] == "error"
        assert r3["error_code"] == "transaction_firewall_blocked"
        assert "Rate limit" in r3["message"]

    def test_blocked_recipient_blocked(self, pipeline, fresh_firewall):
        """Blocked recipient should be rejected."""
        fresh_firewall.set_policy("default", TransactionPolicy(
            max_single_transaction=100.0,
            daily_limit=1000.0,
            blocked_recipients={"rScammer"},
            dharma_check_required=False,
        ))
        result = pipeline.execute(
            "bounty.create",
            amount=10.0,
            currency="XRP",
            recipient="rScammer",
            task="Test",
        )
        assert result["status"] == "error"
        assert "blocked" in result["message"].lower()


class TestPipelineOrder:
    """Verify middleware is registered in the correct position."""

    def test_firewall_in_full_pipeline(self):
        """The full pipeline should include transaction_firewall."""
        from whitemagic.tools.dispatch_table import get_pipeline

        p = get_pipeline()
        names = p.describe()
        assert "transaction_firewall" in names
        # wasm_verify moved to post-call hooks in Phase 3
        post_call_names = p.describe_post_call()
        assert "wasm_verify" in post_call_names

    def test_firewall_after_governor(self):
        """Firewall should run after governor (governor can set goals/context)."""
        from whitemagic.tools.dispatch_table import get_pipeline

        p = get_pipeline()
        names = p.describe()
        gov_idx = names.index("governor")
        fw_idx = names.index("transaction_firewall")
        assert fw_idx > gov_idx

    def test_wasm_verify_is_last_before_router(self):
        """WASM verify should be in post-call hooks (post-dispatch)."""
        from whitemagic.tools.dispatch_table import get_pipeline

        p = get_pipeline()
        post_call_names = p.describe_post_call()
        assert "wasm_verify" in post_call_names
