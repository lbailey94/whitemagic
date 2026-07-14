from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

GANA_NAMES: list[str] = [
    "gana_horn",
    "gana_neck",
    "gana_root",
    "gana_room",
    "gana_heart",
    "gana_tail",
    "gana_winnowing_basket",
    "gana_ghost",
    "gana_willow",
    "gana_star",
    "gana_extended_net",
    "gana_wings",
    "gana_chariot",
    "gana_abundance",
    "gana_straddling_legs",
    "gana_mound",
    "gana_stomach",
    "gana_hairy_head",
    "gana_net",
    "gana_turtle_beak",
    "gana_three_stars",
    "gana_dipper",
    "gana_ox",
    "gana_girl",
    "gana_void",
    "gana_roof",
    "gana_encampment",
    "gana_wall",
]

GANA_SHORT_DESC: dict[str, str] = {
    "gana_horn": "Session initialisation — bootstrap, create, resume, checkpoint, handoff",
    "gana_neck": "Core memory creation — create, update, import, delete, clone memories",
    "gana_root": "System health — health report, rust status/audit, state summary, ship check",
    "gana_room": "Resource locks & privacy — sangha lock, sandbox, hermit crab mode, MCP integrity, security monitor",
    "gana_heart": "Session context — scratchpad (create/update/finalize/analyze), handoff, context pack/status",
    "gana_tail": "Performance & acceleration — SIMD ops (cosine/batch), cascade execution",
    "gana_winnowing_basket": "Wisdom & search — search, vector search, hybrid recall, graph walk, JIT research, batch read",
    "gana_ghost": "Introspection & self-model — gnosis, telemetry, capabilities, graph topology, surprise stats, watchers, self-model forecast, narrative compression",
    "gana_willow": "Resilience — rate limiter, grimoire spells/suggest/cast/walkthrough, oracle",
    "gana_star": "Governance — governor validate/set-goal/drift/budget/dharma, forge status/reload/validate",
    "gana_extended_net": "Pattern connectivity — pattern search, cluster stats, learning, coherence boost, resonance trace",
    "gana_wings": "Deployment & export — export memories, audit export, mesh broadcast/status",
    "gana_chariot": "Codebase navigation & external research — archaeology, KG extract/query, STRATA, codegenome, Windsurf conversations, browser automation, web search/fetch, Fragment",
    "gana_abundance": "Regeneration — dream cycle (start/stop/now/status), lifecycle, serendipity, entity resolve, narrative compress, ILP payments, gratitude",
    "gana_straddling_legs": "Ethics & balance — ethics eval, boundaries, consent, harmony vector, wu xing balance, verification",
    "gana_mound": "Metrics & caching — hologram view, metric tracking, yin-yang balance, green score",
    "gana_stomach": "Digestion & tasks — pipeline (create/list/status), task distribute/status/route/complete",
    "gana_hairy_head": "Detail & debug — salience, anomaly (check/history/status), otel (metrics/spans), karma report/trace/anchor/verify, dharma rules",
    "gana_net": "Capture & filtering — prompt render/list/reload, karma verify chain",
    "gana_turtle_beak": "Precision — edge/bitnet inference, edge batch, stats",
    "gana_three_stars": "Judgment & synthesis — bicameral reasoning, ensemble (query/history/status), optimization, kaizen analyze/apply, sabha convene/status",
    "gana_dipper": "Strategy — homeostasis (check/status), maturity assess, starter packs (get/list/suggest), cognitive modes",
    "gana_ox": "Endurance — swarm decompose/route/complete/vote/plan/resolve/status, worker",
    "gana_girl": "Nurture — agent register/heartbeat/list/capabilities/deregister/trust",
    "gana_void": "Stillness & galaxies — galactic dashboard, gardens, galaxy CRUD/transfer/merge/sync/lineage/taxonomy, OMS export/import/inspect",
    "gana_roof": "Shelter — llama.cpp models/generate/chat/agent, model signing/verify, sovereign sandbox (shelter create/execute/inspect/destroy)",
    "gana_encampment": "Community — sangha chat, broker publish/history/status, gan ying emit/history/listeners",
    "gana_wall": "Boundaries & marketplace — vote create/cast/analyze/list/record_outcome, engagement tokens (issue/validate/revoke/list/status), marketplace (publish/discover/negotiate/complete)",
}

_COMMON_PROPS: dict[str, Any] = {
    "request_id": {
        "type": "string",
        "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated.",
    },
    "idempotency_key": {
        "type": "string",
        "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results.",
    },
    "dry_run": {
        "type": "boolean",
        "description": "If true, do not perform writes; return an execution preview when possible.",
        "default": False,
    },
    "now": {
        "type": "string",
        "description": "Optional ISO timestamp override for deterministic evaluation/replay (best-effort).",
    },
}


