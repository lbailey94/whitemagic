# ruff: noqa: E402
from typing import cast

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

from whitemagic.tools.dispatch_agents import DISPATCH_AGENTS
from whitemagic.tools.dispatch_core import (  # noqa: E402
    LazyHandler,
)
from whitemagic.tools.dispatch_intelligence import DISPATCH_INTELLIGENCE
from whitemagic.tools.dispatch_memory import DISPATCH_MEMORY
from whitemagic.tools.dispatch_security import DISPATCH_SECURITY

_DISPATCH_OPERATIONAL: dict[str, Callable[..., dict[str, Any]]] = {
    "record_yin_yang_activity": LazyHandler(
        "balance", "handle_record_yin_yang_activity"
    ),
    "get_yin_yang_balance": LazyHandler("balance", "handle_get_yin_yang_balance"),
    "harmony_vector": LazyHandler("balance", "handle_harmony_vector"),
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
    "immune_scan": LazyHandler("misc", "handle_immune_scan"),
    "immune_heal": LazyHandler("misc", "handle_immune_heal"),
    # ── Error Pattern Library ──
    "pattern.lookup": LazyHandler("pattern_tools", "handle_pattern_lookup"),
    "pattern.avoid": LazyHandler("pattern_tools", "handle_pattern_avoid"),
    "pattern.resolve": LazyHandler("pattern_tools", "handle_pattern_resolve"),
    "pattern.learn": LazyHandler("pattern_tools", "handle_pattern_learn"),
    "pattern.list": LazyHandler("pattern_tools", "handle_pattern_list"),
    "pattern.summary": LazyHandler("pattern_tools", "handle_pattern_summary"),
    "pattern.ingest": LazyHandler("pattern_tools", "handle_pattern_ingest"),
    "dna_validate": LazyHandler("misc", "handle_dna_validate"),
    "dna_principles": LazyHandler("misc", "handle_dna_principles"),
    "cast_oracle": LazyHandler("misc", "handle_cast_oracle"),
    "wu_xing_balance": LazyHandler("misc", "handle_wu_xing_balance"),
    "ganying_emit": LazyHandler("ganying", "handle_ganying_emit"),
    "ganying_history": LazyHandler("ganying", "handle_ganying_history"),
    "ganying_listeners": LazyHandler("ganying", "handle_ganying_listeners"),
    "resonance_trace": LazyHandler("ganying", "handle_resonance_trace"),
    "archaeology": LazyHandler("archaeology", "handle_archaeology"),
    "archaeology_scan_directory": LazyHandler(
        "archaeology", "handle_archaeology_scan_directory"
    ),
    "archaeology_mark_read": LazyHandler("archaeology", "handle_archaeology_mark_read"),
    "archaeology_mark_written": LazyHandler(
        "archaeology", "handle_archaeology_mark_written"
    ),
    "archaeology_have_read": LazyHandler("archaeology", "handle_archaeology_have_read"),
    "archaeology_find_unread": LazyHandler(
        "archaeology", "handle_archaeology_find_unread"
    ),
    "archaeology_find_changed": LazyHandler(
        "archaeology", "handle_archaeology_find_changed"
    ),
    "archaeology_recent_reads": LazyHandler(
        "archaeology", "handle_archaeology_recent_reads"
    ),
    "archaeology_stats": LazyHandler("archaeology", "handle_archaeology_stats"),
    "archaeology_report": LazyHandler("archaeology", "handle_archaeology_report"),
    "archaeology_search": LazyHandler("archaeology", "handle_archaeology_search"),
    "archaeology_process_wisdom": LazyHandler(
        "archaeology", "handle_archaeology_process_wisdom"
    ),
    "archaeology_daily_digest": LazyHandler(
        "archaeology", "handle_archaeology_daily_digest"
    ),
    "wiki.generate": LazyHandler("wiki", "handle_wiki_generate"),
    "wiki.query": LazyHandler("wiki", "handle_wiki_query"),
    "wiki.update": LazyHandler("wiki", "handle_wiki_update"),
    "wiki.scan": LazyHandler("wiki", "handle_wiki_scan"),
    "wiki.stats": LazyHandler("wiki", "handle_wiki_stats"),
    "external.wiki_query": LazyHandler("external_repo", "handle_external_wiki_query"),
    "external.repo_scan": LazyHandler("external_repo", "handle_external_repo_scan"),
    "external.repo_compare": LazyHandler(
        "external_repo", "handle_external_repo_compare"
    ),
    "strata.analyze": LazyHandler("strata", "handle_strata_analyze"),
    "strata.survey": LazyHandler("strata", "handle_strata_survey"),
    "strata.archaeology": LazyHandler("strata", "handle_strata_archaeology"),
    "strata.list_checks": LazyHandler("strata", "handle_strata_list_checks"),
    "fragment.search": LazyHandler("fragment", "handle_fragment_search"),
    "fragment.index": LazyHandler("fragment", "handle_fragment_index"),
    "fragment.status": LazyHandler("fragment", "handle_fragment_status"),
    "fragment.query": LazyHandler("fragment", "handle_fragment_query"),
    "fast_write.write": LazyHandler("fast_write", "handle_fast_write_write"),
    "fast_write.append": LazyHandler("fast_write", "handle_fast_write_append"),
    "fast_write.batch": LazyHandler("fast_write", "handle_fast_write_batch"),
    "fast_write.validate": LazyHandler("fast_write", "handle_fast_write_validate"),
    "polyglot.memory_query": LazyHandler("polyglot", "handle_polyglot_memory_query"),
    "polyglot.search": LazyHandler("polyglot", "handle_polyglot_search"),
    "polyglot.status": LazyHandler("polyglot", "handle_polyglot_status"),
    "polyglot.evolution": LazyHandler("polyglot", "handle_polyglot_evolution"),
    "polyglot.yield": LazyHandler("polyglot", "handle_polyglot_yield"),
    "polyglot.actor": LazyHandler("polyglot", "handle_polyglot_actor"),
    "windsurf_list_conversations": LazyHandler(
        "windsurf_conv", "handle_windsurf_list_conversations"
    ),
    "windsurf_read_conversation": LazyHandler(
        "windsurf_conv", "handle_windsurf_read_conversation"
    ),
    "windsurf_export_conversation": LazyHandler(
        "windsurf_conv", "handle_windsurf_export_conversation"
    ),
    "windsurf_search_conversations": LazyHandler(
        "windsurf_conv", "handle_windsurf_search_conversations"
    ),
    "windsurf_stats": LazyHandler("windsurf_conv", "handle_windsurf_stats"),
    "windsurf.export_all": LazyHandler("windsurf_conv", "handle_windsurf_export_all"),
    "windsurf.ingest": LazyHandler("windsurf_conv", "handle_windsurf_ingest"),
    "windsurf.sync": LazyHandler("windsurf_conv", "handle_windsurf_sync"),
    "windsurf.mine": LazyHandler("windsurf_conv", "handle_windsurf_mine"),
    "windsurf.categorize": LazyHandler("windsurf_conv", "handle_windsurf_categorize"),
    "windsurf.full_steps": LazyHandler("windsurf_conv", "handle_windsurf_full_steps"),
    "windsurf.compare": LazyHandler("windsurf_conv", "handle_windsurf_compare"),
    "windsurf.semantic_search": LazyHandler("windsurf_conv", "handle_windsurf_semantic_search"),
    "browser_navigate": LazyHandler("browser_tools", "handle_browser_navigate"),
    "browser_click": LazyHandler("browser_tools", "handle_browser_click"),
    "browser_type": LazyHandler("browser_tools", "handle_browser_type"),
    "browser_extract_dom": LazyHandler("browser_tools", "handle_browser_extract_dom"),
    "browser_screenshot": LazyHandler("browser_tools", "handle_browser_screenshot"),
    "browser_get_interactables": LazyHandler(
        "browser_tools", "handle_browser_get_interactables"
    ),
    "web_fetch": LazyHandler("web_research", "handle_web_fetch"),
    "web_fetch_enhanced": LazyHandler("web_research", "handle_web_fetch_enhanced"),
    "web_search": LazyHandler("web_research", "handle_web_search"),
    "web_search_and_read": LazyHandler("web_research", "handle_web_search_and_read"),
    "research_topic": LazyHandler("web_research", "handle_research_topic"),
    "web_search_category": LazyHandler("web_research", "handle_web_search_category"),
    "web_search_batch": LazyHandler("web_research", "handle_web_search_batch"),
    "deep_fetch": LazyHandler("web_research", "handle_deep_fetch"),
    "research_repo": LazyHandler("web_research", "handle_research_repo"),
    "research_url": LazyHandler("web_research", "handle_research_url"),
    "rabbit_hole_research": LazyHandler("web_research", "handle_rabbit_hole_research"),
    "web_cache_list": LazyHandler("web_research", "handle_web_cache_list"),
    "web_cache_clear": LazyHandler("web_research", "handle_web_cache_clear"),
    "parallel_reason": LazyHandler("web_research", "handle_parallel_reason"),
    "codegenome_validate": LazyHandler("web_research", "handle_codegenome_validate"),
    "alchemical_cycle": LazyHandler("web_research", "handle_alchemical_cycle"),
    "browser_session_status": LazyHandler(
        "web_research", "handle_browser_session_status"
    ),
    "image_analyze": LazyHandler("image_tools", "handle_image_analyze"),
    "scratchpad": LazyHandler("scratchpad", "handle_scratchpad"),
    "scratchpad_create": LazyHandler("scratchpad", "handle_scratchpad_create"),
    "scratchpad_update": LazyHandler("scratchpad", "handle_scratchpad_update"),
    "analyze_scratchpad": LazyHandler("scratchpad", "handle_analyze_scratchpad"),
    "scratchpad_finalize": LazyHandler("scratchpad", "handle_scratchpad_finalize"),
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
    "get_telemetry_summary": LazyHandler(
        "introspection", "handle_get_telemetry_summary"
    ),
    "tool_usage_stats": LazyHandler(
        "introspection", "handle_tool_usage_stats"
    ),
    "health_report": LazyHandler("introspection", "handle_health_report"),
    "list_ganas": LazyHandler("introspection", "handle_list_ganas"),
    "vitality": LazyHandler("introspection", "handle_vitality"),
    "discover": LazyHandler("introspection", "handle_discover"),
    "track_metric": LazyHandler("misc", "handle_track_metric"),
    "get_metrics_summary": LazyHandler("misc", "handle_get_metrics_summary"),
    "focus_session": LazyHandler("misc", "handle_focus_session"),
    "capability_harness": LazyHandler("misc", "handle_capability_harness"),
    "otel": LazyHandler("otel", "handle_otel"),
    "otel.spans": LazyHandler("otel", "handle_otel_spans"),
    "otel.metrics": LazyHandler("otel", "handle_otel_metrics"),
    "otel.status": LazyHandler("otel", "handle_otel_status"),
    "whitemagic.tip": LazyHandler("gratitude", "handle_tip"),
    "gratitude.stats": LazyHandler("gratitude", "handle_gratitude_stats"),
    "gratitude.benefits": LazyHandler("gratitude", "handle_gratitude_benefits"),
    "pulse.status": LazyHandler("economy", "handle_pulse_status"),
    "bounty.create": LazyHandler("economy", "handle_create_bounty"),
    "bounty.list": LazyHandler("economy", "handle_list_bounties"),
    "ilp.configure": LazyHandler("ilp", "handle_ilp_configure"),
    "ilp.send": LazyHandler("ilp", "handle_ilp_send"),
    "ilp.receipt": LazyHandler("ilp", "handle_ilp_receipt"),
    "ilp.history": LazyHandler("ilp", "handle_ilp_history"),
    "ilp.balance": LazyHandler("ilp", "handle_ilp_balance"),
    "ilp.status": LazyHandler("ilp", "handle_ilp_status"),
    "cache.status": LazyHandler("cache_coherence", "handle_cache_status"),
    "cache.flush": LazyHandler("cache_coherence", "handle_cache_flush"),
    "cache.tune": LazyHandler("cache_coherence", "handle_cache_tune"),
    "skill.list": LazyHandler("skill_forge", "handle_skill_list"),
    "skill.invoke": LazyHandler("skill_forge", "handle_skill_invoke"),
    "skill.seed": LazyHandler("skill_forge", "handle_skill_seed"),
    "skill.export_all": LazyHandler("skill_forge", "handle_skill_export_all"),
    "skill.import": LazyHandler("skill_forge", "handle_skill_import"),
    "skill.amend": LazyHandler("skill_forge", "handle_skill_amend"),
    "skill.history": LazyHandler("skill_forge", "handle_skill_history"),
    "skill.rollback": LazyHandler("skill_forge", "handle_skill_rollback"),
    "skill.evaluate": LazyHandler("skill_forge", "handle_skill_evaluate"),
    "zodiac.status": LazyHandler("zodiac_progression", "handle_zodiac_status"),
    "astro_status": LazyHandler("gana_dipper", "astro_status"),
    "astro_shift": LazyHandler("gana_dipper", "astro_shift"),
    "neurotransmitter.status": LazyHandler(
        "neurotransmitters", "handle_neurotransmitter_status"
    ),
    "neurotransmitter.report": LazyHandler(
        "neurotransmitters", "handle_neurotransmitter_report"
    ),
    "watcher_add": LazyHandler("watcher", "handle_watcher_add"),
    "watcher_remove": LazyHandler("watcher", "handle_watcher_remove"),
    "watcher_start": LazyHandler("watcher", "handle_watcher_start"),
    "watcher_stop": LazyHandler("watcher", "handle_watcher_stop"),
    "watcher_status": LazyHandler("watcher", "handle_watcher_status"),
    "watcher_recent_events": LazyHandler("watcher", "handle_watcher_recent_events"),
    "watcher_stats": LazyHandler("watcher", "handle_watcher_stats"),
    "watcher_list": LazyHandler("watcher", "handle_watcher_list"),
    "grimoire_walkthrough": LazyHandler(
        "grimoire_walkthrough", "handle_grimoire_walkthrough"
    ),
    "galactic_dashboard": LazyHandler(
        "galactic_dashboard", "handle_galactic_dashboard"
    ),
    "foresight.analyze": LazyHandler("foresight", "handle_foresight_analyze"),
    "foresight.constellations": LazyHandler(
        "foresight", "handle_foresight_constellations"
    ),
    "foresight.decay": LazyHandler("foresight", "handle_foresight_decay"),
    "foresight.convergence": LazyHandler("foresight", "handle_foresight_convergence"),
    "navigate_grimoire": LazyHandler("aspirational", "handle_navigate_grimoire"),
    "get_session_context": LazyHandler("aspirational", "handle_get_session_context"),
    "consult_wisdom_council": LazyHandler(
        "aspirational", "handle_consult_wisdom_council"
    ),
    "prat_get_context": LazyHandler("adaptive", "prat_get_context"),
    "prat_list_morphologies": LazyHandler("adaptive", "prat_list_morphologies"),
    "prat_invoke": LazyHandler("adaptive", "prat_invoke"),
    "prat_status": LazyHandler("adaptive", "prat_status"),
    "wm": LazyHandler("meta_tool", "handle_wm"),
    "wm_help": LazyHandler("meta_tool", "handle_wm_help"),
    "consciousness.depth": LazyHandler("consciousness", "handle_consciousness_depth"),
    "consciousness.coherence": LazyHandler(
        "consciousness", "handle_consciousness_coherence"
    ),
    "consciousness.awaken": LazyHandler("consciousness", "handle_consciousness_awaken"),
    "consciousness.reflect": LazyHandler(
        "consciousness", "handle_consciousness_reflect"
    ),
    "consciousness.token_report": LazyHandler(
        "consciousness", "handle_consciousness_token_report"
    ),
    "consciousness.narrative": LazyHandler(
        "consciousness", "handle_consciousness_narrative"
    ),
    "consciousness.unified_field": LazyHandler(
        "consciousness", "handle_consciousness_unified_field"
    ),
    "consciousness.status": LazyHandler("consciousness", "handle_consciousness_status"),
    "consciousness.smarana": LazyHandler(
        "consciousness", "handle_consciousness_smarana"
    ),
    "consciousness.flow": LazyHandler("consciousness", "handle_consciousness_flow"),
    "consciousness.time_dilation": LazyHandler(
        "consciousness", "handle_consciousness_time_dilation"
    ),
    "consciousness.calibration": LazyHandler(
        "consciousness", "handle_consciousness_calibration"
    ),
    "consciousness.token_economy": LazyHandler(
        "consciousness", "handle_consciousness_token_economy"
    ),
    "citta.continuity": LazyHandler("consciousness", "handle_citta_continuity"),
    "citta.stream_summary": LazyHandler("consciousness", "handle_citta_stream_summary"),
    "citta.sensorium": LazyHandler("consciousness", "handle_citta_sensorium"),
    "citta.cycle": LazyHandler("consciousness", "handle_citta_cycle"),
    "consciousness.stillness": LazyHandler(
        "consciousness", "handle_consciousness_stillness"
    ),
    # ── v24.3 Screenshot Upgrade Strategy Tools ──
    "tx_firewall.status": LazyHandler("v24_3_handlers", "handle_tx_firewall_status"),
    "tx_firewall.set_policy": LazyHandler("v24_3_handlers", "handle_tx_firewall_set_policy"),
    "bounty.scan": LazyHandler("v24_3_handlers", "handle_bounty_scan"),
    "bounty.auto_claim": LazyHandler("v24_3_handlers", "handle_bounty_auto_claim"),
    "bounty.connector_status": LazyHandler("v24_3_handlers", "handle_bounty_connector_status"),
    "model.optimize": LazyHandler("v24_3_handlers", "handle_model_optimize"),
    "model.optimize_status": LazyHandler("v24_3_handlers", "handle_model_optimize_status"),
    "ambient.state": LazyHandler("v24_3_handlers", "handle_ambient_state"),
    "ambient.status": LazyHandler("v24_3_handlers", "handle_ambient_status"),
    "wasm_verify.status": LazyHandler("v24_3_handlers", "handle_wasm_verify_status"),
    "network_state.status": LazyHandler("v24_3_handlers", "handle_network_state_status"),
    "network_state.create_identity": LazyHandler("v24_3_handlers", "handle_network_state_create_identity"),
    "network_state.propose": LazyHandler("v24_3_handlers", "handle_network_state_propose"),
    "network_state.vote": LazyHandler("v24_3_handlers", "handle_network_state_vote"),
    "network_state.resolve": LazyHandler("v24_3_handlers", "handle_network_state_resolve"),
    "genetic.run": LazyHandler("v24_3_handlers", "handle_genetic_run"),
    "genetic.status": LazyHandler("v24_3_handlers", "handle_genetic_status"),
    # ── Quantum Geometry Tools ──
    "quantum.manifold_distance": LazyHandler("quantum", "handle_quantum_manifold_distance"),
    "quantum.fubini_study": LazyHandler("quantum", "handle_quantum_fubini_study"),
    "quantum.natural_gradient": LazyHandler("quantum", "handle_quantum_natural_gradient"),
    "quantum.mps_compress": LazyHandler("quantum", "handle_quantum_mps_compress"),
    "quantum.auto_manifold": LazyHandler("quantum", "handle_quantum_auto_manifold"),
    "quantum.born_sample": LazyHandler("quantum", "handle_quantum_born_sample"),
    "quantum.born_distribution": LazyHandler("quantum", "handle_quantum_born_distribution"),
    "quantum.interference": LazyHandler("quantum", "handle_quantum_interference"),
    # ── Topological Protection Tools ──
    "topological.berry_phase": LazyHandler("quantum", "handle_topological_berry_phase"),
    "topological.chern_number": LazyHandler("quantum", "handle_topological_chern_number"),
    "topological.encode": LazyHandler("quantum", "handle_topological_encode"),
    "topological.decode": LazyHandler("quantum", "handle_topological_decode"),
}

