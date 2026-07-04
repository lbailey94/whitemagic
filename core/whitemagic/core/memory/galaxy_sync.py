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
