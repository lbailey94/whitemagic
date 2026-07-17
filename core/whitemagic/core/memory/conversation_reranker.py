"""Conversation-Aware Reranker — 4 ranking improvements for conversational memory.

Implements §8.7.1 of the Memory & Cognitive Systems Strategy 2026.

Problem: LoCoMo recall@1 is 20% but recall@5 is 92%. The correct memory IS
retrieved but not ranked first. FTS5 BM25 ranks by keyword density, so a turn
mentioning "machine learning" 3 times outranks the turn where Alice actually
states her opinion.

Four 0-token heuristic approaches applied as additive bonuses:
  1. Conversation-grouped reranking
  2. Answer-type detection (opinion/fact/preference)
  3. Turn-position weighting
  4. Semantic similarity tiebreaker
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_OPINION_RE = re.compile(
    r"\b(?:what did .+ (?:think|feel|say|believe|suggest|recommend)|"
    r"what(?:'s| is) .+ (?:opinion|view|take|stance)|"
    r"how does .+ feel about|what are .+ (?:thoughts|views) on)\b",
    re.IGNORECASE,
)
_PREFERENCE_RE = re.compile(
    r"\b(?:what does .+ (?:prefer|like|enjoy|love|favorite)|"
    r"what is .+ favorite|what would .+ choose)\b",
    re.IGNORECASE,
)
_FACT_RE = re.compile(
    r"\b(?:what (?:is|are|was|were) the|when (?:is|was|did)|"
    r"where (?:is|was|did)|how many|how much|who (?:is|was|did))\b",
    re.IGNORECASE,
)

_OPINION_MARKERS = {
    "think", "feel", "believe", "opinion", "personally", "i'd say",
    "my view", "my take", "i think", "i feel", "i believe",
    "suggest", "recommend", "should", "ought to", "in my opinion",
    "from my perspective", "i'd recommend", "i'd suggest",
}
_FACT_MARKERS = {
    "is", "are", "was", "were", "the deadline", "the budget",
    "the team", "the meeting", "the report", "the client",
    "the project", "the deployment", "the conference",
}
_PREFERENCE_MARKERS = {
    "prefer", "favorite", "love", "enjoy", "like more",
    "my favorite", "i prefer", "i love", "i enjoy",
    "i'd choose", "i'd pick", "i'd go with",
}

_CONV_ID_RE = re.compile(r"(conv_\d+|sess_\d+)")

W_CONV_GROUP = 0.08
W_ANSWER_TYPE = 0.12
W_TURN_POSITION = 0.05
W_SEMANTIC = 0.10
W_ENTITY = 0.15        # boost when query entity (person name) appears in content
W_SUMMARY = 0.06       # boost summary memories over raw turns
W_EMBED_TIEBREAK = 0.03  # small embedding cosine tiebreaker for close scores

# Common person names for entity extraction
_NAME_RE = re.compile(
    r"\b(?:What did|What (?:is|was)|What are|What were|"
    r"How does|How did|What about|"
    r"In which session did)\s+"
    r"([A-Z][a-z]+)\b"
)


def detect_answer_type(query: str) -> str:
    if _OPINION_RE.search(query):
        return "opinion"
    if _PREFERENCE_RE.search(query):
        return "preference"
    if _FACT_RE.search(query):
        return "fact"
    return "general"


def _marker_score(content: str, markers: set[str]) -> float:
    cl = content.lower()
    hits = sum(1 for m in markers if m in cl)
    return min(1.0, hits / 3.0)


def _extract_conv_id(mem: Any) -> str | None:
    tags = getattr(mem, "tags", None)
    if tags:
        for tag in tags:
            m = _CONV_ID_RE.search(str(tag))
            if m:
                return m.group(1)
    title = getattr(mem, "title", None)
    if title:
        m = _CONV_ID_RE.search(str(title))
        if m:
            return m.group(1)
    md = getattr(mem, "metadata", None)
    if md:
        for k in ("conversation_id", "session_id", "conv_id"):
            v = md.get(k)
            if v:
                return str(v)
    return None


def _extract_turn_idx(mem: Any) -> int | None:
    title = getattr(mem, "title", None)
    if not title:
        return None
    m = re.search(r"turn_(\d+)", str(title))
    return int(m.group(1)) if m else None


def _extract_query_entities(query: str) -> set[str]:
    """Extract person names and capitalized entities from the query."""
    entities: set[str] = set()
    for m in _NAME_RE.finditer(query):
        name = m.group(1)
        if name not in {"What", "How", "The", "Which", "In", "Did"}:
            entities.add(name.lower())
    return entities


def _is_summary(mem: Any) -> bool:
    """Check if a memory is a summary (tagged 'summary' or title contains 'summary')."""
    tags = getattr(mem, "tags", None)
    if tags and "summary" in tags:
        return True
    title = getattr(mem, "title", None)
    if title and "summary" in str(title).lower():
        return True
    return False


def _get_embedding(mem: Any) -> list[float] | None:
    """Get embedding vector from memory if available."""
    md = getattr(mem, "metadata", None)
    if md:
        emb = md.get("embedding") or md.get("embedding_vector")
        if emb and isinstance(emb, (list, tuple)) and len(emb) > 0:
            return list(emb)
    return None


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _get_base_score(mem: Any, idx: int) -> float:
    md = getattr(mem, "metadata", None)
    if md:
        for k in ("blended_score", "similarity_score", "semantic_score"):
            v = md.get(k)
            if v is not None:
                return float(v)
    return max(0.1, 0.9 - idx * 0.05)


def conversation_rerank(
    query: str,
    results: list[Any],
    limit: int = 10,
) -> list[Any]:
    """Apply conversation-aware reranking to search results."""
    if len(results) <= 1:
        if results:
            results[0].metadata["conv_rerank_score"] = round(_get_base_score(results[0], 0), 6)
            results[0].metadata["answer_type"] = detect_answer_type(query)
        return results

    # Guard: only apply when conversation structure is detected in results.
    # The internal benchmark uses generic memories without conv_XXX tags,
    # so conversation grouping and turn-position weighting would be noise.
    has_conv_structure = any(_extract_conv_id(m) is not None for m in results)
    if not has_conv_structure:
        return results

    atype = detect_answer_type(query)
    markers = {"opinion": _OPINION_MARKERS, "preference": _PREFERENCE_MARKERS,
               "fact": _FACT_MARKERS}.get(atype, set())

    # Extract entities from query for entity-aware boosting
    query_entities = _extract_query_entities(query)

    # Find dominant conversation
    conv_best: dict[str, float] = {}
    for mem in results:
        cid = _extract_conv_id(mem)
        if cid is None:
            continue
        s = _get_base_score(mem, 0)
        if cid not in conv_best or s > conv_best[cid]:
            conv_best[cid] = s
    top_conv = max(conv_best, key=conv_best.get) if conv_best else None

    # Max turn index for normalization
    max_turn = 0
    for mem in results:
        ti = _extract_turn_idx(mem)
        if ti is not None and ti > max_turn:
            max_turn = ti

    # Compute embedding similarity for tiebreaking (if embeddings available)
    embed_sims: dict[int, float] = {}
    query_emb = None
    # Try to get query embedding from the first result's metadata (if stored)
    for mem in results:
        md = getattr(mem, "metadata", None)
        if md and md.get("_query_embedding"):
            query_emb = md["_query_embedding"]
            break
    if query_emb:
        for idx, mem in enumerate(results):
            mem_emb = _get_embedding(mem)
            if mem_emb:
                embed_sims[idx] = _cosine_sim(query_emb, mem_emb)

    scored: list[tuple[float, int, Any]] = []
    for idx, mem in enumerate(results):
        base = _get_base_score(mem, idx)

        cid = _extract_conv_id(mem)
        conv_bonus = W_CONV_GROUP if (top_conv and cid == top_conv) else 0.0

        type_bonus = 0.0
        if markers:
            type_bonus = W_ANSWER_TYPE * _marker_score(str(getattr(mem, "content", "")), markers)

        turn_bonus = 0.0
        ti = _extract_turn_idx(mem)
        if ti is not None and max_turn > 0:
            turn_bonus = W_TURN_POSITION * (ti / max_turn)

        sem_bonus = W_SEMANTIC * base

        # Entity-aware boosting: if query mentions a person name, boost
        # memories whose content contains that name
        entity_bonus = 0.0
        if query_entities:
            content_lower = str(getattr(mem, "content", "")).lower()
            for entity in query_entities:
                if entity in content_lower:
                    entity_bonus += W_ENTITY
                    break  # one match is enough

        # Summary-preference bias: summaries are higher density, boost them
        summary_bonus = W_SUMMARY if _is_summary(mem) else 0.0

        # Embedding cosine tiebreaker: small bonus for high embedding similarity
        embed_bonus = 0.0
        if idx in embed_sims:
            embed_bonus = W_EMBED_TIEBREAK * embed_sims[idx]

        final = base + conv_bonus + type_bonus + turn_bonus + sem_bonus + entity_bonus + summary_bonus + embed_bonus
        mem.metadata["conv_rerank_score"] = round(final, 6)
        mem.metadata["answer_type"] = atype
        scored.append((final, -idx, mem))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    reranked = [m for _, _, m in scored]
    return reranked[:limit] if limit else reranked
