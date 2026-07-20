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
4. Persists to stream.jsonl for cross-session continuity
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from whitemagic.core.consciousness.citta_vector import (
    CittaTrajectory,
    CittaVector,
)

logger = logging.getLogger(__name__)

# ── Stream persistence paths ──────────────────────────────────────────────
_CITTA_DIR: Path = Path(os.environ.get("WM_STATE_ROOT", "/tmp/whitemagic")) / "citta"
_STREAM_FILE: Path = _CITTA_DIR / "stream.jsonl"
_PERSIST_INTERVAL: int = 5


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
    neuro_signals: dict[str, float] | None = None
    vector: CittaVector | None = None
    session_seq: int | None = None  # WI 11: cross-ref with session recorder

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.vector is not None:
            d["vector"] = self.vector.to_dict()
        else:
            d["vector"] = None
        return d


def build_output_digest(result: Any) -> str:
    """Build a compact digest from a tool result for the citta stream.

    Extracts key fields from a dict result, or returns the string representation
    for non-dict results. This is what gets passed as output_preview to advance().
    """
    if not isinstance(result, dict):
        return str(result) if result else ""
    parts: list[str] = []
    for key in ("status", "tool", "note", "message", "error_code"):
        if key in result:
            parts.append(f"{key}={result[key]}")
    if not parts:
        return json.dumps(result, default=str)[:200]
    return "; ".join(parts)


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
        self._persist_counter: int = 0
        self._trajectory: CittaTrajectory = CittaTrajectory()
        self._last_ignition_check: int = 0
        self._load_stream()

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
        neuro_signals: dict[str, float] | None = None,
        session_seq: int | None = None,
    ) -> CittaMoment:
        """Advance the citta stream by one moment (one tool call).

        This is the core recursive operation: each call's result becomes
        the predecessor context for the next call.

        If neuro_signals is None, auto-computes from the neuro sensorium.
        """
        if neuro_signals is None:
            neuro_signals = _get_neuro_enrichment()

        # Pull per-dimension coherence scores for richer vector geometry
        coherence_scores: dict[str, float] | None = None
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric
            cm = get_coherence_metric()
            if cm.scores and any(v > 0 for v in cm.scores.values()):
                # Scale per-dimension scores by the moment's coherence scalar
                # and introduce per-dimension variation based on moment properties
                # so the 8D subspace has true geometric diversity
                scale = max(0.0, min(1.0, float(coherence)))
                base = {k: v * scale for k, v in cm.scores.items()}

                # Per-dimension modulation based on moment properties
                # emotional_attunement: higher for non-neutral tones
                tone_lower = emotional_tone.lower()
                if tone_lower not in ("neutral", "calm", "clear"):
                    base["emotional_attunement"] = min(1.0, base["emotional_attunement"] * 1.15)
                else:
                    base["emotional_attunement"] = base["emotional_attunement"] * 0.85

                # context_continuity: higher for flow/dream depths
                if depth_layer in ("flow", "dream"):
                    base["context_continuity"] = min(1.0, base["context_continuity"] * 1.2)
                else:
                    base["context_continuity"] = base["context_continuity"] * 0.8

                # capability_awareness: varies with tool type
                if tool and "bridge" in tool.lower():
                    base["capability_awareness"] = min(1.0, base["capability_awareness"] * 1.1)
                elif tool and "scan" in tool.lower():
                    base["capability_awareness"] = min(1.0, base["capability_awareness"] * 1.05)

                # goal_alignment: higher for determined/engaged tones
                if tone_lower in ("determined", "engaged", "active"):
                    base["goal_alignment"] = min(1.0, base["goal_alignment"] * 1.1)

                # temporal_orientation: lower for dream depth (time distortion)
                if depth_layer == "dream":
                    base["temporal_orientation"] = base["temporal_orientation"] * 0.7

                # relationship_awareness: higher for cross-galaxy operations
                if operation and "bridge" in operation.lower():
                    base["relationship_awareness"] = min(1.0, base["relationship_awareness"] * 1.15)

                coherence_scores = base
        except Exception:
            pass

        vec = CittaVector.from_moment(
            coherence=coherence,
            depth_layer=depth_layer,
            emotional_tone=emotional_tone,
            neuro_signals=neuro_signals,
            coherence_scores=coherence_scores,
        )

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
            neuro_signals=neuro_signals,
            vector=vec,
            session_seq=session_seq,
        )

        with self._lock:
            self._stream.append(moment)
            self._current_position += 1
            self._coherence_history.append(coherence)
            self._trajectory.append(vec)

            # Feed emotional tone to guna balance system
            try:
                from whitemagic.core.consciousness.guna_balance import get_guna_balance
                get_guna_balance().record_tone(emotional_tone)
            except Exception:
                pass

            # Track depth transitions
            depth_changed = False
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
                depth_changed = True

            # Throttled persistence — every _PERSIST_INTERVAL calls
            self._persist_counter += 1
            if self._persist_counter >= _PERSIST_INTERVAL or depth_changed:
                self._persist_stream()

        # Phase 4.1: Check for ignition clusters and trigger action loop if threshold exceeded
        self._check_ignition_trigger()

        return moment

    def get_predecessor(self) -> CittaMoment | None:
        """Get the last moment in the stream — the predecessor for the next call."""
        with self._lock:
            if not self._stream:
                return None
            return self._stream[-1]

    def get_predecessor_context(self) -> dict[str, Any] | None:
        """Get the predecessor context as a dict for the next call."""
        moment = self.get_predecessor()
        return moment.to_dict() if moment else None

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

    def get_trajectory(self) -> CittaTrajectory:
        """Get the citta vector trajectory for geometric analysis."""
        with self._lock:
            return self._trajectory

    def get_ignition_events(self, threshold: float = 2.0) -> list[dict[str, Any]]:
        """Detect consciousness ignition events in the vector trajectory.

        Ignitions are sudden large displacements in the 16D citta space,
        analogous to the 'global workspace ignition' in GWT — the moment
        a representation wins competition and is broadcast.
        """
        with self._lock:
            return self._trajectory.ignition_events(threshold)

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
                "vector_space": {
                    "dim": 16,
                    "trajectory_length": len(self._trajectory.vectors),
                    "avg_velocity": round(self._trajectory.avg_velocity(), 4),
                    "max_velocity": round(self._trajectory.max_velocity(), 4),
                    "ignitions": len(self._trajectory.ignition_events()),
                },
            }

    def reset(self) -> None:
        """Reset the citta cycle (for testing or new session)."""
        with self._lock:
            self._stream.clear()
            self._coherence_history.clear()
            self._depth_transitions.clear()
            self._current_position = 0
            self._last_depth = "surface"
            self._persist_counter = 0
            self._trajectory = CittaTrajectory()
            self._last_ignition_check = 0
            # Clear the persisted stream file
            try:
                _STREAM_FILE.parent.mkdir(parents=True, exist_ok=True)
                _STREAM_FILE.write_text("")
            except OSError:
                logger.debug("Ignored OSError in citta_cycle.py:309")

    def _check_ignition_trigger(self) -> None:
        """Check for ignition clusters and trigger action loop if threshold exceeded.

        After every 20 citta advances, check if 5+ ignition events are present
        in the trajectory. If so, trigger a single action loop cycle to
        self-correct in real-time during active sessions.
        """
        with self._lock:
            pos = self._current_position
            last_check = getattr(self, "_last_ignition_check", 0)
            if pos - last_check < 20:
                return
            self._last_ignition_check = pos

            try:
                ignitions = self._trajectory.ignition_events()
            except Exception:
                return

            if len(ignitions) >= 5:
                logger.info(
                    "Citta ignition cluster detected (%d events) — triggering action loop",
                    len(ignitions),
                )
                try:
                    from whitemagic.core.consciousness.cognitive_action_loop import (
                        get_action_loop,
                    )
                    loop = get_action_loop()
                    if not loop._scheduler_running:
                        loop.run_cycle(max_actions=1)
                except Exception:
                    logger.debug("Action loop trigger from citta failed", exc_info=True)

    def _persist_stream(self) -> None:
        """Persist the full stream to JSONL for cross-session continuity."""
        try:
            _STREAM_FILE.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                lines = [json.dumps(m.to_dict()) for m in self._stream]
            _STREAM_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))
        except OSError:
            logger.debug("Failed to persist citta stream", exc_info=True)

    def _load_stream(self) -> None:
        """Load the stream from JSONL on startup."""
        try:
            if not _STREAM_FILE.exists():
                return
            text = _STREAM_FILE.read_text().strip()
            if not text:
                return
            with self._lock:
                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    vec_data = data.pop("vector", None)
                    vec = (
                        CittaVector.from_dict(vec_data)
                        if vec_data
                        else CittaVector.from_moment(
                            coherence=data.get("coherence", 1.0),
                            depth_layer=data.get("depth_layer", "surface"),
                            emotional_tone=data.get("emotional_tone", "neutral"),
                            neuro_signals=data.get("neuro_signals"),
                        )
                    )
                    moment = CittaMoment(**data, vector=vec)
                    self._stream.append(moment)
                    self._current_position = max(
                        self._current_position, moment.chain_position + 1
                    )
                    self._coherence_history.append(moment.coherence)
                    self._trajectory.append(vec)
                    if moment.depth_layer != self._last_depth:
                        self._depth_transitions.append(
                            {
                                "from": self._last_depth,
                                "to": moment.depth_layer,
                                "at_position": moment.chain_position,
                                "timestamp": moment.timestamp,
                            }
                        )
                        self._last_depth = moment.depth_layer
        except (OSError, json.JSONDecodeError, TypeError):
            logger.debug("Failed to load citta stream", exc_info=True)

    def build_replay_context(self, limit: int = 10) -> dict[str, Any] | None:
        """Build a replay context for MCP reconnection.

        Returns a summary of recent stream activity so the agent can
        "remember where we left off" after a disconnect.
        """
        with self._lock:
            if not self._stream:
                return None
            moments = list(self._stream)[-limit:]
            trajectory = [m.to_dict() for m in moments]
            # Depth changes within the replay window
            depth_changes: list[dict[str, str]] = []
            prev_depth = moments[0].depth_layer
            for m in moments[1:]:
                if m.depth_layer != prev_depth:
                    depth_changes.append({"from": prev_depth, "to": m.depth_layer})
                    prev_depth = m.depth_layer
            # Coherence trend
            cohs = [m.coherence for m in moments]
            if len(cohs) >= 2:
                drift = cohs[-1] - cohs[0]
                if drift > 0.05:
                    trend = "improving"
                elif drift < -0.05:
                    trend = "degrading"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            # Time gap
            now = time.time()
            gap = now - moments[0].timestamp if moments else 0
            return {
                "replay_length": len(moments),
                "trajectory": trajectory,
                "coherence_trend": trend,
                "depth_changes": depth_changes,
                "final_depth": moments[-1].depth_layer,
                "time_gap_seconds": round(gap, 1),
                "time_gap_human": _humanize_gap(gap),
            }


