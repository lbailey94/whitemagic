"""Autodidactic Feedback Loop - Recursive Self-Improvement

The system learns which patterns actually work by:
1. Tracking pattern applications
2. Measuring outcomes
3. Updating confidence scores
4. Feeding results back into pattern discovery

This creates true recursive evolution.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from whitemagic.config.paths import AUTODIDACTIC_DIR


@dataclass
class PatternApplication:
    """Record of a pattern being applied"""

    application_id: str
    pattern_id: str
    pattern_type: str
    timestamp: float
    initial_confidence: float
    context: dict[str, Any]


@dataclass
class PatternOutcome:
    """Measured outcome of a pattern application"""

    application_id: str
    pattern_id: str
    success: bool
    performance_gain: float | None  # e.g., 3.28x speedup
    quality_score: float | None  # 0-1 scale
    user_feedback: str | None
    measured_at: float
    metrics: dict[str, Any]


@dataclass
class UpdatedPattern:
    """Pattern with updated confidence based on outcomes"""

    pattern_id: str
    original_confidence: float
    updated_confidence: float
    application_count: int
    success_rate: float
    avg_performance_gain: float
    last_updated: float


class AutodidacticLoop:
    """Manages the recursive self-improvement feedback loop"""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = AUTODIDACTIC_DIR / "feedback.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Pattern applications
        c.execute("""
            CREATE TABLE IF NOT EXISTS pattern_applications (
                application_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                initial_confidence REAL NOT NULL,
                context TEXT NOT NULL
            )
        """)

        # Pattern outcomes
        c.execute("""
            CREATE TABLE IF NOT EXISTS pattern_outcomes (
                outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                performance_gain REAL,
                quality_score REAL,
                user_feedback TEXT,
                measured_at REAL NOT NULL,
                metrics TEXT NOT NULL,
                FOREIGN KEY (application_id) REFERENCES pattern_applications(application_id)
            )
        """)

        # Pattern confidence updates
        c.execute("""
            CREATE TABLE IF NOT EXISTS pattern_updates (
                update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                original_confidence REAL NOT NULL,
                updated_confidence REAL NOT NULL,
                application_count INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                avg_performance_gain REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Objective B: Pattern correlations for interaction-aware MC
        c.execute("""
            CREATE TABLE IF NOT EXISTS pattern_correlations (
                correlation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_a TEXT NOT NULL,
                pattern_b TEXT NOT NULL,
                correlation REAL NOT NULL,
                co_occurrences INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE(pattern_a, pattern_b)
            )
        """)

        # Indexes
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pattern_id ON pattern_applications(pattern_id)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_outcome_pattern ON pattern_outcomes(pattern_id)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_update_pattern ON pattern_updates(pattern_id)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_corr_a ON pattern_correlations(pattern_a)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_corr_b ON pattern_correlations(pattern_b)"
        )

        conn.commit()
        conn.close()

    def record_application(self, application: PatternApplication) -> None:
        """Record that a pattern was applied"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO pattern_applications
            (application_id, pattern_id, pattern_type, timestamp, initial_confidence, context)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                application.application_id,
                application.pattern_id,
                application.pattern_type,
                application.timestamp,
                application.initial_confidence,
                json.dumps(application.context),
            ),
        )

        conn.commit()
        conn.close()

    def record_outcome(self, outcome: PatternOutcome) -> None:
        """Record the measured outcome of a pattern application"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO pattern_outcomes
            (application_id, pattern_id, success, performance_gain, quality_score,
             user_feedback, measured_at, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                outcome.application_id,
                outcome.pattern_id,
                1 if outcome.success else 0,
                outcome.performance_gain,
                outcome.quality_score,
                outcome.user_feedback,
                outcome.measured_at,
                json.dumps(outcome.metrics),
            ),
        )

        conn.commit()
        conn.close()

        # Trigger confidence update
        self._update_pattern_confidence(outcome.pattern_id)

        # Objective B: Update pairwise correlations
        self.update_correlations(outcome.pattern_id, outcome.success)

    def _update_pattern_confidence(self, pattern_id: str) -> None:
        """Update pattern confidence based on accumulated outcomes"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Get all outcomes for this pattern
        c.execute(
            """
            SELECT success, performance_gain, quality_score
            FROM pattern_outcomes
            WHERE pattern_id = ?
        """,
            (pattern_id,),
        )

        outcomes = c.fetchall()
        if not outcomes:
            conn.close()
            return

        # Calculate statistics
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o[0])
        success_rate = successes / total

        # Average performance gain (only from successful applications)
        gains = [o[1] for o in outcomes if o[0] and o[1] is not None]
        avg_gain = sum(gains) / len(gains) if gains else 0.0

        # Get original confidence
        c.execute(
            """
            SELECT initial_confidence
            FROM pattern_applications
            WHERE pattern_id = ?
            LIMIT 1
        """,
            (pattern_id,),
        )

        result = c.fetchone()
        original_confidence = result[0] if result else 0.5

        # Calculate updated confidence
        # Formula: original * (0.7) + success_rate * (0.2) + normalized_gain * (0.1)
        normalized_gain = min(avg_gain / 10.0, 1.0) if avg_gain > 0 else 0.0
        updated_confidence = min(
            original_confidence * 0.7 + success_rate * 0.2 + normalized_gain * 0.1, 1.0
        )

        # Record update
        c.execute(
            """
            INSERT INTO pattern_updates
            (pattern_id, original_confidence, updated_confidence, application_count,
             success_rate, avg_performance_gain, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                pattern_id,
                original_confidence,
                updated_confidence,
                total,
                success_rate,
                avg_gain,
                time.time(),
            ),
        )

        conn.commit()
        conn.close()

    def get_pattern_confidence(self, pattern_id: str) -> float | None:
        """Get the latest confidence score for a pattern"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute(
            """
            SELECT updated_confidence
            FROM pattern_updates
            WHERE pattern_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """,
            (pattern_id,),
        )

        result = c.fetchone()
        conn.close()

        return result[0] if result else None

    def get_pattern_stats(self, pattern_id: str) -> dict[str, Any] | None:
        """Get comprehensive statistics for a pattern"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Get latest update
        c.execute(
            """
            SELECT original_confidence, updated_confidence, application_count,
                   success_rate, avg_performance_gain, updated_at
            FROM pattern_updates
            WHERE pattern_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """,
            (pattern_id,),
        )

        result = c.fetchone()
        if not result:
            conn.close()
            return None

        # Get recent outcomes
        c.execute(
            """
            SELECT success, performance_gain, quality_score, measured_at
            FROM pattern_outcomes
            WHERE pattern_id = ?
            ORDER BY measured_at DESC
            LIMIT 10
        """,
            (pattern_id,),
        )

        recent_outcomes = c.fetchall()
        conn.close()

        return {
            "pattern_id": pattern_id,
            "original_confidence": result[0],
            "current_confidence": result[1],
            "confidence_change": result[1] - result[0],
            "application_count": result[2],
            "success_rate": result[3],
            "avg_performance_gain": result[4],
            "last_updated": result[5],
            "recent_outcomes": [
                {
                    "success": bool(o[0]),
                    "performance_gain": o[1],
                    "quality_score": o[2],
                    "measured_at": o[3],
                }
                for o in recent_outcomes
            ],
        }

    def get_top_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top patterns by updated confidence"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute("""
            SELECT DISTINCT pattern_id
            FROM pattern_updates
        """)

        pattern_ids = [row[0] for row in c.fetchall()]
        conn.close()

        # Get stats for each
        stats = []
        for pid in pattern_ids:
            s = self.get_pattern_stats(pid)
            if s:
                stats.append(s)

        # Sort by current confidence
        stats.sort(key=lambda x: x["current_confidence"], reverse=True)
        return stats[:limit]

    def get_learning_summary(self) -> dict[str, Any]:
        """Get overall learning statistics"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Total applications
        c.execute("SELECT COUNT(*) FROM pattern_applications")
        total_applications = c.fetchone()[0]

        # Total outcomes
        c.execute("SELECT COUNT(*) FROM pattern_outcomes")
        total_outcomes = c.fetchone()[0]

        # Overall success rate
        c.execute("SELECT AVG(success) FROM pattern_outcomes")
        overall_success_rate = c.fetchone()[0] or 0.0

        # Average performance gain
        c.execute(
            "SELECT AVG(performance_gain) FROM pattern_outcomes WHERE performance_gain IS NOT NULL"
        )
        avg_performance_gain = c.fetchone()[0] or 0.0

        # Patterns with improved confidence
        c.execute("""
            SELECT COUNT(DISTINCT pattern_id)
            FROM pattern_updates
            WHERE updated_confidence > original_confidence
        """)
        improved_patterns = c.fetchone()[0]

        # Patterns with decreased confidence
        c.execute("""
            SELECT COUNT(DISTINCT pattern_id)
            FROM pattern_updates
            WHERE updated_confidence < original_confidence
        """)
        decreased_patterns = c.fetchone()[0]

        conn.close()

        return {
            "total_applications": total_applications,
            "total_outcomes": total_outcomes,
            "overall_success_rate": overall_success_rate,
            "avg_performance_gain": avg_performance_gain,
            "improved_patterns": improved_patterns,
            "decreased_patterns": decreased_patterns,
            "learning_active": total_outcomes > 0,
        }

    def update_correlations(self, pattern_id: str, success: bool) -> None:
        """Update pairwise correlations after a pattern outcome is recorded.

        Finds all other patterns that have outcomes recorded and updates the
        correlation between this pattern and each of them by pairing outcomes
        sorted by time.

        Args:
            pattern_id: The pattern that just had an outcome recorded.
            success: Whether the outcome was successful.
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Get this pattern's outcomes sorted by time
        c.execute(
            """
            SELECT success, measured_at FROM pattern_outcomes
            WHERE pattern_id = ? ORDER BY measured_at
        """,
            (pattern_id,),
        )
        own_outcomes = [(r[0], r[1]) for r in c.fetchall()]

        if len(own_outcomes) < 2:
            conn.close()
            return

        # Find all other patterns that have outcomes
        c.execute(
            """
            SELECT DISTINCT pattern_id FROM pattern_outcomes
            WHERE pattern_id != ?
        """,
            (pattern_id,),
        )
        other_patterns = [r[0] for r in c.fetchall()]

        for other_id in other_patterns:
            c.execute(
                """
                SELECT success, measured_at FROM pattern_outcomes
                WHERE pattern_id = ? ORDER BY measured_at
            """,
                (other_id,),
            )
            other_outcomes = [(r[0], r[1]) for r in c.fetchall()]

            if len(other_outcomes) < 2:
                continue

            # Pair by index (both sorted by time)
            n = min(len(own_outcomes), len(other_outcomes))
            a_vals = [float(own_outcomes[i][0]) for i in range(n)]
            b_vals = [float(other_outcomes[i][0]) for i in range(n)]

            a_mean = sum(a_vals) / n
            b_mean = sum(b_vals) / n

            cov = sum((a - a_mean) * (b - b_mean) for a, b in zip(a_vals, b_vals)) / n
            a_std = (sum((a - a_mean) ** 2 for a in a_vals) / n) ** 0.5
            b_std = (sum((b - b_mean) ** 2 for b in b_vals) / n) ** 0.5

            if a_std > 0 and b_std > 0:
                correlation = cov / (a_std * b_std)
            else:
                correlation = 0.0

            correlation = max(-1.0, min(1.0, correlation))

            c.execute(
                """
                INSERT INTO pattern_correlations (pattern_a, pattern_b, correlation, co_occurrences, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(pattern_a, pattern_b)
                DO UPDATE SET correlation = ?, co_occurrences = ?, updated_at = ?
            """,
                (
                    pattern_id,
                    other_id,
                    correlation,
                    n,
                    time.time(),
                    correlation,
                    n,
                    time.time(),
                ),
            )

        conn.commit()
        conn.close()

    def get_correlation(self, pattern_a: str, pattern_b: str) -> float:
        """Get the correlation between two patterns.

        Returns:
            Correlation in [-1, 1], or 0.0 if no correlation data exists.
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        # Try both orderings
        c.execute(
            """
            SELECT correlation FROM pattern_correlations
            WHERE (pattern_a = ? AND pattern_b = ?)
               OR (pattern_a = ? AND pattern_b = ?)
        """,
            (pattern_a, pattern_b, pattern_b, pattern_a),
        )

        result = c.fetchone()
        conn.close()

        return result[0] if result else 0.0

    def get_correlation_matrix(
        self, pattern_ids: list[str]
    ) -> dict[str, dict[str, float]]:
        """Get the correlation matrix for a set of patterns.

        Args:
            pattern_ids: List of pattern IDs to include.

        Returns:
            Nested dict: matrix[a][b] = correlation.
        """
        matrix: dict[str, dict[str, float]] = {}
        for a in pattern_ids:
            matrix[a] = {}
            for b in pattern_ids:
                if a == b:
                    matrix[a][b] = 1.0
                else:
                    matrix[a][b] = self.get_correlation(a, b)
        return matrix

    def get_all_correlations(self) -> list[dict[str, Any]]:
        """Get all recorded correlations.

        Returns:
            List of dicts with pattern_a, pattern_b, correlation, co_occurrences.
        """
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()

        c.execute("""
            SELECT pattern_a, pattern_b, correlation, co_occurrences
            FROM pattern_correlations
            ORDER BY ABS(correlation) DESC
        """)

        rows = c.fetchall()
        conn.close()

        return [
            {
                "pattern_a": r[0],
                "pattern_b": r[1],
                "correlation": r[2],
                "co_occurrences": r[3],
            }
            for r in rows
        ]
