"""Effect Registry — MandalaOS Phase A.

Auto-infers declared EffectSignature for every registered tool based on
ToolDefinition metadata (category, safety), WRITE_TOOLS membership, and
known tool behavior patterns.

This module provides:
- ``infer_effects(tool_name)`` — return declared effects for a tool
- ``get_declared_safety(tool_name)`` — return READ/WRITE/DELETE string
- ``build_effect_registry()`` — build the full registry from ToolDefinitions

The registry is used by the dispatch pipeline to automatically call
``KarmaLedger.record_with_effects()`` for every tool invocation.
"""

from __future__ import annotations

import logging

from whitemagic.dharma.karma_ledger import EffectSignature, EffectType

logger = logging.getLogger(__name__)

# ── Category → EffectType mapping ──────────────────────────────────────

_CATEGORY_EFFECTS: dict[str, EffectType] = {
    "memory": EffectType.LOCAL_WRITE,
    "session": EffectType.LOCAL_WRITE,
    "garden": EffectType.LOCAL_WRITE,
    "system": EffectType.LOCAL_WRITE,
    "governor": EffectType.PURE,
    "governance": EffectType.PURE,
    "dharma": EffectType.PURE,
    "security": EffectType.DESTRUCTIVE,
    "browser": EffectType.NETWORK,
    "inference": EffectType.PURE,
    "agent": EffectType.NETWORK,
    "broker": EffectType.NETWORK,
    "voting": EffectType.PURE,
    "introspection": EffectType.OBSERVATION,
    "metrics": EffectType.OBSERVATION,
    "edge": EffectType.OBSERVATION,
    "archaeology": EffectType.OBSERVATION,
    "synthesis": EffectType.PURE,
    "gana": EffectType.PURE,
    "task": EffectType.LOCAL_WRITE,
    "watcher": EffectType.OBSERVATION,
}

# ── Tools that make network calls ──────────────────────────────────────

_NETWORK_TOOLS: set[str] = {
    "browser.navigate",
    "browser.click",
    "browser.screenshot",
    "browser.scroll",
    "browser.fill",
    "browser.evaluate",
    "browser.close",
    "research_web",
    "web_search",
    "web_fetch",
    "read_url_content",
    "fetch_url",
    "llama.generate",
    "llama.chat",
    "llama.agent",
    "ollama.generate",
    "ollama.chat",
    "inference.route",
    "route_inference",
    "cloud_inference",
    "mesh.broadcast",
    "mesh.connect",
    "galaxy.share",
    "broker.publish",
    "broker.history",
}

# ── Tools that are destructive ─────────────────────────────────────────

_DESTRUCTIVE_TOOLS: set[str] = {
    "delete_memory",
    "memory_delete",
    "galaxy.delete",
    "garden_delete",
    "shelter.destroy",
    "mandala.destroy",
    "session.delete",
    "delete_session",
    "vitality",
}

# ── Tools that are pure (no side effects) ──────────────────────────────

_PURE_TOOLS: set[str] = {
    "gnosis",
    "capabilities",
    "explain_this",
    "galaxy.list",
    "galaxy.status",
    "galaxy.list_types",
    "galaxy.stats",
    "galaxy.route",
    "shelter.status",
    "health_report",
    "karma.report",
    "harmony.vector",
    "tool.graph",
    "maturity.assess",
    "homeostasis",
    "consciousness.loop.status",
    "session.recall",
    "session.replay",
    "session.search",
    "session.memory_stats",
    "grimoire_suggest",
    "grimoire_auto_status",
    "grimoire_walkthrough",
    "grimoire_recommend",
}

# ── Tools that only observe (logging, metrics, telemetry) ──────────────

_OBSERVATION_TOOLS: set[str] = {
    "telemetry",
    "otel.metrics",
    "otel.spans",
    "anomaly.check",
    "anomaly.history",
    "anomaly.status",
    "karma.verify_chain",
    "tool_usage_stats",
    "get_metrics_summary",
    "get_yin_yang_balance",
    "green_score",
}


