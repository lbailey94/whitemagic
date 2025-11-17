"""
Basic tests for parallel infrastructure.

Tests core functionality of all parallel modules.
"""

import pytest
import asyncio
from pathlib import Path

from whitemagic.parallel import (
    ParallelFileReader,
    ParallelScheduler,
    TaskPriority,
    ThreadingManager,
    ThreadingTier,
    AdaptiveThreadingController,
    DistributedCache,
    ParallelPipeline,
)


class TestThreadingManager:
    """Test threading manager."""
    
    def test_tier_from_complexity(self):
        """Test threading tier selection."""
        assert ThreadingTier.from_complexity(5) == ThreadingTier.TIER_0
        assert ThreadingTier.from_complexity(20) == ThreadingTier.TIER_1
        assert ThreadingTier.from_complexity(40) == ThreadingTier.TIER_2
        assert ThreadingTier.from_complexity(80) == ThreadingTier.TIER_3
        assert ThreadingTier.from_complexity(150) == ThreadingTier.TIER_4
        assert ThreadingTier.from_complexity(300) == ThreadingTier.TIER_5
    
    @pytest.mark.asyncio
    async def test_threading_manager_basic(self):
        """Test basic threading manager operations."""
        manager = ThreadingManager()
        
        def simple_task(x):
            return x * 2
        
        result = await manager.run_io_task(simple_task, 5)
        assert result == 10
        
        manager.shutdown()


class TestParallelFileReader:
    """Test parallel file operations."""
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading non-existent file."""
        reader = ParallelFileReader(max_workers=4)
        
        results = await reader.read_batch(["/nonexistent/file.txt"])
        
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error is not None
        
        reader.close()
    
    @pytest.mark.asyncio
    async def test_read_empty_list(self):
        """Test reading empty file list."""
        reader = ParallelFileReader()
        results = await reader.read_batch([])
        assert results == []
        reader.close()


class TestParallelScheduler:
    """Test parallel scheduler."""
    
    @pytest.mark.asyncio
    async def test_basic_scheduling(self):
        """Test basic task scheduling."""
        scheduler = ParallelScheduler(max_concurrent=4)
        
        def task1():
            return "result1"
        
        def task2():
            return "result2"
        
        scheduler.add_task(task1, priority=TaskPriority.HIGH)
        scheduler.add_task(task2, priority=TaskPriority.NORMAL)
        
        stats = await scheduler.run()
        
        assert stats.total_tasks == 2
        assert stats.completed_tasks == 2
        assert stats.failed_tasks == 0
    
    @pytest.mark.asyncio
    async def test_task_dependencies(self):
        """Test task dependencies."""
        scheduler = ParallelScheduler(max_concurrent=4)
        
        results = []
        
        def task1():
            results.append(1)
            return "task1"
        
        def task2():
            results.append(2)
            return "task2"
        
        task1_id = scheduler.add_task(task1)
        scheduler.add_task(task2, dependencies=[task1_id])
        
        await scheduler.run()
        
        # Task 1 should run before task 2
        assert results == [1, 2]


class TestAdaptiveController:
    """Test adaptive threading controller."""
    
    def test_recommend_tier(self):
        """Test tier recommendation."""
        controller = AdaptiveThreadingController()
        
        # Low task count
        tier = controller.recommend_tier(task_count=5, task_complexity=50)
        assert tier == ThreadingTier.TIER_0
        
        # High task count
        tier = controller.recommend_tier(task_count=150, task_complexity=50)
        assert tier == ThreadingTier.TIER_4


class TestDistributedCache:
    """Test distributed cache."""
    
    @pytest.mark.asyncio
    async def test_cache_basic(self):
        """Test basic cache operations."""
        cache = DistributedCache(redis_url=None)  # In-memory
        
        # Set and get
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
        
        # Delete
        await cache.delete("key1")
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing."""
        cache = DistributedCache(redis_url=None)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        count = await cache.clear()
        assert count == 2
        assert cache.size == 0


class TestParallelPipeline:
    """Test parallel pipeline."""
    
    @pytest.mark.asyncio
    async def test_basic_pipeline(self):
        """Test basic pipeline execution."""
        pipeline = ParallelPipeline()
        
        # Add stages
        pipeline.add_stage("double", lambda x: x * 2, workers=2)
        pipeline.add_stage("add_one", lambda x: x + 1, workers=2)
        
        # Execute
        result = await pipeline.execute([1, 2, 3])
        
        assert result.success
        assert result.final_results == [3, 5, 7]  # (1*2)+1, (2*2)+1, (3*2)+1
    
    @pytest.mark.asyncio
    async def test_pipeline_stats(self):
        """Test pipeline statistics."""
        pipeline = ParallelPipeline()
        pipeline.add_stage("identity", lambda x: x, workers=1)
        
        result = await pipeline.execute([1, 2, 3])
        
        stats = pipeline.get_stats()
        assert stats["total_stages"] == 1
        assert len(stats["stages"]) == 1
        assert stats["stages"][0]["input_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
