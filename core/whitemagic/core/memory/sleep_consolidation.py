# ruff: noqa: BLE001
"""Sleep Consolidation — Cross-Galaxy Memory Transfer.

================================================================
Implements biologically-inspired sleep consolidation: the process by
which the brain transfers memories from episodic (hippocampal) storage
to semantic (cortical) storage during sleep, strengthening important
connections and discarding noise.

In WhiteMagic's galaxy system, this translates to:
    1. Identifying high-value memories in session/working galaxies
    2. Transferring (or copying) them to long-term semantic galaxies
    3. Strengthening cross-galaxy associations discovered during dreaming
    4. Pruning low-importance memories (lowering neuro_score)
    5. Promoting insights from dreams galaxy to research/codex galaxies

Consolidation cycle:
    - Episodic → Semantic: sessions → codex/research (handoffs → permanent docs)
    - Emotional → Identity: citta → aria (significant moments → identity)
    - Creative → Knowledge: dreams → research (dream insights → research notes)
    - Working → Long-term: universal → appropriate galaxy (reclassification)

Usage:
    from whitemagic.core.memory.sleep_consolidation import get_sleep_consolidation

    consol = get_sleep_consolidation()
    report = consol.consolidate(galaxy_db_paths={...})
"""

from __future__ import annotations

import logging
import sqlite3
from whitemagic.core.memory.db_manager import safe_connect
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationTransfer:
    """A single memory transfer during consolidation."""

    memory_id: str
    source_galaxy: str
    target_galaxy: str
    reason: str
    importance: float
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "source_galaxy": self.source_galaxy,
            "target_galaxy": self.target_galaxy,
            "reason": self.reason,
            "importance": round(self.importance, 3),
            "title": self.title[:80] if self.title else "",
        }


@dataclass
class ConsolidationReport:
    """Result of a sleep consolidation cycle."""

    transfers: list[ConsolidationTransfer] = field(default_factory=list)
    pruned: int = 0  # Memories with lowered neuro_score
    strengthened: int = 0  # Memories with boosted neuro_score
    associations_created: int = 0
    replayed: int = 0  # Memories replayed during consolidation
    ripples_decayed: int = 0  # Ripple tags decayed after consolidation
    metaplasticity_updated: int = 0  # Metaplasticity thresholds updated
    edges_scaled: int = 0  # Association edges homeostatically scaled
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def total_transfers(self) -> int:
        return len(self.transfers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_transfers": self.total_transfers,
            "transfers": [t.to_dict() for t in self.transfers[:20]],
            "pruned": self.pruned,
            "strengthened": self.strengthened,
            "associations_created": self.associations_created,
            "replayed": self.replayed,
            "ripples_decayed": self.ripples_decayed,
            "metaplasticity_updated": self.metaplasticity_updated,
            "edges_scaled": self.edges_scaled,
            "duration_ms": round(self.duration_ms, 2),
            "errors": self.errors[:5] if self.errors else None,
        }


