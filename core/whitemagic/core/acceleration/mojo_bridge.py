# ruff: noqa: BLE001
"""Mojo Accelerator Bridge — Stub (Mojo removed in v23.2).
========================================================
Previously bridged to compiled Mojo executables for batch encoding,
embedding quantization, and neuro scoring. All functions now return
graceful fallback responses for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_HAS_MOJO = False


def mojo_batch_encode(
    memories: list[dict[str, Any]],
) -> list[tuple[float, float, float, float, float]] | None:
    """Batch encode memories — returns None (Mojo removed in v23.2)."""
    return None


def mojo_neuro_score(
    memories: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Neuro score memories — returns None (Mojo removed in v23.2)."""
    return None


def mojo_quantize(
    vectors: list[list[float]],
    mode: str = "int8",
) -> dict[str, Any] | None:
    """Quantize vectors — returns None (Mojo removed in v23.2)."""
    return None


def mojo_status() -> dict[str, Any]:
    """Get Mojo bridge status — always unavailable."""
    return {
        "has_mojo": False,
        "mojo_bin": "not found",
        "mojo_dir": "not found",
        "modules": {},
        "backend": "python_fallback",
    }
