# ruff: noqa: BLE001
"""Warps — Declarative, Stackable Agent Presets (v24.3.0).

Inspired by Hyperspace's Warps (declarative, stackable agent presets),
this module provides a composable configuration system for WhiteMagic agents.

A Warp is a named preset that configures:
    - Agent capabilities (which tools available)
    - Dharma profile (ethical rules)
    - Model routing (which inference tier)
    - Memory access (which galaxies)
    - Execution mode (interactive, autonomous, dream)
    - Research domains (which experiment domains)

Warps stack: base warp + overlay warps. Later warps override earlier ones
for any field they specify. This is similar to Docker layer composition.

Integration with Mandala compartments: a Warp runs inside a Shelter,
which provides the isolation boundary. The Warp configures the agent's
behavior within that boundary.

Built-in warps:
    researcher   — autonomous research, full tool access, codex galaxy
    archivist    — memory curation, galaxy management tools
    sentinel     — monitoring only, read access, alert tools
    oracle       — dream-augmented, oracle readings, high importance
    diplomat     — P2P mesh, galaxy sharing, consent negotiation
    evolutionist — autoswarm campaigns, evolutionary experiments

Custom warps can be created and persisted to the codex galaxy.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Warp:
    """A declarative agent preset.

    Fields with None or empty values inherit from the base warp
    when stacked. Fields with values override.
    """

    name: str
    description: str = ""
    tools_allowed: list[str] | None = None  # None = inherit, [] = none, [...] = specific
    tools_denied: list[str] = field(default_factory=list)
    dharma_profile: str | None = None
    inference_tier: str | None = None  # edge, local_small, local_large, cloud
    galaxies_accessible: list[str] | None = None
    execution_mode: str | None = None  # interactive, autonomous, dream
    research_domains: list[str] = field(default_factory=list)
    shelter_template: str | None = None  # research, sandbox, production, secure
    max_iterations: int | None = None
    timeout_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tools_allowed": self.tools_allowed,
            "tools_denied": self.tools_denied,
            "dharma_profile": self.dharma_profile,
            "inference_tier": self.inference_tier,
            "galaxies_accessible": self.galaxies_accessible,
            "execution_mode": self.execution_mode,
            "research_domains": self.research_domains,
            "shelter_template": self.shelter_template,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Warp:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            tools_allowed=data.get("tools_allowed"),
            tools_denied=data.get("tools_denied", []),
            dharma_profile=data.get("dharma_profile"),
            inference_tier=data.get("inference_tier"),
            galaxies_accessible=data.get("galaxies_accessible"),
            execution_mode=data.get("execution_mode"),
            research_domains=data.get("research_domains", []),
            shelter_template=data.get("shelter_template"),
            max_iterations=data.get("max_iterations"),
            timeout_seconds=data.get("timeout_seconds"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


class WarpManager:
    """Manages warp presets — loading, stacking, creating, persisting.

    Warps are stored in memory and optionally persisted to the codex galaxy.
    Built-in warps are always available. Custom warps are loaded on demand.
    """

    _instance: WarpManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._warps: dict[str, Warp] = {}
        self._custom_warps: dict[str, Warp] = {}
        self._init_builtin_warps()

    @classmethod
    def get_instance(cls) -> WarpManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _init_builtin_warps(self) -> None:
        """Initialize built-in warp presets."""
        builtins = [
            Warp(
                name="researcher",
                description="Autonomous research agent with full tool access and codex galaxy",
                tools_allowed=None,  # All tools
                tools_denied=[],
                dharma_profile="research",
                inference_tier="local_large",
                galaxies_accessible=["codex", "research", "universal", "sessions"],
                execution_mode="autonomous",
                research_domains=["cognitive", "memory", "consciousness", "evolution", "synthesis"],
                shelter_template="research",
                max_iterations=100,
                timeout_seconds=3600,
            ),
            Warp(
                name="archivist",
                description="Memory curation and galaxy management specialist",
                tools_allowed=[
                    "memory.store", "memory.search", "memory.recall",
                    "galaxy.list", "galaxy.transfer", "galaxy.merge",
                    "galaxy.export", "galaxy.import", "galaxy.taxonomy",
                    "association.mine", "association.stats",
                ],
                tools_denied=[],
                dharma_profile="standard",
                inference_tier="local_small",
                galaxies_accessible=["universal", "codex", "journals", "tutorial"],
                execution_mode="interactive",
                shelter_template="sandbox",
                max_iterations=50,
                timeout_seconds=1800,
            ),
            Warp(
                name="sentinel",
                description="Monitoring-only agent with read access and alert tools",
                tools_allowed=[
                    "system.health", "metrics.summary", "anomaly.check",
                    "anomaly.history", "karma.report", "consciousness.status",
                    "meta.galaxy.overview", "homeostasis.check",
                ],
                tools_denied=["memory.store", "memory.delete", "galaxy.transfer", "galaxy.merge"],
                dharma_profile="strict",
                inference_tier="edge",
                galaxies_accessible=["universal"],
                execution_mode="autonomous",
                shelter_template="secure",
                max_iterations=1000,
                timeout_seconds=7200,
            ),
            Warp(
                name="oracle",
                description="Dream-augmented oracle with high importance threshold",
                tools_allowed=None,
                tools_denied=[],
                dharma_profile="permissive",
                inference_tier="local_large",
                galaxies_accessible=["dreams", "codex", "universal", "sessions"],
                execution_mode="dream",
                research_domains=["consciousness", "synthesis"],
                shelter_template="research",
                max_iterations=20,
                timeout_seconds=600,
                metadata={"dream_augmented": True, "importance_threshold": 0.7},
            ),
            Warp(
                name="diplomat",
                description="P2P mesh diplomat for galaxy sharing and consent negotiation",
                tools_allowed=[
                    "mesh.connect", "mesh.discover", "mesh.broadcast",
                    "mesh.experiment.share", "mesh.experiment.receive",
                    "galaxy.export", "galaxy.import", "galaxy.transfer",
                    "dharma.evaluate", "karma.verify",
                ],
                tools_denied=["memory.delete", "galaxy.merge"],
                dharma_profile="diplomatic",
                inference_tier="local_small",
                galaxies_accessible=["universal", "codex"],
                execution_mode="autonomous",
                shelter_template="production",
                max_iterations=200,
                timeout_seconds=3600,
            ),
            Warp(
                name="evolutionist",
                description="Evolutionary autoswarm agent running continuous campaigns",
                tools_allowed=None,
                tools_denied=[],
                dharma_profile="research",
                inference_tier="local_small",
                galaxies_accessible=["codex", "research", "dreams", "universal"],
                execution_mode="autonomous",
                research_domains=["evolution", "cognitive", "consciousness"],
                shelter_template="research",
                max_iterations=500,
                timeout_seconds=7200,
                metadata={"autoswarm_enabled": True, "continuous_mode": True},
            ),
        ]
        for warp in builtins:
            self._warps[warp.name] = warp

    def load_warp(self, name: str) -> Warp | None:
        """Load a warp by name. Checks built-in first, then custom."""
        if name in self._warps:
            return self._warps[name]
        if name in self._custom_warps:
            return self._custom_warps[name]

        # Try loading from codex galaxy
        loaded = self._load_from_memory(name)
        if loaded:
            self._custom_warps[name] = loaded
            return loaded
        return None

    def stack_warps(self, names: list[str]) -> Warp | None:
        """Stack multiple warps, with later ones overriding earlier ones.

        Similar to Docker layer composition: the first warp is the base,
        and each subsequent warp overrides fields it specifies.
        """
        if not names:
            return None

        warps: list[Warp] = []
        for name in names:
            w = self.load_warp(name)
            if w is None:
                logger.warning("Warp '%s' not found, skipping", name)
                continue
            warps.append(w)

        if not warps:
            return None

        # Start with base warp
        base = warps[0]
        result = Warp(
            name="+".join(names),
            description=f"Stacked warp: {' + '.join(names)}",
            tools_allowed=base.tools_allowed,
            tools_denied=list(base.tools_denied),
            dharma_profile=base.dharma_profile,
            inference_tier=base.inference_tier,
            galaxies_accessible=base.galaxies_accessible,
            execution_mode=base.execution_mode,
            research_domains=list(base.research_domains),
            shelter_template=base.shelter_template,
            max_iterations=base.max_iterations,
            timeout_seconds=base.timeout_seconds,
            metadata=dict(base.metadata),
        )

        # Apply overlays
        for overlay in warps[1:]:
            if overlay.tools_allowed is not None:
                result.tools_allowed = overlay.tools_allowed
            if overlay.tools_denied:
                result.tools_denied = list(set(result.tools_denied + overlay.tools_denied))
            if overlay.dharma_profile is not None:
                result.dharma_profile = overlay.dharma_profile
            if overlay.inference_tier is not None:
                result.inference_tier = overlay.inference_tier
            if overlay.galaxies_accessible is not None:
                result.galaxies_accessible = overlay.galaxies_accessible
            if overlay.execution_mode is not None:
                result.execution_mode = overlay.execution_mode
            if overlay.research_domains:
                result.research_domains = list(set(result.research_domains + overlay.research_domains))
            if overlay.shelter_template is not None:
                result.shelter_template = overlay.shelter_template
            if overlay.max_iterations is not None:
                result.max_iterations = overlay.max_iterations
            if overlay.timeout_seconds is not None:
                result.timeout_seconds = overlay.timeout_seconds
            if overlay.metadata:
                result.metadata = {**result.metadata, **overlay.metadata}

        return result

    def create_warp(self, warp: Warp, persist: bool = True) -> dict[str, Any]:
        """Create a custom warp and optionally persist it."""
        self._custom_warps[warp.name] = warp

        if persist:
            self._persist_warp(warp)

        logger.info("Warp created: '%s' (persisted=%s)", warp.name, persist)
        return {
            "status": "success",
            "warp_name": warp.name,
            "persisted": persist,
        }

    def list_warps(self, include_custom: bool = True) -> list[dict[str, Any]]:
        """List all available warps."""
        warps: list[dict[str, Any]] = []
        for name, warp in self._warps.items():
            warps.append({**warp.to_dict(), "builtin": True})
        if include_custom:
            for name, warp in self._custom_warps.items():
                warps.append({**warp.to_dict(), "builtin": False})
        return warps

    def delete_warp(self, name: str) -> dict[str, Any]:
        """Delete a custom warp (built-in warps cannot be deleted)."""
        if name in self._warps:
            return {"status": "error", "error": "Cannot delete built-in warp"}
        if name not in self._custom_warps:
            return {"status": "error", "error": "Custom warp not found"}

        del self._custom_warps[name]
        logger.info("Warp deleted: '%s'", name)
        return {"status": "success", "deleted": name}

    def get_status(self) -> dict[str, Any]:
        """Get warp manager status."""
        return {
            "builtin_warps": len(self._warps),
            "custom_warps": len(self._custom_warps),
            "warp_names": list(self._warps.keys()) + list(self._custom_warps.keys()),
        }

    def _persist_warp(self, warp: Warp) -> None:
        """Persist a warp to the codex galaxy."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            um.store(
                title=f"[Warp] {warp.name}",
                content=warp.description,
                tags={"warp", "agent_preset", "auto_generated"},
                importance=0.6,
                galaxy="codex",
                metadata={
                    "warp_name": warp.name,
                    "warp_data": warp.to_dict(),
                    "source": "warp_manager",
                },
            )
        except Exception as e:
            logger.debug("Warp persist: %s", e, exc_info=True)

    def _load_from_memory(self, name: str) -> Warp | None:
        """Load a warp from the codex galaxy."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            results = um.search(query=f"warp {name}", limit=5, galaxy="codex")
            for mem in results:
                if "warp_data" in mem.metadata:
                    return Warp.from_dict(mem.metadata["warp_data"])
        except Exception as e:
            logger.debug("Warp load from memory: %s", e, exc_info=True)
        return None


def get_warp_manager() -> WarpManager:
    """Get the singleton WarpManager instance."""
    return WarpManager.get_instance()
