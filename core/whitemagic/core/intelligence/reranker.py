# ruff: noqa: BLE001
"""Cross-Encoder Reranking — Optional precision layer after hybrid search.

Source: LIVING_MEMORY_GAP_ANALYSIS.md (Zep comparison)

After hybrid_recall returns top-K candidates via FTS + vector + graph walk,
this module re-scores each candidate against the original query using a
cross-encoder model for higher precision. Cross-encoders jointly encode
(query, document) pairs, producing more accurate relevance scores than
bi-encoder cosine similarity alone.

Graceful degradation: if no cross-encoder model is available (no torch,
no sentence-transformers), falls back to a lightweight lexical reranker
using BM25-style term overlap scoring.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_cross_encoder: Any | None = None
_cross_encoder_available: bool | None = None


@dataclass
class RankedResult:
    """A search result with a reranking score."""

    memory_id: str
    title: str
    content: str
    original_score: float
    rerank_score: float
    metadata: dict[str, Any] | None = None

    @property
    def combined_score(self) -> float:
        """Weighted combination of original and rerank scores.
        30% original signal + 70% rerank signal. The reranker's purpose is
        precision refinement, so it receives majority weight while the original
        retrieval score acts as a stability anchor.
        """
        return 0.3 * self.original_score + 0.7 * self.rerank_score


def _check_cross_encoder() -> bool:
    """Check if cross-encoder model is available."""
    global _cross_encoder_available
    if _cross_encoder_available is not None:
        return _cross_encoder_available
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401

        _cross_encoder_available = True
    except ImportError:
        _cross_encoder_available = False
    return _cross_encoder_available


def _get_cross_encoder() -> Any:
    """Get or initialize the cross-encoder model (lazy singleton)."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
        logger.info("Cross-encoder model loaded: ms-marco-MiniLM-L-6-v2")
        return _cross_encoder
    except Exception as e:
        logger.warning("Cross-encoder unavailable: %s", e, exc_info=True)
        return None


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"\b\w+\b", text.lower())


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    k1: float = 1.5,
    b: float = 0.75,
    avgdl: float = 100.0,
) -> float:
    """BM25 score for a single document against query tokens."""
    doc_len = len(doc_tokens)
    if doc_len == 0:
        return 0.0

    tf = Counter(doc_tokens)
    score = 0.0
    for term in query_tokens:
        if term not in tf:
            continue
        freq = tf[term]
        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * doc_len / avgdl)
        # IDF approximation (assume term appears in ~10% of docs)
        idf = math.log(1 + 10.0)
        score += idf * numerator / denominator

    return score


def lexical_rerank(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 10,
) -> list[RankedResult]:
    """Enhanced lexical reranker using TF-IDF and Numpy for precision.

    Args:
        query: The search query
        results: List of search result dicts
        top_k: Number of results to return

    Returns:
        Reranked results sorted by combined score
    """
    if not results:
        return []

    try:
        import numpy as np
    except ImportError:
        logger.debug("Numpy not available, using simple BM25 fallback")
        return _simple_bm25_rerank(query, results, top_k)

    query_tokens = _tokenize(query)
    if not query_tokens:
        orig_scores = [r.get("score", 0.0) for r in results]
        max_orig = max(orig_scores) if orig_scores else 0.0
        norm_factor = max_orig if max_orig > 0 else 1.0
        return [
            RankedResult(
                memory_id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                original_score=r.get("score", 0.0) / norm_factor,
                rerank_score=0.0,
                metadata=r.get("metadata"),
            )
            for r in results[:top_k]
        ]

    # 1. Build Vocab from the 200 candidates
    all_docs = []
    for r in results:
        text = (r.get("title") or "") + " " + (r.get("content") or "")
        all_docs.append(_tokenize(text))

    vocab = sorted(list(set([t for doc in all_docs for t in doc] + query_tokens)))
    word_to_idx = {word: i for i, word in enumerate(vocab)}

    # 2. Vectorize
    doc_vectors = np.zeros((len(all_docs), len(vocab)))
    query_vector = np.zeros(len(vocab))

    for word in query_tokens:
        if word in word_to_idx:
            query_vector[word_to_idx[word]] += 1

    for i, doc in enumerate(all_docs):
        for word in doc:
            if word in word_to_idx:
                doc_vectors[i, word_to_idx[word]] += 1

    # 3. TF-IDF Weighting
    df = np.sum(doc_vectors > 0, axis=0)
    idf = np.log((len(all_docs) + 1) / (df + 1)) + 1

    doc_vectors_tfidf = doc_vectors * idf
    query_vector_tfidf = query_vector * idf

    # 4. Cosine Similarity
    doc_norms = np.linalg.norm(doc_vectors_tfidf, axis=1)
    query_norm = np.linalg.norm(query_vector_tfidf)

    if query_norm > 0:
        scores = np.dot(doc_vectors_tfidf, query_vector_tfidf) / (
            doc_norms * query_norm + 1e-9
        )
    else:
        scores = np.zeros(len(all_docs))

    # 5. Normalize original scores to [0, 1]
    orig_scores = [r.get("score", 0.0) for r in results]
    max_orig = max(orig_scores) if orig_scores else 0.0
    norm_factor = max_orig if max_orig > 0 else 1.0

    # 6. Assemble Results
    reranked = []
    for i, (r, score) in enumerate(zip(results, scores)):
        reranked.append(
            RankedResult(
                memory_id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                original_score=r.get("score", 0.0) / norm_factor,
                rerank_score=float(score),
                metadata=r.get("metadata"),
            )
        )

    reranked.sort(key=lambda x: x.combined_score, reverse=True)
    return reranked[:top_k]


