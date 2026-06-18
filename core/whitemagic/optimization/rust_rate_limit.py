# ruff: noqa: BLE001
"""Rust Atomic Rate Limiter Bridge.

Extracted from rust_accelerators.py for better separation of concerns.
Provides atomic sliding window rate limiting with Rust acceleration.
"""

import logging
from typing import Any

from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust availability check
# ---------------------------------------------------------------------------

_RUST_RATE_LIMITER = False
_rs: Any = None

try:
    import whitemagic_rust as _rs_mod
    _rs = _rs_mod
except ImportError:
    try:
        import whitemagic_rs as _rs_mod
        _rs = _rs_mod
    except ImportError:
        pass

if _rs is not None and hasattr(_rs, "rate_check"):
    _RUST_RATE_LIMITER = True
    logger.debug("Rust atomic rate limiter available")


def rust_rate_limiter_available() -> bool:
    """Check if Rust atomic rate limiter is available."""
    return _RUST_RATE_LIMITER


def rate_check(tool_name: str) -> dict[str, Any] | None:
    """Check rate limit for a tool using Rust atomic sliding windows.

    Returns:
        Dict with {allowed: bool, retry_after_ms: int|None} or None.

    """
    if not _RUST_RATE_LIMITER:
        return None
    try:
        # v14: Native tuple return — no JSON serialization
        if hasattr(_rs, "rate_check_native"):
            allowed, retry_ms = _rs.rate_check_native(tool_name)
            return {"allowed": allowed, "retry_after_ms": retry_ms}
        # Fallback to JSON path
        result_json = _rs.rate_check(tool_name)
        parsed: dict[str, Any] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust rate_check failed: {e}")
        return None


def rate_set_override(tool_name: str, rpm: int) -> bool:
    """Set a per-tool RPM override in the Rust rate limiter.

    Returns:
        True if set successfully, False otherwise.

    """
    if not _RUST_RATE_LIMITER:
        return False
    try:
        _rs.rate_set_override(tool_name, rpm)
        return True
    except Exception as e:
        logger.debug(f"Rust rate_set_override failed: {e}")
        return False


def rate_stats() -> dict[str, Any] | None:
    """Get rate limiter statistics from Rust.

    Returns:
        Dict with stats per tool and global, or None.

    """
    if not _RUST_RATE_LIMITER:
        return None
    try:
        # v14: Native dict return — no JSON serialization
        if hasattr(_rs, "rate_stats_native"):
            native_stats = _rs.rate_stats_native()
            if isinstance(native_stats, dict):
                return native_stats
        # Fallback to JSON path
        result_json = _rs.rate_stats()
        parsed: dict[str, Any] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust rate_stats failed: {e}")
        return None


def rate_check_batch(tool_names: list[str]) -> list[dict[str, Any]] | None:
    """Batch check rate limits for N tools in a single FFI call.

    Amortizes Python→Rust crossing overhead: N checks for the cost of 1
    FFI round-trip. At 2-3μs per check, a batch of 100 tools completes
    in ~5μs total vs ~300μs for 100 individual calls.

    Returns:
        List of {tool, allowed, retry_after_ms} dicts, or None.

    """
    if not _RUST_RATE_LIMITER:
        return None
    try:
        # v14: Native tuple-list return — no JSON serialization
        if hasattr(_rs, "rate_check_batch_native"):
            results = _rs.rate_check_batch_native(tool_names)
            return [
                {"tool": tool, "allowed": allowed, "retry_after_ms": retry_ms}
                for tool, allowed, retry_ms in results
            ]
        # Fallback to JSON path
        if not hasattr(_rs, "rate_check_batch"):
            return None
        result_json = _rs.rate_check_batch(tool_names)
        parsed: list[dict[str, Any]] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust rate_check_batch failed: {e}")
        return None
