# ruff: noqa: BLE001
"""Unified Nervous System — v23 adaptation.

Wires biological subsystems together for emergent intelligence.
Adapted from WM2's UnifiedNervousSystem for v23.3.0 architecture.

Instead of WM2's BaseEngine, this uses the v23 GanYingBus for
cross-subsystem communication and the existing subsystem modules
(dream_cycle, resonance_engine, coherence, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class UnifiedNervousSystem:
    """Unified nervous system integrating all biological subsystems.

    Enables emergent behaviors through cross-system communication
    via the GanYingBus event bus.

    Seven subsystems (adapted for v23):
    1. Dream — dream_cycle.py
    2. Resonance — resonance_engine.py / GanYingBus
    3. Evolution — pattern_engines.py / learning.py
    4. Consciousness — coherence.py / depth_gauge.py
    5. Emergence — synchronicity_detector.py
    6. Metabolism — token_economy.py
    7. Immune — security/tool_gating.py
    """

    SUBSYSTEM_NAMES = [
        "dream",
        "resonance",
        "evolution",
        "consciousness",
        "emergence",
        "metabolism",
        "immune",
    ]

    def __init__(self) -> None:
        self.subsystems: dict[str, Any] = {}
        self._wired = False
        self._init_subsystems()

    def _init_subsystems(self) -> None:
        """Initialize all subsystems with graceful degradation."""
        for name in self.SUBSYSTEM_NAMES:
            try:
                self.subsystems[name] = self._load_subsystem(name)
            except Exception as e:
                logger.debug("Subsystem %s not available: %s", name, e, exc_info=True)
                self.subsystems[name] = None

    def _load_subsystem(self, name: str) -> Any:
        """Load a subsystem by name."""
        if name == "dream":
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
            return get_dream_cycle()
        if name == "resonance":
            from whitemagic.resonance.gan_ying_async import GanYingBus
            return GanYingBus()
        if name == "evolution":
            from whitemagic.core.intelligence.pattern_engines import (
                get_pattern_engine,
            )
            return get_pattern_engine()
        if name == "consciousness":
            from whitemagic.core.consciousness.coherence import CoherenceMetric
            return CoherenceMetric()
        if name == "emergence":
            from whitemagic.core.consciousness.synchronicity_detector import (
                SynchronicityDetector,
            )
            return SynchronicityDetector()
        if name == "metabolism":
            from whitemagic.core.consciousness.token_economy import (
                get_token_tracker,
            )
            return get_token_tracker()
        if name == "immune":
            from whitemagic.security.tool_gating import get_tool_gate
            return get_tool_gate()
        return None

    def wire_all(self) -> dict[str, bool]:
        """Wire all subsystems together."""
        results: dict[str, bool] = {}
        for name, subsystem in self.subsystems.items():
            results[name] = subsystem is not None
        self._wired = all(results.values())
        return results

    def route_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Route a signal through appropriate subsystems."""
        if not self._wired:
            return {"error": "nervous_system_not_wired"}

        signal_type = signal.get("type", "unknown")
        results: dict[str, Any] = {}

        routing: dict[str, list[str]] = {
            "consolidation": ["dream"],
            "dream": ["dream"],
            "harmony": ["resonance"],
            "resonance": ["resonance"],
            "evolution": ["evolution"],
            "mutation": ["evolution"],
            "awareness": ["consciousness"],
            "consciousness": ["consciousness"],
            "emergence": ["emergence"],
            "serendipity": ["emergence"],
            "decay": ["metabolism"],
            "metabolism": ["metabolism"],
            "threat": ["immune"],
            "immune": ["immune"],
        }

        for target in routing.get(signal_type, []):
            subsystem = self.subsystems.get(target)
            if subsystem is not None:
                try:
                    if hasattr(subsystem, "process_signal"):
                        results[target] = subsystem.process_signal(signal)
                    elif hasattr(subsystem, "handle_event"):
                        results[target] = subsystem.handle_event(signal)
                    else:
                        results[target] = {"status": "received", "signal": signal_type}
                except Exception as e:
                    results[target] = {"error": str(e)}

        return results

    def get_system_health(self) -> dict[str, Any]:
        """Get health status of entire nervous system."""
        health: dict[str, Any] = {
            "wired": self._wired,
            "subsystems": {},
        }

        for name, subsystem in self.subsystems.items():
            if subsystem is None:
                health["subsystems"][name] = {"active": False, "reason": "not_loaded"}
            else:
                health["subsystems"][name] = {"active": True}

        active_count = sum(1 for s in self.subsystems.values() if s is not None)
        health["active_subsystems"] = active_count
        health["total_subsystems"] = len(self.SUBSYSTEM_NAMES)

        return health


# Singleton
_nervous_system: UnifiedNervousSystem | None = None


def get_nervous_system() -> UnifiedNervousSystem:
    """Get the global UnifiedNervousSystem singleton."""
    global _nervous_system
    if _nervous_system is None:
        _nervous_system = UnifiedNervousSystem()
    return _nervous_system
