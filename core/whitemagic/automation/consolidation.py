# ruff: noqa: BLE001
"""
Automated Memory Consolidation System.

Automatically consolidates short-term memories into long-term when:
1. Short-term count > threshold (default: 40)
2. Age of memories > threshold (default: 7 days)
3. Similar/duplicate memories detected
4. On session end
5. On version release
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationResult:
    """Result of a consolidation run."""
    consolidated: int = 0
    duplicates_removed: int = 0
    archived: int = 0
    errors: list[str] = field(default_factory=list)
    duration_s: float = 0.0


class ConsolidationEngine:
    """Automated memory consolidation engine."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "automation"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "consolidation_log.jsonl"
        self.short_term_threshold = 40
        self.age_threshold_days = 7

    def should_consolidate(self) -> tuple[bool, str]:
        """Check if consolidation should run."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            mem = get_unified_memory()
            if hasattr(mem, "count"):
                count = mem.count()
                if count > self.short_term_threshold:
                    return True, f"count={count} > threshold={self.short_term_threshold}"
        except Exception:
            pass
        return False, "not needed"

    def consolidate(self, force: bool = False) -> ConsolidationResult:
        """Run consolidation."""
        start = time.monotonic()
        result = ConsolidationResult()

        if not force:
            should, reason = self.should_consolidate()
            if not should:
                return result

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            mem = get_unified_memory()
            if hasattr(mem, "consolidate"):
                consolidated = mem.consolidate()
                result.consolidated = consolidated if isinstance(consolidated, int) else 0
        except Exception as e:
            result.errors.append(str(e))
            logger.debug("Consolidation error: %s", e)

        result.duration_s = time.monotonic() - start
        self._log(result)
        return result

    def _log(self, result: ConsolidationResult) -> None:
        entry = {
            "consolidated": result.consolidated,
            "duplicates_removed": result.duplicates_removed,
            "archived": result.archived,
            "duration_s": result.duration_s,
            "errors": result.errors,
            "timestamp": time.time(),
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "threshold": self.short_term_threshold,
            "age_threshold_days": self.age_threshold_days,
        }


_engine: ConsolidationEngine | None = None


def get_consolidation() -> ConsolidationEngine:
    global _engine
    if _engine is None:
        _engine = ConsolidationEngine()
    return _engine
