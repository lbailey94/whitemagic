"""dispatch_table.py — Tool router: assembles domain slices into one table.

The DISPATCH_TABLE dict is composed from per-domain slice modules:

    dispatch_core.py          — LazyHandler, LazyHandlerAbs, WRITE_TOOLS, _audit_tool_call
    dispatch_memory.py        — Memory, galaxy, living-graph, OMS, hologram
    dispatch_intelligence.py  — Knowledge graph, embeddings, dream, cognition, analytics
    dispatch_agents.py        — Session, swarm, agent registry, mesh, voting, pipeline
    dispatch_security.py      — Security, sandbox, shelter, dharma, watcher, forge

Tools NOT yet migrated to a slice (operational/misc) are defined inline below.
New tools should be added to the appropriate domain slice, not inline here.

Public API (unchanged):
    dispatch(tool_name, **kwargs) -> dict | None
    get_pipeline() -> DispatchPipeline
    DISPATCH_TABLE  (for read-only introspection)
    WRITE_TOOLS     (re-exported from dispatch_core)
    LazyHandler     (re-exported from dispatch_core)
    LazyHandlerAbs  (re-exported from dispatch_core)
"""
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export primitives from dispatch_core so existing imports keep working
# ---------------------------------------------------------------------------
from whitemagic.tools.dispatch_agents import DISPATCH_AGENTS
from whitemagic.tools.dispatch_core import (  # noqa: E402
    LazyHandler,
)
from whitemagic.tools.dispatch_intelligence import DISPATCH_INTELLIGENCE

# ---------------------------------------------------------------------------
# Import domain slices
# ---------------------------------------------------------------------------
from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
from whitemagic.tools.dispatch_security import DISPATCH_SECURITY

