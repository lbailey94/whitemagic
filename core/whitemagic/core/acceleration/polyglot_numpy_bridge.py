"""Universal Numpy Bridge — Zero-copy FFI for all polyglot backends.

Provides a unified interface for passing numpy arrays to Rust, Zig, and Haskell
backends without copying data. Uses numpy's buffer protocol to get direct
pointers to contiguous memory.

Usage:
    from polyglot_numpy_bridge import to_ptr, to_flat_ptr, from_ptr

    # Single vector to ctypes pointer (zero-copy)
    ptr = to_ptr(arr)

    # 2D array flattened to 1D pointer (zero-copy)
    ptr, shape = to_flat_ptr(arr_2d)

    # Ctypes pointer back to numpy (view, not copy)
    arr = from_ptr(ptr, length, dtype=np.float32)
"""

from __future__ import annotations

import ctypes
from typing import Any

import numpy as np


def to_ptr(arr: np.ndarray) -> Any:
    """Get ctypes pointer to numpy array data (zero-copy).

    Args:
        arr: Numpy array (must be contiguous)

    Returns:
        ctypes pointer to array data

    Raises:
        ValueError: If array is not contiguous
    """
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    return arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))


def to_double_ptr(arr: np.ndarray) -> Any:
    """Get ctypes double pointer to numpy array data (zero-copy).

    For Haskell FFI which uses CDouble (double precision).

    Args:
        arr: Numpy array (must be contiguous)

    Returns:
        ctypes pointer to array data as double
    """
    if arr.dtype != np.float64:
        arr = arr.astype(np.float64)
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    return arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def to_flat_ptr(arr_2d: np.ndarray) -> tuple[Any, tuple[int, int]]:
    """Flatten 2D array and get pointer (zero-copy).

    Args:
        arr_2d: 2D numpy array

    Returns:
        Tuple of (ctypes pointer, (n_rows, n_cols))
    """
    if arr_2d.ndim != 2:
        raise ValueError(f"Expected 2D array, got {arr_2d.ndim}D")
    if not arr_2d.flags["C_CONTIGUOUS"]:
        arr_2d = np.ascontiguousarray(arr_2d)
    ptr = arr_2d.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    return ptr, arr_2d.shape


def from_ptr(ptr: Any, length: int, dtype: type = np.float32) -> np.ndarray:
    """Create numpy array view from ctypes pointer (zero-copy).

    WARNING: The returned array is a view into the original memory.
    Do not use after the original array is garbage collected.

    Args:
        ptr: ctypes pointer
        length: Number of elements
        dtype: Numpy dtype (default: float32)

    Returns:
        Numpy array view
    """
    if dtype == np.float32:
        c_type: type[ctypes._SimpleCData[float]] = ctypes.c_float
    elif dtype == np.float64:
        c_type = ctypes.c_double
    elif dtype == np.int32:
        c_type = ctypes.c_int32  # type: ignore[assignment]
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")

    arr_type = c_type * length
    arr = arr_type.from_address(ctypes.addressof(ptr.contents))
    return np.frombuffer(arr, dtype=dtype)


def batch_to_ptrs(vectors: list[np.ndarray] | np.ndarray) -> tuple[list[Any], int]:
    """Convert list of vectors or 2D array to list of pointers (zero-copy).

    Args:
        vectors: List of 1D numpy arrays or 2D numpy array

    Returns:
        Tuple of (list of ctypes pointers, dimension)
    """
    if isinstance(vectors, np.ndarray):
        if vectors.ndim != 2:
            raise ValueError(f"Expected 2D array, got {vectors.ndim}D")
        if not vectors.flags["C_CONTIGUOUS"]:
            vectors = np.ascontiguousarray(vectors)
        n, dim = vectors.shape
        ptrs = []
        for i in range(n):
            row = vectors[i]
            ptrs.append(row.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
        return ptrs, dim

    # List of arrays
    if not vectors:
        return [], 0
    dim = len(vectors[0])
    ptrs = []
    for vec in vectors:
        if not vec.flags["C_CONTIGUOUS"]:
            vec = np.ascontiguousarray(vec)
        ptrs.append(vec.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
    return ptrs, dim


class ArrayPool:
    """Pre-allocated array pool to avoid repeated allocations.

    Useful for high-frequency FFI calls where allocation overhead matters.
    """

    def __init__(self, max_size: int = 10_000):
        self._pool: dict[int, np.ndarray] = {}
        self._max_size = max_size

    def get(self, size: int, dtype: type = np.float32) -> np.ndarray:
        """Get or create a pre-allocated array."""
        key = (size, dtype)
        if key not in self._pool:
            self._pool[key] = np.empty(size, dtype=dtype)  # type: ignore[index]
        return self._pool[key]  # type: ignore[index]

    def get_batch(self, n: int, dim: int, dtype: type = np.float32) -> np.ndarray:
        """Get or create a pre-allocated 2D array."""
        return self.get(n * dim, dtype).reshape(n, dim)

    def clear(self) -> int:
        """Clear the pool. Returns count of arrays cleared."""
        count = len(self._pool)
        self._pool.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        total_elements = sum(arr.size for arr in self._pool.values())
        return {
            "arrays": len(self._pool),
            "total_elements": total_elements,
            "total_bytes": total_elements * 4,  # Assuming float32
        }


# Global array pool for high-frequency operations
_global_pool = ArrayPool()


def get_array_pool() -> ArrayPool:
    """Get the global array pool."""
    return _global_pool
