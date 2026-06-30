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
            from whitemagic.core.resonance.gan_ying_async import get_async_bus

            return get_async_bus()
        if name == "evolution":
            from whitemagic.core.intelligence.learning.rapid_cognition import (
                RapidCognition,
            )

            return RapidCognition()
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


class CrossSubsystemPatterns:
    """Common patterns for cross-subsystem communication.

    Recovered from v0.2 archive. Provides predefined event patterns
    for coherence cascades, emergence detection, security threats,
    dream cycle completion, and memory pressure.
    """

    @staticmethod
    def coherence_cascade(
        nervous_system: UnifiedNervousSystem, coherence_score: float
    ) -> None:
        """When coherence drops, notify multiple subsystems to take corrective action."""
        if coherence_score < 0.6:
            nervous_system.route_signal(
                {
                    "type": "consciousness",
                    "event": "coherence.critical",
                    "coherence": coherence_score,
                    "action": "trigger_dream",
                }
            )
            nervous_system.route_signal(
                {
                    "type": "resonance",
                    "event": "harmony.check",
                    "coherence": coherence_score,
                }
            )

    @staticmethod
    def emergence_detected(
        nervous_system: UnifiedNervousSystem,
        emergence_type: str,
        details: dict[str, Any],
    ) -> None:
        """When emergence is detected, propagate to consciousness and evolution."""
        nervous_system.route_signal(
            {
                "type": "emergence",
                "event": "emergence.record",
                "emergence_type": emergence_type,
                "details": details,
            }
        )
        nervous_system.route_signal(
            {
                "type": "consciousness",
                "event": "coherence.adjust",
                "adjustment": 0.05,
                "reason": emergence_type,
            }
        )

    @staticmethod
    def security_threat(
        nervous_system: UnifiedNervousSystem,
        threat_type: str,
        severity: str,
    ) -> None:
        """Security threats trigger immune response and notify consciousness."""
        nervous_system.route_signal(
            {
                "type": "immune",
                "event": "immune.activate",
                "threat": threat_type,
                "severity": severity,
            }
        )
        nervous_system.route_signal(
            {
                "type": "consciousness",
                "event": "threat_awareness",
                "threat": threat_type,
                "immune_response": "active",
            }
        )

    @staticmethod
    def dream_cycle_complete(
        nervous_system: UnifiedNervousSystem,
        cycle_results: dict[str, Any],
    ) -> None:
        """When dream cycle completes, update consciousness and trigger metabolism."""
        nervous_system.route_signal(
            {
                "type": "consciousness",
                "event": "coherence.restore",
                "dream_results": cycle_results,
            }
        )
        nervous_system.route_signal(
            {
                "type": "metabolism",
                "event": "metabolism.consolidate",
                "constellations": cycle_results.get("constellations", []),
            }
        )

    @staticmethod
    def memory_pressure(
        nervous_system: UnifiedNervousSystem,
        usage_percent: float,
    ) -> None:
        """When memory pressure is high, trigger metabolism."""
        nervous_system.route_signal(
            {
                "type": "metabolism",
                "event": "forgetting_sweep",
                "pressure": usage_percent,
                "strategy": "gentle",
            }
        )


def wire_cross_subsystem_patterns() -> dict[str, bool]:
    """Wire CrossSubsystemPatterns into the GanYingBus event system.

    Registers event handlers so that cross-subsystem patterns
    fire automatically when relevant events are emitted.

    Returns:
        Dict mapping pattern name to wiring success.
    """
    results: dict[str, bool] = {}
    try:
        from whitemagic.core.resonance.gan_ying_async import get_async_bus

        bus = get_async_bus()
        uns = get_nervous_system()

        def _on_coherence_check(event):
            coherence = (
                event.data.get("coherence", 1.0) if hasattr(event, "data") else 1.0
            )
            CrossSubsystemPatterns.coherence_cascade(uns, coherence)
            results["coherence_cascade_wired"] = True

        def _on_emergence(event):
            etype = (
                event.data.get("emergence_type", "unknown")
                if hasattr(event, "data")
                else "unknown"
            )
            CrossSubsystemPatterns.emergence_detected(uns, etype, {})
            results["emergence_wired"] = True

        def _on_security_threat(event):
            threat = (
                event.data.get("threat", "unknown")
                if hasattr(event, "data")
                else "unknown"
            )
            severity = (
                event.data.get("severity", "high") if hasattr(event, "data") else "high"
            )
            CrossSubsystemPatterns.security_threat(uns, threat, severity)
            results["security_wired"] = True

        def _on_dream_complete(event):
            CrossSubsystemPatterns.dream_cycle_complete(uns, {})
            results["dream_wired"] = True

        def _on_memory_pressure(event):
            pressure = (
                event.data.get("pressure", 50.0) if hasattr(event, "data") else 50.0
            )
            CrossSubsystemPatterns.memory_pressure(uns, pressure)
            results["memory_wired"] = True

        bus.on("coherence.check", _on_coherence_check)
        bus.on("emergence.detected", _on_emergence)
        bus.on("security.threat", _on_security_threat)
        bus.on("dream.cycle_complete", _on_dream_complete)
        bus.on("memory.pressure", _on_memory_pressure)

        results["all_wired"] = True
    except Exception as e:
        logger.debug("Cross-subsystem pattern wiring failed: %s", e)
        results["all_wired"] = False

    return results


# Singleton
_nervous_system: UnifiedNervousSystem | None = None


def get_nervous_system() -> UnifiedNervousSystem:
    """Get the global UnifiedNervousSystem singleton."""
    global _nervous_system
    if _nervous_system is None:
        _nervous_system = UnifiedNervousSystem()
    return _nervous_system
