#!/usr/bin/env python3
"""TF-IDF Embedding Pipeline — Lightweight Semantic Indexing
=============================================================

Populates the memory_embeddings table using TF-IDF vectors.
This is a fast, dependency-light alternative to sentence-transformers.

Features:
- TF-IDF vectorization (384 dims, matches BGE-small)
- SVD dimensionality reduction via scipy
- Batch processing with progress tracking
- Incremental — only embeds memories without embeddings
- Compatible with existing vector search infrastructure

Usage:
    python scripts/tfidf_embedding_pipeline.py                    # All memories
    python scripts/tfidf_embedding_pipeline.py --limit 1000       # Limit
    python scripts/tfidf_embedding_pipeline.py --batch-size 200   # Batch size
    python scripts/tfidf_embedding_pipeline.py --dry-run          # Preview
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WM_SILENT_INIT"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tfidf_pipeline")

EMBEDDING_DIM = 384  # Matches BGE-small for compatibility


def get_db_path() -> Path:
    from whitemagic.config.paths import DB_PATH

    return DB_PATH


def get_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def tokenize(text: str) -> list[str]:
    """Simple tokenizer — lowercase, remove punctuation, filter stopwords."""
    import re

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = text.split()

    stopwords = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "has",
        "have",
        "been",
        "from",
        "this",
        "that",
        "they",
        "with",
        "will",
        "each",
        "make",
        "like",
        "just",
        "over",
        "such",
        "more",
        "than",
        "them",
        "very",
        "when",
        "come",
        "could",
        "into",
        "time",
        "only",
        "its",
        "also",
        "after",
        "some",
        "then",
        "other",
        "what",
        "which",
        "their",
        "there",
        "about",
        "would",
        "these",
        "should",
        "because",
        "through",
        "between",
        "during",
        "before",
        "above",
        "below",
        "any",
        "same",
        "both",
        "few",
        "most",
        "own",
        "while",
        "where",
        "how",
        "who",
        "whom",
        "why",
        "did",
        "does",
        "doing",
        "done",
        "being",
        "is",
        "it",
        "in",
        "on",
        "at",
        "to",
        "of",
        "by",
        "or",
        "an",
        "as",
        "if",
        "so",
        "we",
        "he",
        "she",
        "my",
        "his",
        "me",
        "us",
        "am",
        "be",
        "are",
        "was",
        "were",
        "said",
        "say",
        "says",
        "went",
        "go",
        "get",
        "got",
        "a",
        "i",
        "s",
        "t",
        "m",
        "re",
        "ll",
        "ve",
        "d",
        "don",
        "didn",
    }
    return [w for w in words if w not in stopwords and len(w) > 2]


def build_vocabulary(
    documents: list[list[str]], max_vocab: int = 5000
) -> dict[str, int]:
    """Build vocabulary from documents, keeping top-N terms by document frequency."""
    doc_freq = Counter()
    for doc in documents:
        doc_freq.update(set(doc))

    # Keep most common terms
    vocab = {term: idx for idx, (term, _) in enumerate(doc_freq.most_common(max_vocab))}
    return vocab


def compute_tfidf(
    documents: list[list[str]], vocab: dict[str, int]
) -> list[list[float]]:
    """Compute TF-IDF vectors for all documents."""
    n_docs = len(documents)
    n_terms = len(vocab)

    # Document frequency for IDF
    doc_freq = Counter()
    for doc in documents:
        doc_freq.update(set(doc))

    # IDF: log(N / df)
    idf = {}
    for term, idx in vocab.items():
        df = doc_freq.get(term, 0)
        idf[idx] = math.log((n_docs + 1) / (df + 1)) + 1  # Smoothed IDF

    # TF-IDF vectors
    vectors = []
    for doc in documents:
        # Term frequency
        tf = Counter(doc)
        max_tf = max(tf.values()) if tf else 1

        # Build vector
        vec = [0.0] * n_terms
        for term, count in tf.items():
            if term in vocab:
                idx = vocab[term]
                # Normalized TF * IDF
                normalized_tf = 0.5 + 0.5 * (count / max_tf)
                vec[idx] = normalized_tf * idf[idx]

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        vectors.append(vec)

    return vectors


def reduce_dimensions(
    vectors: list[list[float]], target_dim: int = EMBEDDING_DIM
) -> list[list[float]]:
    """Reduce dimensionality using random projection (fast alternative to SVD)."""
    import random

    n_docs = len(vectors)
    if n_docs == 0:
        return []

    source_dim = len(vectors[0])
    if source_dim <= target_dim:
        # Pad with zeros
        return [vec + [0.0] * (target_dim - len(vec)) for vec in vectors]

    # Random projection matrix (seeded for reproducibility)
    random.seed(42)
    projection = [
        [random.gauss(0, 1) for _ in range(source_dim)] for _ in range(target_dim)
    ]

    # Normalize projection rows
    for row in projection:
        norm = math.sqrt(sum(v * v for v in row))
        if norm > 0:
            row[:] = [v / norm for v in row]

    # Project
    reduced = []
    for vec in vectors:
        projected = []
        for proj_row in projection:
            val = sum(v * p for v, p in zip(vec, proj_row))
            projected.append(val)

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in projected))
        if norm > 0:
            projected = [v / norm for v in projected]

        reduced.append(projected)

    return reduced


def pack_embedding(vec: list[float]) -> bytes:
    """Pack float list to bytes for storage."""
    import struct

    return struct.pack(f"{len(vec)}f", *vec)


def run_pipeline(limit: int = 0, batch_size: int = 200, dry_run: bool = False) -> dict:
    """Run the TF-IDF embedding pipeline."""
    db_path = get_db_path()
    conn = get_conn(db_path)

    # Find memories without embeddings
    query = """
        SELECT m.id, m.title, m.content
        FROM memories m
        LEFT JOIN memory_embeddings me ON m.id = me.memory_id
        WHERE me.memory_id IS NULL
        AND LENGTH(m.content) > 10
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    memories = conn.execute(query).fetchall()
    total = len(memories)

    log.info(f"═══ TF-IDF Embedding Pipeline ═══")
    log.info("  Memories to embed: %s", total)
    log.info("  Batch size: %s", batch_size)
    log.info("  Target dimension: %s", EMBEDDING_DIM)
    log.info("  Dry run: %s", dry_run)

    if total == 0:
        log.info("  ✅ All memories already have embeddings!")
        return {"embedded": 0, "total": 0}

    embedded_count = 0
    failed_count = 0
    start_time = time.perf_counter()

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = memories[batch_start:batch_end]

        # Tokenize
        documents = []
        for mem in batch:
            text = f"{mem['title'] or ''} {mem['content'] or ''}"[:5000]
            documents.append(tokenize(text))

        # Build vocabulary for this batch
        vocab = build_vocabulary(documents, max_vocab=2000)

        if not vocab:
            log.warning("  Empty vocabulary for batch %s-%s", batch_start, batch_end)
            failed_count += len(batch)
            continue

        # Compute TF-IDF
        vectors = compute_tfidf(documents, vocab)

        # Reduce dimensions
        reduced = reduce_dimensions(vectors, target_dim=EMBEDDING_DIM)

        now = datetime.now().isoformat()
        for i, mem in enumerate(batch):
            if i < len(reduced):
                vec = reduced[i]
                packed = pack_embedding(vec)

                if not dry_run:
                    try:
                        conn.execute(
                            """INSERT OR REPLACE INTO memory_embeddings
                               (memory_id, embedding, model, created_at)
                               VALUES (?, ?, ?, ?)""",
                            (mem["id"], packed, "tfidf_384", now),
                        )
                        embedded_count += 1
                    except Exception as e:
                        log.warning(f"  Failed to embed {mem['id'][:12]}: {e}")
                        failed_count += 1
                else:
                    embedded_count += 1

        if (batch_start + batch_size) % 1000 == 0 or batch_end == total:
            if not dry_run:
                conn.commit()
            elapsed = time.perf_counter() - start_time
            rate = embedded_count / elapsed if elapsed > 0 else 0
            log.info(
                f"  Progress: {batch_end}/{total} ({embedded_count} embedded, {rate:.0f}/sec)"
            )

    if not dry_run:
        conn.commit()

    elapsed = time.perf_counter() - start_time
    rate = embedded_count / elapsed if elapsed > 0 else 0

    log.info(
        f"\n  ✅ Embedded {embedded_count} memories in {elapsed:.1f}s ({rate:.0f}/sec)"
    )
    log.info("  ❌ Failed: %s", failed_count)

    total_embedded = conn.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone()[
        0
    ]
    total_memories = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    log.info(f"\n📊 Embedding Statistics:")
    log.info(
        f"  Total embeddings: {total_embedded:,}/{total_memories:,} ({100 * total_embedded / total_memories:.1f}%)"
    )

    conn.close()
    return {
        "embedded": embedded_count,
        "failed": failed_count,
        "total": total,
        "elapsed": elapsed,
        "rate": rate,
    }


def main():
    parser = argparse.ArgumentParser(description="TF-IDF Embedding Pipeline")
    parser.add_argument("--limit", type=int, default=0, help="Limit memories")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    run_pipeline(limit=args.limit, batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