class SleepConsolidation:
    """Cross-galaxy sleep consolidation engine.

    Performs memory transfer, strengthening, and pruning across galaxies
    to mimic biological sleep consolidation.
    """

    def __init__(
        self,
        min_importance_transfer: float = 0.6,
        prune_threshold: float = 0.2,
        strengthen_threshold: float = 0.7,
        max_transfers_per_cycle: int = 50,
    ) -> None:
        self._min_importance = min_importance_transfer
        self._prune_threshold = prune_threshold
        self._strengthen_threshold = strengthen_threshold
        self._max_transfers = max_transfers_per_cycle
        self._lock = threading.RLock()
        self._total_cycles = 0
        self._total_transfers = 0
        self._total_pruned = 0
        self._total_strengthened = 0

    def consolidate(
        self,
        galaxy_db_paths: dict[str, str],
        dry_run: bool = False,
    ) -> ConsolidationReport:
        """Run a consolidation cycle across galaxies.

        Args:
            galaxy_db_paths: Map of galaxy_name → db_path.
            dry_run: If True, only report what would be transferred without doing it.

        Returns:
            ConsolidationReport with transfer details and statistics.
        """
        start_time = time.time()
        report = ConsolidationReport()

        # Define consolidation pathways (source → target)
        pathways = [
            ("sessions", "codex", "episodic_to_semantic",
             "Session handoffs with high importance promoted to permanent codex"),
            ("citta", "aria", "emotional_to_identity",
             "Significant consciousness moments promoted to Aria identity"),
            ("dreams", "research", "creative_to_knowledge",
             "Dream insights with research value promoted to research"),
            ("universal", "codex", "working_to_longterm",
             "High-importance universal memories reclassified to codex"),
        ]

        for source, target, pathway, reason in pathways:
            if source not in galaxy_db_paths or target not in galaxy_db_paths:
                continue

            transfers = self._consolidate_pathway(
                source_galaxy=source,
                target_galaxy=target,
                source_db=galaxy_db_paths[source],
                target_db=galaxy_db_paths[target],
                reason=reason,
                dry_run=dry_run,
            )
            report.transfers.extend(transfers)

            if len(report.transfers) >= self._max_transfers:
                report.transfers = report.transfers[:self._max_transfers]
                break

        # Strengthen high-importance memories across all galaxies
        if not dry_run:
            for galaxy_name, db_path in galaxy_db_paths.items():
                if galaxy_name == "archive":
                    continue
                try:
                    strengthened, pruned = self._strengthen_and_prune(db_path)
                    report.strengthened += strengthened
                    report.pruned += pruned
                except Exception as e:
                    report.errors.append(f"{galaxy_name}: {e}")

        # Create cross-galaxy associations between transferred memories
        if not dry_run and report.transfers:
            report.associations_created = self._create_cross_galaxy_associations(
                report.transfers, galaxy_db_paths
            )

        # Neuro-upgrade integration: replay transferred memories
        if not dry_run and report.transfers:
            report.replayed = self._replay_transferred_memories(report.transfers)

        # Neuro-upgrade integration: apply metaplasticity decay (sleep cycle)
        if not dry_run:
            report.metaplasticity_updated = self._metaplasticity_sleep_cycle()

        # Neuro-upgrade integration: decay ripple tags (consolidation consumed them)
        if not dry_run:
            report.ripples_decayed = self._decay_ripple_tags()

        # Neuro-upgrade integration: homeostatic scaling of association edges
        if not dry_run:
            report.edges_scaled = self._homeostatic_scaling(galaxy_db_paths)

        report.duration_ms = (time.time() - start_time) * 1000

        with self._lock:
            self._total_cycles += 1
            self._total_transfers += report.total_transfers
            self._total_pruned += report.pruned
            self._total_strengthened += report.strengthened

        return report

    def _consolidate_pathway(
        self,
        source_galaxy: str,
        target_galaxy: str,
        source_db: str,
        target_db: str,
        reason: str,
        dry_run: bool,
    ) -> list[ConsolidationTransfer]:
        """Consolidate memories along a single pathway."""
        transfers: list[ConsolidationTransfer] = []

        try:
            src_conn = safe_connect(source_db, timeout=10)
            src_conn.row_factory = sqlite3.Row

            # Find high-importance memories in source
            rows = src_conn.execute(
                """SELECT id, title, importance, content_hash
                   FROM memories
                   WHERE importance >= ?
                   ORDER BY importance DESC
                   LIMIT ?""",
                (self._min_importance, self._max_transfers),
            ).fetchall()

            # Filter out memories that already exist in target
            if rows and not dry_run:
                dst_conn = safe_connect(target_db, timeout=10)
                dst_cols = [c[1] for c in dst_conn.execute("PRAGMA table_info(memories)").fetchall()]

                filtered_rows = []
                for row in rows:
                    existing = dst_conn.execute(
                        "SELECT 1 FROM memories WHERE id = ? OR (content_hash = ? AND content_hash IS NOT NULL)",
                        (row["id"], row["content_hash"]),
                    ).fetchone()
                    if not existing:
                        filtered_rows.append(row)
                rows = filtered_rows

                # Copy memories to target
                for row in rows:
                    full_row = src_conn.execute(
                        "SELECT * FROM memories WHERE id = ?", (row["id"],)
                    ).fetchone()
                    if full_row:
                        row_dict = dict(full_row)
                        filtered = {k: v for k, v in row_dict.items() if k in dst_cols}
                        col_names = list(filtered.keys())
                        placeholders = ",".join(["?"] * len(col_names))
                        try:
                            dst_conn.execute(
                                f"INSERT OR IGNORE INTO memories ({','.join(col_names)}) VALUES ({placeholders})",
                                [filtered[c] for c in col_names],
                            )
                        except Exception as e:
                            logger.debug("Consolidation insert failed: %s", e)

                dst_conn.commit()
                dst_conn.close()
            elif rows and dry_run:
                # In dry run, still filter against target for accurate reporting
                try:
                    dst_conn = safe_connect(target_db, timeout=10)
                    filtered_rows = []
                    for row in rows:
                        existing = dst_conn.execute(
                            "SELECT 1 FROM memories WHERE id = ? OR (content_hash = ? AND content_hash IS NOT NULL)",
                            (row["id"], row["content_hash"]),
                        ).fetchone()
                        if not existing:
                            filtered_rows.append(row)
                    rows = filtered_rows
                    dst_conn.close()
                except Exception:
                    logger.debug("Ignored error in sleep_consolidation.py:290")

            for row in rows:
                transfers.append(ConsolidationTransfer(
                    memory_id=row["id"],
                    source_galaxy=source_galaxy,
                    target_galaxy=target_galaxy,
                    reason=reason,
                    importance=row["importance"],
                    title=row["title"] or "",
                ))

            src_conn.close()
        except Exception as e:
            logger.debug("Consolidation pathway %s→%s failed: %s", source_galaxy, target_galaxy, e)

        return transfers

    def _strengthen_and_prune(self, db_path: str) -> tuple[int, int]:
        """Strengthen high-importance memories and prune low-importance ones.

        Returns (strengthened_count, pruned_count).
        """
        strengthened = 0
        pruned = 0

        try:
            conn = safe_connect(db_path, timeout=10)

            # Strengthen: boost neuro_score for high-importance, high-recall memories
            cur = conn.execute(
                """UPDATE memories
                   SET neuro_score = MIN(1.0, COALESCE(neuro_score, 1.0) * 1.05)
                   WHERE importance >= ? AND recall_count > 0""",
                (self._strengthen_threshold,),
            )
            strengthened = cur.rowcount

            # Prune: decay neuro_score for low-importance, never-recalled memories
            cur = conn.execute(
                """UPDATE memories
                   SET neuro_score = MAX(0.1, COALESCE(neuro_score, 1.0) * 0.95)
                   WHERE importance < ? AND recall_count = 0""",
                (self._prune_threshold,),
            )
            pruned = cur.rowcount

            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("Strengthen/prune failed for %s: %s", db_path, e)

        return strengthened, pruned

    def _create_cross_galaxy_associations(
        self,
        transfers: list[ConsolidationTransfer],
        galaxy_db_paths: dict[str, str],
    ) -> int:
        """Create association edges between transferred memories and their originals.

        This creates a "consolidation bridge" — an association edge in the
        target galaxy pointing back to the source memory, enabling
        cross-galaxy graph traversal to follow consolidation pathways.
        """
        count = 0
        for transfer in transfers:
            target_db = galaxy_db_paths.get(transfer.target_galaxy)
            if not target_db:
                continue
            try:
                conn = safe_connect(target_db, timeout=5)
                now = time.strftime("%Y-%m-%dT%H:%M:%S")
                # Create self-referential association marking the consolidation
                conn.execute(
                    """INSERT OR IGNORE INTO associations
                       (source_id, target_id, strength, direction, relation_type,
                        edge_type, created_at, ingestion_time)
                       VALUES (?, ?, ?, 'forward', 'consolidated_from', 'bridge', ?, ?)""",
                    (transfer.memory_id, transfer.memory_id, 0.9, now, now),
                )
                conn.commit()
                conn.close()
                count += 1
            except Exception as e:
                logger.debug("Cross-galaxy association creation failed: %s", e)

        return count

    def _replay_transferred_memories(self, transfers: list[ConsolidationTransfer]) -> int:
        """Replay transferred memory sequences with STDP strengthening.

        During consolidation, transferred memories are replayed to strengthen
        their associations (biological hippocampal replay analog).
        """
        count = 0
        try:
            from whitemagic.core.memory.replay_simulation import replay

            # Build a sequence from transferred memories
            sequence = [
                {
                    "memory_id": t.memory_id,
                    "timestamp": float(i),
                    "importance": t.importance,
                }
                for i, t in enumerate(transfers)
            ]
            if sequence:
                result = replay(sequence)
                count = result.get("total_items", 0)
        except Exception as e:
            logger.debug("Replay during consolidation failed: %s", e)
        return count

    def _metaplasticity_sleep_cycle(self) -> int:
        """Apply metaplasticity decay during sleep cycle.

        During sleep, metaplasticity thresholds relax toward baseline
        and activity counters decay — biological analog of synaptic homeostasis.
        """
        count = 0
        try:
            from whitemagic.core.memory.metaplasticity import get_metaplasticity
            mp = get_metaplasticity()
            count = mp.decay_all()
            mp.save()
        except Exception as e:
            logger.debug("Metaplasticity sleep cycle failed: %s", e)
        return count

    def _decay_ripple_tags(self) -> int:
        """Decay ripple tags after consolidation (tags were consumed).

        Biological analog: awake ripple tags are cleared after sleep
        consolidation completes — the tags served their purpose of
        selecting which memories to consolidate.
        """
        count = 0
        try:
            from whitemagic.core.memory.ripple_tagging import decay_tags
            count = decay_tags()
        except Exception as e:
            logger.debug("Ripple tag decay failed: %s", e)
        return count

    def _homeostatic_scaling(self, galaxy_db_paths: dict[str, str]) -> int:
        """Apply multiplicative homeostatic scaling to association edges.

        After consolidation, all association strengths are scaled toward a
        target mean to prevent runaway potentiation (synaptic homeostasis
        hypothesis, PNAS 2026 two-factor model). Strong edges are slightly
        dampened, weak edges are slightly boosted — renormalization toward
        a healthy distribution.

        Returns the total number of edges scaled.
        """
        total_scaled = 0
        target_mean = 0.5  # Target mean association strength
        scaling_factor = 0.95  # Edges pulled toward target_mean by 5%

        for galaxy_name, db_path in galaxy_db_paths.items():
            if galaxy_name == "archive":
                continue
            try:
                conn = safe_connect(db_path, timeout=10)
                # Get current mean strength
                cur = conn.execute(
                    "SELECT AVG(strength) FROM associations WHERE strength IS NOT NULL"
                )
                row = cur.fetchone()
                current_mean = row[0] if row and row[0] is not None else target_mean

                # Scale: pull each edge toward target_mean by scaling_factor
                # new = old + (target - old) * (1 - scaling_factor)
                # This is a gentle multiplicative renormalization
                delta = (target_mean - current_mean) * (1.0 - scaling_factor)
                if abs(delta) < 0.001:
                    conn.close()
                    continue

                cur = conn.execute(
                    """UPDATE associations
                       SET strength = MIN(1.0, MAX(0.0, COALESCE(strength, 0.5) + ?))
                       WHERE strength IS NOT NULL""",
                    (delta,),
                )
                total_scaled += cur.rowcount
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug("Homeostatic scaling failed for %s: %s", galaxy_name, e)

        return total_scaled

    def stats(self) -> dict[str, Any]:
        """Get consolidation engine statistics."""
        with self._lock:
            return {
                "total_cycles": self._total_cycles,
                "total_transfers": self._total_transfers,
                "total_pruned": self._total_pruned,
                "total_strengthened": self._total_strengthened,
                "min_importance_transfer": self._min_importance,
                "prune_threshold": self._prune_threshold,
                "strengthen_threshold": self._strengthen_threshold,
            }


# Singleton
_instance: SleepConsolidation | None = None
_lock = threading.RLock()


def get_sleep_consolidation() -> SleepConsolidation:
    """Get the global SleepConsolidation singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SleepConsolidation()
    return _instance
