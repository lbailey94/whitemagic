"""Julia bridge — scientific computing core via PyJulia.

Provides Python access to whitemagic-jl scientific computing modules.
Gracefully degrades when Julia or PyJulia is not available.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_jl = None
_HAS_JULIA = False


def _init_julia() -> Any:
    """Initialize Julia runtime via PyJulia."""
    global _jl, _HAS_JULIA
    if _jl is not None:
        return _jl
    try:
        from julia import Main
        jl_project = Path(__file__).resolve().parent.parent.parent.parent / "polyglot" / "whitemagic-jl"
        Main.eval(f'using Pkg; Pkg.activate("{jl_project}")')
        Main.eval("using WhiteMagicSpatial")
        _jl = Main
        _HAS_JULIA = True
        logger.info("Julia scientific computing core initialized")
        return _jl
    except ImportError:
        logger.debug("PyJulia not installed — Julia bridge unavailable")
        return None
    except Exception as e:
        logger.debug("Failed to initialize Julia: %s", e)
        return None


def jl_batch_cosine(query: list[float], corpus: list[list[float]]) -> list[float] | None:
    """Compute batch cosine similarity via Julia."""
    jl = _init_julia()
    if jl is None:
        return None
    try:
        result = jl.WhiteMagicSpatial.batch_cosine(query, corpus)
        return list(result)
    except Exception as e:
        logger.debug("Julia batch_cosine failed: %s", e)
        return None


def jl_spatial_status() -> dict[str, Any]:
    """Get Julia scientific computing core status."""
    jl = _init_julia()
    return {
        "has_julia": _HAS_JULIA,
        "backend": "julia_pyjulia" if _HAS_JULIA else "unavailable",
        "note": "Install PyJulia and Julia to enable scientific computing bridge",
    }
