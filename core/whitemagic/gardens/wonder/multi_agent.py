# ruff: noqa: BLE001
"""Multi-Agent Wonder — Wonder in multi-agent contexts.

Provides AgentRole enum and MultiAgentCoordinator for spawning
parallel agents across wonder gardens.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles agents can take in multi-agent wonder contexts."""

    ANALYST = "analyst"
    EXPLORER = "explorer"
    CREATOR = "creator"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"


class MultiAgentCoordinator:
    """Coordinates multiple agents for parallel wonder exploration."""

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def spawn_agent(self, role: AgentRole, label: str) -> str:
        """Spawn an agent with the given role and label. Returns agent ID."""
        self._counter += 1
        agent_id = f"agent_{self._counter:06d}"
        self._agents[agent_id] = {
            "role": role.value,
            "label": label,
            "active": True,
        }
        logger.debug("Spawned agent %s (%s/%s)", agent_id, role.value, label)
        return agent_id

    def active_count(self) -> int:
        return sum(1 for a in self._agents.values() if a["active"])

    def retire_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id]["active"] = False
            return True
        return False


class MultiAgentWonder:
    """Facilitates shared wonder across multiple agents."""

    def __init__(self) -> None:
        self._shared_wonders: list[dict[str, Any]] = []
        self._agents: set[str] = set()

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for multi-agent wonder."""
        self._agents.add(agent_id)

    def share_wonder(self, agent_id: str, wonder: str) -> dict[str, Any]:
        """Share a wonder from one agent to the collective."""
        entry = {"agent": agent_id, "wonder": wonder}
        self._shared_wonders.append(entry)
        return entry

    def collective_wonders(self) -> list[dict[str, Any]]:
        """Get all shared wonders."""
        return list(self._shared_wonders)

    def summary(self) -> dict[str, Any]:
        return {
            "registered_agents": len(self._agents),
            "shared_wonders": len(self._shared_wonders),
        }