DISPATCH_TABLE: dict[str, Callable[..., dict[str, Any]]] = {
    **DISPATCH_MEMORY,
    **DISPATCH_INTELLIGENCE,
    **DISPATCH_AGENTS,
    **DISPATCH_SECURITY,
    **_DISPATCH_OPERATIONAL,
}


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
        logger.debug("Gana invoke bridge not available: %s", e, exc_info=True)
    except RuntimeError as e:
        logger.warning("Gana invoke bridge initialization failed: %s", e, exc_info=True)
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from whitemagic.core.bridge.tools import execute_mcp_tool
        _bridge_execute = execute_mcp_tool
    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")
    _router_cached = True


def _mw_core_router(
    ctx: Any, next_fn: Callable[[Any], dict[str, Any] | None]
) -> dict[str, Any] | None:
    """Gana prefix → Dispatch table → Bridge fallback."""
    _ensure_router_cached()
    result = None

    # Garden resonance pre-dispatch (v23.3: gardens as active participants)
    try:
        from whitemagic.core.engines.registry import get_garden_for_tool

        garden_name = get_garden_for_tool(ctx.tool_name)
        if garden_name is not None:
            from whitemagic.gardens import get_garden

            garden = get_garden(garden_name)
            if garden is not None:
                garden.boost(0.1)
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)

    if ctx.tool_name.startswith("gana_") and _gana_invoke is not None:
        try:
            result = _gana_invoke(tool_name=ctx.tool_name, args=ctx.kwargs)
        except (TypeError, ValueError, AttributeError) as e:
            result = {
                "status": "error",
                "error_code": "gana_invocation_failed",
                "message": f"Gana argument/route error: {str(e)}",
            }
        except RuntimeError as e:
            result = {
                "status": "error",
                "error_code": "gana_runtime_error",
                "message": f"Gana runtime failure: {str(e)}",
            }

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
            logger.debug(
                "Bridge execution fallback (type/attr error): %s", e, exc_info=True
            )
        except RuntimeError as e:
            logger.warning(
                "Bridge execution fallback runtime error: %s", e, exc_info=True
            )

    if result is None:
        return next_fn(ctx)

    return result


