"""WorldModelBuilder — Simulation Environment (P5.1).

Builds simulation worlds from seed documents. Ingests into a dedicated
simulation galaxy, extracts entities via association miner, builds
knowledge graph using HNSW + FTS5, defines simulation rules as Dharma
profiles. Supports multiple simultaneous world models via galaxy
isolation. Snapshot/restore for branching trajectories.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorldEntity:
    """An entity in the simulation world."""
    id: str
    name: str
    entity_type: str  # person, concept, event, object, location
    properties: dict[str, Any] = field(default_factory=dict)
    relations: list[tuple[str, str]] = field(default_factory=list)  # (relation_type, target_id)


@dataclass
class SimulationRule:
    """A rule governing the simulation world."""
    id: str
    name: str
    description: str
    rule_type: str  # constraint, dynamics, interaction, decay
    parameters: dict[str, Any] = field(default_factory=dict)
    dharma_profile: dict[str, float] = field(default_factory=dict)


@dataclass
class WorldModel:
    """A simulation world model."""
    id: str
    name: str
    galaxy: str  # dedicated simulation galaxy
    entities: dict[str, WorldEntity] = field(default_factory=dict)
    rules: dict[str, SimulationRule] = field(default_factory=dict)
    seed_documents: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    _state: dict[str, Any] = field(default_factory=dict)

    @property
    def tick(self) -> int:
        return self._state.get("tick", 0)

    def advance_tick(self) -> int:
        self._state["tick"] = self.tick + 1
        return self._state["tick"]

    def add_entity(self, entity: WorldEntity) -> None:
        self.entities[entity.id] = entity

    def add_rule(self, rule: SimulationRule) -> None:
        self.rules[rule.id] = rule

    def get_entity(self, entity_id: str) -> WorldEntity | None:
        return self.entities.get(entity_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "galaxy": self.galaxy,
            "entity_count": len(self.entities),
            "rule_count": len(self.rules),
            "seed_documents": self.seed_documents,
            "created_at": self.created_at,
            "tick": self.tick,
        }


class WorldModelBuilder:
    """Builds simulation worlds from seed documents.

    Pipeline:
    1. Ingest seed documents into a dedicated simulation galaxy
    2. Extract entities via association miner
    3. Build knowledge graph using HNSW + FTS5
    4. Define simulation rules as Dharma profiles
    5. Support branching via galaxy snapshot/restore
    """

    def __init__(self) -> None:
        self._worlds: dict[str, WorldModel] = {}

    def create_world(
        self,
        name: str,
        seed_documents: list[str] | None = None,
        galaxy: str | None = None,
    ) -> WorldModel:
        """Create a new simulation world.

        Args:
            name: World name.
            seed_documents: List of seed document contents to ingest.
            galaxy: Galaxy to use for this world (default: simulation/<name>).

        Returns:
            Created WorldModel.
        """
        galaxy_name = galaxy or f"simulation/{name}"
        wid = hashlib.sha256(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        world = WorldModel(id=wid, name=name, galaxy=galaxy_name)
        self._worlds[wid] = world

        # Ingest seed documents
        if seed_documents:
            self._ingest_seeds(world, seed_documents)

        logger.info("Created world %s (%s) with %d seed documents", name, wid, len(seed_documents or []))
        return world

    def _ingest_seeds(self, world: WorldModel, documents: list[str]) -> None:
        """Ingest seed documents into the world's galaxy and extract entities."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()

            for i, doc in enumerate(documents):
                # Store in simulation galaxy
                from whitemagic.core.memory.unified_types import MemoryType
                mem = um.store(
                    content=doc,
                    title=f"seed_{world.name}_{i}",
                    galaxy=world.galaxy,
                    memory_type=MemoryType.LONG_TERM,
                    importance=0.8,
                    tags={"seed", "simulation", world.name},
                )
                world.seed_documents.append(mem.id)

                # Extract simple entities from document
                self._extract_entities(world, doc, i)

        except Exception as e:
            logger.warning("Seed ingestion failed (non-fatal): %s", e, exc_info=True)

    def _extract_entities(self, world: WorldModel, doc: str, doc_idx: int) -> None:
        """Extract simple entities from a document.

        This is a lightweight extraction — the association miner does
        the heavy lifting. Here we just identify key terms.
        """
        import re

        # Simple capitalized word extraction for entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', doc)
        seen = set()
        for ent_name in entities:
            if ent_name.lower() in seen or len(ent_name) < 3:
                continue
            seen.add(ent_name.lower())
            eid = hashlib.sha256(f"{world.id}_{ent_name}".encode()).hexdigest()[:8]
            if eid not in world.entities:
                world.add_entity(WorldEntity(
                    id=eid,
                    name=ent_name,
                    entity_type="concept",
                    properties={"source_doc": doc_idx},
                ))

    def add_rule(
        self,
        world_id: str,
        name: str,
        description: str,
        rule_type: str = "dynamics",
        parameters: dict[str, Any] | None = None,
        dharma_profile: dict[str, float] | None = None,
    ) -> SimulationRule | None:
        """Add a simulation rule to a world."""
        world = self._worlds.get(world_id)
        if world is None:
            return None

        rid = hashlib.sha256(f"{world_id}_{name}".encode()).hexdigest()[:8]
        rule = SimulationRule(
            id=rid,
            name=name,
            description=description,
            rule_type=rule_type,
            parameters=parameters or {},
            dharma_profile=dharma_profile or {"harm": 0.0, "benefit": 1.0},
        )
        world.add_rule(rule)
        return rule

    def get_world(self, world_id: str) -> WorldModel | None:
        return self._worlds.get(world_id)

    def list_worlds(self) -> list[WorldModel]:
        return list(self._worlds.values())

    def branch_world(self, world_id: str, branch_name: str) -> WorldModel | None:
        """Create a branch of an existing world via galaxy snapshot/restore.

        Args:
            world_id: Source world ID.
            branch_name: Name for the branched world.

        Returns:
            New branched WorldModel, or None if source not found.
        """
        source = self._worlds.get(world_id)
        if source is None:
            return None

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            snapshot = um.galaxy_snapshot(galaxy=source.galaxy)
            branch_galaxy = f"simulation/{branch_name}"
            um.galaxy_restore(snapshot, target_galaxy=branch_galaxy, merge=True)
        except Exception as e:
            logger.warning("World branch failed (non-fatal): %s", e, exc_info=True)

        branch = self.create_world(
            name=branch_name,
            galaxy=branch_galaxy,
        )
        # Copy entities and rules
        branch.entities = dict(source.entities)
        branch.rules = dict(source.rules)
        return branch

    def stats(self) -> dict[str, Any]:
        return {
            "total_worlds": len(self._worlds),
            "total_entities": sum(len(w.entities) for w in self._worlds.values()),
            "total_rules": sum(len(w.rules) for w in self._worlds.values()),
        }


# Singleton
_builder: WorldModelBuilder | None = None


def get_world_model_builder() -> WorldModelBuilder:
    global _builder
    if _builder is None:
        _builder = WorldModelBuilder()
    return _builder
