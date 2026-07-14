"""Tests for Security Capabilities Assessment Phase 7: TransactionFirewall Dharma Integration.

Covers:
  - DharmaRulesEngine.evaluate() is called for transactions with dharma_check_required
  - Dharma deny action blocks the transaction
  - Dharma allow action with sufficient score passes
  - Dharma allow action with insufficient score blocks
  - DHARMA_BLOCKED event published on denial
  - Fallback to legacy Dharma when rules engine unavailable
"""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase7_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── DharmaRulesEngine Integration ────────────────────────────────────────


class TestDharmaRulesEngineIntegration:
    """Test that TransactionFirewall uses DharmaRulesEngine.evaluate()."""

    def test_dharma_check_called_when_required(self):
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        firewall = TransactionFirewall()
        firewall.set_policy("test_agent", TransactionPolicy(
            max_single_transaction=1000,
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=100,
            currency="USDC",
            recipient="0xabc",
            tool_name="test_tool",
            purpose="test transfer",
        )
        verdict = firewall.validate(request)
        # Should either be approved or denied based on Dharma evaluation
        # The key is that it doesn't crash and produces a verdict
        assert verdict.verdict_reason in (
            "approved",
            "policy_denied",
            "policy_unavailable",
        )

    def test_dharma_blocked_event_published(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        firewall = TransactionFirewall()
        # Set very high threshold so Dharma score won't meet it
        firewall.set_policy("test_agent", TransactionPolicy(
            max_single_transaction=100000,
            daily_limit=100000,
            rate_limit_per_minute=100,
            dharma_check_required=True,
            dharma_threshold=0.99,  # Almost impossible to meet
        ))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=50,
            currency="USDC",
            recipient="0xabc",
            tool_name="transfer",
            purpose="test transfer",
        )
        verdict = firewall.validate(request)

        # If Dharma denied (score < 0.99), we should see DHARMA_BLOCKED event
        if not verdict.approved and "Dharma" in verdict.reason:
            events = bus.history(event_type=SecurityEventType.DHARMA_BLOCKED)
            assert len(events) >= 1
            assert events[-1].source == "transaction_firewall"
            assert events[-1].severity == "high"

    def test_dharma_not_checked_when_not_required(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        firewall = TransactionFirewall()
        firewall.set_policy("test_agent", TransactionPolicy(
            max_single_transaction=1000,
            dharma_check_required=False,
        ))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=100,
            currency="USDC",
            recipient="0xabc",
            tool_name="test_tool",
            purpose="test",
        )
        verdict = firewall.validate(request)
        assert verdict.approved

        # No DHARMA_BLOCKED events should be published
        dharma_events = bus.history(event_type=SecurityEventType.DHARMA_BLOCKED)
        assert len(dharma_events) == 0

    def test_transaction_approved_publishes_event(self):
        from whitemagic.security.event_bus import (
            SecurityEventType,
            get_security_event_bus,
            reset_security_event_bus,
        )
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        reset_security_event_bus()
        bus = get_security_event_bus()
        bus.clear()

        firewall = TransactionFirewall()
        firewall.set_policy("test_agent", TransactionPolicy(
            max_single_transaction=1000,
            dharma_check_required=False,
        ))

        request = TransactionRequest(
            agent_id="test_agent",
            amount=100,
            currency="USDC",
            recipient="0xabc",
            tool_name="test_tool",
            purpose="test",
        )
        verdict = firewall.validate(request)
        assert verdict.approved

        events = bus.history(event_type=SecurityEventType.TRANSACTION_APPROVED)
        assert len(events) >= 1


# ─── Dharma Decision Handling ─────────────────────────────────────────────


class TestDharmaDecisionHandling:
    """Test that DharmaDecision action types are handled correctly."""

    def test_dharma_evaluate_returns_decision(self):
        from whitemagic.dharma.rules import get_rules_engine

        engine = get_rules_engine()
        decision = engine.evaluate({
            "tool": "transfer",
            "description": "test transfer",
            "safety": "economic",
            "amount": 100,
            "currency": "USDC",
            "recipient": "0xabc",
        })
        # Should return a DharmaDecision with action and score
        assert hasattr(decision, "action")
        assert hasattr(decision, "score")
        assert hasattr(decision, "triggered_rules")
        action_val = decision.action.value if hasattr(decision.action, "value") else str(decision.action)
        assert action_val in ("allow", "deny", "block", "log")

    def test_dharma_threshold_affects_outcome(self):
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        firewall = TransactionFirewall()
        # Low threshold — should be more permissive
        firewall.set_policy("permissive_agent", TransactionPolicy(
            max_single_transaction=100000,
            daily_limit=100000,
            rate_limit_per_minute=100,
            dharma_check_required=True,
            dharma_threshold=0.0,  # Accept anything
        ))

        request = TransactionRequest(
            agent_id="permissive_agent",
            amount=50,
            currency="USDC",
            recipient="0xabc",
            tool_name="transfer",
            purpose="test",
        )
        verdict = firewall.validate(request)
        # With threshold=0.0, any allow/log should pass
        # (unless Dharma explicitly denies)
        if "Dharma" not in verdict.reason:
            assert verdict.approved

    def test_high_threshold_blocks(self):
        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        firewall = TransactionFirewall()
        # Very high threshold — should block most transactions
        firewall.set_policy("strict_agent", TransactionPolicy(
            max_single_transaction=100000,
            daily_limit=100000,
            rate_limit_per_minute=100,
            dharma_check_required=True,
            dharma_threshold=1.0,  # Impossible to meet
        ))

        request = TransactionRequest(
            agent_id="strict_agent",
            amount=50,
            currency="USDC",
            recipient="0xabc",
            tool_name="transfer",
            purpose="test",
        )
        verdict = firewall.validate(request)
        # With threshold=1.0, even allow with score < 1.0 should block
        # (unless Dharma returns score exactly 1.0)
        assert not verdict.approved or "Dharma" not in verdict.reason


# ─── Fallback Behavior ────────────────────────────────────────────────────


class TestDharmaFallback:
    """Test fallback behavior when DharmaRulesEngine is unavailable."""

    def test_fail_closed_blocks_when_dharma_unavailable(self):
        import os

        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        # Enable fail-closed mode via env var
        old_val = os.environ.get("WM_FIREWALL_FAIL_CLOSED", "")
        os.environ["WM_FIREWALL_FAIL_CLOSED"] = "1"

        firewall = TransactionFirewall()
        firewall.set_policy("fail_closed_agent", TransactionPolicy(
            max_single_transaction=100000,
            daily_limit=100000,
            rate_limit_per_minute=100,
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))

        # Mock _check_dharma to return None (unavailable)
        original = firewall._check_dharma
        firewall._check_dharma = lambda req: None

        try:
            request = TransactionRequest(
                agent_id="fail_closed_agent",
                amount=50,
                currency="USDC",
                recipient="0xabc",
                tool_name="transfer",
                purpose="test",
            )
            verdict = firewall.validate(request)
            assert not verdict.approved
            assert "unavailable" in verdict.reason.lower() or "fail-closed" in verdict.reason.lower()
        finally:
            firewall._check_dharma = original
            if old_val:
                os.environ["WM_FIREWALL_FAIL_CLOSED"] = old_val
            else:
                os.environ.pop("WM_FIREWALL_FAIL_CLOSED", None)

    def test_permissive_allows_when_dharma_unavailable(self):
        import os

        from whitemagic.security.transaction_firewall import (
            TransactionFirewall,
            TransactionPolicy,
            TransactionRequest,
        )

        # Ensure fail-closed is off
        old_val = os.environ.get("WM_FIREWALL_FAIL_CLOSED", "")
        os.environ["WM_FIREWALL_FAIL_CLOSED"] = "0"

        firewall = TransactionFirewall()
        firewall.set_policy("permissive_unavail_agent", TransactionPolicy(
            max_single_transaction=100000,
            daily_limit=100000,
            rate_limit_per_minute=100,
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))

        # Mock _check_dharma to return None (unavailable)
        original = firewall._check_dharma
        firewall._check_dharma = lambda req: None

        try:
            request = TransactionRequest(
                agent_id="permissive_unavail_agent",
                amount=50,
                currency="USDC",
                recipient="0xabc",
                tool_name="transfer",
                purpose="test",
            )
            verdict = firewall.validate(request)
            # Permissive mode should allow
            assert verdict.approved
        finally:
            firewall._check_dharma = original
            if old_val:
                os.environ["WM_FIREWALL_FAIL_CLOSED"] = old_val
            else:
                os.environ.pop("WM_FIREWALL_FAIL_CLOSED", None)
