"""Canonical tool name resolution — shared by ToolRuntime and call_tool().

Extracted from unified_api.py to avoid circular imports and to make
canonical name resolution available to the ToolRuntime boundary
without depending on the full call_tool() pipeline.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_TOOL_ALIASES: dict[str, str] = {
    # Legacy names -> canonical v11 names
    "manifest_read": "manifest",
    "manifest_summary": "manifest",
    "state_paths": "state.paths",
    "state_summary": "state.summary",
    "repo_summary": "repo.summary",
    "ship_check": "ship.check",
    # Underscore aliases for dot-notation tools
    "mesh_connect": "mesh.connect",
    "broker_publish": "broker.publish",
    "broker_history": "broker.history",
    "broker_status": "broker.status",
    "task_distribute": "task.distribute",
    "task_status": "task.status",
    "task_list": "task.list",
    "task_complete": "task.complete",
    "vote_create": "vote.create",
    "vote_cast": "vote.cast",
    "vote_analyze": "vote.analyze",
    "vote_list": "vote.list",
    "vote_record_outcome": "vote.record_outcome",
    "llama.models": "llama.models",
    "llama.generate": "llama.generate",
    "llama.chat": "llama.chat",
    "agent_register": "agent.register",
    "agent_heartbeat": "agent.heartbeat",
    "agent_list": "agent.list",
    "agent_capabilities": "agent.capabilities",
    "agent_deregister": "agent.deregister",
    "pipeline_create": "pipeline.create",
    "pipeline_status": "pipeline.status",
    "pipeline_list": "pipeline.list",
    "homeostasis_status": "homeostasis.status",
    "homeostasis_check": "homeostasis.check",
    "maturity_assess": "maturity.assess",
    "tool_graph": "tool.graph",
    "tool_graph_full": "tool.graph_full",
    "dharma_reload": "dharma.reload",
    "salience_spotlight": "salience.spotlight",
    "reasoning_bicameral": "reasoning.bicameral",
    "memory_retention_sweep": "memory.retention_sweep",
    "read_memory": "memory_read",
    "update_memory": "memory_update",
    "delete_memory": "memory_delete",
    "starter_packs_list": "starter_packs.list",
    "starter_packs_get": "starter_packs.get",
    "starter_packs_suggest": "starter_packs.suggest",
    "capability_matrix": "capability.matrix",
    "capability_status": "capability.status",
    "capability_suggest": "capability.suggest",
    # Missing aliases for tools with handlers
    "galaxy_status": "galaxy.status",
    "galaxy_list": "galaxy.list",
    "galaxy_switch": "galaxy.switch",
    "galaxy_ingest": "galaxy.ingest",
    "galaxy_delete": "galaxy.delete",
    "prompt_list": "prompt.list",
    "prompt_render": "prompt.render",
    "prompt_reload": "prompt.reload",
    "otel_status": "otel.status",
    "otel_spans": "otel.spans",
    "otel_metrics": "otel.metrics",
    "working_memory_status": "working_memory.status",
    "working_memory_attend": "working_memory.attend",
    "working_memory_context": "working_memory.context",
    "cognitive_mode": "cognitive.mode",
    "cognitive_set": "cognitive.set",
    "cognitive_hints": "cognitive.hints",
    "cognitive_stats": "cognitive.stats",
    "rate_limiter_stats": "rate_limiter.stats",
    "audit_export": "audit.export",
    "agent_trust": "agent.trust",
    # Additional legacy aliases
    "health": "health.check",
    "health_status": "health.check",
    "system_status": "system.status",
    "gnosis_snapshot": "gnosis",
    "search": "search_memories",
    "read": "memory_read",
    "create": "memory_create",
    "update": "memory_update",
    "delete": "memory_delete",
    "list_memories": "memory_list",
    "list_tools": "tool.list",
}


def canonical_tool_name(tool_name: str) -> str:
    """Convert tool name to canonical form, with deprecation warnings for aliases.

    Args:
        tool_name: The tool name (may be an alias).

    Returns:
        The canonical tool name.
    """
    name = tool_name.strip()
    canonical = _TOOL_ALIASES.get(name, name)

    if canonical != name:
        logger.warning(
            "DEPRECATION: Tool alias '%s' is deprecated. "
            "Use '%s' instead. "
            "This alias will be removed in the next minor release.",
            name,
            canonical,
        )

    return canonical


def is_alias(tool_name: str) -> bool:
    """Check if a tool name is an alias (not canonical)."""
    return tool_name.strip() in _TOOL_ALIASES