def _simple_bm25_rerank(query: str, results: list[Any], top_k: int) -> list[Any]:
    # (Original BM25 logic as fallback)
    query_tokens = _tokenize(query)
    all_tokens = [
        _tokenize(r.get("content", "") + " " + r.get("title", "")) for r in results
    ]
    avgdl = sum(len(t) for t in all_tokens) / max(len(all_tokens), 1)
    ranked = []
    max_bm25 = 0.0
    for r, doc_tokens in zip(results, all_tokens):
        bm25 = _bm25_score(query_tokens, doc_tokens, avgdl=avgdl)
        max_bm25 = max(max_bm25, bm25)
        ranked.append((r, bm25))

    # Normalize original scores to [0, 1]
    orig_scores = [r.get("score", 0.0) for r in results]
    max_orig = max(orig_scores) if orig_scores else 0.0
    norm_factor = max_orig if max_orig > 0 else 1.0

    reranked = []
    for r, bm25 in ranked:
        norm_score = bm25 / max_bm25 if max_bm25 > 0 else 0.0
        reranked.append(
            RankedResult(
                memory_id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                original_score=r.get("score", 0.0) / norm_factor,
                rerank_score=norm_score,
                metadata=r.get("metadata"),
            )
        )
    reranked.sort(key=lambda x: x.combined_score, reverse=True)
    return reranked[:top_k]


def cross_encoder_rerank(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 10,
) -> list[RankedResult]:
    """Rerank results using a cross-encoder model for maximum precision.

    Args:
        query: The search query
        results: List of search result dicts with at least 'id', 'title', 'content'
        top_k: Number of results to return

    Returns:
        Reranked results sorted by cross-encoder score

    """
    model = _get_cross_encoder()
    if model is None:
        logger.debug("Cross-encoder unavailable, falling back to lexical reranker")
        return lexical_rerank(query, results, top_k)

    # Prepare (query, document) pairs for cross-encoder
    pairs = []
    for r in results:
        doc_text = r.get("title", "") + " " + r.get("content", "")
        # Truncate to avoid exceeding model max_length
        doc_text = doc_text[:1024]
        pairs.append([query, doc_text])

    try:
        scores = model.predict(pairs)

        # Normalize to [0, 1]
        min_s = float(min(scores)) if len(scores) > 0 else 0.0
        max_s = float(max(scores)) if len(scores) > 0 else 1.0
        score_range = max_s - min_s if max_s > min_s else 1.0

        # Normalize original scores to [0, 1]
        orig_scores = [r.get("score", 0.0) for r in results]
        max_orig = max(orig_scores) if orig_scores else 0.0
        norm_factor = max_orig if max_orig > 0 else 1.0

        reranked = []
        for r, score in zip(results, scores):
            norm_score = (float(score) - min_s) / score_range
            reranked.append(
                RankedResult(
                    memory_id=r.get("id", ""),
                    title=r.get("title", ""),
                    content=r.get("content", ""),
                    original_score=r.get("score", 0.0) / norm_factor,
                    rerank_score=norm_score,
                    metadata=r.get("metadata"),
                )
            )

        for i, res in enumerate(reranked[:10]):
            logger.debug(
                "RANK %s: id=%s combined_score=%s (orig=%s, rerank=%s)",
                i + 1,
                res.memory_id,
                res.combined_score,
                res.original_score,
                res.rerank_score,
            )
        return reranked[:top_k]

    except Exception as e:
        logger.warning(
            "Cross-encoder inference failed: %s, falling back to lexical",
            e,
            exc_info=True,
        )
        return lexical_rerank(query, results, top_k)


class Reranker:
    """Wrapper class for reranking operations (backward compatibility)."""

    def rerank(
        self, query: str, items: list[dict[str, Any]], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """
        Perform the rerank operation.

        Args:
            query: Parameter description.
            items: Parameter description.
            top_k: Parameter description.

        Returns:
            list[dict[str, Any]]
        """
        results = rerank(query, items, top_k=top_k)
        return [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in results]

    def get_status(self) -> dict[str, Any]:
        """
        Get the status.

        Returns:
            dict[str, Any]
        """
        return get_status()


def rerank(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 10,
    strategy: str = "auto",
) -> list[RankedResult]:
    """Rerank search results using the best available strategy.

    Args:
        query: The search query
        results: List of search result dicts
        top_k: Number of results to return
        strategy: 'auto' (best available), 'cross_encoder', or 'lexical'

    Returns:
        Reranked results sorted by combined score

    """
    if not results:
        return []

    if strategy == "cross_encoder" or (strategy == "auto" and _check_cross_encoder()):
        return cross_encoder_rerank(query, results, top_k)
    else:
        return lexical_rerank(query, results, top_k)


def get_status() -> dict[str, Any]:
    """Get reranker status."""
    return {
        "cross_encoder_available": _check_cross_encoder(),
        "model": "cross-encoder/ms-marco-MiniLM-L-6-v2"
        if _check_cross_encoder()
        else None,
        "fallback": "lexical_bm25",
        "strategies": ["auto", "cross_encoder", "lexical"],
    }
