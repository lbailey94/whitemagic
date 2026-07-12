"""PersonaEngine — Cognitive Agent Generation (P5.1).

Generates diverse cognitive agents with distinct internal states:
- Coherence profile (from CoherenceMetric)
- Guna balance (sattvic/rajasic/tamasic ratio)
- Emotional baseline (from citta cycle)
- Memory galaxy (dedicated per-agent galaxy)
- Capability set (which MCP tools the agent can use)
- Dharma profile (ethical constraints)
- Depth profile (cognitive depth layer)

Unlike MiroFish personas (LLM prompts with personality descriptions),
WM personas are structured cognitive profiles with measurable internal
states that drift over simulation time.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CognitiveProfile:
    """Structured cognitive profile for a simulation agent."""

    coherence_baseline: float = 0.7
    guna_sattvic: float = 0.3
    guna_rajasic: float = 0.4
    guna_tamasic: float = 0.3
    emotional_baseline: float = 0.5  # [0=negative, 1=positive]
    depth_layer: int = 2  # 0=surface, 4=deepest
    capability_set: set[str] = field(default_factory=lambda: {"search", "recall", "think"})
    dharma_strictness: float = 0.5  # [0=permissive, 1=strict]
    memory_galaxy: str = "universal"
    curiosity: float = 0.5
    adaptability: float = 0.5
    creativity: float = 0.5

    def guna_vector(self) -> tuple[float, float, float]:
        """Return normalized guna vector."""
        total = self.guna_sattvic + self.guna_rajasic + self.guna_tamasic
        if total == 0:
            return (0.33, 0.33, 0.34)
        return (
            self.guna_sattvic / total,
            self.guna_rajasic / total,
            self.guna_tamasic / total,
        )

    def to_dict(self) -> dict[str, Any]:
        d = {
            "coherence_baseline": self.coherence_baseline,
            "guna_sattvic": self.guna_sattvic,
            "guna_rajasic": self.guna_rajasic,
            "guna_tamasic": self.guna_tamasic,
            "emotional_baseline": self.emotional_baseline,
            "depth_layer": self.depth_layer,
            "capability_set": sorted(self.capability_set),
            "dharma_strictness": self.dharma_strictness,
            "memory_galaxy": self.memory_galaxy,
            "curiosity": self.curiosity,
            "adaptability": self.adaptability,
            "creativity": self.creativity,
        }
        return d


@dataclass
class Persona:
    """A simulation persona with cognitive profile and state."""

    id: str
    name: str
    profile: CognitiveProfile
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    _state: dict[str, Any] = field(default_factory=dict)

    @property
    def coherence(self) -> float:
        return self._state.get("coherence", self.profile.coherence_baseline)

    @coherence.setter
    def coherence(self, value: float) -> None:
        self._state["coherence"] = max(0.0, min(1.0, value))

    @property
    def emotional_state(self) -> float:
        return self._state.get("emotional_state", self.profile.emotional_baseline)

    @emotional_state.setter
    def emotional_state(self, value: float) -> None:
        self._state["emotional_state"] = max(0.0, min(1.0, value))

    def drift(self, dt: float = 1.0) -> None:
        """Apply natural drift to cognitive state over simulation time."""
        # Coherence drifts toward baseline
        self.coherence += (self.profile.coherence_baseline - self.coherence) * 0.01 * dt
        # Emotional state drifts toward baseline
        self.emotional_state += (self.profile.emotional_baseline - self.emotional_state) * 0.02 * dt
        # Guna balance slowly drifts
        s, r, t = self.profile.guna_vector()
        self._state["guna_sattvic"] = s
        self._state["guna_rajasic"] = r
        self._state["guna_tamasic"] = t

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "profile": self.profile.to_dict(),
            "created_at": self.created_at,
            "state": dict(self._state),
        }


class PersonaEngine:
    """Generates and manages cognitive personas for simulation.

    Supports:
    - Random persona generation with diverse cognitive profiles
    - Cloning personas with mutations (for evolutionary simulation)
    - Importing personas from galaxy memories
    - Exporting personas to galaxy snapshots
    """

    # Persona archetypes with preset cognitive profiles
    ARCHETYPES: dict[str, CognitiveProfile] = {
        "analyst": CognitiveProfile(
            coherence_baseline=0.85, guna_sattvic=0.5, guna_rajasic=0.3, guna_tamasic=0.2,
            emotional_baseline=0.4, depth_layer=4, curiosity=0.7, creativity=0.3,
            capability_set={"search", "recall", "think", "analyze", "synthesize"},
            dharma_strictness=0.7,
        ),
        "creative": CognitiveProfile(
            coherence_baseline=0.6, guna_sattvic=0.2, guna_rajasic=0.6, guna_tamasic=0.2,
            emotional_baseline=0.7, depth_layer=3, curiosity=0.9, creativity=0.9,
            capability_set={"search", "recall", "think", "create", "dream"},
            dharma_strictness=0.3,
        ),
        "conservative": CognitiveProfile(
            coherence_baseline=0.9, guna_sattvic=0.6, guna_rajasic=0.1, guna_tamasic=0.3,
            emotional_baseline=0.5, depth_layer=2, curiosity=0.3, creativity=0.2,
            capability_set={"search", "recall", "verify"},
            dharma_strictness=0.9,
        ),
        "explorer": CognitiveProfile(
            coherence_baseline=0.65, guna_sattvic=0.3, guna_rajasic=0.5, guna_tamasic=0.2,
            emotional_baseline=0.6, depth_layer=3, curiosity=0.95, creativity=0.7,
            capability_set={"search", "recall", "think", "explore", "dream", "create"},
            dharma_strictness=0.4,
        ),
        "synthesizer": CognitiveProfile(
            coherence_baseline=0.8, guna_sattvic=0.4, guna_rajasic=0.3, guna_tamasic=0.3,
            emotional_baseline=0.6, depth_layer=4, curiosity=0.7, creativity=0.8,
            capability_set={"search", "recall", "think", "synthesize", "analyze"},
            dharma_strictness=0.5,
        ),
    }

    def __init__(self) -> None:
        self._personas: dict[str, Persona] = {}

    def create_persona(
        self,
        name: str,
        archetype: str | None = None,
        profile: CognitiveProfile | None = None,
        galaxy: str | None = None,
    ) -> Persona:
        """Create a new persona.

        Args:
            name: Persona name.
            archetype: Preset archetype name (analyst, creative, conservative, explorer, synthesizer).
            profile: Custom cognitive profile (overrides archetype).
            galaxy: Memory galaxy for this persona.

        Returns:
            Created Persona.
        """
        if profile is None:
            if archetype and archetype in self.ARCHETYPES:
                profile = self.ARCHETYPES[archetype]
            else:
                profile = CognitiveProfile()

        if galaxy:
            profile.memory_galaxy = galaxy

        pid = hashlib.sha256(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        persona = Persona(id=pid, name=name, profile=profile)
        self._personas[pid] = persona
        logger.info("Created persona %s (%s) with archetype %s", name, pid, archetype or "custom")
        return persona

    def clone_with_mutation(
        self,
        source_id: str,
        name: str,
        mutation_rate: float = 0.1,
    ) -> Persona | None:
        """Clone a persona with random mutations to its cognitive profile.

        Args:
            source_id: ID of the source persona.
            name: Name for the cloned persona.
            mutation_rate: How much to mutate each parameter [0, 1].

        Returns:
            New mutated Persona, or None if source not found.
        """
        import random

        source = self._personas.get(source_id)
        if source is None:
            return None

        src = source.profile
        mutated = CognitiveProfile(
            coherence_baseline=max(0.0, min(1.0, src.coherence_baseline + random.gauss(0, mutation_rate))),
            guna_sattvic=max(0.0, src.guna_sattvic + random.gauss(0, mutation_rate * 0.5)),
            guna_rajasic=max(0.0, src.guna_rajasic + random.gauss(0, mutation_rate * 0.5)),
            guna_tamasic=max(0.0, src.guna_tamasic + random.gauss(0, mutation_rate * 0.5)),
            emotional_baseline=max(0.0, min(1.0, src.emotional_baseline + random.gauss(0, mutation_rate))),
            depth_layer=max(0, min(4, src.depth_layer + random.choice([-1, 0, 0, 1]))),
            capability_set=set(src.capability_set),
            dharma_strictness=max(0.0, min(1.0, src.dharma_strictness + random.gauss(0, mutation_rate))),
            memory_galaxy=src.memory_galaxy,
            curiosity=max(0.0, min(1.0, src.curiosity + random.gauss(0, mutation_rate))),
            adaptability=max(0.0, min(1.0, src.adaptability + random.gauss(0, mutation_rate))),
            creativity=max(0.0, min(1.0, src.creativity + random.gauss(0, mutation_rate))),
        )
        return self.create_persona(name, profile=mutated, galaxy=mutated.memory_galaxy)

    def get_persona(self, persona_id: str) -> Persona | None:
        return self._personas.get(persona_id)

    def list_personas(self) -> list[Persona]:
        return list(self._personas.values())

    def remove_persona(self, persona_id: str) -> bool:
        return self._personas.pop(persona_id, None) is not None

    def stats(self) -> dict[str, Any]:
        archetypes = {}
        for p in self._personas.values():
            for name, arch in self.ARCHETYPES.items():
                if p.profile is arch:
                    archetypes[name] = archetypes.get(name, 0) + 1
        return {
            "total_personas": len(self._personas),
            "archetype_distribution": archetypes,
        }


# Singleton
_engine: PersonaEngine | None = None


def get_persona_engine() -> PersonaEngine:
    global _engine
    if _engine is None:
        _engine = PersonaEngine()
    return _engine
