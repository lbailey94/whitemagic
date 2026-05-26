"""Knowledge Graph 2.0 (v16) - Batch NER with Typed Edge Storage.
================================================================
Enhanced knowledge graph with:
  - LightNER for fast pattern-based extraction
  - Batch processing for efficiency
  - Typed edges stored in associations table
  - Entity deduplication and normalization
  - Background daemon integration

Usage:
    from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2

    kg = get_kg_v2()
    result = kg.extract_and_store("memory_123", "WhiteMagic uses Rust for embeddings")
    # Creates typed edges: WhiteMagic --[USES]--> Rust
"""
from __future__ import annotations

import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from whitemagic.core.intelligence.lightweight_ner import get_light_ner

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """An extracted entity ready for storage."""
    name: str
    entity_type: str
    normalized_name: str  # Lowercase, underscored
    confidence: float
    source_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.entity_type,
            "normalized": self.normalized_name,
            "confidence": self.confidence,
            "source": self.source_id,
        }


@dataclass
class ExtractedRelation:
    """An extracted relation ready for storage."""
    subject: str
    predicate: str
    obj: str
    confidence: float
    source_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.obj,
            "confidence": self.confidence,
            "source": self.source_id,
        }


@dataclass
class ExtractionStats:
    """Statistics for KG extraction."""
    total_memories_processed: int = 0
    total_entities_extracted: int = 0
    total_relations_extracted: int = 0
    total_edges_stored: int = 0
    last_run: datetime | None = None
    rate: float = 0.0


