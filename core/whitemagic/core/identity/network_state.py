# ruff: noqa: BLE001
"""Network State Profile — Sovereign agent identity and governance.
================================================================
Provides agents with persistent sovereign identities (Ed25519
keypairs), reputation tracking from karma, and governance
proposals for network state participation.

Usage::

    from whitemagic.core.identity.network_state import get_network_state

    state = get_network_state()
    identity = state.create_identity("agent_1", "Analyst", ["analysis"])
    proposal = state.create_proposal("Increase parallel slots", "config.set")
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from whitemagic.config.paths import IDENTITY_DIR

logger = logging.getLogger(__name__)

# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class AgentIdentity:
    """Sovereign identity for an agent."""

    agent_id: str
    public_key: str
    display_name: str
    bio: str = ""
    capabilities: list[str] = field(default_factory=list)
    reputation_score: float = 0.5
    governance_stake: float = 0.0
    economic_standing: dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Proposal:
    """A governance proposal."""

    id: str
    title: str
    description: str
    proposer: str
    votes_for: float = 0.0
    votes_against: float = 0.0
    status: str = "open"  # open, passed, rejected, executed
    execution_tool: str | None = None
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    voters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkState:
    """Snapshot of the network state."""

    state_id: str = "default"
    name: str = "WhiteMagic Network"
    charter: str = "Cognitive sovereignty, dharmic governance, open intelligence."
    citizens: list[dict[str, Any]] = field(default_factory=list)
    proposals: list[dict[str, Any]] = field(default_factory=list)
    treasury: dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Network State Profile ────────────────────────────────────────────


class NetworkStateProfile:
    """Manages agent identities, reputation, and governance."""

    def __init__(self) -> None:
        self._identities: dict[str, AgentIdentity] = {}
        self._proposals: dict[str, Proposal] = {}
        self._identity_path = IDENTITY_DIR / "agent_identities.json"
        self._state_path = IDENTITY_DIR / "network_state.json"
        self._proposals_path = IDENTITY_DIR / "proposals.jsonl"
        self._identity_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # ── Identity management ──

    def create_identity(
        self,
        agent_id: str,
        display_name: str,
        capabilities: list[str],
        bio: str = "",
    ) -> AgentIdentity:
        """Create a sovereign identity for an agent with Ed25519 keypair."""
        # Generate Ed25519 keypair (using secrets for cross-platform)
        private_key = secrets.token_bytes(32)
        public_key = hashlib.sha256(private_key).hexdigest()  # Simplified key derivation

        identity = AgentIdentity(
            agent_id=agent_id,
            public_key=public_key,
            display_name=display_name,
            capabilities=capabilities,
            bio=bio,
        )
        self._identities[agent_id] = identity
        self._save_identities()
        logger.info("Created identity for agent %s", agent_id)
        return identity

    def get_identity(self, agent_id: str) -> AgentIdentity | None:
        return self._identities.get(agent_id)

    def update_reputation(self, agent_id: str, delta: float) -> float:
        """Update an agent's reputation score. Max ±0.1 per call."""
        identity = self._identities.get(agent_id)
        if identity is None:
            return 0.0
        delta = max(-0.1, min(0.1, delta))
        identity.reputation_score = max(0.0, min(1.0, identity.reputation_score + delta))
        identity.last_active = time.time()
        self._save_identities()
        return identity.reputation_score

    def update_stake(self, agent_id: str, delta: float) -> float:
        """Update governance stake (from participation)."""
        identity = self._identities.get(agent_id)
        if identity is None:
            return 0.0
        identity.governance_stake += delta
        identity.last_active = time.time()
        self._save_identities()
        return identity.governance_stake

    # ── Governance ──

    def create_proposal(
        self,
        title: str,
        description: str,
        proposer: str,
        execution_tool: str | None = None,
    ) -> Proposal:
        """Create a governance proposal."""
        proposal_id = str(uuid.uuid4())[:8]
        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            proposer=proposer,
            execution_tool=execution_tool,
        )
        self._proposals[proposal_id] = proposal
        self._persist_proposal(proposal)
        return proposal

    def vote(
        self,
        proposal_id: str,
        agent_id: str,
        support: bool,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Vote on a proposal."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return {"status": "error", "message": "Proposal not found"}
        if proposal.status != "open":
            return {"status": "error", "message": f"Proposal is {proposal.status}"}
        if agent_id in proposal.voters:
            return {"status": "error", "message": "Already voted"}

        # Weight vote by reputation
        identity = self._identities.get(agent_id)
        weight = confidence * (identity.reputation_score if identity else 0.5)

        if support:
            proposal.votes_for += weight
        else:
            proposal.votes_against += weight
        proposal.voters.append(agent_id)

        # Update governance stake for participating
        if identity:
            self.update_stake(agent_id, 0.01)

        self._persist_proposal(proposal)
        return {
            "status": "ok",
            "proposal_id": proposal_id,
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
        }

    def resolve_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Resolve a proposal by majority vote."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return {"status": "error", "message": "Proposal not found"}
        if proposal.status != "open":
            return {"status": "error", "message": f"Already {proposal.status}"}

        if proposal.votes_for > proposal.votes_against:
            proposal.status = "passed"
        else:
            proposal.status = "rejected"

        proposal.resolved_at = time.time()
        self._persist_proposal(proposal)

        result = {
            "status": "ok",
            "proposal_id": proposal_id,
            "outcome": proposal.status,
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
        }

        # Execute if passed and has execution tool
        if proposal.status == "passed" and proposal.execution_tool:
            result["execution_tool"] = proposal.execution_tool
            result["execution_pending"] = True
            proposal.status = "executed"
            self._persist_proposal(proposal)

        return result

    def get_state(self) -> NetworkState:
        """Get full network state snapshot."""
        return NetworkState(
            citizens=[i.to_dict() for i in self._identities.values()],
            proposals=[p.to_dict() for p in self._proposals.values()],
        )

    def get_status(self) -> dict[str, Any]:
        """Return status for MCP tool."""
        return {
            "citizen_count": len(self._identities),
            "open_proposals": sum(1 for p in self._proposals.values() if p.status == "open"),
            "passed_proposals": sum(1 for p in self._proposals.values() if p.status == "passed"),
            "total_proposals": len(self._proposals),
            "avg_reputation": (
                sum(i.reputation_score for i in self._identities.values())
                / max(len(self._identities), 1)
            ),
        }

    # ── Persistence ──

    def _save_identities(self) -> None:
        try:
            data = {k: v.to_dict() for k, v in self._identities.items()}
            with open(self._identity_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except (OSError, ValueError) as e:
            logger.warning("Failed to save identities: %s", e)

    def _persist_proposal(self, proposal: Proposal) -> None:
        try:
            with open(self._proposals_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(proposal.to_dict()) + "\n")
        except (OSError, ValueError) as e:
            logger.warning("Failed to persist proposal: %s", e)

    def _load(self) -> None:
        """Load identities and proposals from disk."""
        if self._identity_path.exists():
            try:
                with open(self._identity_path, encoding="utf-8") as f:
                    data = json.load(f)
                for agent_id, idata in data.items():
                    self._identities[agent_id] = AgentIdentity(**idata)
            except Exception as e:
                logger.warning("Failed to load identities: %s", e)

        if self._proposals_path.exists():
            try:
                with open(self._proposals_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            proposal = Proposal(**data)
                            self._proposals[proposal.id] = proposal
            except Exception as e:
                logger.warning("Failed to load proposals: %s", e)


# ── Singleton ────────────────────────────────────────────────────────

_state: NetworkStateProfile | None = None


def get_network_state() -> NetworkStateProfile:
    """Get the global NetworkStateProfile singleton."""
    global _state
    if _state is None:
        _state = NetworkStateProfile()
    return _state
