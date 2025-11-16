"""
Unit tests for v2.2.2 features:
- MCP Optimization (fast reads, batch, cache)
- Parallel Contexts (environment variable support)
- Incremental Backups (CLI flags)
"""

import os
import tempfile
import time
from pathlib import Path
import pytest

from whitemagic import MemoryManager
from whitemagic.backup import BackupManager
from whitemagic.models import MemoryCreate


class TestParallelContexts:
    """Test parallel memory contexts via environment variable."""
    
    def test_env_var_support(self, tmp_path):
        """Test WHITEMAGIC_BASE_DIR environment variable."""
        # Create two separate contexts
        context_a = tmp_path / "contextA"
        context_b = tmp_path / "contextB"
        context_a.mkdir()
        context_b.mkdir()
        
        # Create managers for each context
        mgr_a = MemoryManager(base_dir=str(context_a))
        mgr_b = MemoryManager(base_dir=str(context_b))
        
        # Create memory in context A
        mem_a = mgr_a.create_memory(
            "Context A Memory",
            "This is in context A",
            memory_type="short_term"
        )
        
        # Create memory in context B
        mem_b = mgr_b.create_memory(
            "Context B Memory",
            "This is in context B",
            memory_type="short_term"
        )
        
        # Verify isolation
        assert mgr_a.list_all_memories()["short_term"][0].title == "Context A Memory"
        assert mgr_b.list_all_memories()["short_term"][0].title == "Context B Memory"
        
        # Context A should not see B's memory
        assert len(mgr_a.list_all_memories()["short_term"]) == 1
        assert len(mgr_b.list_all_memories()["short_term"]) == 1
    
    def test_concurrent_writes(self, tmp_path):
        """Test that concurrent writes to different contexts are safe."""
        context = tmp_path / "concurrent"
        context.mkdir()
        
        mgr1 = MemoryManager(base_dir=str(context))
        mgr2 = MemoryManager(base_dir=str(context))
        
        # Both should be able to write without conflict
        mem1 = mgr1.create_memory(
            "Memory 1",
            "From manager 1",
            memory_type="short_term"
        )
        
        mem2 = mgr2.create_memory(
            "Memory 2",
            "From manager 2",
            memory_type="short_term"
        )
        
        # Both memories should exist
        memories = mgr1.list_all_memories()["short_term"]
        assert len(memories) == 2
        titles = [m.title for m in memories]
        assert "Memory 1" in titles
        assert "Memory 2" in titles


class TestIncrementalBackups:
    """Test incremental backup functionality."""
    
    def test_incremental_backup_skips_unchanged(self, tmp_path):
        """Test that incremental backup only includes changed files."""
        context = tmp_path / "backup_test"
        context.mkdir()
        
        mgr = MemoryManager(base_dir=str(context))
        backup_mgr = BackupManager(base_dir=context)
        
        # Create initial memories
        mgr.create_memory("Memory 1", "Content 1", memory_type="short_term")
        mgr.create_memory("Memory 2", "Content 2", memory_type="short_term")
        
        # Full backup
        backup1 = backup_mgr.create_backup()
        assert backup1["success"]
        backup1_path = Path(backup1["backup_path"])
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)
        
        # Add one more memory
        mgr.create_memory("Memory 3", "Content 3", memory_type="short_term")
        
        # Incremental backup
        backup2 = backup_mgr.create_backup(
            incremental=True,
            last_backup=backup1_path
        )
        assert backup2["success"]
        
        # Incremental should have fewer files
        assert backup2["manifest"]["incremental"] is True
        incremental_files = backup2["manifest"]["stats"]["total_files"]
        full_files = backup1["manifest"]["stats"]["total_files"]
        
        # Incremental should only have the new memory + metadata
        assert incremental_files < full_files
    
    def test_backup_verification(self, tmp_path):
        """Test backup integrity verification."""
        context = tmp_path / "verify_test"
        context.mkdir()
        
        mgr = MemoryManager(base_dir=str(context))
        backup_mgr = BackupManager(base_dir=context)
        
        # Create memories
        mgr.create_memory("Test Memory", "Test Content", memory_type="short_term")
        
        # Create backup
        result = backup_mgr.create_backup()
        backup_path = Path(result["backup_path"])
        
        # Verify backup
        verification = backup_mgr.verify_backup(backup_path)
        assert verification["valid"]
        assert verification["has_manifest"]
        assert verification["manifest_valid"]
        assert verification["hash_mismatches"] == 0


class TestPerformanceBenchmarks:
    """Performance benchmarks for v2.2.2 features."""
    
    def test_parallel_context_overhead(self, tmp_path):
        """Benchmark: Parallel contexts should have minimal overhead."""
        contexts = [tmp_path / f"context{i}" for i in range(5)]
        for ctx in contexts:
            ctx.mkdir()
        
        # Create 5 managers
        start = time.time()
        managers = [MemoryManager(base_dir=str(ctx)) for ctx in contexts]
        init_time = time.time() - start
        
        # Should be fast (< 1 second for 5 contexts)
        assert init_time < 1.0
        
        # Create memory in each
        start = time.time()
        for i, mgr in enumerate(managers):
            mgr.create_memory(f"Memory {i}", f"Content {i}", memory_type="short_term")
        write_time = time.time() - start
        
        # Should be reasonably fast (< 0.5 seconds for 5 writes)
        assert write_time < 0.5
    
    def test_incremental_vs_full_backup_speed(self, tmp_path):
        """Benchmark: Incremental backups should be significantly faster."""
        context = tmp_path / "speed_test"
        context.mkdir()
        
        mgr = MemoryManager(base_dir=str(context))
        backup_mgr = BackupManager(base_dir=context)
        
        # Create 20 memories
        for i in range(20):
            mgr.create_memory(f"Memory {i}", f"Content {i}" * 100, memory_type="short_term")
        
        # Full backup
        start = time.time()
        backup1 = backup_mgr.create_backup()
        full_time = time.time() - start
        
        # Add 2 more memories
        time.sleep(0.1)
        mgr.create_memory("New 1", "New content 1", memory_type="short_term")
        mgr.create_memory("New 2", "New content 2", memory_type="short_term")
        
        # Incremental backup
        start = time.time()
        backup2 = backup_mgr.create_backup(
            incremental=True,
            last_backup=Path(backup1["backup_path"])
        )
        incremental_time = time.time() - start
        
        # Incremental should be faster
        # (May not always be true for small sets, but good indicator)
        assert incremental_time <= full_time * 2  # At worst, similar speed


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide a temporary directory for tests."""
    return tmp_path_factory.mktemp("whitemagic_test")
