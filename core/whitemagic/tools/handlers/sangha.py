"""Sangha coordination tool handlers (chat + locks)."""
from typing import Any, cast


def handle_sangha_chat_send(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a sangha chat send event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.collaboration import sangha_chat_send
    return cast("dict[str, Any]", sangha_chat_send(**kwargs))


def handle_sangha_chat_read(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a sangha chat read event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.collaboration import sangha_chat_read
    return cast("dict[str, Any]", sangha_chat_read(**kwargs))


def handle_sangha_lock(**kwargs: Any) -> dict[str, Any]:
    """Unified sangha lock handler — routes by action parameter."""
    action = kwargs.get("action", "list")
    dispatch = {
        "acquire": handle_sangha_lock_acquire,
        "release": handle_sangha_lock_release,
        "list": handle_sangha_lock_list,
    }
    handler = dispatch.get(action)
    if not handler:
        return {"status": "error", "message": f"Unknown action '{action}'. Valid: {sorted(dispatch.keys())}"}
    return handler(**kwargs)


def handle_sangha_lock_acquire(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a sangha lock acquire event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.collaboration import sangha_lock_acquire
    return cast("dict[str, Any]", sangha_lock_acquire(**kwargs))


def handle_sangha_lock_release(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a sangha lock release event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.collaboration import sangha_lock_release
    return cast("dict[str, Any]", sangha_lock_release(**kwargs))


def handle_sangha_lock_list(**kwargs: Any) -> dict[str, Any]:
    """
    Handle a sangha lock list event.

    Returns:
        dict[str, Any]
    """
    from whitemagic.core.bridge.collaboration import sangha_lock_list
    return cast("dict[str, Any]", sangha_lock_list(**kwargs))
