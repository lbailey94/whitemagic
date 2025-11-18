"""Advanced parallel operations tests."""

import pytest

from whitemagic.parallel import (
    ParallelMemoryManager,
    ParallelPipeline,
    ParallelScheduler,
    TaskPriority,
)


class TestParallelScheduler:
    """Test advanced scheduler features."""

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test tasks execute in priority order."""
        scheduler = ParallelScheduler(max_concurrent=1)
        results = []

        def task(name):
            results.append(name)
            return name

        scheduler.add_task(task, "low", priority=TaskPriority.LOW)
        scheduler.add_task(task, "high", priority=TaskPriority.HIGH)
        scheduler.add_task(task, "normal", priority=TaskPriority.NORMAL)

        await scheduler.run()

        # High priority should run first
        assert results[0] == "high"


class TestParallelMemoryManager:
    """Test parallel memory operations."""

    @pytest.mark.asyncio
    async def test_parallel_search_dedup(self):
        """Test parallel search with deduplication."""
        manager = ParallelMemoryManager()

        results = await manager.parallel_search(queries=["test", "example"], deduplicate=True)

        assert len(results) == 2
        assert all(r.success for r in results)


class TestParallelPipeline:
    """Test pipeline processing."""

    @pytest.mark.asyncio
    async def test_multi_stage(self):
        """Test multi-stage pipeline."""
        pipeline = ParallelPipeline()

        pipeline.add_stage("double", lambda x: x * 2, workers=2)
        pipeline.add_stage("add", lambda x: x + 10, workers=2)

        result = await pipeline.execute([1, 2, 3])

        assert result.success
        assert result.final_results == [12, 14, 16]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
