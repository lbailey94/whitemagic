"""Language Bindings - Rust/Haskell FFI

Multi-language integration with graceful degradation:
- Rust: Performance (10-100x faster)
- Haskell: Correctness (compile-time guarantees)
- Python: Flexibility (fallback + orchestration)
"""

from .rust_bridge import RustBridge, rust_available
from .haskell_bridge import HaskellBridge, haskell_available

__all__ = ['RustBridge', 'HaskellBridge', 'rust_available', 'haskell_available']
