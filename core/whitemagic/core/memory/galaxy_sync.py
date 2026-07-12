# ruff: noqa: BLE001
"""Galaxy sync — real-time multi-user galaxy synchronization via Redis.

Publishes galaxy lifecycle events (create, delete, switch, ingest) on
user-scoped Redis channels so distributed instances can stay in sync.

Channel naming:
    galaxy:<user_id>           — all galaxy events for a user
    galaxy:<user_id>:<name>    — events for a specific galaxy

Event types:
    galaxy.created
    galaxy.deleted
    galaxy.switched
    galaxy.ingested

Falls back gracefully when Redis is unavailable.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _is_sync_enabled() -> bool:
    """Check if galaxy sync is enabled (Redis must be available)."""
    if os.environ.get("WM_SILENT_INIT") == "1":
        return False
    from whitemagic.tools.handlers.broker import _resolve_redis_url
    redis_url = _resolve_redis_url()
    if redis_url:
        return True
    import socket
    try:
        socket.create_connection(("localhost", 6379), timeout=0.5).close()
        return True
    except OSError:
        return False


def _galaxy_channel(user_id: str, galaxy_name: str | None = None) -> str:
    """Build a Redis channel name for galaxy sync events."""
    if galaxy_name:
        return f"galaxy:{user_id}:{galaxy_name}"
    return f"galaxy:{user_id}"


def publish_galaxy_event(
    event_type: str,
    user_id: str,
    galaxy_name: str,
    data: dict[str, Any] | None = None,
) -> bool:
    """Publish a galaxy sync event to Redis.

    Args:
        event_type: One of galaxy.created, galaxy.deleted, galaxy.switched, galaxy.ingested
        user_id: The user ID whose galaxy changed
        galaxy_name: The galaxy name that changed
        data: Optional additional event data

    Returns:
        True if published, False if Redis unavailable or error.
    """
    if not _is_sync_enabled():
        return False

    try:
        from whitemagic.tools.handlers.broker import _get_broker, _run

        channel = _galaxy_channel(user_id, galaxy_name)
        message = {
            "event_type": event_type,
            "user_id": user_id,
            "galaxy_name": galaxy_name,
            "data": data or {},
        }

        async def _do() -> str:
            broker = await _get_broker()
            return await broker.publish(channel, message)

        coro = _do()
        try:
            _run(coro)
        except Exception:
            coro.close()
            raise
        logger.debug("Published %s on %s", event_type, channel)
        return True
    except Exception as e:
        logger.debug("Galaxy sync publish failed: %s", e, exc_info=True)
        return False


def start_galaxy_sync_listener(
    user_id: str,
    galaxy_name: str | None = None,
    callback: Any | None = None,
) -> Any | None:
    """Start listening for galaxy sync events on Redis.

    Args:
        user_id: The user ID to listen for
        galaxy_name: Optional specific galaxy to listen for
        callback: Optional async callback called with each event dict

    Returns:
        The pubsub object if subscription succeeded, None otherwise.
    """
    if not _is_sync_enabled():
        return None

    try:
        from whitemagic.tools.handlers.broker import _get_broker, _run

        channel = _galaxy_channel(user_id, galaxy_name)

        async def _do() -> Any:
            broker = await _get_broker()
            return await broker.subscribe(channel)

        pubsub = _run(_do())
        logger.info("Subscribed to galaxy sync channel: %s", channel)
        return pubsub
    except Exception as e:
        logger.debug("Galaxy sync subscribe failed: %s", e, exc_info=True)
        return None


def stop_galaxy_sync_listener(user_id: str, galaxy_name: str | None = None) -> bool:
    """Stop listening for galaxy sync events.

    Args:
        user_id: The user ID to stop listening for
        galaxy_name: Optional specific galaxy channel to unsubscribe

    Returns:
        True if unsubscribed, False if Redis unavailable or error.
    """
    if not _is_sync_enabled():
        return False

    try:
        from whitemagic.tools.handlers.broker import _get_broker, _run

        channel = _galaxy_channel(user_id, galaxy_name)

        async def _do() -> None:
            broker = await _get_broker()
            await broker.unsubscribe(channel)

        _run(_do())
        logger.info("Unsubscribed from galaxy sync channel: %s", channel)
        return True
    except Exception as e:
        logger.debug("Galaxy sync unsubscribe failed: %s", e, exc_info=True)
        return False


def merge_remote_memory(remote_memory_data: dict[str, Any]) -> dict[str, Any]:
    """Merge a remote memory update using CRDT Last-Writer-Wins resolution.

    Called when a galaxy sync event delivers a remote memory update.
    Uses UnifiedMemory._lww_resolve() to pick the winning version.

    Args:
        remote_memory_data: Dict with memory fields (id, content, version, agent_id, etc.)

    Returns:
        Dict with merge result: success, winner (local/remote), memory_id.
    """
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        from whitemagic.core.memory.unified_types import Memory, MemoryType

        memory_id = remote_memory_data.get("id", "")
        if not memory_id:
            return {"success": False, "error": "missing memory id"}

        um = get_unified_memory()
        local = um.recall(memory_id)

        # Reconstruct remote Memory from dict
        mem_type_str = remote_memory_data.get("memory_type", "SHORT_TERM")
        try:
            mem_type = MemoryType(mem_type_str)
        except ValueError:
            mem_type = MemoryType.SHORT_TERM

        remote = Memory(
            id=memory_id,
            content=remote_memory_data.get("content", ""),
            memory_type=mem_type,
            version=remote_memory_data.get("version", 0),
            agent_id=remote_memory_data.get("agent_id", ""),
        )

        if local is None:
            # No local copy — store remote directly
            um.store(
                content=remote.content,
                memory_type=remote.memory_type,
                galaxy=remote_memory_data.get("galaxy", "universal"),
                agent_id=remote.agent_id,
            )
            return {"success": True, "winner": "remote (no local)", "memory_id": memory_id}

        winner = um._lww_resolve(local, remote)
        won_by = "local" if winner is local else "remote"

        if winner is remote:
            # Apply remote update locally
            um.update_memory(memory_id, {"content": remote.content}, agent_id=remote.agent_id)

        return {"success": True, "winner": won_by, "memory_id": memory_id}
    except Exception as e:
        logger.debug("merge_remote_memory failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}