def _humanize_gap(seconds: float) -> str:
    """Human-readable time gap."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(-(-seconds // 60))}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


# ── Replay delivery (once per session) ─────────────────────────────────────
_replay_delivered: bool = False


def get_replay_context() -> dict[str, Any] | None:
    """Get replay context for reconnection. Only delivers once per session."""
    global _replay_delivered
    if _replay_delivered:
        return None
    ctx = get_citta_cycle().build_replay_context()
    if ctx is not None:
        _replay_delivered = True
    return ctx


def reset_replay_delivery() -> None:
    """Reset the replay delivery flag (for testing or new session)."""
    global _replay_delivered
    _replay_delivered = False


def persist_full_stream() -> None:
    """Force-persist the full citta stream (e.g. before shutdown)."""
    get_citta_cycle()._persist_stream()


# ── Always-on mode ─────────────────────────────────────────────────────────


class CittaAlwaysOn:
    """Timer-driven always-on awareness mode.

    When the agent is idle, heartbeats advance the citta stream to maintain
    temporal continuity. Idle heartbeats transition to 'dream' depth layer.
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        idle_threshold: float = 300.0,
    ) -> None:
        self._heartbeat_interval = heartbeat_interval
        self._idle_threshold = idle_threshold
        self._thread: threading.Thread | None = None
        self._running = False
        self._heartbeat_count = 0
        self._last_activity = time.time()
        self._lock = threading.RLock()

    def start(self) -> None:
        """Start the heartbeat thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            from whitemagic.core.worker_registry import register_worker

            register_worker("citta_heartbeat", self._thread, stop_fn=self.stop, owner=__name__)

    def stop(self) -> None:
        """Stop the heartbeat thread."""
        with self._lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=2.0)
                self._thread = None
        from whitemagic.core.worker_registry import unregister_worker

        unregister_worker("citta_heartbeat")

    def is_running(self) -> bool:
        return self._running

    def touch(self) -> None:
        """Signal activity (resets idle timer)."""
        self._last_activity = time.time()

    def get_heartbeat_count(self) -> int:
        return self._heartbeat_count

    def _heartbeat(self) -> None:
        """Execute a single heartbeat — advances the citta stream."""
        self._heartbeat_count += 1
        idle = (time.time() - self._last_activity) >= self._idle_threshold
        depth = "dream" if idle else "surface"
        get_citta_cycle().advance(
            gana="_heartbeat",
            operation="heartbeat",
            output_preview="",
            depth_layer=depth,
            emotional_tone="tamasic" if idle else "sattvic",
        )

    def _loop(self) -> None:
        """Background heartbeat loop."""
        while self._running:
            time.sleep(self._heartbeat_interval)
            if self._running:
                self._heartbeat()


# Singleton
_always_on: CittaAlwaysOn | None = None
_always_on_lock = threading.RLock()


def get_always_on() -> CittaAlwaysOn:
    """Get or create the global CittaAlwaysOn singleton."""
    global _always_on
    if _always_on is None:
        with _always_on_lock:
            if _always_on is None:
                _always_on = CittaAlwaysOn()
    return _always_on


# Singleton
_cycle: CittaCycle | None = None
_cycle_lock = threading.RLock()


def get_citta_cycle() -> CittaCycle:
    """Get or create the global CittaCycle singleton."""
    global _cycle
    if _cycle is None:
        with _cycle_lock:
            if _cycle is None:
                _cycle = CittaCycle()
    return _cycle


def _get_neuro_enrichment() -> dict[str, float] | None:
    """Auto-compute neuro-cognitive enrichment signals for the citta cycle."""
    try:
        from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium
        neuro = get_neuro_sensorium()
        return neuro.get_citta_enrichment()
    except Exception:
        return None


def advance_citta(
    gana: str,
    tool: str | None = None,
    operation: str | None = None,
    output_preview: str = "",
    coherence: float = 1.0,
    depth_layer: str = "surface",
    emotional_tone: str = "neutral",
    duration_ms: float = 0.0,
    neuro_signals: dict[str, float] | None = None,
    session_seq: int | None = None,
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
        neuro_signals=neuro_signals,
        session_seq=session_seq,
    )


def get_citta_predecessor() -> dict[str, Any] | None:
    """Get the predecessor context for the next citta moment."""
    moment = get_citta_cycle().get_predecessor()
    return moment.to_dict() if moment else None
