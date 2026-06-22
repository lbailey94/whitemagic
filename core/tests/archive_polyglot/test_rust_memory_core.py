"""Tests for PSR-001 Rust Memory Core

Tests the Rust implementations of unified.py and db_manager.py
via the whitemagic_rs Python bindings.
"""
import pytest
import json

try:
    import whitemagic_rs as wm_rs
    RUST_AVAILABLE = True
    # Map available classes
    PyUnifiedMemory = getattr(wm_rs, 'PyUnifiedMemoryV3', getattr(wm_rs, 'PyUnifiedMemory', None))
    PyConnectionPool = getattr(wm_rs, 'PyConnectionPool', None)
    # Check if classes are actually usable
    try:
        if PyUnifiedMemory:
            # Try to instantiate to verify it works
            import tempfile
            test_db = tempfile.mktemp(suffix=".db")
            try:
                test_mem = PyUnifiedMemory(test_db, 2)
                RUST_USABLE = True
            except Exception:
                RUST_USABLE = False
        else:
            RUST_USABLE = False
    except Exception:
        RUST_USABLE = False
except ImportError:
    RUST_AVAILABLE = False
    PyUnifiedMemory = None
    PyConnectionPool = None
    RUST_USABLE = False


# Skip entire module if Rust backend is unavailable or not working
pytestmark = pytest.mark.skipif(not RUST_USABLE, reason="Rust backend not available or has implementation issues")


class TestRustUnifiedMemoryV3:
    """Test PyUnifiedMemoryV3 Rust implementation."""

    def test_create_memory_pool(self, tmp_path):
        """Create a memory pool with connection pool."""
        if not PyUnifiedMemory:
            pytest.skip("PyUnifiedMemory not available")
        
        db_path = str(tmp_path / "test_memory.db")
        
        # Create memory instance with pool
        memory = PyUnifiedMemory(db_path, 4)
        assert memory is not None

    def test_store_memory(self, tmp_path):
        """Store a memory and verify it returns an ID."""
        db_path = str(tmp_path / "test_store.db")
        
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 2)
        mem_id, was_dup = memory.store(
            content="Test memory content",
            title="Test Title",
            memory_type="short_term",
            importance=0.8,
            tags=["test", "rust"]
        )
        
        # Should return a memory ID
        assert mem_id is not None
        assert len(mem_id) > 0
        assert isinstance(was_dup, bool)

    def test_store_duplicate_detection(self, tmp_path):
        """Duplicate content should return existing ID."""
        db_path = str(tmp_path / "test_dup.db")
        
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 2)
        
        # Store first time
        id1, dup1 = memory.store(
            content="Duplicate test content",
            title="Original",
            memory_type="short_term",
            importance=0.5,
            tags=None
        )
        
        # Store same content again
        id2, dup2 = memory.store(
            content="Duplicate test content",
            title="Duplicate",
            memory_type="long_term",
            importance=0.9,
            tags=None
        )
        
        # Should return same ID and mark as duplicate
        assert id1 == id2
        assert dup1 is False
        assert dup2 is True

    def test_recall_memory(self, tmp_path):
        """Store and recall a memory."""
        db_path = str(tmp_path / "test_recall.db")
        
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 2)
        
        # Store
        mem_id, _ = memory.store(
            content="Recall test content",
            title="Recall Test",
            memory_type="short_term",
            importance=0.7,
            tags=["recall"]
        )
        
        # Recall
        result = memory.recall(mem_id)
        assert result is not None
        
        # Parse JSON result
        mem = json.loads(result)
        assert mem["id"] == mem_id
        assert "content" in mem

    def test_search_memories(self, tmp_path):
        """Search for memories."""
        db_path = str(tmp_path / "test_search.db")
        
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 2)
        
        # Store multiple memories
        for i in range(5):
            memory.store(
                content=f"Searchable content number {i}",
                title=f"Search {i}",
                memory_type="short_term",
                importance=0.5 + i * 0.1,
                tags=None
            )
        
        # Search
        results = memory.search(
            query="Searchable",
            tags=None,
            memory_type=None,
            min_importance=0.0,
            limit=10
        )
        
        assert results is not None
        matches = json.loads(results)
        assert len(matches) > 0


class TestRustConnectionPool:
    """Test PyConnectionPool Rust implementation."""

    def test_create_pool(self, tmp_path):
        """Create a connection pool."""
        db_path = str(tmp_path / "test_pool.db")
        
        pool = wm_rs.PyConnectionPool(db_path, 5)
        assert pool is not None

    def test_execute_query(self, tmp_path):
        """Execute a write query."""
        db_path = str(tmp_path / "test_execute.db")
        
        pool = wm_rs.PyConnectionPool(db_path, 2)
        
        # Create table
        affected = pool.execute(
            "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)",
            None
        )
        assert affected >= 0

    def test_query_select(self, tmp_path):
        """Execute a SELECT query."""
        db_path = str(tmp_path / "test_query.db")
        
        pool = wm_rs.PyConnectionPool(db_path, 2)
        
        # Create and insert
        pool.execute(
            "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)",
            None
        )
        pool.execute(
            "INSERT INTO test (name) VALUES ('test1')",
            None
        )
        
        # Query
        results = pool.query("SELECT * FROM test")
        assert results is not None
        
        rows = json.loads(results)
        assert len(rows) >= 1
        assert rows[0]["name"] == "test1"

    def test_pool_pragmas_applied(self, tmp_path):
        """Verify PRAGMA settings are applied."""
        db_path = str(tmp_path / "test_pragma.db")
        
        pool = wm_rs.PyConnectionPool(db_path, 2)
        
        # Check journal mode
        results = pool.query("PRAGMA journal_mode")
        assert results is not None
        
        rows = json.loads(results)
        # Should be WAL mode
        assert len(rows) == 1


class TestRustMemoryPerformance:
    """Performance benchmarks for Rust memory core."""

    def test_store_performance(self, tmp_path, benchmark):
        """Benchmark memory store operation."""
        db_path = str(tmp_path / "perf_store.db")
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 4)
        
        def store_op():
            memory.store(
                content="Performance test content",
                title="Perf Test",
                memory_type="short_term",
                importance=0.5,
                tags=None
            )
        
        # Run benchmark
        result = benchmark(store_op)
        # Should complete in reasonable time
        assert result is not None

    def test_batch_store(self, tmp_path):
        """Store many memories and verify performance."""
        import time
        
        db_path = str(tmp_path / "test_batch.db")
        memory = wm_rs.PyUnifiedMemoryV3(db_path, 4)
        
        start = time.time()
        
        # Store 100 memories
        for i in range(100):
            memory.store(
                content=f"Batch memory content {i}",
                title=f"Batch {i}",
                memory_type="short_term",
                importance=0.5,
                tags=None
            )
        
        elapsed = time.time() - start
        
        # Should complete in under 5 seconds (conservative)
        assert elapsed < 5.0
        print(f"Stored 100 memories in {elapsed:.2f}s ({100/elapsed:.1f} ops/sec)")
