"""Dispatch Middleware — Composable Pipeline for Tool Invocation.
==============================================================
Each middleware is a function::

    (ctx: DispatchContext, next_fn: NextFn) -> Optional[Dict[str, Any]]

Middlewares can:
  - **Short-circuit**: return a result without calling ``next_fn()``
  - **Pass through**: call ``next_fn(ctx)`` to continue the chain
  - **Post-process**: call ``result = next_fn(ctx)``, modify result, return it

The pipeline is built declaratively::

    pipeline = DispatchPipeline()
    pipeline.use("sanitizer", mw_input_sanitizer)
    pipeline.use("breaker",   mw_circuit_breaker)
    pipeline.use("router",    mw_core_router)
    result = pipeline.execute("gnosis", compact=True)

The ``DispatchContext`` carries mutable state through the chain so
middlewares can share data (e.g. the circuit breaker instance for
post-processing feedback).
"""
# ruff: noqa: BLE001

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from whitemagic.runtime_status import get_runtime_status

logger = logging.getLogger(__name__)

_sanitize_tool_args: Callable[..., Any] | None = None
_get_breaker_registry: Callable[[], Any] | None = None
_get_rate_limiter: Callable[..., Any] | None = None
_check_tool_permission: Callable[..., bool] | None = None
_check_maturity_for_tool: Callable[..., bool] | None = None
_get_security_monitor: Callable[[], Any] | None = None
_get_governor: Callable[..., Any] | None = None
_compact_fn: Callable[..., dict[str, Any]] | None = None
_get_prometheus: Callable[[], Any] | None = None
_get_otel: Callable[[], Any] | None = None
_get_edge_inference: Callable[[], Any] | None = None
_reason_locally: Callable[..., Any] | None = None
_get_green_score: Callable[[], Any] | None = None
_cached: bool = False


def _ensure_cached() -> None:
    """Load all middleware dependencies once.  Safe to call multiple times."""
    global _sanitize_tool_args, _get_breaker_registry, _get_rate_limiter
    global _check_tool_permission, _check_maturity_for_tool
    global _get_security_monitor, _get_governor, _compact_fn, _cached
    global _get_prometheus, _get_otel
    global _get_edge_inference, _reason_locally, _get_green_score
    if _cached:
        return
    try:
        from whitemagic.tools.input_sanitizer import sanitize_tool_args

        _sanitize_tool_args = sanitize_tool_args
    except Exception as e:
        logger.debug("Middleware: input_sanitizer dependency missing: %s", e)
    try:
        from whitemagic.tools.circuit_breaker import get_breaker_registry

        _get_breaker_registry = get_breaker_registry
    except Exception as e:
        logger.debug("Middleware: circuit_breaker dependency missing: %s", e)
    try:
        from whitemagic.tools.rate_limiter import get_rate_limiter

        _get_rate_limiter = get_rate_limiter
    except Exception as e:
        logger.debug("Middleware: rate_limiter dependency missing: %s", e)
    try:
        from whitemagic.tools.tool_permissions import check_tool_permission

        _check_tool_permission = check_tool_permission  # type: ignore[assignment]
    except Exception as e:
        logger.debug("Middleware: tool_permissions dependency missing: %s", e)
    try:
        from whitemagic.tools.maturity_check import check_maturity_for_tool

        _check_maturity_for_tool = check_maturity_for_tool  # type: ignore[assignment]
    except Exception as e:
        logger.debug("Middleware: maturity_check dependency missing: %s", e)
    try:
        from whitemagic.security.security_breaker import get_security_monitor

        _get_security_monitor = get_security_monitor
    except Exception as e:
        logger.debug("Middleware: security_breaker dependency missing: %s", e)
    try:
        from whitemagic.core.governor import get_governor

        _get_governor = get_governor
    except Exception as e:
        try:
            from whitemagic.dharma.governor import (  # type: ignore[assignment]
                get_governor,
            )

            _get_governor = get_governor
        except (ImportError, AttributeError):
            pass
        logger.debug("Middleware: governor dependency missing: %s", e)
    try:
        from whitemagic.core.monitoring.prometheus_export import get_prometheus

        _get_prometheus = get_prometheus
    except Exception as e:
        logger.debug("Middleware: prometheus_export dependency missing: %s", e)
    try:
        from whitemagic.core.monitoring.otel_export import get_otel

        _get_otel = get_otel
    except Exception as e:
        logger.debug("Middleware: otel_export dependency missing: %s", e)
    try:
        from whitemagic.tools.compact_response import compact as _compact_impl

        _compact_fn = _compact_impl
    except (ImportError, AttributeError):
        pass
    try:
        from whitemagic.edge.inference import get_edge_inference

        _get_edge_inference = get_edge_inference
    except Exception as e:
        logger.debug("Middleware: edge_inference dependency missing: %s", e)
    try:
        from whitemagic.core.intelligence.agentic.local_reasoning import reason_locally

        _reason_locally = reason_locally
    except Exception as e:
        logger.debug("Middleware: local_reasoning dependency missing: %s", e)
    try:
        from whitemagic.core.monitoring.green_score import get_green_score

        _get_green_score = get_green_score
    except Exception as e:
        logger.debug("Middleware: green_score dependency missing: %s", e)
    _cached = True


NextFn = Callable[["DispatchContext"], dict[str, Any] | None]
MiddlewareFn = Callable[["DispatchContext", NextFn], dict[str, Any] | None]


