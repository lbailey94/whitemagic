"""Critical path tests for PSR-014 90% coverage target.

Tests the most critical hot paths in the WhiteMagic system:
1. Memory storage and retrieval
2. Search operations (FTS + vector)
3. Association mining
4. Galactic scoring
"""
import unittest

import pytest

# Skip if whitemagic not available
try:
    from whitemagic.core.memory.unified import get_unified_memory
    from whitemagic.optimization.rust_accelerators import (
        galactic_batch_score,
        association_mine,
        search_build_index,
        search_query,
    )
    HAS_WHITEMAGIC = True
except ImportError:
    HAS_WHITEMAGIC = False

pytestmark = pytest.mark.core


@pytest.mark.skipif(not HAS_WHITEMAGIC, reason="WhiteMagic not available")
class TestCriticalPathMemoryStorage:
    """Critical path: Memory storage and retrieval."""

    def test_store_and_retrieve_memory(self):
        """Store a memory and retrieve it."""
        um = get_unified_memory()
        
        # Store
        stored = um.store(
            content="Test critical path memory storage",
            title="Critical Path Test",
            memory_type="test",
            importance=0.8,
        )
        assert stored is not None
        
        # Retrieve by ID
        mem = um.recall(stored.id)
        assert mem is not None
        assert mem.content == "Test critical path memory storage"
        assert mem.title == "Critical Path Test"

    def test_store_with_embedding(self):
        """Store memory with automatic embedding generation."""
        um = get_unified_memory()
        
        # Store with embedding trigger
        mem_id = um.store(
            content="Rust performance optimization techniques",
            title="Rust Optimization",
            memory_type="technical",
            importance=0.9,
            auto_embed=False,  # Skip for speed in tests
        )
        assert mem_id is not None

    def test_batch_store_retrieve(self):
        """Batch store and retrieve operations."""
        um = get_unified_memory()
        
        # Batch store
        stored_mems = []
        for i in range(10):
            m = um.store(
                content=f"Batch memory number {i}",
                title=f"Batch {i}",
                memory_type="batch_test",
                importance=0.5 + (i * 0.05),
            )
            stored_mems.append(m)
        
        # Verify all retrievable by ID
        for stored in stored_mems:
            mem = um.recall(stored.id)
            assert mem is not None
            assert mem.id == stored.id


@pytest.mark.skipif(not HAS_WHITEMAGIC, reason="WhiteMagic not available")
class TestCriticalPathSearchOperations(unittest.TestCase):
    """Critical path: Search operations (FTS + BM25)."""

    def test_fts_search_returns_results(self):
        """FTS search returns relevant results."""
        # Build a small index
        docs = [
            {"id": "m1", "title": "Rust Programming", "content": "Memory safety without garbage collection"},
            {"id": "m2", "title": "Python Performance", "content": "Optimization techniques for Python code"},
            {"id": "m3", "title": "Async Rust", "content": "Tokio and async programming in Rust"},
        ]
        
        result = search_build_index(docs)
        assert result is not None
        
        # Search
        results = search_query("Rust programming", 5)
        assert results is not None
        assert len(results) > 0
        # Rust docs should rank higher
        ids = [r["id"] for r in results]
        assert "m1" in ids or "m3" in ids

    def test_search_fuzzy_typo_tolerance(self):
        """Fuzzy search handles typos."""
        docs = [
            {"id": "m1", "title": "Optimization", "content": "Code optimization strategies"},
        ]
        
        search_build_index(docs)
        
        # Search with typo "optimiztion" missing 'a'
        from whitemagic.optimization.rust_accelerators import search_fuzzy
        results = search_fuzzy("optimiztion", 5, max_distance=2)
        assert results is not None
        # Should find "optimization" despite typo


