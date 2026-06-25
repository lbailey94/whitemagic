"""Tests for Cross-Domain Collision Detector."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from whitemagic.core.intelligence.synthesis.cross_domain_detector import (
    CollisionPair,
    CoreSchema,
    CrossDomainCollisionDetector,
    get_cross_domain_detector,
)


def _make_test_db(tmpdir: str) -> str:
    """Create a temporary test database with memories, tags, and embeddings."""
    db_path = str(Path(tmpdir) / "test_collisions.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            memory_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE tags (
            memory_id TEXT,
            tag TEXT
        );
        CREATE TABLE memory_embeddings (
            memory_id TEXT PRIMARY KEY,
            embedding TEXT
        );
    """)

    # Insert memories with shared tags but different content
    import json
    memories = [
        ("mem_a", "Refactor API", "We need to restructure the REST endpoints", "OBSERVATION", ["refactor", "api", "technical"]),
        ("mem_b", "Reorganize Garden", "Rearrange the joy garden for better flow", "OBSERVATION", ["refactor", "garden", "emotional"]),
        ("mem_c", "Debug Router", "Fix the inference router token budget bug", "OBSERVATION", ["debug", "router", "technical"]),
        ("mem_d", "Debug Dream", "Fix dream cycle phase ordering issue", "OBSERVATION", ["debug", "dream", "emotional"]),
        ("mem_e", "Unrelated Memory", "Random content about cooking", "REFLECTION", ["cooking", "food"]),
    ]

    for mid, title, content, mtype, tags in memories:
        conn.execute(
            "INSERT INTO memories (id, title, content, memory_type) VALUES (?, ?, ?, ?)",
            (mid, title, content, mtype),
        )
        for tag in tags:
            conn.execute("INSERT INTO tags (memory_id, tag) VALUES (?, ?)", (mid, tag))

    # Insert embeddings — make semantically similar ones have similar vectors
    # mem_a and mem_b share "refactor" tag but should have different embeddings
    embeddings = {
        "mem_a": [0.9, 0.1, 0.05, 0.0] * 96,  # API/technical direction
        "mem_b": [0.1, 0.9, 0.05, 0.0] * 96,  # Garden/emotional direction
        "mem_c": [0.05, 0.0, 0.9, 0.1] * 96,  # Router/technical
        "mem_d": [0.05, 0.0, 0.1, 0.9] * 96,  # Dream/emotional
        "mem_e": [0.5, 0.5, 0.5, 0.5] * 96,   # Neutral
    }

    for mid, emb in embeddings.items():
        conn.execute(
            "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
            (mid, json.dumps(emb)),
        )

    conn.commit()
    conn.close()
    return db_path


class TestCrossDomainCollisionDetector:
    def test_detect_finds_collisions(self, tmp_path):
        """Should find collision pairs with high behavioral, low semantic similarity."""
        db_path = _make_test_db(str(tmp_path))
        detector = CrossDomainCollisionDetector(db_path=db_path)
        collisions = detector.detect(sample_limit=100, min_behavioral=0.2, max_semantic=0.8, top_n=10)

        # Should find at least the refactor pair (mem_a, mem_b) and debug pair (mem_c, mem_d)
        assert len(collisions) > 0

        # Check that collision pairs have the expected structure
        for c in collisions:
            assert isinstance(c, CollisionPair)
            assert c.behavioral_score > 0.0
            assert c.semantic_similarity < 1.0
            assert c.collision_score > 0.0
            assert len(c.schema_hint) > 0

    def test_detect_respects_min_behavioral(self, tmp_path):
        """Should filter out pairs below minimum behavioral similarity."""
        db_path = _make_test_db(str(tmp_path))
        detector = CrossDomainCollisionDetector(db_path=db_path)

        # High threshold should filter most pairs
        collisions = detector.detect(sample_limit=100, min_behavioral=0.9, max_semantic=0.9, top_n=10)
        # With Jaccard on 3 tags, 0.9 is very high — likely no pairs
        for c in collisions:
            assert c.behavioral_score >= 0.9

    def test_detect_respects_max_semantic(self, tmp_path):
        """Should filter out pairs above maximum semantic similarity."""
        db_path = _make_test_db(str(tmp_path))
        detector = CrossDomainCollisionDetector(db_path=db_path)

        # Very low max_semantic means only very dissimilar pairs
        collisions = detector.detect(sample_limit=100, min_behavioral=0.1, max_semantic=0.1, top_n=10)
        for c in collisions:
            assert c.semantic_similarity < 0.1

    def test_detect_returns_empty_on_empty_db(self, tmp_path):
        """Should return empty list when no memories exist."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE memories (id TEXT PRIMARY KEY, title TEXT, content TEXT, memory_type TEXT, created_at TEXT);
            CREATE TABLE tags (memory_id TEXT, tag TEXT);
            CREATE TABLE memory_embeddings (memory_id TEXT PRIMARY KEY, embedding TEXT);
        """)
        conn.close()

        detector = CrossDomainCollisionDetector(db_path=db_path)
        collisions = detector.detect(sample_limit=100)
        assert collisions == []

    def test_collision_pair_to_dict(self):
        """CollisionPair.to_dict should produce expected fields."""
        pair = CollisionPair(
            memory_a_id="a",
            memory_b_id="b",
            memory_a_title="Title A",
            memory_b_title="Title B",
            shared_tags=["refactor", "api"],
            same_type=True,
            behavioral_score=0.7,
            semantic_similarity=0.2,
            collision_score=0.56,
            schema_hint="Schema [refactor, api]",
        )
        d = pair.to_dict()
        assert d["memory_a_id"] == "a"
        assert d["shared_tags"] == ["refactor", "api"]
        assert d["collision_score"] == 0.56

    def test_core_schema_to_dict(self):
        """CoreSchema.to_dict should produce expected fields."""
        schema = CoreSchema(
            schema_id="schema_12345678",
            name="Cross-domain: refactor",
            tags=["refactor"],
            memory_type="OBSERVATION",
            member_count=4,
            avg_behavioral_score=0.6,
            avg_semantic_distance=0.8,
            description="Test schema",
        )
        d = schema.to_dict()
        assert d["schema_id"] == "schema_12345678"
        assert d["member_count"] == 4

    def test_jaccard(self):
        """Jaccard similarity should compute correctly."""
        assert CrossDomainCollisionDetector._jaccard({"a", "b"}, {"a", "b"}) == 1.0
        assert CrossDomainCollisionDetector._jaccard({"a"}, {"b"}) == 0.0
        assert CrossDomainCollisionDetector._jaccard(set(), set()) == 0.0
        assert CrossDomainCollisionDetector._jaccard({"a", "b", "c"}, {"a", "b"}) == 2 / 3

    def test_cosine_sim(self):
        """Cosine similarity should compute correctly."""
        assert CrossDomainCollisionDetector._cosine_sim(None, [1.0]) is None
        assert CrossDomainCollisionDetector._cosine_sim([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert CrossDomainCollisionDetector._cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_get_stats(self, tmp_path):
        """get_stats should return cumulative counters."""
        db_path = _make_test_db(str(tmp_path))
        detector = CrossDomainCollisionDetector(db_path=db_path)
        detector.detect(sample_limit=100, min_behavioral=0.1, top_n=5)
        stats = detector.get_stats()
        assert "total_collisions" in stats
        assert "total_schemas" in stats

    def test_singleton(self):
        """get_cross_domain_detector should return the same instance."""
        d1 = get_cross_domain_detector()
        d2 = get_cross_domain_detector()
        assert d1 is d2
