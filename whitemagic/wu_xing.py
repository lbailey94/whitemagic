from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Phase(Enum):
    WOOD = "wood"  # Planning/Research
    FIRE = "fire"  # Execution/Creation
    EARTH = "earth"  # Consolidation (tests/docs)
    METAL = "metal"  # Refinement/Debugging
    WATER = "water"  # Reflection/Review


@dataclass
class Activity:
    timestamp: datetime
    action: str  # e.g., "read", "search", "edit", "write", "test", "doc", "memory"
    reads: int = 0
    writes: int = 0
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    tests_run: int = 0
    docs_changed: bool = False
    memory_ops: int = 0  # e.g., create/update/consolidate memories


class WuXingDetector:

    def __init__(self, window_minutes: int = 90):
        self.window = timedelta(minutes=window_minutes)

    def _windowed(
        self, activity_log: List[Activity], now: Optional[datetime] = None
    ) -> List[Activity]:
        if not now:
            now = datetime.now()
        cutoff = now - self.window
        return [a for a in activity_log if a.timestamp >= cutoff]

    def detect_phase(
        self, activity_log: List[Activity], now: Optional[datetime] = None
    ) -> Tuple[Phase, float, Dict[str, Any]]:
        recent = self._windowed(activity_log, now)
        if not recent:
            # Default to Water (reflection) when idle
            return Phase.WATER, 0.4, {"reason": "no_recent_activity"}

        reads = sum(a.reads for a in recent)
        writes = sum(a.writes for a in recent)
        files = sum(a.files_changed for a in recent)
        added = sum(a.lines_added for a in recent)
        deleted = sum(a.lines_deleted for a in recent)
        tests = sum(a.tests_run for a in recent)
        docs = sum(1 for a in recent if a.docs_changed)
        mems = sum(a.memory_ops for a in recent)

        edits = writes + files
        churn = added + deleted
        total = max(reads + writes + tests + docs + mems, 1)

        scores: Dict[Phase, float] = {
            Phase.WOOD: 0.0,
            Phase.FIRE: 0.0,
            Phase.EARTH: 0.0,
            Phase.METAL: 0.0,
            Phase.WATER: 0.0,
        }

        scores[Phase.WOOD] += (reads / total) * 0.7
        scores[Phase.WOOD] += (1.0 if edits == 0 and reads > 0 else 0.0) * 0.3

        scores[Phase.FIRE] += (edits / total) * 0.4
        scores[Phase.FIRE] += (min(churn / 500.0, 1.0)) * 0.4
        scores[Phase.FIRE] += (1.0 if files >= 5 else 0.0) * 0.2

        scores[Phase.EARTH] += (min(tests / 20.0, 1.0)) * 0.6
        scores[Phase.EARTH] += (docs / max(len(recent), 1)) * 0.4

        small_edits = edits >= 5 and churn <= 150
        scores[Phase.METAL] += (1.0 if small_edits else 0.0) * 0.6
        scores[Phase.METAL] += (edits / max(len(recent), 1)) * 0.2
        scores[Phase.METAL] += (1.0 if tests > 0 and small_edits else 0.0) * 0.2

        scores[Phase.WATER] += (mems / max(len(recent), 1)) * 0.6
        scores[Phase.WATER] += 0.3 if total <= 3 else 0.0
        scores[Phase.WATER] += (docs / max(len(recent), 1)) * 0.1

        best_phase = max(scores.items(), key=lambda kv: kv[1])[0]
        confidence = round(min(max(scores[best_phase], 0.0), 1.0), 2)

        diagnostics = {
            "metrics": {
                "reads": reads,
                "writes": writes,
                "files": files,
                "churn": churn,
                "tests": tests,
                "docs": docs,
                "memory_ops": mems,
                "events": len(recent),
            },
            "scores": {k.value: round(v, 3) for k, v in scores.items()},
            "window_minutes": int(self.window.total_seconds() // 60),
        }

        return best_phase, confidence, diagnostics


def simple_detect(activity_log: List[Activity]) -> str:
    phase, _, _ = WuXingDetector().detect_phase(activity_log)
    return phase.value
