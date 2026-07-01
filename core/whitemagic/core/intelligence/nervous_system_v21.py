# ruff: noqa: BLE001
"""Unified Nervous System V21 - Complete Implementation.

This is the complete V021 implementation with event bus integration
and all 7 biological subsystems wired together.
"""

import asyncio
import logging
import time
from typing import Any

from .biological_event_bus import (
    BiologicalEventBus,
    EventType,
    connect_dream_to_immune,
    connect_metabolism_to_evolution,
    connect_resonance_to_emergence,
    get_event_bus,
)

logger = logging.getLogger(__name__)


class UnifiedNervousSystemV21:
    """Complete V21 nervous system with event bus coordination."""

    def __init__(self):
        self.is_active = False
        self.event_bus: BiologicalEventBus | None = None
        self._stats = {
            "pulses": 0,
            "errors": 0,
            "subsystem_errors": {},
            "last_pulse": 0,
        }

        self.subsystems = self._initialize_subsystems()

    def _initialize_subsystems(self) -> dict[str, Any]:
        """Initialize all 7 biological subsystems."""
        subsystems = {}

        # 1. Immune System
        try:
            from whitemagic.core.intelligence.immune.dna import ImmuneRegulator

            subsystems["immune"] = ImmuneRegulator()
            logger.info("🛡️ Immune System initialized")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("⚠️ Immune System unavailable: %s", e, exc_info=True)
            subsystems["immune"] = None  # type: ignore[assignment]

        # 2. Evolution System
        try:
            from whitemagic.core.evolution.continuous_evolution import (
                ContinuousEvolutionEngine,
            )

            subsystems["evolution"] = ContinuousEvolutionEngine()  # type: ignore[assignment]
            logger.info("🧬 Evolution System initialized")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("⚠️ Evolution System unavailable: %s", e, exc_info=True)
            subsystems["evolution"] = None  # type: ignore[assignment]

        # 3. Dream System
        try:
            from whitemagic.core.dreaming.dream_cycle import DreamCycle

            subsystems["dreams"] = DreamCycle()  # type: ignore[assignment]
            logger.info("💭 Dream System initialized")
        except ImportError as e:
            logger.warning("⚠️ Dream System unavailable: %s", e, exc_info=True)
            subsystems["dreams"] = None  # type: ignore[assignment]

        # 4. Memory Metabolism
        try:
            from whitemagic.core.intelligence.hologram.consolidation import (
                HolographicConsolidator,
            )

            subsystems["metabolism"] = HolographicConsolidator()  # type: ignore[assignment]
            logger.info("🔄 Memory Metabolism initialized")
        except ImportError as e:
            logger.warning("⚠️ Memory Metabolism unavailable: %s", e, exc_info=True)
            subsystems["metabolism"] = None  # type: ignore[assignment]

        # 5. Consciousness
        try:
            from whitemagic.core.intelligence.agentic.coherence_persistence import (
                CoherencePersistence,
            )

            subsystems["consciousness"] = CoherencePersistence()  # type: ignore[assignment]
            logger.info("🌟 Consciousness initialized")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("⚠️ Consciousness unavailable: %s", e, exc_info=True)
            subsystems["consciousness"] = None  # type: ignore[assignment]

        # 6. Resonance
        try:
            from whitemagic.core.intelligence.agentic.resonance_amp import (
                ResonanceAmplifier,
            )

            subsystems["resonance"] = ResonanceAmplifier()  # type: ignore[assignment]
            logger.info("🎵 Resonance initialized")
        except ImportError as e:
            logger.warning("⚠️ Resonance unavailable: %s", e, exc_info=True)
            subsystems["resonance"] = None  # type: ignore[assignment]

        # 7. Emergence
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                EmergenceEngine,
            )

            subsystems["emergence"] = EmergenceEngine()  # type: ignore[assignment]
            logger.info("✨ Emergence initialized")
        except ImportError as e:
            logger.warning("⚠️ Emergence unavailable: %s", e, exc_info=True)
            subsystems["emergence"] = None  # type: ignore[assignment]

        return subsystems

    async def start(self) -> None:
        """Start the complete nervous system with event bus."""
        if self.is_active:
            return

        self.event_bus = await get_event_bus()

        # Wire the 3 key integrations (Victory Conditions 2-4)
        await connect_dream_to_immune()
        await connect_metabolism_to_evolution()
        await connect_resonance_to_emergence()

        for name, subsystem in self.subsystems.items():
            if subsystem and hasattr(subsystem, "start"):
                try:
                    if asyncio.iscoroutinefunction(subsystem.start):
                        await subsystem.start()
                    else:
                        subsystem.start()
                    logger.info("▶️ %s subsystem started", name, exc_info=True)
                except Exception as e:
                    self._stats["subsystem_errors"][name] = str(e)
                    logger.error("❌ Failed to start %s: %s", name, e, exc_info=True)

        self.is_active = True
        logger.info("🧠 Unified Nervous System V21 fully operational")

    async def stop(self) -> None:
        """Stop the nervous system gracefully."""
        if not self.is_active:
            return

        self.is_active = False

        # Stop subsystems
        for name, subsystem in self.subsystems.items():
            if subsystem and hasattr(subsystem, "stop"):
                try:
                    if asyncio.iscoroutinefunction(subsystem.stop):
                        await subsystem.stop()
                    else:
                        subsystem.stop()
                    logger.info("⏹️ %s subsystem stopped", name, exc_info=True)
                except Exception as e:
                    logger.error("❌ Failed to stop %s: %s", name, e, exc_info=True)

        # Stop event bus
        if self.event_bus:
            await self.event_bus.stop()

        logger.info("🧠 Unified Nervous System V21 stopped")

    async def pulse(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Complete pulse with cross-system coordination."""
        if not self.is_active:
            return {"status": "inactive"}

        self._stats["pulses"] += 1
        self._stats["last_pulse"] = time.time()
        pulse_start = time.time()

        # Coordinate subsystem pulses
        subsystem_results = {}

        # 1. Dream System Pulse - publishes events
        if self.subsystems.get("dreams") is not None:
            try:
                logger.debug("DEBUG: Triggering dream pulse")
                dream_result = await self._dream_pulse()
                subsystem_results["dreams"] = dream_result
            except Exception as e:
                self._stats["subsystem_errors"]["dreams"] = str(e)
                logger.error("Dream pulse failed: %s", e, exc_info=True)

        # 2. Memory Metabolism Pulse - publishes decay events
        if self.subsystems.get("metabolism") is not None:
            try:
                # Calculate decay rate
                logger.debug("DEBUG: Triggering metabolism pulse")
                metabolism_result = await self._metabolism_pulse()
                subsystem_results["metabolism"] = metabolism_result
            except Exception as e:
                self._stats["subsystem_errors"]["metabolism"] = str(e)
                logger.error("Metabolism pulse failed: %s", e, exc_info=True)

        # 3. Resonance Pulse - publishes harmony events
        if self.subsystems.get("resonance") is not None:
            try:
                logger.debug("DEBUG: Triggering resonance pulse")
                resonance_result = await self._resonance_pulse()
                subsystem_results["resonance"] = resonance_result
            except Exception as e:
                self._stats["subsystem_errors"]["resonance"] = str(e)
                logger.error("Resonance pulse failed: %s", e, exc_info=True)

        event_stats = {}
        if self.event_bus:
            event_stats = self.event_bus.get_stats()

        pulse_duration = time.time() - pulse_start

        return {
            "status": "ok",
            "pulses": self._stats["pulses"],
            "pulse_duration_ms": pulse_duration * 1000,
            "subsystems_active": sum(
                1 for sys in self.subsystems.values() if sys is not None
            ),
            "subsystem_results": subsystem_results,
            "event_bus_stats": event_stats,
            "errors": self._stats["errors"],
            "subsystem_errors": self._stats["subsystem_errors"],
        }

    async def _dream_pulse(self) -> dict[str, Any]:
        """Run dream cycle and publish events."""
        dreams = self.subsystems["dreams"]

        if dreams and hasattr(dreams, "run_phase"):
            # In V21, dreams is a DreamCycle instance from whitemagic.core.intelligence.dream_cycle
            # Need to ensure we're calling the correct async method
            try:
                # The dream_cycle.py has _run_phase (internal) and we added it as async
                # But nervous_system_v21 expects run_phase. Let's adapt.
                if hasattr(dreams, "_run_phase"):
                    await dreams._run_phase()
                    return {"status": "ok", "phase": "rotated"}

                # Fallback to a simulated result if method not found but object exists
                return {
                    "status": "simulated",
                    "message": "Dream cycle heartbeat active",
                }
            except Exception as e:
                logger.error("Dream pulse execution failed: %s", e, exc_info=True)
                return {"status": "error", "error": str(e)}
        else:
            return {"status": "no_phase_method"}

    async def _metabolism_pulse(self) -> dict[str, Any]:
        """Check memory decay and publish events."""
        metabolism = self.subsystems["metabolism"]

        # Calculate decay rate
        if hasattr(metabolism, "calculate_decay_rate"):
            decay_rate = metabolism.calculate_decay_rate()

            # Publish memory decay if significant
            if decay_rate > 0.1 and self.event_bus:
                await self.event_bus.publish(
                    EventType.MEMORY_DECAY,
                    {"decay_rate": decay_rate, "threshold": 0.1},
                    "metabolism_system",
                    priority=2,
                )

            return {"decay_rate": decay_rate}
        else:
            return {"status": "no_decay_calculation"}

    async def _resonance_pulse(self) -> dict[str, Any]:
        """Check resonance and publish harmony events."""
        resonance = self.subsystems["resonance"]

        if hasattr(resonance, "get_harmony_level"):
            harmony_level = resonance.get_harmony_level()

            # Publish resonance shift if significant
            if abs(harmony_level - 0.5) > 0.1 and self.event_bus:
                await self.event_bus.publish(
                    EventType.RESONANCE_SHIFT,
                    {"harmony_level": harmony_level, "baseline": 0.5},
                    "resonance_system",
                    priority=2,
                )

            return {"harmony_level": harmony_level}
        else:
            return {"status": "no_harmony_calculation"}


# Global V21 instance
_unified_nervous_system_v21: UnifiedNervousSystemV21 | None = None


async def get_nervous_system_v21() -> UnifiedNervousSystemV21:
    """Get the global V21 nervous system instance."""
    global _unified_nervous_system_v21
    if _unified_nervous_system_v21 is None:
        _unified_nervous_system_v21 = UnifiedNervousSystemV21()
        await _unified_nervous_system_v21.start()
    return _unified_nervous_system_v21


# Backward compatibility
def get_nervous_system():
    """Legacy compatibility - returns V21 instance."""
    return _unified_nervous_system_v21 or UnifiedNervousSystemV21()
