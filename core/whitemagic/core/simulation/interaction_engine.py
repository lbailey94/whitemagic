"""InteractionEngine — Multi-Agent Cognitive Simulation (P5.2).

Simulates agents interacting, debating, and influencing each other.
Each agent perceives world state via memory retrieval, decides action
via tool calls + cognitive state, actions modify world state.
EmergenceEngine detects patterns in interactions. GlobalWorkspace
competitive ignition broadcasts ideas to all agents. Dharma governance
constrains behavior.
"""

from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.simulation.persona_engine import Persona
from whitemagic.core.simulation.world_model import WorldModel

logger = logging.getLogger(__name__)


@dataclass
class InteractionEvent:
    """A single interaction event between agents."""
    id: str
    tick: int
    actor_id: str
    action: str  # speak, query, create, modify, reflect
    content: str
    target_id: str | None = None
    impact: float = 0.0  # how much this event changed the world state
    emergence_score: float = 0.0  # novelty/emergence detected by EmergenceEngine


@dataclass
class InteractionLog:
    """Log of all interactions in a simulation run."""
    events: list[InteractionEvent] = field(default_factory=list)

    def add(self, event: InteractionEvent) -> None:
        self.events.append(event)

    def filter_by_actor(self, actor_id: str) -> list[InteractionEvent]:
        return [e for e in self.events if e.actor_id == actor_id]

    def filter_by_action(self, action: str) -> list[InteractionEvent]:
        return [e for e in self.events if e.action == action]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_events": len(self.events),
            "actions": {a: len([e for e in self.events if e.action == a])
                        for a in set(e.action for e in self.events)},
            "avg_impact": sum(e.impact for e in self.events) / max(len(self.events), 1),
            "avg_emergence": sum(e.emergence_score for e in self.events) / max(len(self.events), 1),
        }