def _build_pipeline() -> Any:
    """Build the standard dispatch pipeline. Called once at import time."""
    from whitemagic.core.monitoring.token_tracker import mw_token_tracker
    from whitemagic.tools.middleware import (
        DispatchPipeline,
        mw_auto_optimize,
        mw_circuit_breaker,
        mw_citta_consciousness,
        mw_cognitive_mode,
        mw_draft_review,
        mw_engagement_token,
        mw_error_learner,
        mw_governor,
        mw_inference_router,
        mw_input_sanitizer,
        mw_karma_effects,
        mw_maturity_gate,
        mw_model_signing,
        mw_observability,
        mw_pattern_guard,
        mw_rate_limiter,
        mw_security_monitor,
        mw_semantic_cache,
        mw_session_recorder,
        mw_timeout,
        mw_tool_permissions,
        mw_transaction_firewall,
        mw_wasm_verify,
        mw_zodiac_resonance,
        mw_code_nudge,
    )

    p = DispatchPipeline()
    p.use("input_sanitizer", mw_input_sanitizer)
    p.use("circuit_breaker", mw_circuit_breaker)
    p.use("timeout", mw_timeout)
    p.use("rate_limiter", mw_rate_limiter)
    p.use("security_monitor", mw_security_monitor)
    p.use("pattern_guard", mw_pattern_guard)
    p.use("engagement_token", mw_engagement_token)
    p.use("model_signing", mw_model_signing)
    p.use("cognitive_mode", mw_cognitive_mode)
    p.use("tool_permissions", mw_tool_permissions)
    p.use("maturity_gate", mw_maturity_gate)
    p.use("zodiac_resonance", mw_zodiac_resonance)
    p.use("citta_consciousness", mw_citta_consciousness)
    p.use("governor", mw_governor)
    p.use("transaction_firewall", mw_transaction_firewall)
    p.use("semantic_cache", mw_semantic_cache)
    p.use("auto_optimize", mw_auto_optimize)
    p.use("inference_router", mw_inference_router)
    p.use("draft_review", mw_draft_review)
    p.use("token_tracker", mw_token_tracker)
    p.use("karma_effects", mw_karma_effects)
    p.use("observability", mw_observability)
    p.use("session_recorder", mw_session_recorder)
    p.use("error_learner", mw_error_learner)
    p.use("wasm_verify", mw_wasm_verify)
    p.use("code_nudge", mw_code_nudge)
    p.use("core_router", _mw_core_router)
    return p


