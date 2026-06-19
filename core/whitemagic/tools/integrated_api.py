"""Integrated Tool API - Adds blackboard, gan ying, and autocast to all tool calls.

Wraps unified_api with:
- Automatic blackboard posting
- Gan Ying bus emission
- Tool discovery metrics
- Autocast suggestions
"""
# ruff: noqa: BLE001

import logging
import time
from typing import Any

from whitemagic.tools.discovery import get_tool_discovery
from whitemagic.tools.unified_api import call_tool as _call_tool_base

logger = logging.getLogger(__name__)


def call_tool(
    tool_name: str,
    _compact: bool = True,
    _record_metrics: bool = True,
    _emit_gan_ying: bool = True,
    _post_blackboard: bool = True,
    **kwargs: Any
) -> dict[str, Any]:
    """Enhanced tool call with integrated blackboard, gan ying, and metrics.

    Args:
        tool_name: Name of tool to call
        _compact: Return compact response (default True for token efficiency)
        _record_metrics: Record call metrics for autocast (default True)
        _emit_gan_ying: Emit to gan ying bus (default True)
        _post_blackboard: Post to blackboard (default True)
        **kwargs: Tool-specific arguments

    Returns:
        Tool result (compact or full envelope based on _compact flag)
    """
    start_time = time.perf_counter()
    context_tags = kwargs.pop("_context_tags", [])

    # Get integrations
    discovery = get_tool_discovery() if _record_metrics else None
    blackboard = None
    gan_ying = None

    if _post_blackboard:
        try:
            from whitemagic.agents.blackboard import get_blackboard
            blackboard = get_blackboard()
        except (ImportError, ModuleNotFoundError) as e:
            import logging
            logging.getLogger(__name__).debug("Exception silenced: %s", e)

    if _emit_gan_ying:
        try:
            from whitemagic.core.resonance.gan_ying_enhanced import get_event_bus
            gan_ying = get_event_bus()
        except (ImportError, ModuleNotFoundError) as e:
            import logging
            logging.getLogger(__name__).debug("Exception silenced: %s", e)

    # Post to blackboard (pre-call)
    if blackboard:
        try:
            blackboard.post("tool.call", {
                "tool": tool_name,
                "args": {k: str(v)[:100] for k, v in kwargs.items()},  # Truncate for blackboard
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.debug(f"Blackboard post failed: {e}")

    # Call the actual tool
    try:
        result = _call_tool_base(tool_name, **kwargs)
        success = isinstance(result, dict) and result.get("status") == "success"
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics for autocast
        if discovery:
            discovery.record_call(tool_name, latency_ms, success, context_tags)

        # Emit to gan ying bus
        if gan_ying:
            try:
                gan_ying.emit(  # type: ignore[call-arg]
                    "tool.completed",  # type: ignore[arg-type]
                    {
                        "tool": tool_name,
                        "success": success,
                        "latency_ms": latency_ms,
                    },
                    confidence=0.9 if success else 0.5,
                )
            except Exception as e:
                logger.debug(f"Gan ying emit failed: {e}")

        # Post to blackboard (post-call)
        if blackboard:
            try:
                blackboard.post("tool.result", {
                    "tool": tool_name,
                    "success": success,
                    "latency_ms": latency_ms,
                    "timestamp": time.time(),
                })
            except Exception as e:
                logger.debug(f"Blackboard post failed: {e}")

        # Return compact or full response
        if _compact and isinstance(result, dict):
            # Compact mode: strip envelope overhead
            return {
                "status": result.get("status", "unknown"),
                "data": result.get("details", result.get("result", {})),
            }

        return result

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record failure
        if discovery:
            discovery.record_call(tool_name, latency_ms, False, context_tags)

        # Emit failure to gan ying
        if gan_ying:
            try:
                gan_ying.emit(  # type: ignore[call-arg]
                    "tool.failed",  # type: ignore[arg-type]
                    {
                        "tool": tool_name,
                        "error": str(e)[:200],
                        "latency_ms": latency_ms,
                    },
                    confidence=0.3,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Post failure to blackboard
        if blackboard:
            try:
                blackboard.post("tool.error", {
                    "tool": tool_name,
                    "error": str(e)[:200],  # type: ignore[misc]
                    "timestamp": time.time(),
                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug("Exception silenced: %s", e)

        return {
            "status": "error",
            "error": str(e),  # type: ignore[misc]
            "tool": tool_name,
        }


def discover_tools(
    category: str | None = None,
    search: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Discover tools by category or search query.

    Args:
        category: Filter by category (e.g., "memory", "session")
        search: Search query string
        limit: Maximum results to return

    Returns:
        List of matching tools with metadata
    """
    discovery = get_tool_discovery()

    if category:
        tools = discovery.discover_by_category(category)
    elif search:
        tools = discovery.discover_by_search(search, limit)
    else:
        # Return most used tools
        stats = discovery.get_global_stats()
        tools = stats.get("most_used", [])

    return {
        "status": "success",
        "tools": tools[:limit],
        "count": len(tools),
    }


def autocast(
    current_context: list[str] | None = None,
    num_suggestions: int = 5,
    include_random: bool = True,
) -> dict[str, Any]:
    """Get context-aware tool suggestions (autocast).

    Analyzes:
    - Sequential patterns (what typically follows recent tools)
    - Context similarity
    - Underutilized tools (haven't been called recently)
    - Random exploration (for discovering new synergies)

    Args:
        current_context: Context tags for current situation
        num_suggestions: Number of suggestions to return
        include_random: Include random tools for exploration

    Returns:
        List of suggested tools with reasons and confidence scores
    """
    discovery = get_tool_discovery()

    suggestions = discovery.autocast_suggestions(
        current_context=current_context,
        num_suggestions=num_suggestions,
        include_random=include_random,
    )

    return {
        "status": "success",
        "suggestions": suggestions,
        "count": len(suggestions),
    }


def tool_stats(tool_name: str | None = None) -> dict[str, Any]:
    """Get tool usage statistics.

    Args:
        tool_name: Specific tool to get stats for (or None for global stats)

    Returns:
        Tool statistics including usage patterns, latency, success rate
    """
    discovery = get_tool_discovery()

    if tool_name:
        stats = discovery.get_tool_stats(tool_name)
    else:
        stats = discovery.get_global_stats()

    return {
        "status": "success",
        "stats": stats,
    }