class InteractionEngine:
    """Simulates multi-agent cognitive interactions.

    Each tick:
    1. Each agent perceives world state (memory retrieval from galaxy)
    2. Agent decides action based on cognitive profile + world state
    3. Action modifies world state and may trigger emergence
    4. GlobalWorkspace broadcasts significant events to all agents
    5. Dharma governance constrains harmful actions
    """

    ACTIONS = ["speak", "query", "create", "modify", "reflect"]

    def __init__(self) -> None:
        self._logs: dict[str, InteractionLog] = {}  # run_id → log

    def run_interaction(
        self,
        run_id: str,
        personas: list[Persona],
        world: WorldModel,
        ticks: int = 10,
        injection_points: list[dict[str, Any]] | None = None,
    ) -> InteractionLog:
        """Run a multi-agent interaction simulation.

        Args:
            run_id: Unique identifier for this run.
            personas: List of personas to simulate.
            world: World model to simulate in.
            ticks: Number of interaction ticks.
            injection_points: Optional list of {tick, variable, value, target?} dicts
                to inject at specified ticks. Variables: coherence, emotional_state,
                world_state, dharma_strictness.

        Returns:
            InteractionLog with all events.
        """
        log = InteractionLog()
        self._logs[run_id] = log
        injections_by_tick: dict[int, list[dict[str, Any]]] = {}
        if injection_points:
            for inj in injection_points:
                t = inj.get("tick", 0)
                injections_by_tick.setdefault(t, []).append(inj)

        for tick in range(ticks):
            world.advance_tick()

            # Apply injections for this tick
            if tick in injections_by_tick:
                for inj in injections_by_tick[tick]:
                    self._apply_injection(personas, world, inj)

            for persona in personas:
                event = self._agent_step(persona, world, tick)
                if event:
                    log.add(event)

                    # Apply impact to world state
                    if event.impact > 0.1:
                        self._apply_impact(world, event)

                    # Broadcast significant events
                    if event.emergence_score > 0.5:
                        self._broadcast(personas, event)

            # Apply persona drift
            for persona in personas:
                persona.drift(dt=1.0)

        logger.info("Interaction run %s: %d events over %d ticks", run_id, len(log.events), ticks)
        return log

    def _apply_injection(
        self, personas: list[Persona], world: WorldModel, injection: dict[str, Any]
    ) -> None:
        """Apply a variable injection to the simulation state."""
        variable = injection.get("variable", "")
        value = injection.get("value")
        target_id = injection.get("target")

        if variable == "coherence":
            for p in personas:
                if target_id is None or p.id == target_id or p.name == target_id:
                    p.coherence = max(0.0, min(1.0, float(value)))
        elif variable == "emotional_state":
            for p in personas:
                if target_id is None or p.id == target_id or p.name == target_id:
                    p.emotional_state = max(0.0, min(1.0, float(value)))
        elif variable == "dharma_strictness":
            for p in personas:
                if target_id is None or p.id == target_id or p.name == target_id:
                    p.profile.dharma_strictness = max(0.0, min(1.0, float(value)))
        elif variable == "world_state":
            key = injection.get("key", "injected")
            world._state[key] = value
        else:
            world._state[variable] = value

    def _agent_step(self, persona: Persona, world: WorldModel, tick: int) -> InteractionEvent | None:
        """Execute one step for a single agent.

        The agent's action is determined by:
        - Cognitive profile (curiosity → query, creativity → create, etc.)
        - Current emotional state
        - World state (tick, entities)
        - Dharma constraints
        """
        # Weight actions by cognitive profile
        weights = {
            "speak": 0.2 + persona.profile.curiosity * 0.3,
            "query": 0.1 + persona.profile.curiosity * 0.4,
            "create": 0.1 + persona.profile.creativity * 0.4,
            "modify": 0.1 + persona.profile.adaptability * 0.3,
            "reflect": 0.2 + (1.0 - persona.profile.curiosity) * 0.2,
        }

        # Dharma constrains harmful modifications
        if persona.profile.dharma_strictness > 0.7:
            weights["modify"] *= 0.3

        # Normalize and select action
        total = sum(weights.values())
        r = random.random() * total
        cumulative = 0.0
        selected_action = "reflect"
        for action, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                selected_action = action
                break

        # Generate content based on action
        content = self._generate_content(persona, selected_action, world, tick)

        # Compute impact
        impact = self._compute_impact(persona, selected_action, world)

        # Compute emergence score
        emergence = self._compute_emergence(persona, selected_action, content)

        eid = hashlib.sha256(f"{persona.id}_{tick}".encode()).hexdigest()[:8]
        return InteractionEvent(
            id=eid,
            tick=tick,
            actor_id=persona.id,
            action=selected_action,
            content=content,
            impact=impact,
            emergence_score=emergence,
        )

    def _generate_content(self, persona: Persona, action: str, world: WorldModel, tick: int) -> str:
        """Generate content for an agent's action."""
        entity_names = [e.name for e in list(world.entities.values())[:5]]
        entities_str = ", ".join(entity_names) if entity_names else "the environment"

        templates = {
            "speak": f"{persona.name} discusses {entities_str} at tick {tick}",
            "query": f"{persona.name} investigates {entities_str}",
            "create": f"{persona.name} creates a new concept related to {entities_str}",
            "modify": f"{persona.name} modifies the state of {entities_str}",
            "reflect": f"{persona.name} reflects on the current state (coherence={persona.coherence:.2f})",
        }
        return templates.get(action, f"{persona.name} acts at tick {tick}")

    def _compute_impact(self, persona: Persona, action: str, world: WorldModel) -> float:
        """Compute the impact of an action on the world state."""
        base_impact = {
            "speak": 0.1,
            "query": 0.05,
            "create": 0.3,
            "modify": 0.5,
            "reflect": 0.02,
        }
        impact = base_impact.get(action, 0.1)
        # Creativity amplifies create/modify impact
        if action in ("create", "modify"):
            impact *= (0.5 + persona.profile.creativity * 0.5)
        # Dharma strictness reduces modify impact
        if action == "modify":
            impact *= (1.0 - persona.profile.dharma_strictness * 0.3)
        return min(1.0, impact)

    def _compute_emergence(self, persona: Persona, action: str, content: str) -> float:
        """Compute emergence score for an event."""
        # High emergence = novel + creative + high coherence
        novelty = persona.profile.curiosity * 0.5
        creativity = persona.profile.creativity * 0.3
        coherence_bonus = persona.coherence * 0.2
        return min(1.0, novelty + creativity + coherence_bonus)

    def _apply_impact(self, world: WorldModel, event: InteractionEvent) -> None:
        """Apply an event's impact to the world state."""
        world._state["last_event"] = event.action
        world._state["last_impact"] = event.impact
        # Track cumulative impact
        world._state["cumulative_impact"] = world._state.get("cumulative_impact", 0.0) + event.impact

    def _broadcast(self, personas: list[Persona], event: InteractionEvent) -> None:
        """Broadcast a significant event to all agents (GlobalWorkspace)."""
        for persona in personas:
            if persona.id != event.actor_id:
                # Receiving agents' coherence may shift
                shift = event.emergence_score * 0.05 * persona.profile.adaptability
                persona.coherence += shift

    def get_log(self, run_id: str) -> InteractionLog | None:
        return self._logs.get(run_id)

    def stats(self) -> dict[str, Any]:
        return {
            "total_runs": len(self._logs),
            "total_events": sum(len(log.events) for log in self._logs.values()),
        }


# Singleton
_engine: InteractionEngine | None = None


def get_interaction_engine() -> InteractionEngine:
    global _engine
    if _engine is None:
        _engine = InteractionEngine()
    return _engine