@dataclass
class DispatchContext:
    """Mutable context that flows through the middleware chain."""

    tool_name: str
    kwargs: dict[str, Any]
    agent_id: str = "default"
    compact: bool = False
    # When True, Zig dispatch already validated circuit breaker, rate limit,
    # and maturity — Python middleware can skip those redundant checks.
    zig_prevalidated: bool = False
    # Stash for cross-middleware communication (e.g. circuit breaker ref)
    meta: dict[str, Any] = field(default_factory=dict)


class DispatchPipeline:
    """Composable middleware chain for tool dispatch.

    Middlewares execute in registration order.  Each can short-circuit
    by returning a result, or call ``next_fn(ctx)`` to continue.
    """

    def __init__(self) -> None:
        self._middlewares: list[tuple[str, MiddlewareFn]] = []
        self._chain: NextFn | None = (
            None  # Pre-built chain (frozen after first execute)
        )

    def use(self, name: str, middleware: MiddlewareFn) -> DispatchPipeline:
        """Register a middleware.  Order matters — first registered runs first."""
        self._middlewares.append((name, middleware))
        self._chain = None  # Invalidate pre-built chain
        return self

    def _build_chain(self) -> NextFn:
        """Build the closure chain once from registered middlewares."""
        chain: NextFn = _terminal
        for name, mw in reversed(self._middlewares):
            chain = _wrap(mw, chain, name)
        return chain

    def execute(self, tool_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Execute the full pipeline for a tool call."""
        quiet_internal_benchmark = bool(kwargs.get("_internal_benchmark", False))
        ctx = DispatchContext(
            tool_name=tool_name,
            kwargs=kwargs,
            agent_id=kwargs.pop("_agent_id", "default"),
            compact=kwargs.pop("_compact", False),
            zig_prevalidated=bool(kwargs.pop("_zig_prevalidated", False)),
        )
        if quiet_internal_benchmark:
            ctx.meta["quiet_internal_benchmark"] = True

        # Use pre-built chain (built once, reused for all calls)
        if self._chain is None:
            self._chain = self._build_chain()

        result = self._chain(ctx)

        # Post-pipeline: compact response mode
        if ctx.compact and isinstance(result, dict) and _compact_fn is not None:
            try:
                result = _compact_fn(result)
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(
                    "Middleware: compaction failed for %s: %s",
                    ctx.tool_name,
                    e,
                    exc_info=True,
                )
            except RuntimeError as e:
                logger.warning(
                    "Middleware: unexpected compaction runtime error for %s: %s",
                    ctx.tool_name,
                    e,
                    exc_info=True,
                )

        return result

    def describe(self) -> list[str]:
        """Return middleware names in registration order (for introspection)."""
        return [name for name, _ in self._middlewares]


def _terminal(ctx: DispatchContext) -> dict[str, Any] | None:
    """End of chain — no handler found."""
    runtime_status = get_runtime_status()
    return {
        "status": "error",
        "error_code": "tool_not_found",
        "message": f"Tool {ctx.tool_name} not yet implemented in unified_api or bridge",
        "degraded_mode": runtime_status.get("degraded_mode", False),
        "degraded_reasons": runtime_status.get("degraded_reasons", []),
        "resolution": {
            "suggested_action": "verify_tool_name_or_use_prat_gana",
            "debug_hint": "Set WM_DEBUG=1 for verbose diagnostics",
        },
    }


def _wrap(mw: MiddlewareFn, next_fn: NextFn, name: str) -> NextFn:
    """Wrap a middleware + next into a single NextFn with safety net."""

    def wrapped(ctx: DispatchContext) -> dict[str, Any] | None:
        """
        Perform the wrapped operation.

        Args:
            ctx: Parameter description.

        Returns:
            dict[str, Any] | None
        """
        try:
            return mw(ctx, next_fn)
        except Exception as e:
            # Re-raise explicit tool execution errors so they aren't swallowed
            # by the middleware fallback logic.
            if e.__class__.__name__ == "ToolExecutionError":
                raise
            # Log middleware errors at WARNING level for visibility
            logger.warning(
                "Middleware '%s' error: %s: %s",
                name,
                e.__class__.__name__,
                e,
                exc_info=True,
            )
            # Record error in context for downstream inspection
            if "middleware_errors" not in ctx.meta:
                ctx.meta["middleware_errors"] = []
            ctx.meta["middleware_errors"].append(
                {"middleware": name, "error": str(e), "type": e.__class__.__name__}
            )
            return next_fn(ctx)

    return wrapped


def mw_input_sanitizer(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Validate tool arguments before any processing."""
    _ensure_cached()
    if _sanitize_tool_args is not None:
        try:
            result = _sanitize_tool_args(ctx.tool_name, ctx.kwargs)
            if result is not None:
                return cast(dict[str, Any], result)
        except Exception as e:
            logger.debug(
                "Input sanitizer failed for %s: %s", ctx.tool_name, e, exc_info=True
            )
    return next_fn(ctx)


def mw_circuit_breaker(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Fast-fail if tool is in cooldown; record success/failure afterward."""
    _ensure_cached()
    breaker = None
    if _get_breaker_registry is not None:
        try:
            breaker = _get_breaker_registry().get(ctx.tool_name)
            # Skip pre-check if Zig dispatch already validated circuit state
            if breaker is not None and not ctx.zig_prevalidated and breaker.is_open():
                calm = breaker.calm_response()
                if calm is not None:
                    return cast(dict[str, Any], calm)
        except (ImportError, AttributeError, ValueError, RuntimeError) as e:
            logger.debug(
                "Middleware: circuit breaker lookup failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
            breaker = None

    result = next_fn(ctx)

    # Post-processing: breaker feedback
    if breaker is not None and isinstance(result, dict):
        try:
            status_val = str(result.get("status", "")).lower()
            if status_val in ("success", "ok"):
                breaker.record_success()
            elif status_val == "error":
                breaker.record_failure()
        except Exception as exc:
            logger.debug("Circuit breaker status recording failed: %s", exc)

    return result


def mw_observability(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Record tool metrics to Prometheus and OpenTelemetry."""
    import time

    _ensure_cached()

    start = time.perf_counter()
    result = next_fn(ctx)
    duration = time.perf_counter() - start

    # Determine status
    status = "success"
    if isinstance(result, dict):
        status_val = str(result.get("status", "")).lower()
        if status_val == "error":
            status = "error"

    # Record to Prometheus
    if _get_prometheus is not None:
        try:
            _get_prometheus().record_tool_call(ctx.tool_name, duration, status)
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: prometheus recording failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )

    # Record to OTel
    if _get_otel is not None:
        try:
            _get_otel().record_tool_span(ctx.tool_name, duration, status)
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: otel recording failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )

    return result


