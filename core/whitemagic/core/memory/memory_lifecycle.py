# ruff: noqa: BLE001
"""Memory Lifecycle Manager — Consolidation, decay, and maintenance operations.

Handles memory consolidation, association decay, pruning, and other maintenance
operations for the SQLite backend. Extracted from sqlite_backend.py for better
separation of concerns.
"""

import logging
import math
import sqlite3
from datetime import datetime
from typing import Any, cast

logger = logging.getLogger(__name__)


class MemoryLifecycleManager:
    """Manages memory lifecycle operations for SQLite backend."""

    def __init__(self, pool):
        self.pool = pool

    def consolidate(self) -> int:
        """Consolidate memories efficiently using SQL and Neural/Hebbian logic.
        - Strengthen frequently accessed (>5)
        - Decay rarely accessed short-term (<2) based on half-life
        - Promote important short-term to long-term (>0.8).
        """
        consolidated_count = 0
        with self.pool.connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                # 1. Neural Decay: Update neuro_score based on half-life
                # Equation: score = score * 0.5^(days_since_recall / half_life)
                # In SQL, we use a simpler linear approximation or direct update if time elapsed
                conn.execute("""
                    UPDATE memories
                    SET neuro_score = MAX(0.1, neuro_score * 0.95)
                    WHERE is_protected = 0 AND (julianday('now') - julianday(accessed_at)) > 1
                """)

                # 2. Strengthen frequently accessed
                cursor = conn.execute("""
                    UPDATE memories
                    SET importance = MIN(1.0, importance + 0.05),
                        neuro_score = MIN(1.0, neuro_score + 0.1)
                    WHERE access_count > 5
                """)
                consolidated_count += cast(int, cursor.rowcount)

                # 3. Decay rarely accessed short-term
                cursor = conn.execute("""
                    UPDATE memories
                    SET importance = MAX(0.0, importance - 0.1),
                        neuro_score = MAX(0.1, neuro_score - 0.05)
                    WHERE memory_type = 'SHORT_TERM' AND access_count < 2 AND is_protected = 0
                """)
                consolidated_count += cast(int, cursor.rowcount)

                # 4. Promote important short-term to long-term
                cursor = conn.execute("""
                    UPDATE memories
                    SET memory_type = 'LONG_TERM'
                    WHERE memory_type = 'SHORT_TERM' AND (importance > 0.8 OR neuro_score > 0.8)
                """)
                consolidated_count += cast(int, cursor.rowcount)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error("Consolidation failed: %s", e, exc_info=True)
                raise

        return consolidated_count

    def decay_associations(self, batch_size: int = 5000) -> dict[str, Any]:
        """Apply time-based decay to association strengths (v14.0 Living Graph).

        Episodic edges decay fast (30-day half-life, exponential):
            w(t) = w_prev × e^(-0.0231 × Δt_days)

        Semantic edges decay slow (power-law, long tail):
            w(t) = w_0 × (1 + 0.1 × Δt_days)^(-0.5)

        Associations with w(t) < 0.05 are pruned.

        Returns:
            Dict with decay stats.
        """
        now_iso = datetime.now().isoformat()
        decayed = 0
        pruned = 0
        total = 0

        with self.pool.connection() as conn:
            conn.row_factory = sqlite3.Row

            # Process in batches for large association tables
            rows = conn.execute(
                """SELECT source_id, target_id, strength,
                          COALESCE(edge_type, 'semantic') as edge_type,
                          created_at
                   FROM associations
                   WHERE strength >= 0.05
                   ORDER BY ROWID
                   LIMIT ?""",
                (batch_size,),
            ).fetchall()

            total = len(rows)
            updates: list[tuple[float, str, str, str]] = []
            prune_pairs: list[tuple[str, str]] = []

            for row in rows:
                old_strength = row["strength"]
                edge_type = row["edge_type"]
                created_at = row["created_at"]

                if not created_at:
                    continue

                try:
                    created = datetime.fromisoformat(created_at)
                    days_old = max(0.0, (datetime.now() - created).total_seconds() / 86400.0)
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    continue

                if days_old < 0.5:
                    continue  # Skip very recent edges

                # Compute decayed strength
                if edge_type == "episodic":
                    # Exponential decay: 30-day half-life
                    new_strength = old_strength * math.exp(-0.0231 * days_old)
                else:
                    # Semantic: power-law (long tail)
                    new_strength = old_strength * ((1.0 + 0.1 * days_old) ** -0.5)

                new_strength = max(0.0, new_strength)

                if new_strength < 0.05:
                    prune_pairs.append((row["source_id"], row["target_id"]))
                    pruned += 1
                elif abs(new_strength - old_strength) > 0.001:
                    updates.append((new_strength, now_iso, row["source_id"], row["target_id"]))
                    decayed += 1

            # Apply updates
            if updates:
                with conn:
                    conn.executemany(
                        """UPDATE associations
                           SET strength = ?, last_traversed_at = COALESCE(last_traversed_at, ?)
                           WHERE source_id = ? AND target_id = ?""",
                        updates,
                    )

            # Prune dead edges
            if prune_pairs:
                with conn:
                    conn.executemany(
                        "DELETE FROM associations WHERE source_id = ? AND target_id = ?",
                        prune_pairs,
                    )

        result = {
            "status": "success",
            "associations_evaluated": total,
            "associations_decayed": decayed,
            "associations_pruned": pruned,
        }
        if total > 0:
            logger.info(
                "🔗 Association decay: %s decayed, %s pruned out of %s evaluated",
             decayed, pruned, total)
        return result

    def prune_associations(self, min_strength: float = 0.3) -> dict[str, Any]:
        """Prune weak associations below the minimum strength threshold.

        Args:
            min_strength: Minimum strength threshold for associations.

        Returns:
            Dict with prune stats.
        """
        with self.pool.connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM associations WHERE strength < ?",
                (min_strength,),
            )
            count = cursor.fetchone()[0]

            cursor = conn.execute(
                "DELETE FROM associations WHERE strength < ?",
                (min_strength,),
            )

        result = {
            "status": "success",
            "associations_pruned": count,
            "min_strength_threshold": min_strength,
        }
        logger.info("🔗 Pruned %s associations below strength %s", count, min_strength, exc_info=True)
        return result
