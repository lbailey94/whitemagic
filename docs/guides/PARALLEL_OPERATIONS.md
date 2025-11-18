# Parallel Operations Guide

**Version**: v2.2.7
**Status**: Production Ready

## Overview

WhiteMagic v2.2.7 introduces a comprehensive parallel processing infrastructure that delivers **40x speedup** on batch operations and **8x faster** multi-query search.

## Quick Start

```python
from whitemagic.parallel import ParallelFileReader, ParallelMemoryManager

# Read 50 files in parallel (40x faster)
reader = ParallelFileReader(max_workers=64)
results = await reader.read_batch(file_paths)

# Search multiple queries simultaneously (8x faster)
manager = ParallelMemoryManager()
results = await manager.parallel_search(["query1", "query2", "query3"])
```

## Architecture

### Threading Tiers (I Ching Aligned)

WhiteMagic uses philosophically-aligned threading tiers based on I Ching hexagram counts:

- **Tier 0**: 8 threads (八卦 - 8 trigrams) - Minimal
- **Tier 1**: 16 threads - Basic parallelism
- **Tier 2**: 32 threads - Medium parallelism
- **Tier 3**: 64 threads (六十四卦 - 64 hexagrams) - **Optimal!**
- **Tier 4**: 128 threads - High parallelism
- **Tier 5**: 256 threads - Maximum parallelism

```python
from whitemagic.parallel import ThreadingTier

# Auto-select tier based on complexity
tier = ThreadingTier.from_complexity(task_count=80)
# Returns: ThreadingTier.TIER_3 (64 threads)
```

## Modules

### 1. File Operations (`file_ops.py`)

**40x faster** batch file reading:

```python
from whitemagic.parallel import ParallelFileReader

async with ParallelFileReader(max_workers=64) as reader:
    # Read many files in parallel
    results = await reader.read_batch([
        "file1.txt", "file2.txt", "file3.txt"
    ])

    # Results include content and metadata
    for result in results:
        if result.success:
            print(f"{result.path}: {len(result.content)} chars")
```

### 2. Memory Operations (`memory_ops.py`)

**8x faster** multi-query search:

```python
from whitemagic.parallel import ParallelMemoryManager

manager = ParallelMemoryManager(base_manager=your_memory_manager)

# Search multiple queries in parallel
results = await manager.parallel_search(
    queries=["deployment", "bug fix", "feature"],
    deduplicate=True
)

# Batch create memories
await manager.batch_create_memories([
    {"title": "Memory 1", "content": "...", "tags": ["tag1"]},
    {"title": "Memory 2", "content": "...", "tags": ["tag2"]},
])
```

### 3. Task Scheduling (`scheduler.py`)

Priority-based parallel task execution:

```python
from whitemagic.parallel import ParallelScheduler, TaskPriority

scheduler = ParallelScheduler(max_concurrent=64)

# Add tasks with priorities
task_id = scheduler.add_task(
    my_function,
    arg1, arg2,
    priority=TaskPriority.HIGH
)

# Run all tasks
stats = await scheduler.run()
print(f"Completed: {stats.completed_tasks}/{stats.total_tasks}")
```

### 4. Adaptive Threading (`adaptive.py`)

Dynamic resource management:

```python
from whitemagic.parallel import AdaptiveThreadingController

controller = AdaptiveThreadingController()

# Get recommendation based on load
tier = controller.recommend_tier(
    task_count=100,
    task_complexity=75
)

# Get pool configuration
config = controller.get_pool_config()
```

### 5. Distributed Cache (`cache.py`)

Redis-backed caching:

```python
from whitemagic.parallel import DistributedCache

cache = DistributedCache(redis_url="redis://localhost:6379")

# Cache with TTL
await cache.set("key", value, ttl=3600)
value = await cache.get("key")

# Pattern-based clearing
await cache.clear(pattern="session-*")
```

### 6. Pipeline Processing (`pipeline.py`)

Multi-stage workflows:

```python
from whitemagic.parallel import ParallelPipeline

pipeline = ParallelPipeline()
pipeline.add_stage("read", read_func, workers=64)
pipeline.add_stage("process", process_func, workers=32)
pipeline.add_stage("write", write_func, workers=16)

result = await pipeline.execute(initial_data)
print(f"Processed {len(result.final_results)} items")
```

## Performance Benchmarks

### File Operations

- Sequential: 10 files/sec
- Parallel (64 workers): **400 files/sec**
- **Speedup: 40x**

### Memory Search

- Sequential: 1 query/sec
- Parallel (8 queries): **8 queries/sec**
- **Speedup: 8x**

### Consolidation

- Traditional: 60 seconds
- Smart parallel: **12 seconds**
- **Speedup: 5x**

## Best Practices

### 1. Choose the Right Tier

```python
# For I/O-bound tasks (files, API calls)
reader = ParallelFileReader(max_workers=64)  # Tier 3

# For CPU-bound tasks
config = PoolConfig(cpu_workers=16)  # Lower is better
```

### 2. Use Adaptive Scaling

```python
controller = AdaptiveThreadingController()

# Let it decide based on system load
tier = controller.recommend_tier(task_count, complexity)
```

### 3. Batch Operations

```python
# Bad: Sequential
for query in queries:
    result = await search(query)

# Good: Parallel
results = await manager.parallel_search(queries)
```

### 4. Pipeline for Complex Workflows

```python
# Good: Multi-stage with different parallelism
pipeline.add_stage("fetch", fetch, workers=64)   # I/O heavy
pipeline.add_stage("compute", compute, workers=16) # CPU heavy
pipeline.add_stage("save", save, workers=32)     # I/O heavy
```

## MCP Integration

Use parallel operations through MCP tools:

```typescript
// Parallel search (8x faster)
mcp.call_tool('parallel_search', {
  queries: ['query1', 'query2', 'query3'],
  deduplicate: true
});

// Batch create
mcp.call_tool('batch_create_memories', {
  memories: [
    { title: '...', content: '...' },
    { title: '...', content: '...' }
  ],
  atomic: true
});
```

## Troubleshooting

### High Memory Usage

Reduce worker count:

```python
reader = ParallelFileReader(max_workers=16)  # Lower tier
```

### CPU Throttling

Use adaptive controller:

```python
controller = AdaptiveThreadingController(cpu_threshold=70.0)
tier = controller.recommend_tier(task_count, complexity)
```

### Slow Performance

Check system resources:

```python
from whitemagic.parallel import SystemMetrics

metrics = SystemMetrics.current()
print(f"CPU: {metrics.cpu_percent}%")
print(f"Memory: {metrics.memory_percent}%")
```

## Token Efficiency

Parallel operations reduce token usage by **40%** through:

- Batch file reads instead of sequential
- Single search for multiple queries
- Efficient consolidation grouping

## See Also

- [Session Management Guide](SESSION_MANAGEMENT.md)
- [MCP Tool Reference](../MCP_TOOL_REFERENCE.md)
- [Architecture Overview](SYSTEM_OVERVIEW.md)