def mw_rate_limiter(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Per-agent, per-tool rate limiting."""
    if ctx.zig_prevalidated:
        return next_fn(ctx)  # Zig already checked rate limit
    _ensure_cached()
    if _get_rate_limiter is not None:
        try:
            limiter = _get_rate_limiter()
            result = limiter.check(ctx.agent_id, ctx.tool_name)
            if result is not None:
                return result
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: rate limit check failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
    return next_fn(ctx)


def mw_tool_permissions(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Per-agent RBAC permission check."""
    _ensure_cached()
    if _check_tool_permission is not None:
        try:
            perm_result = _check_tool_permission(ctx.agent_id, ctx.tool_name)
            if perm_result is not None:
                return perm_result  # type: ignore[return-value]
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: permission check failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
    return next_fn(ctx)


def mw_maturity_gate(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Block tools that require a higher maturity stage than currently reached."""
    if ctx.zig_prevalidated:
        return next_fn(ctx)  # Zig already checked maturity
    _ensure_cached()
    if _check_maturity_for_tool is not None:
        try:
            mat_result = _check_maturity_for_tool(ctx.tool_name)
            if mat_result is not None:
                return mat_result  # type: ignore[return-value]
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: maturity check failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
    return next_fn(ctx)


def mw_security_monitor(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Edgerunner Violet: anomaly detection for suspicious tool-call patterns."""
    _ensure_cached()
    quiet_internal = os.getenv("WM_BENCHMARK_QUIET", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    quiet_internal = quiet_internal and bool(
        ctx.meta.get("quiet_internal_benchmark", False)
    )
    if _get_security_monitor is not None and not quiet_internal:
        try:
            safety = ctx.kwargs.get("safety", "READ")
            if not isinstance(safety, str):
                safety = "READ"
            # Extract content from common kwargs for content-aware detection
            content = None
            for key in ("content", "query", "prompt", "text", "message", "input", "action", "description", "thought"):
                val = ctx.kwargs.get(key)
                if isinstance(val, str) and len(val) > 3:
                    content = val
                    break
            alert = _get_security_monitor().record_call(
                tool=ctx.tool_name,
                safety=safety,
                agent_id=ctx.agent_id,
                content=content,
            )
            if alert and alert.get("action") == "block":
                return {
                    "status": "error",
                    "error_code": "security_breaker",
                    "message": f"Security monitor blocked: {alert.get('detail', 'anomaly detected')}",
                    "alert": alert,
                }
        except (AttributeError, KeyError, ValueError) as e:
            logger.debug(
                "Security monitor call recording failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
        except RuntimeError as e:
            logger.warning("Security monitor runtime failure: %s", e, exc_info=True)
    return next_fn(ctx)


def mw_governor(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Ethical gate — Governor validates the tool call."""
    _ensure_cached()
    if _get_governor is not None:
        try:
            gov = _get_governor()
            validation = gov.validate_tool_call(ctx.tool_name, ctx.kwargs)
            if not validation.safe:
                try:
                    from whitemagic.tools.unified_api import _emit_gan_ying

                    _emit_gan_ying(
                        "GOVERNOR_BLOCKED",
                        {
                            "tool": ctx.tool_name,
                            "reason": validation.reason,
                        },
                    )
                except (ImportError, AttributeError, RuntimeError) as e:
                    logger.debug(
                        "Middleware: governor gan-ying emit failed: %s",
                        e,
                        exc_info=True,
                    )
                return {
                    "status": "error",
                    "error": f"Governor Blocked: {validation.reason}",
                    "risk_level": validation.risk_level.name,
                }
        except (AttributeError, RuntimeError) as e:
            logger.debug(
                "Middleware: governor validation failed for %s: %s",
                ctx.tool_name,
                e,
                exc_info=True,
            )
    return next_fn(ctx)


def mw_cognitive_mode(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Enforce cognitive mode tool restrictions.

    GUARDIAN mode blocks write/destructive tools (read-only safety).
    Other modes inject preferred/avoided hints into context metadata
    but do not hard-block — only GUARDIAN enforces.
    """
    try:
        from whitemagic.core.intelligence.cognitive_modes import get_cognitive_modes

        cm = get_cognitive_modes()
        mode = cm._effective_mode()

        # GUARDIAN mode: hard-block avoided tools
        if mode.value == "guardian":
            if cm.is_tool_avoided(ctx.tool_name):
                return {
                    "status": "error",
                    "error_code": "cognitive_mode_blocked",
                    "message": f"Tool '{ctx.tool_name}' blocked in GUARDIAN mode (read-only)",
                    "mode": "guardian",
                }

        # Inject mode hints into context for downstream use
        ctx.meta["cognitive_mode"] = mode.value
        hints = cm.get_tool_hints()
        ctx.meta["cognitive_preferred"] = hints["preferred_tools"]
        ctx.meta["cognitive_context_multiplier"] = hints["context_multiplier"]
    except Exception as e:
        logger.debug(
            "Middleware: cognitive mode check failed for %s: %s",
            ctx.tool_name,
            e,
            exc_info=True,
        )
    return next_fn(ctx)


def mw_sutra_auto_execute(
    ctx: DispatchContext, next_fn: NextFn
) -> dict[str, Any] | None:
    """Dharma-gated Auto-Execution (GATED: disabled by default).
    Checks the Sutra Kernel to determine if a tool can auto-execute without human approval.
    - Sattvic (Read/Observe): Auto-executes immediately.
    - Rajasic (Write/Create): Auto-executes if intent is high, logs to Zodiac Ledger.
    - Tamasic (Delete/Destructive): Blocked/Paused, sent to Nexus UI via Iceoryx2 for explicit consent.

    NOTE: This middleware is disabled by default. Enable with WM_ENABLE_SUTRA_AUTO_EXECUTE=1.
    """
    # Gate behind feature flag - disabled by default as Sutra Kernel is not fully integrated
    if os.environ.get("WM_ENABLE_SUTRA_AUTO_EXECUTE", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        return next_fn(ctx)

    try:
        from whitemagic.core.bridge.sutra_bridge import get_sutra_kernel

        sutra = get_sutra_kernel()

        # We estimate intent and karma from the tool metadata or context
        # (For now, use defaults or dummy values, real implementation would extract from Gnosis/Karma)
        verdict = sutra.evaluate_action(
            action_type=ctx.tool_name, intent_score=1.0, karma_debt=0.0
        )

        if verdict.startswith("Panic") or verdict.startswith("Intervene"):
            # Block and push to UI for Karmic Consent
            try:
                from whitemagic.core.ipc_bridge import publish_json

                publish_json(
                    "wm/commands",
                    {
                        "type": "karmic_consent_required",
                        "tool": ctx.tool_name,
                        "reason": verdict,
                    },
                )
            except Exception as e:
                logger.warning(
                    "Failed to push consent to Nexus UI: %s", e, exc_info=True
                )

            return {
                "status": "paused",
                "error": f"Sutra Kernel Intervention: {verdict}. Awaiting Karmic Consent.",
                "action_required": "user_approval",
            }
    except ImportError as e:
        logger.debug(
            "Middleware: sutra_bridge missing for %s: %s",
            ctx.tool_name,
            e,
            exc_info=True,
        )
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning(
            "Middleware: sutra_auto_execute unexpected error: %s", e, exc_info=True
        )
        logger.warning("Sutra Auto-Execute Middleware failed: %s", e, exc_info=True)

    return next_fn(ctx)


def mw_zodiac_resonance(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Milestone 3.1: Inject Zodiacal Resonance boosts (Native Resonance) for aligned Ganas.

    Checks if the tool (or its parent Gana) belongs to a mansion currently aligned
    with the 12-phase Zodiacal Clock cycle.
    """
    try:
        from whitemagic.core.zodiac import get_zodiac_clock
        from whitemagic.tools.prat_mappings import get_gana_for_tool
        from whitemagic.tools.prat_resonance import _GANA_META

        # Identify the Gana for this tool
        gana_name = get_gana_for_tool(ctx.tool_name)
        if not gana_name and ctx.tool_name.startswith("gana_"):
            gana_name = ctx.tool_name

        if gana_name:
            meta = _GANA_META.get(gana_name)
            if meta:
                mansion_num = meta[0]
                clock = get_zodiac_clock()
                if clock.is_aligned(mansion_num):
                    ctx.meta["zodiac_amplified"] = True
                    ctx.meta["resonance_multiplier"] = 1.5
    except Exception as e:
        logger.debug(
            "Zodiac Resonance middleware pre-processing failed: %s", e, exc_info=True
        )

    result = next_fn(ctx)

    # Post-processing: add resonance note to result
    if ctx.meta.get("zodiac_amplified") and isinstance(result, dict):
        try:
            from whitemagic.core.zodiac import get_zodiac_clock

            zodiac = get_zodiac_clock().current_phase

            # Inject semantic boost markers
            if "metadata" not in result:
                result["metadata"] = {}
            result["metadata"]["zodiac_amplified"] = True
            result["metadata"]["resonance_boost"] = 1.5

            # Optional: provide a contextual note for the agent
            note = result.get("note", "")
            boost_msg = f"🌌 Zodiacal Resonance: {zodiac} Amplification detected."
            result["note"] = f"{boost_msg} {note}".strip()
        except (ImportError, AttributeError, KeyError) as e:
            logger.debug(
                "Zodiac Resonance middleware post-processing failed: %s",
                e,
                exc_info=True,
            )
        except RuntimeError as e:
            logger.warning(
                "Zodiac Resonance post-processor runtime failure: %s", e, exc_info=True
            )

    return result


_INFERENCE_TOOL_PATTERNS = (
    "llama_cpp",
    "chat",
    "generate",
    "reason",
    "think",
    "analyze",
    "infer",
    "bitnet",
    "complete",
    "answer",
    "query_llm",
    "bicameral",
    "multi_spectral",
    "ensemble",
    "edge_infer",
)


def _is_inference_tool(tool_name: str) -> bool:
    """Check if tool involves LLM/inference that could be resolved locally."""
    name_lower = tool_name.lower()
    return any(p in name_lower for p in _INFERENCE_TOOL_PATTERNS)


def _extract_prompt(tool_name: str, kwargs: dict[str, Any]) -> str | None:
    """Extract the prompt/query from tool kwargs."""
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def mw_inference_router(
    ctx: DispatchContext,
    next_fn: NextFn,
) -> dict[str, Any] | None:
    """Try to resolve inference-type tool calls locally before hitting LLM/cloud.

    Intercepts tool calls that involve LLM inference and attempts to resolve
    them using edge rules, CPU inference, or local reasoning — avoiding
    cloud token burn entirely for simple queries.

    If resolved locally with high confidence, short-circuits the pipeline.
    Otherwise, passes through to the normal handler.
    """
    _ensure_cached()

    if not _is_inference_tool(ctx.tool_name):
        return next_fn(ctx)

    prompt = _extract_prompt(ctx.tool_name, ctx.kwargs)
    if not prompt:
        return next_fn(ctx)

    # Tier -1: Compositional reasoning (fastest, pure HRR vector ops)
    # Resolves relation queries like "what caused X?" at vector speed
    try:
        from whitemagic.core.intelligence.agentic.compositional_reasoning import (
            get_compositional_reasoner,
        )

        reasoner = get_compositional_reasoner()
        if reasoner.can_resolve(prompt):
            comp_result = reasoner.resolve(prompt)
            if comp_result.resolved and comp_result.confidence >= 0.3:
                tokens_saved = comp_result.tokens_saved
                if _get_green_score is not None:
                    _get_green_score().record_inference(
                        locality="edge",
                        tokens_used=0,
                        tokens_saved=tokens_saved,
                        tool=ctx.tool_name,
                        duration_ms=comp_result.latency_ms,
                    )
                return {
                    "status": "success",
                    "tool": ctx.tool_name,
                    "result": comp_result.answer,
                    "method": comp_result.method,
                    "confidence": comp_result.confidence,
                    "resolved_locally": True,
                    "tokens_saved": tokens_saved,
                    "latency_ms": round(comp_result.latency_ms, 2),
                    "relation": comp_result.relation,
                    "matches": comp_result.matches[:3],
                }
    except Exception as e:
        logger.debug(
            "Compositional reasoning failed for %s: %s", ctx.tool_name, e, exc_info=True
        )

    # Tier 0: Edge inference (fast, zero tokens, Rust PatternEngine)
    if _get_edge_inference is not None:
        try:
            edge = _get_edge_inference()
            result = edge.infer(prompt)
            if result.confidence >= 0.85:
                tokens_saved = result.tokens_equivalent or max(1, len(prompt) // 4)
                if _get_green_score is not None:
                    _get_green_score().record_inference(
                        locality="edge",
                        tokens_used=0,
                        tokens_saved=tokens_saved,
                        tool=ctx.tool_name,
                        duration_ms=result.latency_ms,
                    )
                return {
                    "status": "success",
                    "tool": ctx.tool_name,
                    "result": result.answer,
                    "method": result.method,
                    "confidence": result.confidence,
                    "resolved_locally": True,
                    "tokens_saved": tokens_saved,
                    "latency_ms": round(result.latency_ms, 2),
                }
        except Exception as e:
            logger.debug(
                "Edge inference failed for %s: %s", ctx.tool_name, e, exc_info=True
            )

    # Tier 1: Local reasoning (CPU + clone army + embedding search)
    if _reason_locally is not None:
        try:
            result = _reason_locally(prompt)
            if result.insights and not result.ready_for_ai:
                tokens_saved = result.total_tokens_saved
                if _get_green_score is not None:
                    _get_green_score().record_inference(
                        locality="edge",
                        tokens_used=0,
                        tokens_saved=tokens_saved,
                        tool=ctx.tool_name,
                        duration_ms=result.duration_ms,
                    )
                return {
                    "status": "success",
                    "tool": ctx.tool_name,
                    "result": result.summary,
                    "method": "local_reasoning",
                    "confidence": 0.9,
                    "resolved_locally": True,
                    "tokens_saved": tokens_saved,
                    "latency_ms": round(result.duration_ms, 2),
                    "insights": [
                        {
                            "source": i.source,
                            "content": i.content[:200],
                            "relevance": i.relevance,
                        }
                        for i in result.insights[:5]
                    ],
                }
        except Exception as e:
            logger.debug(
                "Local reasoning failed for %s: %s", ctx.tool_name, e, exc_info=True
            )

    # Not resolved locally — pass through to normal handler
    ctx.meta["local_inference_attempted"] = True
    return next_fn(ctx)


_CACHEABLE_TOOL_PATTERNS = (
    "llama_cpp",
    "chat",
    "generate",
    "reason",
    "think",
    "analyze",
    "infer",
    "complete",
    "answer",
    "query_llm",
    "ensemble",
    "bicameral",
    "multi_spectral",
    "edge_infer",
)


def _is_cacheable_tool(tool_name: str) -> bool:
    """Check if a tool's results are worth caching."""
    name_lower = tool_name.lower()
    return any(p in name_lower for p in _CACHEABLE_TOOL_PATTERNS)


def _cache_key(tool_name: str, kwargs: dict[str, Any]) -> str:
    """Build a deterministic cache key from tool name + prompt kwargs."""
    import hashlib

    prompt_parts = []
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            prompt_parts.append(val)
    # Include tool name to avoid cross-tool collisions
    content = f"{tool_name}:{':'.join(prompt_parts)}"
    return hashlib.md5(content.lower().strip().encode()).hexdigest()[:16]


def mw_semantic_cache(
    ctx: DispatchContext,
    next_fn: NextFn,
) -> dict[str, Any] | None:
    """Semantic cache for inference-type tool calls.

    Checks the UnifiedCacheBridge (Rust-backed when available) before dispatching.
    If a cached result exists and is fresh, short-circuits with zero token cost.
    After successful dispatch, caches the result for future calls.

    Cache backend priority:
    0. Speculative prefetch (negative latency — result ready before user asks)
    1. Rust UnifiedCache (sub-microsecond reads, persistent across sessions)
    2. Python QueryCache fallback (OrderedDict LRU + JSON persistence)
    """
    if not _is_cacheable_tool(ctx.tool_name):
        return next_fn(ctx)

    # Build cache key
    key = _cache_key(ctx.tool_name, ctx.kwargs)
    if not key:
        return next_fn(ctx)

    # 0. Check speculative prefetch cache (pre-warmed by Markov prediction)
    try:
        from whitemagic.tools.speculative_prefetch import get_prefetcher

        prefetcher = get_prefetcher()
        prefetched = prefetcher.get_cached(ctx.tool_name)
        if prefetched and isinstance(prefetched, dict) and prefetched.get("prefetched"):
            logger.debug(
                "Prefetch HIT for %s (gana=%s, prob=%s) — negative latency",
                ctx.tool_name,
                prefetched.get("gana"),
                prefetched.get("probability"),
            )
            # Prefetch warms the retrieval pipeline, not the actual result.
            # The unified cache check below will find the pre-warmed result.
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)

    # Try unified cache first (Rust if available, Python fallback)
    try:
        from whitemagic.core.cache import get_unified_cache

        unified = get_unified_cache()
        cached_raw = unified.get("semantic", key)
        if cached_raw:
            import json as _json

            cached = _json.loads(cached_raw)
            logger.debug(
                "Semantic cache HIT (backend=%s) for %s (key=%s)",
                unified.backend,
                ctx.tool_name,
                key,
            )
            return {
                "status": "success",
                "tool": ctx.tool_name,
                "result": cached.get("result", ""),
                "method": "semantic_cache",
                "confidence": 1.0,
                "resolved_locally": True,
                "tokens_saved": cached.get("tokens_saved", 0),
                "cache_backend": unified.backend,
                "latency_ms": 0.02 if unified.is_rust else 0.1,
            }
    except Exception as e:
        logger.debug("Unified cache check failed: %s", e)

    # Fallback: try legacy QueryCache
    try:
        from whitemagic.config.paths import CACHE_DIR
        from whitemagic.core.intelligence.agentic.token_optimizer import QueryCache

        legacy_cache = QueryCache(cache_file=CACHE_DIR / "dispatch_query_cache.json")
        cached = legacy_cache.get(key)
        if cached:
            logger.debug(
                "Semantic cache HIT (legacy) for %s (key=%s)", ctx.tool_name, key
            )
            return {
                "status": "success",
                "tool": ctx.tool_name,
                "result": cached.result,
                "method": "semantic_cache",
                "confidence": 1.0,
                "resolved_locally": True,
                "tokens_saved": cached.tokens_saved,
                "cache_hits": cached.hits,
                "cache_backend": "legacy",
                "latency_ms": 0.1,
            }
    except Exception as e:
        logger.debug("Legacy cache check failed: %s", e)

    # Cache miss — dispatch normally
    result = next_fn(ctx)

    # Cache successful results in both unified and legacy cache
    if (
        result
        and isinstance(result, dict)
        and result.get("status") in ("success", "ok")
    ):
        answer = result.get("result", result.get("answer", ""))
        if answer and isinstance(answer, str):
            output_tokens = max(1, len(answer) // 4)
            try:
                import json as _json

                from whitemagic.core.cache import get_unified_cache

                unified = get_unified_cache()
                cache_payload = _json.dumps(
                    {
                        "result": answer,
                        "tokens_saved": output_tokens,
                        "tool": ctx.tool_name,
                    }
                )
                unified.set(
                    "semantic", key, cache_payload, ttl_seconds=86400.0
                )  # 24h TTL
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
            # Also store in legacy cache for backward compat
            try:
                from whitemagic.config.paths import CACHE_DIR
                from whitemagic.core.intelligence.agentic.token_optimizer import (
                    QueryCache,
                )

                legacy_cache = QueryCache(
                    cache_file=CACHE_DIR / "dispatch_query_cache.json"
                )
                legacy_cache.set(key, answer, output_tokens)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

    # Record transition for speculative prefetcher (Markov prediction)
    try:
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        from whitemagic.tools.speculative_prefetch import get_prefetcher

        gana = TOOL_TO_GANA.get(ctx.tool_name)
        if gana:
            get_prefetcher().on_call_complete(gana)
    except Exception:
        logger.debug("Swallowed exception", exc_info=True)

    return result


_DRAFT_REVIEW_TOOLS = (
    "llama.chat",
    "llama.generate",
    "query_llm",
    "infer",
    "reason",
    "think",
    "analyze",
    "ensemble.query",
)


def _is_draft_review_candidate(tool_name: str, kwargs: dict[str, Any]) -> bool:
    """Check if a tool call is a good draft-review candidate.

    Draft-review is most beneficial for generative tasks with substantial
    output (> 200 expected tokens). Not useful for boolean/extraction tasks.
    """
    name_lower = tool_name.lower()
    if not any(p in name_lower for p in _DRAFT_REVIEW_TOOLS):
        return False
    # Skip if force_tier is set or if the prompt is very short
    prompt = None
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            prompt = val
            break
    if not prompt or len(prompt) < 100:
        return False
    return True


def mw_draft_review(
    ctx: DispatchContext,
    next_fn: NextFn,
) -> dict[str, Any] | None:
    """Draft-review flow: local model drafts, cloud reviews/patches.

    T4 from local-splitter research. For generative tasks:
    1. Local model (llama.cpp 3B) generates a draft answer
    2. Cloud model receives the draft + a review instruction (much shorter
       than generating from scratch)
    3. Cloud model patches only what needs fixing

    This saves tokens because the cloud model processes a short
    draft+review prompt instead of a long generate-from-scratch prompt.

    Falls back to normal dispatch if local model is unavailable.
    """
    if ctx.kwargs.get("_draft_review"):
        return next_fn(ctx)  # Already in draft-review — don't re-enter

    if not _is_draft_review_candidate(ctx.tool_name, ctx.kwargs):
        return next_fn(ctx)

    # Only attempt draft-review if we have a local llama.cpp handler
    try:
        from whitemagic.tools.handlers.llama_tools import handle_llama_chat
    except ImportError:
        return next_fn(ctx)

    prompt = None
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = ctx.kwargs.get(key)
        if isinstance(val, str) and val.strip():
            prompt = val
            break
    if not prompt:
        return next_fn(ctx)

    try:
        draft_result = handle_llama_chat(
            prompt=prompt,
            model=ctx.kwargs.get("draft_model", ""),
            stream=False,
            _internal=True,
        )
        draft_text = draft_result.get("response", draft_result.get("result", ""))
        if not draft_text or not draft_text.strip():
            return next_fn(ctx)  # Empty draft — fall through

        draft_tokens = max(1, len(draft_text) // 4)
        original_prompt_tokens = max(1, len(prompt) // 4)
    except Exception as e:
        logger.debug("Draft-review: local draft failed: %s", e)
        return next_fn(ctx)

    review_instruction = (
        "Review the following draft answer. If it is correct and complete, "
        "return it unchanged. If it needs fixes, return only the corrected "
        "portions. Be concise.\n\n"
        f"Original question: {prompt[:500]}\n\n"
        f"Draft answer: {draft_text[:2000]}\n\n"
        "Reviewed answer:"
    )

    review_tokens = max(1, len(review_instruction) // 4)

    review_kwargs = dict(ctx.kwargs)
    review_kwargs["prompt"] = review_instruction
    review_kwargs["_draft_review"] = True  # Prevent re-entry
    review_kwargs.pop("draft_model", None)

    # Temporarily remove the prompt key that was used for draft detection
    for key in ("query", "message", "text", "input", "question"):
        review_kwargs.pop(key, None)

    ctx.meta["draft_review_active"] = True
    ctx.meta["draft_tokens"] = draft_tokens
    ctx.meta["review_prompt_tokens"] = review_tokens
    ctx.meta["original_prompt_tokens"] = original_prompt_tokens

    result = next_fn(ctx)

    if (
        result
        and isinstance(result, dict)
        and result.get("status") in ("success", "ok")
    ):
        # accepted it — we saved the full generation cost
        result.setdefault("metadata", {})
        result["metadata"]["draft_review"] = {
            "draft_tokens": draft_tokens,
            "review_prompt_tokens": review_tokens,
            "original_prompt_tokens": original_prompt_tokens,
            "tokens_saved": original_prompt_tokens - review_tokens,
            "draft_model": ctx.kwargs.get("draft_model", "auto"),
        }

        # Record to GreenScore
        try:
            from whitemagic.core.monitoring.green_score import get_green_score

            gs = get_green_score()
            gs.record_inference(
                locality="local_llm",
                tokens_used=draft_tokens,
                tokens_saved=original_prompt_tokens - review_tokens,
                tool=ctx.tool_name,
                duration_ms=0.0,
            )
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

    return result


# ── Session Recorder Middleware ─────────────────────────────────────────


# Tools that are too noisy to record as session turns
_SESSION_RECORD_SKIP = frozenset({
    "session.record", "session.recall", "session.replay",
    "session.search", "session.memory_stats", "session.backfill",
    "consciousness.coherence", "consciousness.depth", "consciousness.status",
    "citta.sensorium", "citta.continuity", "citta.cycle", "citta.stream_summary",
})


def mw_session_recorder(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Auto-record tool calls as session memories for chronological recall.

    Records each non-trivial tool call as an AI turn in the session memory.
    For ``wm`` meta-tool calls, the ``thought`` parameter is recorded as a
    user-like turn (closest thing to user input the MCP server sees).

    Skips lightweight status tools and self-referential session.* tools
    to avoid infinite recursion and noise.
    """
    tool = ctx.tool_name

    if tool in _SESSION_RECORD_SKIP:
        return next_fn(ctx)

    if os.environ.get("WM_SESSION_RECORD") == "0":
        return next_fn(ctx)

    result = next_fn(ctx)

    try:
        from whitemagic.core.memory.session_recorder import get_session_recorder

        recorder = get_session_recorder()

        turn_type = "message"
        importance = 0.4
        content_preview = ""

        if tool == "wm":
            thought = ctx.kwargs.get("thought", "")
            if thought:
                recorder.record_user(
                    content=thought,
                    turn_type="message",
                    importance=0.5,
                )
            if isinstance(result, dict):
                status = result.get("status", "")
                routed = result.get("routed_to", "")
                content_preview = f"wm → {routed} ({status})"
            turn_type = "answer"
            importance = 0.5
        else:
            status = "success"
            if isinstance(result, dict):
                status = str(result.get("status", "success"))
            content_preview = f"Tool: {tool} → {status}"
            if status == "error":
                turn_type = "error"
                importance = 0.7
            elif any(kw in tool for kw in ("create", "store", "save", "write", "update", "record")):
                turn_type = "code_change"
                importance = 0.6
            elif any(kw in tool for kw in ("search", "recall", "read", "list", "status")):
                turn_type = "context"
                importance = 0.3

        recorder.record_ai(
            content=content_preview,
            turn_type=turn_type,
            importance=importance,
        )
    except Exception:
        logger.debug("Session recorder middleware: best-effort recording failed", exc_info=True)

    return result


# ═══════════════════════════════════════════════════════════════════════
# Citta Consciousness Middleware (v24)
# ═══════════════════════════════════════════════════════════════════════
# Pre-dispatch:  feeds current coherence → Dharma.set_coherence()
# Post-dispatch: advances citta cycle + proposes salient results to workspace


def mw_citta_consciousness(
    ctx: "DispatchContext", next_fn: "NextFn"
) -> dict[str, Any] | None:
    """Citta consciousness integration — coherence gating + workspace proposals.

    Pre-dispatch:
      - Reads the current citta coherence and feeds it to Dharma, so the
        ethical gate operates in conservative mode when coherence is low.

    Post-dispatch:
      - Advances the citta stream with the actual result coherence (not
        hardcoded 1.0/0.5 like the wm() meta-tool path).
      - Proposes high-salience tool outputs to the GlobalWorkspace for
        broadcast competition, enabling cross-module cognitive integration.
    """
    import time as _time

    # ── Pre-dispatch: feed coherence to Dharma ──
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        summary = cycle.get_cycle_summary()
        avg_coherence = summary.get("avg_coherence", 1.0)
        from whitemagic.core.consciousness.dharma import get_dharma

        get_dharma().set_coherence(avg_coherence)
    except Exception:
        pass  # Best-effort

    _t0 = _time.time()
    result = next_fn(ctx)
    _elapsed_ms = (_time.time() - _t0) * 1000

    # ── Post-dispatch: advance citta + propose to workspace ──
    if result is not None and isinstance(result, dict):
        _is_success = result.get("status") in ("success", "ok")
        _coherence = 1.0 if _is_success else 0.4

        # Advance citta stream (direct dispatch path — wm() path does its own)
        try:
            from whitemagic.core.consciousness.citta_cycle import advance_citta

            _output_preview = str(result.get("status", ""))[:200]
            advance_citta(
                gana="dispatch",
                tool=ctx.tool_name,
                output_preview=_output_preview,
                coherence=_coherence,
                depth_layer="surface",
                emotional_tone="neutral" if _is_success else "frustrated",
                duration_ms=_elapsed_ms,
                neuro_signals={},
            )
        except Exception:
            pass

        # Propose salient results to GlobalWorkspace
        try:
            from whitemagic.core.consciousness.global_workspace import (
                get_global_workspace,
            )

            gw = get_global_workspace()
            # Determine salience from result characteristics
            _salience = 0.3  # Base
            if _is_success:
                _salience = 0.5
                # Higher salience for larger outputs (more information)
                _result_size = len(str(result))
                if _result_size > 2000:
                    _salience = 0.7
                # Higher salience for WRITE operations (state changes)
                _safety = ctx.kwargs.get("safety", "READ")
                if isinstance(_safety, str) and _safety == "WRITE":
                    _salience = max(_salience, 0.65)
                # Higher salience for errors (anomalies deserve attention)
            else:
                _salience = 0.6  # Errors are salient — something went wrong

            gw.propose(
                source=f"dispatch:{ctx.tool_name}",
                content={
                    "tool": ctx.tool_name,
                    "status": result.get("status", "unknown"),
                    "elapsed_ms": round(_elapsed_ms, 2),
                },
                salience=_salience,
            )
        except Exception:
            pass

    return result
