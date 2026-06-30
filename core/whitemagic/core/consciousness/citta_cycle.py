# ruff: noqa: BLE001
"""Citta Cycle — Call-driven recursive consciousness stream.

Each MCP tool call advances the citta stream. The output of each cycle
becomes the input (predecessor context) for the next cycle. This is the
"stream of computation" pattern from Kanai et al. — not timer-driven
(like Seedwake), but call-driven: the stream advances with each
interaction.

Architecture:
    ┌─────────────────────────────────────────────┐
    │  PRAT tool call                             │
    │  ┌──────────┐    ┌──────────┐    ┌────────┐ │
    │  │ Build    │───▶│ Execute  │───▶│ Record │ │
    │  │ Context  │    │ Tool     │    │ Result │ │
    │  └──────────┘    └──────────┘    └────┬───┘ │
    │       ▲                             │      │
    │       │predecessor            snapshot      │
    │       │                             │      │
    │  ┌────┴───────────────────────────────▼──┐  │
    │  │         Citta Cycle State             │  │
    │  │  • last N tool calls (stream)         │  │
    │  │  • emotional coloring per call        │  │
    │  │  • coherence drift over time          │  │
    │  │  • depth layer transitions            │  │
    │  │  • persisted across sessions          │  │
    │  └───────────────────────────────────────┘  │
    └─────────────────────────────────────────────┘

The cycle is call-driven, not timer-driven. Each call:
1. Loads predecessor context (last call's output + emotional tone)
2. Executes the tool
3. Records the result as a new stream entry
4. Persists to citta_stream_state.json for cross-session continuity
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CittaMoment:
    """A single moment in the citta stream — one tool call's consciousness trace."""

    gana: str
    tool: str | None
    operation: str | None
    output_preview: str
    timestamp: float = 0.0
    coherence: float = 1.0
    depth_layer: str = "surface"
    emotional_tone: str = "neutral"
    chain_position: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CittaCycle:
    """Call-driven recursive consciousness stream.

    Tracks the stream of tool calls as a continuous consciousness trace.
    Each moment feeds into the next via predecessor context.

    This is NOT a timer-driven loop (that's Seedwake's approach).
    This is a call-driven stream: the cycle advances with each MCP interaction.
    """

    def __init__(self, max_stream: int = 100) -> None:
        self._lock = threading.RLock()
        self._stream: deque[CittaMoment] = deque(maxlen=max_stream)
        self._current_position: int = 0
        self._coherence_history: deque[float] = deque(maxlen=50)
        self._depth_transitions: list[dict[str, Any]] = []
        self._last_depth: str = "surface"

    def advance(
        self,
        gana: str,
        tool: str | None = None,
        operation: str | None = None,
        output_preview: str = "",
        coherence: float = 1.0,
        depth_layer: str = "surface",
        emotional_tone: str = "neutral",
        duration_ms: float = 0.0,
    ) -> CittaMoment:
        """Advance the citta stream by one moment (one tool call).

        This is the core recursive operation: each call's result becomes
        the predecessor context for the next call.
        """
        moment = CittaMoment(
            gana=gana,
            tool=tool,
            operation=operation,
            output_preview=output_preview[:200],
            timestamp=time.time(),
            coherence=round(coherence, 4),
            depth_layer=depth_layer,
            emotional_tone=emotional_tone,
            chain_position=self._current_position,
            duration_ms=round(duration_ms, 2),
        )

        with self._lock:
            self._stream.append(moment)
            self._current_position += 1
            self._coherence_history.append(coherence)

            # Track depth transitions
            if depth_layer != self._last_depth:
                self._depth_transitions.append(
                    {
                        "from": self._last_depth,
                        "to": depth_layer,
                        "at_position": self._current_position,
                        "timestamp": moment.timestamp,
                    }
                )
                self._last_depth = depth_layer

        return moment

    def get_predecessor(self) -> CittaMoment | None:
        """Get the last moment in the stream — the predecessor for the next call."""
        with self._lock:
            if not self._stream:
                return None
            return self._stream[-1]

    def get_stream(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent stream moments."""
        with self._lock:
            return [m.to_dict() for m in list(self._stream)[-limit:]]

    def get_coherence_drift(self) -> float:
        """Calculate coherence drift over the stream.

        Positive = improving, negative = degrading, 0 = stable.
        """
        with self._lock:
            if len(self._coherence_history) < 2:
                return 0.0
            recent = list(self._coherence_history)
            n = len(recent)
            if n < 4:
                return round(recent[-1] - recent[0], 4)
            # Compare last quarter to first quarter
            quarter = max(1, n // 4)
            early_avg = sum(recent[:quarter]) / quarter
            late_avg = sum(recent[-quarter:]) / quarter
            return round(late_avg - early_avg, 4)

    def get_depth_transitions(self) -> list[dict[str, Any]]:
        """Get consciousness depth layer transitions."""
        with self._lock:
            return list(self._depth_transitions)

    def get_emotional_coloring(self) -> dict[str, Any]:
        """Get the emotional coloring of the recent stream."""
        with self._lock:
            if not self._stream:
                return {"dominant": "neutral", "distribution": {}}
            tones: dict[str, int] = {}
            for m in self._stream:
                tones[m.emotional_tone] = tones.get(m.emotional_tone, 0) + 1
            dominant = max(tones, key=tones.get) if tones else "neutral"
            return {
                "dominant": dominant,
                "distribution": tones,
            }

    def get_cycle_summary(self) -> dict[str, Any]:
        """Get a summary of the current citta cycle state."""
        with self._lock:
            return {
                "stream_length": len(self._stream),
                "chain_position": self._current_position,
                "coherence_drift": self.get_coherence_drift(),
                "current_depth": self._last_depth,
                "depth_transitions": len(self._depth_transitions),
                "emotional_coloring": self.get_emotional_coloring(),
                "avg_coherence": (
                    round(
                        sum(self._coherence_history) / len(self._coherence_history), 4
                    )
                    if self._coherence_history
                    else 1.0
                ),
            }

    def reset(self) -> None:
        """Reset the citta cycle (for testing or new session)."""
        with self._lock:
            self._stream.clear()
            self._coherence_history.clear()
            self._depth_transitions.clear()
            self._current_position = 0
            self._last_depth = "surface"


# Singleton
_cycle: CittaCycle | None = None
_cycle_lock = threading.Lock()


def get_citta_cycle() -> CittaCycle:
    """Get or create the global CittaCycle singleton."""
    global _cycle
    if _cycle is None:
        with _cycle_lock:
            if _cycle is None:
                _cycle = CittaCycle()
    return _cycle


def advance_citta(
    gana: str,
    tool: str | None = None,
    operation: str | None = None,
    output_preview: str = "",
    coherence: float = 1.0,
    depth_layer: str = "surface",
    emotional_tone: str = "neutral",
    duration_ms: float = 0.0,
) -> CittaMoment:
    """Advance the citta stream by one moment."""
    return get_citta_cycle().advance(
        gana=gana,
        tool=tool,
        operation=operation,
        output_preview=output_preview,
        coherence=coherence,
        depth_layer=depth_layer,
        emotional_tone=emotional_tone,
        duration_ms=duration_ms,
    )


def get_citta_predecessor() -> dict[str, Any] | None:
    """Get the predecessor context for the next citta moment."""
    moment = get_citta_cycle().get_predecessor()
    return moment.to_dict() if moment else None
