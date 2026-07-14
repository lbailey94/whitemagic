"""Phase 3 §7.1 — Transaction firewall fail-closed behavior and typed verdicts.

Tests that:
- Firewall blocks when dharma check returns False
- Firewall blocks when dharma engine is unavailable (fail-closed mode)
- Firewall blocks when dharma engine itself raises (fail-closed mode)
- Firewall blocks malformed policy inputs with POLICY_MALFORMED
- Firewall verdicts include typed VerdictReason
- Firewall emits append-only security events
- Maintenance mode bypass works with MAINTENANCE_BYPASS reason
- Firewall middleware blocks economic tools when firewall raises (fail-closed)
"""
from __future__ import annotations

import time

import pytest

from whitemagic.security.transaction_firewall import (
    ECONOMIC_TOOLS,
    TransactionPolicy,
    TransactionRequest,
    VerdictReason,
)


@pytest.fixture
def firewall(tmp_path, monkeypatch):
    """Create a fresh firewall with a temp state root."""
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    import importlib

    import whitemagic.config.paths as paths_mod
    import whitemagic.security.transaction_firewall as mod
    importlib.reload(paths_mod)
    importlib.reload(mod)
    mod._firewall = None
    fw = mod.get_transaction_firewall()
    yield fw
    mod._firewall = None


@pytest.fixture
def fail_closed_firewall(firewall, monkeypatch):
    """Firewall with fail-closed mode enabled."""
    monkeypatch.setenv("WM_FIREWALL_FAIL_CLOSED", "1")
    return firewall


class TestFirewallFailClosed:
    """Economic tools must fail closed when governance is unavailable."""

    def test_blocks_when_dharma_returns_false(self, firewall):
        """When dharma check returns False, transaction must be blocked."""
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.8,
        ))
        firewall._check_dharma = lambda req: False
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "Dharma" in verdict.reason
        assert verdict.verdict_reason == VerdictReason.POLICY_DENIED

    def test_blocks_when_dharma_unavailable_fail_closed(self, fail_closed_firewall):
        """When dharma engine is unavailable and fail-closed is enabled, transaction must be blocked."""
        fail_closed_firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))
        fail_closed_firewall._check_dharma = lambda req: None
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = fail_closed_firewall.validate(req)
        assert not verdict.approved
        assert "fail-closed" in verdict.reason
        assert verdict.verdict_reason == VerdictReason.POLICY_UNAVAILABLE

    def test_permits_when_dharma_unavailable_permissive(self, firewall):
        """When dharma engine is unavailable and fail-closed is NOT enabled, transaction is allowed."""
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))
        firewall._check_dharma = lambda req: None
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved
        assert verdict.verdict_reason == VerdictReason.APPROVED

    def test_blocks_when_dharma_engine_raises(self, fail_closed_firewall):
        """When dharma engine raises an exception, _check_dharma returns None,
        and fail-closed mode blocks the transaction."""
        fail_closed_firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))

        def raising_dharma(req):
            raise RuntimeError("Dharma engine crashed")

        fail_closed_firewall._check_dharma = raising_dharma
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = fail_closed_firewall.validate(req)
        assert not verdict.approved
        assert verdict.verdict_reason == VerdictReason.POLICY_UNAVAILABLE

    def test_blocks_overspend_with_clear_reason(self, firewall):
        """Overspend must produce a structured verdict with policy info."""
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=50.0,
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=100.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "exceeds limit" in verdict.reason
        assert verdict.policy is not None
        assert verdict.policy.max_single_transaction == 50.0
        assert verdict.verdict_reason == VerdictReason.POLICY_DENIED

    def test_blocks_rate_limit_with_remaining_zero(self, firewall):
        """Rate limit violation must report zero remaining."""
        firewall.set_policy("agent_1", TransactionPolicy(
            rate_limit_per_minute=2,
            dharma_check_required=False,
        ))
        for i in range(2):
            req = TransactionRequest(
                agent_id="agent_1", amount=1.0, currency="XRP",
                recipient="rAddr", purpose=f"t{i}", tool_name="bounty.create",
                timestamp=time.time() + i * 0.001,
            )
            v = firewall.validate(req)
            assert v.approved

        req3 = TransactionRequest(
            agent_id="agent_1", amount=1.0, currency="XRP",
            recipient="rAddr", purpose="t3", tool_name="bounty.create",
            timestamp=time.time() + 0.1,
        )
        v3 = firewall.validate(req3)
        assert not v3.approved
        assert v3.rate_remaining == 0
        assert v3.verdict_reason == VerdictReason.POLICY_DENIED

    def test_blocks_blocked_recipient_with_name(self, firewall):
        """Blocked recipient must include the address in the reason."""
        firewall.set_policy("agent_1", TransactionPolicy(
            blocked_recipients={"rScammer123"},
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=1.0, currency="XRP",
            recipient="rScammer123", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "rScammer123" in verdict.reason
        assert verdict.verdict_reason == VerdictReason.POLICY_DENIED

    def test_blocks_when_persist_fails(self, firewall, monkeypatch):
        """If audit log persistence fails, the transaction should still be recorded in-memory."""
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=False,
        ))
        persist_called = [False]
        def failing_but_caught_persist(req):
            persist_called[0] = True
            try:
                raise OSError("Disk full")
            except OSError:
                pass

        monkeypatch.setattr(firewall, "_persist_spend", failing_but_caught_persist)

        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved
        assert persist_called[0]

    def test_verdict_structure_for_denied(self, firewall):
        """Denied verdicts must have all required fields populated."""
        import whitemagic.security.transaction_firewall as mod
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=1.0,
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=100.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert isinstance(verdict, mod.TransactionVerdict)
        assert verdict.approved is False
        assert isinstance(verdict.reason, str)
        assert verdict.policy is not None
        assert verdict.daily_spent == 0.0
        assert verdict.verdict_reason == VerdictReason.POLICY_DENIED

    def test_economic_tools_set_completeness(self):
        """Verify key economic tools are in the firewall set."""
        expected = {"bounty.create", "bounty.complete", "wallet.transfer", "wallet.send"}
        assert expected.issubset(ECONOMIC_TOOLS)


