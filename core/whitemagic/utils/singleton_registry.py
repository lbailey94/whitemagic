"""Singleton Registry — Automatic singleton tracking and reset for tests.

This module provides a centralized registry for singleton instances,
allowing automatic reset between tests without manual bookkeeping.

Two patterns are supported:

1. **New-style (factory-based):** Singletons register a factory callable.
   The registry caches the instance and clears it on reset::

    from whitemagic.utils.singleton_registry import register_singleton

    def get_my_singleton():
        return register_singleton("my_module.MySingleton", lambda: MySingleton())

2. **Legacy (module-attribute):** Singletons that use the ``_var = None``
   pattern at module level are tracked via a declarative table. The
   registry sets the attribute back to ``None`` on reset::

    from whitemagic.utils.singleton_registry import reset_all_singletons

    # In conftest.py:
    reset_all_singletons()  # clears both new-style and legacy singletons

The legacy table is auto-discovered at first reset from
``_LEGACY_SINGLETONS`` below.  Each entry is ``(module_path, attr_name)``.
Stale entries (module not importable or attribute missing) are silently
skipped.
"""

from __future__ import annotations

import importlib
import logging
import sys
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy singleton table — module-level ``_var = None`` pattern.
#
# This replaces the fragile ~80-entry manual list that lived in
# ``conftest.py:_reset_singletons()``.  Each tuple is
# ``(module_dotted_path, attribute_name)``.
#
# When adding a new singleton that uses the ``_var = None`` pattern,
# add it here.  Eventually these should be migrated to the factory-based
# ``register_singleton()`` API so the list shrinks over time.
# ---------------------------------------------------------------------------
_LEGACY_SINGLETONS: list[tuple[str, str]] = [
    # --- Memory subsystem ---
    ("whitemagic.core.memory.unified", "_unified_memory_instances"),
    ("whitemagic.core.memory.galactic_map", "_galactic_map"),
    ("whitemagic.core.memory.consolidation", "_consolidator"),
    ("whitemagic.core.memory.lifecycle", "_manager"),
    ("whitemagic.core.memory.mindful_forgetting", "_engine_instance"),
    ("whitemagic.core.memory.holographic", "_holo_memory"),
    ("whitemagic.core.memory.constellations", "_detector_instance"),
    ("whitemagic.core.memory.association_miner", "_miner_instance"),
    # v14.0 Living Graph
    ("whitemagic.core.memory.graph_walker", "_walker"),
    ("whitemagic.core.memory.graph_engine", "_engine"),
    ("whitemagic.core.memory.surprise_gate", "_gate"),
    ("whitemagic.core.memory.bridge_synthesizer", "_synthesizer"),
    # --- Background daemons (stop called by WorkerRegistry, now null the refs) ---
    ("whitemagic.core.memory.neural.decay_daemon", "_daemon"),
    ("whitemagic.core.intelligence.learning.rapid_cognition", "_instance"),
    # --- Resonance / scheduling ---
    ("whitemagic.core.resonance.salience_arbiter", "_arbiter"),
    ("whitemagic.core.resonance._consolidated", "_bus"),
    # --- Harmony / governance ---
    ("whitemagic.harmony.vector", "_harmony_vector"),
    ("whitemagic.harmony.homeostatic_loop", "_loop"),
    ("whitemagic.harmony.anomaly_detector", "_detector"),
    ("whitemagic.dharma.karma_ledger", "_ledger"),
    # --- Tools / dispatch ---
    ("whitemagic.tools.dependency_graph", "_graph"),
    ("whitemagic.tools.circuit_breaker", "_registry"),
    ("whitemagic.tools.rate_limiter", "_instance"),
    ("whitemagic.tools.tool_permissions", "_registry_instance"),
    ("whitemagic.tools.sandbox", "_sandbox"),
    ("whitemagic.tools.speculative_prefetch", "_prefetcher"),
    ("whitemagic.tools.handlers.broker", "_BROKER_INSTANCE"),
    # --- Cache ---
    ("whitemagic.cache.redis", "_redis_cache"),
    # --- Intelligence ---
    ("whitemagic.core.intelligence.bicameral", "_reasoner_instance"),
    ("whitemagic.core.intelligence.emotion_drive", "_instance"),
    ("whitemagic.core.intelligence.self_model", "_instance"),
    # --- Dreaming ---
    ("whitemagic.core.dreaming.dream_cycle", "_dream_cycle"),
    # --- Consciousness subsystem ---
    ("whitemagic.core.consciousness.citta_cycle", "_cycle"),
    ("whitemagic.core.consciousness.citta_cycle", "_always_on"),
    ("whitemagic.core.consciousness.citta_cycle", "_replay_delivered"),
    ("whitemagic.core.consciousness.coherence", "_coherence"),
    ("whitemagic.core.consciousness.coherence", "_smarana"),
    ("whitemagic.core.consciousness.guna_balance", "_guna_balance"),
    ("whitemagic.core.consciousness.consciousness_loop", "_loop"),
    ("whitemagic.core.consciousness.possibility_explorer", "_explorer"),
    ("whitemagic.core.consciousness.meta_galaxy", "_meta_galaxy"),
    ("whitemagic.core.consciousness.knowledge_gap_loop", "_kg_loop"),
    ("whitemagic.core.consciousness.prediction_calibration", "_calibration"),
    ("whitemagic.core.consciousness.apotheosis_engine", "_apotheosis_engine"),
    # --- Evolution ---
    ("whitemagic.core.evolution.recursive_loop", "_loop"),
    # --- Memory / scanning ---
    ("whitemagic.core.memory.codebase_scanner", "_scanner"),
    # --- Pattern Consciousness ---
    (
        "whitemagic.core.patterns.pattern_consciousness.resonance_cascade",
        "_orchestrator",
    ),
    # --- Mesh ---
    ("whitemagic.mesh.awareness", "_awareness"),
    # --- Intelligence / Session / Monitoring ---
    ("whitemagic.core.intelligence.researcher", "_researcher"),
    ("whitemagic.core.intelligence.omni.skill_forge", "_forge"),
    ("whitemagic.core.memory.session_recorder", "_recorder"),
    ("whitemagic.core.monitoring.tool_usage_tracker", "_tracker"),
    # --- Cache ---
    ("whitemagic.core.cache.unified_cache_bridge", "_unified_cache"),
    # --- PRAT resonance state ---
    ("whitemagic.tools.prat_resonance", "_state"),
    # --- Mesh subsystem ---
    ("whitemagic.mesh.dilo_co", "_coordinator"),
    ("whitemagic.mesh.client", "_client"),
    ("whitemagic.mesh.cognitive_client", "_client"),
    ("whitemagic.mesh.ws_bridge", "_bridge"),
    # --- Cascade / context ---
    ("whitemagic.core.cascade.context_synthesizer", "_synthesizer"),
    ("whitemagic.core.cascade.adaptive_portal", "_portal"),
    ("whitemagic.core.cascade.holographic_context", "_holographic_injector"),
    # --- Cycle engine lazy imports ---
    ("whitemagic.core.cycle_engine", "_yy_tracker"),
    ("whitemagic.core.cycle_engine", "_zodiacal"),
    ("whitemagic.core.cycle_engine", "_wu_xing"),
    ("whitemagic.core.cycle_engine", "_context_synth"),
    ("whitemagic.core.cycle_engine", "_gan_ying_bus"),
    # --- Security subsystem ---
    ("whitemagic.security.event_bus", "_bus"),
    ("whitemagic.security.security_breaker", "_monitor"),
    ("whitemagic.security.engagement_tokens", "_manager"),
    ("whitemagic.security.wasm_verifier", "_verifier"),
    ("whitemagic.security.model_signing", "_registry"),
    ("whitemagic.security.mcp_integrity", "_instance"),
    ("whitemagic.security.sandbox", "_default_sandbox"),
    ("whitemagic.security.canary_tokens", "_manager"),
    ("whitemagic.security.vault", "_vault"),
    ("whitemagic.security.transaction_firewall", "_firewall"),
    ("whitemagic.security.tool_gating", "_tool_gate"),
    ("whitemagic.security.semantic_defense", "_embedder_instance"),
    ("whitemagic.security.zodiac.ledger", "_ledger_instance"),
    # --- Connection ---
    ("whitemagic.connection.synastry_governor", "_governor"),
    # --- Root modules ---
    ("whitemagic.root_modules.session_templates", "_templates"),
    ("whitemagic.root_modules.lazy_memory_loader", "_loader"),
    ("whitemagic.root_modules.symbolic_memory", "_sym_mem"),
    ("whitemagic.root_modules.pattern_discovery_enhanced", "_discovery"),
    ("whitemagic.root_modules.concept_map", "_map"),
    ("whitemagic.root_modules.workflow_patterns", "_patterns"),
    ("whitemagic.root_modules.yin_synthesis", "_synthesis"),
    ("whitemagic.root_modules.backup_system", "_backup"),
    ("whitemagic.root_modules.symbolic", "_engine"),
    ("whitemagic.root_modules.workspace_loader", "_loader"),
    ("whitemagic.root_modules.delta_tracking", "_tracker"),
    # --- Pattern consciousness (additional) ---
    ("whitemagic.core.patterns.pattern_consciousness.pattern_engine_enhanced", "_engine"),
    ("whitemagic.core.patterns.pattern_consciousness.gan_ying_integration", "_hub"),
    # --- Defense ---
    ("whitemagic.defense.granular_awareness", "_awareness"),
    ("whitemagic.defense.autoimmune", "_autoimmune"),
    ("whitemagic.defense.multi_agent", "_coordinator"),
    ("whitemagic.defense.homeostatic_monitor", "_monitor"),
    # --- Memory matrix ---
    ("whitemagic.memory_matrix.seen_registry", "_registry"),
    ("whitemagic.memory_matrix.timeline", "_timeline"),
    ("whitemagic.memory_matrix.embedding_index", "_index"),
    ("whitemagic.memory_matrix.matrix", "_matrix"),
    # --- Systems / monitoring ---
    ("whitemagic.systems.monitoring.system_monitor", "_monitor"),
    # --- Economy ---
    ("whitemagic.core.economy.wallet_manager", "_wallet_manager"),
]

