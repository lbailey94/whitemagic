# ruff: noqa: BLE001
"""dispatch_core.py — Shared primitives for all dispatch domain slices.

This module contains:
- ``LazyHandler`` and ``LazyHandlerAbs``: lazy-loading handler wrappers
- ``WRITE_TOOLS``: the set of mutating tool names for audit tracking
- ``_audit_tool_call()``: dharma audit helper

All domain slice files (dispatch_memory.py, dispatch_agents.py, etc.)
import from HERE, not from dispatch_table.py, to avoid circular imports.
"""
import importlib
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WRITE_TOOLS: Tools that mutate state (automatically audited)
# ---------------------------------------------------------------------------
WRITE_TOOLS: set[str] = {
    # Memory mutations
    "create_memory", "update_memory", "delete_memory",
    "memory_create", "memory_update", "memory_delete",
    "import_memories", "export_memories",
    # Session mutations
    "create_session", "update_session", "delete_session",
    "checkpoint_session", "resume_session",
    # Garden mutations
    "garden_activate", "garden_update", "garden_delete",
    "garden_list_files", "garden_list_functions",
    # Dharma/Karma mutations
    "karma_record", "karma.anchor", "set_dharma_profile",
    # Configuration mutations
    "sandbox.set_limits", "sangha_lock",
}


class LazyHandler:
    """Lazy-loads a tool handler from ``whitemagic.tools.handlers.<module>``.

    Automatically audits write operations (tools in WRITE_TOOLS) to the
    dharma_audit table for ethical governance tracking.
    """

    def __init__(self, module_name: str, function_name: str, tool_name: str = ""):
        self.module_name = module_name
        self.function_name = function_name
        self.tool_name = tool_name
        self._cached_func: Callable | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._cached_func is None:
            mod = importlib.import_module(f"whitemagic.tools.handlers.{self.module_name}")
            self._cached_func = getattr(mod, self.function_name)

        should_audit = self.tool_name and self.tool_name in WRITE_TOOLS
        if should_audit:
            _audit_tool_call(self.tool_name, "start", kwargs)

        result = self._cached_func(*args, **kwargs)

        if should_audit:
            status = "success" if result.get("status") == "success" else "failure"
            _audit_tool_call(self.tool_name, status, kwargs, result)

        return result


class LazyHandlerAbs:
    """Lazy-loads a handler from an absolute Python module path."""

    def __init__(self, module_path: str, function_name: str):
        self.module_path = module_path
        self.function_name = function_name
        self._cached_func: Callable | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._cached_func is None:
            mod = importlib.import_module(self.module_path)
            self._cached_func = getattr(mod, self.function_name)
        return self._cached_func(*args, **kwargs)


# ---------------------------------------------------------------------------
# Dharma Audit Helper
# ---------------------------------------------------------------------------
def _audit_tool_call(
    tool_name: str,
    status: str,
    kwargs: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> None:
    """Log a tool call to the dharma_audit table for ethical governance.

    Audit logging failures are non-fatal — they must never block operations.
    """
    try:
        from datetime import datetime

        safe_kwargs = {k: v for k, v in kwargs.items() if k not in {"password", "token", "secret"}}
        audit_record = {
            "timestamp": datetime.now().isoformat(),
            "action": f"{tool_name}:{status}",
            "context": str(safe_kwargs)[:500],
            "decision": "approved",
        }

        try:
            from whitemagic.core.memory.unified import get_unified_memory
            backend = get_unified_memory().backend
            if hasattr(backend, "_execute"):
                backend._execute(
                    """INSERT INTO dharma_audit
                       (timestamp, action, ethical_score, harmony_score, consent_level, boundary_type, concerns, context, decision)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        audit_record["timestamp"],
                        audit_record["action"],
                        1.0, 1.0, "granted", "none", "",
                        audit_record["context"],
                        audit_record["decision"],
                    ),
                )
        except Exception as e:
            logger.debug("Dharma audit logging skipped: %s", e, exc_info=True)

    except Exception as e:
        logger.debug("Dharma audit error: %s", e, exc_info=True)