# ---------------------------------------------------------------------------
# Operational & miscellaneous tools (not yet extracted to a domain slice)
# Add new tools to the relevant slice file instead.
# ---------------------------------------------------------------------------
_DISPATCH_OPERATIONAL: dict[str, Callable[..., dict[str, Any]]] = {
    # --- Yin-Yang Balance & Harmony Vector ---
    "record_yin_yang_activity": LazyHandler("balance", "handle_record_yin_yang_activity"),
    "get_yin_yang_balance": LazyHandler("balance", "handle_get_yin_yang_balance"),
    "harmony_vector": LazyHandler("balance", "handle_harmony_vector"),

    # --- Garden ---
    "garden_activate": LazyHandler("garden", "handle_garden_activate"),
    "garden_status": LazyHandler("garden", "handle_garden_status"),
    "garden_synergy": LazyHandler("garden", "handle_garden_synergy"),
    "garden_health": LazyHandler("garden", "handle_garden_health"),
    "garden_list_files": LazyHandler("garden", "handle_garden_list_files"),
    "garden_list_functions": LazyHandler("garden", "handle_garden_list_functions"),
    "garden_search": LazyHandler("garden", "handle_garden_search"),
    "garden_resonance": LazyHandler("garden", "handle_garden_resonance"),
    "garden_map_system": LazyHandler("garden", "handle_garden_map_system"),
    "garden_stats": LazyHandler("garden", "handle_garden_stats"),
    "garden_browse": LazyHandler("garden", "handle_garden_browse"),
    "garden_resolve": LazyHandler("garden", "handle_garden_resolve"),

    # --- War Room ---
    "art_of_war.chapter": LazyHandler("war_room", "handle_art_of_war_chapter"),
    "art_of_war.assess": LazyHandler("war_room", "handle_assess_terrain"),
    "art_of_war.plan": LazyHandler("war_room", "handle_plan_campaign"),
    "war_room.status": LazyHandler("war_room", "handle_war_room_status"),
    "war_room.plan": LazyHandler("war_room", "handle_war_room_plan"),
    "war_room.execute": LazyHandler("war_room", "handle_war_room_execute"),
    "war_room.hierarchy": LazyHandler("war_room", "handle_war_room_hierarchy"),
    "war_room.campaigns": LazyHandler("war_room", "handle_war_room_campaigns"),
    "war_room.phase": LazyHandler("war_room", "handle_war_room_phase"),
    "doctrine.summary": LazyHandler("war_room", "handle_doctrine_summary"),
    "doctrine.stratagems": LazyHandler("war_room", "handle_doctrine_stratagems"),
    "doctrine.force": LazyHandler("war_room", "handle_doctrine_force"),
    "art_of_war.wisdom": LazyHandler("war_room", "handle_art_of_war_wisdom"),
    "art_of_war.terrain": LazyHandler("war_room", "handle_art_of_war_terrain"),
    "art_of_war.campaign": LazyHandler("war_room", "handle_art_of_war_campaign"),
    "fool_guard.status": LazyHandler("war_room", "handle_fool_guard_status"),
    "fool_guard.dare_to_die": LazyHandler("war_room", "handle_fool_guard_dare_to_die"),
    "fool_guard.ralph": LazyHandler("war_room", "handle_fool_guard_ralph"),

    # --- Immune (stubs) ---
    "immune_scan": LazyHandler("misc", "handle_immune_scan"),
    "immune_heal": LazyHandler("misc", "handle_immune_heal"),

    # --- Symbolic / Oracle ---
    "cast_oracle": LazyHandler("misc", "handle_cast_oracle"),
    "wu_xing_balance": LazyHandler("misc", "handle_wu_xing_balance"),

    # --- Gan Ying ---
    "ganying_emit": LazyHandler("ganying", "handle_ganying_emit"),
    "ganying_history": LazyHandler("ganying", "handle_ganying_history"),
    "ganying_listeners": LazyHandler("ganying", "handle_ganying_listeners"),
    "resonance_trace": LazyHandler("ganying", "handle_resonance_trace"),

    # --- Archaeology ---
    "archaeology": LazyHandler("archaeology", "handle_archaeology"),
    "archaeology_scan_directory": LazyHandler("archaeology", "handle_archaeology_scan_directory"),
    "archaeology_mark_read": LazyHandler("archaeology", "handle_archaeology_mark_read"),
    "archaeology_mark_written": LazyHandler("archaeology", "handle_archaeology_mark_written"),
    "archaeology_have_read": LazyHandler("archaeology", "handle_archaeology_have_read"),
    "archaeology_find_unread": LazyHandler("archaeology", "handle_archaeology_find_unread"),
    "archaeology_find_changed": LazyHandler("archaeology", "handle_archaeology_find_changed"),
    "archaeology_recent_reads": LazyHandler("archaeology", "handle_archaeology_recent_reads"),
    "archaeology_stats": LazyHandler("archaeology", "handle_archaeology_stats"),
    "archaeology_report": LazyHandler("archaeology", "handle_archaeology_report"),
    "archaeology_search": LazyHandler("archaeology", "handle_archaeology_search"),
    "archaeology_process_wisdom": LazyHandler("archaeology", "handle_archaeology_process_wisdom"),
    "archaeology_daily_digest": LazyHandler("archaeology", "handle_archaeology_daily_digest"),

    # --- Windsurf ---
    "windsurf_list_conversations": LazyHandler("windsurf_conv", "handle_windsurf_list_conversations"),
    "windsurf_read_conversation": LazyHandler("windsurf_conv", "handle_windsurf_read_conversation"),
    "windsurf_export_conversation": LazyHandler("windsurf_conv", "handle_windsurf_export_conversation"),
    "windsurf_search_conversations": LazyHandler("windsurf_conv", "handle_windsurf_search_conversations"),
    "windsurf_stats": LazyHandler("windsurf_conv", "handle_windsurf_stats"),

    # --- Browser ---
    "browser_navigate": LazyHandler("browser_tools", "handle_browser_navigate"),
    "browser_click": LazyHandler("browser_tools", "handle_browser_click"),
    "browser_type": LazyHandler("browser_tools", "handle_browser_type"),
    "browser_extract_dom": LazyHandler("browser_tools", "handle_browser_extract_dom"),
    "browser_screenshot": LazyHandler("browser_tools", "handle_browser_screenshot"),
    "browser_get_interactables": LazyHandler("browser_tools", "handle_browser_get_interactables"),

    # --- Web Research ---
    "web_fetch": LazyHandler("web_research", "handle_web_fetch"),
    "web_search": LazyHandler("web_research", "handle_web_search"),
    "web_search_and_read": LazyHandler("web_research", "handle_web_search_and_read"),
    "research_topic": LazyHandler("web_research", "handle_research_topic"),
    "browser_session_status": LazyHandler("web_research", "handle_browser_session_status"),

    # --- Scratchpad ---
    "scratchpad": LazyHandler("scratchpad", "handle_scratchpad"),
    "scratchpad_create": LazyHandler("scratchpad", "handle_scratchpad_create"),
    "scratchpad_update": LazyHandler("scratchpad", "handle_scratchpad_update"),
    "analyze_scratchpad": LazyHandler("scratchpad", "handle_analyze_scratchpad"),
    "scratchpad_finalize": LazyHandler("scratchpad", "handle_scratchpad_finalize"),

    # --- Introspection ---
    "gnosis": LazyHandler("introspection", "handle_gnosis"),
    "capability.matrix": LazyHandler("introspection", "handle_capability_matrix"),
    "capability.status": LazyHandler("introspection", "handle_capability_status"),
    "capability.suggest": LazyHandler("introspection", "handle_capability_suggest"),
    "capabilities": LazyHandler("introspection", "handle_capabilities"),
    "manifest": LazyHandler("introspection", "handle_manifest"),
    "state.paths": LazyHandler("introspection", "handle_state_paths"),
    "state.summary": LazyHandler("introspection", "handle_state_summary"),
    "repo.summary": LazyHandler("introspection", "handle_repo_summary"),
    "ship.check": LazyHandler("introspection", "handle_ship_check"),
    "get_telemetry_summary": LazyHandler("introspection", "handle_get_telemetry_summary"),
    "health_report": LazyHandler("introspection", "handle_health_report"),

    # --- Metrics & Utility ---
    "track_metric": LazyHandler("misc", "handle_track_metric"),
    "get_metrics_summary": LazyHandler("misc", "handle_get_metrics_summary"),
    "focus_session": LazyHandler("misc", "handle_focus_session"),
    "capability_harness": LazyHandler("misc", "handle_capability_harness"),

    # --- OTel ---
    "otel": LazyHandler("otel", "handle_otel"),
    "otel.spans": LazyHandler("otel", "handle_otel_spans"),
    "otel.metrics": LazyHandler("otel", "handle_otel_metrics"),
    "otel.status": LazyHandler("otel", "handle_otel_status"),

    # --- Gratitude / Economy ---
    "whitemagic.tip": LazyHandler("gratitude", "handle_tip"),
    "gratitude.stats": LazyHandler("gratitude", "handle_gratitude_stats"),
    "gratitude.benefits": LazyHandler("gratitude", "handle_gratitude_benefits"),
    "pulse.status": LazyHandler("economy", "handle_pulse_status"),
    "bounty.create": LazyHandler("economy", "handle_create_bounty"),
    "bounty.list": LazyHandler("economy", "handle_list_bounties"),

    # --- ILP Streaming Payments ---
    "ilp.configure": LazyHandler("ilp", "handle_ilp_configure"),
    "ilp.send": LazyHandler("ilp", "handle_ilp_send"),
    "ilp.receipt": LazyHandler("ilp", "handle_ilp_receipt"),
    "ilp.history": LazyHandler("ilp", "handle_ilp_history"),
    "ilp.balance": LazyHandler("ilp", "handle_ilp_balance"),
    "ilp.status": LazyHandler("ilp", "handle_ilp_status"),
}

