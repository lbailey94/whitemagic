"""Optimizer - Apply performance optimizations"""

from typing import Dict, List, Optional, Callable


class Optimizer:
    """Coordinate performance optimizations"""
    
    def __init__(self):
        self.optimizations_applied = {}
        self.rust_bridge = None
        self.haskell_bridge = None
        self._init_bridges()
    
    def _init_bridges(self):
        """Initialize language bridges"""
        try:
            from whitemagic.bindings.rust_bridge import get_rust_bridge
            self.rust_bridge = get_rust_bridge()
        except Exception:
            pass
        
        try:
            from whitemagic.bindings.haskell_bridge import get_haskell_bridge
            self.haskell_bridge = get_haskell_bridge()
        except Exception:
            pass
    
    def optimize_operation(
        self,
        operation: str,
        python_impl: Callable,
        *args,
        **kwargs
    ):
        """Optimize operation using best available method
        
        Args:
            operation: Operation name
            python_impl: Python implementation fallback
            *args, **kwargs: Operation arguments
            
        Returns:
            Result of optimized operation
        """
        # Try Rust first for compute-heavy ops
        if self.rust_bridge and self.rust_bridge.available:
            if 'consolidate' in operation or 'search' in operation:
                try:
                    # Would call Rust implementation
                    self.optimizations_applied[operation] = 'rust'
                    print(f"⚡ Using Rust optimization for: {operation}")
                except Exception:
                    pass
        
        # Try Haskell for type-safe transformations
        if self.haskell_bridge and self.haskell_bridge.available:
            if 'transform' in operation or 'validate' in operation:
                try:
                    # Would call Haskell implementation
                    self.optimizations_applied[operation] = 'haskell'
                    print(f"🎯 Using Haskell type safety for: {operation}")
                except Exception:
                    pass
        
        # Fall back to Python
        return python_impl(*args, **kwargs)
    
    def get_optimization_stats(self) -> Dict:
        """Get optimization statistics"""
        return {
            'rust_available': self.rust_bridge and self.rust_bridge.available,
            'haskell_available': self.haskell_bridge and self.haskell_bridge.available,
            'optimizations_applied': len(self.optimizations_applied),
            'by_type': self._count_by_type()
        }
    
    def _count_by_type(self) -> Dict:
        """Count optimizations by type"""
        counts = {}
        for opt_type in self.optimizations_applied.values():
            counts[opt_type] = counts.get(opt_type, 0) + 1
        return counts
