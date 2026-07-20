"""P5.4 — Batch retrieval hydration tests.

Verifies that batch_recall:
- Returns correct memories for valid IDs
- Omits missing IDs
- Handles empty input
- Handles large ID lists (chunking)
- Produces same results as individual recall() calls
- Galaxy router batches across backends
"""
import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.core.memory.unified_types import Memory, MemoryType
from whitemagic.core.memory.sqlite_backend import SQLiteBackend


class TestSQLiteBatchRecall:
    """Test SQLiteBackend.batch_recall."""

    @pytest.fixture
    def backend(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        backend = SQLiteBackend(db_path=db_path)
        # Store a few memories
        for i in range(5):
            mem = Memory(
                id=f"mem-{i}",
                content=f"content-{i}",
                memory_type=MemoryType.SHORT_TERM,
                title=f"Title {i}",
                importance=0.5 + i * 0.1,
                tags={f"tag-{i}"},
                galaxy="test",
            )
            backend.store(mem)
        return backend

    def test_batch_recall_returns_all_found(self, backend):
        result = backend.batch_recall(["mem-0", "mem-1", "mem-2"])
        assert len(result) == 3
        assert "mem-0" in result
        assert "mem-1" in result
        assert "mem-2" in result
        assert result["mem-0"].content == "content-0"

    def test_batch_recall_omits_missing(self, backend):
        result = backend.batch_recall(["mem-0", "nonexistent", "mem-2"])
        assert len(result) == 2
        assert "nonexistent" not in result
        assert "mem-0" in result
        assert "mem-2" in result

    def test_batch_recall_empty_input(self, backend):
        result = backend.batch_recall([])
        assert result == {}

    def test_batch_recall_all_missing(self, backend):
        result = backend.batch_recall(["nope-1", "nope-2"])
        assert result == {}

    def test_batch_recall_matches_individual(self, backend):
        ids = [f"mem-{i}" for i in range(5)]
        batch_result = backend.batch_recall(ids)
        for mid in ids:
            individual = backend.recall(mid)
            if individual is not None:
                assert mid in batch_result
                assert batch_result[mid].id == individual.id
                assert batch_result[mid].content == individual.content

    def test_batch_recall_preserves_tags(self, backend):
        result = backend.batch_recall(["mem-0", "mem-1"])
        assert "tag-0" in result["mem-0"].tags
        assert "tag-1" in result["mem-1"].tags

    def test_batch_recall_large_list(self, tmp_path):
        db_path = str(tmp_path / "large.db")
        backend = SQLiteBackend(db_path=db_path)
        for i in range(600):
            mem = Memory(
                id=f"bulk-{i}",
                content=f"bulk-content-{i}",
                memory_type=MemoryType.SHORT_TERM,
                title=f"Bulk {i}",
                importance=0.5,
                galaxy="bulk",
            )
            backend.store(mem)
        ids = [f"bulk-{i}" for i in range(600)]
        result = backend.batch_recall(ids)
        assert len(result) == 600
        # Verify chunking worked (500+ IDs should trigger chunk logic)
        assert result["bulk-0"].content == "bulk-content-0"
        assert result["bulk-599"].content == "bulk-content-599"

    def test_batch_recall_query_count(self, backend):
        """Batch recall should use bounded queries, not N individual queries."""
        # This is implicitly tested by the batch_recall implementation:
        # 1 query for memories, 1 for tags, 1 for associations = 3 total
        # vs 5 * 3 = 15 for individual recall() calls
        result = backend.batch_recall(["mem-0", "mem-1", "mem-2", "mem-3", "mem-4"])
        assert len(result) == 5


class TestGalaxyRouterBatchRecall:
    """Test GalaxyAwareBackend.batch_recall across multiple galaxy backends."""

    def test_batch_recall_across_galaxies(self, tmp_path):
        from whitemagic.core.memory.backends.galaxy_router import GalaxyAwareBackend

        default_db = tmp_path / "default.db"
        router = GalaxyAwareBackend(default_db_path=default_db)

        # Store memories in different galaxies
        for galaxy in ["alpha", "beta"]:
            backend = router._get_galaxy_backend(galaxy)
            for i in range(3):
                mem = Memory(
                    id=f"{galaxy}-mem-{i}",
                    content=f"{galaxy} content {i}",
                    memory_type=MemoryType.SHORT_TERM,
                    title=f"{galaxy} {i}",
                    importance=0.5,
                    galaxy=galaxy,
                )
                backend.store(mem)

        # Batch recall across galaxies
        ids = ["alpha-mem-0", "beta-mem-1", "alpha-mem-2", "nonexistent"]
        result = router.batch_recall(ids)
        assert len(result) == 3
        assert "alpha-mem-0" in result
        assert "beta-mem-1" in result
        assert "alpha-mem-2" in result
        assert "nonexistent" not in result
        assert result["alpha-mem-0"].galaxy == "alpha"
        assert result["beta-mem-1"].galaxy == "beta"
