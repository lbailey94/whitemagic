# ruff: noqa: BLE001
"""Tests for Transaction Firewall (v24.3 §3.1)."""
from __future__ import annotations

import os
import tempfile
import time

import pytest

from whitemagic.security.transaction_firewall import (
    ECONOMIC_TOOLS,
    TransactionFirewall,
    TransactionPolicy,
    TransactionRequest,
    TransactionVerdict,
    get_transaction_firewall,
)


@pytest.fixture
def firewall(tmp_path, monkeypatch):
    """Create a fresh firewall with a temp state root."""
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    # Reset singleton
    import whitemagic.security.transaction_firewall as mod
    mod._firewall = None
    # Re-import paths to pick up new state root
    import importlib
    import whitemagic.config.paths as paths_mod
    importlib.reload(paths_mod)
    importlib.reload(mod)
    fw = mod.get_transaction_firewall()
    yield fw
    mod._firewall = None


class TestTransactionPolicy:
    def test_default_policy(self):
        p = TransactionPolicy()
        assert p.max_single_transaction == 100.0
        assert p.daily_limit == 1000.0
        assert p.rate_limit_per_minute == 10
        assert p.dharma_check_required is True

    def test_custom_policy(self):
        p = TransactionPolicy(
            max_single_transaction=50.0,
            daily_limit=500.0,
            blocked_recipients={"bad_addr"},
        )
        assert p.max_single_transaction == 50.0
        assert "bad_addr" in p.blocked_recipients


class TestTransactionFirewallValidation:
    def test_policy_allows_normal_transaction(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1",
            amount=10.0,
            currency="XRP",
            recipient="rGoodAddress",
            purpose="bounty reward",
            tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved
        assert verdict.reason == "approved"

    def test_policy_blocks_overspend(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            max_single_transaction=50.0,
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1",
            amount=100.0,
            currency="XRP",
            recipient="rAddr",
            purpose="test",
            tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "exceeds limit" in verdict.reason

    def test_policy_blocks_daily_limit(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            daily_limit=100.0,
            dharma_check_required=False,
        ))
        req1 = TransactionRequest(
            agent_id="agent_1", amount=80.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        v1 = firewall.validate(req1)
        assert v1.approved

        req2 = TransactionRequest(
            agent_id="agent_1", amount=30.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        v2 = firewall.validate(req2)
        assert not v2.approved
        assert "Daily limit exceeded" in v2.reason

    def test_policy_blocks_blocked_recipient(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            blocked_recipients={"rScammer"},
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rScammer", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "blocked" in verdict.reason

    def test_policy_enforces_allowlist(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            allowed_recipients={"rAllowed"},
            dharma_check_required=False,
        ))
        req_ok = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAllowed", purpose="test", tool_name="bounty.create",
        )
        assert firewall.validate(req_ok).approved

        req_bad = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rNotAllowed", purpose="test", tool_name="bounty.create",
        )
        v = firewall.validate(req_bad)
        assert not v.approved
        assert "allowlist" in v.reason

    def test_rate_limit_enforced(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            rate_limit_per_minute=3,
            dharma_check_required=False,
        ))
        for i in range(3):
            req = TransactionRequest(
                agent_id="agent_1", amount=1.0, currency="XRP",
                recipient="rAddr", purpose=f"test_{i}", tool_name="bounty.create",
                timestamp=time.time(),
            )
            v = firewall.validate(req)
            assert v.approved

        req4 = TransactionRequest(
            agent_id="agent_1", amount=1.0, currency="XRP",
            recipient="rAddr", purpose="test_4", tool_name="bounty.create",
            timestamp=time.time(),
        )
        v4 = firewall.validate(req4)
        assert not v4.approved
        assert "Rate limit" in v4.reason

    def test_dharma_rejection(self, firewall, monkeypatch):
        """Low dharma score blocks transaction."""
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.8,
        ))

        # Mock dharma to return low score
        class MockDharma:
            def evaluate_action(self, action_type, context):
                return 0.3

        import whitemagic.security.transaction_firewall as mod
        orig_check = firewall._check_dharma
        monkeypatch.setattr(firewall, "_check_dharma", lambda req: False)

        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert not verdict.approved
        assert "Dharma" in verdict.reason

    def test_dharma_passes_when_ok(self, firewall, monkeypatch):
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=True,
            dharma_threshold=0.5,
        ))
        monkeypatch.setattr(firewall, "_check_dharma", lambda req: True)

        req = TransactionRequest(
            agent_id="agent_1", amount=10.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        verdict = firewall.validate(req)
        assert verdict.approved


class TestTransactionFirewallStatus:
    def test_get_status(self, firewall):
        status = firewall.get_status()
        assert "enabled" in status
        assert "default_policy" in status
        assert "economic_tools" in status
        assert "bounty.create" in status["economic_tools"]

    def test_status_shows_daily_spent(self, firewall):
        firewall.set_policy("agent_1", TransactionPolicy(
            dharma_check_required=False,
        ))
        req = TransactionRequest(
            agent_id="agent_1", amount=25.0, currency="XRP",
            recipient="rAddr", purpose="test", tool_name="bounty.create",
        )
        firewall.validate(req)
        status = firewall.get_status()
        assert status["daily_spent"].get("agent_1") == 25.0


class TestEconomicToolsSet:
    def test_economic_tools_contains_bounty(self):
        assert "bounty.create" in ECONOMIC_TOOLS
        assert "bounty.complete" in ECONOMIC_TOOLS

    def test_economic_tools_contains_wallet(self):
        assert "wallet.transfer" in ECONOMIC_TOOLS