def _apply_common_props(tools: list[ToolDefinition]) -> list[ToolDefinition]:
    from whitemagic.tools.stable_surface import is_stable

    for tool_def in tools:
        schema = tool_def.input_schema or {}
        props = schema.setdefault("properties", {})
        if isinstance(props, dict):
            for key, value in _COMMON_PROPS.items():
                props.setdefault(key, value)
        tool_def.input_schema = schema
        # Enforce stable surface: tools in the canonical STABLE set get
        # stability=STABLE regardless of their authored default.
        if is_stable(tool_def.name) and tool_def.stability != ToolStability.STABLE:
            tool_def.stability = ToolStability.STABLE
    return tools


def collect_authored_tool_definitions() -> list[ToolDefinition]:
    """
    Perform the collect authored tool definitions operation.

    Returns:
        list[ToolDefinition]
    """
    tools: list[ToolDefinition] = []
    try:
        from whitemagic.tools.registry_defs import collect as _collect_domain_tools

        tools.extend(_collect_domain_tools())
    except (ImportError, ModuleNotFoundError):
        logger.debug("Optional dependency unavailable: ImportError")
    return _apply_common_props(tools)


def get_gana_nested_tools() -> dict[str, list[str]]:
    """
    Get the gana nested tools.

    Returns:
        dict[str, list[str]]
    """
    from whitemagic.tools.prat_mappings import GANA_TO_TOOLS

    return {gana: sorted(tools) for gana, tools in GANA_TO_TOOLS.items()}


def get_dispatch_tool_names() -> list[str]:
    """
    Get the dispatch tool names.

    Returns:
        list[str]
    """
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE

    return sorted(DISPATCH_TABLE.keys())


def _registry_tool_map(
    authored_tools: list[ToolDefinition],
) -> dict[str, ToolDefinition]:
    return {tool.name: tool for tool in authored_tools}


def synthesize_callable_tool_definitions(
    authored_tools: list[ToolDefinition],
) -> list[ToolDefinition]:
    """
    Perform the synthesize callable tool definitions operation.

    Args:
        authored_tools: Parameter description.

    Returns:
        list[ToolDefinition]
    """
    registry_map = _registry_tool_map(authored_tools)
    callable_names = sorted(set(get_dispatch_tool_names()) | set(GANA_NAMES))
    defs: list[ToolDefinition] = []
    nested_tools = get_gana_nested_tools()

    for name in callable_names:
        existing = registry_map.get(name)
        if existing is not None:
            defs.append(existing)
            continue

        if name.startswith("gana_"):
            defs.append(
                ToolDefinition(
                    name=name,
                    description=GANA_SHORT_DESC.get(name, f"Gana {name}"),
                    category=ToolCategory.GANA,
                    safety=ToolSafety.WRITE,
                    stability=ToolStability.STABLE,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "enum": nested_tools.get(name, []),
                                "description": "Which nested tool to invoke within this Gana.",
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments to pass to the selected tool.",
                                "default": {},
                            },
                            "operation": {
                                "type": "string",
                                "enum": [
                                    "search",
                                    "analyze",
                                    "transform",
                                    "consolidate",
                                ],
                                "description": "Polymorphic operation (when no specific tool is given).",
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional resonance context.",
                            },
                        },
                    },
                    gana=name,
                )
            )
            continue

        # Default to READ safety for dispatch-only tools without authored definitions.
        # Name-pattern inference was removed (Phase 7 WI 8): safety must be declared
        # in registry_defs/, not inferred from tool name prefixes.
        # Exception: tools in WRITE_TOOLS (dispatch_core.py) get WRITE safety.
        from whitemagic.tools.dispatch_core import WRITE_TOOLS

        inferred_safety = (
            ToolSafety.WRITE if name in WRITE_TOOLS else ToolSafety.READ
        )
        _logger = logging.getLogger(__name__)
        _logger.debug(
            "Tool %s has no authored definition — defaulting to %s safety. "
            "Add a ToolDefinition in registry_defs/ to declare explicit safety.",
            name,
            inferred_safety.value,
        )

        defs.append(
            ToolDefinition(
                name=name,
                description=f"Dispatch-routable WhiteMagic tool '{name}'.",
                category=ToolCategory.SYSTEM,
                safety=inferred_safety,
                input_schema={"type": "object", "properties": {}},
            )
        )

    return _apply_common_props(defs)