class TestFirewallMalformedInput:
    """Firewall must reject malformed inputs with POLICY_MALFORMED."""

    def test_blocks_empty_agent_id(self, firewall):
        req = TransactionRequest(
            agent_id="", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert verdict.verdict_reason == VerdictReason.POLICY_MALFORMED
        assert "agent_id" in verdict.reason

    def test_blocks_negative_amount(self, firewall):
        req = TransactionRequest(
            agent_id="agent_1", amount=-5.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert verdict.verdict_reason == VerdictReason.POLICY_MALFORMED
        assert "amount" in verdict.reason

    def test_blocks_empty_tool_name(self, firewall):
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert verdict.verdict_reason == VerdictReason.POLICY_MALFORMED
        assert "tool_name" in verdict.reason


class TestFirewallSecurityEventStream:
    """Firewall must emit append-only security events for all verdicts."""

    def test_security_event_emitted_on_denial(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=1.0,
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=100.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        # Check security event log
        assert firewall._security_log_path.exists()
        import json
        with open(firewall._security_log_path) as f:
            lines = f.readlines()
        assert len(lines) >= 1
        event = json.loads(lines[-1])
        assert event["approved"] is False
        assert event["verdict_reason"] == "policy_denied"
        assert event["tool_name"] == "bounty.create"
        assert event["agent_id"] == "agent_1"

    def test_security_event_emitted_on_approval(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved
        assert firewall._security_log_path.exists()
        import json
        with open(firewall._security_log_path) as f:
            lines = f.readlines()
        assert len(lines) >= 1
        event = json.loads(lines[-1])
        assert event["approved"] is True
        assert event["verdict_reason"] == "approved"


class TestFirewallMaintenanceMode:
    """Maintenance mode bypass requires explicit env var."""

    def test_maintenance_mode_bypasses_checks(self, firewall, monkeypatch):
        monkeypatch.setenv("WM_FIREWALL_MAINTENANCE", "1")
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=1.0,
            dharma_check_required=True,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=100.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved
        assert verdict.verdict_reason == VerdictReason.MAINTENANCE_BYPASS

    def test_no_maintenance_mode_blocks_normally(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=1.0,
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=100.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert verdict.verdict_reason != VerdictReason.MAINTENANCE_BYPASS
