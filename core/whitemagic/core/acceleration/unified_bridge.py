"""Unified Memory Bridge - Rust-accelerated core memory operations.

Phase 1 VC6: Translate unified.py core methods to Rust.
"""
from __future__ import annotations

import hashlib
from typing import Any

# Try to load Rust module
try:
    import whitemagic_rs as _rs_mod
    _rs = _rs_mod
except Exception:
    _rs = None


def fast_content_hash(content: str | bytes) -> str:
    """Compute SHA-256 content hash with Rust acceleration."""
    # Try Rust fast path
    if _rs is not None and hasattr(_rs, 'compute_sha256'):
        try:
            if isinstance(content, str):
                return str(_rs.compute_sha256(content))
            return str(_rs.compute_sha256_bytes(content))
        except Exception:
            pass

    # Python fallback
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def batch_content_hash(contents: list[str | bytes]) -> list[str]:
    """Compute content hashes in batch with Rust parallelization."""
    # Try Rust fast path
    if _rs is not None and hasattr(_rs, 'batch_sha256'):
        try:
            return list(_rs.batch_sha256(contents))
        except Exception:
            pass

    # Python fallback - use list comprehension
    return [fast_content_hash(c) for c in contents]


class UnifiedMemoryBridge:
    """Rust-accelerated unified memory operations."""

    def __init__(self) -> None:
        self._rust_available = _rs is not None

    def dedup_check(
        self,
        content_hash: str,
        existing_hashes: set[str]
    ) -> tuple[bool, str | None]:
        """Check if content hash exists in set with Rust acceleration."""
        # Try Rust fast path for large sets
        if _rs is not None and len(existing_hashes) > 10000:
            try:
                bloom_filter_check = getattr(_rs, 'bloom_filter_check', None)
                if bloom_filter_check is not None:
                    # Use Bloom filter for probabilistic fast check
                    result = bloom_filter_check(content_hash, list(existing_hashes))
                    if result["probably_exists"] and result["confirmed"]:
                        return True, result.get("matched_id")
            except Exception:
                pass

        # Python fallback - simple set lookup
        return content_hash in existing_hashes, None

    def batch_store(
        self,
        memories: list[dict[str, Any]],
        backend_store_fn: Any
    ) -> list[dict[str, Any]]:
        """Batch store memories with deduplication.

        Args:
            memories: List of memory dicts to store
            backend_store_fn: Function to call for actual storage
        """
        # Compute all hashes
        contents: list[str | bytes] = [str(m.get('content', '')) for m in memories]
        hashes = batch_content_hash(contents)

        # Deduplicate
        seen_hashes: set[str] = set()
        unique_memories = []

        for memory, content_hash in zip(memories, hashes):
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                memory['_content_hash'] = content_hash
                unique_memories.append(memory)

        # Store in batches
        results = []
        batch_size = 100
        for i in range(0, len(unique_memories), batch_size):
            batch = unique_memories[i:i + batch_size]
            for mem in batch:
                result = backend_store_fn(mem)
                results.append(result)

        return results

    def compute_importance_boost(
        self,
        base_importance: float,
        access_count: int,
        emotional_valence: float,
        novelty_score: float
    ) -> float:
        """Compute boosted importance score with Rust acceleration."""
        # Try Rust fast path
        if _rs is not None and hasattr(_rs, 'compute_importance'):
            try:
                return float(_rs.compute_importance(
                    base_importance,
                    access_count,
                    emotional_valence,
                    novelty_score
                ))
            except Exception:
                pass

        # Python fallback
        boost = 0.0

        # Access frequency boost
        if access_count > 10:
            boost += 0.05
        if access_count > 50:
            boost += 0.05

        # Emotional significance boost
        if abs(emotional_valence) > 0.7:
            boost += 0.03

        # Novelty boost
        boost += novelty_score * 0.02

        return min(1.0, base_importance + boost)

    def get_backend(self) -> str:
        """Report which backend is active."""
        return "rust" if self._rust_available else "python"


def get_unified_memory_bridge() -> UnifiedMemoryBridge:
    """Get unified memory bridge instance."""
    return UnifiedMemoryBridge()
