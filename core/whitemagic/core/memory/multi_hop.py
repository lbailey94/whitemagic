"""Multi-hop aggregation — two-pass search for multi-hop questions.

When a query like "What team is the person working on project Eta on?"
requires combining facts from multiple memories, a single FTS5 search
often misses the hop-2 result because the query doesn't contain the
hop-2 keyword (e.g., "frontend").

This module implements a lightweight two-pass search:

Pass 1: Normal search → top-K results (hop-1 seeds)
Pass 2: Extract entities from hop-1 results → search for those entities
        + remaining query terms → merge via RRF

This is a 0-token approach that uses the existing FTS5 backend.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _extract_result_entities(results: list[Any], top_k: int = 3) -> list[str]:
    """Extract entity-like terms from the top search results.

    These serve as seeds for the second-pass search.
    Handles both capitalized proper nouns and lowercase entity IDs
    like "entity_012".
    """
    entities: list[str] = []
    seen: set[str] = set()

    # Patterns for entity extraction from result content
    patterns = [
        r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b",  # Capitalized: "Alice", "New York"
        r"\b\w+_\d+\b",  # Entity IDs: "entity_012", "fact_00005"
    ]

    for mem in results[:top_k]:
        content = str(mem.content)
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                if m not in seen:
                    seen.add(m)
                    entities.append(m)

    return entities


def _extract_key_terms(query: str) -> list[str]:
    """Extract non-stopword terms from the query for secondary search."""
    _stop = {
        "what", "who", "which", "where", "when", "why", "how",
        "is", "are", "was", "were", "the", "a", "an",
        "did", "does", "do", "has", "have", "had",
        "on", "in", "at", "for", "with", "about",
        "person", "people", "team", "group", "project",
        "working", "assigned", "involved",
    }
    terms = re.findall(r"\b[a-z]{3,}\b", query.lower())
    return [t for t in terms if t not in _stop]


def multi_hop_search(
    query: str,
    results: list[Any],
    backend: Any = None,
    galaxy: str | None = None,
    hop_limit: int = 10,
    max_results: int = 20,
) -> list[Any]:
    """Two-pass search that uses hop-1 results as seeds for hop-2.

    Args:
        query: Original search query
        results: Initial search results (hop-1)
        backend: Galaxy backend for secondary search
        galaxy: Galaxy to search in
        hop_limit: Max results per hop
        max_results: Maximum total results to return

    Returns:
        Augmented and re-ranked results list
    """
    if not results or not backend:
        return results

    # Only run multi-hop for natural language questions (not synthetic queries)
    query_lower = query.lower().strip()
    _question_starts = ("what ", "who ", "which ", "where ", "when ", "why ", "how ", "whose ")
    if not any(query_lower.startswith(s) for s in _question_starts):
        return results

    # Extract entities from top results (hop-1 seeds)
    seed_entities = _extract_result_entities(results, top_k=3)
    if not seed_entities:
        return results

    # Extract remaining query terms (non-entity, non-stopword)
    query_terms = _extract_key_terms(query)

    # Build secondary search query: entity names + query terms
    # The idea: if hop-1 found "entity_012 has project Eta",
    # we search for "entity_012 team" to find the team memory
    secondary_queries: list[str] = []

    # Strategy 1: Each entity + query terms that aren't in the entity
    for entity in seed_entities[:3]:  # Top 3 entities
        # Use entity name + non-overlapping query terms
        remaining = [t for t in query_terms if t.lower() not in entity.lower()]
        if remaining:
            secondary_queries.append(f"{entity} {' '.join(remaining[:3])}")
        else:
            secondary_queries.append(entity)

    # Strategy 2: All entities together (for cross-entity questions)
    if len(seed_entities) > 1:
        secondary_queries.append(" ".join(seed_entities[:3]))

    # Run secondary searches and collect results
    existing_ids = {m.id for m in results}
    secondary_results: list[Any] = []

    for sq in secondary_queries[:1]:  # Limit to 1 secondary search for latency
        try:
            hits = backend.search(query=sq, limit=hop_limit, galaxy=galaxy)
            for mem in hits:
                if mem.id not in existing_ids:
                    mem.metadata["multi_hop_source"] = "secondary"
                    mem.metadata["multi_hop_seed_query"] = sq
                    secondary_results.append(mem)
                    existing_ids.add(mem.id)
        except Exception as e:
            logger.debug("Multi-hop secondary search failed: %s", e)

    if not secondary_results:
        return results

    # Merge via simple RRF: primary results get rank bonus
    # RRF score = 1 / (k + rank) with k=60
    rrf_k = 60
    all_results = results + secondary_results

    scored: list[tuple[float, int, Any]] = []
    for rank, mem in enumerate(all_results):
        # Primary results get higher base score (they were ranked first)
        is_primary = rank < len(results)
        rrf_score = 1.0 / (rrf_k + rank + 1)
        if is_primary:
            rrf_score *= 1.5  # Boost primary results

        # Blend with existing similarity/blended score
        existing_score = 0.0
        if hasattr(mem, "metadata"):
            existing_score = mem.metadata.get(
                "blended_score",
                mem.metadata.get("similarity_score", 0.0),
            )

        final_score = rrf_score + existing_score * 0.3
        scored.append((final_score, rank, mem))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    return [m for _, _, m in scored[:max_results]]
