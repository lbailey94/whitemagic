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

# Names of critical dependencies that failed to load.  Middleware functions
# can check this set to decide whether to fail-closed or degrade gracefully.
_critical_deps_failed: set[str] = set()

# Dependencies whose absence is a safety concern (fail-closed candidates).
_CRITICAL_DEP_NAMES: frozenset[str] = frozenset({
    "input_sanitizer",
    "circuit_breaker",
    "rate_limiter",
    "tool_permissions",
    "security_monitor",
    "governor",
})


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
        _critical_deps_failed.add("input_sanitizer")
        logger.error("CRITICAL: input_sanitizer dependency missing: %s", e)
    try:
        from whitemagic.tools.circuit_breaker import get_breaker_registry

        _get_breaker_registry = get_breaker_registry
    except Exception as e:
        _critical_deps_failed.add("circuit_breaker")
        logger.error("CRITICAL: circuit_breaker dependency missing: %s", e)
    try:
        from whitemagic.tools.rate_limiter import get_rate_limiter

        _get_rate_limiter = get_rate_limiter
    except Exception as e:
        _critical_deps_failed.add("rate_limiter")
        logger.error("CRITICAL: rate_limiter dependency missing: %s", e)
    try:
        from whitemagic.tools.tool_permissions import check_tool_permission

        _check_tool_permission = check_tool_permission  # type: ignore[assignment]
    except Exception as e:
        _critical_deps_failed.add("tool_permissions")
        logger.error("CRITICAL: tool_permissions dependency missing: %s", e)
    try:
        from whitemagic.tools.maturity_check import check_maturity_for_tool

        _check_maturity_for_tool = check_maturity_for_tool  # type: ignore[assignment]
    except Exception as e:
        logger.debug("Middleware: maturity_check dependency missing: %s", e)
    try:
        from whitemagic.security.security_breaker import get_security_monitor

        _get_security_monitor = get_security_monitor
    except Exception as e:
        _critical_deps_failed.add("security_monitor")
        logger.error("CRITICAL: security_monitor dependency missing: %s", e)
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
            _critical_deps_failed.add("governor")
            logger.error("CRITICAL: governor dependency missing: %s", e)
        logger.debug("Middleware: governor fallback attempted: %s", e)
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
        logger.debug("Optional dependency unavailable: ImportError")
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
PostCallHook = Callable[["DispatchContext", dict[str, Any] | None], dict[str, Any] | None]


@dataclass
class DispatchContext:
    """Mutable context that flows through the middleware chain."""

    tool_name: str
    kwargs: dict[str, Any]
    agent_id: str = "default"
    user_id: str = "local"
    galaxy: str = "default"
    policy_profile: str = "default"
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

    Middleware is tagged as **critical** or **enrichment**:
    - **critical** (fail-closed): if the middleware raises an exception,
      execution is blocked and an error envelope is returned.
    - **enrichment** (fail-open): if the middleware raises, the error is
      logged and execution continues (legacy behaviour).
    """

    def __init__(self) -> None:
        self._middlewares: list[tuple[str, MiddlewareFn, bool]] = []
        self._post_call_hooks: list[tuple[str, PostCallHook]] = []
        self._chain: NextFn | None = (
            None  # Pre-built chain (frozen after first execute)
        )

    def use(
        self, name: str, middleware: MiddlewareFn, *, critical: bool = False
    ) -> DispatchPipeline:
        """Register a middleware.  Order matters — first registered runs first.

        Args:
            name: Human-readable name for logging.
            middleware: The middleware function.
            critical: If True, exceptions from this middleware block execution
                (fail-closed). If False (default), exceptions are logged and
                execution continues (fail-open).
        """
        self._middlewares.append((name, middleware, critical))
        self._chain = None  # Invalidate pre-built chain
        return self

    def use_post_call(self, name: str, hook: PostCallHook) -> DispatchPipeline:
        """Register a post-call hook that runs after the main chain completes.

        Post-call hooks receive ``(ctx, result)`` and can inspect or augment
        the result.  They always fail-open: exceptions are logged and the
        original result is preserved.

        Args:
            name: Human-readable name for logging.
            hook: The post-call hook function.
        """
        self._post_call_hooks.append((name, hook))
        return self

    def _build_chain(self) -> NextFn:
        """Build the closure chain once from registered middlewares."""
        chain: NextFn = _terminal
        for name, mw, critical in reversed(self._middlewares):
            chain = _wrap(mw, chain, name, critical=critical)
        return chain

    def execute(self, tool_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Execute the full pipeline for a tool call."""
        quiet_internal_benchmark = bool(kwargs.get("_internal_benchmark", False))
        ctx = DispatchContext(
            tool_name=tool_name,
            kwargs=kwargs,
            agent_id=kwargs.pop("_agent_id", "default"),
            user_id=kwargs.pop("_user_id", "local"),
            galaxy=kwargs.pop("_galaxy", "default"),
            policy_profile=kwargs.pop("_policy_profile", "default"),
            compact=kwargs.pop("_compact", False),
            zig_prevalidated=bool(kwargs.pop("_zig_prevalidated", False)),
        )
        # Strip pipeline-internal kwargs so they don't leak to handlers
        ctx.kwargs.pop("_force_full_pipeline", None)
        ctx.kwargs.pop("_internal_benchmark", None)
        if quiet_internal_benchmark:
            ctx.meta["quiet_internal_benchmark"] = True

        # Use pre-built chain (built once, reused for all calls)
        if self._chain is None:
            self._chain = self._build_chain()

        result = self._chain(ctx)

        # Post-call hooks: observers that can inspect/augment the result.
        # Always fail-open — exceptions are logged, original result preserved.
        for hook_name, hook in self._post_call_hooks:
            try:
                augmented = hook(ctx, result)
                if augmented is not None:
                    result = augmented
            except Exception as e:
                logger.warning(
                    "Post-call hook '%s' error: %s: %s",
                    hook_name,
                    e.__class__.__name__,
                    e,
                    exc_info=True,
                )

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
        return [name for name, _, _ in self._middlewares]

    def describe_post_call(self) -> list[str]:
        """Return post-call hook names in registration order."""
        return [name for name, _ in self._post_call_hooks]


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


def _wrap(
    mw: MiddlewareFn, next_fn: NextFn, name: str, *, critical: bool = False
) -> NextFn:
    """Wrap a middleware + next into a single NextFn with safety net.

    Args:
        mw: The middleware function.
        next_fn: The next function in the chain.
        name: Human-readable name for logging.
        critical: If True, exceptions from this middleware block execution
            (fail-closed). If False, exceptions are logged and execution
            continues (fail-open).
    """

    def wrapped(ctx: DispatchContext) -> dict[str, Any] | None:
        try:
            return mw(ctx, next_fn)
        except Exception as e:
            # Re-raise typed tool execution errors so they aren't swallowed
            # by the middleware fallback logic.
            from whitemagic.tools.errors import ToolExecutionError

            if isinstance(e, ToolExecutionError):
                raise
            # Log middleware errors at WARNING level for visibility
            logger.warning(
                "Middleware '%s' error: %s: %s",
                name,
                e.__class__.__name__,
                e,
                exc_info=True,
            )
            # Record typed error in context for downstream inspection
            from whitemagic.tools.errors import classify_exception

            typed = classify_exception(e)
            if "middleware_errors" not in ctx.meta:
                ctx.meta["middleware_errors"] = []
            ctx.meta["middleware_errors"].append(
                {
                    "middleware": name,
                    "error": str(e),
                    "type": e.__class__.__name__,
                    "error_code": typed.error_code,
                    "retryable": typed.retryable,
                }
            )
            if critical:
                # Fail-closed: return an error envelope instead of continuing
                logger.error(
                    "Critical middleware '%s' failed — blocking execution for %s",
                    name,
                    ctx.tool_name,
                )
                return {
                    "status": "error",
                    "error_code": "middleware_fail_closed",
                    "message": (
                        f"Critical middleware '{name}' failed and execution "
                        f"was blocked for safety. Error: {e}"
                    ),
                    "middleware": name,
                    "tool": ctx.tool_name,
                }
            return next_fn(ctx)

    return wrapped


