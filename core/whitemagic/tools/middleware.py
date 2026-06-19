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

# ---------------------------------------------------------------------------
# Cached module references — hoisted from per-call lazy imports to eliminate
# import-lock contention on rapid parallel tool dispatch.
# Each is loaded once on first access; failures are cached as None.
# ---------------------------------------------------------------------------

_sanitize_tool_args: Callable[..., Any] | None = None
_get_breaker_registry: Callable[[], Any] | None = None
_get_rate_limiter: Callable[..., Any] | None = None
_check_tool_permission: Callable[..., bool] | None = None
_check_maturity_for_tool: Callable[..., bool] | None = None
_get_security_monitor: Callable[[], Any] | None = None
_get_governor: Callable[[], Any] | None = None
_compact_fn: Callable[..., dict[str, Any]] | None = None
_get_prometheus: Callable[[], Any] | None = None
_get_otel: Callable[[], Any] | None = None
_cached: bool = False


def _ensure_cached() -> None:
    """Load all middleware dependencies once.  Safe to call multiple times."""
    global _sanitize_tool_args, _get_breaker_registry, _get_rate_limiter
    global _check_tool_permission, _check_maturity_for_tool
    global _get_security_monitor, _get_governor, _compact_fn, _cached
    global _get_prometheus, _get_otel
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
            from whitemagic.dharma.governor import (
                get_governor,  # type: ignore[assignment]
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
        from whitemagic.utils.core import compact_dict
        _compact_fn = compact_dict
    except (ImportError, AttributeError):
        pass
    _cached = True


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

NextFn = Callable[["DispatchContext"], dict[str, Any] | None]
MiddlewareFn = Callable[["DispatchContext", NextFn], dict[str, Any] | None]


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DispatchPipeline:
    """Composable middleware chain for tool dispatch.

    Middlewares execute in registration order.  Each can short-circuit
    by returning a result, or call ``next_fn(ctx)`` to continue.
    """

    def __init__(self) -> None:
        self._middlewares: list[tuple[str, MiddlewareFn]] = []
        self._chain: NextFn | None = None  # Pre-built chain (frozen after first execute)

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
                logger.debug(f"Middleware: compaction failed for {ctx.tool_name}: {e}")
            except RuntimeError as e:
                logger.warning(f"Middleware: unexpected compaction runtime error for {ctx.tool_name}: {e}")

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
        "resolution": {"suggested_action": "verify_tool_name_or_use_prat_gana", "debug_hint": "Set WM_DEBUG=1 for verbose diagnostics"},
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
            logger.warning(f"Middleware '{name}' error: {e.__class__.__name__}: {e}")
            # Record error in context for downstream inspection
            if "middleware_errors" not in ctx.meta:
                ctx.meta["middleware_errors"] = []
            ctx.meta["middleware_errors"].append({"middleware": name, "error": str(e), "type": e.__class__.__name__})
            return next_fn(ctx)
    return wrapped


# =========================================================================
# Built-in middlewares
# =========================================================================

def mw_input_sanitizer(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Validate tool arguments before any processing."""
    _ensure_cached()
    if _sanitize_tool_args is not None:
        try:
            result = _sanitize_tool_args(ctx.tool_name, ctx.kwargs)
            if result is not None:
                return cast(dict[str, Any], result)
        except Exception as e:
            logger.debug(f"Input sanitizer failed for {ctx.tool_name}: {e}")
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
            logger.debug(f"Middleware: circuit breaker lookup failed for {ctx.tool_name}: {e}")
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
            logger.debug(f"Middleware: prometheus recording failed for {ctx.tool_name}: {e}")

    # Record to OTel
    if _get_otel is not None:
        try:
            _get_otel().record_tool_span(ctx.tool_name, duration, status)
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Middleware: otel recording failed for {ctx.tool_name}: {e}")

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
            logger.debug(f"Middleware: rate limit check failed for {ctx.tool_name}: {e}")
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
            logger.debug(f"Middleware: permission check failed for {ctx.tool_name}: {e}")
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
            logger.debug(f"Middleware: maturity check failed for {ctx.tool_name}: {e}")
    return next_fn(ctx)


def mw_security_monitor(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Edgerunner Violet: anomaly detection for suspicious tool-call patterns."""
    _ensure_cached()
    quiet_internal = os.getenv("WM_BENCHMARK_QUIET", "").strip().lower() in ("1", "true", "yes")
    quiet_internal = quiet_internal and bool(ctx.meta.get("quiet_internal_benchmark", False))
    if _get_security_monitor is not None and not quiet_internal:
        try:
            safety = ctx.kwargs.get("safety", "READ")
            if not isinstance(safety, str):
                safety = "READ"
            alert = _get_security_monitor().record_call(
                tool=ctx.tool_name,
                safety=safety,
                agent_id=ctx.agent_id,
            )
            if alert and alert.get("action") == "block":
                return {
                    "status": "error",
                    "error_code": "security_breaker",
                    "message": f"Security monitor blocked: {alert.get('detail', 'anomaly detected')}",
                    "alert": alert,
                }
        except (AttributeError, KeyError, ValueError) as e:
            logger.debug(f"Security monitor call recording failed for {ctx.tool_name}: {e}")
        except RuntimeError as e:
            logger.warning(f"Security monitor runtime failure: {e}")
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
                    _emit_gan_ying("GOVERNOR_BLOCKED", {
                        "tool": ctx.tool_name, "reason": validation.reason,
                    })
                except (ImportError, AttributeError, RuntimeError) as e:
                    logger.debug(f"Middleware: governor gan-ying emit failed: {e}")
                return {
                    "status": "error",
                    "error": f"Governor Blocked: {validation.reason}",
                    "risk_level": validation.risk_level.name,
                }
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Middleware: governor validation failed for {ctx.tool_name}: {e}")
    return next_fn(ctx)


def mw_sutra_auto_execute(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Dharma-gated Auto-Execution (GATED: disabled by default).
    Checks the Sutra Kernel to determine if a tool can auto-execute without human approval.
    - Sattvic (Read/Observe): Auto-executes immediately.
    - Rajasic (Write/Create): Auto-executes if intent is high, logs to Zodiac Ledger.
    - Tamasic (Delete/Destructive): Blocked/Paused, sent to Nexus UI via Iceoryx2 for explicit consent.

    NOTE: This middleware is disabled by default. Enable with WM_ENABLE_SUTRA_AUTO_EXECUTE=1.
    """
    # Gate behind feature flag - disabled by default as Sutra Kernel is not fully integrated
    if os.environ.get("WM_ENABLE_SUTRA_AUTO_EXECUTE", "").strip().lower() not in ("1", "true", "yes"):
        return next_fn(ctx)

    try:
        from whitemagic.core.bridge.sutra_bridge import get_sutra_kernel
        sutra = get_sutra_kernel()

        # We estimate intent and karma from the tool metadata or context
        # (For now, use defaults or dummy values, real implementation would extract from Gnosis/Karma)
        verdict = sutra.evaluate_action(
            action_type=ctx.tool_name,
            intent_score=1.0,
            karma_debt=0.0
        )

        if verdict.startswith("Panic") or verdict.startswith("Intervene"):
            # Block and push to UI for Karmic Consent
            try:
                from whitemagic.core.ipc_bridge import publish_json
                publish_json("wm/commands", {
                    "type": "karmic_consent_required",
                    "tool": ctx.tool_name,
                    "reason": verdict
                })
            except Exception as e:
                logger.warning(f"Failed to push consent to Nexus UI: {e}")

            return {
                "status": "paused",
                "error": f"Sutra Kernel Intervention: {verdict}. Awaiting Karmic Consent.",
                "action_required": "user_approval"
            }
    except ImportError as e:
        logger.debug(f"Middleware: sutra_bridge missing for {ctx.tool_name}: {e}")
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning(f"Middleware: sutra_auto_execute unexpected error: {e}")
        logger.warning(f"Sutra Auto-Execute Middleware failed: {e}")

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
        logger.debug(f"Zodiac Resonance middleware pre-processing failed: {e}")

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
            logger.debug(f"Zodiac Resonance middleware post-processing failed: {e}")
        except RuntimeError as e:
            logger.warning(f"Zodiac Resonance post-processor runtime failure: {e}")

    return result
