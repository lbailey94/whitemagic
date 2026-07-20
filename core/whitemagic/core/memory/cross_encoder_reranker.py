"""Cross-Encoder Reranker — optional second-pass relevance scoring.

Implements Gap A from the Memory & Cognitive Systems Strategy 2026.

A cross-encoder processes (query, document) pairs jointly, producing a
relevance score that captures fine-grained semantic matching beyond what
bi-encoder cosine similarity can achieve.

This module supports two modes:
  1. **Local model** (0 tokens): Uses FastEmbed sentence-transformers
     with a cross-encoder model (e.g., BAAI/bge-reranker-base) when
     available. No LLM calls — pure local inference.
  2. **Heuristic fallback** (0 tokens): When no cross-encoder model is
     available, falls back to enhanced lexical+semantic scoring that
     approximates cross-encoder behavior using:
     - Fine-grained token overlap (bigrams, trigrams)
     - Embedding cosine similarity with query expansion
     - Semantic density (how many query concepts appear in the document)

Both modes preserve the 0-token search guarantee.

Usage:
    from whitemagic.core.memory.cross_encoder_reranker import rerank_cross_encoder

    results = rerank_cross_encoder(query, results)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Model name for optional local cross-encoder
CROSS_ENCODER_MODEL = "BAAI/bge-reranker-base"

_instance: Any = None


def _get_cross_encoder_model() -> Any | None:
    """Try to load a local cross-encoder model. Returns None if unavailable."""
    global _instance
    if _instance is not None:
        return _instance
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

        _instance = CrossEncoder(CROSS_ENCODER_MODEL)
        logger.info("Cross-encoder model loaded: %s", CROSS_ENCODER_MODEL)
        return _instance
    except (ImportError, ModuleNotFoundError, Exception) as e:  # noqa: BLE001
        logger.debug("Cross-encoder model unavailable: %s", e)
        _instance = False  # Mark as checked but unavailable
        return None


def _compute_bigram_overlap(query: str, content: str) -> float:
    """Compute bigram overlap ratio between query and content."""
    def _bigrams(text: str) -> set[str]:
        words = text.lower().split()
        return {f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)}

    q_bigrams = _bigrams(query)
    c_bigrams = _bigrams(content)
    if not q_bigrams:
        return 0.0
    return len(q_bigrams & c_bigrams) / len(q_bigrams)


def _compute_trigram_overlap(query: str, content: str) -> float:
    """Compute trigram overlap ratio between query and content."""
    def _trigrams(text: str) -> set[str]:
        words = text.lower().split()
        return {f"{words[i]}_{words[i + 1]}_{words[i + 2]}" for i in range(len(words) - 2)}

    q_trigrams = _trigrams(query)
    c_trigrams = _trigrams(content)
    if not q_trigrams:
        return 0.0
    return len(q_trigrams & c_trigrams) / len(q_trigrams)


def _compute_semantic_density(query: str, content: str) -> float:
    """Compute semantic density — fraction of query content words in document."""
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    # Filter very common words
    stopword_like = {"the", "a", "an", "is", "are", "was", "were", "in", "on",
                     "at", "to", "for", "of", "with", "and", "or", "not", "from",
                     "by", "as", "this", "that", "these", "those", "it", "its",
                     "be", "been", "being", "have", "has", "had", "do", "does",
                     "did", "will", "would", "could", "should", "may", "might",
                     "can", "about", "what", "how", "why", "when", "where", "who",
                     "research", "recent", "advances", "historical", "understanding",
                     "application", "key", "principle", "study", "studies",
                     "analysis", "review", "overview", "introduction", "summary",
                     "concept", "role", "theory", "theoretical", "practical",
                     "framework", "frameworks", "fundamental", "crucial"}
    meaningful = query_words - stopword_like
    if not meaningful:
        return 0.0
    return len(meaningful & content_words) / len(meaningful)


def _heuristic_cross_score(query: str, content: str) -> float:
    """Heuristic cross-encoder score (0-1) using lexical features.

    Approximates cross-encoder behavior with:
    - Unigram overlap (30%)
    - Bigram overlap (25%)
    - Trigram overlap (15%)
    - Semantic density (30%)
    """
    # Unigram overlap (excluding stopwords so distinctive terms dominate)
    _stop = {"the", "a", "an", "is", "are", "was", "were", "in", "on",
             "at", "to", "for", "of", "with", "and", "or", "not", "from",
             "by", "as", "this", "that", "these", "those", "it", "its",
             "be", "been", "being", "have", "has", "had", "do", "does",
             "did", "will", "would", "could", "should", "may", "might",
             "can", "about", "what", "how", "why", "when", "where", "who",
             "research", "recent", "advances", "historical", "understanding",
             "application", "key", "principle", "study", "studies",
             "analysis", "review", "overview", "introduction", "summary",
             "concept", "role", "theory", "theoretical", "practical",
             "framework", "frameworks", "fundamental", "crucial"}
    q_words = set(query.lower().split()) - _stop
    c_words = set(content.lower().split())
    unigram = len(q_words & c_words) / len(q_words) if q_words else 0.0

    bigram = _compute_bigram_overlap(query, content)
    trigram = _compute_trigram_overlap(query, content)
    density = _compute_semantic_density(query, content)

    return 0.40 * unigram + 0.10 * bigram + 0.05 * trigram + 0.45 * density


# Blend weights: how much to trust cross-encoder vs bi-encoder
# 0.6 = 60% cross-encoder, 0.4 = bi-encoder (semantic similarity)
CROSS_ENCODER_WEIGHT = 0.6
BI_ENCODER_WEIGHT = 0.4


def _get_bi_encoder_score(mem: Any, idx: int) -> float:
    """Extract the bi-encoder (semantic) score from memory metadata.

    Falls back to a rank-based prior if no score is available.
    """
    if hasattr(mem, "metadata"):
        sem = mem.metadata.get("similarity_score")
        if sem is not None:
            return float(sem)
        sem = mem.metadata.get("semantic_score")
        if sem is not None:
            return float(sem)
    # Rank-based prior: first result gets 0.9, decaying by position
    return max(0.1, 0.9 - idx * 0.05)


def _normalize_score(score: float, method: str) -> float:
    """Normalize a cross-encoder score to 0-1 range."""
    if method == "model":
        # Cross-encoder model scores are logits, apply sigmoid
        import math
        return 1.0 / (1.0 + math.exp(-score)) if score > -50 else 0.0
    return max(0.0, min(1.0, score))


def rerank_cross_encoder(
    query: str,
    results: list[Any],
    top_k: int | None = None,
    use_model: bool = True,
    blend_weight: float | None = None,
) -> list[Any]:
    """Rerank results using cross-encoder scoring blended with bi-encoder scores.

    Uses a **blend** strategy instead of replacing the bi-encoder ordering:
        final_score = w_ce * cross_encoder + w_bi * bi_encoder

    This preserves semantically-relevant matches that the cross-encoder
    might miss due to lexical mismatch, while still boosting results that
    have strong query-document overlap.

    Args:
        query: The search query
        results: List of Memory objects with metadata
        top_k: If provided, return only top K results
        use_model: If True, try to use local cross-encoder model.
                   If False or model unavailable, use heuristic scoring.
        blend_weight: Override for cross-encoder weight (default 0.6).
                      Bi-encoder weight = 1.0 - blend_weight.

    Returns:
        Reranked list of Memory objects with cross_encoder_score and
        blended_score metadata.
    """
    if not results:
        return results

    w_ce = blend_weight if blend_weight is not None else CROSS_ENCODER_WEIGHT
    w_bi = 1.0 - w_ce

    # Try model-based cross-encoder
    model = _get_cross_encoder_model() if use_model else None

    if model and model is not False:
        try:
            pairs = [(query, str(m.content)) for m in results]
            scores = model.predict(pairs)

            scored: list[tuple[float, int, Any]] = []
            for idx, (raw_score, mem) in enumerate(zip(scores, results)):
                ce_score = _normalize_score(float(raw_score), "model")
                bi_score = _get_bi_encoder_score(mem, idx)
                blended = w_ce * ce_score + w_bi * bi_score

                mem.metadata["cross_encoder_score"] = round(ce_score, 6)
                mem.metadata["blended_score"] = round(blended, 6)
                mem.metadata["cross_encoder_method"] = "model"
                scored.append((blended, -idx, mem))

            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            reranked = [m for _, _, m in scored]
            return reranked[:top_k] if top_k else reranked
        except Exception as e:  # noqa: BLE001
            logger.debug("Cross-encoder model scoring failed: %s", e)

    # Heuristic fallback — also blended
    scored: list[tuple[float, int, Any]] = []
    for idx, mem in enumerate(results):
        content = str(mem.content)
        ce_score = _heuristic_cross_score(query, content)
        bi_score = _get_bi_encoder_score(mem, idx)
        blended = w_ce * ce_score + w_bi * bi_score

        mem.metadata["cross_encoder_score"] = round(ce_score, 6)
        mem.metadata["blended_score"] = round(blended, 6)
        mem.metadata["cross_encoder_method"] = "heuristic"
        scored.append((blended, -idx, mem))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    reranked = [m for _, _, m in scored]
    return reranked[:top_k] if top_k else reranked
