"""Rust Mining & Arrow IPC Bridge.

Extracted from rust_accelerators.py for better separation of concerns.
Provides galaxy pattern mining, geneseed codebase mining, and Arrow IPC
zero-copy columnar interchange with Rust acceleration.
"""

import logging
from typing import Any, cast

from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust availability check
# ---------------------------------------------------------------------------

_RUST_ARROW = False
_rs: Any = None
_arrow_bridge: Any = None  # submodule reference (may be nested or flat)

try:
    import whitemagic_rust as _rs_mod
    _rs = _rs_mod
except ImportError:
    try:
        import whitemagic_rs as _rs_mod
        _rs = _rs_mod
    except ImportError:
        pass

# Detect the Arrow bridge — supports both flat (legacy) and nested (current) layouts
if _rs is not None:
    if hasattr(_rs, "arrow_bridge") and hasattr(_rs.arrow_bridge, "arrow_encode_memories"):
        _arrow_bridge = _rs.arrow_bridge
        _RUST_ARROW = True
    elif hasattr(_rs, "arrow_encode_memories"):
        # Legacy flat layout (older builds)
        _arrow_bridge = _rs
        _RUST_ARROW = True

if _RUST_ARROW:
    logger.debug("Rust Arrow IPC bridge available")


def arrow_available() -> bool:
    """Check if Arrow IPC bridge is available."""
    return _RUST_ARROW


# ---------------------------------------------------------------------------
# Galaxy Pattern Miner (v15.10 - Phase 3 Recursive Evolution)
# ---------------------------------------------------------------------------

def mine_access_patterns(db_path: str, min_frequency: int) -> Any:
    """Mine access patterns from galaxy archive DB (Rust accelerated).

    Args:
        db_path: Path to SQLite database
        min_frequency: Minimum access count threshold

    Returns:
        List of AccessPattern objects
    """
    if _rs is not None and hasattr(_rs, "mine_access_patterns"):
        return _rs.mine_access_patterns(db_path, min_frequency)
    raise RuntimeError("Rust galaxy miner not available")


def mine_cache_candidates(db_path: str, min_access: int, min_importance: float) -> Any:
    """Mine cache candidate patterns from galaxy archive DB (Rust accelerated).

    Args:
        db_path: Path to SQLite database
        min_access: Minimum access count threshold
        min_importance: Minimum importance threshold

    Returns:
        List of AccessPattern objects
    """
    if _rs is not None and hasattr(_rs, "mine_cache_candidates"):
        return _rs.mine_cache_candidates(db_path, min_access, min_importance)
    raise RuntimeError("Rust galaxy miner not available")


def mine_semantic_clusters(db_path: str, min_cluster_size: int) -> Any:
    """Mine semantic clusters from galaxy archive DB (Rust accelerated).

    Args:
        db_path: Path to SQLite database
        min_cluster_size: Minimum memories per cluster

    Returns:
        List of SemanticCluster objects
    """
    if _rs is not None and hasattr(_rs, "mine_semantic_clusters"):
        return _rs.mine_semantic_clusters(db_path, min_cluster_size)
    raise RuntimeError("Rust galaxy miner not available")


def get_galaxy_stats(db_path: str) -> Any:
    """Get quick statistics from galaxy archive DB (Rust accelerated).

    Args:
        db_path: Path to SQLite database

    Returns:
        Dict with stats (total_memories, high_access_memories, etc.)
    """
    if _rs is not None and hasattr(_rs, "get_galaxy_stats"):
        return _rs.get_galaxy_stats(db_path)
    raise RuntimeError("Rust galaxy miner not available")


# ---------------------------------------------------------------------------
# Geneseed Codebase Vault Miner (v15.10 - Phase 3C)
# ---------------------------------------------------------------------------

def mine_geneseed_patterns(repo_path: str, min_confidence: float, max_commits: int) -> Any:
    """Mine optimization patterns from git repository history (Rust accelerated).

    Args:
        repo_path: Path to git repository
        min_confidence: Minimum confidence threshold (0.0-1.0)
        max_commits: Maximum commits to analyze

    Returns:
        List of OptimizationPattern objects
    """
    if _rs is not None and hasattr(_rs, "mine_geneseed_patterns"):
        return _rs.mine_geneseed_patterns(repo_path, min_confidence, max_commits)
    raise RuntimeError("Rust geneseed miner not available")


def get_geneseed_stats(repo_path: str) -> Any:
    """Get repository statistics (Rust accelerated).

    Args:
        repo_path: Path to git repository

    Returns:
        GeneseedStats object with commit counts and metrics
    """
    if _rs is not None and hasattr(_rs, "get_geneseed_stats"):
        return _rs.get_geneseed_stats(repo_path)
    raise RuntimeError("Rust geneseed miner not available")


# ---------------------------------------------------------------------------
# Arrow IPC Bridge (zero-copy columnar interchange)
# ---------------------------------------------------------------------------

def arrow_encode_memories(memories_json: str) -> bytes | None:
    """Encode memory JSON to Arrow IPC bytes (zero-copy columnar format).

    Input: JSON array of memory objects with fields:
        id, title, content, importance, memory_type, x, y, z, w, v, tags.
    Returns: Arrow IPC file bytes, or None if Rust/Arrow unavailable.
    """
    if not _RUST_ARROW:
        return None
    try:
        return cast(bytes, _arrow_bridge.arrow_encode_memories(memories_json))
    except Exception as e:
        logger.debug(f"Rust arrow_encode_memories failed: {e}")
        return None


def arrow_decode_memories(ipc_bytes: bytes) -> str | None:
    """Decode Arrow IPC bytes back to memory JSON string.

    Returns: JSON string of memory objects, or None if unavailable.
    """
    if not _RUST_ARROW:
        return None
    try:
        return cast(str, _arrow_bridge.arrow_decode_memories(ipc_bytes))
    except Exception as e:
        logger.debug(f"Rust arrow_decode_memories failed: {e}")
        return None


def arrow_schema_info() -> dict[str, Any] | None:
    """Get Arrow schema metadata as a dict."""
    if not _RUST_ARROW:
        return None
    try:
        return cast(dict[str, Any], _json_loads(_arrow_bridge.arrow_schema_info()))
    except Exception as e:
        logger.debug(f"Rust arrow_schema_info failed: {e}")
        return None


def arrow_roundtrip_bench(n: int = 1000) -> tuple[int, int, int] | None:
    """Benchmark: encode N memories to Arrow IPC and back.

    Returns (encode_ns, decode_ns, ipc_size_bytes), or None.
    """
    if not _RUST_ARROW:
        return None
    try:
        return cast(tuple[int, int, int], _arrow_bridge.arrow_roundtrip_bench(n))
    except Exception as e:
        logger.debug(f"Rust arrow_roundtrip_bench failed: {e}")
        return None
