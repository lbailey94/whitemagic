# ruff: noqa: BLE001
"""Performance — Optimization infrastructure with Rust/Haskell bridges."""

from __future__ import annotations

from .bridge_coordinator import BridgeCoordinator, get_bridge_coordinator
from .rust_embeddings import RustEmbeddingsBridge, get_rust_embeddings

__all__ = [
    "RustEmbeddingsBridge",
    "get_rust_embeddings",
    "BridgeCoordinator",
    "get_bridge_coordinator",
]
