"""DEPRECATED: Consolidated into whitemagic.core.intelligence.quantum.

This shim re-exports QuantumGraphEngine and QuantumNode for backward compatibility.
All new code should import from whitemagic.core.intelligence.quantum.
"""

from whitemagic.core.intelligence.quantum import QuantumGraphEngine, QuantumNode

__all__ = ["QuantumGraphEngine", "QuantumNode"]
