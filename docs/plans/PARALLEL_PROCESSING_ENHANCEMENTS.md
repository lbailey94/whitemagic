# Parallel Processing & Threading Enhancements

**Date**: November 16, 2025  
**Version**: Proposed for v2.2.7  
**Status**: Design Phase

---

## 🎯 Current State Analysis

### Existing Capabilities

**1. WorkflowPatterns Module** (`whitemagic/workflow_patterns.py`)
- ✅ Parallel-first philosophy
- ✅ I Ching-aligned threading tiers (8, 16, 32, 64, 128, 256)
- ✅ Task terrain assessment (Art of War)
- ✅ Max parallel calls: 10 (configurable)
- ✅ Dependency detection

**2. Async Infrastructure**
- ✅ FastAPI with async/await
- ✅ AsyncIO throughout API layer
- ✅ Async database operations (asyncpg, aiosqlite)
- ✅ Async CLI with Rich progress bars

**3. MCP Server**
- ✅ 16 tools available
- ✅ Batch operations: `batch_read_memories`
- ✅ Fast operations: `fast_read_memory`
- ❌ No parallel tool execution

---

## 🚀 Proposed Enhancements

### Phase 1: Enhanced Parallel Primitives

#### 1.1 Parallel File Operations
```python
# whitemagic/parallel/file_ops.py

import asyncio
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

class ParallelFileReader:
    """Parallel file reading with smart batching."""
    
    def __init__(self, max_workers: int = 64):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def read_multiple(
        self,
        paths: List[Path],
        encoding: str = 'utf-8'
    ) -> Dict[str, str]:
        """
        Read multiple files in parallel.
        
        Args:
            paths: List of file paths
            encoding: File encoding
            
        Returns:
            Dict mapping path to content
        """
        loop = asyncio.get_event_loop()
        
        async def read_one(path: Path) -> tuple:
            content = await loop.run_in_executor(
                self.executor,
                lambda: path.read_text(encoding=encoding)
            )
            return (str(path), content)
        
        results = await asyncio.gather(*[read_one(p) for p in paths])
        return dict(results)
    
    async def search_parallel(
        self,
        pattern: str,
        paths: List[Path],
        regex: bool = False
    ) -> Dict[str, List[str]]:
        """
        Search multiple files in parallel for pattern.
        
        Returns:
            Dict mapping path to list of matching lines
        """
        # Implementation with ripgrep-style parallel search
        pass
```

#### 1.2 Parallel Memory Operations
```python
# whitemagic/parallel/memory_ops.py

class ParallelMemoryManager:
    """Parallel memory operations with dependency resolution."""
    
    async def consolidate_parallel(
        self,
        memories: List[Memory],
        max_concurrent: int = 8
    ) -> ConsolidationResult:
        """
        Consolidate multiple memories in parallel.
        
        Uses dependency graph to determine which memories
        can be consolidated simultaneously.
        """
        # Build dependency graph
        graph = self._build_dependency_graph(memories)
        
        # Topological sort to find parallelizable batches
        batches = self._topological_batches(graph)
        
        results = []
        for batch in batches:
            # Process each batch in parallel
            batch_results = await asyncio.gather(*[
                self._consolidate_one(mem) for mem in batch
            ])
            results.extend(batch_results)
        
        return ConsolidationResult(results)
    
    async def search_parallel(
        self,
        queries: List[str],
        max_concurrent: int = 32
    ) -> Dict[str, List[Memory]]:
        """
        Run multiple search queries in parallel.
        
        Useful for comprehensive scans across multiple topics.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_one(query: str):
            async with semaphore:
                return (query, await self.search(query))
        
        results = await asyncio.gather(*[search_one(q) for q in queries])
        return dict(results)
```

