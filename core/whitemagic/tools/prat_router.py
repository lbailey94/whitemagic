"""PRAT Router — Polymorphic Resonant Adaptive Tools.
====================================================
Collapses 175+ MCP tools into 28 Gana meta-tools.

Each Gana accepts a `tool` parameter naming the specific sub-tool,
plus `args` dict that passes through to the underlying dispatch pipeline.

When WM_MCP_PRAT=1, only the 28 Gana tools are registered with MCP.
AI clients call e.g.:
    gana_ghost(tool="gnosis", args={"compact": true})
instead of:
    gnosis(compact=true)

The Gana handler routes through the existing call_tool() pipeline,
preserving all middleware (circuit breaker, rate limiter, RBAC, etc.).
"""
# ruff: noqa: BLE001

import logging
import os
from typing import Any, cast
from uuid import uuid4

from whitemagic.tools.gana_native_contract import (
    build_native_gana_details,
    normalize_native_gana_result,
)
from whitemagic.tools.prat_mappings import (
    TOOL_TO_GANA,
    get_tools_for_gana,
    try_koka_handler,
)
from whitemagic.tools.vectorized import (
    VectorizedDispatcher,
    is_vectorized_mode,
)

logger = logging.getLogger(__name__)


def _is_quiet_internal_benchmark(
    kwargs: dict[str, Any] | None = None, args: dict[str, Any] | None = None
) -> bool:
    if os.getenv("WM_BENCHMARK_QUIET", "").strip().lower() not in ("1", "true", "yes"):
        return False
    kwargs = kwargs or {}
    args = args or {}
    return bool(kwargs.get("_internal_benchmark") or args.get("_internal_benchmark"))


_RESONANCE_COMPACT_KEYS = (
    "gana",
    "chain_position",
    "successor_hint",
    "vitality_warning",
)

# Tools where sensorium data is relevant and should be included in responses
_SENSORIUM_RELEVANT_TOOLS = frozenset({
    # Session / state tools
    "session_status", "session_bootstrap", "create_session", "focus_session",
    "resume_session", "checkpoint_session",
    "state.current", "state.update", "state.context",
    "state.paths", "state.summary",
    # Health / diagnostic tools
    "health_report", "check", "rust_status", "ship.check",
    # Consciousness / citta tools
    "citta.state", "citta.advance", "citta.stream",
    "coherence.measure", "coherence.drift",
    "depth_gauge", "depth.measure",
    "gnosis", "capabilities", "manifest",
    # Session recorder tools
    "session.record", "session.recall", "session.replay",
    "session.search", "session.memory_stats", "session.backfill",
    "session.continuity", "session.consolidate",
})


def _should_include_sensorium(tool_name: str, kwargs: dict | None = None) -> bool:
    """Check if sensorium data should be included in the response for this tool."""
    if kwargs and kwargs.get("_include_sensorium"):
        return True
    if os.getenv("WM_SENSORIUM_ALL", "").strip().lower() in ("1", "true", "yes"):
        return True
    return tool_name in _SENSORIUM_RELEVANT_TOOLS


def _resonance_verbosity() -> str:
    v = os.getenv("WM_RESONANCE", "").strip().lower()
    if v in ("full", "verbose"):
        return "full"
    if v in ("off", "none", "0"):
        return "off"
    return "compact"


def _project_resonance(meta: dict[str, Any]) -> dict[str, Any]:
    """Project resonance metadata to the configured verbosity.

    ``record_resonance`` always returns the complete block; this trims it to
    what an external agent actually benefits from unless verbose mode is set.
    Returns an empty dict (treated as "no resonance" by callers) when off.
    """
    if not meta:
        return meta
    mode = _resonance_verbosity()
    if mode == "full":
        return meta
    if mode == "off":
        return {}
    return {k: meta[k] for k in _RESONANCE_COMPACT_KEYS if k in meta}


