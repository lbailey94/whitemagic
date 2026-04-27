"""Haskell bridge — functional spatial core via ctypes FFI.

Provides Python access to whitemagic-hs compiled shared library.
Gracefully degrades when the Haskell library is not built.
"""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lib: Any = None
_HAS_HS = False


def _find_hs_lib() -> str | None:
    """Locate the compiled Haskell shared library."""
    base = Path(__file__).resolve().parent.parent / "whitemagic-hs"
    candidates = [
        os.environ.get("WM_HS_LIB", ""),
        str(base / "dist" / "newstyle" / "build" / "libwhitemagic_hs.so"),
        str(base / "libwhitemagic_hs.so"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _load_lib() -> Any:
    """Load the Haskell shared library."""
    global _lib, _HAS_HS
    if _lib is not None:
        return _lib
    path = _find_hs_lib()
    if not path:
        logger.debug("Haskell library not found — spatial core unavailable")
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


def hs_spatial_status() -> dict[str, Any]:
    """Get Haskell spatial core status."""
    lib = _load_lib()
    return {
        "has_haskell": _HAS_HS,
        "lib_path": _find_hs_lib() or "not found",
        "backend": "haskell_ffi" if _HAS_HS else "unavailable",
    }