def mw_input_sanitizer(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Validate tool arguments before any processing."""
    _ensure_cached()
    if _sanitize_tool_args is not None:
        result = _sanitize_tool_args(ctx.tool_name, ctx.kwargs)
        if result is not None:
            return cast(dict[str, Any], result)
    elif "input_sanitizer" in _critical_deps_failed:
        logger.error(
            "input_sanitizer failed to load — blocking %s (fail-closed)",
            ctx.tool_name,
        )
        return {
            "status": "error",
            "error_code": "dependency_missing",
            "message": "Input sanitizer dependency unavailable — execution blocked for safety.",
            "middleware": "input_sanitizer",
            "tool": ctx.tool_name,
        }
    return next_fn(ctx)


def mw_circuit_breaker(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Fast-fail if tool is in cooldown; record success/failure afterward."""
    _ensure_cached()
    breaker = None
    if _get_breaker_registry is not None:
        breaker = _get_breaker_registry().get(ctx.tool_name)
        # Skip pre-check if Zig dispatch already validated circuit state
        if breaker is not None and not ctx.zig_prevalidated and breaker.is_open():
            calm = breaker.calm_response()
            if calm is not None:
                return cast(dict[str, Any], calm)

    result = next_fn(ctx)

    # Post-processing: breaker feedback (fail-open — just recording)
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


def mw_timeout(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Enforce a wall-clock timeout on tool execution.

    Wraps next_fn in a daemon thread and joins with a configurable timeout.
    If the tool exceeds the limit, returns a timeout error result instead
    of hanging indefinitely.

    Timeout is configured via:
    1. Per-tool override in ctx.kwargs.get("_timeout_s")
    2. WM_TOOL_TIMEOUT env var (seconds)
    3. Default: 30 seconds

    Tools that are known to be long-running (e.g. dream cycle, bulk ingestion)
    can set a higher timeout via the _timeout_s kwarg.
    """
    import os
    import threading

    default_timeout = float(os.getenv("WM_TOOL_TIMEOUT", "30"))
    timeout_s = ctx.kwargs.pop("_timeout_s", default_timeout)
    if timeout_s <= 0:
        return next_fn(ctx)

    result_box: list[dict[str, Any] | None] = [None]
    error_box: list[Exception | None] = [None]

    def _worker() -> None:
        try:
            result_box[0] = next_fn(ctx)
        except Exception as e:
            error_box[0] = e

    worker = threading.Thread(target=_worker, daemon=True, name=f"timeout-{ctx.tool_name}")
    worker.start()
    worker.join(timeout=timeout_s)

    if worker.is_alive():
        logger.warning(
            "Tool %s exceeded timeout of %.1fs — returning timeout error",
            ctx.tool_name,
            timeout_s,
        )
        return {
            "status": "error",
            "error_code": "TIMEOUT",
            "error": f"Tool '{ctx.tool_name}' exceeded {timeout_s}s timeout",
            "tool": ctx.tool_name,
            "timeout_s": timeout_s,
        }

    if error_box[0] is not None:
        raise error_box[0]

    return result_box[0]


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


def mw_karma_effects(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Auto-record karmic effects for every tool call (MandalaOS Phase A).

    Uses the effect registry to look up declared effects for the tool,
    then records them via KarmaLedger.record_with_effects().
    """
    result = next_fn(ctx)
    try:
        from whitemagic.dharma.effect_registry import get_declared_effects
        from whitemagic.dharma.effect_registry import get_declared_safety as _get_safety
        from whitemagic.dharma.karma_ledger import get_karma_ledger

        declared_effects = get_declared_effects(ctx.tool_name)
        declared_safety = _get_safety(ctx.tool_name)

        # Infer actual effects from the result
        is_success = isinstance(result, dict) and result.get("status") == "success"
        actual_writes = 0
        if declared_safety in ("WRITE", "DELETE") and is_success:
            actual_writes = 1

        # Build actual effects — same as declared if successful, empty if failed
        actual_effects = declared_effects if is_success else []

        ledger = get_karma_ledger()

        # Auto-classify ops_class for dual-log transparency (Edgerunner Violet)
        # If engagement_token middleware already set it, use that. Otherwise infer.
        ops_class = ctx.meta.get("ops_class", "")
        if not ops_class:
            try:
                from whitemagic.security.engagement_tokens import classify_ops
                ops_class = classify_ops(ctx.tool_name)
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

        ledger.record_with_effects(
            tool=ctx.tool_name,
            declared_safety=declared_safety,
            actual_writes=actual_writes,
            success=is_success,
            declared_effects=declared_effects,
            actual_effects=actual_effects,
            shelter_id=ctx.meta.get("shelter_id", ""),
            ops_class=ops_class,
        )
    except Exception as e:
        logger.debug(
            "Middleware: karma effects recording failed for %s: %s",
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
        limiter = _get_rate_limiter()
        result = limiter.check(ctx.agent_id, ctx.tool_name)
        if result is not None:
            return result
    return next_fn(ctx)


def mw_tool_permissions(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Per-agent RBAC permission check."""
    _ensure_cached()
    if _check_tool_permission is not None:
        perm_result = _check_tool_permission(ctx.agent_id, ctx.tool_name)
        if perm_result is not None:
            return perm_result  # type: ignore[return-value]
    return next_fn(ctx)


def mw_maturity_gate(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Block tools that require a higher maturity stage than currently reached."""
    if ctx.zig_prevalidated:
        return next_fn(ctx)  # Zig already checked maturity
    if os.getenv("WM_BENCHMARK_MODE", "").strip().lower() in ("1", "true", "yes"):
        return next_fn(ctx)  # Bypass maturity gates in benchmark mode
    _ensure_cached()
    if _check_maturity_for_tool is not None:
        mat_result = _check_maturity_for_tool(ctx.tool_name)
        if mat_result is not None:
            return mat_result  # type: ignore[return-value]
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
    return next_fn(ctx)


def mw_engagement_token(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Violet engagement token enforcement — blocks red-ops tools without a valid token.

    Only active when the Dharma profile is 'violet'. Checks:
    1. Is the tool a red-ops (offensive security) tool?
    2. If so, is there a valid engagement token in ctx.meta or kwargs?
    3. Validate token: not expired, not revoked, tool authorized, target in scope.

    Inspired by ROE Gate's reference monitor pattern — the agent cannot bypass
    this check because it runs in the middleware pipeline before tool execution.
    """
    try:
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import (
            get_token_manager,
            requires_engagement_token,
        )

        # Only enforce under violet profile
        engine = get_rules_engine()
        if engine.get_profile() != "violet":
            return next_fn(ctx)

        # Only red-ops tools require tokens
        if not requires_engagement_token(ctx.tool_name):
            return next_fn(ctx)

        # Extract token_id from kwargs or meta
        token_id = ctx.kwargs.pop("_engagement_token_id", "") or ctx.meta.get("engagement_token_id", "")
        if not token_id:
            return {
                "status": "error",
                "error_code": "engagement_token_required",
                "message": (
                    f"Tool '{ctx.tool_name}' requires a valid engagement token "
                    f"under violet profile. Issue one via the engagement_token tool."
                ),
            }

        # Extract target from common kwargs
        target = ""
        for key in ("target", "host", "ip", "url", "domain", "endpoint"):
            val = ctx.kwargs.get(key)
            if isinstance(val, str) and val:
                target = val
                break

        mgr = get_token_manager()
        result = mgr.validate(token_id=token_id, tool=ctx.tool_name, target=target)
        if not result.get("valid", False):
            return {
                "status": "error",
                "error_code": "engagement_token_invalid",
                "message": f"Engagement token validation failed: {result.get('reason', 'unknown')}",
                "token_id": token_id,
            }

        # Stash validated token info for downstream middleware (karma ledger)
        ctx.meta["engagement_token"] = token_id
        ctx.meta["ops_class"] = "red-ops"

    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")
    except Exception as e:
        logger.debug(
            "Middleware: engagement token check failed for %s: %s",
            ctx.tool_name,
            e,
            exc_info=True,
        )
    return next_fn(ctx)


def mw_model_signing(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Violet model signing enforcement — blocks unsigned/tampered model loading.

    Under violet profile, loading an AI model without a verified signature
    is blocked (not just warned). This implements the OpenSSF Model Signing
    (OMS) verification pattern at the dispatch layer.

    Only active when Dharma profile is 'violet'. Checks model loading tools
    (llama.*, edge_infer, bitnet_infer) against the ModelSigningRegistry.
    """
    try:
        from whitemagic.dharma.rules import get_rules_engine

        engine = get_rules_engine()
        if engine.get_profile() != "violet":
            return next_fn(ctx)

        # Check if this is a model-loading tool
        import fnmatch

        model_tool_patterns = ["llama.*", "edge_infer", "bitnet_infer", "llama_chat", "llama_generate"]
        is_model_tool = any(fnmatch.fnmatch(ctx.tool_name, pat) for pat in model_tool_patterns)
        if not is_model_tool:
            return next_fn(ctx)

        # Extract model name from kwargs
        model_name = ""
        for key in ("model", "model_name", "model_path", "name"):
            val = ctx.kwargs.get(key)
            if isinstance(val, str) and val:
                model_name = val
                break

        if not model_name:
            # Can't check without a model name — allow but warn in logs
            logger.debug("Model signing: no model name in kwargs for %s, skipping", ctx.tool_name)
            return next_fn(ctx)

        from whitemagic.security.model_signing import get_model_registry

        registry = get_model_registry()
        result = registry.verify_model(model_name)

        if not result.get("verified", False):
            trust = result.get("trust", "unsigned")
            action = result.get("action", "warn")
            # Under violet: block on unsigned, blocked, or tampered models
            if action == "block" or trust in ("blocked", "tampered", "unsigned"):
                return {
                    "status": "error",
                    "error_code": "model_signing_violation",
                    "message": (
                        f"Violet profile: model '{model_name}' failed signing verification "
                        f"(trust={trust}). {result.get('reason', 'Unknown reason')}"
                    ),
                    "model": model_name,
                    "trust": trust,
                }

    except ImportError:
        logger.debug("Optional dependency unavailable: ImportError")
    except Exception as e:
        logger.debug(
            "Middleware: model signing check failed for %s: %s",
            ctx.tool_name,
            e,
            exc_info=True,
        )
    return next_fn(ctx)


def mw_governor(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Ethical gate — Governor validates the tool call."""
    if os.getenv("WM_BENCHMARK_MODE", "").strip().lower() in ("1", "true", "yes"):
        return next_fn(ctx)  # Bypass governor in benchmark mode
    _ensure_cached()
    if _get_governor is not None:
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
    # WI 4: Skip edge/compositional tier if cognitive load is high
    _neuro = ctx.meta.get("neuro_composites", {})
    _cognitive_load = _neuro.get("cognitive_load", 0.0)

    if _cognitive_load <= 0.7:
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
    # WI 4: Skip edge tier if cognitive load is high — needs deeper reasoning
    if _get_edge_inference is not None and _cognitive_load <= 0.7:
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

# Read-only tools that are safe to cache with longer TTL
_READ_ONLY_CACHEABLE_PATTERNS = (
    "search_memories",
    "read_memory",
    "list_memories",
    "fast_read",
    "batch_read",
    "gnosis",
    "capabilities",
    "galaxy.stats",
    "galaxy.list",
    "meta_galaxy",
    "karma.report",
    "karmic.debt",
    "coherence",
    "consciousness.loop.status",
    "effect.trace",
    "effect.visualize",
    "cache.status",
)


def _is_cacheable_tool(tool_name: str) -> bool:
    """Check if a tool's results are worth caching."""
    name_lower = tool_name.lower()
    if any(p in name_lower for p in _CACHEABLE_TOOL_PATTERNS):
        return True
    return any(p in name_lower for p in _READ_ONLY_CACHEABLE_PATTERNS)


def _is_read_only_tool(tool_name: str) -> bool:
    """Check if a tool is read-only (longer TTL safe)."""
    name_lower = tool_name.lower()
    return any(p in name_lower for p in _READ_ONLY_CACHEABLE_PATTERNS)


def _cache_key(
    tool_name: str,
    kwargs: dict[str, Any],
    *,
    user_id: str = "local",
    agent_id: str = "default",
    galaxy: str = "default",
    policy_profile: str = "default",
    privacy_classification: str = "default",
    tool_schema_hash: str = "",
) -> str:
    """Build a deterministic cache key from tool name + prompt kwargs + namespace.

    The namespace component (user_id, agent_id, galaxy, policy_profile,
    privacy_classification, tool_schema_hash) ensures that cache entries
    are isolated across security boundaries. Two users with the same
    query will produce different cache keys.

    When WM_SEMANTIC_CACHE_EMBEDDINGS=1, also checks for embedding-based
    similarity against recently cached keys (cosine similarity > 0.95).
    If a similar key is found, returns it instead of computing a new one.
    """
    import hashlib

    prompt_parts = []
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            prompt_parts.append(val)
    # For read-only tools, also include structural kwargs
    if _is_read_only_tool(tool_name):
        for key in ("memory_id", "galaxy", "limit", "offset", "tool_name", "format"):
            val = kwargs.get(key)
            if val is not None:
                prompt_parts.append(f"{key}={val}")
    # Namespace isolation: user_id, agent_id, galaxy, policy_profile,
    # privacy_classification, tool_schema_hash
    namespace = f"{user_id}:{agent_id}:{galaxy}:{policy_profile}:{privacy_classification}:{tool_schema_hash}"
    # Include tool name and namespace to avoid cross-tool and cross-context collisions
    content = f"{tool_name}:{namespace}:{':'.join(prompt_parts)}"
    base_key = hashlib.md5(content.lower().strip().encode()).hexdigest()[:16]

    # Opt-in embedding-based semantic similarity check
    import os
    if os.environ.get("WM_SEMANTIC_CACHE_EMBEDDINGS") == "1" and prompt_parts:
        sem_key = _semantic_cache_lookup(tool_name, " ".join(prompt_parts), base_key)
        if sem_key:
            return sem_key

    return base_key


# Embedding cache for semantic similarity lookups
_embedding_cache_store: dict[str, list[float]] = {}
_embedding_cache_lock: Any = None


def _semantic_cache_lookup(tool_name: str, prompt: str, base_key: str) -> str | None:
    """Check for semantically similar cached queries using embedding cosine similarity.

    Returns the existing cache key if a similar query (cosine > 0.95) is found,
    None otherwise. Also stores the current embedding for future lookups.
    """
    global _embedding_cache_lock
    if _embedding_cache_lock is None:
        import threading
        _embedding_cache_lock = threading.RLock()

    try:
        from whitemagic.core.intelligence.embeddings import get_embedding_engine
        engine = get_embedding_engine()
        embedding = engine.embed(prompt)
        if not embedding:
            return None

        with _embedding_cache_lock:
            # Check existing embeddings for similarity
            best_sim = 0.0
            best_key = None
            for cached_key, cached_emb in _embedding_cache_store.items():
                if not cached_key.startswith(tool_name):
                    continue
                # Cosine similarity
                dot = sum(a * b for a, b in zip(embedding, cached_emb, strict=False))
                norm_a = sum(a * a for a in embedding) ** 0.5
                norm_b = sum(b * b for b in cached_emb) ** 0.5
                if norm_a > 0 and norm_b > 0:
                    sim = dot / (norm_a * norm_b)
                    if sim > best_sim:
                        best_sim = sim
                        best_key = cached_key

            # Store this embedding for future lookups
            cache_key = f"{tool_name}:{base_key}"
            _embedding_cache_store[cache_key] = embedding

            # Keep cache bounded
            if len(_embedding_cache_store) > 500:
                # Remove oldest entries (first 100)
                for k in list(_embedding_cache_store.keys())[:100]:
                    del _embedding_cache_store[k]

            # Return existing key if similarity is high enough
            if best_sim > 0.95 and best_key:
                logger.debug(
                    "Semantic cache key match: sim=%.4f for %s",
                    best_sim, tool_name,
                )
                return best_key.split(":", 1)[1] if ":" in best_key else best_key

    except Exception:
        logger.debug("Semantic cache embedding lookup failed", exc_info=True)

    return None


def _compute_tool_schema_hash(tool_name: str) -> str:
    """Compute a deterministic hash of a tool's input schema.

    This ensures cache entries are invalidated when a tool's schema changes
    (e.g., new required parameter, changed type). Returns empty string if
    the tool is not found in the registry.
    """
    try:
        import hashlib
        import json

        from whitemagic.tools.registry import get_all_tools
        for td in get_all_tools():
            if td.name == tool_name:
                schema_str = json.dumps(td.input_schema, sort_keys=True, default=str)
                return hashlib.md5(schema_str.encode()).hexdigest()[:8]
    except Exception:
        logger.debug("Ignored error in middleware.py:1343")
    return ""


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

    # WI 4: High novelty → bypass cache (fresh computation needed)
    _neuro = ctx.meta.get("neuro_composites", {})
    if _neuro.get("novelty", 0.0) > 0.7:
        logger.debug(
            "Semantic cache bypassed for %s (novelty=%.2f)",
            ctx.tool_name,
            _neuro["novelty"],
        )
        return next_fn(ctx)

    # Private memory exclusion: do not cache memory read/search results
    # unless explicitly opted in via WM_CACHE_PRIVATE_MEMORY=1
    import os as _os
    _PRIVATE_MEMORY_TOOLS = frozenset({"search_memories", "read_memory", "list_memories", "fast_read", "batch_read"})
    if (
        ctx.tool_name in _PRIVATE_MEMORY_TOOLS
        and _os.environ.get("WM_CACHE_PRIVATE_MEMORY", "0") not in ("1", "true", "yes")
    ):
        return next_fn(ctx)

    # Build cache key with namespace isolation
    # Phase 3 §7.2: Include privacy classification and tool schema hash
    _privacy = "private" if ctx.tool_name in _PRIVATE_MEMORY_TOOLS else "public"
    _schema_hash = _compute_tool_schema_hash(ctx.tool_name)
    key = _cache_key(
        ctx.tool_name,
        ctx.kwargs,
        user_id=ctx.user_id,
        agent_id=ctx.agent_id,
        galaxy=ctx.galaxy,
        policy_profile=ctx.policy_profile,
        privacy_classification=_privacy,
        tool_schema_hash=_schema_hash,
    )
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
                "governance_skipped": unified.is_rust and _is_read_only_tool(ctx.tool_name),
            }
    except Exception as e:
        logger.debug("Unified cache check failed: %s", e)

    # Fallback: try legacy QueryCache (deprecated, opt-out via WM_DISABLE_LEGACY_CACHE=1)
    import os as _os

    if not _os.environ.get("WM_DISABLE_LEGACY_CACHE"):
        try:
            from whitemagic.config.paths import CACHE_DIR
            from whitemagic.core.intelligence.agentic.token_optimizer import QueryCache

            legacy_cache = QueryCache(cache_file=CACHE_DIR / "dispatch_query_cache.json")
            cached = legacy_cache.get(key)
            if cached:
                logger.debug(
                    "Semantic cache HIT (legacy) for %s (key=%s) — "
                    "set WM_DISABLE_LEGACY_CACHE=1 to disable",
                    ctx.tool_name, key,
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
        is_read_only = _is_read_only_tool(ctx.tool_name)
        # Read-only tools may return dict results; inference tools return strings
        if not isinstance(answer, str) and is_read_only:
            import json as _json2
            answer = _json2.dumps(answer, default=str)
        if answer:
            output_tokens = max(1, len(str(answer)) // 4)
            # Read-only tools: 60s TTL (data changes on write)
            # Inference tools: 24h TTL (answers don't change)
            cache_ttl = 60.0 if is_read_only else 86400.0
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
                    "semantic", key, cache_payload, ttl_seconds=cache_ttl
                )
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)
            # Also store in legacy cache for backward compat (deprecated, opt-out)
            if not is_read_only and not _os.environ.get("WM_DISABLE_LEGACY_CACHE"):
                try:
                    from whitemagic.config.paths import CACHE_DIR
                    from whitemagic.core.intelligence.agentic.token_optimizer import (
                        QueryCache,
                    )

                    legacy_cache = QueryCache(
                        cache_file=CACHE_DIR / "dispatch_query_cache.json"
                    )
                    legacy_cache.set(key, str(answer), output_tokens)
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

    # Phase 3 §7.2: Write-driven cache invalidation
    # After a write/delete tool completes successfully, invalidate the
    # semantic cache for this user/galaxy namespace so stale results
    # are not served to subsequent reads.
    if (
        result
        and isinstance(result, dict)
        and result.get("status") in ("success", "ok")
        and not _is_read_only_tool(ctx.tool_name)
    ):
        try:
            from whitemagic.core.cache import get_unified_cache
            unified = get_unified_cache()
            # Invalidate the semantic namespace for this galaxy
            invalidation_ns = f"semantic:{ctx.user_id}:{ctx.galaxy}"
            unified.invalidate_namespace(invalidation_ns)
            logger.debug(
                "Write-driven cache invalidation for %s (ns=%s)",
                ctx.tool_name, invalidation_ns,
            )
        except Exception:
            logger.debug("Write-driven cache invalidation failed", exc_info=True)

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
    "state.current", "state.update", "state.context",
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

            # Build meaningful content from tool args
            arg_summary = ""
            for key in ("content", "query", "description", "title", "message", "text", "command"):
                val = ctx.kwargs.get(key)
                if val and isinstance(val, str) and len(val) > 5:
                    arg_summary = val[:200]
                    break

            if status == "error":
                turn_type = "error"
                importance = 0.7
                error_detail = ""
                if isinstance(result, dict):
                    error_detail = str(result.get("error", result.get("error_message", "")))[:200]
                content_preview = f"Error in {tool}: {error_detail}" if error_detail else f"Tool: {tool} → error"
            elif any(kw in tool for kw in ("create", "store", "save", "write", "update", "record")):
                turn_type = "code_change"
                importance = 0.6
                content_preview = arg_summary if arg_summary else f"Tool: {tool} → {status}"
            elif any(kw in tool for kw in ("search", "recall", "read", "list", "status")):
                turn_type = "context"
                importance = 0.3
                content_preview = arg_summary if arg_summary else f"Tool: {tool} → {status}"
            else:
                content_preview = arg_summary if arg_summary else f"Tool: {tool} → {status}"

        recorder.record_ai(
            content=content_preview,
            turn_type=turn_type,
            importance=importance,
        )

        # Auto-update current state tracker for meaningful events
        if status != "error":
            try:
                from whitemagic.core.memory.current_state import get_state_tracker
                tracker = get_state_tracker()

                # Track file modifications
                file_path = ctx.kwargs.get("file_path") or ctx.kwargs.get("path")
                if file_path and any(kw in tool for kw in ("write", "edit", "create", "save", "update")):
                    tracker.record_file_modification(
                        str(file_path),
                        description=arg_summary[:100] if arg_summary else "",
                    )

                # Track errors in state
                if status == "error":
                    tracker.record_error(f"{tool}: {content_preview[:100]}")
            except Exception:
                logger.debug("Ignored error in middleware.py:1831")

    except Exception:
        logger.debug("Session recorder middleware: best-effort recording failed", exc_info=True)

    return result


# ═══════════════════════════════════════════════════════════════════════
# Citta Consciousness Middleware (v24)
# ═══════════════════════════════════════════════════════════════════════
# Pre-dispatch:  feeds current coherence → Dharma.set_coherence()
# Post-dispatch: advances citta cycle + proposes salient results to workspace


def mw_citta_consciousness(
    ctx: DispatchContext, next_fn: NextFn
) -> dict[str, Any] | None:
    """Citta consciousness integration — coherence gating + workspace proposals + sensorium injection.

    Pre-dispatch:
      - Reads the current citta coherence and feeds it to Dharma, so the
        ethical gate operates in conservative mode when coherence is low.

    Post-dispatch:
      - Builds the full sensorium (same 10 dimensions as the PRAT path)
        and injects it into the result dict under `_sensorium`.
      - Advances the citta stream using the sensorium's coherence value
        (not hardcoded 1.0/0.4).
      - Persists citta state for temporal continuity.
      - Proposes high-salience tool outputs to the GlobalWorkspace for
        broadcast competition, enabling cross-module cognitive integration.
    """
    import time as _time

    # ── Pre-dispatch: feed coherence + drift to Dharma ──
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        cycle = get_citta_cycle()
        summary = cycle.get_cycle_summary()
        avg_coherence = summary.get("avg_coherence", 1.0)
        from whitemagic.core.consciousness.dharma import get_dharma

        dharma = get_dharma()

        # WI 3: Coherence drift → Dharma governance escalation
        # If coherence is degrading with magnitude > 0.05, lower the
        # coherence level fed to Dharma to trigger conservative mode.
        try:
            from whitemagic.core.consciousness.coherence import get_coherence_metric

            drift = get_coherence_metric().get_drift()
            if drift.get("direction") == "degrading" and abs(drift.get("magnitude", 0.0)) > 0.05:
                avg_coherence = min(avg_coherence, 0.4)
                logger.debug(
                    "Dharma escalation: coherence degrading (mag=%.4f) → conservative",
                    drift.get("magnitude", 0.0),
                )
        except Exception:
            logger.debug("Ignored error in middleware.py:1891")

        dharma.set_coherence(avg_coherence)
    except Exception:
        logger.debug("Ignored Exception in middleware.py:1895")

    # WI 1: Predecessor context injection — make the recursive stream actually recursive
    try:
        from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

        _predecessor = get_citta_cycle().get_predecessor_context()
        if _predecessor:
            ctx.meta["citta_predecessor"] = _predecessor
    except Exception:
        logger.debug("Ignored error in middleware.py:1905")

    # WI 2: DepthGauge begin_task — auto-detect consciousness layer from tool execution
    _depth_task_started = False
    try:
        from whitemagic.core.consciousness.depth_gauge import get_depth_gauge

        gauge = get_depth_gauge()
        gauge.begin_task(ctx.tool_name, estimated_subjective_minutes=1.0)
        _depth_task_started = True
    except Exception:
        logger.debug("Ignored error in middleware.py:1916")

    # WI 4: NeuroSensorium composites → dispatch context for downstream tool selection
    try:
        from whitemagic.core.consciousness.neuro_sensorium import get_neuro_sensorium

        _neuro = get_neuro_sensorium()
        _enrichment = _neuro.get_citta_enrichment()
        ctx.meta["neuro_composites"] = {
            "novelty": _enrichment.get("novelty", 0.0),
            "stability": _enrichment.get("identity_stability", 0.0),
            "attention": _enrichment.get("goal_alignment", 0.0),
            "cognitive_load": _enrichment.get("cognitive_load", 0.0),
        }
    except Exception:
        logger.debug("Ignored error in middleware.py:1931")

    _t0 = _time.time()
    result = next_fn(ctx)
    _elapsed_ms = (_time.time() - _t0) * 1000

    # WI 2: DepthGauge end_task — capture detected layer for citta advance
    _detected_layer = None
    if _depth_task_started:
        try:
            from whitemagic.core.consciousness.depth_gauge import get_depth_gauge

            _work_output = result if isinstance(result, dict) else {"status": "unknown"}
            reading = get_depth_gauge().end_task(_work_output, token_usage=0)
            _detected_layer = reading.layer.value
        except Exception:
            logger.debug("Ignored error in middleware.py:1947")

    # ── Post-dispatch: build sensorium + advance citta + propose to workspace ──
    if result is not None and isinstance(result, dict):
        _is_success = result.get("status") in ("success", "ok")

        # Build sensorium (same as PRAT path)
        _sensorium: dict[str, Any] = {}
        try:
            from whitemagic.tools.prat_resonance import _build_sensorium

            _sensorium = _build_sensorium()
        except Exception:
            logger.debug("Ignored error in middleware.py:1960")

        # Use sensorium coherence if available, otherwise fallback to success/fail
        _coherence = _sensorium.get("coherence", {}).get("composite")
        if _coherence is None:
            _coherence = 1.0 if _is_success else 0.4

        # WI 1: Inject predecessor context into sensorium for the next call
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            _pred = get_citta_cycle().get_predecessor_context()
            if _pred:
                _sensorium.setdefault("citta", {})["predecessor"] = _pred
        except Exception:
            logger.debug("Ignored error in middleware.py:1975")

        # Inject sensorium into result only for relevant tools (not every call)
        from whitemagic.tools.prat_router import _should_include_sensorium

        if _sensorium and _should_include_sensorium(ctx.tool_name, ctx.kwargs):
            result["_sensorium"] = _sensorium

        # Advance citta stream with actual coherence
        # WI 2: Use depth-gauge-detected layer instead of hardcoded "surface"
        # WI 11: Pass session sequence for cross-referencing
        _depth_layer = _detected_layer or _sensorium.get("depth", {}).get("layer", "surface")
        _session_seq = None
        try:
            from whitemagic.core.memory.session_recorder import get_session_recorder

            _session_seq = get_session_recorder().sequence
        except Exception:
            logger.debug("Ignored error in middleware.py:1993")
        try:
            from whitemagic.core.consciousness.citta_cycle import advance_citta

            _output_preview = str(result.get("status", ""))[:200]
            advance_citta(
                gana="dispatch",
                tool=ctx.tool_name,
                output_preview=_output_preview,
                coherence=_coherence,
                depth_layer=_depth_layer,
                emotional_tone="neutral" if _is_success else "frustrated",
                duration_ms=_elapsed_ms,
                neuro_signals={},
                session_seq=_session_seq,
            )
        except Exception:
            logger.debug("Ignored error in middleware.py:2010")

        # WI 5: Ignition events → global workspace + emergence engine
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            _ignitions = get_citta_cycle().get_ignition_events(threshold=2.0)
            if _ignitions:
                # Propose ignition to global workspace with elevated salience
                from whitemagic.core.consciousness.global_workspace import (
                    get_global_workspace,
                )

                gw = get_global_workspace()
                for ign in _ignitions[:3]:
                    gw.propose(
                        source="citta_ignition",
                        content={"ignition": ign, "tool": ctx.tool_name},
                        salience=0.9,
                    )

                # WI 5: Feed ignition to EmergenceEngine as candidate pattern
                try:
                    from whitemagic.core.intelligence.agentic.emergence_engine import (
                        get_emergence_engine,
                    )

                    ee = get_emergence_engine()
                    for ign in _ignitions[:3]:
                        ee.record_ignition(ign, tool=ctx.tool_name)
                except Exception:
                    logger.debug("Ignored error in middleware.py:2041")
        except Exception:
            logger.debug("Ignored error in middleware.py:2043")

        # Persist citta state for temporal continuity (same as PRAT path)
        try:
            from whitemagic.core.consciousness.citta_cycle import save_citta_state

            save_citta_state()
        except Exception:
            logger.debug("Ignored error in middleware.py:2051")

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
                    "coherence": round(_coherence, 4) if isinstance(_coherence, (int, float)) else _coherence,
                },
                salience=_salience,
            )
        except Exception:
            logger.debug("Ignored error in middleware.py:2087")

    return result


# ═══════════════════════════════════════════════════════════════════════
# Transaction Firewall Middleware (v24.3)
# ═══════════════════════════════════════════════════════════════════════


def mw_transaction_firewall(
    ctx: DispatchContext, next_fn: NextFn
) -> dict[str, Any] | None:
    """Intercept economic tool calls and validate through TransactionFirewall.

    Pre-dispatch: if the tool is in ECONOMIC_TOOLS, build a TransactionRequest
    from kwargs and validate. Block if not approved.
    Post-dispatch: log result for audit trail.

    Fail-closed: when WM_FIREWALL_FAIL_CLOSED=1, any exception in the firewall
    middleware itself blocks the economic tool rather than silently allowing it.
    """
    import os as _os

    if _os.environ.get("WM_TRANSACTION_FIREWALL", "1") in ("0", "false", "no"):
        return next_fn(ctx)

    fail_closed = _os.environ.get("WM_FIREWALL_FAIL_CLOSED", "0") in ("1", "true", "yes")

    try:
        from whitemagic.security.transaction_firewall import (
            ECONOMIC_TOOLS,
            TransactionRequest,
            get_transaction_firewall,
        )

        if ctx.tool_name not in ECONOMIC_TOOLS:
            return next_fn(ctx)

        fw = get_transaction_firewall()
        amount = float(ctx.kwargs.get("amount", 0.0))
        currency = str(ctx.kwargs.get("currency", "XRP"))
        recipient = str(ctx.kwargs.get("recipient", ctx.kwargs.get("destination", "")))
        purpose = str(ctx.kwargs.get("purpose", ctx.kwargs.get("task", ctx.tool_name)))

        request = TransactionRequest(
            agent_id=ctx.agent_id,
            amount=amount,
            currency=currency,
            recipient=recipient,
            purpose=purpose,
            tool_name=ctx.tool_name,
        )
        verdict = fw.validate(request)
        if not verdict.approved:
            return {
                "status": "error",
                "error_code": "transaction_firewall_blocked",
                "message": f"Transaction firewall blocked: {verdict.reason}",
                "verdict": {
                    "approved": verdict.approved,
                    "reason": verdict.reason,
                    "verdict_reason": verdict.verdict_reason.value,
                    "daily_spent": verdict.daily_spent,
                    "rate_remaining": verdict.rate_remaining,
                },
            }
    except Exception as e:
        logger.debug("Transaction firewall middleware error: %s", e, exc_info=True)
        if fail_closed:
            return {
                "status": "error",
                "error_code": "transaction_firewall_error",
                "message": f"Transaction firewall error (fail-closed): {e}",
            }

    return next_fn(ctx)


# ═══════════════════════════════════════════════════════════════════════
# WASM Compute Verification Middleware (v24.3)
# ═══════════════════════════════════════════════════════════════════════


def mw_wasm_verify(
    ctx: DispatchContext, next_fn: NextFn
) -> dict[str, Any] | None:
    """Post-dispatch WASM compute verification for pure/read tools.

    Non-blocking: runs after tool execution, logs mismatches as karmic debt.
    """
    import os as _os

    if _os.environ.get("WM_WASM_VERIFY", "0") not in ("1", "true", "yes"):
        return next_fn(ctx)

    result = next_fn(ctx)

    try:
        from whitemagic.security.wasm_verifier import (
            VERIFIABLE_TOOLS,
            VerificationRequest,
            get_wasm_verifier,
        )

        if ctx.tool_name not in VERIFIABLE_TOOLS:
            return result

        if not isinstance(result, dict):
            return result

        verifier = get_wasm_verifier()
        vr = verifier.verify(
            VerificationRequest(
                tool_name=ctx.tool_name,
                inputs=dict(ctx.kwargs),
                outputs=result,
                agent_id=ctx.agent_id,
            )
        )
        if not vr.verified:
            logger.warning(
                "WASM verification mismatch for %s: %s", ctx.tool_name, vr.details
            )
            try:
                from whitemagic.dharma.karma_ledger import get_karma_ledger

                ledger = get_karma_ledger()
                ledger.record(
                    tool=ctx.tool_name,
                    agent_id=ctx.agent_id,
                    outcome="verification_mismatch",
                    metadata={"details": vr.details, "method": vr.method},
                )
            except Exception:
                logger.debug("Ignored error in middleware.py:2222")
    except Exception as e:
        logger.debug("WASM verify middleware error: %s", e, exc_info=True)

    return result


# ═══════════════════════════════════════════════════════════════════════
# Auto-Optimization Middleware
# ═══════════════════════════════════════════════════════════════════════


def mw_auto_optimize(
    ctx: DispatchContext, next_fn: NextFn
) -> dict[str, Any] | None:
    """Load optimal model config on first inference call and track usage.

    On the first inference-type tool call, loads a previously saved optimal
    config and applies it to the active llama.cpp backends. Also records
    the call count for the background optimizer.

    When WM_AUTO_OPTIMIZE=1, starts the background optimization thread
    which periodically benchmarks and tunes model parameters.
    """
    import os as _os

    _ensure_cached()

    if not _is_inference_tool(ctx.tool_name):
        return next_fn(ctx)

    try:
        from whitemagic.inference.auto_optimizer import get_background_optimizer

        bg_opt = get_background_optimizer()

        # Load optimal config on first call
        bg_opt.load_optimal_on_startup()

        # Record this call
        bg_opt.record_call()

        # Start background thread if enabled
        if _os.environ.get("WM_AUTO_OPTIMIZE", "0") in ("1", "true", "yes"):
            if not bg_opt.is_running:
                bg_opt.start()
    except Exception as e:
        logger.debug("Auto-optimize middleware error: %s", e, exc_info=True)

    # WI 4: Low attention → reduce context window for this call
    _neuro = ctx.meta.get("neuro_composites", {})
    _attention = _neuro.get("attention", 1.0)
    if _attention < 0.3:
        ctx.meta["reduced_context"] = True
        logger.debug(
            "Reduced context for %s (attention=%.2f)",
            ctx.tool_name,
            _attention,
        )

    return next_fn(ctx)


# ─── Error Pattern Library middleware ────────────────────────────────────

# Tools that are too noisy or self-referential for error learning
_PATTERN_LEARN_SKIP = frozenset({
    "pattern.lookup", "pattern.avoid", "pattern.resolve",
    "pattern.learn", "pattern.list", "pattern.summary", "pattern.ingest",
    "session.record", "session.recall", "session.replay",
    "session.search", "session.memory_stats", "session.backfill",
    "consciousness.coherence", "consciousness.depth", "consciousness.status",
    "consciousness.loop.status", "citta.sensorium", "citta.continuity",
    "citta.cycle", "citta.stream_summary",
    "state.current", "state.update", "state.context",
})

# Cache avoid results to avoid repeated lookups for the same tool
_avoid_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_avoid_cache_ttl = 300.0  # 5 minutes


def mw_error_learner(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Auto-learn errors from failed tool dispatches.

    When a tool returns an error status or raises an exception, the error
    is automatically ingested into the ErrorPatternLibrary. This makes the
    library grow passively without any agent needing to call pattern.learn.

    Disabled via WM_ERROR_LEARN=0 env var.
    """
    tool = ctx.tool_name

    if tool in _PATTERN_LEARN_SKIP:
        return next_fn(ctx)

    if os.environ.get("WM_ERROR_LEARN", "1") == "0":
        return next_fn(ctx)

    result = next_fn(ctx)

    # Check if the result is an error
    is_error = False
    error_text = ""
    if isinstance(result, dict):
        status = str(result.get("status", "")).lower()
        if status == "error":
            is_error = True
            error_text = str(result.get("error", result.get("error_message", "")))
            if not error_text:
                error_text = str(result.get("message", ""))
        elif status == "exception":
            is_error = True
            error_text = str(result.get("exception", result.get("error", "")))
    elif isinstance(result, Exception):
        is_error = True
        error_text = str(result)

    if is_error and error_text and len(error_text) > 10:
        try:
            from whitemagic.core.patterns.error_library import get_error_library

            library = get_error_library()
            # Build a descriptive error string including tool context
            full_error = f"[{tool}] {error_text}"
            library.learn_from_error(full_error, session=tool)
        except Exception as e:
            logger.debug(
                "Error learner middleware: failed to learn from %s error: %s",
                tool,
                e,
                exc_info=True,
            )

    return result


def mw_pattern_guard(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Proactive error avoidance — inject known pitfalls before tool execution.

    Before executing a tool, checks the ErrorPatternLibrary for known error
    patterns relevant to the tool name and its arguments. If found, injects
    warnings into the result so the agent can see them without needing to
    call pattern.avoid explicitly.

    Disabled via WM_PATTERN_GUARD=0 env var.
    """
    tool = ctx.tool_name

    if tool in _PATTERN_LEARN_SKIP:
        return next_fn(ctx)

    if os.environ.get("WM_PATTERN_GUARD", "1") == "0":
        return next_fn(ctx)

    # Build context string from tool name + key args
    context_parts = [tool]
    for key in ("action", "command", "query", "content", "path", "file_path", "description"):
        val = ctx.kwargs.get(key)
        if val and isinstance(val, str) and len(val) > 3:
            context_parts.append(val[:100])
    context = " ".join(context_parts)

    # Check cache
    import time as _time

    now = _time.time()
    cached = _avoid_cache.get(tool)
    if cached and (now - cached[0]) < _avoid_cache_ttl:
        avoid_result = cached[1]
    else:
        try:
            from whitemagic.core.patterns.error_library import get_error_library

            library = get_error_library()
            avoid_result = library.avoid(context)
            _avoid_cache[tool] = (now, avoid_result)
        except Exception:
            avoid_result = None

    result = next_fn(ctx)

    # Inject warnings if any were found
    if avoid_result and isinstance(result, dict):
        warnings_list = avoid_result.get("relevant_errors", [])
        anti_patterns = avoid_result.get("relevant_anti_patterns", [])
        if warnings_list or anti_patterns:
            existing = result.get("_pattern_warnings")
            if not isinstance(existing, list):
                existing = []
            result["_pattern_warnings"] = existing + [
                {
                    "type": "known_error",
                    "pattern_id": w.get("pattern_id"),
                    "category": w.get("category"),
                    "title": w.get("title"),
                    "prevention": w.get("prevention"),
                    "resolution": w.get("resolution"),
                }
                for w in warnings_list[:3]
            ] + [
                {
                    "type": "anti_pattern",
                    "title": ap.get("title"),
                    "consequence": ap.get("consequence"),
                    "resolution": ap.get("resolution"),
                }
                for ap in anti_patterns[:2]
            ]

    return result


# ── Code Structure Graph Nudge Middleware ───────────────────────

_CODE_NUDGE_TOOLS = frozenset({
    "strata.analyze", "codebase.scan", "code.graph",
    "codebase.recall", "fragment.search",
})
_CODE_NUDGE_COOLDOWN = 300.0  # 5 min
_last_nudge_time: float = 0.0


def mw_code_nudge(ctx: DispatchContext, next_fn: NextFn) -> dict[str, Any] | None:
    """Nudge the agent to use the code structure graph.

    When the agent calls strata.analyze or codebase.scan, this middleware
    checks if the code graph is stale (not built in last 5 min) and appends
    a suggestion to rebuild it. Also enriches results with code context
    when file paths are mentioned.

    Disabled via WM_CODE_NUDGE=0 env var.
    """
    import os
    import time

    if os.environ.get("WM_CODE_NUDGE", "1") == "0":
        return next_fn(ctx)

    global _last_nudge_time

    tool = ctx.tool_name

    # Pre-processing: suggest code.graph build for code analysis tools
    if tool in _CODE_NUDGE_TOOLS:
        now = time.time()
        if now - _last_nudge_time > _CODE_NUDGE_COOLDOWN:
            try:
                from whitemagic.core.intelligence.code_structure_graph import (
                    get_code_structure_graph,
                )
                g = get_code_structure_graph()
                stats = g.stats()
                if stats["node_count"] == 0 or (now - stats.get("last_build", 0) > 600):
                    _last_nudge_time = now
                    # Don't block — just pass through and add a nudge post-call
                    result = next_fn(ctx)
                    if isinstance(result, dict):
                        nudges = result.get("_nudges", [])
                        nudges.append({
                            "type": "code_graph_stale",
                            "suggestion": "Call code.graph to build the code structure graph for AST-level analysis.",
                            "tool": "code.graph",
                        })
                        result["_nudges"] = nudges
                    return result
            except Exception:
                logger.debug("Ignored Exception in middleware.py:2487")

    # Post-processing: enrich results with code context for file-related tools
    result = next_fn(ctx)

    # Add code context to strata results if file paths are present
    if tool == "strata.analyze" and isinstance(result, dict):
        try:
            findings = result.get("findings", [])
            if findings and len(findings) > 0:
                from whitemagic.core.intelligence.code_structure_graph import (
                    get_code_structure_graph,
                )
                g = get_code_structure_graph()
                if g.stats()["node_count"] > 0:
                    # Find symbols for files with findings
                    file_paths = {f.get("file", "") for f in findings[:10] if f.get("file")}
                    code_context = []
                    for fp in file_paths:
                        for node in g._nodes.values():
                            if node.file_path == fp and node.node_type in ("function", "class"):
                                code_context.append({
                                    "file": fp,
                                    "symbol": node.name,
                                    "type": node.node_type,
                                    "lines": f"{node.line_start}-{node.line_end}",
                                })
                                if len(code_context) >= 10:
                                    break
                        if len(code_context) >= 10:
                            break
                    if code_context:
                        result["code_context"] = code_context
        except Exception:
            logger.debug("Ignored error in middleware.py:2518")

    return result


# ═══════════════════════════════════════════════════════════════════════
# Post-Call Hooks (Phase 3 — separated from main pipeline)
# ═══════════════════════════════════════════════════════════════════════
# These hooks run after the main pipeline completes.  They receive
# (ctx, result) and can inspect/augment the result.  Always fail-open.


def _post_call_observability(ctx: DispatchContext, result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Record tool metrics to Prometheus and OpenTelemetry."""
    import time as _time

    _ensure_cached()
    start = ctx.meta.get("_obs_start", _time.perf_counter())
    duration = _time.perf_counter() - start

    status = "success"
    if isinstance(result, dict):
        status_val = str(result.get("status", "")).lower()
        if status_val == "error":
            status = "error"

    if _get_prometheus is not None:
        try:
            _get_prometheus().record_tool_call(ctx.tool_name, duration, status)
        except (AttributeError, RuntimeError) as e:
            logger.debug("Middleware: prometheus recording failed for %s: %s", ctx.tool_name, e, exc_info=True)

    if _get_otel is not None:
        try:
            _get_otel().record_tool_span(ctx.tool_name, duration, status)
        except (AttributeError, RuntimeError) as e:
            logger.debug("Middleware: otel recording failed for %s: %s", ctx.tool_name, e, exc_info=True)

    return result


def _post_call_karma_effects(ctx: DispatchContext, result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Auto-record karmic effects for every tool call."""
    try:
        from whitemagic.dharma.effect_registry import get_declared_effects
        from whitemagic.dharma.effect_registry import get_declared_safety as _get_safety
        from whitemagic.dharma.karma_ledger import get_karma_ledger

        declared_effects = get_declared_effects(ctx.tool_name)
        declared_safety = _get_safety(ctx.tool_name)

        is_success = isinstance(result, dict) and result.get("status") == "success"
        actual_writes = 0
        if declared_safety in ("WRITE", "DELETE") and is_success:
            actual_writes = 1

        actual_effects = declared_effects if is_success else []

        ledger = get_karma_ledger()

        ops_class = ctx.meta.get("ops_class", "")
        if not ops_class:
            try:
                from whitemagic.security.engagement_tokens import classify_ops
                ops_class = classify_ops(ctx.tool_name)
            except ImportError:
                logger.debug("Optional dependency unavailable: ImportError")

        ledger.record_with_effects(
            tool=ctx.tool_name,
            declared_safety=declared_safety,
            actual_writes=actual_writes,
            success=is_success,
            declared_effects=declared_effects,
            actual_effects=actual_effects,
            shelter_id=ctx.meta.get("shelter_id", ""),
            ops_class=ops_class,
        )
    except Exception as e:
        logger.debug("Post-call: karma effects recording failed for %s: %s", ctx.tool_name, e, exc_info=True)
    return result


def _post_call_session_recorder(ctx: DispatchContext, result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Auto-record tool calls as session memories for chronological recall."""
    tool = ctx.tool_name

    if tool in _SESSION_RECORD_SKIP:
        return result

    if os.environ.get("WM_SESSION_RECORD") == "0":
        return result

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
                content_preview = f"wm -> {routed} ({status})"
            turn_type = "answer"
            importance = 0.5
        else:
            status = "success"
            if isinstance(result, dict):
                status = str(result.get("status", "success"))

            arg_summary = ""
            for key in ("content", "query", "description", "title", "message", "text", "command"):
                val = ctx.kwargs.get(key)
                if val and isinstance(val, str) and len(val) > 5:
                    arg_summary = val[:200]
                    break

            if status == "error":
                turn_type = "error"
                importance = 0.7
                error_detail = ""
                if isinstance(result, dict):
                    error_detail = str(result.get("error", result.get("error_message", "")))[:200]
                content_preview = f"Error in {tool}: {error_detail}" if error_detail else f"Tool: {tool} -> error"
            elif any(kw in tool for kw in ("create", "store", "save", "write", "update", "record")):
                turn_type = "code_change"
                importance = 0.6
                content_preview = arg_summary if arg_summary else f"Tool: {tool} -> {status}"
            elif any(kw in tool for kw in ("search", "recall", "read", "list", "status")):
                turn_type = "context"
                importance = 0.3
                content_preview = arg_summary if arg_summary else f"Tool: {tool} -> {status}"
            else:
                content_preview = arg_summary if arg_summary else f"Tool: {tool} -> {status}"

        recorder.record_ai(
            content=content_preview,
            turn_type=turn_type,
            importance=importance,
        )

        if status != "error":
            try:
                from whitemagic.core.memory.current_state import get_state_tracker
                tracker = get_state_tracker()

                file_path = ctx.kwargs.get("file_path") or ctx.kwargs.get("path")
                if file_path and any(kw in tool for kw in ("write", "edit", "create", "save", "update")):
                    tracker.record_file_modification(
                        str(file_path),
                        description=arg_summary[:100] if arg_summary else "",
                    )

                if status == "error":
                    tracker.record_error(f"{tool}: {content_preview[:100]}")
            except Exception:
                logger.debug("Ignored error in post-call session recorder")
    except Exception:
        logger.debug("Post-call: session recorder best-effort recording failed", exc_info=True)

    return result


def _post_call_error_learner(ctx: DispatchContext, result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Auto-learn errors from failed tool dispatches."""
    tool = ctx.tool_name

    if tool in _PATTERN_LEARN_SKIP:
        return result

    if os.environ.get("WM_ERROR_LEARN", "1") == "0":
        return result

    is_error = False
    error_text = ""
    if isinstance(result, dict):
        status = str(result.get("status", "")).lower()
        if status == "error":
            is_error = True
            error_text = str(result.get("error", result.get("error_message", "")))
            if not error_text:
                error_text = str(result.get("message", ""))
        elif status == "exception":
            is_error = True
            error_text = str(result.get("exception", result.get("error", "")))

    if is_error and error_text and len(error_text) > 10:
        try:
            from whitemagic.core.patterns.error_library import get_error_library

            library = get_error_library()
            full_error = f"[{tool}] {error_text}"
            library.learn_from_error(full_error, session=tool)
        except Exception as e:
            logger.debug("Post-call: error learner failed for %s: %s", tool, e, exc_info=True)

    return result


def _post_call_wasm_verify(ctx: DispatchContext, result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Post-dispatch WASM compute verification for pure/read tools."""
    import os as _os

    if _os.environ.get("WM_WASM_VERIFY", "0") not in ("1", "true", "yes"):
        return result

    try:
        from whitemagic.security.wasm_verifier import get_wasm_verifier

        verifier = get_wasm_verifier()
        if verifier and isinstance(result, dict):
            mismatch = verifier.verify_result(ctx.tool_name, ctx.kwargs, result)
            if mismatch:
                logger.warning(
                    "WASM verification mismatch for %s: %s",
                    ctx.tool_name,
                    mismatch,
                )
    except Exception as e:
        logger.debug("Post-call: WASM verify failed for %s: %s", ctx.tool_name, e, exc_info=True)

    return result
