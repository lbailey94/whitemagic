"""
Performance - Optimization Infrastructure

性能 (Xìng Néng) - Performance

Rust/Haskell bridges for critical paths + optimization coordination:
- Performance monitoring
- Bottleneck detection
- Optimization recommendations
- Bridge coordination

Philosophy: Optimize where it matters. Like water finding fastest path.
"""

from whitemagic.performance.performance_monitor import PerformanceMonitor
from whitemagic.performance.bottleneck_detector import BottleneckDetector
from whitemagic.performance.optimizer import Optimizer
from whitemagic.performance.bridge_coordinator import BridgeCoordinator

__all__ = [
    'PerformanceMonitor',
    'BottleneckDetector',
    'Optimizer',
    'BridgeCoordinator',
]

__version__ = "2.6.5"