def _infer_effect_type(tool_name: str, category: str = "", safety: str = "") -> EffectType:
    """Infer the primary EffectType for a tool.

    Priority: explicit tool sets > safety level > category defaults.
    """
    # Explicit tool sets take priority
    if tool_name in _DESTRUCTIVE_TOOLS:
        return EffectType.DESTRUCTIVE
    if tool_name in _NETWORK_TOOLS:
        return EffectType.NETWORK
    if tool_name in _PURE_TOOLS:
        return EffectType.PURE
    if tool_name in _OBSERVATION_TOOLS:
        return EffectType.OBSERVATION

    # Fall back to safety level
    safety_upper = safety.upper() if safety else ""
    if safety_upper == "DELETE":
        return EffectType.DESTRUCTIVE
    if safety_upper == "READ":
        return EffectType.PURE

    # Fall back to category
    if category and category in _CATEGORY_EFFECTS:
        return _CATEGORY_EFFECTS[category]

    # Default: local write (conservative assumption)
    return EffectType.LOCAL_WRITE


def infer_effects(
    tool_name: str,
    category: str = "",
    safety: str = "",
) -> list[EffectSignature]:
    """Infer declared EffectSignatures for a tool.

    Returns a list of pre-declared effects that the tool is expected to produce.
    Most tools produce a single primary effect; some may produce secondary effects.
    """
    primary = _infer_effect_type(tool_name, category, safety)

    effects = [
        EffectSignature(
            effect_type=primary,
            target=_infer_target(tool_name, primary),
            description=f"Declared effect for {tool_name}",
            declared=True,
        )
    ]

    # Some tools have secondary effects
    if tool_name in _NETWORK_TOOLS and primary != EffectType.NETWORK:
        effects.append(
            EffectSignature(
                effect_type=EffectType.NETWORK,
                target="external",
                description=f"Network call by {tool_name}",
                declared=True,
            )
        )

    return effects


def _infer_target(tool_name: str, effect_type: EffectType) -> str:
    """Infer a reasonable target string for an effect."""
    if effect_type == EffectType.NETWORK:
        return "external"
    if effect_type == EffectType.DESTRUCTIVE:
        return f"resource:{tool_name}"
    if effect_type == EffectType.LOCAL_WRITE:
        if "memory" in tool_name:
            return "memory:db"
        if "session" in tool_name:
            return "session:db"
        if "garden" in tool_name:
            return "garden:db"
        if "galaxy" in tool_name:
            return "galaxy:db"
        return "state:local"
    if effect_type == EffectType.OBSERVATION:
        return "telemetry"
    return ""


def get_declared_safety(tool_name: str, safety: str = "") -> str:
    """Get the declared safety level for a tool.

    Falls back to inferring from the tool name if not provided.
    """
    if safety:
        return safety.upper()
    if tool_name in _DESTRUCTIVE_TOOLS:
        return "DELETE"
    if tool_name in _PURE_TOOLS or tool_name in _OBSERVATION_TOOLS:
        return "READ"
    return "WRITE"


def build_effect_registry() -> dict[str, list[EffectSignature]]:
    """Build the full effect registry from all registered ToolDefinitions.

    Iterates over the LazyToolRegistry to build a mapping of
    tool_name -> [EffectSignature, ...].
    """
    registry: dict[str, list[EffectSignature]] = {}

    try:
        from whitemagic.tools.registry import get_all_tools

        for tool_def in get_all_tools():
            effects = infer_effects(
                tool_def.name,
                category=tool_def.category.value if tool_def.category else "",
                safety=tool_def.safety.value if tool_def.safety else "",
            )
            registry[tool_def.name] = effects
    except Exception as e:
        logger.debug("Failed to build full effect registry: %s", e, exc_info=True)

    # Also check WRITE_TOOLS for any tools not in the registry
    try:
        from whitemagic.tools.dispatch_core import WRITE_TOOLS

        for tool_name in WRITE_TOOLS:
            if tool_name not in registry:
                registry[tool_name] = infer_effects(tool_name, safety="WRITE")
    except Exception as e:
        logger.debug("Failed to merge WRITE_TOOLS: %s", e, exc_info=True)

    logger.info("Effect registry: %d tools mapped", len(registry))
    return registry


# ── Singleton ──────────────────────────────────────────────────────────

_registry_cache: dict[str, list[EffectSignature]] | None = None


def get_effect_registry() -> dict[str, list[EffectSignature]]:
    """Get the cached effect registry, building it on first access."""
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = build_effect_registry()
    return _registry_cache


def get_declared_effects(tool_name: str) -> list[EffectSignature]:
    """Get declared effects for a single tool from the registry."""
    registry = get_effect_registry()
    if tool_name in registry:
        return registry[tool_name]
    # Infer on-the-fly for unregistered tools
    return infer_effects(tool_name)
