"""
Local ML (Archived)
===================

This package used to embed local model execution (BitNet/Ollama/etc) directly
inside Whitemagic.

Whitemagic's current direction is to be model-agnostic and expose capabilities
via MCP/REST so *external* models (local or cloud) can use it as a cognitive and
memory substrate.

The implementation has been archived and is no longer available.
"""

from __future__ import annotations

from typing import Any


def _disabled_error() -> RuntimeError:
    return RuntimeError(
        "Local model execution is archived and no longer available."
    )


def get_model_info() -> dict[str, object]:
    """
    Get the model info.

    Returns:
        dict[str, object]
    """
    raise _disabled_error()


def get_local_ml_engine() -> Any:
    """
    Get the local ml engine.

    Returns:
        Any
    """
    raise _disabled_error()


def get_engine() -> Any:
    """
    Get the engine.

    Returns:
        Any
    """
    raise _disabled_error()


__all__ = [
    "get_model_info",
    "get_local_ml_engine",
    "get_engine",
]
