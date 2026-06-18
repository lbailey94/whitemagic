# ruff: noqa: BLE001
"""Rust Tokio Clone Army & IPC Bridge.

Extracted from rust_accelerators.py for better separation of concerns.
Provides massively parallel exploration via Tokio async runtime and
Iceoryx2 shared memory IPC bridge with Rust acceleration.
"""

import logging
from typing import Any, cast

from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust availability check
# ---------------------------------------------------------------------------

_RUST_TOKIO_CLONES = False
_RUST_IPC = False
_rs: Any = None
_ipc_bridge: Any = None  # submodule reference (may be nested or flat)

try:
    import whitemagic_rust as _rs_mod
    _rs = _rs_mod
except ImportError:
    try:
        import whitemagic_rs as _rs_mod
        _rs = _rs_mod
    except ImportError:
        pass

# Detect IPC bridge — supports both flat (legacy) and nested (current) layouts
if _rs is not None:
    if hasattr(_rs, "tokio_deploy_clones"):
        _RUST_TOKIO_CLONES = True
        logger.debug("Rust Tokio Clone Army available")
    if hasattr(_rs, "ipc_bridge") and hasattr(_rs.ipc_bridge, "ipc_bridge_status"):
        _ipc_bridge = _rs.ipc_bridge
        _RUST_IPC = True
    elif hasattr(_rs, "ipc_bridge_status"):
        # Legacy flat layout (older builds)
        _ipc_bridge = _rs
        _RUST_IPC = True

if _RUST_IPC:
    logger.debug("Rust IPC bridge available")


# ---------------------------------------------------------------------------
# Tokio Clone Army (massively parallel exploration)
# ---------------------------------------------------------------------------

def tokio_clones_available() -> bool:
    """Check if Rust Tokio Clone Army is available."""
    return _RUST_TOKIO_CLONES


def tokio_deploy_clones(
    prompt: str,
    num_clones: int = 100,
    strategies: list[str] | None = None,
) -> dict[str, Any] | None:
    """Deploy a Rust tokio clone army for parallel exploration.

    Args:
        prompt: The exploration prompt.
        num_clones: Number of clones to deploy (1-100,000).
        strategies: List of strategy names. Default: mixed
            (direct, chain_of_thought, analytical, creative, synthesis).

    Returns:
        Dict with keys: winner, total_clones, strategy_votes,
        avg_confidence, total_tokens, elapsed_ms. Or None.
    """
    if not _RUST_TOKIO_CLONES:
        return None
    try:
        result_json = _rs.tokio_deploy_clones(prompt, num_clones, strategies or [])
        return cast(dict[str, Any], _json_loads(result_json))
    except Exception as e:
        logger.debug(f"Rust tokio_deploy_clones failed: {e}")
        return None


def tokio_clone_bench(num_clones: int = 1000) -> tuple[float, float] | None:
    """Benchmark: deploy N clones and return (elapsed_ms, clones_per_sec)."""
    if not _RUST_TOKIO_CLONES:
        return None
    try:
        return cast(tuple[float, float], _rs.tokio_clone_bench(num_clones))
    except Exception as e:
        logger.debug(f"Rust tokio_clone_bench failed: {e}")
        return None


def tokio_clone_stats() -> dict[str, Any] | None:
    """Get global Tokio clone army statistics."""
    if not _RUST_TOKIO_CLONES:
        return None
    try:
        return cast(dict[str, Any], _json_loads(_rs.tokio_clone_stats()))
    except Exception as e:
        logger.debug(f"Rust tokio_clone_stats failed: {e}")
        return None


# ---------------------------------------------------------------------------
# IPC Bridge (Iceoryx2 shared memory)
# ---------------------------------------------------------------------------

def ipc_available() -> bool:
    """Check if Rust IPC bridge is available."""
    return _RUST_IPC


def ipc_status() -> dict[str, Any] | None:
    """Get IPC bridge status (backend, channels, stats)."""
    if not _RUST_IPC:
        return None
    try:
        return cast(dict[str, Any], _json_loads(_ipc_bridge.ipc_bridge_status()))
    except Exception as e:
        logger.debug(f"Rust ipc_bridge_status failed: {e}")
        return None
