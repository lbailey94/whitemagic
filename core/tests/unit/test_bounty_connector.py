# ruff: noqa: BLE001
"""Tests for BountyPlatform Auto-Connector (v24.3 §3.2)."""
from __future__ import annotations

import pytest

from whitemagic.agents.bounty_connector import (
    BountyAutoConnector,
    ExternalBounty,
    MockBountyPlatform,
    ReachingAIPlatform,
)


@pytest.fixture
def connector():
    """Fresh connector with mock platform."""
    c = BountyAutoConnector()
    mock_bounties = [
        ExternalBounty(
            platform="mock",
            external_id="b1",
            title="Analyze smart contract",
            description="Audit a Solidity contract",
            reward=50.0,
            required_capabilities=["code_analysis", "testing"],
        ),
        ExternalBounty(
            platform="mock",
            external_id="b2",
            title="Search memories",
            description="Find relevant memories",
            reward=10.0,
            required_capabilities=["memory_search"],
        ),
        ExternalBounty(
            platform="mock",
            external_id="b3",
            title="General task",
            description="No specific capabilities needed",
            reward=5.0,
            required_capabilities=[],
        ),
    ]
    platform = MockBountyPlatform(bounties=mock_bounties)
    c.register_platform(platform)
    c.register_agent("agent_a", ["code_analysis", "testing", "deployment"])
    c.register_agent("agent_b", ["memory_search", "vector_search"])
    c.register_agent("agent_c", ["general"])
    return c


class TestBountyPlatformAdapters:
    def test_reaching_ai_no_key_returns_empty(self):
        import os
        old = os.environ.pop("WM_REACHING_AI_KEY", None)
        try:
            p = ReachingAIPlatform()
            assert p.scan_bounties() == []
        finally:
            if old:
                os.environ["WM_REACHING_AI_KEY"] = old

    def test_mock_platform_scans(self):
        bounties = [
            ExternalBounty(platform="mock", external_id="x1", title="T", description="D", reward=1.0),
        ]
        p = MockBountyPlatform(bounties=bounties)
        result = p.scan_bounties()
        assert len(result) == 1
        assert result[0].external_id == "x1"

    def test_mock_platform_claim(self):
        bounties = [
            ExternalBounty(platform="mock", external_id="x1", title="T", description="D", reward=1.0),
        ]
        p = MockBountyPlatform(bounties=bounties)
        assert p.claim_bounty("x1", "agent_1")
        # Already claimed — should not appear in scan
        assert p.scan_bounties() == []

    def test_mock_platform_submit(self):
        bounties = [
            ExternalBounty(platform="mock", external_id="x1", title="T", description="D", reward=1.0),
        ]
        p = MockBountyPlatform(bounties=bounties)
        p.claim_bounty("x1", "agent_1")
        assert p.submit_result("x1", {"result": "done"})


class TestBountyAutoConnector:
    def test_scan_finds_bounties(self, connector):
        matched = connector.scan_and_match()
        assert len(matched) == 3

    def test_capability_matching(self, connector):
        matched = connector.scan_and_match()
        # agent_a should match the code analysis bounty
        code_bounty = next(m for m in matched if m.bounty.external_id == "b1")
        assert code_bounty.best_agent_id == "agent_a"
        assert code_bounty.capability_match_score == 1.0

        # agent_b should match the memory search bounty
        mem_bounty = next(m for m in matched if m.bounty.external_id == "b2")
        assert mem_bounty.best_agent_id == "agent_b"
        assert mem_bounty.capability_match_score == 1.0

    def test_no_caps_matches_any_agent(self, connector):
        matched = connector.scan_and_match()
        gen_bounty = next(m for m in matched if m.bounty.external_id == "b3")
        assert gen_bounty.capability_match_score == 0.5

    def test_matched_sorted_by_score_x_reward(self, connector):
        matched = connector.scan_and_match()
        # b1: score=1.0, reward=50 → 50.0
        # b2: score=1.0, reward=10 → 10.0
        # b3: score=0.5, reward=5 → 2.5
        assert matched[0].bounty.external_id == "b1"
        assert matched[1].bounty.external_id == "b2"
        assert matched[2].bounty.external_id == "b3"

    def test_auto_claim_imports_to_board(self, connector, tmp_path, monkeypatch):
        """Claimed bounty appears in local BountyBoard."""
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.config.paths as paths_mod
        importlib.reload(paths_mod)
        import whitemagic.core.economy.bounty_board as bb_mod
        importlib.reload(bb_mod)
        bb_mod._board = None

        matched = connector.scan_and_match()
        bounty = connector.auto_claim(matched[0])
        assert bounty is not None
        assert bounty.status == "active"
        assert bounty.executor == "agent_a"
        assert bounty.metadata["external_platform"] == "mock"
        assert bounty.metadata["external_id"] == "b1"

    def test_run_cycle_full_flow(self, connector, tmp_path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib

        import whitemagic.config.paths as paths_mod
        importlib.reload(paths_mod)
        import whitemagic.core.economy.bounty_board as bb_mod
        importlib.reload(bb_mod)
        bb_mod._board = None

        result = connector.run_cycle()
        assert result["scanned"] == 3
        assert result["matched"] == 3
        assert result["claimed"] == 3  # All 3 matched (capped at 5)
        assert len(result["claims"]) == 3

    def test_get_status(self, connector):
        connector.scan_and_match()
        status = connector.get_status()
        assert "mock" in status["platforms"]
        assert status["registered_agents"] == 3
        assert status["last_scan_count"] == 3
