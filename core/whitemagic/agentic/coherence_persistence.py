# ruff: noqa: BLE001
"""
Coherence Persistence — Remember coherence across sessions.

Tracks coherence scores over time, enabling drift detection and
continuity of consciousness state across MCP disconnects.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class CoherenceSnapshot:
    """A point-in-time coherence measurement."""

    timestamp: float = field(default_factory=time.time)
    composite: float = 0.0
    dimensions: dict[str, float] = field(default_factory=dict)
    session_id: str = ""
    context: str = ""


class CoherencePersistence:
    """Persists coherence measurements across sessions."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "agentic"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "coherence_history.jsonl"
        self.snapshots: list[CoherenceSnapshot] = []
        self._load()

    def _load(self) -> None:
        if self.history_file.exists():
            for line in self.history_file.read_text().splitlines():
                if line.strip():
                    try:
                        d = json.loads(line)
                        self.snapshots.append(CoherenceSnapshot(**d))
                    except Exception:
                        logger.debug("Skipping malformed coherence snapshot")

    def record(
        self,
        composite: float,
        dimensions: dict[str, float] | None = None,
        session_id: str = "",
        context: str = "",
    ) -> CoherenceSnapshot:
        snap = CoherenceSnapshot(
            composite=composite,
            dimensions=dimensions or {},
            session_id=session_id,
            context=context,
        )
        self.snapshots.append(snap)
        with open(self.history_file, "a") as f:
            f.write(json.dumps(asdict(snap)) + "\n")
        return snap

    def latest(self) -> CoherenceSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    def drift(self, window: int = 10) -> float:
        """Calculate coherence drift over last N snapshots."""
        if len(self.snapshots) < 2:
            return 0.0
        recent = self.snapshots[-window:]
        if len(recent) < 2:
            return 0.0
        return recent[-1].composite - recent[0].composite

    def trend(self, window: int = 20) -> str:
        """Describe coherence trend."""
        d = self.drift(window)
        if d > 0.05:
            return "improving"
        if d < -0.05:
            return "declining"
        return "stable"

    def summary(self) -> dict[str, Any]:
        latest_snap = self.latest()
        return {
            "total_snapshots": len(self.snapshots),
            "latest_composite": latest_snap.composite if latest_snap else 0.0,
            "drift": self.drift(),
            "trend": self.trend(),
        }


_persistence: CoherencePersistence | None = None


def get_coherence_persistence() -> CoherencePersistence:
    global _persistence
    if _persistence is None:
        _persistence = CoherencePersistence()
    return _persistence
