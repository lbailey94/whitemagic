"""DEPRECATED: Consolidated into whitemagic.core.intelligence.quantum.

This shim re-exports QuantumEngine for backward compatibility.
All new code should import from whitemagic.core.intelligence.quantum.
"""
from whitemagic.core.intelligence.quantum import QuantumEngine, get_quantum_engine

__all__ = ["QuantumEngine", "get_quantum_engine"]
