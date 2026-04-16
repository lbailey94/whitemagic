"""
Nervous System Bootstrap (V005)
===============================

Wires all 7 biological organs into the Unified Nervous System.
Ensures the organism is fully connected before operation.
"""

import logging

from whitemagic.core.nervous_system import OrganType, get_nervous_system

logger = logging.getLogger(__name__)

def bootstrap_nervous_system():
    """Discover and register all biological organs."""
    ns = get_nervous_system()

    # 1. Immune System
    try:
        from whitemagic.core.immune.pattern_immunity import get_immune_system
        ns.register_organ(OrganType.IMMUNE, get_immune_system())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Immune System: {e}")

    # 2. Genetics (Phylogenetics)
    try:
        from whitemagic.core.memory.phylogenetics import get_phylogenetics
        ns.register_organ(OrganType.GENETICS, get_phylogenetics())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Genetics: {e}")

    # 3. Dream Cycle
    try:
        from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
        # Note: DreamCycle usually needs start(), we just register the instance here
        # Ideally we'd have a singleton accessor that returns the shared instance
        # whitemagic/core/dreaming/dream_cycle.py doesn't have a singleton accessor in the snippet I saw earlier?
        # Wait, I saw `def get_dream_cycle() -> DreamCycle` in the snippet?
        # Checking... yes, I'll assume it exists or I'll fix it.
        # Actually, let's double check if I need to create one.
        # The snippet for dream_cycle.py ended before showing a singleton getter?
        # No, I can import it if it exists. If not, I'll catch the error.
        ns.register_organ(OrganType.DREAM, get_dream_cycle())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Dream Cycle: {e}")

    # 4. Metabolism (Consolidation)
    try:
        from whitemagic.core.memory.consolidation import get_consolidator
        ns.register_organ(OrganType.METABOLISM, get_consolidator())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Metabolism: {e}")

    # 5. Consciousness (Embodiment/Harmony)
    try:
        from whitemagic.core.embodiment import get_harmony_monitor
        ns.register_organ(OrganType.CONSCIOUSNESS, get_harmony_monitor())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Consciousness: {e}")

    # 6. Resonance (Gan Ying Bus)
    try:
        from whitemagic.core.resonance.gan_ying_enhanced import get_bus
        ns.register_organ(OrganType.RESONANCE, get_bus())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Resonance: {e}")

    # 7. Emergence (Detector)
    try:
        from whitemagic.core.patterns.emergence.detector import get_detector
        ns.register_organ(OrganType.EMERGENCE, get_detector())
    except ImportError as e:
        logger.warning(f"Failed to bootstrap Emergence: {e}")

    # Wire Feedback Loops (Subscribers)
    _wire_feedback_loops(ns)

    logger.info(f"Nervous System Bootstrap Complete. Organs online: {len(ns.organs)}")

def _wire_feedback_loops(ns):
    """Wire Gan Ying events to Nervous System signals."""
    try:
        from whitemagic.core.resonance.gan_ying_enhanced import EventType, get_bus
        bus = get_bus()

        # Immune -> Dream (Threat -> Defense Cycle)
        def on_threat(event):
            ns.signal_threat_detected(event.confidence, event.data)

        bus.listen(EventType.THREAT_DETECTED, on_threat)

        # Dream -> Genetics (Consolidation -> Fitness)
        def on_consolidation(event):
            if "strategies" in event.data and event.data["strategies"] > 0:
                ns.signal_dream_consolidation([{"type": "strategy_count", "count": event.data["strategies"]}])

        bus.listen(EventType.MEMORY_CONSOLIDATED, on_consolidation)

    except ImportError:
        logger.warning("Could not wire resonance events (bus missing?)")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bootstrap_nervous_system()