# ---------------------------------------------------------------------------
# DISPATCH_TABLE: merge all domain slices (last-write-wins on key conflicts)
# ---------------------------------------------------------------------------
DISPATCH_TABLE: dict[str, Callable[..., dict[str, Any]]] = {
    **DISPATCH_MEMORY,
    **DISPATCH_INTELLIGENCE,
    **DISPATCH_AGENTS,
    **DISPATCH_SECURITY,
    **_DISPATCH_OPERATIONAL,
}


# ---------------------------------------------------------------------------
# Core router middleware
# ---------------------------------------------------------------------------
_gana_invoke: Callable | None = None
_bridge_execute: Callable | None = None
_router_cached = False


def _ensure_router_cached() -> None:
    """Cache gana_invoke and bridge fallback once."""
    global _gana_invoke, _bridge_execute, _router_cached
    if _router_cached:
        return
    try:
        from whitemagic.core.bridge.gana import gana_invoke
        _gana_invoke = gana_invoke
    except (ImportError, AttributeError) as e:
        logger.debug(f"Gana invoke bridge not available: {e}")
    except RuntimeError as e:
        logger.warning(f"Gana invoke bridge initialization failed: {e}")
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from whitemagic.core.bridge.tools import execute_mcp_tool
        _bridge_execute = execute_mcp_tool
    except ImportError:
        pass
    _router_cached = True


