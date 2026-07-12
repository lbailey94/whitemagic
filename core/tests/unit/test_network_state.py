# ruff: noqa: BLE001
"""Tests for Network State Profile (v24.3 §4.3)."""
from __future__ import annotations

import pytest

from whitemagic.core.identity.network_state import (
    AgentIdentity,
    NetworkStateProfile,
    Proposal,
)


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    import importlib
    import whitemagic.config.paths as paths_mod
    importlib.reload(paths_mod)
    import whitemagic.core.identity.network_state as ns_mod
    importlib.reload(ns_mod)
    return ns_mod.NetworkStateProfile()


class TestAgentIdentity:
    def test_create_identity_generates_keys(self, state):
        identity = state.create_identity("agent_1", "Analyst", ["analysis"])
        assert identity.agent_id == "agent_1"
        assert identity.display_name == "Analyst"
        assert identity.public_key  # Non-empty
        assert len(identity.public_key) >= 32  # SHA256 hex
        assert "analysis" in identity.capabilities

    def test_get_identity(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        identity = state.get_identity("agent_1")
        assert identity is not None
        assert identity.display_name == "Analyst"

    def test_get_identity_not_found(self, state):
        assert state.get_identity("nonexistent") is None

    def test_identity_persists(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        # Create new instance — should load from disk
        state2 = NetworkStateProfile()
        identity = state2.get_identity("agent_1")
        assert identity is not None
        assert identity.display_name == "Analyst"


class TestReputation:
    def test_reputation_increases(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        new_rep = state.update_reputation("agent_1", 0.05)
        assert new_rep > 0.5

    def test_reputation_decreases(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        new_rep = state.update_reputation("agent_1", -0.05)
        assert new_rep < 0.5

    def test_reputation_clamped_per_call(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        # Try to increase by 1.0 — should be clamped to 0.1
        new_rep = state.update_reputation("agent_1", 1.0)
        assert new_rep == 0.6  # 0.5 + 0.1

    def test_reputation_clamped_to_range(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        # Set to max
        for _ in range(10):
            state.update_reputation("agent_1", 0.1)
        assert state.get_identity("agent_1").reputation_score == 1.0

    def test_reputation_nonexistent_agent(self, state):
        result = state.update_reputation("nonexistent", 0.1)
        assert result == 0.0


class TestGovernance:
    def test_create_proposal(self, state):
        proposal = state.create_proposal(
            "Increase parallel slots",
            "Raise parallel from 4 to 8",
            "agent_1",
            "config.set",
        )
        assert proposal.title == "Increase parallel slots"
        assert proposal.status == "open"
        assert proposal.proposer == "agent_1"

    def test_vote_on_proposal(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        proposal = state.create_proposal("Test", "Test proposal", "agent_1")
        result = state.vote(proposal.id, "agent_1", support=True, confidence=0.8)
        assert result["status"] == "ok"
        assert result["votes_for"] > 0

    def test_double_vote_rejected(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        proposal = state.create_proposal("Test", "Test proposal", "agent_1")
        state.vote(proposal.id, "agent_1", support=True)
        result = state.vote(proposal.id, "agent_1", support=False)
        assert result["status"] == "error"
        assert "Already voted" in result["message"]

    def test_resolve_proposal_passes(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        state.create_identity("agent_2", "Worker", ["general"])
        proposal = state.create_proposal("Test", "Test proposal", "agent_1")
        state.vote(proposal.id, "agent_1", support=True)
        state.vote(proposal.id, "agent_2", support=True)
        result = state.resolve_proposal(proposal.id)
        assert result["outcome"] in ("passed", "executed")

    def test_resolve_proposal_rejects(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        state.create_identity("agent_2", "Worker", ["general"])
        proposal = state.create_proposal("Test", "Test proposal", "agent_1")
        state.vote(proposal.id, "agent_1", support=False)
        state.vote(proposal.id, "agent_2", support=False)
        result = state.resolve_proposal(proposal.id)
        assert result["outcome"] == "rejected"

    def test_vote_increases_stake(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        proposal = state.create_proposal("Test", "Test proposal", "agent_1")
        initial_stake = state.get_identity("agent_1").governance_stake
        state.vote(proposal.id, "agent_1", support=True)
        new_stake = state.get_identity("agent_1").governance_stake
        assert new_stake > initial_stake


class TestNetworkStateSnapshot:
    def test_get_state(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        state.create_proposal("Test", "Test proposal", "agent_1")
        snapshot = state.get_state()
        assert len(snapshot.citizens) == 1
        assert len(snapshot.proposals) == 1

    def test_get_status(self, state):
        state.create_identity("agent_1", "Analyst", ["analysis"])
        status = state.get_status()
        assert status["citizen_count"] == 1
        assert status["total_proposals"] == 0
        assert "avg_reputation" in status
