"""Elixir Actor-Based Concurrent Outcome Processing (Objective M).

Models the Elixir GenServer actor pattern for concurrent, fault-tolerant
outcome processing. Each hypothesis gets its own "actor" that independently
tracks state and updates beliefs.

In Python, this is simulated with independent state objects that could
be distributed across processes. The design maps directly to Elixir GenServers.

Actor state: {prior, posterior, outcome_count, confidence, bandit_params}
Messages: {:outcome, success, gain}, {:query, field}, {:transfer, from_hypothesis}
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from whitemagic.core.evolution._elixir_actor_bridge import ElixirActorBridge

    _elixir_bridge: ElixirActorBridge | None = ElixirActorBridge()
except ImportError:
    _elixir_bridge = None


@dataclass
class HypothesisActor:
    """Simulated Elixir GenServer for a single hypothesis.

    In Elixir, this would be a GenServer process. In Python, it's an
    independent state object that can be pickled and distributed.
    """

    hypothesis_id: str
    prior: float = 0.5
    posterior: float = 0.5
    outcome_count: int = 0
    success_count: int = 0
    confidence: float = 0.5
    alpha: float = 1.0  # Beta distribution parameter
    beta: float = 1.0  # Beta distribution parameter
    last_update: float = field(default_factory=time.time)
    mailbox: list[tuple[str, Any]] = field(default_factory=list)

    def handle_outcome(self, success: bool, gain: float = 0.0) -> dict[str, Any]:
        """Handle {:outcome, success, gain} message.

        Updates posterior via Bayesian update of Beta distribution.
        """
        self.outcome_count += 1
        if success:
            self.success_count += 1
            self.alpha += 1.0
        else:
            self.beta += 1.0

        # Posterior mean of Beta(α, β)
        self.posterior = self.alpha / (self.alpha + self.beta)

        # Confidence increases with more observations
        total = self.alpha + self.beta
        self.confidence = 1.0 - 1.0 / (1.0 + total * 0.1)

        self.last_update = time.time()

        return {
            "posterior": self.posterior,
            "confidence": self.confidence,
            "outcome_count": self.outcome_count,
            "success_rate": self.success_count / self.outcome_count
            if self.outcome_count > 0
            else 0.0,
        }

    def handle_query(self, field_name: str) -> Any:
        """Handle {:query, field} message."""
        return getattr(self, field_name, None)

    def handle_transfer(self, from_actor: HypothesisActor, weight: float = 0.5) -> None:
        """Handle {:transfer, from_hypothesis} message.

        Transfers beliefs from another hypothesis actor.
        """
        blended_prior = weight * from_actor.prior + (1 - weight) * self.prior
        blended_alpha = weight * from_actor.alpha + (1 - weight) * self.alpha
        blended_beta = weight * from_actor.beta + (1 - weight) * self.beta

        self.prior = blended_prior
        self.alpha = max(0.1, blended_alpha)
        self.beta = max(0.1, blended_beta)
        self.posterior = self.alpha / (self.alpha + self.beta)

    def send(self, message: tuple[str, Any]) -> None:
        """Send a message to this actor's mailbox."""
        self.mailbox.append(message)

    def process_mailbox(self) -> list[dict[str, Any]]:
        """Process all messages in the mailbox."""
        results = []
        while self.mailbox:
            msg_type, payload = self.mailbox.pop(0)
            if msg_type == "outcome":
                success, gain = payload
                results.append(self.handle_outcome(success, gain))
            elif msg_type == "query":
                results.append({"field": payload, "value": self.handle_query(payload)})
            elif msg_type == "transfer":
                from_actor, weight = payload
                self.handle_transfer(from_actor, weight)
                results.append({"transferred": True})
        return results


class ActorSupervisor:
    """Supervises hypothesis actors with fault tolerance.

    In Elixir, this would be a Supervisor tree. In Python, it tracks
    actors and can restart failed ones.
    """

    def __init__(self) -> None:
        self._actors: dict[str, HypothesisActor] = {}
        self._failed: set[str] = set()
        self._restart_count: dict[str, int] = {}
        self._use_elixir = _elixir_bridge is not None and _elixir_bridge.is_available()

    def start_actor(self, hypothesis_id: str, prior: float = 0.5) -> HypothesisActor:
        """Start a new actor for a hypothesis."""
        if self._use_elixir:
            result = _elixir_bridge.call(
                "start_actor", hypothesis_id=hypothesis_id, prior=prior
            )
            if result is not None:
                logger.debug("Started Elixir actor for %s", hypothesis_id)
        # Always create Python-side actor for local state tracking
        actor = HypothesisActor(hypothesis_id=hypothesis_id, prior=prior)
        self._actors[hypothesis_id] = actor
        return actor

    def get_actor(self, hypothesis_id: str) -> HypothesisActor | None:
        return self._actors.get(hypothesis_id)

    def send_outcome(
        self, hypothesis_id: str, success: bool, gain: float = 0.0
    ) -> dict[str, Any] | None:
        """Send an outcome message to an actor."""
        if self._use_elixir:
            result = _elixir_bridge.call(
                "send_outcome", hypothesis_id=hypothesis_id, success=success, gain=gain
            )
            if result is not None:
                # Update Python-side actor state too for consistency
                actor = self._actors.get(hypothesis_id)
                if actor is not None:
                    actor.handle_outcome(success, gain)
                return result
        actor = self._actors.get(hypothesis_id)
        if actor is None:
            return None
        return actor.handle_outcome(success, gain)

    def broadcast_outcome(
        self, success: bool, gain: float = 0.0
    ) -> dict[str, dict[str, Any]]:
        """Broadcast an outcome to all actors (for global updates)."""
        results = {}
        for hid, actor in self._actors.items():
            results[hid] = actor.handle_outcome(success, gain)
        return results

    def transfer_belief(self, from_id: str, to_id: str, weight: float = 0.5) -> bool:
        """Transfer beliefs from one actor to another."""
        from_actor = self._actors.get(from_id)
        to_actor = self._actors.get(to_id)
        if from_actor is None or to_actor is None:
            return False
        to_actor.handle_transfer(from_actor, weight)
        return True

    def restart_actor(self, hypothesis_id: str) -> HypothesisActor | None:
        """Restart a failed actor with default state."""
        prior = 0.5
        if hypothesis_id in self._actors:
            prior = self._actors[hypothesis_id].prior
        actor = self.start_actor(hypothesis_id, prior=prior)
        self._restart_count[hypothesis_id] = (
            self._restart_count.get(hypothesis_id, 0) + 1
        )
        self._failed.discard(hypothesis_id)
        return actor

    def mark_failed(self, hypothesis_id: str) -> None:
        """Mark an actor as failed."""
        self._failed.add(hypothesis_id)

    def get_active_count(self) -> int:
        return len(self._actors) - len(self._failed)

    def get_all_posteriors(self) -> dict[str, float]:
        """Get posterior for all actors."""
        return {hid: actor.posterior for hid, actor in self._actors.items()}

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_actors": len(self._actors),
            "active_actors": self.get_active_count(),
            "failed_actors": len(self._failed),
            "total_outcomes": sum(a.outcome_count for a in self._actors.values()),
            "restarts": sum(self._restart_count.values()),
        }
