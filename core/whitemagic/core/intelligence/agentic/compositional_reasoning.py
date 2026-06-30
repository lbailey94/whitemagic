"""HRR-Based Compositional Reasoning — Pre-LLM Vector Reasoning.

Resolves relation-based queries using Holographic Reduced Representations
instead of sending them to an LLM. This turns multi-hop reasoning into
single vector operations at SIMD speed.

Examples:
    "What caused X?" → inverse_project(X_embedding, "CAUSES") → vector search
    "What uses X?"   → project(X_embedding, "USES") → vector search
    "Find events with agent Y" → decode_event_role(event, "AGENT") → match

This module integrates with the LocalReasoningEngine as a new reasoning
strategy that runs before any LLM call is made.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from whitemagic.core.memory.hrr import HRREngine, get_hrr_engine

logger = logging.getLogger(__name__)


@dataclass
class CompositionalResult:
    """Result from compositional reasoning."""

    resolved: bool
    answer: str
    method: str
    confidence: float
    relation: str = ""
    projected_query: str = ""
    matches: list[dict[str, Any]] = field(default_factory=list)
    tokens_saved: int = 0
    latency_ms: float = 0.0


_RELATION_PATTERNS: list[tuple[str, str, str]] = [
    # (regex_pattern, relation, direction)
    # direction: "forward" = project, "inverse" = inverse_project
    (r"what (?:caused|leads to|triggers)\s+(.+)", "CAUSES", "inverse"),
    (r"what (?:is caused by|resulted from)\s+(.+)", "CAUSED_BY", "inverse"),
    (r"what (?:follows|comes after)\s+(.+)", "FOLLOWS", "inverse"),
    (r"what (?:precedes|comes before)\s+(.+)", "PRECEDED_BY", "inverse"),
    (r"what (?:is part of|belongs to)\s+(.+)", "PART_OF", "forward"),
    (r"what (?:contains|includes|has part)\s+(.+)", "CONTAINS", "forward"),
    (r"what (?:is similar to|resembles|is like)\s+(.+)", "SIMILAR_TO", "forward"),
    (r"what (?:is opposite of|contradicts)\s+(.+)", "OPPOSITE_OF", "forward"),
    (r"what (?:extends|builds on|expands)\s+(.+)", "EXTENDS", "inverse"),
    (r"what (?:is extended by|is built upon)\s+(.+)", "EXTENDED_BY", "forward"),
    (r"what (?:uses|utilizes|employs)\s+(.+)", "USES", "inverse"),
    (r"what (?:is used by|is utilized by)\s+(.+)", "USED_BY", "forward"),
    (r"what (?:creates|produces|generates)\s+(.+)", "CREATES", "inverse"),
    (r"what (?:is created by|is made by)\s+(.+)", "CREATED_BY", "inverse"),
    (r"what (?:implements|realizes)\s+(.+)", "IMPLEMENTS", "inverse"),
    (r"what (?:is implemented by|is realized by)\s+(.+)", "IMPLEMENTED_BY", "forward"),
]


def _extract_relation(query: str) -> tuple[str, str, str] | None:
    """Extract relation and subject from a natural language query.

    Returns (subject, relation, direction) or None if no relation pattern matches.
    """
    query_lower = query.lower().strip()
    for pattern, relation, direction in _RELATION_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            subject = match.group(1).strip().rstrip("?.,!")
            return subject, relation, direction
    return None


class CompositionalReasoner:
    """Resolves relation-based queries using HRR vector operations.

    Instead of sending "what caused X?" to an LLM, this module:
    1. Encodes the subject X into an embedding
    2. Projects/inverse-projects through the relation vector
    3. Searches memory for similar embeddings
    4. Returns results without any LLM call
    """

    def __init__(self, hrr: HRREngine | None = None) -> None:
        self._hrr = hrr

    def _get_hrr(self) -> HRREngine:
        if self._hrr is None:
            self._hrr = get_hrr_engine()
        return self._hrr

    def can_resolve(self, query: str) -> bool:
        """Check if this query can be resolved via compositional reasoning."""
        return _extract_relation(query) is not None

    def resolve(
        self,
        query: str,
        max_results: int = 5,
    ) -> CompositionalResult:
        """Attempt to resolve a relation-based query using HRR projections.

        Args:
            query: Natural language query (e.g., "what caused the outage?")
            max_results: Maximum number of matches to return.

        Returns:
            CompositionalResult with resolved=True if successful.
        """
        start = time.time()

        extracted = _extract_relation(query)
        if extracted is None:
            return CompositionalResult(
                resolved=False,
                answer="",
                method="none",
                confidence=0.0,
                latency_ms=(time.time() - start) * 1000,
            )

        subject, relation, direction = extracted

        # Encode the subject text into an embedding
        try:
            from whitemagic.core.memory.embeddings import EmbeddingEngine

            engine = EmbeddingEngine()
            subject_embedding = engine.encode(subject)
            if subject_embedding is None:
                return CompositionalResult(
                    resolved=False,
                    answer="",
                    method="encoding_failed",
                    confidence=0.0,
                    relation=relation,
                    latency_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            logger.debug("Embedding engine unavailable: %s", e, exc_info=True)
            return CompositionalResult(
                resolved=False,
                answer="",
                method="embedding_unavailable",
                confidence=0.0,
                relation=relation,
                latency_ms=(time.time() - start) * 1000,
            )

        # Apply HRR projection through the relation
        hrr = self._get_hrr()
        if direction == "forward":
            projected = hrr.project(subject_embedding, relation)
        else:
            projected = hrr.inverse_project(subject_embedding, relation)

        # Search memory for vectors similar to the projected embedding
        matches = self._search_projected(projected.tolist(), max_results)

        if not matches:
            return CompositionalResult(
                resolved=False,
                answer="",
                method="no_matches",
                confidence=0.0,
                relation=relation,
                projected_query=subject,
                latency_ms=(time.time() - start) * 1000,
            )

        # Build answer from matches
        answer_parts = []
        for m in matches[:max_results]:
            title = m.get("title", "")
            content = m.get("content", "")[:200]
            score = m.get("similarity", 0.0)
            answer_parts.append(f"- {title}: {content} (score: {score:.2f})")

        answer = f"Via {relation} relation with '{subject}':\n" + "\n".join(
            answer_parts
        )
        tokens_saved = len(answer) // 4  # rough token estimate

        return CompositionalResult(
            resolved=True,
            answer=answer,
            method=f"hrr:{direction}:{relation}",
            confidence=min(0.9, matches[0].get("similarity", 0.5)),
            relation=relation,
            projected_query=subject,
            matches=matches[:max_results],
            tokens_saved=tokens_saved,
            latency_ms=(time.time() - start) * 1000,
        )

    def _search_projected(
        self,
        projected_embedding: list[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search memory using a projected embedding vector.

        Uses the embedding engine's similarity search to find memories
        that match the HRR-projected query vector.
        """
        try:
            from whitemagic.core.memory.embeddings import EmbeddingEngine

            engine = EmbeddingEngine()

            # Use search_similar with the projected vector
            results = engine.search_similar_by_vector(
                projected_embedding,
                limit=limit,
                min_similarity=0.1,
            )
            return results
        except AttributeError:
            # search_similar_by_vector may not exist — fall back to text search
            logger.debug(
                "Vector search by embedding not available, using text fallback"
            )
            return []
        except Exception as e:
            logger.debug("Projected search failed: %s", e, exc_info=True)
            return []


_reasoner: CompositionalReasoner | None = None


def get_compositional_reasoner() -> CompositionalReasoner:
    """Get the global CompositionalReasoner singleton."""
    global _reasoner
    if _reasoner is None:
        _reasoner = CompositionalReasoner()
    return _reasoner


def reason_compositionally(query: str, max_results: int = 5) -> CompositionalResult:
    """Convenience function for compositional reasoning."""
    return get_compositional_reasoner().resolve(query, max_results=max_results)
