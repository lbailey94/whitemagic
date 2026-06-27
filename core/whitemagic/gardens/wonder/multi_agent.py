# ruff: noqa: BLE001
"""Multi-Agent Wonder — Wonder in multi-agent contexts."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


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
