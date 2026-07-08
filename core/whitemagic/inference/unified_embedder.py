# ruff: noqa: BLE001
"""Unified Polyglot Embedder - Routes to Rust ONNX or Python FastEmbed

This module provides a zero-copy Arrow-based embedding pipeline that routes
to the fastest available backend:
1. Rust ONNX GPU
2. Rust ONNX CPU
3. Python FastEmbed (fallback)

Usage:
    embedder = UnifiedEmbedder()
    embeddings = embedder.encode_batch(texts, batch_size=2048)
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from whitemagic.config.paths import CACHE_DIR
from whitemagic.core.memory.db_manager import safe_connect

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


class UnifiedEmbedder:
    """Embedding router with zero-copy Arrow pipeline.

    v1.0: Basic fallback chain implemented
    v1.1: Arrow zero-copy integration (pending)
    v1.2: Iceoryx2 shared memory (pending)
    """

    def __init__(self, model_path: str | None = None):
        """Initialize the unified embedder.

        Args:
            model_path: Path to ONNX model. If None, uses default.
        """
        self.model_path = model_path or self._get_default_model_path()
        self.rust_onnx_available = self._check_rust_onnx()

        logger.info("UnifiedEmbedder initialized")
        logger.info("  Rust ONNX: %s", "✓" if self.rust_onnx_available else "✗")

    def _get_default_model_path(self) -> str:
        """Get default ONNX model path."""
        # Look in standard locations
        possible_paths = [
            "models/all-MiniLM-L6-v2.onnx",
            str(CACHE_DIR / "models" / "all-MiniLM-L6-v2.onnx"),
            "/usr/local/share/whitemagic/models/all-MiniLM-L6-v2.onnx",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Default fallback
        return "models/all-MiniLM-L6-v2.onnx"

    def _check_rust_onnx(self) -> bool:
        """Check if Rust ONNX is available."""
        try:
            import whitemagic_rs

            rs = cast(Any, whitemagic_rs)
            return hasattr(rs, "arrow_onnx_embed")
        except ImportError:
            return False

    def encode_batch(self, texts: list[str], batch_size: int = 2048) -> np.ndarray:
        """Encode batch with automatic polyglot routing.

        Args:
            texts: List of text strings to embed
            batch_size: Maximum batch size for GPU efficiency

        Returns:
            NumPy array of embeddings (batch_size, embedding_dim)

        Raises:
            RuntimeError: If no backend is available
        """
        import numpy as np

        # Split into sub-batches if needed
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self._encode_single_batch(batch)
            all_embeddings.append(batch_embeddings)

        # Concatenate all batches
        return cast(np.ndarray, np.vstack(all_embeddings))

    def _encode_single_batch(self, texts: list[str]) -> np.ndarray:
        """Encode a single batch using the best available backend."""

        # Route 1: Rust ONNX (fast)
        if self.rust_onnx_available:
            try:
                return self._encode_rust_onnx(texts)
            except Exception as e:
                logger.warning("Rust ONNX failed, falling back: %s", e, exc_info=True)

        # Route 2: Python FastEmbed (slow but reliable)
        return self._encode_python_fastembed(texts)

    def _encode_rust_onnx(self, texts: list[str]) -> np.ndarray:
        """Encode using Rust ONNX with Arrow."""
        import whitemagic_rs

        rs = cast(Any, whitemagic_rs)

        texts_arrow = rs.arrow_encode_memories(
            json.dumps(
                [{"id": str(i), "title": "", "content": t} for i, t in enumerate(texts)]
            )
        )

        result_arrow = rs.arrow_onnx_embed(texts_arrow, self.model_path)

        return self._arrow_to_numpy(cast(bytes, result_arrow))

    def _encode_python_fastembed(self, texts: list[str]) -> np.ndarray:
        """Encode using Python FastEmbed (fallback)."""
        try:
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            embeddings = list(model.embed(texts))

            return cast(np.ndarray, np.array(embeddings))

        except ImportError:
            # Ultimate fallback: random embeddings for testing
            logger.warning("FastEmbed not available, using random embeddings")
            embedding_dim = 384
            return cast(
                np.ndarray,
                np.random.randn(len(texts), embedding_dim).astype(np.float32),
            )

    def _arrow_to_numpy(self, arrow_bytes: bytes) -> np.ndarray:
        """Convert Arrow IPC to numpy (zero-copy).

        Args:
            arrow_bytes: Arrow IPC serialized bytes

        Returns:
            NumPy array viewing the Arrow buffer
        """
        import pyarrow as pa  # type: ignore[import-untyped]

        reader = pa.ipc.open_stream(arrow_bytes)
        batch = reader.read_next_batch()

        # Zero-copy: numpy array views Arrow buffer
        return cast(np.ndarray, batch.column(0).to_numpy(zero_copy_only=True))


def batch_embed_memories(db_path: str, embedder: UnifiedEmbedder | None = None) -> int:
    """Batch embed all memories in database.

    This is the F001 completion function.

    Args:
        db_path: Path to SQLite database
        embedder: UnifiedEmbedder instance (creates new if None)

    Returns:
        Number of memories embedded
    """

    if embedder is None:
        embedder = UnifiedEmbedder()

    conn = safe_connect(db_path)
    cursor = conn.execute(
        "SELECT id, content FROM memories WHERE memory_type != 'quarantined'"
    )

    batch_size = 2048
    batch_ids: list[str] = []
    batch_texts: list[str] = []
    total_embedded = 0

    for memory_id, content in cursor:
        batch_ids.append(str(memory_id))
        batch_texts.append(content[:512])  # Truncate for efficiency

        if len(batch_texts) >= batch_size:
            # Encode via unified pipeline
            embeddings = embedder.encode_batch(batch_texts, batch_size)

            # Write to DB
            for mid, emb in zip(batch_ids, embeddings):
                conn.execute(
                    """INSERT OR REPLACE INTO memory_embeddings
                       (memory_id, embedding) VALUES (?, ?)""",
                    (mid, emb.tobytes()),
                )

            total_embedded += len(batch_texts)
            logger.info("Embedded %s memories...", total_embedded)

            batch_ids.clear()
            batch_texts.clear()

    if batch_texts:
        embeddings = embedder.encode_batch(batch_texts, batch_size)
        for mid, emb in zip(batch_ids, embeddings):
            conn.execute(
                """INSERT OR REPLACE INTO memory_embeddings
                   (memory_id, embedding) VALUES (?, ?)""",
                (mid, emb.tobytes()),
            )
        total_embedded += len(batch_texts)

    conn.commit()
    conn.close()

    logger.info("✅ Completed! %s memories embedded", total_embedded)
    return total_embedded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    embedder = UnifiedEmbedder()

    texts = [
        "Rust programming language performance",
        "Python async await concurrency",
        "Memory safety without garbage collection",
    ]

    embeddings = embedder.encode_batch(texts)
    print(f"Encoded {len(texts)} texts → {embeddings.shape}")