#### 1.3 Smart Task Scheduling
```python
# whitemagic/parallel/scheduler.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Callable, Any

class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

@dataclass
class Task:
    """Representation of a parallelizable task."""
    name: str
    func: Callable
    priority: TaskPriority
    dependencies: List[str]
    estimated_time: float  # seconds
    estimated_tokens: int

class ParallelScheduler:
    """
    Intelligent task scheduler with resource awareness.
    
    Features:
    - Priority-based scheduling
    - Dependency resolution
    - Token budget awareness
    - Deadline support
    """
    
    def __init__(
        self,
        max_concurrent: int = 64,
        token_budget: int = 200000
    ):
        self.max_concurrent = max_concurrent
        self.token_budget = token_budget
        self.tasks: List[Task] = []
        self.completed: List[str] = []
    
    def add_task(self, task: Task):
        """Add task to scheduler."""
        self.tasks.append(task)
    
    async def execute_all(self) -> Dict[str, Any]:
        """
        Execute all tasks with optimal parallelization.
        
        Returns:
            Results dictionary
        """
        # Sort by priority and dependencies
        execution_plan = self._create_execution_plan()
        
        results = {}
        for batch in execution_plan:
            # Check token budget before batch
            if self._exceeds_budget(batch):
                break
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(*[
                self._execute_task(task) for task in batch
            ])
            
            results.update(dict(zip([t.name for t in batch], batch_results)))
        
        return results
    
    def _create_execution_plan(self) -> List[List[Task]]:
        """
        Create optimal execution plan using:
        1. Dependency graph analysis
        2. Critical path method
        3. Token budget constraints
        
        Returns:
            List of batches (each batch can run in parallel)
        """
        # Build dependency graph
        graph = self._build_graph()
        
        # Topological sort with priority
        sorted_tasks = self._priority_topological_sort(graph)
        
        # Group into parallelizable batches
        batches = self._create_batches(sorted_tasks)
        
        return batches
```

---

### Phase 2: MCP Tool Enhancements

#### 2.1 New Parallel Tools

**Tool: `parallel_search`**
```typescript
{
  name: 'parallel_search',
  description: '⚡ Search multiple queries simultaneously',
  inputSchema: {
    type: 'object',
    properties: {
      queries: {
        type: 'array',
        items: { type: 'string' },
        description: 'List of search queries to run in parallel'
      },
      max_concurrent: {
        type: 'number',
        default: 32,
        description: 'Maximum concurrent searches'
      }
    },
    required: ['queries']
  }
}
```

**Tool: `batch_create_memories`**
```typescript
{
  name: 'batch_create_memories',
  description: '⚡ Create multiple memories in one operation',
  inputSchema: {
    type: 'object',
    properties: {
      memories: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            content: { type: 'string' },
            type: { type: 'string', enum: ['short_term', 'long_term'] },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['title', 'content']
        },
        description: 'Array of memories to create'
      }
    },
    required: ['memories']
  }
}
```

**Tool: `parallel_update_memories`**
```typescript
{
  name: 'parallel_update_memories',
  description: '⚡ Update multiple memories simultaneously',
  inputSchema: {
    type: 'object',
    properties: {
      updates: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            filename: { type: 'string' },
            title: { type: 'string' },
            content: { type: 'string' },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['filename']
        }
      }
    },
    required: ['updates']
  }
}
```

**Tool: `smart_consolidate`**
```typescript
{
  name: 'smart_consolidate',
  description: 'Intelligently consolidate related memories in parallel',
  inputSchema: {
    type: 'object',
    properties: {
      strategy: {
        type: 'string',
        enum: ['by_topic', 'by_date', 'by_project', 'auto'],
        description: 'Consolidation strategy'
      },
      min_similarity: {
        type: 'number',
        default: 0.7,
        description: 'Minimum similarity for grouping'
      },
      dry_run: {
        type: 'boolean',
        default: true
      }
    }
  }
}
```

#### 2.2 Session Management Tools

**Tool: `create_session`**
```typescript
{
  name: 'create_session',
  description: 'Create a new work session with automatic memory management',
  inputSchema: {
    type: 'object',
    properties: {
      name: { type: 'string', description: 'Session name' },
      goals: { type: 'array', items: { type: 'string' } },
      context_tier: { type: 'number', enum: [0, 1, 2] },
      auto_checkpoint: { type: 'boolean', default: true }
    },
    required: ['name']
  }
}
```

**Tool: `checkpoint_session`**
```typescript
{
  name: 'checkpoint_session',
  description: 'Save session state for resume',
  inputSchema: {
    type: 'object',
    properties: {
      session_id: { type: 'string' },
      include_metrics: { type: 'boolean', default: true }
    },
    required: ['session_id']
  }
}
```

**Tool: `resume_session`**
```typescript
{
  name: 'resume_session',
  description: 'Resume a previous session with full context',
  inputSchema: {
    type: 'object',
    properties: {
      session_id: { type: 'string' },
      load_tier: { type: 'number', enum: [0, 1, 2], default: 1 }
    },
    required: ['session_id']
  }
}
```

