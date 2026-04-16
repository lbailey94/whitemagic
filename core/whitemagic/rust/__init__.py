"""
WhiteMagic Rust Implementations
High-performance Rust implementations for critical paths
"""

# Optional imports - these may not exist in all builds
try:
    from .rust_bridge import (
        RustBridge,
        get_rust_bridge,
        is_rust_available,
    )
    _has_rust_bridge = True
except ImportError:
    _has_rust_bridge = False

# Import optimization module (provides RustAccelerator)
try:
    from .optimization import RustAccelerator
    _has_optimization = True
except ImportError:
    _has_optimization = False

__all__ = [
    'get_rust_bridge',
    'is_rust_available',
    'RustBridge',
    'RustAccelerator',
]
