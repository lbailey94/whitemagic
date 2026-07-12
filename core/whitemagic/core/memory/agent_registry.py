"""Agent Registry for Multi-Agent Cache Coherence.

Tracks known agents, their IDs, and metadata for the version-vector
cache coherence protocol. Each agent that reads or writes memories
should register itself to enable conflict detection and resolution.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    name: str = ""
    capabilities: list[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update last_seen timestamp."""
        self.last_seen = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": list(self.capabilities),
            "registered_at": self.registered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "metadata": dict(self.metadata),
        }


class AgentRegistry:
    """Registry of known agents for multi-agent cache coherence.

    Tracks agents that participate in the memory system, enabling:
    - Agent ID assignment for version vectors
    - Conflict detection (which agent wrote a conflicting version)
    - Heartbeat tracking (detect stale agents)
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._lock = threading.RLock()

    def register(self, agent_id: str, name: str = "",
                 capabilities: list[str] | None = None,
                 metadata: dict[str, Any] | None = None) -> AgentInfo:
        """Register a new agent or update an existing one."""
        with self._lock:
            if agent_id in self._agents:
                info = self._agents[agent_id]
                info.touch()
                if name:
                    info.name = name
                if capabilities:
                    info.capabilities = list(capabilities)
                if metadata:
                    info.metadata.update(metadata)
                return info

            info = AgentInfo(
                agent_id=agent_id,
                name=name or agent_id,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )
            self._agents[agent_id] = info
            logger.debug("Registered agent: %s (%s)", agent_id, info.name)
            return info

    def deregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.debug("Deregistered agent: %s", agent_id)
                return True
            return False

    def get(self, agent_id: str) -> AgentInfo | None:
        """Get agent info by ID."""
        with self._lock:
            info = self._agents.get(agent_id)
            if info:
                info.touch()
            return info

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def heartbeat(self, agent_id: str) -> bool:
        """Update agent's last_seen timestamp. Returns False if agent unknown."""
        with self._lock:
            info = self._agents.get(agent_id)
            if info:
                info.touch()
                return True
            return False

    def stale_agents(self, max_age_seconds: float = 300.0) -> list[str]:
        """Return IDs of agents not seen within the given timeout."""
        now = datetime.now()
        with self._lock:
            return [
                aid for aid, info in self._agents.items()
                if (now - info.last_seen).total_seconds() > max_age_seconds
            ]

    def resolve_conflict(self, local: Any, remote: Any,
                         local_agent_id: str = "", remote_agent_id: str = "") -> dict[str, Any]:
        """Resolve a version conflict between local and remote memory versions.

        Strategy: last-writer-wins (higher version wins).
        If versions are equal, the agent with the lexicographically larger ID wins
        (deterministic tiebreaker).

        Args:
            local: Local Memory object.
            remote: Remote Memory object.
            local_agent_id: Agent ID of the local writer.
            remote_agent_id: Agent ID of the remote writer.

        Returns:
            Dict with resolution info: winner, loser, strategy, merged.
        """
        local_version = getattr(local, "version", 0)
        remote_version = getattr(remote, "version", 0)

        if remote_version > local_version:
            winner = "remote"
            loser = "local"
            merged = remote
        elif local_version > remote_version:
            winner = "local"
            loser = "remote"
            merged = local
        else:
            # Tie: deterministic tiebreaker by agent_id
            if remote_agent_id >= local_agent_id:
                winner = "remote"
                loser = "local"
                merged = remote
            else:
                winner = "local"
                loser = "remote"
                merged = local

        return {
            "winner": winner,
            "loser": loser,
            "strategy": "last_writer_wins" if local_version != remote_version else "agent_id_tiebreaker",
            "local_version": local_version,
            "remote_version": remote_version,
            "local_agent_id": local_agent_id,
            "remote_agent_id": remote_agent_id,
            "merged": merged,
        }

    def stats(self) -> dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            return {
                "total_agents": len(self._agents),
                "agent_ids": list(self._agents.keys()),
                "stale": self.stale_agents(),
            }

    def clear(self) -> None:
        """Clear all registered agents."""
        with self._lock:
            self._agents.clear()


# Singleton
_registry: AgentRegistry | None = None
_singleton_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry singleton."""
    global _registry
    if _registry is None:
        with _singleton_lock:
            if _registry is None:
                _registry = AgentRegistry()
    return _registry


def reset_agent_registry() -> None:
    """Reset the singleton (for testing)."""
    global _registry
    with _singleton_lock:
        if _registry is not None:
            _registry.clear()
        _registry = None