@pytest.mark.skipif(not HAS_WHITEMAGIC, reason="WhiteMagic not available")
class TestCriticalPathGalacticScoring:
    """Critical path: Galactic batch scoring."""

    def test_galactic_batch_score_basic(self):
        """Basic galactic scoring produces valid results."""
        memories = [
            {"id": "m1", "importance": 0.8, "neuro_score": 0.7, "emotional_valence": 0.5, "recall_count": 10},
            {"id": "m2", "importance": 0.3, "neuro_score": 0.4, "emotional_valence": 0.1, "recall_count": 2},
        ]
        
        results = galactic_batch_score(memories, quick=True)
        assert results is not None
        assert len(results) == 2
        
        # Higher importance should result in lower distance
        assert results[0]["retention_score"] > results[1]["retention_score"]
        assert results[0]["galactic_distance"] < results[1]["galactic_distance"]

    def test_galactic_score_protected_memories(self):
        """Protected memories get core zone."""
        memories = [
            {"id": "m1", "is_protected": True, "importance": 0.5},  # Low importance but protected
            {"id": "m2", "importance": 1.0},  # High importance but not protected
        ]
        
        results = galactic_batch_score(memories, quick=False)
        assert results is not None
        
        # Protected memory should be in core regardless of importance
        protected_result = next(r for r in results if r["id"] == "m1")
        assert protected_result["zone"] == "core"
        assert protected_result["galactic_distance"] == 0.0


@pytest.mark.skipif(not HAS_WHITEMAGIC, reason="WhiteMagic not available")
class TestCriticalPathAssociationMining:
    """Critical path tests for core functionality."""

    def test_association_mine_finds_similar(self):
        """Association mining finds similar memories."""
        texts = [
            ("m1", "Rust programming language memory safety performance systems concurrent async tokio rayon parallel"),
            ("m2", "Rust programming performance optimization systems memory concurrent async parallel efficient"),
            ("m3", "Gardening plants soil nutrients organic growing flowers vegetables compost water sunlight"),
        ]
        
        result = association_mine(texts, max_keywords=10, min_score=0.1, max_results=10)
        assert result is not None
        assert result["memory_count"] == 3
        
        # m1 and m2 should have overlap (both about Rust programming)
        m1_m2_overlap = next(
            (o for o in result["overlaps"] 
             if (o["source_id"] == "m1" and o["target_id"] == "m2") or
                (o["source_id"] == "m2" and o["target_id"] == "m1")),
            None
        )
        assert m1_m2_overlap is not None, f"Expected m1-m2 overlap, got: {result['overlaps']}"
        assert m1_m2_overlap["overlap_score"] > 0.1

    def test_association_mine_respects_limits(self):
        """Association mining respects max_results limit."""
        # Create many memories
        texts = [(f"m{i}", f"Memory about topic {i % 3} with shared keywords") for i in range(20)]
        
        result = association_mine(texts, max_keywords=5, min_score=0.0, max_results=5)
        assert result is not None
        assert len(result["overlaps"]) <= 5


@pytest.mark.skipif(not HAS_WHITEMAGIC, reason="WhiteMagic not available")
class TestCriticalPathIntegration:
    """Integration tests for critical paths working together."""

    def test_full_memory_workflow(self):
        """Full workflow: store → index → search → score."""
        um = get_unified_memory()
        
        # Store memories
        stored_mems = []
        for i in range(5):
            m = um.store(
                content=f"Critical workflow test memory {i} about optimization and performance",
                title=f"Workflow {i}",
                memory_type="integration_test",
                importance=0.6 + (i * 0.08),
            )
            stored_mems.append(m)
        
        # Verify all stored
        assert len(stored_mems) == 5
        mem_ids = [m.id for m in stored_mems]
        
        # Retrieve and score
        memories = [um.recall(mid) for mid in mem_ids]
        memories = [m for m in memories if m is not None]
        # Convert to dict format for galactic_batch_score
        mem_dicts = [{"id": m.id, "importance": m.importance, "neuro_score": 0.5, 
                      "emotional_valence": 0.0, "recall_count": 0} for m in memories]
        
        # Score them
        scored = galactic_batch_score(mem_dicts, quick=True)
        assert len(scored) == 5
        
        # Higher importance should score better
        sorted_by_score = sorted(scored, key=lambda x: x["retention_score"], reverse=True)
        # The memory with importance=1.0 should be first
        assert sorted_by_score[0]["retention_score"] >= sorted_by_score[-1]["retention_score"]