class KnowledgeGraphV2:
    """Enhanced Knowledge Graph with LightNER and typed edge storage.

    Features:
    - Batch extraction for efficiency
    - Typed edges in associations table
    - Entity normalization and deduplication
    - Integration with embedding daemon
    """

    _instance: KnowledgeGraphV2 | None = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls, *args, **kwargs) -> KnowledgeGraphV2:
        """Singleton pattern for global KG."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._ner = get_light_ner()
        self._stats = ExtractionStats()
        self._entity_cache: dict[str, str] = {}  # normalized -> canonical name
        self._initialized = True

    def _normalize_entity(self, name: str) -> str:
        """Normalize entity name for deduplication."""
        # Lowercase, replace spaces with underscores
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        return normalized

    def _get_db(self) -> sqlite3.Connection | None:
        """Get database connection."""
        try:
            from whitemagic.config.paths import DB_PATH
            if not DB_PATH.exists():
                return None
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            return None

    def extract_from_text(self, text: str, source_id: str) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
        """Extract entities and relations from text.

        Args:
            text: Text to extract from
            source_id: Source memory ID

        Returns:
            Tuple of (entities, relations)
        """
        if not text or not text.strip():
            return [], []

        # Use LightNER for extraction
        ner_entities, ner_relations = self._ner.extract(text)

        # Convert to storage format
        entities = []
        for e in ner_entities:
            normalized = self._normalize_entity(e.text)
            entities.append(ExtractedEntity(
                name=e.text,
                entity_type=e.entity_type,
                normalized_name=normalized,
                confidence=e.confidence,
                source_id=source_id,
            ))
            # Update cache
            if normalized not in self._entity_cache:
                self._entity_cache[normalized] = e.text

        relations = []
        for subj, pred, obj in ner_relations:
            relations.append(ExtractedRelation(
                subject=subj,
                predicate=pred,
                obj=obj,
                confidence=0.7,  # Base confidence for pattern relations
                source_id=source_id,
            ))

        return entities, relations

    def store_relations(self, relations: list[ExtractedRelation], conn: sqlite3.Connection | None = None) -> int:
        """Store relations as typed edges in associations table.

        Args:
            relations: List of relations to store
            conn: Optional existing connection

        Returns:
            Number of edges stored
        """
        if not relations:
            return 0

        own_conn = conn is None
        if own_conn:
            conn = self._get_db()

        if conn is None:
            return 0

        try:
            now = datetime.now().isoformat()
            stored = 0

            for rel in relations:
                # Normalize object to entity ID
                obj_norm = self._normalize_entity(rel.obj)
                obj_id = f"entity:{obj_norm}"

                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO associations
                           (source_id, target_id, strength, direction, relation_type, edge_type, created_at, ingestion_time)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            rel.source_id,  # Memory ID as source
                            obj_id,          # Entity as target
                            rel.confidence,
                            "forward",
                            rel.predicate,   # Typed edge!
                            "semantic",
                            now,
                            now,
                        )
                    )
                    stored += 1
                except Exception:
                    pass

            conn.commit()
            return stored

        except Exception as e:
            logger.error(f"Failed to store relations: {e}")
            return 0
        finally:
            if own_conn and conn:
                conn.close()

    def extract_and_store(self, memory_id: str, text: str) -> dict[str, Any]:
        """Extract entities and relations from text and store them.

        Args:
            memory_id: Source memory ID
            text: Text to extract from

        Returns:
            Dict with extraction results
        """
        t0 = time.perf_counter()

        entities, relations = self.extract_from_text(text, memory_id)
        stored = self.store_relations(relations)

        elapsed = time.perf_counter() - t0

        return {
            "memory_id": memory_id,
            "entities_extracted": len(entities),
            "relations_extracted": len(relations),
            "edges_stored": stored,
            "elapsed_ms": round(elapsed * 1000, 1),
        }

    def batch_extract_and_store(
        self,
        memories: list[tuple[str, str]],  # (memory_id, text) pairs
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Batch extract and store from multiple memories.

        Args:
            memories: List of (memory_id, text) tuples
            batch_size: Batch size for processing

        Returns:
            Dict with batch results
        """
        t0 = time.perf_counter()

        total_entities = 0
        total_relations = 0
        total_stored = 0

        conn = self._get_db()
        if conn is None:
            return {"error": "DB unavailable", "processed": 0}

        try:
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]

                for memory_id, text in batch:
                    if not text or not text.strip():
                        continue

                    entities, relations = self.extract_from_text(text, memory_id)
                    total_entities += len(entities)
                    total_relations += len(relations)

                    stored = self.store_relations(relations, conn=conn)
                    total_stored += stored

            elapsed = time.perf_counter() - t0
            rate = len(memories) / elapsed if elapsed > 0 else 0

            # Update stats
            self._stats.total_memories_processed += len(memories)
            self._stats.total_entities_extracted += total_entities
            self._stats.total_relations_extracted += total_relations
            self._stats.total_edges_stored += total_stored
            self._stats.last_run = datetime.now()
            self._stats.rate = rate

            return {
                "processed": len(memories),
                "entities_extracted": total_entities,
                "relations_extracted": total_relations,
                "edges_stored": total_stored,
                "duration_s": round(elapsed, 2),
                "rate": round(rate, 1),
            }

        finally:
            conn.close()

    def process_unextracted_memories(self, limit: int = 1000) -> dict[str, Any]:
        """Process memories that haven't had entity extraction yet.

        Finds memories without typed edges and extracts entities from them.

        Args:
            limit: Maximum memories to process

        Returns:
            Dict with processing results
        """
        conn = self._get_db()
        if conn is None:
            return {"error": "DB unavailable", "processed": 0}

        try:
            # Find memories without typed edges
            # (memories where no associations with relation_type != 'associated_with' exist)
            sql = """
                SELECT m.id, COALESCE(m.title, '') || ' ' || COALESCE(m.content, '') as text
                FROM memories m
                WHERE m.memory_type != 'quarantined'
                  AND m.id NOT IN (
                    SELECT DISTINCT source_id FROM associations
                    WHERE relation_type IS NOT NULL
                      AND relation_type != 'associated_with'
                  )
                ORDER BY m.importance DESC
                LIMIT ?
            """

            rows = conn.execute(sql, (limit,)).fetchall()
            conn.close()

            memories = [(row[0], row[1].strip()) for row in rows if row[1].strip()]

            if not memories:
                return {"processed": 0, "reason": "no unextracted memories"}

            return self.batch_extract_and_store(memories)

        except Exception as e:
            logger.error(f"Failed to process unextracted memories: {e}")
            return {"error": str(e), "processed": 0}

    def get_entity_graph(self, entity_name: str, depth: int = 2) -> dict[str, Any]:
        """Get the graph around an entity.

        Args:
            entity_name: Entity name to query
            depth: Traversal depth (1 = direct connections only)

        Returns:
            Dict with entity and connected entities
        """
        normalized = self._normalize_entity(entity_name)
        entity_id = f"entity:{normalized}"

        conn = self._get_db()
        if conn is None:
            return {"found": False, "entity": entity_name}

        try:
            # Find direct connections
            sql = """
                SELECT target_id, relation_type, strength FROM associations
                WHERE source_id = ? AND relation_type IS NOT NULL
                ORDER BY strength DESC
                LIMIT 20
            """

            rows = conn.execute(sql, (entity_id,)).fetchall()

            connections = []
            for row in rows:
                target = row[0].replace("entity:", "") if row[0].startswith("entity:") else row[0]
                connections.append({
                    "entity": target,
                    "relation": row[1],
                    "strength": row[2],
                })

            return {
                "found": len(connections) > 0,
                "entity": entity_name,
                "normalized": normalized,
                "connections": connections,
                "total_connections": len(connections),
            }

        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get extraction statistics."""
        return {
            "total_memories_processed": self._stats.total_memories_processed,
            "total_entities_extracted": self._stats.total_entities_extracted,
            "total_relations_extracted": self._stats.total_relations_extracted,
            "total_edges_stored": self._stats.total_edges_stored,
            "last_run": self._stats.last_run.isoformat() if self._stats.last_run else None,
            "rate": self._stats.rate,
            "entity_cache_size": len(self._entity_cache),
        }

    def clear_cache(self) -> None:
        """Clear the entity cache."""
        self._entity_cache.clear()


def get_kg_v2() -> KnowledgeGraphV2:
    """Get the global KnowledgeGraphV2 instance."""
    return KnowledgeGraphV2()


# Integration with memory store
def extract_on_store(memory_id: str, text: str) -> dict[str, Any]:
    """Hook for automatic extraction on memory store.

    Call this when a memory is stored to automatically extract entities.
    """
    kg = get_kg_v2()
    return kg.extract_and_store(memory_id, text)
