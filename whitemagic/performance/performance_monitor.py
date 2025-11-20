"""Performance Monitor - Track execution performance"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import time


@dataclass
class PerformanceMetric:
    """A performance measurement"""
    operation: str
    duration_ms: float
    timestamp: datetime
    optimization_applied: Optional[str]


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.current_operation = None
        self.start_time = None
    
    def start_operation(self, operation: str):
        """Start timing an operation"""
        self.current_operation = operation
        self.start_time = time.time()
    
    def end_operation(self, optimization: Optional[str] = None):
        """End timing and record metric"""
        if not self.start_time or not self.current_operation:
            return
        
        duration_ms = (time.time() - self.start_time) * 1000
        
        metric = PerformanceMetric(
            operation=self.current_operation,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            optimization_applied=optimization
        )
        
        self.metrics.append(metric)
        
        # Reset
        self.current_operation = None
        self.start_time = None
        
        return metric
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.metrics:
            return {'operations': 0}
        
        total_time = sum(m.duration_ms for m in self.metrics)
        avg_time = total_time / len(self.metrics)
        
        optimized = [m for m in self.metrics if m.optimization_applied]
        optimization_rate = len(optimized) / len(self.metrics) if self.metrics else 0
        
        return {
            'operations': len(self.metrics),
            'total_time_ms': total_time,
            'average_time_ms': avg_time,
            'optimization_rate': optimization_rate,
            'optimizations_used': len(set(m.optimization_applied for m in optimized))
        }
    
    def get_slowest_operations(self, count: int = 5) -> List[PerformanceMetric]:
        """Get slowest operations"""
        return sorted(self.metrics, key=lambda m: m.duration_ms, reverse=True)[:count]


# Global instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
