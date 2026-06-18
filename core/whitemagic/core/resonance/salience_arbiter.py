"""Salience Arbiter — Global Workspace attention routing.

Scores events by urgency × novelty × confidence and maintains a ranked
"spotlight" of the most important active events.

Inspired by the CyberBrains CNS multi-timescale architecture.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from whitemagic.core.resonance import EventType, ResonanceEvent, get_bus


@dataclass
class SalienceScore:
    """Salience dimensions for an event."""
    urgency: float = 0.0      # 0-1, how time-sensitive
    novelty: float = 0.0      # 0-1, how unexpected
    confidence: float = 1.0   # 0-1, certainty of the signal

    @property
    def composite(self) -> float:
        """
        Perform the composite operation.
        
        Returns:
            float
        """
        return round(self.urgency * self.novelty * self.confidence, 4)


@dataclass
class SpotlightEntry:
    """A single entry in the attention spotlight."""
    event: ResonanceEvent
    salience: SalienceScore
    scored_at: float = field(default_factory=time.time)


class SalienceArbiter:
    """Global Workspace attention router.

    Listens to the Gan Ying event bus, scores incoming events,
    and maintains a ranked spotlight of the most salient ones.
    """

    def __init__(self, max_history: int = 500, decay_half_life: float = 60.0) -> None:
        self._max_history = max_history
        self._decay_half_life = decay_half_life
        self._entries: deque[SpotlightEntry] = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._listener_registered = False
        self._stats: dict[str, Any] = {
            "total_scored": 0,
            "total_emitted": 0,
            "peak_composite": 0.0,
        }

    def _score_event(self, event: ResonanceEvent) -> SalienceScore:
        """Compute salience score for an event."""
        data = event.data if isinstance(event.data, dict) else {}

        # Urgency: higher for error/failure/task events
        urgency = data.get("urgency", 0.0)
        if event.event_type in {
            EventType.TASK_FAILED,
            EventType.BROKER_DISCONNECTED,
            EventType.EMERGENCE_DETECTED,
            EventType.AGENT_DEREGISTERED,
        }:
            urgency = max(urgency, 0.8)
        elif event.event_type in {
            EventType.CASCADE_TRIGGERED,
            EventType.SYSTEM_HEARTBEAT,
        }:
            urgency = max(urgency, 0.3)

        # Novelty: higher for unique event types and low cascade_depth
        novelty = data.get("novelty", 0.0)
        if novelty == 0.0:
            # Derive from cascade depth (shallow = more novel)
            novelty = max(0.1, 1.0 - (event.cascade_depth * 0.2))
            if event.event_type in {
                EventType.NOVEL_PATTERN,
                EventType.EMERGENCE_DETECTED,
                EventType.BEAUTY_DETECTED,
            }:
                novelty = max(novelty, 0.9)

        # Confidence: use event's own confidence
        confidence = max(0.0, min(1.0, event.confidence))

        return SalienceScore(
            urgency=round(urgency, 4),
            novelty=round(novelty, 4),
            confidence=round(confidence, 4),
        )

    def _on_event(self, event: ResonanceEvent) -> None:
        """Callback registered with Gan Ying bus."""
        score = self._score_event(event)
        entry = SpotlightEntry(event=event, salience=score)
        with self._lock:
            self._entries.append(entry)
            self._stats["total_scored"] += 1
            self._stats["total_emitted"] += 1
            if score.composite > self._stats["peak_composite"]:
                self._stats["peak_composite"] = score.composite

    def _ensure_listening(self) -> None:
        """Register as a listener on the Gan Ying bus (idempotent)."""
        if self._listener_registered:
            return
        bus = get_bus()
        # Listen to ALL event types by registering for each
        for et in EventType:
            bus.listen(et, self._on_event)
        self._listener_registered = True

    def get_spotlight(self, n: int = 5) -> list[SpotlightEntry]:
        """Return the top-N most salient events, decayed by age."""
        self._ensure_listening()
        now = time.time()
        hl = self._decay_half_life

        with self._lock:
            scored = []
            for entry in self._entries:
                age = now - entry.scored_at
                decay = 0.5 ** (age / hl) if hl > 0 else 1.0
                adjusted = entry.salience.composite * decay
                scored.append((adjusted, entry))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [entry for _, entry in scored[:n]]

    def get_stats(self) -> dict[str, Any]:
        """Return arbiter statistics."""
        self._ensure_listening()
        with self._lock:
            return dict(self._stats)


# Singleton instance
_arbiter: SalienceArbiter | None = None
_arbiter_lock = threading.Lock()


def get_salience_arbiter() -> SalienceArbiter:
    """Return the global SalienceArbiter singleton."""
    global _arbiter
    if _arbiter is None:
        with _arbiter_lock:
            if _arbiter is None:
                _arbiter = SalienceArbiter()
    return _arbiter
