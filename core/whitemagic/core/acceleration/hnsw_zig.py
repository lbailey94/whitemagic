# ruff: noqa: BLE001
"""Zig HNSW Index — Python Bridge.

Provides approximate nearest neighbor search using Hierarchical Navigable
Small World (HNSW) graphs compiled in Zig with SIMD acceleration.

Usage:
    from whitemagic.core.acceleration.hnsw_zig import HnswIndex

    index = HnswIndex(dim=384, m=16, ef_construction=200, ef_search=50)
    index.add(vector)  # Add vectors
    results = index.search(query, k=10)  # Find nearest neighbors
"""

from __future__ import annotations

import ctypes
import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

from whitemagic.core.acceleration.polyglot_numpy_bridge import to_ptr

logger = logging.getLogger(__name__)

_lib = None
_lib_lock = threading.Lock()
_HAS_HNSW = False


class Connection(ctypes.Structure):
    """Connection: connection."""

    _fields_ = [("node_id", ctypes.c_uint32), ("distance", ctypes.c_float)]


def _find_zig_lib() -> str | None:
    """Locate the compiled Zig shared library."""
    base = (
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "polyglot"
        / "whitemagic-zig"
    )
    candidates = [
        os.environ.get("WM_ZIG_LIB", ""),
        str(base / "zig-out" / "lib" / "libwhitemagic.so"),
        str(base / "libwhitemagic.so"),
        str(base / "zig-out" / "lib" / "libwhitemagic.dylib"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _load_lib() -> Any:
    """Load the Zig shared library with HNSW functions."""
    global _lib, _HAS_HNSW
    if _lib is not None:
        return _lib

    path = _find_zig_lib()
    if not path:
        logger.debug("Zig HNSW library not found")
        return None

    try:
        lib = ctypes.CDLL(path)

        # wm_hnsw_create(dim, m, ef_construction, ef_search, max_elements) -> handle
        lib.wm_hnsw_create.argtypes = [
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        lib.wm_hnsw_create.restype = ctypes.c_void_p

        # wm_hnsw_free(handle)
        lib.wm_hnsw_free.argtypes = [ctypes.c_void_p]
        lib.wm_hnsw_free.restype = None

        # wm_hnsw_add(handle, vector_ptr) -> node_id
        lib.wm_hnsw_add.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)]
        lib.wm_hnsw_add.restype = ctypes.c_ssize_t

        # wm_hnsw_search(handle, query_ptr, k, results_ptr) -> count
        lib.wm_hnsw_search.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
            ctypes.POINTER(Connection),
        ]
        lib.wm_hnsw_search.restype = ctypes.c_size_t

        # wm_hnsw_count(handle) -> count
        lib.wm_hnsw_count.argtypes = [ctypes.c_void_p]
        lib.wm_hnsw_count.restype = ctypes.c_size_t

        # wm_hnsw_max_level(handle) -> level
        lib.wm_hnsw_max_level.argtypes = [ctypes.c_void_p]
        lib.wm_hnsw_max_level.restype = ctypes.c_size_t

        _lib = lib
        _HAS_HNSW = True
        logger.info("Zig HNSW loaded: path=%s", path)
        return lib
    except Exception as e:
        logger.debug("Failed to load Zig HNSW library: %s", e)
        return None


class HnswIndex:
    """HNSW index for approximate nearest neighbor search.

    Args:
        dim: Vector dimensionality
        m: Max connections per layer (default 16)
        ef_construction: Construction-time search width (default 200)
        ef_search: Query-time search width (default 50)
        max_elements: Maximum number of vectors (default 10000)
    """

    def __init__(
        self,
        dim: int = 384,
        m: int = 16,
        ef_construction: int = 200,
        ef_search: int = 50,
        max_elements: int = 10000,
    ):
        self.dim = dim
        self.m = m
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.max_elements = max_elements
        self._handle = None

        lib = _load_lib()
        if lib is not None:
            self._handle = lib.wm_hnsw_create(
                dim, m, ef_construction, ef_search, max_elements
            )
            if self._handle is None:
                raise RuntimeError("Failed to create HNSW index")

    def __del__(self):
        if self._handle is not None:
            lib = _load_lib()
            if lib is not None:
                lib.wm_hnsw_free(self._handle)

    def add(self, vector: np.ndarray | list[float]) -> int:
        """Add a vector to the index.

        Returns:
            Node ID of the added vector, or -1 on failure.
        """
        if self._handle is None:
            return -1

        lib = _load_lib()
        if lib is None:
            return -1

        if isinstance(vector, np.ndarray):
            vec_ptr = to_ptr(vector.astype(np.float32))
        else:
            vec_np = np.array(vector, dtype=np.float32)
            vec_ptr = to_ptr(vec_np)

        return int(lib.wm_hnsw_add(self._handle, vec_ptr))

    def search(
        self, query: np.ndarray | list[float], k: int = 10
    ) -> list[tuple[int, float]]:
        """Search for k nearest neighbors.

        Returns:
            List of (node_id, distance) tuples sorted by distance.
        """
        if self._handle is None:
            return []

        lib = _load_lib()
        if lib is None:
            return []

        if isinstance(query, np.ndarray):
            q_ptr = to_ptr(query.astype(np.float32))
        else:
            q_np = np.array(query, dtype=np.float32)
            q_ptr = to_ptr(q_np)

        results = (Connection * k)()
        count = lib.wm_hnsw_search(self._handle, q_ptr, k, results)

        return [
            (int(results[i].node_id), float(results[i].distance)) for i in range(count)
        ]

    @property
    def count(self) -> int:
        """Number of vectors in the index."""
        if self._handle is None:
            return 0
        lib = _load_lib()
        if lib is None:
            return 0
        return int(lib.wm_hnsw_count(self._handle))

    @property
    def max_level(self) -> int:
        """Maximum layer level in the graph."""
        if self._handle is None:
            return 0
        lib = _load_lib()
        if lib is None:
            return 0
        return int(lib.wm_hnsw_max_level(self._handle))

    def status(self) -> dict[str, Any]:
        """Get HNSW index status."""
        return {
            "has_hnsw": _HAS_HNSW,
            "dim": self.dim,
            "m": self.m,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "count": self.count,
            "max_level": self.max_level,
            "backend": "zig_hnsw" if _HAS_HNSW else "unavailable",
        }
