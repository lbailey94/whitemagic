# ruff: noqa: BLE001
"""
Symbolic Memory Integration — Connect symbolic reasoning with memory system.

Integrates symbolic reasoning with WhiteMagic's memory system,
allowing concepts to be linked to memories and vice versa.
"""

from __future__ import annotations

import logging
from typing import Any

from .symbolic import SymbolicEngine, get_symbolic_engine

logger = logging.getLogger(__name__)


class SymbolicMemory:
    """Bridges symbolic concepts and memory entries."""

    def __init__(self, engine: SymbolicEngine | None = None) -> None:
        self.engine = engine or get_symbolic_engine()
        self._memory_tags: dict[str, list[str]] = {}  # memory_id -> [concept_names]

    def tag_memory(self, memory_id: str, concepts: list[str]) -> None:
        """Tag a memory with symbolic concepts."""
        self._memory_tags.setdefault(memory_id, []).extend(concepts)

    def get_tags(self, memory_id: str) -> list[str]:
        """Get concepts tagged to a memory."""
        return self._memory_tags.get(memory_id, [])

    def find_by_concept(self, concept: str) -> list[str]:
        """Find all memories tagged with a concept."""
        return [mid for mid, tags in self._memory_tags.items() if concept in tags]

    def encode_memory(self, memory_id: str, content: str) -> str:
        """Encode a memory's content using symbolic representation."""
        return self.engine.encode(content)

    def decode_memory(self, encoded: str) -> str:
        """Decode a symbolically encoded memory."""
        return self.engine.decode(encoded)

    def summary(self) -> dict[str, Any]:
        return {
            "tagged_memories": len(self._memory_tags),
            "total_tags": sum(len(tags) for tags in self._memory_tags.values()),
            "concepts_available": self.engine.summary()["total_concepts"],
        }


_sym_mem: SymbolicMemory | None = None


def get_symbolic_memory() -> SymbolicMemory:
    global _sym_mem
    if _sym_mem is None:
        _sym_mem = SymbolicMemory()
    return _sym_mem
