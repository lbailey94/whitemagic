# ruff: noqa: BLE001
"""Hemisphere Agents — Event-driven left and right hemisphere listeners.

These agents subscribe to the Gan Ying bus and can initiate or respond to
debates via the Corpus Callosum Bus. They are lightweight wrappers that
embody the cognitive stance of each hemisphere.

Usage:
    from whitemagic.core.intelligence.hemisphere_agents import (
        LeftHemisphereAgent, RightHemisphereAgent,
    )
    left = LeftHemisphereAgent()
    right = RightHemisphereAgent()
    left.start_listening()
    right.start_listening()
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class HemisphereAgent:
    """Base class for hemisphere agents."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._listening = False
        self._lock = threading.Lock()

    def start_listening(self) -> None:
        """
        Perform the start listening operation.

        Returns:
            None
        """
        with self._lock:
            if self._listening:
                return
            try:
                from whitemagic.core.resonance import EventType, get_bus
                get_bus().listen(EventType.REASONING_COMPLETE, self._on_reasoning)
                self._listening = True
                logger.info("%s hemisphere agent registered on Gan Ying bus", self.name)
            except Exception as exc:
                logger.warning("%s failed to register: %s", self.name, exc, exc_info=True)

    def _on_reasoning(self, event: Any) -> None:
        """React to reasoning completion events."""
        data = getattr(event, "data", {})
        tension = data.get("tension", 0.0)
        if tension > 0.7:
            logger.info("%s noticed high tension ({tension:.2f}) — debate may be needed", self.name, exc_info=True)

    def propose(self, topic: str) -> str:
        """Generate a position statement on a topic."""
        logger.warning("HemisphereAgent.propose called on base class — use LeftHemisphereAgent or RightHemisphereAgent")
        return f"[BASE] No stance on '{topic}' — use a concrete hemisphere agent."

    def critique(self, position: str) -> str:
        """Critique a position from the opposing hemisphere."""
        logger.warning("HemisphereAgent.critique called on base class — use LeftHemisphereAgent or RightHemisphereAgent")
        return "[BASE] No critique available — use a concrete hemisphere agent."


class LeftHemisphereAgent(HemisphereAgent):
    """Deterministic, precise, safety-first agent."""

    def __init__(self) -> None:
        super().__init__("Left")

    def propose(self, topic: str) -> str:
        """
        Perform the propose operation.

        Args:
            topic: Parameter description.

        Returns:
            str
        """
        return (
            f"[LEFT] Regarding '{topic}': We must proceed with rigorous analysis, "
            f"deterministic guarantees, and comprehensive risk mitigation."
        )

    def critique(self, position: str) -> str:
        """
        Perform the critique operation.

        Args:
            position: Parameter description.

        Returns:
            str
        """
        return (
            f"[LEFT→RIGHT] The proposal '{position[:80]}...' lacks concrete validation. "
            f"What are the failure modes? What is the rollback plan?"
        )


class RightHemisphereAgent(HemisphereAgent):
    """Stochastic, creative, possibility-oriented agent."""

    def __init__(self) -> None:
        super().__init__("Right")

    def propose(self, topic: str) -> str:
        """
        Perform the propose operation.

        Args:
            topic: Parameter description.

        Returns:
            str
        """
        return (
            f"[RIGHT] Regarding '{topic}': I see emergent patterns and novel "
            f"connections. Let's explore the adjacent possible."
        )

    def critique(self, position: str) -> str:
        """
        Perform the critique operation.

        Args:
            position: Parameter description.

        Returns:
            str
        """
        return (
            f"[RIGHT→LEFT] The stance '{position[:80]}...' is over-constrained. "
            f"Where is the room for serendipity and creative breakthrough?"
        )