#### 2.3 Analysis & Insights Tools

**Tool: `analyze_memory_graph`**
```typescript
{
  name: 'analyze_memory_graph',
  description: 'Analyze connections between memories',
  inputSchema: {
    type: 'object',
    properties: {
      depth: { type: 'number', default: 2, description: 'Graph traversal depth' },
      min_strength: { type: 'number', default: 0.5 },
      visualize: { type: 'boolean', default: false }
    }
  }
}
```

**Tool: `find_patterns`**
```typescript
{
  name: 'find_patterns',
  description: 'Discover recurring patterns across memories',
  inputSchema: {
    type: 'object',
    properties: {
      time_range: { type: 'string', description: 'e.g., "last_7_days"' },
      pattern_types: { 
        type: 'array', 
        items: { 
          type: 'string',
          enum: ['code', 'workflow', 'decision', 'problem']
        }
      }
    }
  }
}
```

**Tool: `get_recommendations`**
```typescript
{
  name: 'get_recommendations',
  description: 'Get AI-powered recommendations based on memory analysis',
  inputSchema: {
    type: 'object',
    properties: {
      context: { type: 'string', description: 'Current task context' },
      categories: {
        type: 'array',
        items: {
          type: 'string',
          enum: ['consolidation', 'next_steps', 'related_memories', 'optimizations']
        }
      }
    },
    required: ['context']
  }
}
```

---

### Phase 3: Threading Infrastructure

#### 3.1 Configurable Threading Pools
```python
# whitemagic/parallel/pools.py

class ThreadingManager:
    """Manage multiple thread pools for different workload types."""
    
    def __init__(self):
        # I Ching-aligned pools
        self.pools = {
            'io_intensive': ThreadPoolExecutor(max_workers=64),  # File I/O
            'cpu_intensive': ProcessPoolExecutor(max_workers=16),  # Embeddings
            'api_calls': ThreadPoolExecutor(max_workers=32),  # HTTP requests
            'db_operations': ThreadPoolExecutor(max_workers=8),  # Database
        }
    
    def get_pool(self, workload_type: str) -> Executor:
        """Get appropriate pool for workload type."""
        return self.pools.get(workload_type, self.pools['io_intensive'])
    
    async def execute_parallel(
        self,
        tasks: List[Callable],
        workload_type: str = 'io_intensive'
    ) -> List[Any]:
        """Execute tasks in parallel using appropriate pool."""
        pool = self.get_pool(workload_type)
        loop = asyncio.get_event_loop()
        
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, task) for task in tasks
        ])
        
        return results
```

#### 3.2 Adaptive Threading
```python
# whitemagic/parallel/adaptive.py

class AdaptiveThreadingController:
    """
    Dynamically adjust thread count based on:
    - System load
    - Token budget
    - Memory pressure
    - Task complexity
    """
    
    def __init__(self):
        self.base_threads = 64  # I Ching hexagram count
        self.current_threads = self.base_threads
        self.metrics_history = []
    
    def adjust_for_load(self, cpu_percent: float, memory_percent: float):
        """Adjust thread count based on system resources."""
        if cpu_percent > 80 or memory_percent > 80:
            # Reduce threads
            self.current_threads = max(8, self.current_threads // 2)
        elif cpu_percent < 40 and memory_percent < 40:
            # Increase threads
            self.current_threads = min(256, self.current_threads * 2)
    
    def adjust_for_tokens(self, tokens_remaining: int):
        """Adjust parallelism based on token budget."""
        if tokens_remaining < 20000:  # 10% remaining
            # Reduce parallelism to save tokens
            self.current_threads = min(16, self.current_threads)
        elif tokens_remaining > 100000:  # 50%+ remaining
            # Can afford more parallelism
            self.current_threads = min(128, self.current_threads * 2)
```

---

### Phase 4: Performance Optimizations

#### 4.1 Caching Layer
```python
# whitemagic/parallel/cache.py

from functools import lru_cache
import hashlib
import pickle

class DistributedCache:
    """Redis-backed distributed cache for parallel operations."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.local_cache = {}
        self.max_local_size = 1000
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        ttl: int = 3600
    ) -> Any:
        """
        Get from cache or compute (with parallel support).
        
        Multiple parallel requests for same key will wait
        for first computation instead of duplicate work.
        """
        # Check local cache first
        if key in self.local_cache:
            return self.local_cache[key]
        
        # Check Redis
        cached = await self.redis.get(key)
        if cached:
            result = pickle.loads(cached)
            self.local_cache[key] = result
            return result
        
        # Compute and cache
        result = await compute_func()
        await self.redis.setex(key, ttl, pickle.dumps(result))
        self.local_cache[key] = result
        
        return result
```

