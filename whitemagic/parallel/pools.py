"""
Threading Pool Management - I Ching Aligned

Provides thread pool management with tiers aligned to I Ching hexagram counts.
Supports adaptive scaling and resource limits.

Philosophy:
- Tier 0: 8 threads (八卦 - 8 trigrams)
- Tier 1: 16 threads
- Tier 2: 32 threads
- Tier 3: 64 threads (六十四卦 - 64 hexagrams, sweet spot!)
- Tier 4: 128 threads
- Tier 5: 256 threads (maximum complexity)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, TypeVar

T = TypeVar("T")


class ThreadingTier(Enum):
    """I Ching-aligned threading tiers."""
    
    TIER_0 = 8      # 八卦 (8 trigrams) - Minimal
    TIER_1 = 16     # Basic parallelism
    TIER_2 = 32     # Medium parallelism
    TIER_3 = 64     # 六十四卦 (64 hexagrams) - Optimal!
    TIER_4 = 128    # High parallelism
    TIER_5 = 256    # Maximum parallelism
    
    @classmethod
    def from_complexity(cls, complexity: int) -> "ThreadingTier":
        """Select tier based on task complexity."""
        if complexity <= 10:
            return cls.TIER_0
        elif complexity <= 25:
            return cls.TIER_1
        elif complexity <= 50:
            return cls.TIER_2
        elif complexity <= 100:
            return cls.TIER_3
        elif complexity <= 200:
            return cls.TIER_4
        else:
            return cls.TIER_5


@dataclass
class PoolConfig:
    """Configuration for thread/process pools."""
    
    io_workers: int = 64        # I/O-bound tasks
    cpu_workers: int = 16       # CPU-bound tasks
    api_workers: int = 32       # API calls
    db_workers: int = 8         # Database operations
    
    max_queue_size: int = 1000  # Maximum queued tasks
    timeout: float = 300.0      # Task timeout (seconds)
    
    # Adaptive scaling
    enable_adaptive: bool = True
    scale_threshold: float = 0.8  # Scale up at 80% utilization


class ThreadingManager:
    """
    Manages thread and process pools for parallel execution.
    
    Provides specialized pools for different workload types and
    handles lifecycle management.
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        """Initialize threading manager with optional configuration."""
        self.config = config or PoolConfig()
        
        # Thread pools for different workloads
        self._io_pool: Optional[ThreadPoolExecutor] = None
        self._cpu_pool: Optional[ProcessPoolExecutor] = None
        self._api_pool: Optional[ThreadPoolExecutor] = None
        self._db_pool: Optional[ThreadPoolExecutor] = None
        
        # State tracking
        self._active = False
    
    def start(self) -> None:
        """Start all thread pools."""
        if self._active:
            return
        
        self._io_pool = ThreadPoolExecutor(
            max_workers=self.config.io_workers,
            thread_name_prefix="wm-io-"
        )
        
        self._cpu_pool = ProcessPoolExecutor(
            max_workers=self.config.cpu_workers
        )
        
        self._api_pool = ThreadPoolExecutor(
            max_workers=self.config.api_workers,
            thread_name_prefix="wm-api-"
        )
        
        self._db_pool = ThreadPoolExecutor(
            max_workers=self.config.db_workers,
            thread_name_prefix="wm-db-"
        )
        
        self._active = True
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown all thread pools."""
        if not self._active:
            return
        
        pools = [self._io_pool, self._cpu_pool, self._api_pool, self._db_pool]
        for pool in pools:
            if pool:
                pool.shutdown(wait=wait)
        
        self._io_pool = None
        self._cpu_pool = None
        self._api_pool = None
        self._db_pool = None
        self._active = False
    
    async def run_io_task(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run I/O-bound task in thread pool."""
        if not self._active:
            self.start()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._io_pool,
            lambda: func(*args, **kwargs)
        )
    
    async def run_cpu_task(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run CPU-bound task in process pool."""
        if not self._active:
            self.start()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._cpu_pool,
            lambda: func(*args, **kwargs)
        )
    
    async def run_api_task(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run API call in dedicated pool."""
        if not self._active:
            self.start()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._api_pool,
            lambda: func(*args, **kwargs)
        )
    
    async def run_db_task(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run database operation in dedicated pool."""
        if not self._active:
            self.start()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._db_pool,
            lambda: func(*args, **kwargs)
        )
    
    async def run_batch(
        self,
        tasks: List[tuple[Callable, tuple, dict]],
        pool_type: str = "io"
    ) -> List[Any]:
        """
        Run batch of tasks in parallel.
        
        Args:
            tasks: List of (func, args, kwargs) tuples
            pool_type: "io", "cpu", "api", or "db"
        
        Returns:
            List of results in same order as tasks
        """
        if pool_type == "io":
            runner = self.run_io_task
        elif pool_type == "cpu":
            runner = self.run_cpu_task
        elif pool_type == "api":
            runner = self.run_api_task
        elif pool_type == "db":
            runner = self.run_db_task
        else:
            raise ValueError(f"Invalid pool type: {pool_type}")
        
        # Create coroutines for all tasks
        coros = [
            runner(func, *args, **kwargs)
            for func, args, kwargs in tasks
        ]
        
        # Execute all in parallel
        return await asyncio.gather(*coros, return_exceptions=True)
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
    
    @property
    def is_active(self) -> bool:
        """Check if pools are active."""
        return self._active