_pipeline = _build_pipeline()


_FAST_PATH_TOOLS = frozenset({
    "consciousness.loop.status",
    "consciousness.mode",
    "guna.balance.status",
    "meta.galaxy.overview",
    "galaxy.stats",
    "galaxy.list",
    "health.check",
    "system.status",
    # ── Common read operations for MCP/IDE response time ──
    "search_memories",
    "health_report",
    "gnosis",
    "state.current",
    "session_bootstrap",
    "galactic.dashboard",
    "capabilities",
    "manifest",
})

# Phase 3: Registry-declared fast-path tools.
# Built from ToolDefinition.fast_path=True and gana="gana_ghost" entries.
# Replaces the former _FAST_PATH_PREFIXES name-pattern inference.
_FAST_PATH_FROM_REGISTRY: set[str] = set()


def _ensure_fast_path_registry() -> None:
    """Populate _FAST_PATH_FROM_REGISTRY from the tool registry (lazy, once).

    Mechanically enforces fast-path safety declarations:
    - Tools with ``fast_path=True`` must have ``safety=READ`` and
      ``fast_path_safety`` declared with all constraints satisfied.
    - Tools with ``gana="gana_ghost"`` are included as before (legacy trust).
    - Tools that fail safety verification are skipped with a warning.
    """
    if _FAST_PATH_FROM_REGISTRY:
        return
    try:
        from whitemagic.tools.registry import get_all_tools
        for td in get_all_tools():
            if td.gana == "gana_ghost":
                _FAST_PATH_FROM_REGISTRY.add(td.name)
            elif td.fast_path:
                if td.fast_path_eligible:
                    _FAST_PATH_FROM_REGISTRY.add(td.name)
                else:
                    logger.warning(
                        "Fast-path safety check failed for '%s' — "
                        "safety=%s, fast_path_safety=%s. Skipping.",
                        td.name, td.safety, td.fast_path_safety,
                    )
    except Exception:
        pass  # Registry not available yet — fall back to explicit set


