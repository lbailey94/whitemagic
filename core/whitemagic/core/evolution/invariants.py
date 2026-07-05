"""Observer Effect & Self-Reference Invariants (Objective W).

Identifies metrics that are preserved under self-improvement and defines
the self-improvement uncertainty principle.

The core insight: the system improving itself changes the system being
improved. Metrics that were meaningful before may not be meaningful after.
This module distinguishes:

- **Invariant metrics**: preserved under self-improvement (total information
  content, Kolmogorov complexity proxies, test count). Use these for
  long-term tracking.
- **Non-invariant metrics**: change when the system improves itself (memory
  quality scores, kaizen proposal count, Brier score). Use these for
  short-term feedback only.

The self-improvement uncertainty principle:
    Δmeasurement · Δsystem_state ≥ ħ_self

You cannot simultaneously know the system's state and measure its improvement
with arbitrary precision. The act of improving changes the state being measured.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from whitemagic.core.memory.db_manager import safe_connect
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class InvariantSnapshot:
    """A snapshot of invariant metrics at a point in time."""

    timestamp: str
    total_memories: int
    total_tags: int
    unique_tags: int
    shannon_entropy: float
    test_count: int | None = None
    codebase_line_count: int | None = None
    kolmogorov_proxy: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def delta_from(self, other: InvariantSnapshot) -> dict[str, float]:
        """Compute delta between two snapshots."""
        return {
            "total_memories_delta": float(self.total_memories - other.total_memories),
            "total_tags_delta": float(self.total_tags - other.total_tags),
            "unique_tags_delta": float(self.unique_tags - other.unique_tags),
            "shannon_entropy_delta": round(
                self.shannon_entropy - other.shannon_entropy, 6
            ),
            "test_count_delta": float((self.test_count or 0) - (other.test_count or 0)),
        }


NON_INVARIANT_METRICS = [
    "memory_quality_score",
    "kaizen_proposal_count",
    "brier_score",
    "prediction_confidence",
    "novelty_score",
    "improvement_rate",
]

# Gödel-undecidable statements (cannot be answered from within the system)
GODEL_UNDECIDABLE = [
    "is_my_improvement_strategy_optimal",
    "is_my_self_model_accurate",
    "am_i_measuring_the_right_things",
]


class InvariantTracker:
    """Tracks invariant metrics across improvement cycles.

    Provides:
    - snapshot(): capture current invariant state
    - check_invariants(): verify that invariants hold after an improvement
    - uncertainty_principle(): compute the measurement-system tradeoff
    - is_godel_undecidable(): check if a question is undecidable from within
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import DB_PATH

            self._db_path = str(DB_PATH)
        else:
            self._db_path = db_path
        self._snapshots: list[InvariantSnapshot] = []
        self._h_self = 0.1  # Self-improvement uncertainty constant

    def snapshot(self, test_count: int | None = None) -> InvariantSnapshot:
        """Capture current invariant metrics.

        Args:
            test_count: External test count (the key invariant — tests define
                correct behavior and don't change when the system improves itself).

        Returns:
            InvariantSnapshot with current state.
        """
        from datetime import datetime

        total_memories = 0
        total_tags = 0
        unique_tags = 0
        shannon_entropy = 0.0

        try:
            conn = safe_connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM memories")
            total_memories = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM tags")
            total_tags = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT tag) FROM tags")
            unique_tags = cur.fetchone()[0]

            # Shannon entropy of tag distribution
            cur.execute("""
                SELECT tag, COUNT(*) as cnt FROM tags
                GROUP BY tag ORDER BY cnt DESC
            """)
            tag_counts = [r[1] for r in cur.fetchall()]
            if tag_counts and total_tags > 0:
                probs = [c / total_tags for c in tag_counts]
                shannon_entropy = -sum(p * math.log2(p) for p in probs if p > 0)

            conn.close()
        except Exception as e:
            logger.debug("Invariant snapshot failed: %s", e)

        snap = InvariantSnapshot(
            timestamp=datetime.now().isoformat(),
            total_memories=total_memories,
            total_tags=total_tags,
            unique_tags=unique_tags,
            shannon_entropy=round(shannon_entropy, 6),
            test_count=test_count,
        )
        self._snapshots.append(snap)
        return snap

    def check_invariants(
        self,
        before: InvariantSnapshot,
        after: InvariantSnapshot,
    ) -> dict[str, Any]:
        """Verify that invariant metrics are preserved after an improvement.

        Invariant metrics should not decrease (information is not destroyed).
        Shannon entropy may redistribute but total information content should
        be conserved or grow.

        Args:
            before: Snapshot before the improvement.
            after: Snapshot after the improvement.

        Returns:
            Dict with invariant check results.
        """
        deltas = after.delta_from(before)

        results: dict[str, Any] = {
            "invariants_held": True,
            "violations": [],
            "deltas": deltas,
        }

        # Total memories should not decrease (improvements add, don't remove)
        if deltas["total_memories_delta"] < 0:
            results["violations"].append(
                f"total_memories decreased by {abs(deltas['total_memories_delta'])}"
            )

        # Shannon entropy should not decrease significantly
        # (redistribution is fine, but information loss is not)
        if deltas["shannon_entropy_delta"] < -0.5:
            results["violations"].append(
                f"shannon_entropy decreased by {abs(deltas['shannon_entropy_delta'])}"
            )

        if deltas["test_count_delta"] < 0:
            results["violations"].append(
                f"test_count decreased by {abs(deltas['test_count_delta'])}"
            )

        if results["violations"]:
            results["invariants_held"] = False

        return results

    def uncertainty_principle(
        self,
        delta_measurement: float,
        delta_system_state: float,
    ) -> dict[str, Any]:
        """Compute the self-improvement uncertainty principle.

        Δmeasurement · Δsystem_state ≥ ħ_self

        You cannot simultaneously know the system's state and measure its
        improvement with arbitrary precision. The act of improving changes
        the state being measured.

        Args:
            delta_measurement: Uncertainty in the measurement (e.g., Brier score variance).
            delta_system_state: How much the system changed (e.g., code lines modified).

        Returns:
            Dict with uncertainty analysis.
        """
        product = delta_measurement * delta_system_state
        satisfied = product >= self._h_self

        return {
            "delta_measurement": delta_measurement,
            "delta_system_state": delta_system_state,
            "product": round(product, 6),
            "h_self": self._h_self,
            "principle_satisfied": satisfied,
            "interpretation": (
                "Measurement is reliable — system changed little"
                if delta_system_state < 0.01
                else "Measurement may be unreliable — system changed significantly"
                if delta_system_state > 0.1
                else "Measurement is moderately reliable"
            ),
        }

    @staticmethod
    def is_godel_undecidable(question: str) -> bool:
        """Check if a question is undecidable from within the system.

        These are statements that cannot be answered by the system about itself.
        They require external evaluation (see Objective X).

        Args:
            question: The question to check (snake_case identifier).

        Returns:
            True if the question is Gödel-undecidable from within.
        """
        return question in GODEL_UNDECIDABLE

    @staticmethod
    def classify_metric(metric_name: str) -> str:
        """Classify a metric as invariant or non-invariant.

        Args:
            metric_name: The metric identifier.

        Returns:
            "invariant" or "non_invariant".
        """
        if metric_name in NON_INVARIANT_METRICS:
            return "non_invariant"
        return "invariant"

    def get_history(self) -> list[InvariantSnapshot]:
        """Get all recorded snapshots."""
        return list(self._snapshots)

    def get_tracking_guidance(self, metric_name: str) -> dict[str, str]:
        """Get guidance on how to track a metric.

        Args:
            metric_name: The metric to get guidance for.

        Returns:
            Dict with tracking guidance.
        """
        classification = self.classify_metric(metric_name)
        if classification == "invariant":
            return {
                "classification": "invariant",
                "guidance": "Use for long-term tracking. This metric is preserved "
                "under self-improvement and provides reliable signal.",
            }
        return {
            "classification": "non_invariant",
            "guidance": "Use for short-term feedback only. This metric changes "
            "when the system improves itself — do not use for "
            "long-term trend analysis.",
        }
