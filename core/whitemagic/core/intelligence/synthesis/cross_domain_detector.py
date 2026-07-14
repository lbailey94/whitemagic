"""Cross-Domain Collision Detector — Dream Cycle Phase 2b.

Finds memory pairs that exhibit high behavioral similarity (shared tags,
memory types, association patterns) but low semantic similarity (different
embedding content). These "collisions" indicate that two memories from
different domains are being treated similarly by the system — a strong
signal for abstracting a cross-domain schema.

The detector is called during the Dream Cycle's serendipity phase to
surface latent structural patterns that wouldn't be found by graph-based
bridge discovery (which relies on graph topology, not behavioral/semantic
divergence).

Usage:
    from whitemagic.core.intelligence.synthesis.cross_domain_detector import (
        get_cross_domain_detector,
    )
    detector = get_cross_domain_detector()
    collisions = detector.detect(sample_limit=500)
"""

from __future__ import annotations

import logging
import sqlite3
from whitemagic.core.memory.db_manager import safe_connect, pooled_connection
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CollisionPair:
    """A pair of memories with high behavioral but low semantic similarity."""

    memory_a_id: str
    memory_b_id: str
    memory_a_title: str
    memory_b_title: str
    shared_tags: list[str]
    same_type: bool
    behavioral_score: float  # 0-1, based on tag/type overlap
    semantic_similarity: float  # 0-1, cosine similarity of embeddings
    collision_score: float  # behavioral_score * (1 - semantic_similarity)
    schema_hint: str  # Abstracted pattern description
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_a_id": self.memory_a_id,
            "memory_b_id": self.memory_b_id,
            "memory_a_title": self.memory_a_title,
            "memory_b_title": self.memory_b_title,
            "shared_tags": self.shared_tags[:5],
            "same_type": self.same_type,
            "behavioral_score": round(self.behavioral_score, 3),
            "semantic_similarity": round(self.semantic_similarity, 3),
            "collision_score": round(self.collision_score, 3),
            "schema_hint": self.schema_hint,
            "timestamp": self.timestamp,
        }


@dataclass
class CoreSchema:
    """An abstracted schema extracted from collision pairs."""

    schema_id: str
    name: str
    tags: list[str]
    memory_type: str
    member_count: int
    avg_behavioral_score: float
    avg_semantic_distance: float
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "tags": self.tags[:5],
            "memory_type": self.memory_type,
            "member_count": self.member_count,
            "avg_behavioral_score": round(self.avg_behavioral_score, 3),
            "avg_semantic_distance": round(self.avg_semantic_distance, 3),
            "description": self.description,
            "timestamp": self.timestamp,
        }