def _mw_core_router(ctx: Any, next_fn: Callable[[Any], dict[str, Any] | None]) -> dict[str, Any] | None:
    """Gana prefix → Dispatch table → Bridge fallback."""
    _ensure_router_cached()
    result = None

    if ctx.tool_name.startswith("gana_") and _gana_invoke is not None:
        try:
            result = _gana_invoke(tool_name=ctx.tool_name, args=ctx.kwargs)
        except (TypeError, ValueError, AttributeError) as e:
            result = {"status": "error", "error_code": "gana_invocation_failed", "message": f"Gana argument/route error: {str(e)}"}
        except RuntimeError as e:
            result = {"status": "error", "error_code": "gana_runtime_error", "message": f"Gana runtime failure: {str(e)}"}

    if result is None:
        handler = DISPATCH_TABLE.get(ctx.tool_name)
        if handler is not None:
            result = handler(**ctx.kwargs)

    if result is None and _bridge_execute is not None:
        try:
            bridge_result = _bridge_execute(ctx.tool_name, **ctx.kwargs)
            if bridge_result:
                result = bridge_result
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.debug(f"Bridge execution fallback (type/attr error): {e}")
        except RuntimeError as e:
            logger.warning(f"Bridge execution fallback runtime error: {e}")

    if result is None:
        return next_fn(ctx)

    return result


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------
def _build_pipeline() -> Any:
    """Build the standard dispatch pipeline. Called once at import time."""
    from whitemagic.tools.middleware import (
        DispatchPipeline,
        mw_circuit_breaker,
        mw_governor,
        mw_input_sanitizer,
        mw_maturity_gate,
        mw_observability,
        mw_rate_limiter,
        mw_security_monitor,
        mw_tool_permissions,
        mw_zodiac_resonance,
    )
    p = DispatchPipeline()
    p.use("input_sanitizer", mw_input_sanitizer)
    p.use("circuit_breaker", mw_circuit_breaker)
    p.use("rate_limiter",    mw_rate_limiter)
    p.use("security_monitor", mw_security_monitor)
    p.use("tool_permissions", mw_tool_permissions)
    p.use("maturity_gate",   mw_maturity_gate)
    p.use("zodiac_resonance", mw_zodiac_resonance)
    p.use("governor",        mw_governor)
    p.use("observability",   mw_observability)
    p.use("core_router",     _mw_core_router)
    return p


_pipeline = _build_pipeline()


def dispatch(tool_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """Dispatch a tool call through the composable middleware pipeline.

    Pipeline (in order):
      1. Input sanitizer   — validate args
      2. Circuit breaker   — fast-fail on cooldown + post-feedback
      3. Rate limiter      — per-agent, per-tool throttling
      4. Security monitor  — anomaly detection
      5. Tool permissions  — per-agent RBAC
      6. Maturity gate     — developmental stage gating
      7. Governor          — ethical validation
      8. Observability     — Prometheus + OTel metrics
      9. Core router       — Gana prefix → dispatch table → bridge fallback

    Returns:
        The handler result, or an error dict if no handler matched.
    """
    from whitemagic.core.governance.unified_progression import get_progression_daemon
    from whitemagic.core.monitoring.otel_export import get_otel

    otel = get_otel()
    daemon = get_progression_daemon()
    current_phase = daemon.state.current_phase.value if daemon else "unknown"

    with otel.tool_span(tool_name) as ctx:
        ctx["attributes"] = {"zodiac_phase": current_phase}
        result = _pipeline.execute(tool_name, **kwargs)
        if isinstance(result, dict) and result.get("status") == "error":
            ctx["status"] = "error"
        return cast("dict[str, Any] | None", result)


def get_pipeline() -> Any:
    """Return the active pipeline for introspection or extension."""
    return _pipeline