#### 4.2 Batch Processing Pipeline
```python
# whitemagic/parallel/pipeline.py

class ParallelPipeline:
    """
    Build and execute multi-stage parallel pipelines.
    
    Example:
        pipeline = ParallelPipeline()
        pipeline.add_stage('read', read_files, parallel=True)
        pipeline.add_stage('process', process_content, parallel=True)
        pipeline.add_stage('save', save_results, parallel=False)
        results = await pipeline.execute(inputs)
    """
    
    def __init__(self):
        self.stages = []
    
    def add_stage(
        self,
        name: str,
        func: Callable,
        parallel: bool = True,
        max_workers: int = 64
    ):
        """Add a processing stage."""
        self.stages.append({
            'name': name,
            'func': func,
            'parallel': parallel,
            'max_workers': max_workers
        })
    
    async def execute(self, inputs: List[Any]) -> List[Any]:
        """Execute pipeline on inputs."""
        data = inputs
        
        for stage in self.stages:
            if stage['parallel']:
                # Execute stage in parallel
                data = await asyncio.gather(*[
                    stage['func'](item) for item in data
                ])
            else:
                # Sequential execution
                data = [stage['func'](item) for item in data]
        
        return data
```

---

## 📊 Expected Performance Improvements

### Current vs Enhanced

**File Reading**:
- Current: Sequential, ~100ms per file
- Enhanced: Parallel 64 files in ~150ms total
- **Improvement**: 40x faster for large batches

**Memory Search**:
- Current: Sequential search, ~500ms
- Enhanced: Parallel multi-query, ~600ms for 10 queries
- **Improvement**: 8x faster for multiple queries

**Consolidation**:
- Current: Sequential, ~5 seconds for 10 memories
- Enhanced: Parallel with dependency resolution, ~1 second
- **Improvement**: 5x faster

**Overall Session Speed**:
- Current: ~100K tokens per complex session
- Enhanced: ~60K tokens (parallel loading reduces sequential overhead)
- **Improvement**: 40% reduction in token usage

---

## 🎯 Implementation Roadmap

### v2.2.7 (This Release)
- ✅ Phase 1: Enhanced parallel primitives
- ✅ Phase 2: 8 new MCP tools
- ✅ Phase 3: Threading infrastructure
- ⏳ Phase 4: Basic caching (Redis required)

### v2.2.8 (Future)
- ⏳ Advanced caching strategies
- ⏳ Distributed task execution
- ⏳ GPU acceleration for embeddings

### v2.3.0 (Future)
- ⏳ Full distributed system
- ⏳ Multi-node coordination
- ⏳ Advanced scheduling algorithms

---

## 🛠️ Configuration

### User-Facing Settings
```python
# ~/.whitemagic/config.yaml

parallel:
  enabled: true
  max_workers: 64  # I Ching hexagram count (sweet spot)
  adaptive: true  # Adjust based on system resources
  
  # Per-workload settings
  io_workers: 64
  cpu_workers: 16
  api_workers: 32
  db_workers: 8
  
  # Caching
  cache_enabled: true
  cache_ttl: 3600  # seconds
  
  # Session management
  auto_checkpoint: true
  checkpoint_interval: 7200  # 2 hours
```

---

## 🔬 Testing Strategy

### Unit Tests
- Test each parallel primitive in isolation
- Verify thread safety
- Check resource cleanup

### Integration Tests
- Test end-to-end parallel workflows
- Verify dependency resolution
- Check token budget enforcement

### Performance Tests
- Benchmark parallel vs sequential
- Measure token savings
- Profile CPU/memory usage

### Stress Tests
- 1000+ parallel operations
- Resource exhaustion scenarios
- Race condition detection

---

## 📝 Documentation Requirements

1. **User Guide**: "Working with Parallel Operations"
2. **API Reference**: All new parallel APIs
3. **MCP Tool Reference**: New parallel tools
4. **Performance Guide**: Tuning parallel settings
5. **Troubleshooting**: Common parallel issues

---

**Status**: Ready for implementation in v2.2.7  
**Dependencies**: None (uses existing infrastructure)  
**Risk**: Low (additive changes, backwards compatible)