def _normalize_gana_native_result(
    gana_name: str, raw: dict[str, Any]
) -> dict[str, Any]:
    details = build_native_gana_details(
        gana_name,
        operation=raw.get("operation"),
        mode=raw.get("mode"),
        note=raw.get("note"),
        available_tools=raw.get("available_tools"),
        output=raw.get("output"),
        garden=raw.get("garden"),
        garden_status=raw.get("garden_status"),
        mansion=raw.get("mansion"),
        successor_hint=raw.get("successor_hint"),
        execution_ms=raw.get("execution_ms"),
        karma_trace=raw.get("karma_trace"),
        predecessor_context=raw.get("predecessor_context") or raw.get("predecessor"),
        lunar_amplification=raw.get("lunar_amplification"),
        resonance=raw.get("_resonance"),
        koka_latency_ms=raw.get("_koka_latency_ms"),
        koka_path=raw.get("_koka_path"),
        extra={
            key: value
            for key, value in raw.items()
            if key
            not in {
                "status",
                "gana",
                "operation",
                "mode",
                "note",
                "available_tools",
                "output",
                "garden",
                "garden_status",
                "mansion",
                "successor_hint",
                "execution_ms",
                "karma_trace",
                "predecessor_context",
                "predecessor",
                "lunar_amplification",
                "_resonance",
                "_koka_latency_ms",
                "_koka_path",
            }
        },
    )
    return cast(
        dict[str, Any],
        normalize_native_gana_result(
            gana_name,
            request_id=str(uuid4()),
            details=details,
        ),
    )


def build_prat_description(gana_name: str, base_desc: str) -> str:
    """Build a rich description for a PRAT Gana tool listing its nested tools."""
    tools = get_tools_for_gana(gana_name)
    if not tools:
        return base_desc

    tool_list = ", ".join(sorted(tools))
    return f"{base_desc}\n\nNested tools ({len(tools)}): {tool_list}\n\nPass tool='<name>' and args={{...}} to invoke a specific tool."


def build_prat_schema(gana_name: str, tool_registry: list) -> dict:
    """Build a PRAT schema for a Gana with its nested tools enumerated."""
    tools = get_tools_for_gana(gana_name)

    # Build tool descriptions for the enum
    tool_descs = {}
    for td in tool_registry:
        if td.name in tools:
            tool_descs[td.name] = td.description

    tool_enum = sorted(tools) if tools else []

    # Build description lines for each nested tool
    tool_desc_lines = []
    for t in tool_enum:
        desc = tool_descs.get(t, "")
        short = desc[:80] + "..." if len(desc) > 80 else desc
        tool_desc_lines.append(f"  - {t}: {short}")

    tool_help = "\n".join(tool_desc_lines)

    return {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "enum": tool_enum,
                "description": f"Which tool to invoke within this Gana.\n{tool_help}",
            },
            "args": {
                "type": "object",
                "description": "Arguments to pass to the selected tool. See individual tool schemas.",
                "default": {},
            },
            "operation": {
                "type": "string",
                "enum": ["search", "analyze", "transform", "consolidate"],
                "description": "Polymorphic operation (used when no specific tool is specified).",
            },
            "context": {
                "type": "object",
                "description": "Optional resonance context.",
            },
        },
    }


