"""Galactic Zone Lifecycle for Hypotheses (Objective G).

Applies the galactic lifecycle (Core → Inner Rim → Mid Band → Outer Rim → Far Edge)
to improvement hypotheses. New proposals start in Core. Tested-and-rejected drift
outward. Validated improvements get pulled back to Core as "confirmed knowledge."

Drift rate: drift_rate = 1 / (1 + outcome_count * confidence)
Well-validated improvements resist drift.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HypothesisZone(Enum):
    """Galactic zones for hypothesis lifecycle."""
    CORE = "core"              # New, untested — high attention
    INNER_RIM = "inner_rim"    # Tested once, inconclusive
    MID_BAND = "mid_band"      # Tested and rejected
    OUTER_RIM = "outer_rim"    # Superseded by better approach
    FAR_EDGE = "far_edge"      # Deprecated / no longer relevant


# Zone ordering for drift direction (0 = core, 4 = far edge)
ZONE_ORDER = [
    HypothesisZone.CORE,
    HypothesisZone.INNER_RIM,
    HypothesisZone.MID_BAND,
    HypothesisZone.OUTER_RIM,
    HypothesisZone.FAR_EDGE,
]


@dataclass
class HypothesisState:
    """Lifecycle state of a hypothesis in the galactic map."""
    hypothesis_id: str
    zone: HypothesisZone = HypothesisZone.CORE
    outcome_count: int = 0
    success_count: int = 0
    confidence: float = 0.5
    last_evaluated: float = field(default_factory=time.time)
    drift_distance: float = 0.0  # Accumulated galactic distance (0=core, 1=far edge)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.outcome_count == 0:
            return 0.0
        return self.success_count / self.outcome_count

    @property
    def drift_rate(self) -> float:
        """How fast this hypothesis drifts outward.

        drift_rate = 1 / (1 + outcome_count * confidence)
        Well-validated, high-confidence hypotheses resist drift.
        """
        return 1.0 / (1.0 + self.outcome_count * self.confidence)


class HypothesisGalacticMap:
    """Manages the galactic zone lifecycle for improvement hypotheses.

    Zone transitions:
    - New hypothesis → CORE
    - Tested + success → stays CORE or pulled back from outer zones
    - Tested + inconclusive → INNER_RIM
    - Tested + rejected → MID_BAND
    - Superseded → OUTER_RIM
    - Deprecated → FAR_EDGE
    """

    def __init__(self) -> None:
        self._states: dict[str, HypothesisState] = {}

    def register(self, hypothesis_id: str, confidence: float = 0.5) -> HypothesisState:
        """Register a new hypothesis in the Core zone."""
        state = HypothesisState(
            hypothesis_id=hypothesis_id,
            zone=HypothesisZone.CORE,
            confidence=confidence,
        )
        self._states[hypothesis_id] = state
        return state

    def get_state(self, hypothesis_id: str) -> HypothesisState | None:
        return self._states.get(hypothesis_id)

    def record_outcome(self, hypothesis_id: str, success: bool, confidence: float | None = None) -> HypothesisZone:
        """Record an outcome and update the hypothesis's zone.

        Args:
            hypothesis_id: The hypothesis ID.
            success: Whether the outcome was successful.
            confidence: Updated confidence (if None, keeps existing).

        Returns:
            The new zone after the update.
        """
        state = self._states.get(hypothesis_id)
        if state is None:
            state = self.register(hypothesis_id)

        state.outcome_count += 1
        if success:
            state.success_count += 1
        if confidence is not None:
            state.confidence = max(0.0, min(1.0, confidence))
        state.last_evaluated = time.time()

        # Zone transitions based on outcome
        if success:
            # Success pulls toward Core
            if state.zone != HypothesisZone.CORE:
                state = self._promote(hypothesis_id)
        else:
            # Failure pushes outward
            state = self._demote(hypothesis_id)

        return state.zone

    def _promote(self, hypothesis_id: str) -> HypothesisState:
        """Move a hypothesis one zone toward Core."""
        state = self._states[hypothesis_id]
        current_idx = ZONE_ORDER.index(state.zone)
        if current_idx > 0:
            state.zone = ZONE_ORDER[current_idx - 1]
            state.drift_distance = current_idx * 0.2  # Update distance
        return state

    def _demote(self, hypothesis_id: str) -> HypothesisState:
        """Move a hypothesis one zone toward Far Edge."""
        state = self._states[hypothesis_id]
        current_idx = ZONE_ORDER.index(state.zone)
        if current_idx < len(ZONE_ORDER) - 1:
            # Apply drift rate — well-validated hypotheses resist
            if __import__("random").random() < state.drift_rate:
                state.zone = ZONE_ORDER[current_idx + 1]
                state.drift_distance = (current_idx + 1) * 0.2
        return state

    def supersede(self, hypothesis_id: str, by_id: str) -> None:
        """Mark a hypothesis as superseded by another."""
        state = self._states.get(hypothesis_id)
        if state is None:
            state = self.register(hypothesis_id)
        state.zone = HypothesisZone.OUTER_RIM
        state.drift_distance = 0.65
        state.metadata["superseded_by"] = by_id

    def deprecate(self, hypothesis_id: str) -> None:
        """Mark a hypothesis as deprecated (Far Edge)."""
        state = self._states.get(hypothesis_id)
        if state is None:
            state = self.register(hypothesis_id)
        state.zone = HypothesisZone.FAR_EDGE
        state.drift_distance = 0.85

    def get_zone_counts(self) -> dict[str, int]:
        """Get count of hypotheses in each zone."""
        counts = {z.value: 0 for z in HypothesisZone}
        for state in self._states.values():
            counts[state.zone.value] += 1
        return counts

    def get_active_hypotheses(self) -> list[str]:
        """Get IDs of hypotheses in Core and Inner Rim (active evaluation)."""
        return [
            hid for hid, state in self._states.items()
            if state.zone in (HypothesisZone.CORE, HypothesisZone.INNER_RIM)
        ]

    def get_archived_hypotheses(self) -> list[str]:
        """Get IDs of hypotheses in Outer Rim and Far Edge (archived)."""
        return [
            hid for hid, state in self._states.items()
            if state.zone in (HypothesisZone.OUTER_RIM, HypothesisZone.FAR_EDGE)
        ]

    def apply_time_drift(self) -> int:
        """Apply time-based drift to all hypotheses.

        Hypotheses with no recent outcomes drift outward at their drift_rate.

        Returns:
            Number of hypotheses that drifted.
        """
        now = time.time()
        drifted = 0
        for hid, state in self._states.items():
            # Only drift if no evaluation in the last "cycle" (simplified: 3600s)
            if now - state.last_evaluated > 3600:
                if state.zone != HypothesisZone.FAR_EDGE:
                    import random
                    if random.random() < state.drift_rate * 0.1:  # Slow time drift
                        current_idx = ZONE_ORDER.index(state.zone)
                        state.zone = ZONE_ORDER[current_idx + 1]
                        state.drift_distance = (current_idx + 1) * 0.2
                        drifted += 1
        return drifted

    def get_stats(self) -> dict[str, Any]:
        counts = self.get_zone_counts()
        total = sum(counts.values())
        return {
            "total_hypotheses": total,
            "zone_counts": counts,
            "active_count": len(self.get_active_hypotheses()),
            "archived_count": len(self.get_archived_hypotheses()),
        }