# Class-level ``_instance`` singletons (``__new__``-based pattern).
# These need ``cls._instance = None`` rather than module-attribute nulling.
_LEGACY_CLASS_SINGLETONS: list[tuple[str, str]] = [
    ("whitemagic.core.consciousness.dharma", "DharmaProtocol"),
    ("whitemagic.core.nervous_system", "NervousSystem"),
    ("whitemagic.agents.warps", "WarpManager"),
    ("whitemagic.mesh.warp_marketplace", "WarpMarketplace"),
]


class SingletonRegistry:
    """Centralized registry for singleton instances.

    Tracks singleton instances by name and provides a reset mechanism
    for test isolation. New singletons are automatically included in
    test resets without manual bookkeeping.

    Thread-safe via an RLock protecting instance/factory maps.
    """

    _instances: dict[str, Any] = {}
    _factories: dict[str, Callable[[], Any]] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, name: str, factory: Callable[[], Any]) -> Any:
        """Register a singleton factory and return the instance.

        Args:
            name: Unique identifier for the singleton (e.g., "module.ClassName")
            factory: Callable that creates the singleton instance

        Returns:
            The singleton instance (cached or newly created)
        """
        with cls._lock:
            if name in cls._instances:
                return cls._instances[name]

            cls._factories[name] = factory
            instance = factory()
            cls._instances[name] = instance
            logger.debug("Registered singleton: %s", name)
            return instance

    @classmethod
    def reset(cls, name: str) -> None:
        """Reset a specific singleton by clearing its cached instance.

        Args:
            name: The singleton identifier
        """
        with cls._lock:
            if name in cls._instances:
                del cls._instances[name]
                logger.debug("Reset singleton: %s", name)

    @classmethod
    def reset_all(cls) -> None:
        """Reset all registered singletons (both new-style and legacy).

        Clears all cached instances from the factory-based registry,
        then nulls module-level attributes for legacy singletons.
        Stale entries are silently skipped.
        """
        with cls._lock:
            count = len(cls._instances)
            cls._instances.clear()
            logger.debug("Reset all %s factory singletons", count)

        # Legacy module-attribute singletons
        for mod_name, attr_name in _LEGACY_SINGLETONS:
            mod = sys.modules.get(mod_name)
            if mod is None:
                # Try importing — if it fails, skip silently
                try:
                    mod = importlib.import_module(mod_name)
                except Exception:
                    continue
            if mod and hasattr(mod, attr_name):
                current = getattr(mod, attr_name)
                if isinstance(current, dict):
                    current.clear()
                else:
                    setattr(mod, attr_name, None)

        # Legacy class-level _instance singletons
        for mod_name, cls_name in _LEGACY_CLASS_SINGLETONS:
            mod = sys.modules.get(mod_name)
            if mod is None:
                try:
                    mod = importlib.import_module(mod_name)
                except Exception:
                    continue
            if mod and hasattr(mod, cls_name):
                klass = getattr(mod, cls_name)
                if hasattr(klass, "_instance"):
                    klass._instance = None

    @classmethod
    def get_registered_names(cls) -> list[str]:
        """Get list of all registered singleton names.

        Returns:
            List of singleton identifiers
        """
        with cls._lock:
            return list(cls._factories.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a singleton is registered.

        Args:
            name: The singleton identifier

        Returns:
            True if registered, False otherwise
        """
        with cls._lock:
            return name in cls._factories

    @classmethod
    def get_legacy_count(cls) -> int:
        """Return the number of legacy singleton entries (for diagnostics)."""
        return len(_LEGACY_SINGLETONS) + len(_LEGACY_CLASS_SINGLETONS)


def register_singleton(name: str, factory: Callable[[], Any]) -> Any:
    """Convenience function to register a singleton.

    Args:
        name: Unique identifier for the singleton
        factory: Callable that creates the singleton instance

    Returns:
        The singleton instance
    """
    return SingletonRegistry.register(name, factory)


def reset_singleton(name: str) -> None:
    """Convenience function to reset a specific singleton.

    Args:
        name: The singleton identifier
    """
    SingletonRegistry.reset(name)


def reset_all_singletons() -> None:
    """Convenience function to reset all registered singletons."""
    SingletonRegistry.reset_all()


def get_registered_singletons() -> list[str]:
    """Get list of all registered singleton names.

    Returns:
        List of singleton identifiers
    """
    return SingletonRegistry.get_registered_names()
