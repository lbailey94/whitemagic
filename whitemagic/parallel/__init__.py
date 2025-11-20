"""
WhiteMagic Parallel Processing Infrastructure

Provides high-performance parallel execution for file operations, memory management,
and general task scheduling. Designed for 40x+ speedup on batch operations.

Key Features:
- Parallel file reading (64 concurrent)
- Parallel memory operations (dependency-aware)
- I Ching-aligned threading (8, 16, 32, 64, 128, 256)
- Adaptive resource management
- Distributed caching
- Multi-stage pipelines

Usage:
    from whitemagic.parallel import ParallelFileReader, ParallelMemoryManager

    # Read 50 files in parallel
    reader = ParallelFileReader(max_workers=64)
    results = await reader.read_batch(file_paths)

    # Search multiple queries simultaneously
    manager = ParallelMemoryManager()
    results = await manager.parallel_search(["query1", "query2", "query3"])
"""

from whitemagic.parallel.adaptive import AdaptiveThreadingController
from whitemagic.parallel.cache import DistributedCache
from whitemagic.parallel.file_ops import ParallelFileReader, batch_read_files
from whitemagic.parallel.memory_ops import ParallelMemoryManager
from whitemagic.parallel.pipeline import ParallelPipeline, PipelineStage
from whitemagic.parallel.pools import ThreadingManager, ThreadingTier
from whitemagic.parallel.scheduler import ParallelScheduler, TaskPriority

__all__ = [
    # File Operations
    "ParallelFileReader",
    "batch_read_files",
    # Memory Operations
    "ParallelMemoryManager",
    # Scheduling
    "ParallelScheduler",
    "TaskPriority",
    # Threading
    "ThreadingManager",
    "ThreadingTier",
    # Adaptive Control
    "AdaptiveThreadingController",
    # Caching
    "DistributedCache",
    # Pipelines
    "ParallelPipeline",
    "PipelineStage",
]

__version__ = "2.6.5"
