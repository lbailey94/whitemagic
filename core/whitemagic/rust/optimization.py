"""Rust Optimization Module

Provides high-performance Rust-accelerated operations.
"""


from whitemagic.utils.rust_helper import get_rust_module, is_rust_available


class RustAccelerator:
    """Rust-based accelerator for performance-critical operations.

    This class provides a Python interface to Rust implementations
    for operations like similarity calculation, search, and pattern matching.
    """

    def __init__(self) -> None:
        """Initialize the Rust accelerator.

        Raises:
            ImportError: If Rust bridge is not available
        """
        if not is_rust_available():
            raise ImportError(
                "Rust bridge not available. "
                "Install whitemagic-rust or build from source."
            )
        self._rust = get_rust_module()

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using Rust.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if hasattr(self._rust, 'rust_similarity'):
            return float(self._rust.rust_similarity(text1, text2))
        # Fallback to pure Python
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()

    def is_available(self) -> bool:
        """Check if Rust accelerator is available.

        Returns:
            True if Rust is available and loaded
        """
        return self._rust is not None


__all__ = ['RustAccelerator']
