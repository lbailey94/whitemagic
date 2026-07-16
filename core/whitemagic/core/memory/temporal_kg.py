"""Temporal Knowledge Graph — state tracking and temporal validity.

Implements Gap C from the Memory & Cognitive Systems Strategy 2026.

Tracks how facts/entities change over time, enabling:
  - Supersession chains: "Alice preferred Python" → "Alice now prefers Rust"
  - Temporal validity: is this fact still current or has it been superseded?
  - "What changed since X" queries
  - FAMA-style temporal scoring for search relevance

The temporal KG stores (subject, predicate, object, valid_from, valid_to,
superseded_by) tuples in a dedicated SQLite table. When a new fact
contradicts an existing one, the old fact is marked as superseded.

FAMA scoring (Freshness-Aware Memory Access):
  - Fresh facts (not superseded) get a temporal boost
  - Stale facts (superseded) get a temporal penalty
  - Facts with known valid_from dates get recency-weighted scoring

Usage:
    from whitemagic.core.memory.temporal_kg import TemporalKnowledgeGraph

    tkg = TemporalKnowledgeGraph()
    tkg.assert_fact("alice", "prefers_language", "Rust",
                    valid_from="2026-07-01", supersede=True)
    current = tkg.get_current_facts("alice", "prefers_language")
    changes = tkg.changes_since("2026-06-01")
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from whitemagic.core.memory.db_manager import safe_connect
from whitemagic.config.paths import WM_ROOT

logger = logging.getLogger(__name__)

_TKG_DB_PATH = WM_ROOT / "memory" / "temporal_kg.db"

# FAMA scoring weights
FAMA_FRESH_BOOST = 0.15  # Boost for current (non-superseded) facts
FAMA_STALE_PENALTY = 0.20  # Penalty for superseded facts
FAMA_RECENCY_DECAY_DAYS = 90  # Half-life for recency weighting


@dataclass
class TemporalFact:
    """A temporally-valid fact in the knowledge graph."""
    id: str
    subject: str
    predicate: str
    object: str
    valid_from: str  # ISO timestamp
    valid_to: str | None = None  # None = still current
    superseded_by: str | None = None
    source_memory_id: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_current(self) -> bool:
        return self.valid_to is None and self.superseded_by is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "superseded_by": self.superseded_by,
            "source_memory_id": self.source_memory_id,
            "confidence": self.confidence,
            "is_current": self.is_current,
            "metadata": self.metadata,
        }


class TemporalKnowledgeGraph:
    """Temporal knowledge graph with supersession tracking and FAMA scoring.

    Stores facts as (subject, predicate, object) triples with temporal
    validity windows. When a new fact contradicts an existing one, the
    old fact is superseded.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or str(_TKG_DB_PATH)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the temporal KG database."""
        try:
            conn = safe_connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_facts (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    superseded_by TEXT,
                    source_memory_id TEXT,
                    confidence REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tf_subject_pred
                ON temporal_facts(subject, predicate)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tf_current
                ON temporal_facts(superseded_by) WHERE superseded_by IS NULL
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tf_valid_from
                ON temporal_facts(valid_from)
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to init temporal KG DB: %s", e)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def assert_fact(
        self,
        subject: str,
        predicate: str,
        object: str,
        valid_from: str | None = None,
        source_memory_id: str = "",
        confidence: float = 1.0,
        supersede: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Assert a new fact, optionally superseding existing ones.

        Args:
            subject: Entity the fact is about (e.g., "alice")
            predicate: Property/relationship (e.g., "prefers_language")
            object: Value (e.g., "Rust")
            valid_from: When this fact became true (ISO timestamp)
            source_memory_id: Memory that asserted this fact
            confidence: Confidence score (0-1)
            supersede: If True, mark existing current facts as superseded
            metadata: Additional metadata

        Returns:
            The fact ID.
        """
        ts = valid_from or self._now_iso()
        fact_id = f"tf_{int(time.time() * 1000)}_{hash((subject, predicate, object)) & 0xFFFFFF:06x}"

        with self._lock:
            conn = safe_connect(self._db_path)
            try:
                # Supersede existing current facts for same (subject, predicate)
                if supersede:
                    conn.execute("""
                        UPDATE temporal_facts
                        SET valid_to = ?, superseded_by = ?
                        WHERE subject = ? AND predicate = ?
                        AND superseded_by IS NULL AND valid_to IS NULL
                    """, (ts, fact_id, subject, predicate))

                # Insert new fact
                conn.execute("""
                    INSERT INTO temporal_facts
                        (id, subject, predicate, object, valid_from,
                         source_memory_id, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fact_id, subject, predicate, object, ts,
                    source_memory_id, confidence,
                    json.dumps(metadata or {}),
                ))
                conn.commit()
            finally:
                conn.close()

        return fact_id

    def get_current_facts(
        self,
        subject: str,
        predicate: str | None = None,
    ) -> list[TemporalFact]:
        """Get current (non-superseded) facts for a subject.

        Args:
            subject: Entity to query
            predicate: Optional predicate filter

        Returns:
            List of current TemporalFact objects.
        """
        conn = safe_connect(self._db_path)
        try:
            if predicate:
                rows = conn.execute("""
                    SELECT * FROM temporal_facts
                    WHERE subject = ? AND predicate = ?
                    AND superseded_by IS NULL AND valid_to IS NULL
                    ORDER BY valid_from DESC
                """, (subject, predicate)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM temporal_facts
                    WHERE subject = ?
                    AND superseded_by IS NULL AND valid_to IS NULL
                    ORDER BY valid_from DESC
                """, (subject,)).fetchall()

            return [self._row_to_fact(r) for r in rows]
        finally:
            conn.close()

    def get_fact_history(
        self,
        subject: str,
        predicate: str,
    ) -> list[TemporalFact]:
        """Get full history of facts for a (subject, predicate) pair.

        Returns facts ordered from newest to oldest, including superseded ones.
        """
        conn = safe_connect(self._db_path)
        try:
            rows = conn.execute("""
                SELECT * FROM temporal_facts
                WHERE subject = ? AND predicate = ?
                ORDER BY valid_from DESC
            """, (subject, predicate)).fetchall()
            return [self._row_to_fact(r) for r in rows]
        finally:
            conn.close()

    def changes_since(
        self,
        since: str,
        subject: str | None = None,
    ) -> list[TemporalFact]:
        """Get facts that changed (were asserted or superseded) since a date.

        Args:
            since: ISO timestamp
            subject: Optional subject filter

        Returns:
            List of facts that changed since the given date.
        """
        conn = safe_connect(self._db_path)
        try:
            if subject:
                rows = conn.execute("""
                    SELECT * FROM temporal_facts
                    WHERE (valid_from >= ? OR (valid_to IS NOT NULL AND valid_to >= ?))
                    AND subject = ?
                    ORDER BY valid_from DESC
                """, (since, since, subject)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM temporal_facts
                    WHERE valid_from >= ? OR (valid_to IS NOT NULL AND valid_to >= ?)
                    ORDER BY valid_from DESC
                """, (since, since)).fetchall()
            return [self._row_to_fact(r) for r in rows]
        finally:
            conn.close()

    def fama_score(self, memory_id: str, reference_time: str | None = None) -> float:
        """Compute FAMA (Freshness-Aware Memory Access) score for a memory.

        Combines:
        - Freshness: is the fact still current? (+FAMA_FRESH_BOOST)
        - Staleness: has it been superseded? (-FAMA_STALE_PENALTY)
        - Recency: how recent is the fact? (exponential decay)

        Args:
            memory_id: The memory ID to score
            reference_time: Optional reference time (default: now)

        Returns:
            FAMA score adjustment (additive to base relevance score)
        """
        conn = safe_connect(self._db_path)
        try:
            # Find facts sourced from this memory
            rows = conn.execute("""
                SELECT * FROM temporal_facts
                WHERE source_memory_id = ?
            """, (memory_id,)).fetchall()

            if not rows:
                return 0.0  # No temporal facts → neutral

            ref_time = datetime.fromisoformat(reference_time) if reference_time else datetime.now(timezone.utc)

            total_adjustment = 0.0
            for row in rows:
                fact = self._row_to_fact(row)

                if fact.is_current:
                    total_adjustment += FAMA_FRESH_BOOST * fact.confidence
                else:
                    total_adjustment -= FAMA_STALE_PENALTY * fact.confidence

                # Recency decay
                try:
                    valid_from_dt = datetime.fromisoformat(fact.valid_from.replace("Z", "+00:00"))
                    age_days = (ref_time - valid_from_dt).total_seconds() / 86400.0
                    recency_factor = 0.5 ** (age_days / FAMA_RECENCY_DECAY_DAYS)
                    total_adjustment += 0.05 * recency_factor * fact.confidence
                except (ValueError, TypeError):
                    pass

            return max(-0.5, min(0.5, total_adjustment))
        finally:
            conn.close()

    def get_superseded_memory_ids(self) -> set[str]:
        """Get the set of memory IDs that sourced superseded facts.

        These memories should be filtered out of search results when
        temporal_filter is enabled, as they contain outdated information.
        """
        conn = safe_connect(self._db_path)
        try:
            rows = conn.execute("""
                SELECT DISTINCT source_memory_id FROM temporal_facts
                WHERE superseded_by IS NOT NULL
                AND source_memory_id != ''
            """).fetchall()
            return {row[0] for row in rows}
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)
            return set()
        finally:
            conn.close()

    def extract_and_assert(
        self,
        content: str,
        memory_id: str = "",
    ) -> list[str]:
        """Extract facts from content and assert them in the temporal KG.

        Uses simple pattern matching to find (subject, predicate, object)
        triples. This is a lightweight extractor — for production use,
        this would be replaced with a proper NER + relation extraction pipeline.

        Returns list of asserted fact IDs.
        """
        fact_ids: list[str] = []

        # Pattern: "X prefers Y" / "X uses Y" / "X likes Y" / "X switched from A to B"
        import re

        # Preference patterns
        for match in re.finditer(r"(\w+)\s+(?:prefers?|uses?|likes?|chose|selected)\s+(\w+)", content, re.IGNORECASE):
            subject, obj = match.group(1).lower(), match.group(2).lower()
            fact_ids.append(self.assert_fact(
                subject=subject, predicate="preference", object=obj,
                source_memory_id=memory_id,
            ))

        # Switch patterns: "X switched from A to B"
        for match in re.finditer(r"(\w+)\s+switched\s+from\s+(\w+)\s+to\s+(\w+)", content, re.IGNORECASE):
            subject, new_obj = match.group(1).lower(), match.group(3).lower()
            fact_ids.append(self.assert_fact(
                subject=subject, predicate="preference", object=new_obj,
                source_memory_id=memory_id,
            ))

        # Location patterns: "X moved from A to B" / "X is in Y"
        for match in re.finditer(r"(\w+)\s+(?:moved\s+to|is\s+in|lives\s+in)\s+(\w+)", content, re.IGNORECASE):
            subject, obj = match.group(1).lower(), match.group(2).lower()
            fact_ids.append(self.assert_fact(
                subject=subject, predicate="location", object=obj,
                source_memory_id=memory_id,
            ))

        return fact_ids

    def stats(self) -> dict[str, Any]:
        """Get temporal KG statistics."""
        conn = safe_connect(self._db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM temporal_facts").fetchone()[0]
            current = conn.execute(
                "SELECT COUNT(*) FROM temporal_facts WHERE superseded_by IS NULL AND valid_to IS NULL"
            ).fetchone()[0]
            superseded = conn.execute(
                "SELECT COUNT(*) FROM temporal_facts WHERE superseded_by IS NOT NULL"
            ).fetchone()[0]
            subjects = conn.execute(
                "SELECT COUNT(DISTINCT subject) FROM temporal_facts"
            ).fetchone()[0]
            return {
                "total_facts": total,
                "current_facts": current,
                "superseded_facts": superseded,
                "unique_subjects": subjects,
            }
        finally:
            conn.close()

    def _row_to_fact(self, row: sqlite3.Row) -> TemporalFact:
        """Convert a database row to a TemporalFact."""
        meta = {}
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        return TemporalFact(
            id=row["id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            superseded_by=row["superseded_by"],
            source_memory_id=row["source_memory_id"],
            confidence=row["confidence"],
            metadata=meta,
        )


# Singleton
_instance: TemporalKnowledgeGraph | None = None
_lock = threading.RLock()


def get_temporal_kg() -> TemporalKnowledgeGraph:
    """Get the global TemporalKnowledgeGraph singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = TemporalKnowledgeGraph()
    return _instance
