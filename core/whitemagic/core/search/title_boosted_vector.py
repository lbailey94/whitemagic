"""Title-Boosted Vector Search — V019 Tier 2 LoCoMo Optimizer.
============================================================
Boosts vector similarity scores when query terms match memory titles.
Addresses the open-domain ceiling (~48%) by weighting title matches.

Algorithm:
1. Get base vector similarity scores (cosine)
2. Compute title overlap score (Jaccard or exact match)
3. Combine: final_score = vector_sim * (1 + title_boost * title_match)
"""
from __future__ import annotations

import re

from whitemagic.core.acceleration.simd_cosine import batch_cosine


def _tokenize(text: str) -> set[str]:
    """Tokenization for title matching - handles snake_case, kebab-case, CamelCase."""
    # Normalize: replace separators with spaces
    normalized = re.sub(r'[_\-\.]', ' ', text)
    # Split CamelCase
    normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', normalized)
    # Extract words (3+ chars)
    return set(re.findall(r'\b[a-zA-Z]{3,}\b', normalized.lower()))


def _title_match_score(query: str, title: str) -> float:
    """Compute title overlap score (0-1)."""
    query_tokens = _tokenize(query)
    title_tokens = _tokenize(title)

    if not query_tokens or not title_tokens:
        return 0.0

    intersection = len(query_tokens & title_tokens)
    union = len(query_tokens | title_tokens)

    if union == 0:
        return 0.0

    jaccard = intersection / union

    # Strong bonus for exact substring match (either direction)
    query_lower = query.lower().replace(' ', '').replace('_', '').replace('-', '')
    title_lower = title.lower().replace(' ', '').replace('_', '').replace('-', '')

    if query_lower in title_lower:
        # Query is substring of title
        jaccard = max(jaccard, 0.85)
    elif title_lower in query_lower:
        # Title is substring of query
        jaccard = max(jaccard, 0.75)

    # Extra bonus for word prefix matching (e.g., "session" matches "SESSION_CHECKPOINT")
    for q_word in query_tokens:
        for t_word in title_tokens:
            if q_word == t_word:
                jaccard = max(jaccard, 0.9)
            elif q_word.startswith(t_word) or t_word.startswith(q_word):
                jaccard = max(jaccard, 0.6)
                break

    return min(jaccard, 1.0)


def search_title_boosted(
    query: str,
    memories: list[dict],
    query_embedding: list[float] | None = None,
    top_k: int = 10,
    title_boost: float = 0.3,
    min_similarity: float = 0.1,
) -> list[dict]:
    """Search with title-boosted vector scoring."""
    if not memories:
        return []

    if query_embedding is None:
        from whitemagic.core.memory.embeddings import get_embedding_engine
        engine_obj = get_embedding_engine()
        query_embedding = engine_obj.encode(query)
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()

    mem_embeddings = []
    valid_memories = []

    for m in memories:
        emb = m.get('embedding')
        if emb is not None:
            if hasattr(emb, 'tolist'):
                emb = emb.tolist()
            mem_embeddings.append(emb)
            valid_memories.append(m)

    if not valid_memories:
        return []

    similarities = batch_cosine(query_embedding, mem_embeddings)

    scored_results = []

    for mem, sim in zip(valid_memories, similarities):
        if sim < min_similarity:
            continue

        title = mem.get('title', '') or mem.get('content', '')[:100]
        title_match = _title_match_score(query, title)

        combined_score = sim * (1 + title_boost * title_match)

        mem_copy = dict(mem)
        mem_copy['vector_similarity'] = sim
        mem_copy['title_match_score'] = title_match
        mem_copy['combined_score'] = combined_score
        scored_results.append(mem_copy)

    scored_results.sort(key=lambda x: x['combined_score'], reverse=True)

    return scored_results[:top_k]


def hybrid_search_with_dedup(
    query: str,
    memories: list[dict],
    top_k: int = 10,
    dedup_threshold: float = 0.95,
) -> list[dict]:
    """Hybrid search: vector + title boost + deduplication."""
    # Deduplicate by content hash
    seen_hashes = set()
    deduped = []

    for m in memories:
        content = m.get('content', '')
        content_hash = hash(content[:200].lower().strip())

        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            deduped.append(m)

    # Increase candidate pool from memories to ensure title matches are caught
    # single_hop and temporal often have keywords in title that vector misses at top-10
    results = search_title_boosted(
        query,
        deduped,
        top_k=top_k * 5,  # Increased candidate pool
        title_boost=0.8,  # Increased boost
    )

    # Final dedup by embedding similarity
    final_results = []
    seen_embeddings: list[list[float]] = []

    for r in results:
        emb = r.get('embedding')
        if emb is None:
            final_results.append(r)
            continue

        if hasattr(emb, 'tolist'):
            emb = emb.tolist()

        is_duplicate = False
        for seen_emb in seen_embeddings:
            sim = batch_cosine(emb, [seen_emb])[0]
            if sim > dedup_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_embeddings.append(emb)
            final_results.append(r)

    return final_results[:top_k]