class CrossDomainCollisionDetector:
    """Detects cross-domain collisions in the memory store.

    A collision = high behavioral similarity + low semantic similarity.
    This means two memories are treated similarly by the system (same tags,
    same type, similar association patterns) but their content is semantically
    distant — they come from different knowledge domains.

    These pairs are candidates for schema abstraction: the shared behavioral
    pattern is the schema, the different content is the domain variation.
    """

    def __init__(self, db_path: str | None = None) -> None:
        from whitemagic.config.paths import DB_PATH

        self.db_path = db_path or str(DB_PATH)
        self._lock = threading.RLock()
        self._total_collisions = 0
        self._total_schemas = 0

    def _get_conn(self) -> sqlite3.Connection:
        conn = safe_connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def detect(
        self,
        sample_limit: int = 500,
        min_behavioral: float = 0.3,
        max_semantic: float = 0.5,
        top_n: int = 10,
    ) -> list[CollisionPair]:
        """Detect cross-domain collision pairs.

        Args:
            sample_limit: Max memories to scan.
            min_behavioral: Minimum behavioral similarity to consider.
            max_semantic: Maximum semantic similarity (above = not a collision).
            top_n: Max pairs to return.

        Returns:
            List of CollisionPair objects sorted by collision_score.
        """
        start = time.perf_counter()
        collisions: list[CollisionPair] = []

        try:
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT m.id, m.title, m.content, m.memory_type,
                          GROUP_CONCAT(t.tag) as tags
                   FROM memories m
                   LEFT JOIN tags t ON m.id = t.memory_id
                   GROUP BY m.id
                   ORDER BY m.created_at DESC
                   LIMIT ?""",
                (sample_limit,),
            ).fetchall()
            conn.close()

            if len(rows) < 2:
                return collisions

            memories = []
            for r in rows:
                tags_str = r["tags"] or ""
                tags = (
                    set(t.strip() for t in tags_str.split(",") if t.strip())
                    if tags_str
                    else set()
                )
                memories.append(
                    {
                        "id": r["id"],
                        "title": r["title"] or "Untitled",
                        "content": r["content"] or "",
                        "memory_type": r["memory_type"] or "UNKNOWN",
                        "tags": tags,
                    }
                )

            embeddings = self._load_embeddings([m["id"] for m in memories])

            # Find collision pairs
            for i, memorie in enumerate(memories):
                for j in range(i + 1, len(memories)):
                    a, b = memories[i], memories[j]

                    # Behavioral similarity: Jaccard of tags + type match
                    tag_overlap = self._jaccard(a["tags"], b["tags"])
                    type_match = 1.0 if a["memory_type"] == b["memory_type"] else 0.0
                    behavioral = tag_overlap * 0.7 + type_match * 0.3

                    if behavioral < min_behavioral:
                        continue

                    # Semantic similarity via embeddings
                    sem_sim = self._cosine_sim(
                        embeddings.get(a["id"]),
                        embeddings.get(b["id"]),
                    )
                    if sem_sim is None:
                        continue

                    if sem_sim >= max_semantic:
                        continue  # Too similar semantically — not a collision

                    collision_score = behavioral * (1.0 - sem_sim)

                    # Generate schema hint from shared tags
                    shared_tags = sorted(a["tags"] & b["tags"])
                    schema_hint = self._generate_schema_hint(
                        shared_tags,
                        a["memory_type"],
                        b["title"],
                        a["title"],
                    )

                    collisions.append(
                        CollisionPair(
                            memory_a_id=a["id"],
                            memory_b_id=b["id"],
                            memory_a_title=a["title"],
                            memory_b_title=b["title"],
                            shared_tags=shared_tags,
                            same_type=a["memory_type"] == b["memory_type"],
                            behavioral_score=behavioral,
                            semantic_similarity=sem_sim,
                            collision_score=collision_score,
                            schema_hint=schema_hint,
                        )
                    )

            # Sort by collision score (highest = most interesting)
            collisions.sort(key=lambda c: c.collision_score, reverse=True)
            collisions = collisions[:top_n]

            # Abstract into schemas
            if collisions:
                schemas = self._abstract_schemas(collisions)
                if schemas:
                    self._persist_schemas(schemas, conn=None)

            with self._lock:
                self._total_collisions += len(collisions)

            elapsed = (time.perf_counter() - start) * 1000
            if collisions:
                logger.info(
                    "Cross-domain collisions: %d found, %d schemas abstracted (%.0fms)",
                    len(collisions),
                    len(schemas) if collisions else 0,
                    elapsed,
                )

        except Exception as e:
            logger.warning(
                "Cross-domain collision detection failed: %s", e, exc_info=True
            )

        return collisions

    def _load_embeddings(self, memory_ids: list[str]) -> dict[str, list[float]]:
        """Load embeddings for given memory IDs."""
        embeddings: dict[str, list[float]] = {}
        try:
            with pooled_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ",".join("?" * len(memory_ids))
                rows = conn.execute(
                    f"SELECT memory_id, embedding FROM memory_embeddings WHERE memory_id IN ({placeholders})",
                    memory_ids,
                ).fetchall()

            import json

            for r in rows:
                emb = r["embedding"]
                if emb:
                    vec = json.loads(emb) if isinstance(emb, str) else list(emb)
                    if len(vec) >= 64:
                        embeddings[r["memory_id"]] = (
                            vec[:384] if len(vec) > 384 else vec
                        )
        except Exception as e:
            logger.debug("Embedding load failed: %s", e)

        return embeddings

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        """Jaccard similarity between two tag sets."""
        if not a and not b:
            return 0.0
        union = a | b
        if not union:
            return 0.0
        return len(a & b) / len(union)

    @staticmethod
    def _cosine_sim(a: list[float] | None, b: list[float] | None) -> float | None:
        """Cosine similarity between two embedding vectors."""
        if a is None or b is None:
            return None
        try:
            import numpy as np

            va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            if na < 1e-8 or nb < 1e-8:
                return None
            return float(np.dot(va, vb) / (na * nb))
        except Exception:
            return None

    @staticmethod
    def _generate_schema_hint(
        shared_tags: list[str],
        memory_type: str,
        title_a: str,
        title_b: str,
    ) -> str:
        """Generate a human-readable schema hint from a collision pair."""
        tag_str = ", ".join(shared_tags[:3]) if shared_tags else "no shared tags"
        return (
            f"Schema [{tag_str}] ({memory_type}): "
            f"'{title_a[:30]}' ~ '{title_b[:30]}' — "
            f"same behavioral pattern, different domain content"
        )

    def _abstract_schemas(self, collisions: list[CollisionPair]) -> list[CoreSchema]:
        """Abstract collision pairs into core schemas.

        Groups collisions by their shared tag sets and memory type,
        creating a schema for each group with 2+ members.
        """
        groups: dict[tuple[str, ...], list[CollisionPair]] = {}

        for c in collisions:
            key = (tuple(sorted(c.shared_tags[:3])),)
            groups.setdefault(key, []).append(c)

        schemas: list[CoreSchema] = []
        for key, members in groups.items():
            if len(members) < 2:
                continue

            tags = list(key[0])
            mem_type = members[0].same_type and "mixed" or "cross-type"

            avg_beh = sum(m.behavioral_score for m in members) / len(members)
            avg_sem_dist = sum(1.0 - m.semantic_similarity for m in members) / len(
                members
            )

            # Collect unique memory IDs
            member_ids = set()
            for m in members:
                member_ids.add(m.memory_a_id)
                member_ids.add(m.memory_b_id)

            schema = CoreSchema(
                schema_id=f"schema_{hash(key) & 0xFFFFFFFF:08x}",
                name=f"Cross-domain: {', '.join(tags[:3])}"
                if tags
                else "Cross-domain pattern",
                tags=tags,
                memory_type=mem_type,
                member_count=len(member_ids),
                avg_behavioral_score=avg_beh,
                avg_semantic_distance=avg_sem_dist,
                description=(
                    f"Abstracted from {len(members)} collision pairs. "
                    f"Behavioral alignment {avg_beh:.2f} with semantic distance {avg_sem_dist:.2f}. "
                    f"Suggests a reusable pattern across domains."
                ),
            )
            schemas.append(schema)

        with self._lock:
            self._total_schemas += len(schemas)

        return schemas

    def _persist_schemas(
        self, schemas: list[CoreSchema], conn: sqlite3.Connection | None
    ) -> None:
        """Persist abstracted schemas as LONG_TERM memories."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            from whitemagic.core.memory.unified_types import MemoryType

            um = get_unified_memory()

            for schema in schemas:
                try:
                    um.store(
                        content=schema.description,
                        memory_type=MemoryType.LONG_TERM,
                        tags={"cross_domain_schema", "dream_synthesis", "v23"},
                        importance=0.6 + schema.avg_behavioral_score * 0.2,
                        title=f"Schema: {schema.name}",
                        metadata={
                            "source": "cross_domain_collision_detector",
                            "schema_id": schema.schema_id,
                            "member_count": schema.member_count,
                            "avg_behavioral_score": schema.avg_behavioral_score,
                            "avg_semantic_distance": schema.avg_semantic_distance,
                        },
                        galaxy="creative_solutions",
                    )
                except Exception as e:
                    logger.debug("Schema persist failed: %s", e)
        except Exception as e:
            logger.debug("Schema persistence skipped: %s", e)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_collisions": self._total_collisions,
                "total_schemas": self._total_schemas,
            }


_detector: CrossDomainCollisionDetector | None = None
_detector_lock = threading.RLock()


def get_cross_domain_detector(
    db_path: str | None = None,
) -> CrossDomainCollisionDetector:
    """Get the global CrossDomainCollisionDetector singleton."""
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = CrossDomainCollisionDetector(db_path=db_path)
    return _detector
