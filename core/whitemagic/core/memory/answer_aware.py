"""Answer-aware retrieval — boosts results likely to contain the answer.

When a query asks "What did Alice say about X?", FTS5 tends to rank
individual turns with high keyword density above the turn that actually
contains the answer. This module:

1. Extracts entity + topic hints from the query pattern
2. Runs a secondary FTS5 search focused on those hints
3. Boosts results that contain both the entity and the topic keyword

This is a 0-token, heuristic approach — no LLM calls.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Query patterns that benefit from answer-aware boosting
# Each pattern captures (entity, topic) groups from natural language questions
_QUERY_PATTERNS: list[re.Pattern[str]] = [
    # "What did Alice say about machine learning?" → entity=Alice, topic=machine learning
    re.compile(r"what\s+(?:did|does|do)\s+(.+?)\s+(?:say|mention|tell|talk|state)\s+about\s+(.+)", re.IGNORECASE),
    # "What is the location of entity_003?" → entity=entity_003, topic=location (swapped)
    re.compile(r"what\s+(?:is|are)\s+the\s+(.+?)\s+of\s+(.+)", re.IGNORECASE),
    # "What is entity_012 role?" → entity=entity_012, topic=role
    re.compile(r"what\s+(?:is|are)\s+(\w+)\s+(\w+)", re.IGNORECASE),
    # "Who is the person working on project Eta?" → entity=project Eta, topic=person
    re.compile(r"who\s+(?:is|are)\s+(.+?)\s+(?:working|assigned|involved)\s+(?:on|in|with)\s+(.+)", re.IGNORECASE),
    # "What did Bob do?" → entity=Bob
    re.compile(r"what\s+(?:did|does)\s+(.+?)\s+(?:do|study|work|prefer|like|enjoy)\s*\??", re.IGNORECASE),
    # "Alice's current project" → entity=Alice, topic=project
    re.compile(r"(\w+)'s\s+(?:current|latest|new|previous)\s+(.+)", re.IGNORECASE),
]

# Words that should never be extracted as entities
_NON_ENTITIES = {
    "what", "who", "which", "where", "when", "why", "how",
    "the", "a", "an", "this", "that", "these", "those",
    "is", "are", "was", "were", "did", "does", "do",
    "person", "people", "someone", "anyone",
    "tell", "explain", "describe", "show", "list", "give",
}


def extract_answer_hints(query: str) -> dict[str, str]:
    """Extract entity and topic hints from a natural language query.

    Returns a dict with optional 'entity' and 'topic' keys.
    """
    for idx, pattern in enumerate(_QUERY_PATTERNS):
        match = pattern.match(query.strip())
        if match:
            groups = match.groups()
            hints: dict[str, str] = {}

            # Pattern index 1 ("what is the X of Y") has swapped groups:
            # group 0 = topic (attribute), group 1 = entity (subject)
            if idx == 1:
                topic_raw, entity_raw = groups[0], groups[1]
            else:
                entity_raw, topic_raw = groups[0], groups[1] if len(groups) > 1 else None

            if entity_raw:
                entity = entity_raw.strip().rstrip("?.,!")
                if entity.lower() not in _NON_ENTITIES:
                    hints["entity"] = entity
            if topic_raw:
                topic = topic_raw.strip().rstrip("?.,!")
                if topic.lower() not in _NON_ENTITIES:
                    hints["topic"] = topic
            if hints:
                return hints

    # Fallback: extract capitalized entities as hints
    # But exclude common non-entity words that appear capitalized at sentence start
    _FALLBACK_EXCLUDE = _NON_ENTITIES | {
        "research", "recent", "advances", "historical", "understanding",
        "application", "key", "principle", "influence", "impact",
        "role", "analysis", "study", "studies", "review", "overview",
        "introduction", "summary", "conclusion", "method", "approach",
        "result", "results", "discussion", "background", "abstract",
    }
    entities = re.findall(r"\b[A-Z][a-z]{2,}\b", query)
    entities = [e for e in entities if e.lower() not in _FALLBACK_EXCLUDE]
    if entities:
        return {"entity": entities[0]}

    return {}


def content_boost(
    query: str,
    results: list[Any],
    boost_factor: float = 0.15,
    max_boost: float = 0.3,
) -> list[Any]:
    """Boost results that contain both entity and topic from the query.

    This is a post-retrieval reranking step that promotes results likely
    to contain the actual answer by checking for co-occurrence of the
    query's entity and topic terms in the result content.
    """
    if not results or len(results) <= 1:
        return results

    hints = extract_answer_hints(query)
    if not hints:
        return results

    entity = hints.get("entity", "").lower()
    topic = hints.get("topic", "").lower()

    if not entity and not topic:
        return results

    # Also extract key content terms from the query (non-stopwords)
    query_terms = set(re.findall(r"\b[a-z]{3,}\b", query.lower()))
    _stop = {
        "what", "did", "does", "the", "was", "were", "has", "have", "had",
        "about", "said", "told", "asked", "answered", "mentioned", "stated",
        "who", "which", "that", "this", "from", "into", "with", "for",
        "are", "was", "were", "been", "being", "their", "there", "they",
        "his", "her", "she", "him", "his", "its", "our", "your",
    }
    content_terms = query_terms - _stop
    if entity:
        content_terms.discard(entity)
    if topic:
        content_terms.discard(topic)

    for mem in results:
        content = str(mem.content).lower()
        boost = 0.0

        # Strong boost: both entity and topic present
        if entity and topic and entity in content and topic in content:
            boost += boost_factor * 2
            # Extra boost if they appear close together (within 50 chars)
            e_pos = content.find(entity)
            t_pos = content.find(topic)
            if e_pos >= 0 and t_pos >= 0 and abs(e_pos - t_pos) < 50:
                boost += boost_factor

        # Medium boost: entity present + at least one content term
        elif entity and entity in content:
            matching_terms = sum(1 for t in content_terms if t in content)
            if matching_terms > 0:
                boost += boost_factor * min(matching_terms, 2)

        # Medium boost: topic present
        elif topic and topic in content:
            boost += boost_factor

        boost = min(boost, max_boost)

        if boost > 0 and hasattr(mem, "metadata"):
            existing = mem.metadata.get("answer_aware_boost", 0.0)
            mem.metadata["answer_aware_boost"] = round(max(existing, boost), 6)
            # Apply boost to similarity_score if present
            if "similarity_score" in mem.metadata:
                mem.metadata["similarity_score"] = round(
                    mem.metadata["similarity_score"] + boost, 6
                )

    # Re-sort by similarity_score (or blended_score if present) descending
    def _score(mem: Any) -> float:
        if hasattr(mem, "metadata"):
            return mem.metadata.get(
                "blended_score",
                mem.metadata.get("similarity_score", 0.0),
            )
        return 0.0

    results.sort(key=_score, reverse=True)
    return results


def answer_aware_search(
    query: str,
    results: list[Any],
    backend: Any = None,
    galaxy: str | None = None,
) -> list[Any]:
    """Full answer-aware retrieval pipeline.

    1. Extract answer hints from query
    2. If entity hints found, run secondary FTS5 search for entity terms
    3. Merge secondary results with primary results (dedup by ID)
    4. Apply content-based boosting
    5. Return re-ranked results
    """
    if not results:
        return results

    hints = extract_answer_hints(query)
    if not hints:
        return results

    entity = hints.get("entity")
    topic = hints.get("topic")

    # Secondary search: search for entity + topic terms
    secondary_results: list[Any] = []
    if backend and (entity or topic):
        search_terms = " ".join(filter(None, [entity, topic]))
        if search_terms.strip():
            try:
                secondary_results = backend.search(
                    query=search_terms,
                    limit=10,
                    galaxy=galaxy,
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("Answer-aware secondary search failed: %s", e)

    # Merge: add secondary results not already in primary
    existing_ids = {m.id for m in results}
    for mem in secondary_results:
        if mem.id not in existing_ids:
            mem.metadata["answer_aware_source"] = "secondary"
            results.append(mem)
            existing_ids.add(mem.id)

    # Apply content boosting
    results = content_boost(query, results)

    return results
