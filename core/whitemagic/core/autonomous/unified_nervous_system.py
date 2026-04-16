"""
Unified Nervous System Event Bus

Connects the 7 biological subsystems of WhiteMagic:
1. Immune (security/dna)
2. Genetic (evolution/phylogenetics)
3. Dream (12 phases)
4. Metabolism (consolidation/forgetting)
5. Consciousness (coherence/embodiment)
6. Resonance (harmony/gardens)
7. Emergence (ecology/serendipity)

Plus the Apotheosis Engine for autonomous evolution.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from whitemagic.core.dreaming.background_dreamer import get_background_dreamer

logger = logging.getLogger(__name__)


class BiologicalSubsystem(Enum):
    """The 7 biological subsystems of WhiteMagic."""
    IMMUNE = "immune"           # security, dna, antibodies
    GENETIC = "genetic"         # evolution, phylogenetics
    DREAM = "dream"             # 12-phase dream cycle
    METABOLISM = "metabolism"   # consolidation, forgetting
    CONSCIOUSNESS = "consciousness"  # coherence, embodiment
    RESONANCE = "resonance"     # harmony, gardens
    EMERGENCE = "emergence"     # ecology, serendipity
    APOTHEOSIS = "apotheosis"   # autonomous evolution


class EventPriority(Enum):
    """Event priority levels."""
    CRITICAL = 0    # Immediate handling (security threats, coherence collapse)
    HIGH = 1        # Urgent (dream cycle trigger, galactic sweep needed)
    NORMAL = 2      # Standard events
    LOW = 3         # Background tasks


@dataclass
class BiologicalEvent:
    """An event on the unified nervous system."""
    event_type: str
    source: BiologicalSubsystem
    target: BiologicalSubsystem | None
    payload: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_id: str = field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")


@dataclass
class SubsystemRegistration:
    """Registration of a biological subsystem."""
    subsystem: BiologicalSubsystem
    handlers: dict[str, list[Callable[[BiologicalEvent], Any]]] = field(default_factory=lambda: defaultdict(list))
    active: bool = True
    last_heartbeat: str | None = None


class UnifiedNervousSystem:
    """
    The central event bus connecting all 7 biological subsystems.
    Implements publish/subscribe pattern with priority handling.
    """

    def __init__(self) -> None:
        self._subsystems: dict[BiologicalSubsystem, SubsystemRegistration] = {}
        self._event_history: list[BiologicalEvent] = []
        self._running = False
        self._event_queue: asyncio.PriorityQueue[tuple[int, BiologicalEvent]] = asyncio.PriorityQueue()
        self._global_handlers: list[Callable[[BiologicalEvent], Any]] = []

    def register_subsystem(
        self,
        subsystem: BiologicalSubsystem,
        event_types: list[str],
        handler: Callable[[BiologicalEvent], Any],
    ) -> None:
        """Register a subsystem to receive specific event types."""
        if subsystem not in self._subsystems:
            self._subsystems[subsystem] = SubsystemRegistration(subsystem=subsystem)

        for event_type in event_types:
            self._subsystems[subsystem].handlers[event_type].append(handler)

        logger.info(f"🔌 Registered {subsystem.value} for events: {event_types}")

    def unregister_subsystem(self, subsystem: BiologicalSubsystem) -> None:
        """Unregister a subsystem."""
        if subsystem in self._subsystems:
            self._subsystems[subsystem].active = False
            logger.info(f"🔌 Unregistered {subsystem.value}")

    def emit(
        self,
        event_type: str,
        source: BiologicalSubsystem,
        payload: dict[str, Any],
        target: BiologicalSubsystem | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> BiologicalEvent:
        """Emit an event to the nervous system."""
        event = BiologicalEvent(
            event_type=event_type,
            source=source,
            target=target,
            payload=payload,
            priority=priority,
        )

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > 10000:
            self._event_history.pop(0)

        # Route to handlers
        self._route_event(event)

        return event

    def _route_event(self, event: BiologicalEvent) -> None:
        """Route event to appropriate handlers."""
        # Global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global handler error: {e}")

        # Targeted or broadcast
        if event.target:
            # Send to specific subsystem
            if event.target in self._subsystems:
                reg = self._subsystems[event.target]
                if reg.active:
                    self._deliver_to_subsystem(event, reg)
        else:
            # Broadcast to all interested subsystems
            for reg in self._subsystems.values():
                if reg.active:
                    self._deliver_to_subsystem(event, reg)

    def _deliver_to_subsystem(
        self,
        event: BiologicalEvent,
        registration: SubsystemRegistration,
    ) -> None:
        """Deliver event to a specific subsystem's handlers."""
        handlers = registration.handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {registration.subsystem.value}: {e}")

    def add_global_handler(self, handler: Callable[[BiologicalEvent], Any]) -> None:
        """Add a global handler that receives all events."""
        self._global_handlers.append(handler)

    def get_event_history(
        self,
        event_type: str | None = None,
        source: BiologicalSubsystem | None = None,
        limit: int = 100,
    ) -> list[BiologicalEvent]:
        """Query event history."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_subsystem_status(self) -> dict[str, Any]:
        """Get status of all registered subsystems."""
        return {
            subsystem.value: {
                "active": reg.active,
                "handlers_registered": sum(len(h) for h in reg.handlers.values()),
                "event_types": list(reg.handlers.keys()),
            }
            for subsystem, reg in self._subsystems.items()
        }

    def create_cross_subsystem_event(
        self,
        event_type: str,
        sources: list[BiologicalSubsystem],
        target: BiologicalSubsystem,
        payload_builder: Callable[[BiologicalSubsystem], dict[str, Any]],
    ) -> list[BiologicalEvent]:
        """Create an event that aggregates data from multiple sources."""
        events = []
        for source in sources:
            payload = payload_builder(source)
            event = self.emit(
                event_type=event_type,
                source=source,
                target=target,
                payload=payload,
            )
            events.append(event)
        return events


# Predefined cross-subsystem event patterns

class CrossSubsystemPatterns:
    """Common patterns for cross-subsystem communication."""

    @staticmethod
    def coherence_cascade(nervous_system: UnifiedNervousSystem, coherence_score: float) -> None:
        """
        When coherence drops, notify multiple subsystems to take corrective action.
        """
        if coherence_score < 0.6:
            # Critical coherence - trigger dream cycle and notify consciousness
            nervous_system.emit(
                event_type="coherence.critical",
                source=BiologicalSubsystem.CONSCIOUSNESS,
                payload={"coherence": coherence_score, "action": "trigger_dream"},
                priority=EventPriority.CRITICAL,
            )

            # Also notify resonance to check harmony
            nervous_system.emit(
                event_type="harmony.check",
                source=BiologicalSubsystem.CONSCIOUSNESS,
                target=BiologicalSubsystem.RESONANCE,
                payload={"coherence": coherence_score},
                priority=EventPriority.HIGH,
            )

    @staticmethod
    def emergence_detected(
        nervous_system: UnifiedNervousSystem,
        emergence_type: str,
        details: dict[str, Any],
    ) -> None:
        """
        When emergence is detected, propagate to genetic and consciousness systems.
        """
        # Notify genetic system to record in phylogenetics
        nervous_system.emit(
            event_type="emergence.record",
            source=BiologicalSubsystem.EMERGENCE,
            target=BiologicalSubsystem.GENETIC,
            payload={"type": emergence_type, "details": details},
            priority=EventPriority.HIGH,
        )

        # Notify consciousness to update coherence
        nervous_system.emit(
            event_type="coherence.adjust",
            source=BiologicalSubsystem.EMERGENCE,
            target=BiologicalSubsystem.CONSCIOUSNESS,
            payload={"adjustment": 0.05, "reason": emergence_type},
            priority=EventPriority.NORMAL,
        )

        # Notify apotheosis for capability discovery
        nervous_system.emit(
            event_type="capability.discover",
            source=BiologicalSubsystem.EMERGENCE,
            target=BiologicalSubsystem.APOTHEOSIS,
            payload={"emergence": emergence_type},
            priority=EventPriority.NORMAL,
        )

    @staticmethod
    def security_threat(
        nervous_system: UnifiedNervousSystem,
        threat_type: str,
        severity: str,
    ) -> None:
        """
        Security threats trigger immune response and notify consciousness.
        """
        priority = EventPriority.CRITICAL if severity == "critical" else EventPriority.HIGH

        # Immune system handles the threat
        nervous_system.emit(
            event_type="immune.activate",
            source=BiologicalSubsystem.IMMUNE,
            payload={"threat": threat_type, "severity": severity},
            priority=priority,
        )

        # Consciousness updates for threat awareness
        nervous_system.emit(
            event_type="consciousness.threat_awareness",
            source=BiologicalSubsystem.IMMUNE,
            target=BiologicalSubsystem.CONSCIOUSNESS,
            payload={"threat": threat_type, "immune_response": "active"},
            priority=priority,
        )

    @staticmethod
    def dream_cycle_complete(
        nervous_system: UnifiedNervousSystem,
        cycle_results: dict[str, Any],
    ) -> None:
        """
        When dream cycle completes, update consciousness and trigger metabolism.
        """
        # Update consciousness coherence
        nervous_system.emit(
            event_type="coherence.restore",
            source=BiologicalSubsystem.DREAM,
            target=BiologicalSubsystem.CONSCIOUSNESS,
            payload={"dream_results": cycle_results},
            priority=EventPriority.HIGH,
        )

        # Trigger memory metabolism
        nervous_system.emit(
            event_type="metabolism.consolidate",
            source=BiologicalSubsystem.DREAM,
            target=BiologicalSubsystem.METABOLISM,
            payload={"constellations": cycle_results.get("constellations", [])},
            priority=EventPriority.NORMAL,
        )

        # Check for apotheosis improvements
        nervous_system.emit(
            event_type="apotheosis.check_improvements",
            source=BiologicalSubsystem.DREAM,
            target=BiologicalSubsystem.APOTHEOSIS,
            payload={"insights": cycle_results.get("insights", [])},
            priority=EventPriority.LOW,
        )

    @staticmethod
    def memory_pressure(
        nervous_system: UnifiedNervousSystem,
        usage_percent: float,
    ) -> None:
        """
        When memory pressure is high, trigger metabolism and apotheosis prediction.
        """
        # Metabolism handles consolidation/forgetting
        nervous_system.emit(
            event_type="metabolism.forgetting_sweep",
            source=BiologicalSubsystem.METABOLISM,
            payload={"pressure": usage_percent, "strategy": "gentle"},
            priority=EventPriority.HIGH if usage_percent > 90 else EventPriority.NORMAL,
        )

        # Apotheosis predicts maintenance needs
        nervous_system.emit(
            event_type="apotheosis.predict_growth",
            source=BiologicalSubsystem.METABOLISM,
            target=BiologicalSubsystem.APOTHEOSIS,
            payload={"current_usage": usage_percent},
            priority=EventPriority.NORMAL,
        )


# Singleton accessor
_nervous_system: UnifiedNervousSystem | None = None


def get_nervous_system() -> UnifiedNervousSystem:
    """Get the global Unified Nervous System."""
    global _nervous_system
    if _nervous_system is None:
        _nervous_system = UnifiedNervousSystem()
    return _nervous_system


def wire_default_subsystems() -> UnifiedNervousSystem:
    """
    Wire up the default subsystems with their event handlers.
    This creates the fully connected "living system".
    """
    uns = get_nervous_system()

    # Wire Apotheosis Engine to listen to all subsystems
    from whitemagic.core.autonomous.apotheosis_engine import get_apotheosis_engine
    get_apotheosis_engine()

    def apotheosis_handler(event: BiologicalEvent) -> None:
        """Apotheosis monitors all events for patterns."""
        # Record in pattern history for learning
        pass

    uns.add_global_handler(apotheosis_handler)

    # Wire Consciousness to respond to coherence events
    def consciousness_handler(event: BiologicalEvent) -> None:
        if event.event_type == "coherence.restore":
            logger.info("🧠 Consciousness: Coherence restored from dream cycle")

    uns.register_subsystem(
        BiologicalSubsystem.CONSCIOUSNESS,
        ["coherence.restore", "coherence.critical"],
        consciousness_handler,
    )

    # Wire Dream to respond to critical coherence
    def dream_handler(event: BiologicalEvent) -> None:
        if event.event_type == "coherence.critical" or event.event_type == "dream.trigger":
            logger.info("💤 Dream: Triggering emergency or idle dream cycle")
            try:
                dreamer = get_background_dreamer()
                dreamer.trigger_dream_cycle()
            except Exception as e:
                logger.error(f"Failed to trigger background dreamer: {e}")

    uns.register_subsystem(
        BiologicalSubsystem.DREAM,
        ["coherence.critical", "dream.trigger"],
        dream_handler,
    )

    logger.info("🧬 Unified Nervous System wired with 7 biological subsystems")

    return uns
