"""
WhiteMagic Rust Bridge
Provides Python interface to Rust implementations
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Try to import Rust bindings
try:
    import whitemagic_rs

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    logger.warning("Rust bindings not available. Install with: maturin develop")


class RustBridge:
    """Bridge between Python and Rust implementations"""

    def __init__(self):
        self.rust_available = RUST_AVAILABLE

    def get_search(self, db_path: str) -> Any:
        """Get Rust search implementation"""
        if not self.rust_available:
            raise RuntimeError("Rust bindings not available")

        return whitemagic_rs.Search(db_path)

    def get_vector_search(self) -> Any:
        """Get Rust vector search implementation"""
        if not self.rust_available:
            raise RuntimeError("Rust bindings not available")

        return whitemagic_rs.VectorSearch()

    def get_graph_walker(self) -> Any:
        """Get Rust graph walker implementation"""
        if not self.rust_available:
            raise RuntimeError("Rust bindings not available")

        return whitemagic_rs.GraphWalker()

    def get_reasoning_engine(self, threshold: float = 0.7) -> Any:
        """Get Rust reasoning engine implementation"""
        if not self.rust_available:
            raise RuntimeError("Rust bindings not available")

        return whitemagic_rs.ReasoningEngine(threshold)

    def get_memory_consolidation(self, threshold: float = 0.7) -> Any:
        """Get Rust memory consolidation implementation"""
        if not self.rust_available:
            raise RuntimeError("Rust bindings not available")

        return whitemagic_rs.MemoryConsolidation(threshold)


# Global bridge instance
_bridge = RustBridge()


def get_rust_bridge() -> RustBridge:
    """Get global Rust bridge instance"""
    return _bridge


def is_rust_available() -> bool:
    """Check if Rust bindings are available"""
    return RUST_AVAILABLE
