"""Haskell bridge — functional spatial core via ctypes FFI.

Provides Python access to whitemagic-hs compiled shared library.
Gracefully degrades when the Haskell library is not built.

Note: Due to GHC RTS circular dependencies (RTS ↔ ghc-prim), the Haskell
library requires LD_PRELOAD to be set before Python starts. Use the helper
script or set environment variables manually:

    export LD_LIBRARY_PATH=/path/to/ghc/lib/x86_64-linux-ghc-9.6.6
    export LD_PRELOAD=$LD_LIBRARY_PATH/libHSrts-1.0.2-ghc9.6.6.so:$LD_LIBRARY_PATH/libHSghc-prim-0.10.0-ghc9.6.6.so:$LD_LIBRARY_PATH/libHSbase-4.18.2.1-ghc9.6.6.so
    python your_script.py

Override paths via environment:

    WM_GHC_LIB_DIR — GHC library directory (e.g. output of `ghc --print-libdir`)
    WM_HS_LIB      — Full path to libwhitemagic_hs.so
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lib: Any = None
_HAS_HS = False


def _resolve_ghc_lib_dir() -> str:
    """Resolve GHC library directory via env var or ghc --print-libdir."""
    env_dir = os.environ.get("WM_GHC_LIB_DIR", "")
    if env_dir:
        return env_dir
    try:
        result = subprocess.run(
            ["ghc", "--print-libdir"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


_GHC_LIB_DIR = _resolve_ghc_lib_dir()
_HS_LIB_PATH = os.environ.get("WM_HS_LIB", "")

# Core GHC libraries needed for RTS initialization
_GHC_CORE_LIBS = [
    "libHSrts-1.0.2-ghc9.6.6.so",
    "libHSghc-prim-0.10.0-ghc9.6.6.so",
    "libHSbase-4.18.2.1-ghc9.6.6.so",
    "libHSbytestring-0.11.5.3-ghc9.6.6.so",
    "libHSarray-0.5.6.0-ghc9.6.6.so",
    "libHScontainers-0.6.7-ghc9.6.6.so",
    "libHStext-2.0.2-ghc9.6.6.so",
    "libHSinteger-gmp-1.1-ghc9.6.6.so",
    "libHStransformers-0.6.1.0-ghc9.6.6.so",
    "libHSdeepseq-1.4.8.1-ghc9.6.6.so",
    "libHSfilepath-1.4.300.1-ghc9.6.6.so",
    "libHSdirectory-1.3.8.5-ghc9.6.6.so",
    "libHSexceptions-0.10.7-ghc9.6.6.so",
]


def _setup_ghc_environment() -> None:
    """Set up LD_LIBRARY_PATH for GHC libraries."""
    if not os.path.isdir(_GHC_LIB_DIR):
        return

    current_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if _GHC_LIB_DIR not in current_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{_GHC_LIB_DIR}:{current_ld}" if current_ld else _GHC_LIB_DIR


def _check_preload() -> bool:
    """Check if LD_PRELOAD is set with GHC libraries."""
    preload = os.environ.get("LD_PRELOAD", "")
    return "libHSrts" in preload and "libHSghc-prim" in preload


def _find_hs_lib() -> str | None:
    """Locate the compiled Haskell shared library."""
    candidates = [
        os.environ.get("WM_HS_LIB", ""),
        _HS_LIB_PATH,
        str(Path(__file__).resolve().parent.parent.parent.parent.parent / "polyglot" / "whitemagic-hs" / "libwhitemagic_hs.so"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _load_lib() -> Any:
    """Load the Haskell shared library with proper RTS initialization."""
    global _lib, _HAS_HS
    if _lib is not None:
        return _lib

    path = _find_hs_lib()
    if not path:
        logger.debug("Haskell library not found — spatial core unavailable")
        return None

    # Set up LD_LIBRARY_PATH
    _setup_ghc_environment()

    # Check if LD_PRELOAD is set
    if not _check_preload():
        logger.debug(
            "Haskell library requires LD_PRELOAD with GHC RTS. "
            "Set LD_PRELOAD before starting Python, or use the helper script."
        )
        return None

    try:
        lib = ctypes.CDLL(path)
        _lib = lib
        _HAS_HS = True
        logger.info("Haskell spatial core loaded from %s", path)
        return lib
    except Exception as e:
        logger.debug("Failed to load Haskell library: %s", e)
        return None


def hs_cosine_similarity(a: list[float], b: list[float]) -> float | None:
    """Compute cosine similarity via Haskell FFI."""
    lib = _load_lib()
    if lib is None:
        return None
    # Full vector FFI requires CArray marshalling — stub for now
    logger.debug("Haskell cosine similarity: CArray marshalling not yet implemented")
    return None


def hs_create_hexagram(lines: list[int]) -> int | None:
    """Create a hexagram from 6 line values (0=Yin, 1=Yang) and return its number."""
    lib = _load_lib()
    if lib is None:
        return None
    if len(lines) != 6:
        raise ValueError(f"Expected 6 lines, got {len(lines)}")

    try:
        create_fn = lib.wm_c_create_hexagram
        create_fn.argtypes = [ctypes.c_int] * 6
        create_fn.restype = ctypes.c_void_p

        num_fn = lib.wm_c_hexagram_to_number
        num_fn.argtypes = [ctypes.c_void_p]
        num_fn.restype = ctypes.c_int

        free_fn = lib.wm_c_free_hexagram
        free_fn.argtypes = [ctypes.c_void_p]

        hex_ptr = create_fn(*lines)
        if hex_ptr is None:
            return None
        num = num_fn(hex_ptr)
        free_fn(hex_ptr)
        return int(num)
    except Exception as e:
        logger.debug("Haskell hexagram creation failed: %s", e)
        return None


def hs_create_hexagrams_batch(lines_list: list[list[int]]) -> list[int] | None:
    """Batch create hexagrams from N lists of 6 line values.

    Uses wm_c_create_hexagrams_batch for single FFI call,
    avoiding N separate calls with individual malloc/free overhead.

    Args:
        lines_list: List of hexagram line lists, each with 6 integers (0 or 1).

    Returns:
        List of hexagram numbers (1-64), or None if Haskell unavailable.
    """
    lib = _load_lib()
    if lib is None:
        return None

    n = len(lines_list)
    if n == 0:
        return []

    # Validate all inputs
    for i, lines in enumerate(lines_list):
        if len(lines) != 6:
            raise ValueError(f"Hexagram {i}: expected 6 lines, got {len(lines)}")

    try:
        # Flatten all lines into contiguous array
        flat_lines = (ctypes.c_int * (n * 6))()
        for i, lines in enumerate(lines_list):
            for j, val in enumerate(lines):
                flat_lines[i * 6 + j] = val

        # Array of hexagram pointers
        hex_ptrs = (ctypes.c_void_p * n)()

        # Batch create
        create_fn = lib.wm_c_create_hexagrams_batch
        create_fn.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        create_fn.restype = ctypes.c_int
        created = create_fn(flat_lines, n, hex_ptrs)

        if created != n:
            logger.warning("Haskell batch hexagram: expected %d, got %d", n, created)

        # Batch get numbers
        numbers = (ctypes.c_int * n)()
        nums_fn = lib.wm_c_hexagrams_to_numbers_batch
        nums_fn.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        nums_fn.restype = None
        nums_fn(hex_ptrs, n, numbers)

        # Batch free
        free_fn = lib.wm_c_free_hexagrams_batch
        free_fn.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int,
        ]
        free_fn.restype = None
        free_fn(hex_ptrs, n)

        return [int(numbers[i]) for i in range(n)]
    except Exception as e:
        logger.debug("Haskell batch hexagram creation failed: %s", e)
        return None


def hs_spatial_status() -> dict[str, Any]:
    """Get Haskell spatial core status."""
    _load_lib()
    return {
        "has_haskell": _HAS_HS,
        "lib_path": _find_hs_lib() or "not found",
        "backend": "haskell_ffi" if _HAS_HS else "unavailable",
        "ghc_lib_dir": _GHC_LIB_DIR if os.path.isdir(_GHC_LIB_DIR) else "not found",
        "preload_set": _check_preload(),
    }