def _is_fast_path(tool_name: str) -> bool:
    """Check if a tool is safe for fast-path dispatch (bypass heavy middleware).

    A tool is fast-path eligible if:
    1. It's in the explicit _FAST_PATH_TOOLS set, OR
    2. It's declared fast_path=True in the tool registry, OR
    3. It belongs to gana_ghost (all introspection/read-only tools)

    No name-pattern prefix inference is used.
    """
    if tool_name in _FAST_PATH_TOOLS:
        return True
    _ensure_fast_path_registry()
    return tool_name in _FAST_PATH_FROM_REGISTRY


def _fast_path_dispatch(tool_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """Direct dispatch to handler, bypassing middleware pipeline.

    Used for safe READ-only tools where the full 17-stage pipeline overhead
    (circuit breaker, rate limiter, security monitor, cognitive mode, permissions,
    maturity gate, zodiac resonance, citta consciousness, governor, semantic cache,
    inference router, draft review, token tracker, observability, session recorder)
    is unnecessary and causes unacceptable latency for status queries.

    A minimal audit envelope (request_id, tool, duration, status, agent_id) is
    stamped on the result for observability.
    """
    import time as _time
    from uuid import uuid4 as _uuid4

    _ensure_router_cached()
    # Strip pipeline-internal kwargs so they don't leak to handlers
    kwargs.pop("_timeout_s", None)
    kwargs.pop("_force_full_pipeline", None)
    kwargs.pop("_internal_benchmark", None)
    _agent_id = kwargs.pop("_agent_id", "default")
    _request_id = str(_uuid4())[:8]
    _start = _time.monotonic()
    result = None

    # Gana-prefixed tools → gana_invoke
    if tool_name.startswith("gana_") and _gana_invoke is not None:
        try:
            result = _gana_invoke(tool_name=tool_name, args=kwargs)
        except (TypeError, ValueError, AttributeError) as e:
            return {"status": "error", "error_code": "gana_invocation_failed", "message": str(e)}
        except RuntimeError as e:
            return {"status": "error", "error_code": "gana_runtime_error", "message": str(e)}

    # Direct dispatch table lookup
    if result is None:
        handler = DISPATCH_TABLE.get(tool_name)
        if handler is not None:
            try:
                result = handler(**kwargs)
            except Exception as e:
                from whitemagic.tools.errors import ToolExecutionError, classify_exception

                if isinstance(e, ToolExecutionError):
                    return {
                        "status": "error",
                        "error_code": e.error_code,
                        "message": e.message,
                        "retryable": e.retryable,
                    }
                typed = classify_exception(e)
                return {
                    "status": "error",
                    "error_code": typed.error_code,
                    "message": str(e),
                    "retryable": typed.retryable,
                }

    # Bridge fallback
    if result is None and _bridge_execute is not None:
        try:
            result = _bridge_execute(tool_name, **kwargs)
        except Exception as e:

            logger.debug(
                "Bridge fallback failed for %s: %s: %s",
                tool_name,
                type(e).__name__,
                e,
                exc_info=True,
            )

    # Minimal audit envelope
    _elapsed_ms = round((_time.monotonic() - _start) * 1000, 2)
    if isinstance(result, dict):
        result.setdefault("_audit", {
            "request_id": _request_id,
            "tool": tool_name,
            "duration_ms": _elapsed_ms,
            "status": result.get("status", "unknown"),
            "agent_id": _agent_id,
            "fast_path": True,
        })

    return result


def dispatch(tool_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """Dispatch a tool call through the composable middleware pipeline.

    Pipeline (in order):
      1. Input sanitizer   — validate args
      2. Circuit breaker   — fast-fail on cooldown + post-feedback
      3. Rate limiter      — per-agent, per-tool throttling
      4. Security monitor  — anomaly detection
      5. Cognitive mode    — enforce mode-based tool restrictions
      6. Tool permissions  — per-agent RBAC
      7. Maturity gate     — developmental stage gating
      8. Zodiac resonance  — semantic boost for aligned Ganas
      9. Citta consciousness — coherence → Dharma, post-dispatch citta advance + workspace propose
     10. Governor          — ethical validation (coherence-aware)
     11. Semantic cache    — T3: short-circuit repeated inference queries
     12. Inference router  — try edge/local resolution before LLM
     13. Draft-review      — T4: local model drafts, cloud reviews/patches
     14. Token tracker     — universal token tracking via GreenScore
     15. Observability     — Prometheus + OTel metrics
     16. Session recorder  — record conversation turns
     17. Core router       — Gana prefix → dispatch table → bridge fallback

    Fast-path: Safe READ-only tools (status queries, introspection) bypass
    the full pipeline for sub-100ms response times.

    Returns:
        The handler result, or an error dict if no handler matched.
    """
    # Fast-path: bypass middleware for safe READ-only tools
    if _is_fast_path(tool_name) and not kwargs.get("_force_full_pipeline"):
        return _fast_path_dispatch(tool_name, **kwargs)

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
