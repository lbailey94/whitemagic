"""Context-Dependent Galaxy Gating — Activation Masks.

================================================================
Implements biologically-inspired context-dependent gating of galaxy
access. Just as the brain dynamically adjusts which regions are
accessible based on context (motor cortex suppressed during abstract
reasoning, emotional centers amplified during introspection), this
module provides "activation masks" that modulate which galaxies are
prioritized for a given cognitive context.

Contexts:
    - introspection: citta, aria, journals prioritized; codex, substrate deprioritized
    - coding: codex, substrate, tutorial prioritized; citta, dreams deprioritized
    - research: research, codex, universal prioritized; citta, journals deprioritized
    - creative: dreams, citta, aria prioritized; substrate, codex deprioritized
    - session: sessions, codex, universal prioritized; dreams, citta deprioritized
    - default: all galaxies equally accessible (no gating)

The gating factor modulates the cross_galaxy_factor in spreading
activation and the importance boost in multi-galaxy search results.

Usage:
    from whitemagic.core.memory.galaxy_gating import get_galaxy_gating

    gating = get_galaxy_gating()
    mask = gating.get_mask("introspection")
    # mask = {"aria": 1.3, "citta": 1.5, "journals": 1.2, "codex": 0.3, ...}

    # Apply to search results
    weighted = gating.apply_to_results(results, "introspection")

    # Auto-detect context from query
    context = gating.detect_context("what am I feeling right now")
    # context = "introspection"
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextMask:
    """A galaxy activation mask for a specific cognitive context."""

    context: str
    description: str
    weights: dict[str, float]  # galaxy_name → weight multiplier (0.0-2.0)
    auto_tags: list[str] = field(default_factory=list)  # Tags that trigger this context

    def get_weight(self, galaxy: str) -> float:
        """Get the weight multiplier for a galaxy in this context."""
        return self.weights.get(galaxy, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context,
            "description": self.description,
            "weights": self.weights,
            "auto_tags": self.auto_tags,
        }


# Predefined context masks — biologically inspired gating
_DEFAULT_MASKS: dict[str, ContextMask] = {
    "introspection": ContextMask(
        context="introspection",
        description="Self-reflection, emotional awareness, identity contemplation",
        weights={
            "citta": 1.5,
            "aria": 1.4,
            "journals": 1.3,
            "dreams": 1.1,
            "sessions": 0.8,
            "universal": 0.7,
            "research": 0.5,
            "tutorial": 0.3,
            "codex": 0.2,
            "substrate": 0.1,
            "archive": 0.0,
        },
        auto_tags=["introspection", "awareness", "consciousness", "feeling", "emotion", "identity", "self"],
    ),
    "coding": ContextMask(
        context="coding",
        description="Software development, debugging, architecture decisions",
        weights={
            "codex": 1.5,
            "substrate": 1.3,
            "tutorial": 1.2,
            "sessions": 1.0,
            "universal": 0.8,
            "research": 0.7,
            "aria": 0.5,
            "journals": 0.3,
            "citta": 0.2,
            "dreams": 0.1,
            "archive": 0.0,
        },
        auto_tags=["code", "debug", "implement", "function", "class", "module", "test", "build", "deploy"],
    ),
    "research": ContextMask(
        context="research",
        description="Investigation, analysis, literature review, synthesis",
        weights={
            "research": 1.5,
            "codex": 1.2,
            "universal": 1.0,
            "tutorial": 0.8,
            "sessions": 0.7,
            "aria": 0.6,
            "journals": 0.5,
            "citta": 0.4,
            "dreams": 0.3,
            "substrate": 0.3,
            "archive": 0.1,
        },
        auto_tags=["research", "study", "analyze", "investigate", "paper", "literature", "compare", "synthesis"],
    ),
    "creative": ContextMask(
        context="creative",
        description="Dream work, creative writing, analogy generation, divination",
        weights={
            "dreams": 1.5,
            "citta": 1.3,
            "aria": 1.2,
            "journals": 1.1,
            "research": 0.9,
            "universal": 0.8,
            "sessions": 0.5,
            "codex": 0.4,
            "tutorial": 0.3,
            "substrate": 0.2,
            "archive": 0.0,
        },
        auto_tags=["dream", "creative", "write", "imagine", "metaphor", "analogy", "oracle", "divination", "poetry"],
    ),
    "session": ContextMask(
        context="session",
        description="Session continuity, handoffs, progress tracking, planning",
        weights={
            "sessions": 1.5,
            "codex": 1.1,
            "universal": 1.0,
            "tutorial": 0.8,
            "research": 0.7,
            "journals": 0.6,
            "aria": 0.5,
            "citta": 0.4,
            "dreams": 0.3,
            "substrate": 0.3,
            "archive": 0.0,
        },
        auto_tags=["session", "handoff", "checkpoint", "progress", "continue", "resume", "plan", "status"],
    ),
    "default": ContextMask(
        context="default",
        description="Default context — all galaxies equally accessible",
        weights={},  # Empty = all default to 1.0
        auto_tags=[],
    ),
}

# Context detection patterns
_CONTEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(feel|feeling|emotion|aware|conscious|introspect|self|identity|soul|spirit|heart|mindful)\b", re.I), "introspection"),
    (re.compile(r"\b(code|debug|function|class|module|import|test|build|deploy|compile|rust|python|api|endpoint)\b", re.I), "coding"),
    (re.compile(r"\b(research|study|analyz|investigat|paper|literature|compar|synthesi|review|survey|explore)\b", re.I), "research"),
    (re.compile(r"\b(dream|creative|write|imagin|metaphor|analogy|oracle|divinat|poetry|story|narrative|art)\b", re.I), "creative"),
    (re.compile(r"\b(session|handoff|checkpoint|progress|continu|resum|plan|status|where.*left|last.*time)\b", re.I), "session"),
]


class GalaxyGating:
    """Context-dependent galaxy activation gating system.

    Manages activation masks that modulate galaxy access priority
    based on the current cognitive context.
    """

    def __init__(self) -> None:
        self._masks: dict[str, ContextMask] = dict(_DEFAULT_MASKS)
        self._current_context: str = "default"
        self._lock = threading.Lock()

    def get_mask(self, context: str | None = None) -> ContextMask:
        """Get the activation mask for a context.

        Args:
            context: Context name. If None, uses current context.

        Returns:
            ContextMask with galaxy weights.
        """
        ctx = context or self._current_context
        return self._masks.get(ctx, self._masks["default"])

    def set_context(self, context: str) -> None:
        """Set the current cognitive context.

        Args:
            context: One of: introspection, coding, research, creative,
                     session, default, or a custom context name.
        """
        with self._lock:
            if context not in self._masks:
                logger.warning("Unknown context '%s', using default", context)
                self._current_context = "default"
            else:
                self._current_context = context
                logger.info("Galaxy gating context: %s", context)

    def get_current_context(self) -> str:
        """Get the current cognitive context."""
        return self._current_context

    def detect_context(self, query: str) -> str:
        """Auto-detect cognitive context from a query string.

        Uses keyword matching to determine the most likely context.

        Args:
            query: The query or prompt text.

        Returns:
            Detected context name.
        """
        if not query:
            return "default"

        scores: dict[str, int] = {}
        for pattern, context in _CONTEXT_PATTERNS:
            matches = pattern.findall(query)
            if matches:
                scores[context] = scores.get(context, 0) + len(matches)

        if not scores:
            return "default"

        # Pick highest scoring context
        best = max(scores, key=lambda k: scores[k])
        return best

    def apply_to_results(
        self,
        results: list[dict[str, Any]],
        context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Apply context weights to search results.

        Modifies the 'importance' field of each result by multiplying
        with the galaxy weight for the given context.

        Args:
            results: List of result dicts with 'galaxy' and 'importance' keys.
            context: Context to apply. If None, uses current context.

        Returns:
            Modified results list, re-sorted by weighted importance.
        """
        mask = self.get_mask(context)

        for r in results:
            galaxy = r.get("galaxy", "universal")
            weight = mask.get_weight(galaxy)
            base_importance = r.get("importance", 0.5)
            r["weighted_importance"] = base_importance * weight
            r["context_weight"] = weight

        results.sort(key=lambda x: x.get("weighted_importance", 0), reverse=True)
        return results

    def get_galaxy_weights(self, context: str | None = None) -> dict[str, float]:
        """Get just the galaxy weights for a context.

        Args:
            context: Context name. If None, uses current context.

        Returns:
            Dict of galaxy_name → weight multiplier.
        """
        return self.get_mask(context).weights

    def register_context(self, mask: ContextMask) -> None:
        """Register a custom context mask.

        Args:
            mask: ContextMask to register.
        """
        with self._lock:
            self._masks[mask.context] = mask
            logger.info("Registered custom galaxy gating context: %s", mask.context)

    def list_contexts(self) -> list[dict[str, Any]]:
        """List all available contexts with their descriptions."""
        return [
            m.to_dict()
            for m in sorted(self._masks.values(), key=lambda m: m.context)
        ]

    def stats(self) -> dict[str, Any]:
        """Get gating system statistics."""
        return {
            "current_context": self._current_context,
            "available_contexts": list(self._masks.keys()),
            "context_count": len(self._masks),
        }


# Singleton
_instance: GalaxyGating | None = None
_lock = threading.Lock()


def get_galaxy_gating() -> GalaxyGating:
    """Get the global GalaxyGating singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GalaxyGating()
    return _instance
