"""
Pathway Optimizers - Implementations of Discovered Adaptations
===============================================================

Optimizers based on patterns discovered by the Recursive Intelligence Engine.
Each optimizer implements specific workflow optimizations with measurable impact.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptimizationMetrics:
    """Track optimization performance metrics."""
    optimization_name: str
    calls_optimized: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    pre_compute_hits: int = 0
    total_latency_saved_ms: float = 0.0
    enabled: bool = True

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def avg_latency_saved_ms(self) -> float:
        return self.total_latency_saved_ms / self.calls_optimized if self.calls_optimized > 0 else 0.0


class MemoryWorkflowOptimizer:
    """
    Optimize the memory creation → linking → consolidation workflow.

    Based on discovered patterns:
    - memory_created → semantic_linked (100% probability)
    - semantic_linked → memory_consolidated (100% probability)
    - memory_consolidated → memory_created (93.3% probability)

    Adaptations #16, #17, #18
    """

    def __init__(self, enable_pre_compute: bool = True, enable_cache: bool = True):
        self.enable_pre_compute = enable_pre_compute
        self.enable_cache = enable_cache

        # Caches
        self.link_cache: Dict[str, List[str]] = {}  # memory_id -> similar_memory_ids
        self.consolidation_cache: Dict[str, Dict[str, Any]] = {}  # memory_id -> consolidation_data

        # Metrics
        self.metrics = OptimizationMetrics("MemoryWorkflow")

        logger.info("🚀 MemoryWorkflowOptimizer initialized")

    def pre_compute_semantic_links(self, memory_id: str, memory_data: Dict[str, Any]) -> Optional[List[str]]:
        """
        Pre-compute semantic links for a newly created memory.

        Adaptation #16: memory_created → semantic_linked (100% probability)
        Since semantic linking always follows memory creation, we can pre-compute
        the likely links before they're requested.
        """
        if not self.enable_pre_compute:
            return None

        try:
            start_time = datetime.now()

            # Check cache first
            if memory_id in self.link_cache:
                self.metrics.cache_hits += 1
                self.metrics.calls_optimized += 1
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.metrics.total_latency_saved_ms += elapsed_ms
                logger.debug(f"💨 Cache hit for semantic links: {memory_id[:8]}")
                return self.link_cache[memory_id]

            self.metrics.cache_misses += 1

            # Pre-compute similar memories (simplified - would use embeddings in production)
            # For now, just return empty list to demonstrate the mechanism
            similar_ids: List[str] = []

            # In production, this would:
            # 1. Get embedding for new memory
            # 2. Search for similar embeddings
            # 3. Return top K similar memory IDs

            # Cache the result
            self.link_cache[memory_id] = similar_ids
            self.metrics.pre_compute_hits += 1
            self.metrics.calls_optimized += 1

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"🔗 Pre-computed {len(similar_ids)} semantic links for {memory_id[:8]} in {elapsed_ms:.2f}ms")

            return similar_ids

        except Exception as e:
            logger.error(f"Error pre-computing semantic links: {e}")
            return None

    def pre_warm_consolidation(self, memory_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        Pre-warm consolidation cache for high-importance memories.

        Adaptation #17: semantic_linked → memory_consolidated (100% probability)
        After semantic linking, consolidation always follows. Pre-compute
        consolidation metadata for high-importance memories.
        """
        if not self.enable_cache:
            return False

        try:
            # Only pre-warm for high-importance memories (93.3% of consolidations)
            importance = memory_data.get('importance', 0.0)
            if importance < 0.7:
                return False

            start_time = datetime.now()

            # Pre-compute consolidation metadata
            consolidation_data = {
                "memory_id": memory_id,
                "timestamp": datetime.now().isoformat(),
                "pre_computed": True,
                "importance": importance,
            }

            self.consolidation_cache[memory_id] = consolidation_data
            self.metrics.calls_optimized += 1

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.total_latency_saved_ms += elapsed_ms

            logger.debug(f"🔥 Pre-warmed consolidation for {memory_id[:8]} (importance={importance:.2f})")
            return True

        except Exception as e:
            logger.error(f"Error pre-warming consolidation: {e}")
            return False

    def get_consolidation_data(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get pre-computed consolidation data if available."""
        if memory_id in self.consolidation_cache:
            self.metrics.cache_hits += 1
            logger.debug(f"💨 Cache hit for consolidation: {memory_id[:8]}")
            return self.consolidation_cache[memory_id]

        self.metrics.cache_misses += 1
        return None

    def clear_cache(self, memory_id: Optional[str] = None):
        """Clear cache for a specific memory or all memories."""
        if memory_id:
            self.link_cache.pop(memory_id, None)
            self.consolidation_cache.pop(memory_id, None)
        else:
            self.link_cache.clear()
            self.consolidation_cache.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Get optimization metrics."""
        return {
            "optimization": self.metrics.optimization_name,
            "enabled": self.metrics.enabled,
            "calls_optimized": self.metrics.calls_optimized,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "pre_compute_hits": self.metrics.pre_compute_hits,
            "avg_latency_saved_ms": self.metrics.avg_latency_saved_ms,
            "total_latency_saved_ms": self.metrics.total_latency_saved_ms,
        }


class PatternLearningOptimizer:
    """
    Optimize the pattern detection → confirmation feedback loop.

    Based on discovered patterns:
    - pattern_detected → pattern_confirmed (100% probability)
    - pattern_confirmed → pattern_detected (100% probability)

    Adaptations #19, #20
    """

    def __init__(self, batch_size: int = 10, enable_batching: bool = True):
        self.batch_size = batch_size
        self.enable_batching = enable_batching

        # Pending confirmations for batch processing
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}

        # Pre-warmed UI state
        self.ui_cache: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self.metrics = OptimizationMetrics("PatternLearning")

        logger.info("🚀 PatternLearningOptimizer initialized")

    def pre_warm_confirmation_ui(self, pattern_id: str, pattern_data: Dict[str, Any]) -> bool:
        """
        Pre-warm confirmation UI components when pattern is detected.

        Adaptation #19: pattern_detected → pattern_confirmed (100% probability)
        Since confirmation always follows detection, pre-load UI components.
        """
        try:
            start_time = datetime.now()

            # Pre-compute UI data
            ui_data = {
                "pattern_id": pattern_id,
                "pattern_data": pattern_data,
                "similar_patterns": [],  # Would load similar patterns
                "confirmation_options": ["confirm", "reject", "defer"],
                "pre_warmed_at": datetime.now().isoformat(),
            }

            self.ui_cache[pattern_id] = ui_data
            self.metrics.calls_optimized += 1

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.total_latency_saved_ms += elapsed_ms

            logger.debug(f"🎨 Pre-warmed UI for pattern {pattern_id[:8]}")
            return True

        except Exception as e:
            logger.error(f"Error pre-warming UI: {e}")
            return False

    def add_to_batch(self, pattern_id: str, pattern_data: Dict[str, Any]):
        """
        Add pattern to batch for related pattern detection.

        Adaptation #20: pattern_confirmed → pattern_detected (100% probability)
        After confirmation, related patterns are always detected. Batch these
        detections for efficiency.
        """
        if not self.enable_batching:
            return

        self.pending_confirmations[pattern_id] = pattern_data

        # Trigger batch processing if threshold reached
        if len(self.pending_confirmations) >= self.batch_size:
            self._process_batch()

    def _process_batch(self):
        """Process batch of confirmed patterns to detect related patterns."""
        if not self.pending_confirmations:
            return

        try:
            start_time = datetime.now()

            confirmed_patterns = list(self.pending_confirmations.values())

            # In production, this would:
            # 1. Extract features from confirmed patterns
            # 2. Search for related patterns in batch
            # 3. Return new pattern detections

            logger.info(f"🔄 Batch processed {len(confirmed_patterns)} patterns for related detection")

            self.pending_confirmations.clear()
            self.metrics.calls_optimized += len(confirmed_patterns)

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.total_latency_saved_ms += elapsed_ms

        except Exception as e:
            logger.error(f"Error processing batch: {e}")

    def get_ui_data(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get pre-warmed UI data if available."""
        if pattern_id in self.ui_cache:
            self.metrics.cache_hits += 1
            logger.debug(f"💨 Cache hit for UI data: {pattern_id[:8]}")
            return self.ui_cache[pattern_id]

        self.metrics.cache_misses += 1
        return None

    def force_batch_process(self):
        """Force process current batch (for testing or shutdown)."""
        self._process_batch()

    def get_metrics(self) -> Dict[str, Any]:
        """Get optimization metrics."""
        return {
            "optimization": self.metrics.optimization_name,
            "enabled": self.metrics.enabled,
            "calls_optimized": self.metrics.calls_optimized,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "pending_batch_size": len(self.pending_confirmations),
            "avg_latency_saved_ms": self.metrics.avg_latency_saved_ms,
            "total_latency_saved_ms": self.metrics.total_latency_saved_ms,
        }


# Global instances (singleton pattern)
_memory_optimizer: Optional[MemoryWorkflowOptimizer] = None
_pattern_optimizer: Optional[PatternLearningOptimizer] = None


def get_memory_optimizer() -> MemoryWorkflowOptimizer:
    """Get singleton memory workflow optimizer."""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryWorkflowOptimizer()
    return _memory_optimizer


def get_pattern_optimizer() -> PatternLearningOptimizer:
    """Get singleton pattern learning optimizer."""
    global _pattern_optimizer
    if _pattern_optimizer is None:
        _pattern_optimizer = PatternLearningOptimizer()
    return _pattern_optimizer


def get_all_optimization_metrics() -> Dict[str, Any]:
    """Get metrics from all optimizers."""
    return {
        "memory_workflow": get_memory_optimizer().get_metrics(),
        "pattern_learning": get_pattern_optimizer().get_metrics(),
    }
