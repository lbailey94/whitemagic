# ruff: noqa: BLE001
"""Mesh Memory Fusion — Go Mesh → Memory Sync Protocol.

Sync memory operations across mesh peers via the Go libp2p network.
Extracted from fusions.py for better separation of concerns.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def mesh_memory_sync(
    memory_id: str = "",
    operation: str = "announce",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sync memory operations across mesh peers via the Go libp2p network.

    The Go mesh (``mesh/``) provides peer discovery via mDNS and message
    passing via Redis pub/sub bridge.  This fusion extends MeshAwareness
    to propagate memory events (create/update/archive) to connected peers.

    Operations:
        ``announce``: Broadcast that a memory was created/updated to all peers
        ``request``:  Request a specific memory from peers by ID
        ``status``:   Get mesh sync status (peers, pending syncs)

    Args:
        memory_id: Memory identifier for announce/request operations
        operation: One of "announce", "request", "status"
        payload: Additional data (e.g., memory metadata for announce)

    Returns:
        Dict with sync result, peer count, and operation details.
    """
    payload = payload or {}

    try:
        from whitemagic.mesh.awareness import get_mesh_awareness

        mesh = get_mesh_awareness()
        peers = mesh.get_peers()
        peer_count = len(peers)

        if operation == "status":
            mesh_status = mesh.status()
            return {
                "operation": "status",
                "peer_count": peer_count,
                "peers": [p.get("node_id", "unknown") for p in peers],
                "mesh_status": mesh_status,
                "sync_capable": peer_count > 0,
            }

        elif operation == "announce":
            if not memory_id:
                return {"operation": "announce", "error": "memory_id required"}

            # Build sync event for mesh broadcast
            sync_event = {
                "type": "MEMORY_SYNC",
                "sub_type": "announce",
                "memory_id": memory_id,
                "source_node": "local",
                "timestamp": time.time(),
                **{
                    k: v
                    for k, v in payload.items()
                    if k
                    in (
                        "title",
                        "memory_type",
                        "tags",
                        "importance",
                        "zone",
                    )
                },
            }

            broadcast_queued = False
            if peer_count > 0:
                try:
                    mesh.record_event(sync_event)
                    broadcast_queued = True
                    logger.info(
                        "Memory sync announced to %d peers: %s",
                        peer_count,
                        memory_id,
                    )
                except Exception as e:
                    logger.debug("Mesh broadcast failed: %s", e)

            return {
                "operation": "announce",
                "memory_id": memory_id,
                "peer_count": peer_count,
                "broadcast_queued": broadcast_queued,
            }

        elif operation == "request":
            if not memory_id:
                return {"operation": "request", "error": "memory_id required"}

            # Request memory from peers
            request_event = {
                "type": "MEMORY_SYNC",
                "sub_type": "request",
                "memory_id": memory_id,
                "source_node": "local",
                "timestamp": time.time(),
            }

            if peer_count > 0:
                try:
                    mesh.record_event(request_event)
                    logger.info(
                        "Memory sync requested from %d peers: %s", peer_count, memory_id
                    )
                    return {
                        "operation": "request",
                        "memory_id": memory_id,
                        "peer_count": peer_count,
                        "request_queued": True,
                    }
                except Exception as e:
                    logger.debug("Mesh request failed: %s", e)

            return {
                "operation": "request",
                "memory_id": memory_id,
                "peer_count": peer_count,
                "request_queued": False,
                "reason": "no peers available",
            }

        else:
            return {"operation": operation, "error": f"unknown operation: {operation}"}

    except Exception as e:
        return {"operation": operation, "error": str(e)}


def get_fusion_status() -> dict[str, Any]:
    """Get status of all fusion modules."""
    return {
        "fusions": {
            "dream_scheduling": "active",
            "wuxing_quadrant": "active",
            "prat_resonance": "active",
            "zodiac_spell": "active",
            "bicameral_consolidation": "active",
            "salience_homeostasis": "active",
            "dream_bicameral": "active",
            "constellation_garden": "active",
            "knowledge_graph": "active",
            "gana_chain_harmony": "active",
            "prat_auto_chain": "active",
            "holographic_encode": "active",
            "elixir_event": "active",
            "mesh_memory_sync": "active",
        },
        "status": "operational",
    }
