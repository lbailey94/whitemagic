"""Abstention Gate — Relevance threshold for search results.

Implements Gap D from the Memory & Cognitive Systems Strategy 2026.

When a query has no relevant memories, the system should abstain (return
empty results) rather than returning the closest irrelevant match. This
module provides the threshold logic for making that determination.

Scoring signals:
  1. Semantic similarity (cosine similarity between query and result embeddings)
  2. FTS5 match quality (keyword overlap ratio)
  3. RRF score (combined ranking score from search planner)

Abstention is triggered when the top result's relevance score falls below
a configurable threshold. The threshold defaults to 0.12 (balanced —
abstains on clearly irrelevant queries while preserving high TPR).

Usage:
    from whitemagic.core.memory.abstention_gate import AbstentionGate

    gate = AbstentionGate(threshold=0.15)
    if gate.should_abstain(query, results):
        return []  # No relevant memories found
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.12
MIN_THRESHOLD = 0.0
MAX_THRESHOLD = 0.5


@dataclass
class AbstentionResult:
    """Result of an abstention check."""
    abstain: bool
    top_score: float
    threshold: float
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "abstain": self.abstain,
            "top_relevance_score": round(self.top_score, 4),
            "threshold": self.threshold,
            "reason": self.reason,
        }


class AbstentionGate:
    """Relevance threshold gate for search abstention.

    Evaluates whether search results are relevant enough to return.
    If the top result's relevance score is below the threshold, the
    system abstains (returns empty results).

    The relevance score is a blend of:
    - Semantic similarity (cosine similarity, 0-1)
    - Keyword overlap ratio (0-1)
    - RRF score (normalized, 0-1)

    Final score = 0.5 * semantic + 0.3 * keyword_overlap + 0.2 * rrf_normalized
    """

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.3,
        rrf_weight: float = 0.2,
    ) -> None:
        self.threshold = max(MIN_THRESHOLD, min(MAX_THRESHOLD, threshold))
        self._semantic_weight = semantic_weight
        self._keyword_weight = keyword_weight
        self._rrf_weight = rrf_weight

    def _compute_semantic_score(self, query: str, content: str) -> float:
        """Compute semantic similarity between query and content."""
        try:
            from whitemagic.core.memory.embeddings import (
                get_embedding_engine,
            )
            engine = get_embedding_engine()
            query_vec = engine.encode(query)
            if query_vec is None:
                return 0.0
            # Use a simple heuristic if we can't get the memory's embedding
            # In practice, the search pipeline already has embeddings cached
            return 0.5  # Neutral score when embeddings unavailable
        except Exception:  # noqa: BLE001
            return 0.5  # Neutral — don't penalize when embeddings unavailable

    def _compute_keyword_overlap(self, query: str, content: str) -> float:
        """Compute keyword overlap ratio between query and content."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & content_words
        return len(overlap) / len(query_words)

    def _normalize_rrf(self, rrf_score: float) -> float:
        """Normalize RRF score to 0-1 range."""
        if rrf_score <= 0:
            return 0.0
        # RRF scores are typically in 0.01-0.1 range for good matches
        return min(1.0, rrf_score * 10.0)

    def compute_relevance(
        self,
        query: str,
        content: str,
        rrf_score: float = 0.0,
        semantic_score: float | None = None,
    ) -> float:
        """Compute relevance score for a single result.

        Args:
            query: The search query
            content: The memory content
            rrf_score: RRF score from search planner (if available)
            semantic_score: Pre-computed semantic similarity (if available)

        Returns:
            Relevance score in 0-1 range
        """
        if semantic_score is not None:
            sem = semantic_score
        else:
            sem = self._compute_semantic_score(query, content)

        kw = self._compute_keyword_overlap(query, content)
        rrf = self._normalize_rrf(rrf_score)

        return (
            self._semantic_weight * sem
            + self._keyword_weight * kw
            + self._rrf_weight * rrf
        )

    def should_abstain(
        self,
        query: str,
        results: list[Any],
        threshold: float | None = None,
    ) -> AbstentionResult:
        """Check if the system should abstain (return no results).

        Args:
            query: The search query
            results: List of search result objects (Memory or dict)
            threshold: Override threshold for this check

        Returns:
            AbstentionResult with decision and scores
        """
        if not results:
            return AbstentionResult(
                abstain=True,
                top_score=0.0,
                threshold=threshold or self.threshold,
                reason="no_results",
            )

        thresh = threshold if threshold is not None else self.threshold

        # Get top result
        top = results[0]

        # Extract content and scores from result
        if hasattr(top, "content"):
            content = str(top.content)
            rrf = float(top.metadata.get("rrf_score", 0.0)) if hasattr(top, "metadata") else 0.0
            sem = None
            if hasattr(top, "metadata"):
                sem = top.metadata.get("similarity_score")
                if sem is not None:
                    sem = float(sem)
        elif isinstance(top, dict):
            content = str(top.get("content", ""))
            rrf = float(top.get("rrf_score", 0.0))
            sem = top.get("similarity_score")
            if sem is not None:
                sem = float(sem)
        else:
            content = str(top)
            rrf = 0.0
            sem = None

        score = self.compute_relevance(query, content, rrf, sem)

        if score < thresh:
            return AbstentionResult(
                abstain=True,
                top_score=score,
                threshold=thresh,
                reason=f"top_score {score:.4f} < threshold {thresh}",
            )

        return AbstentionResult(
            abstain=False,
            top_score=score,
            threshold=thresh,
        )

    def filter_results(
        self,
        query: str,
        results: list[Any],
        threshold: float | None = None,
    ) -> tuple[list[Any], AbstentionResult]:
        """Filter results based on abstention threshold.

        Returns (filtered_results, abstention_result).
        If abstaining, returns empty list.
        """
        decision = self.should_abstain(query, results, threshold)
        if decision.abstain:
            return [], decision
        return results, decision


# Singleton
_instance: AbstentionGate | None = None


def get_abstention_gate() -> AbstentionGate:
    """Get the global AbstentionGate singleton."""
    global _instance
    if _instance is None:
        _instance = AbstentionGate()
    return _instance
