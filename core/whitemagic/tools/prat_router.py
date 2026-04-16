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

import logging
import os
from typing import Any, cast
from uuid import uuid4

from whitemagic.tools.gana_native_contract import (
    build_native_gana_details,
    normalize_native_gana_result,
)

# Import extracted tool mappings
from whitemagic.tools.prat_mappings import (
    TOOL_TO_GANA,
    get_tools_for_gana,
    try_koka_handler,
)

logger = logging.getLogger(__name__)


def _is_quiet_internal_benchmark(kwargs: dict[str, Any] | None = None, args: dict[str, Any] | None = None) -> bool:
    if os.getenv("WM_BENCHMARK_QUIET", "").strip().lower() not in ("1", "true", "yes"):
        return False
    kwargs = kwargs or {}
    args = args or {}
    return bool(kwargs.get("_internal_benchmark") or args.get("_internal_benchmark"))


def _normalize_gana_native_result(gana_name: str, raw: dict[str, Any]) -> dict[str, Any]:
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
            if key not in {
                "status", "gana", "operation", "mode", "note", "available_tools",
                "output", "garden", "garden_status", "mansion", "successor_hint",
                "execution_ms", "karma_trace", "predecessor_context", "predecessor",
                "lunar_amplification", "_resonance", "_koka_latency_ms", "_koka_path",
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


def route_prat_call(gana_name: str, tool: str | None = None,
                    args: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route a PRAT call through the existing dispatch pipeline
    **with full Gana resonance**.

    Resonance protocol:
    1. Build resonance context (predecessor output, lunar phase, harmony, guna)
    2. Execute the tool call through call_tool()
    3. Record resonance state for the next call
    4. Inject _resonance metadata into the response envelope

    If `tool` is specified, delegates to call_tool(tool, **args).
    Otherwise, falls back to the Gana's native polymorphic operation.
    """
    from whitemagic.tools.prat_resonance import (
        _GANA_META,
        build_resonance_context,
        record_resonance,
    )
    from whitemagic.tools.unified_api import call_tool

    # ── Step 1: Build resonance context before execution ──
    quiet_internal_benchmark = _is_quiet_internal_benchmark(kwargs, args)
    resonance_ctx = build_resonance_context(gana_name)
    mode_hint = resonance_ctx.get("mode_hint", "normal")

    # ── Koka Hot Path: Fast dispatch for 3+ Ganas (S023 VC #8) ──
    _koka_result = try_koka_handler(gana_name, tool, args)
    if _koka_result is not None:
        # Record resonance for Koka path too
        resonance_meta = {} if quiet_internal_benchmark else record_resonance(gana_name, tool, "koka_dispatch", _koka_result)
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
        pass

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
    except (ImportError, AttributeError, IndexError, KeyError) as exc:
        logger.debug("Garden lookup for %s: %s", gana_name, exc)

    if tool:
        # Validate that this tool belongs to this Gana
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
            "capabilities", "manifest", "state_paths", "state_summary",
            "repo_summary", "ship_check", "health_report", "gnosis",
            "get_telemetry_summary", "rust_status", "tool_graph", "tool_graph_full",
        }

        if tool not in _DIAGNOSTIC_TOOLS:
            try:
                from whitemagic.core.acceleration.dispatch_bridge import (
                    DispatchResult,
                    get_dispatch,
                )
                dispatch = get_dispatch()
                meta = _GANA_META.get(gana_name)
                engine_slot = (meta[0] - 1) if meta else None  # mansion_num is 1-indexed, slots are 0-indexed
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
                pass  # Dispatch pre-check is optional

        # ── Step 2: Route through existing dispatch pipeline ──
        tool_args = args or {}

        # Inject resonance context into args if the tool accepts it
        if kwargs.get("context"):
            tool_args.setdefault("_resonance_context", kwargs["context"])

        _call_start = __import__("time").time()
        _call_success = False
        try:
            result = call_tool(tool, **tool_args)
            _call_success = not (isinstance(result, dict) and result.get("status") == "error")
        except (ValueError, KeyError, TypeError) as e:
            # Known tool execution errors
            _call_success = False
            try:
                from whitemagic.tools.gana_vitality import get_vitality_monitor
                get_vitality_monitor().record_call(
                    gana_name, success=False,
                    latency_ms=(__import__("time").time() - _call_start) * 1000,
                )
            except (ImportError, AttributeError):
                pass
            return {"status": "error", "error": str(e), "tool": tool}
        except (ImportError, ModuleNotFoundError) as e:
            # Unexpected error - log and return
            logger.exception("Unexpected error calling tool %s", tool)
            _call_success = False
            try:
                from whitemagic.tools.gana_vitality import get_vitality_monitor
                get_vitality_monitor().record_call(
                    gana_name, success=False,
                    latency_ms=(__import__("time").time() - _call_start) * 1000,
                )
            except (ImportError, AttributeError):
                pass
            return {"status": "error", "error": f"Tool execution failed: {type(e).__name__}", "tool": tool}

        # ── Step 3: Record resonance state ──
        resonance_meta = {} if quiet_internal_benchmark else record_resonance(gana_name, tool, None, result)

        # ── Fusion: Resonance → Emotion/Drive ──
        try:
            if not quiet_internal_benchmark:
                from whitemagic.core.fusions import modulate_drive_from_resonance
                modulate_drive_from_resonance(gana_name, tool)
        except (ImportError, ModuleNotFoundError):
            pass

        # ── Garden notification: record the tool call ──
        if _garden_instance:
            try:
                if hasattr(_garden_instance, "record_tool_call"):
                    _garden_instance.record_tool_call(tool, tool_args, result)
                if hasattr(_garden_instance, "emit"):
                    from whitemagic.core.resonance.gan_ying_enhanced import EventType
                    _garden_instance.emit(EventType.GARDEN_ACTIVITY, {  # type: ignore[attr-defined]
                        "action": "prat_tool_call",
                        "gana": gana_name,
                        "tool": tool,
                    })
            except (ImportError, AttributeError, KeyError, TypeError):
                pass

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
                gana_name, success=_call_success,
                latency_ms=(__import__("time").time() - _call_start) * 1000,
            )
        except (ImportError, ModuleNotFoundError):
            pass

        # ── v14: Speculative prefetch — record transition, predict next ──
        try:
            if not quiet_internal_benchmark:
                from whitemagic.tools.speculative_prefetch import get_prefetcher
                get_prefetcher().on_call_complete(gana_name)
        except (ImportError, ModuleNotFoundError):
            pass

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

    # Add garden context to native operations
    if _garden_instance:
        native_result["garden"] = resonance_ctx.get("garden", "unknown")
        if hasattr(_garden_instance, "get_status"):
            try:
                native_result["garden_status"] = _garden_instance.get_status()
            except Exception:
                pass

    # Add predecessor context to native operations
    if resonance_ctx.get("predecessor"):
        native_result["predecessor_context"] = resonance_ctx["predecessor"]

    # Lunar amplification note
    if resonance_ctx.get("lunar_amplification"):
        native_result["lunar_amplification"] = resonance_ctx["lunar_amplification"]

    # Record resonance for native operations too
    resonance_meta = {} if quiet_internal_benchmark else record_resonance(gana_name, None, operation, native_result)
    if resonance_meta:
        native_result["_resonance"] = resonance_meta

    # ── Gana Vitality: record native operation ──
    try:
        from whitemagic.tools.gana_vitality import get_vitality_monitor
        get_vitality_monitor().record_call(gana_name, success=True)
    except (ImportError, ModuleNotFoundError):
        pass

    # ── Fusion: Resonance → Emotion/Drive (native ops too) ──
    try:
        if not quiet_internal_benchmark:
            from whitemagic.core.fusions import modulate_drive_from_resonance
            modulate_drive_from_resonance(gana_name, None)
    except (ImportError, ModuleNotFoundError):
        pass

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