def route_prat_call(
    gana_name: str,
    tool: str | None = None,
    args: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Route a PRAT call through the existing dispatch pipeline
    **with full Gana resonance**.

    Resonance protocol:
    1. Build resonance context (predecessor output, lunar phase, harmony, guna)
    2. Execute the tool call through call_tool()
    3. Record resonance state for the next call
    4. Inject _resonance metadata into the response envelope

    If `tool` is specified, delegates to call_tool(tool, **args).
    Otherwise, falls back to the Gana's native polymorphic operation.

    When ``WM_VECTORIZED=1``, ``tool`` may be a compact glyph string that
    is transparently decoded before dispatch.  The public response still
    carries English; an optional ``_vectorized`` field holds the glyph form.
    """
    from whitemagic.tools.prat_resonance import (
        _GANA_META,
        build_resonance_context,
        record_resonance,
    )
    from whitemagic.tools.unified_api import call_tool

    # ── Vectorized mode: decode glyph tool names ──
    _vd: VectorizedDispatcher | None = None
    _vectorized_meta: dict[str, Any] | None = None
    if is_vectorized_mode() and tool:
        _vd = VectorizedDispatcher()
        decoded_tool, decoded_args = _vd.decode(tool)
        if decoded_tool != tool or decoded_args:
            # Only switch if decode actually changed something
            tool = decoded_tool
            if decoded_args:
                args = {**(args or {}), **decoded_args}
            _vectorized_meta = {"tool_glyph": tool}

    # ── Step 1: Build resonance context before execution ──
    quiet_internal_benchmark = _is_quiet_internal_benchmark(kwargs, args)
    resonance_ctx = build_resonance_context(gana_name)
    mode_hint = resonance_ctx.get("mode_hint", "normal")

    # ── Koka Hot Path: Fast dispatch for 3+ Ganas (S023 VC #8) ──
    _koka_result = try_koka_handler(gana_name, tool, args)
    if _koka_result is not None:
        # Record resonance for Koka path too
        resonance_meta = (
            {}
            if quiet_internal_benchmark
            else _project_resonance(
                record_resonance(gana_name, tool, "koka_dispatch", _koka_result)
            )
        )
        if isinstance(_koka_result, dict):
            _koka_result["_resonance"] = resonance_meta
            _koka_result["_koka_path"] = True
            if tool is None:
                return _normalize_gana_native_result(gana_name, _koka_result)
        return _koka_result

    # ── Wu Xing quadrant boost (Fusion: Wu Xing → Gana) ──
    try:
        import whitemagic.core.fusions as _fusions

        get_wuxing = getattr(_fusions, "get_wuxing_quadrant_boost")
        wuxing_boost = get_wuxing(gana_name)
        resonance_ctx["wuxing_boost"] = wuxing_boost.get("boost_factor", 1.0)
        resonance_ctx["wuxing_boosted"] = wuxing_boost.get("boosted", False)
    except (ImportError, AttributeError, KeyError):
        logger.debug("Optional dependency unavailable: ImportError")

    # ── Garden integration: resolve the Gana's garden ──
    _garden_instance = None
    try:
        meta = _GANA_META.get(gana_name)
        if meta:
            garden_name = meta[3].lower()  # index 3 = garden name
            from whitemagic.gardens import get_garden

            _garden_instance = get_garden(garden_name)
            if _garden_instance and hasattr(_garden_instance, "get_status"):
                resonance_ctx["garden"] = garden_name
                resonance_ctx["garden_status"] = _garden_instance.get_status()
    except (ImportError, AttributeError, IndexError, KeyError, ValueError) as exc:
        logger.debug("Garden lookup for %s: %s", gana_name, exc)

    if tool:
        expected_gana = TOOL_TO_GANA.get(tool)
        if expected_gana and expected_gana != gana_name:
            return {
                "status": "error",
                "error": f"Tool '{tool}' belongs to {expected_gana}, not {gana_name}.",
                "hint": f"Call {expected_gana}(tool='{tool}', args=...) instead.",
            }

        # ── Leap 7: Zig dispatch pre-check (rate limit, circuit breaker, maturity) ──
        # Diagnostic tools are always allowed regardless of Zig dispatch state
        _DIAGNOSTIC_TOOLS = {
            "capabilities",
            "manifest",
            "state_paths",
            "state_summary",
            "repo_summary",
            "ship_check",
            "health_report",
            "gnosis",
            "get_telemetry_summary",
            "tool_usage_stats",
            "rust_status",
            "tool_graph",
            "tool_graph_full",
        }

        if tool not in _DIAGNOSTIC_TOOLS:
            try:
                from whitemagic.core.acceleration.dispatch_bridge import (
                    DispatchResult,
                    get_dispatch,
                )

                dispatch = get_dispatch()
                meta = _GANA_META.get(gana_name)
                engine_slot = (
                    (meta[0] - 1) if meta else None
                )  # mansion_num is 1-indexed, slots are 0-indexed
                if engine_slot is not None and 0 <= engine_slot < 28:
                    check = dispatch.check(engine_slot)
                    if check != DispatchResult.ALLOW:
                        return {
                            "status": "error",
                            "error_code": f"dispatch_{check.name.lower()}",
                            "message": f"Tool '{tool}' blocked by Zig dispatch: {check.name}",
                            "gana": gana_name,
                            "retryable": check != DispatchResult.IMMATURE,
                        }
            except (ImportError, AttributeError, IndexError, TypeError):
                logger.debug("Optional dependency unavailable: ImportError")

        # ── Step 2: Route through existing dispatch pipeline ──
        tool_args = args or {}

        # Inject resonance context into args if the tool accepts it
        if kwargs.get("context"):
            tool_args.setdefault("_resonance_context", kwargs["context"])

        _call_start = __import__("time").time()
        _call_success = False
        try:
            result = call_tool(tool, **tool_args)
            _call_success = not (
                isinstance(result, dict) and result.get("status") == "error"
            )
            # Token economy: estimate tokens from result size
            try:
                from whitemagic.core.consciousness.token_economy import (
                    get_token_tracker,
                )

                _econ = get_token_tracker()
                _result_tokens = max(1, len(str(result)) // 4) if result else 0
                _input_tokens = max(1, len(str(tool_args)) // 4) if tool_args else 0
                _econ.record_usage(
                    _input_tokens + _result_tokens,
                    source="api",
                    operation=f"prat:{gana_name}:{tool}",
                )
            except (ImportError, AttributeError, TypeError):
                logger.debug("Optional dependency unavailable: ImportError")
        except (ValueError, KeyError, TypeError) as e:
            # Known tool execution errors
            _call_success = False
            try:
                from whitemagic.tools.gana_vitality import get_vitality_monitor

                get_vitality_monitor().record_call(
                    gana_name,
                    success=False,
                    latency_ms=(__import__("time").time() - _call_start) * 1000,
                )
            except (ImportError, AttributeError):
                logger.debug("Optional dependency unavailable: ImportError")
            return {
                "status": "error",
                "error": str(e),
                "tool": tool,
                "gana": gana_name,
                "error_code": "tool_execution_failed",
                "suggestion": (
                    f"Call failed inside {gana_name}. "
                    "Use gan.a_ghost (list_ganas) to confirm this tool exists, "
                    "gan.a_ghost (vitality) to check vitality, or "
                    "gan.a_root (ship.check) to validate environment state."
                ),
            }
        except (ImportError, ModuleNotFoundError) as e:
            # Unexpected error - log and return
            logger.exception("Unexpected error calling tool %s", tool)
            _call_success = False
            try:
                from whitemagic.tools.gana_vitality import get_vitality_monitor

                get_vitality_monitor().record_call(
                    gana_name,
                    success=False,
                    latency_ms=(__import__("time").time() - _call_start) * 1000,
                )
            except (ImportError, AttributeError):
                logger.debug("Optional dependency unavailable: ImportError")
            return {
                "status": "error",
                "error": f"Tool execution failed: {type(e).__name__}",
                "tool": tool,
                "gana": gana_name,
                "error_code": "module_missing",
                "suggestion": (
                    f"Missing dependency for {gana_name}. "
                    "Try gan.a_root (ship.check) to validate, "
                    "or gan.a_root (state.paths) to inspect environment."
                ),
            }

        # ── Step 3: Record resonance state ──
        resonance_meta = (
            {}
            if quiet_internal_benchmark
            else _project_resonance(record_resonance(gana_name, tool, None, result))
        )

        # ── Fusion: Resonance → Emotion/Drive ──
        try:
            if not quiet_internal_benchmark:
                from whitemagic.core.fusions import modulate_drive_from_resonance

                modulate_drive_from_resonance(gana_name, tool)
        except (ImportError, ModuleNotFoundError):
            logger.debug("Optional dependency unavailable: ImportError")

        # ── Garden notification: record the tool call ──
        if _garden_instance:
            try:
                if hasattr(_garden_instance, "record_tool_call"):
                    _garden_instance.record_tool_call(tool, tool_args, result)
                if hasattr(_garden_instance, "emit"):
                    from whitemagic.core.resonance.gan_ying_enhanced import EventType

                    _garden_instance.emit(
                        EventType.GARDEN_ACTIVITY,
                        {  # type: ignore[attr-defined]
                            "action": "prat_tool_call",
                            "gana": gana_name,
                            "tool": tool,
                        },
                    )
            except (ImportError, AttributeError, KeyError, TypeError):
                logger.debug("Optional dependency unavailable: ImportError")

        # ── Step 4: Inject resonance into response ──
        if isinstance(result, dict):
            if resonance_meta:
                result["_resonance"] = resonance_meta
            if _garden_instance:
                result["_garden"] = resonance_ctx.get("garden", "unknown")
        else:
            result = {
                "result": result,
            }
            if resonance_meta:
                result["_resonance"] = resonance_meta
            if _garden_instance:
                result["_garden"] = resonance_ctx.get("garden", "unknown")

        # ── Gana Vitality: record call outcome (12.108.20 + 12.108.29) ──
        try:
            from whitemagic.tools.gana_vitality import get_vitality_monitor

            get_vitality_monitor().record_call(
                gana_name,
                success=_call_success,
                latency_ms=(__import__("time").time() - _call_start) * 1000,
            )
        except (ImportError, ModuleNotFoundError):
            logger.debug("Optional dependency unavailable: ImportError")

        # ── v14: Speculative prefetch — record transition, predict next ──
        try:
            if not quiet_internal_benchmark:
                from whitemagic.tools.speculative_prefetch import get_prefetcher

                get_prefetcher().on_call_complete(gana_name)
        except (ImportError, ModuleNotFoundError):
            logger.debug("Optional dependency unavailable: ImportError")

        # ── Vectorized mode: attach glyph metadata ──
        if _vectorized_meta and isinstance(result, dict):
            result["_vectorized"] = _vectorized_meta

        return result

    # No specific tool — use native Gana operation with resonance
    operation = kwargs.get("operation", "search")

    native_result = {
        "status": "success",
        "gana": gana_name,
        "operation": operation,
        "mode": mode_hint,
        "note": f"Native {gana_name} {operation} operation. Specify tool='<name>' for a specific sub-tool.",
        "available_tools": get_tools_for_gana(gana_name),
    }

    if _garden_instance:
        native_result["garden"] = resonance_ctx.get("garden", "unknown")
        if hasattr(_garden_instance, "get_status"):
            try:
                native_result["garden_status"] = _garden_instance.get_status()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

    if resonance_ctx.get("predecessor"):
        native_result["predecessor_context"] = resonance_ctx["predecessor"]

    # Lunar amplification note
    if resonance_ctx.get("lunar_amplification"):
        native_result["lunar_amplification"] = resonance_ctx["lunar_amplification"]

    # Record resonance for native operations too
    resonance_meta = (
        {}
        if quiet_internal_benchmark
        else _project_resonance(
            record_resonance(gana_name, None, operation, native_result)
        )
    )
    if resonance_meta:
        native_result["_resonance"] = resonance_meta

    # ── Gana Vitality: record native operation ──
    try:
        from whitemagic.tools.gana_vitality import get_vitality_monitor

        get_vitality_monitor().record_call(gana_name, success=True)
    except (ImportError, ModuleNotFoundError):
        logger.debug("Optional dependency unavailable: ImportError")

    # ── Fusion: Resonance → Emotion/Drive (native ops too) ──
    try:
        if not quiet_internal_benchmark:
            from whitemagic.core.fusions import modulate_drive_from_resonance

            modulate_drive_from_resonance(gana_name, None)
    except (ImportError, ModuleNotFoundError):
        logger.debug("Optional dependency unavailable: ImportError")

    return _normalize_gana_native_result(gana_name, native_result)


def validate_mapping(tool_registry: list) -> dict[str, Any]:
    """Check that all non-Gana tools are mapped to a Gana.

    A PRAT mapping is considered valid if the tool exists in either
    the formal registry OR the dispatch table (many sub-tools are
    internal and accessed through Gana meta-tools without needing
    their own registry entry).
    """
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE

    mapped = set(TOOL_TO_GANA.keys())
    all_tools = set()
    gana_tools = set()

    for td in tool_registry:
        all_tools.add(td.name)
        if td.name.startswith("gana_"):
            gana_tools.add(td.name)

    # Dispatch tools are also valid (internal sub-tools)
    known_tools = all_tools | set(DISPATCH_TABLE.keys())

    non_gana = all_tools - gana_tools
    unmapped = non_gana - mapped
    orphaned = mapped - known_tools  # In PRAT but not in registry OR dispatch

    return {
        "total_tools": len(all_tools),
        "gana_tools": len(gana_tools),
        "non_gana_tools": len(non_gana),
        "mapped": len(mapped & non_gana),
        "unmapped": sorted(unmapped),
        "orphaned": sorted(orphaned),
    }
