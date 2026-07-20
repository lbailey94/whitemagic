"""Core-side ports for tool-side services.

This module provides thin indirection layers so that core/ modules can
invoke tool-side functionality (dispatch, broker) without directly
importing from whitemagic.tools.*, preserving the architectural boundary.

The ports are call-time imports — they resolve to the real implementation
on first call and cache the reference.  This keeps the dependency direction
clean: core → ports → (lazy) tools.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# ── Dispatch Port ────────────────────────────────────────────────────

_dispatch_fn: Any = None


def call_tool(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """Port for whitemagic.tools.unified_api.call_tool.

    Core modules should use this instead of importing from tools directly.
    Resolves lazily so the import only happens on first actual call.
    """
    global _dispatch_fn
    if _dispatch_fn is None:
        from whitemagic.tools.unified_api import call_tool as _ct
        _dispatch_fn = _ct
    return _dispatch_fn(tool_name, **kwargs)


# ── Broker Port ──────────────────────────────────────────────────────

_resolve_redis_url_fn: Any = None
_get_broker_fn: Any = None
_run_fn: Any = None


def resolve_redis_url() -> str | None:
    """Port for whitemagic.tools.handlers.broker._resolve_redis_url."""
    global _resolve_redis_url_fn
    if _resolve_redis_url_fn is None:
        from whitemagic.tools.handlers.broker import _resolve_redis_url
        _resolve_redis_url_fn = _resolve_redis_url
    return _resolve_redis_url_fn()


async def get_broker() -> Any:
    """Port for whitemagic.tools.handlers.broker._get_broker."""
    global _get_broker_fn
    if _get_broker_fn is None:
        from whitemagic.tools.handlers.broker import _get_broker
        _get_broker_fn = _get_broker
    return await _get_broker_fn()


def run(coro: Any) -> Any:
    """Port for whitemagic.tools.handlers.broker._run."""
    global _run_fn
    if _run_fn is None:
        from whitemagic.tools.handlers.broker import _run
        _run_fn = _run
    return _run_fn(coro)


# ── Dispatch Table Port ──────────────────────────────────────────────

_dispatch_table_dispatch_fn: Any = None
_dispatch_table_fn: Any = None
_emit_gan_ying_fn: Any = None


def dispatch(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    """Port for whitemagic.tools.dispatch_table.dispatch."""
    global _dispatch_table_dispatch_fn
    if _dispatch_table_dispatch_fn is None:
        from whitemagic.tools.dispatch_table import dispatch as _d
        _dispatch_table_dispatch_fn = _d
    return _dispatch_table_dispatch_fn(tool_name, **kwargs)


def get_dispatch_table() -> dict[str, Any]:
    """Port for whitemagic.tools.dispatch_table.DISPATCH_TABLE."""
    from whitemagic.tools.dispatch_table import DISPATCH_TABLE
    return DISPATCH_TABLE


def emit_gan_ying(event: str, **kwargs: Any) -> None:
    """Port for whitemagic.tools.unified_api._emit_gan_ying."""
    global _emit_gan_ying_fn
    if _emit_gan_ying_fn is None:
        from whitemagic.tools.unified_api import _emit_gan_ying
        _emit_gan_ying_fn = _emit_gan_ying
    return _emit_gan_ying_fn(event, **kwargs)


# ── Inference Port ───────────────────────────────────────────────────

_generate_fn: Any = None


def llama_generate(prompt: str, **kwargs: Any) -> Any:
    """Port for whitemagic.tools.handlers.llama_tools._generate."""
    global _generate_fn
    if _generate_fn is None:
        from whitemagic.tools.handlers.llama_tools import _generate
        _generate_fn = _generate
    return _generate_fn(prompt, **kwargs)


def llama_tools_module() -> Any:
    """Lazy access to whitemagic.tools.handlers.llama_tools module."""
    import whitemagic.tools.handlers.llama_tools as m
    return m


_handle_llama_generate_fn: Any = None


def handle_llama_generate(*args: Any, **kwargs: Any) -> Any:
    """Port for whitemagic.tools.handlers.llama_tools.handle_llama_generate."""
    global _handle_llama_generate_fn
    if _handle_llama_generate_fn is None:
        from whitemagic.tools.handlers.llama_tools import handle_llama_generate
        _handle_llama_generate_fn = handle_llama_generate
    return _handle_llama_generate_fn(*args, **kwargs)


# ── Tool Bandit Port ─────────────────────────────────────────────────

_get_tool_bandit_fn: Any = None


def get_tool_bandit() -> Any:
    """Port for whitemagic.tools.handlers.tool_bandit.get_tool_bandit."""
    global _get_tool_bandit_fn
    if _get_tool_bandit_fn is None:
        from whitemagic.tools.handlers.tool_bandit import get_tool_bandit
        _get_tool_bandit_fn = get_tool_bandit
    return _get_tool_bandit_fn()


# ── Strata Port ──────────────────────────────────────────────────────

_strata_cls: Any = None
_finding_severity_cls: Any = None


def get_strata() -> Any:
    """Port for whitemagic.tools.strata.Strata."""
    global _strata_cls
    if _strata_cls is None:
        from whitemagic.tools.strata import Strata
        _strata_cls = Strata
    return _strata_cls


def get_finding_severity() -> Any:
    """Port for whitemagic.tools.strata.FindingSeverity."""
    global _finding_severity_cls
    if _finding_severity_cls is None:
        from whitemagic.tools.strata import FindingSeverity
        _finding_severity_cls = FindingSeverity
    return _finding_severity_cls


# ── Security Port ────────────────────────────────────────────────────

_map_findings_fn: Any = None
_get_contest_pipeline_fn: Any = None


def map_strata_mitre(findings: Any) -> Any:
    """Port for whitemagic.tools.security.strata_mitre_map.map_findings."""
    global _map_findings_fn
    if _map_findings_fn is None:
        from whitemagic.tools.security.strata_mitre_map import map_findings
        _map_findings_fn = map_findings
    return _map_findings_fn(findings)


def get_contest_pipeline() -> Any:
    """Port for whitemagic.tools.security.contest_pipeline.get_contest_pipeline."""
    global _get_contest_pipeline_fn
    if _get_contest_pipeline_fn is None:
        from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
        _get_contest_pipeline_fn = get_contest_pipeline
    return _get_contest_pipeline_fn()


# ── Middleware Port ──────────────────────────────────────────────────

_dispatch_context_cls: Any = None
_next_fn_cls: Any = None


def get_dispatch_context() -> Any:
    """Port for whitemagic.tools.middleware.DispatchContext."""
    global _dispatch_context_cls
    if _dispatch_context_cls is None:
        from whitemagic.tools.middleware import DispatchContext
        _dispatch_context_cls = DispatchContext
    return _dispatch_context_cls


def get_next_fn() -> Any:
    """Port for whitemagic.tools.middleware.NextFn."""
    global _next_fn_cls
    if _next_fn_cls is None:
        from whitemagic.tools.middleware import NextFn
        _next_fn_cls = NextFn
    return _next_fn_cls


# ── Tool Surface Port ────────────────────────────────────────────────

_get_surface_counts_fn: Any = None


def get_surface_counts() -> Any:
    """Port for whitemagic.tools.tool_surface.get_surface_counts."""
    global _get_surface_counts_fn
    if _get_surface_counts_fn is None:
        from whitemagic.tools.tool_surface import get_surface_counts
        _get_surface_counts_fn = get_surface_counts
    return _get_surface_counts_fn()


# ── Scratchpad Port ──────────────────────────────────────────────────

_handle_scratchpad_fn: Any = None


def handle_scratchpad(*args: Any, **kwargs: Any) -> Any:
    """Port for whitemagic.tools.handlers.scratchpad.handle_scratchpad."""
    global _handle_scratchpad_fn
    if _handle_scratchpad_fn is None:
        from whitemagic.tools.handlers.scratchpad import handle_scratchpad
        _handle_scratchpad_fn = handle_scratchpad
    return _handle_scratchpad_fn(*args, **kwargs)


# ── Circuit Breaker Port ─────────────────────────────────────────────

_get_breaker_registry_fn: Any = None


def get_breaker_registry() -> Any:
    """Port for whitemagic.tools.circuit_breaker.get_breaker_registry."""
    global _get_breaker_registry_fn
    if _get_breaker_registry_fn is None:
        from whitemagic.tools.circuit_breaker import get_breaker_registry
        _get_breaker_registry_fn = get_breaker_registry
    return _get_breaker_registry_fn()


# ── Registry Port ────────────────────────────────────────────────────

_get_tool_fn: Any = None


def get_tool(tool_name: str) -> Any:
    """Port for whitemagic.tools.registry.get_tool."""
    global _get_tool_fn
    if _get_tool_fn is None:
        from whitemagic.tools.registry import get_tool
        _get_tool_fn = get_tool
    return _get_tool_fn(tool_name)


_get_registry_fn: Any = None


def get_registry() -> Any:
    """Port for whitemagic.tools.registry.get_registry."""
    global _get_registry_fn
    if _get_registry_fn is None:
        from whitemagic.tools.registry import get_registry
        _get_registry_fn = get_registry
    return _get_registry_fn()


# ── PRAT Port ────────────────────────────────────────────────────────

def get_tool_to_gana() -> dict[str, str]:
    """Port for whitemagic.tools.prat_mappings.TOOL_TO_GANA."""
    from whitemagic.tools.prat_mappings import TOOL_TO_GANA
    return TOOL_TO_GANA


def get_prat_router_tool_to_gana() -> dict[str, str]:
    """Port for whitemagic.tools.prat_router.TOOL_TO_GANA."""
    from whitemagic.tools.prat_router import TOOL_TO_GANA
    return TOOL_TO_GANA


def route_prat_call(*args: Any, **kwargs: Any) -> Any:
    """Port for whitemagic.tools.prat_router.route_prat_call."""
    from whitemagic.tools.prat_router import route_prat_call
    return route_prat_call(*args, **kwargs)


def get_prat_resonance_state() -> Any:
    """Port for whitemagic.tools.prat_resonance.get_resonance_state."""
    from whitemagic.tools.prat_resonance import get_resonance_state
    return get_resonance_state()


def get_prat_meta(gana: str) -> Any:
    """Port for whitemagic.tools.prat_resonance._get_meta."""
    from whitemagic.tools.prat_resonance import _get_meta
    return _get_meta(gana)


def get_gana_meta() -> dict[str, Any]:
    """Port for whitemagic.tools.prat_resonance._GANA_META."""
    from whitemagic.tools.prat_resonance import _GANA_META
    return _GANA_META
