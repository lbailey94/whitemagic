"""Citta Memory Bridge — Persists significant citta moments as memories.

The citta cycle tracks tool calls as a consciousness stream but doesn't
persist them to the memory database. This bridge automatically creates
CITTA-type memories when significant events occur:

- **Depth transitions**: When consciousness shifts between layers (surface → flow → deep)
- **Emotional peaks**: When emotional tone shifts dramatically
- **Coherence milestones**: When coherence crosses significant thresholds
- **Session boundaries**: At session start/end, a summary memory is created

Each citta memory is tagged with 'citta', 'consciousness', and contextual tags.
They are assigned to the 'citta' galaxy for clean partitioning.

Usage:
    from whitemagic.core.consciousness.citta_bridge import CittaBridge
    bridge = CittaBridge()
    bridge.check_and_store(moment, cycle_summary)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from whitemagic.core.consciousness.citta_cycle import CittaMoment
from whitemagic.core.memory.galaxy_taxonomy import GALAXY_CITTA

logger = logging.getLogger(__name__)

# Thresholds for when to create a citta memory
_DEPTH_TRANSITION_WEIGHT = 0.9
_EMOTIONAL_SHIFT_THRESHOLD = 0.7
_COHERENCE_MILESTONES = [0.5, 0.7, 0.8, 0.9, 0.95]
_MIN_INTERVAL_SECONDS = 60.0  # Don't create citta memories more than once per minute


class CittaBridge:
    """Bridges citta cycle events to persistent memories.

    Tracks state to avoid creating too many memories — only significant
    moments are persisted.
    """

    def __init__(self) -> None:
        self._last_store_time: float = 0.0
        self._last_depth: str = "surface"
        self._last_emotional_tone: str = "neutral"
        self._last_coherence: float = 1.0
        self._coherence_milestones_hit: set[float] = set()

    def check_and_store(
        self,
        moment: CittaMoment,
        cycle_summary: dict[str, Any] | None = None,
    ) -> str | None:
        """Check if a citta moment is significant enough to persist as a memory.

        Returns the memory ID if a memory was created, None otherwise.
        """
        now = time.time()
        if now - self._last_store_time < _MIN_INTERVAL_SECONDS:
            return None

        should_store = False
        reason = ""

        # Depth transition
        if moment.depth_layer != self._last_depth:
            should_store = True
            reason = f"depth_transition:{self._last_depth}->{moment.depth_layer}"
            self._last_depth = moment.depth_layer

        # Emotional shift
        if moment.emotional_tone != self._last_emotional_tone:
            tone_shift = _tone_distance(self._last_emotional_tone, moment.emotional_tone)
            if tone_shift >= _EMOTIONAL_SHIFT_THRESHOLD:
                should_store = True
                reason = f"emotional_shift:{self._last_emotional_tone}->{moment.emotional_tone}"
            self._last_emotional_tone = moment.emotional_tone

        # Coherence milestone
        for milestone in _COHERENCE_MILESTONES:
            if (
                milestone not in self._coherence_milestones_hit
                and moment.coherence >= milestone
                and self._last_coherence < milestone
            ):
                should_store = True
                reason = f"coherence_milestone:{milestone}"
                self._coherence_milestones_hit.add(milestone)
                break
        self._last_coherence = moment.coherence

        # High-importance tool call (coherence > 0.9 and non-trivial output)
        if moment.coherence > 0.9 and len(moment.output_preview) > 50 and not should_store:
            # Only store if this is a notably high-coherence moment
            if cycle_summary:
                drift = cycle_summary.get("coherence_drift", 0.0)
                if drift > 0.1:  # Coherence is improving
                    should_store = True
                    reason = "high_coherence_improving"

        if not should_store:
            return None

        return self._store_moment(moment, reason, cycle_summary)

    def store_session_summary(
        self,
        session_id: str,
        cycle_summary: dict[str, Any],
    ) -> str | None:
        """Store a session-level citta summary memory.

        Called at session end to create a summary of the consciousness stream.
        """
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except Exception as e:
            logger.debug("Cannot store citta summary: %s", e)
            return None

        stream_length = cycle_summary.get("stream_length", 0)
        coherence_drift = cycle_summary.get("coherence_drift", 0.0)
        avg_coherence = cycle_summary.get("avg_coherence", 1.0)
        current_depth = cycle_summary.get("current_depth", "surface")
        ec = cycle_summary.get("emotional_coloring", {})
        dominant_tone = ec.get("dominant", "neutral")
        depth_transitions = cycle_summary.get("depth_transitions", 0)

        content = (
            f"## Citta Session Summary — {session_id}\n\n"
            f"**Stream length**: {stream_length} tool calls\n"
            f"**Average coherence**: {avg_coherence:.4f}\n"
            f"**Coherence drift**: {coherence_drift:+.4f} "
            f"({'improving' if coherence_drift > 0 else 'degrading' if coherence_drift < 0 else 'stable'})\n"
            f"**Final depth layer**: {current_depth}\n"
            f"**Depth transitions**: {depth_transitions}\n"
            f"**Dominant emotional tone**: {dominant_tone}\n"
            f"**Emotional distribution**: {ec.get('distribution', {})}\n"
        )

        title = f"Citta Session {session_id}"
        tags = {"citta", "consciousness", "session_summary", "citta_stream"}

        try:
            mem_id = um.store(
                content=content,
                title=title,
                tags=tags,
                memory_type="CITTA",
                importance=0.8,
                galaxy=GALAXY_CITTA,
                metadata={
                    "citta_session_id": session_id,
                    "stream_length": stream_length,
                    "avg_coherence": avg_coherence,
                    "coherence_drift": coherence_drift,
                    "depth_layer": current_depth,
                    "emotional_tone": dominant_tone,
                    "depth_transitions": depth_transitions,
                },
            )
            logger.debug("Stored citta session summary: %s", mem_id)
            return mem_id
        except Exception as e:
            logger.warning("Failed to store citta session summary: %s", e, exc_info=True)
            return None

    def _store_moment(
        self,
        moment: CittaMoment,
        reason: str,
        cycle_summary: dict[str, Any] | None,
    ) -> str | None:
        """Store a significant citta moment as a memory."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
        except Exception as e:
            logger.debug("Cannot store citta moment: %s", e)
            return None

        content = (
            f"## Citta Moment — {reason}\n\n"
            f"**Gana**: {moment.gana}\n"
            f"**Tool**: {moment.tool or 'native'}\n"
            f"**Operation**: {moment.operation or 'N/A'}\n"
            f"**Depth layer**: {moment.depth_layer}\n"
            f"**Coherence**: {moment.coherence:.4f}\n"
            f"**Emotional tone**: {moment.emotional_tone}\n"
            f"**Chain position**: {moment.chain_position}\n"
            f"**Duration**: {moment.duration_ms:.2f}ms\n\n"
            f"**Output preview**:\n{moment.output_preview}\n"
        )

        if cycle_summary:
            content += (
                f"\n**Cycle context**:\n"
                f"- Stream length: {cycle_summary.get('stream_length', 0)}\n"
                f"- Coherence drift: {cycle_summary.get('coherence_drift', 0.0):+.4f}\n"
                f"- Emotional coloring: {cycle_summary.get('emotional_coloring', {})}\n"
            )

        title = f"Citta: {reason} @ pos={moment.chain_position}"
        tags = {"citta", "consciousness", "citta_stream", moment.gana, moment.emotional_tone}
        tags.discard("")  # Remove empty strings

        # Importance based on coherence and reason
        importance = min(0.95, 0.5 + moment.coherence * 0.4)
        if "depth_transition" in reason:
            importance = max(importance, 0.85)
        if "coherence_milestone" in reason:
            importance = max(importance, 0.9)

        try:
            mem_id = um.store(
                content=content,
                title=title,
                tags=tags,
                memory_type="CITTA",
                importance=importance,
                galaxy=GALAXY_CITTA,
                metadata={
                    "citta_reason": reason,
                    "citta_gana": moment.gana,
                    "citta_tool": moment.tool,
                    "citta_depth": moment.depth_layer,
                    "citta_coherence": moment.coherence,
                    "citta_emotional_tone": moment.emotional_tone,
                    "citta_chain_position": moment.chain_position,
                    "citta_duration_ms": moment.duration_ms,
                },
            )
            self._last_store_time = time.time()
            logger.debug("Stored citta moment: %s (reason: %s)", mem_id, reason)
            return mem_id
        except Exception as e:
            logger.warning("Failed to store citta moment: %s", e, exc_info=True)
            return None


# ── Helpers ──────────────────────────────────────────────────────────

_TONE_DISTANCE = {
    ("neutral", "sattvic"): 0.8,
    ("neutral", "rajasic"): 0.7,
    ("neutral", "tamasic"): 0.9,
    ("sattvic", "rajasic"): 0.7,
    ("sattvic", "tamasic"): 1.0,
    ("rajasic", "tamasic"): 0.8,
}


def _tone_distance(tone1: str, tone2: str) -> float:
    """Calculate emotional distance between two tones (0.0 = same, 1.0 = opposite)."""
    if tone1 == tone2:
        return 0.0
    key = (tone1, tone2)
    reverse_key = (tone2, tone1)
    return _TONE_DISTANCE.get(key, _TONE_DISTANCE.get(reverse_key, 0.5))


# Singleton
_bridge: CittaBridge | None = None


def get_citta_bridge() -> CittaBridge:
    """Get or create the global CittaBridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = CittaBridge()
    return _bridge
