"""Sorting Bridge - Rust-accelerated sorting algorithms.

Phase 1 VC3: Translate deploy_grand_army.py sorting to Rust.
"""
from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar('T')

# Try to load Rust module
_rs: Any = None
try:
    import whitemagic_rust as _rs
except Exception:
    pass


def fast_sort(data: list[T], key: Any = None, reverse: bool = False) -> list[T]:
    """Sort list with Rust acceleration for large collections.

    Uses Rust's parallel sort for >10K elements, Python's Timsort otherwise.
    """
    if len(data) < 10000:
        # Python Timsort is fastest for small-to-medium collections
        return sorted(data, key=key, reverse=reverse)

    # Try Rust parallel sort for large collections
    if _rs is not None and hasattr(_rs, 'parallel_sort'):
        try:
            if key is None:
                return list(_rs.parallel_sort(data, reverse))
            else:
                # Rust can't handle key functions - use Python
                pass
        except Exception:
            pass

    # Python fallback
    return sorted(data, key=key, reverse=reverse)


def fast_sort_inplace(data: list[T], key: Any = None, reverse: bool = False) -> None:
    """Sort list in-place with Rust acceleration."""
    if len(data) < 10000:
        data.sort(key=key, reverse=reverse)
        return

    # For large lists, sorted() may be faster due to different algorithm
    sorted_data = fast_sort(data, key=key, reverse=reverse)
    data[:] = sorted_data


def parallel_sort_by_key(
    data: list[dict[str, Any]],
    key_field: str,
    reverse: bool = False
) -> list[dict[str, Any]]:
    """Sort list of dicts by key field with parallel acceleration.

    Specialized for campaign metrics and clone deployment data.
    """
    if not data:
        return []

    # Try Rust fast path for dict sorting
    if _rs is not None and hasattr(_rs, 'sort_dicts_by_field'):
        try:
            return list(_rs.sort_dicts_by_field(data, key_field, reverse))
        except Exception:
            pass

    # Python fallback
    return sorted(data, key=lambda x: x.get(key_field, 0), reverse=reverse)


def top_k(data: list[T], k: int, key: Any = None) -> list[T]:
    """Get top k elements without full sort (O(n log k) vs O(n log n))."""
    import heapq

    if key is None:
        return heapq.nlargest(k, data)
    return heapq.nlargest(k, data, key=key)


class ParallelSorter:
    """Parallel sorting engine for batch operations."""

    def __init__(self) -> None:
        self._rust_available = _rs is not None and hasattr(_rs, 'parallel_sort_batch')

    def sort_batches(
        self,
        batches: list[list[T]],
        key: Any = None,
        reverse: bool = False
    ) -> list[list[T]]:
        """Sort multiple batches in parallel.

        Useful for clone army deployments with multiple objective batches.
        """
        if not batches:
            return []

        # Try Rust parallel batch sort
        if self._rust_available:
            try:
                return list(_rs.parallel_sort_batch(batches, reverse))
            except Exception:
                pass

        # Python fallback - use ThreadPoolExecutor for parallel sorting
        from concurrent.futures import ThreadPoolExecutor

        def sort_batch(batch: list[T]) -> list[T]:
            return sorted(batch, key=key, reverse=reverse)

        with ThreadPoolExecutor(max_workers=min(len(batches), 8)) as executor:
            return list(executor.map(sort_batch, batches))

    def merge_sorted(self, sorted_lists: list[list[T]]) -> list[T]:
        """Merge multiple sorted lists into one sorted list."""
        import heapq

        if not sorted_lists:
            return []

        if len(sorted_lists) == 1:
            return sorted_lists[0]

        # Use heapq.merge for efficient k-way merge
        return list(heapq.merge(*sorted_lists))


def get_parallel_sorter() -> ParallelSorter:
    """Get a parallel sorter instance."""
    return ParallelSorter()
