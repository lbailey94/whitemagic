"""Mesh module — distributed WhiteMagic node coordination.

Provides gRPC mesh client, Redis-based peer awareness, and Go libp2p bridge.
"""

from __future__ import annotations

from .awareness import MeshAwareness, get_mesh_awareness
from .client import MeshClient, MeshPeer, SignalResult, get_mesh_client

__all__ = [
    "MeshAwareness",
    "MeshClient",
    "MeshPeer",
    "SignalResult",
    "get_mesh_awareness",
    "get_mesh_client",
]
