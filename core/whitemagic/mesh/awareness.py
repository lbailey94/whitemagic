"""
Cross-Node Mesh Awareness — Redis ↔ Python Peer Tracking
==========================================================
Listens on the Redis ``ganying`` channel for mesh peer events from the
Go libp2p node.  Maintains a live peer registry and exposes it via
MCP tools ``mesh.status`` and ``mesh.broadcast``.

The Go mesh node publishes events like::

    {"type": "PEER_DISCOVERED", "node_id": "...", "address": "..."}
    {"type": "HOLOGRAM_RECEIVED", "id": "...", "coordinates": [...]}

This module bridges those into the Python Gan Ying bus and the
MeshClient's peer registry.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


class MeshAwareness:
    """
    Watches Redis for mesh events and maintains peer awareness.
    Integrates with the existing MeshClient and Gan Ying bus.
    """

    def __init__(self) -> None:
        self._peers: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._mesh_events: list[dict[str, Any]] = []
        self._max_events = 200
        self._listening = False

    def register_peer(
        self, node_id: str, address: str = "", meta: dict | None = None
    ) -> None:
        """
        Register a peer.

        Args:
            node_id: Parameter description.
            address: Parameter description.
            meta: Parameter description.

        Returns:
            None
        """
        with self._lock:
            self._peers[node_id] = {
                "node_id": node_id,
                "address": address,
                "last_seen": time.time(),
                "meta": meta or {},
            }

    def remove_peer(self, node_id: str) -> None:
        """
        Remove the peer.

        Args:
            node_id: Parameter description.

        Returns:
            None
        """
        with self._lock:
            self._peers.pop(node_id, None)

    def get_peers(self) -> list[dict[str, Any]]:
        """
        Get the peers.

        Returns:
            list[dict[str, Any]]
        """
        with self._lock:
            return list(self._peers.values())

    def record_event(self, event: dict[str, Any]) -> None:
        """
        Perform the record event operation.

        Args:
            event: Parameter description.

        Returns:
            None
        """
        with self._lock:
            self._mesh_events.append({**event, "_received_at": time.time()})
            if len(self._mesh_events) > self._max_events:
                self._mesh_events = self._mesh_events[-self._max_events :]

    def process_redis_message(self, data: str) -> None:
        """Process a message from the Redis ganying channel for mesh events."""
        try:
            msg = _json_loads(data) if isinstance(data, str) else data
        except (ValueError, TypeError):
            return

        msg_type = msg.get("type", msg.get("signal_type", ""))

        if msg_type in ("PEER_DISCOVERED", "peer_discovered"):
            self.register_peer(
                node_id=msg.get("node_id", msg.get("source_id", "unknown")),
                address=msg.get("address", ""),
                meta=msg.get("meta", {}),
            )
            self.record_event(msg)

        elif msg_type in ("PEER_LEFT", "peer_left"):
            self.remove_peer(msg.get("node_id", ""))
            self.record_event(msg)

        elif msg_type in ("HOLOGRAM_RECEIVED", "hologram_broadcast"):
            self.record_event(msg)
            # Forward to mesh client
            try:
                from whitemagic.mesh.client import get_mesh_client

                get_mesh_client()
                coords = msg.get("coordinates", [])
                if coords and msg.get("source_node"):
                    self.register_peer(
                        msg["source_node"], meta={"last_hologram": time.time()}
                    )
            except (ImportError, ModuleNotFoundError) as e:
                import logging

                logging.getLogger(__name__).debug("Exception silenced: %s", e)

    def status(self) -> dict[str, Any]:
        """Full mesh awareness status."""
        try:
            from whitemagic.mesh.client import get_mesh_client

            client = get_mesh_client()
            client_status = client.status()
        except (ImportError, ModuleNotFoundError):
            client_status = {"connected": False}

        with self._lock:
            return {
                "status": "success",
                "client": client_status,
                "peers": list(self._peers.values()),
                "peer_count": len(self._peers),
                "recent_events": len(self._mesh_events),
                "listening": self._listening,
            }


# Singleton
_awareness: MeshAwareness | None = None
_awareness_lock = threading.Lock()


def get_mesh_awareness() -> MeshAwareness:
    """
    Get the mesh awareness.

    Returns:
        MeshAwareness
    """
    global _awareness
    if _awareness is None:
        with _awareness_lock:
            if _awareness is None:
                _awareness = MeshAwareness()
    return _awareness
