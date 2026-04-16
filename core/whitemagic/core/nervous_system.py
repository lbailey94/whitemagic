"""
Unified Nervous System (V005)
=============================

Central nervous bus that wires WhiteMagic's biological subsystems into a unified organism.
Connects Immune, Genetics, Dream, Metabolism, Consciousness, Resonance, and Emergence.
"""

import logging
import threading
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class OrganType(Enum):
    IMMUNE = "immune"
    GENETICS = "genetics"
    DREAM = "dream"
    METABOLISM = "metabolism"
    CONSCIOUSNESS = "consciousness"
    RESONANCE = "resonance"
    EMERGENCE = "emergence"

class NervousSystem:
    """
    Central event bus and coordinator for biological subsystems.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.organs: dict[str, Any] = {}
        self.signals: dict[str, list[Callable]] = {}
        self._initialized = True
        logger.info("Nervous System initialized")

    def register_organ(self, organ_type: OrganType, organ_instance: Any):
        """Register a biological subsystem."""
        self.organs[organ_type.value] = organ_instance
        logger.info(f"Organ registered: {organ_type.value}")

    def get_organ(self, organ_type: OrganType) -> Any | None:
        """Retrieve a registered organ."""
        return self.organs.get(organ_type.value)

    def subscribe(self, signal_type: str, callback: Callable):
        """Subscribe to a nervous signal."""
        if signal_type not in self.signals:
            self.signals[signal_type] = []
        self.signals[signal_type].append(callback)

    def dispatch_signal(self, signal_type: str, data: dict[str, Any]):
        """Dispatch a signal to all subscribers."""
        if signal_type in self.signals:
            for callback in self.signals[signal_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in signal handler for {signal_type}: {e}")

    def health_dashboard(self) -> dict[str, str]:
        """Return status of all registered organs."""
        status = {}
        for name, organ in self.organs.items():
            try:
                # Try standard status methods if they exist
                if hasattr(organ, "status"):
                    s = organ.status()
                    status[name] = "OK" if s else "UNKNOWN"
                elif hasattr(organ, "is_healthy"):
                    status[name] = "OK" if organ.is_healthy() else "UNHEALTHY"
                else:
                    status[name] = "REGISTERED"
            except Exception:
                status[name] = "ERROR"
        return status

    # --- Specific Feedback Loops (V005) ---

    def signal_threat_detected(self, threat_level: float, details: dict[str, Any]):
        """Immune -> Dream: Threat triggers defensive dream cycle."""
        self.dispatch_signal("threat_detected", {"level": threat_level, "details": details})

        # Direct wiring if dream organ exists
        dream = self.get_organ(OrganType.DREAM)
        if dream and hasattr(dream, "trigger_defense_cycle"):
            dream.trigger_defense_cycle(threat_level)

    def signal_homeostasis_update(self, equilibrium_score: float):
        """Homeostasis -> Phylogenetics: Equilibrium modulates mutation rate."""
        self.dispatch_signal("homeostasis_update", {"score": equilibrium_score})

        genetics = self.get_organ(OrganType.GENETICS)
        if genetics and hasattr(genetics, "set_mutation_rate"):
            # Lower equilibrium = higher mutation (adapt faster)
            rate = max(0.01, 1.0 - equilibrium_score)
            genetics.set_mutation_rate(rate)

    def signal_dream_consolidation(self, insights: list[dict[str, Any]]):
        """Dream -> Genetics: Consolidation feeds fitness scores."""
        self.dispatch_signal("dream_consolidated", {"insights": insights})

        genetics = self.get_organ(OrganType.GENETICS)
        if genetics and hasattr(genetics, "update_fitness"):
            genetics.update_fitness(insights)

def get_nervous_system() -> NervousSystem:
    """Singleton accessor."""
    return NervousSystem()
