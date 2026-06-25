"""DEPRECATED: Consolidated into whitemagic.core.intelligence.quantum.

This shim re-exports QuantumGraphAdapter and QuantumWalkConfig for backward compatibility.
All new code should import from whitemagic.core.intelligence.quantum.
"""
from whitemagic.core.intelligence.quantum import QuantumGraphAdapter, QuantumWalkConfig

__all__ = ["QuantumGraphAdapter", "QuantumWalkConfig"]

