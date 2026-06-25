"""Tests for Gan Ying cascade system and garden activation.

Covers Phases 1-5 of the Gan Ying Cascade Activation strategy:
- Phase 1: Cascade trigger wiring in GanYingBus.emit() + listen_all()
- Phase 2: Garden activation levels (boost, dampen, decay)
- Phase 3: Garden resonance partners (cross-garden cascading)
- Phase 4: Garden → dispatch pipeline integration
- Phase 5: Resonance metrics (entropy, cascade stats, quadrant balance)
"""

import time
import unittest

# ruff: noqa: BLE001
from whitemagic.core.resonance._consolidated import (
    CascadeTrigger,
    EventType,
    GanYingBus,
    ResonanceEvent,
)


class TestCascadeTriggers(unittest.TestCase):
    """Phase 1: Cascade trigger wiring in GanYingBus."""

    def setUp(self):
        """Create a fresh bus for each test to avoid singleton pollution."""
        self.bus = GanYingBus()

    def test_add_cascade(self):
        """Adding a cascade trigger registers it on the bus."""
        trigger = CascadeTrigger(
            trigger_event=EventType.JOY_TRIGGERED,
            target_events=[EventType.LOVE_ACTIVATED],
        )
        self.bus.add_cascade(trigger)
        self.assertEqual(len(self.bus._cascade_triggers), 1)

    def test_cascade_fires_on_matching_event(self):
        """When an event matches a cascade trigger, target events are emitted."""
        trigger = CascadeTrigger(
            trigger_event=EventType.JOY_TRIGGERED,
            target_events=[EventType.LOVE_ACTIVATED],
            amplification=1.2,
        )
        self.bus.add_cascade(trigger)
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.JOY_TRIGGERED,
            confidence=0.8,
        ))
        stats = self.bus.get_cascade_stats()
        self.assertEqual(stats["triggers_fired"], 1)
        self.assertEqual(stats["total_cascades"], 1)
        # History should contain both the original and cascaded event
        self.assertEqual(self.bus.total_emissions, 2)

    def test_cascade_does_not_fire_on_non_matching_event(self):
        """Non-matching events don't trigger cascades."""
        trigger = CascadeTrigger(
            trigger_event=EventType.JOY_TRIGGERED,
            target_events=[EventType.LOVE_ACTIVATED],
        )
        self.bus.add_cascade(trigger)
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.THREAT_DETECTED,
            confidence=0.8,
        ))
        stats = self.bus.get_cascade_stats()
        self.assertEqual(stats["triggers_fired"], 0)

    def test_cascade_depth_limit(self):
        """Cascade depth is limited to prevent infinite loops."""
        # Create a cycle: A → B → A
        self.bus.add_cascade(CascadeTrigger(
            trigger_event=EventType.JOY_TRIGGERED,
            target_events=[EventType.LOVE_ACTIVATED],
            max_cascade_depth=2,
        ))
        self.bus.add_cascade(CascadeTrigger(
            trigger_event=EventType.LOVE_ACTIVATED,
            target_events=[EventType.JOY_TRIGGERED],
            max_cascade_depth=2,
        ))
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.JOY_TRIGGERED,
            confidence=0.8,
        ))
        stats = self.bus.get_cascade_stats()
        # Should stop at depth 2, not infinite loop
        self.assertLessEqual(stats["max_depth_reached"], 2)
        # Should have a bounded number of events
        self.assertLess(self.bus.total_emissions, 20)

    def test_cascade_amplification(self):
        """Cascaded events have amplified confidence (capped at 1.0)."""
        trigger = CascadeTrigger(
            trigger_event=EventType.JOY_TRIGGERED,
            target_events=[EventType.LOVE_ACTIVATED],
            amplification=1.5,
        )
        self.bus.add_cascade(trigger)
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.JOY_TRIGGERED,
            confidence=0.8,
        ))
        history = self.bus.get_history(limit=10)
        # The cascaded event should have confidence = min(1.0, 0.8 * 1.5) = 1.0
        cascaded = [e for e in history if e.event_type == EventType.LOVE_ACTIVATED]
        self.assertEqual(len(cascaded), 1)
        self.assertAlmostEqual(cascaded[0].confidence, 1.0, places=2)

    def test_listen_all(self):
        """listen_all() registers a catch-all listener that receives all events."""
        received = []
        self.bus.listen_all(lambda e: received.append(e))
        self.bus.emit(ResonanceEvent(source="t1", event_type=EventType.JOY_TRIGGERED))
        self.bus.emit(ResonanceEvent(source="t2", event_type=EventType.THREAT_DETECTED))
        self.assertEqual(len(received), 2)

    def test_get_history(self):
        """get_history returns the most recent N events."""
        for i in range(5):
            self.bus.emit(ResonanceEvent(source=f"src{i}", event_type=EventType.JOY_TRIGGERED))
        history = self.bus.get_history(limit=3)
        self.assertEqual(len(history), 3)
        # Should be the last 3
        self.assertEqual(history[-1].source, "src4")

    def test_set_dampening(self):
        """Dampening suppresses low-confidence events."""
        self.bus.set_dampening(EventType.JOY_TRIGGERED, 0.5)
        # Low confidence event should be suppressed
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.JOY_TRIGGERED,
            confidence=0.3,
        ))
        self.assertEqual(self.bus.total_emissions, 0)
        # High confidence event should pass
        self.bus.emit(ResonanceEvent(
            source="test",
            event_type=EventType.JOY_TRIGGERED,
            confidence=0.8,
        ))
        self.assertEqual(self.bus.total_emissions, 1)


class TestGardenActivation(unittest.TestCase):
    """Phase 2: Garden activation levels."""

    def test_initial_activation_is_zero(self):
        """New gardens start at activation 0.0."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        self.assertAlmostEqual(g.get_activation_level(), 0.0, places=2)

    def test_boost_increases_activation(self):
        """Boosting a garden increases its activation level."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        level = g.boost(0.5)
        self.assertGreater(level, 0.0)
        self.assertLessEqual(level, 1.0)

    def test_boost_capped_at_1(self):
        """Activation cannot exceed 1.0."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.8)
        level = g.boost(0.8)
        self.assertLessEqual(level, 1.0)

    def test_dampen_decreases_activation(self):
        """Dampening reduces activation level."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.5)
        level = g.dampen(0.3)
        self.assertLess(level, 0.5)

    def test_dampen_floored_at_0(self):
        """Activation cannot go below 0.0."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.1)
        level = g.dampen(0.5)
        self.assertGreaterEqual(level, 0.0)

    def test_activation_decay_over_time(self):
        """Activation decays exponentially with a 5-minute half-life."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.8)
        # Simulate time passing by manipulating _last_active_time
        with g._activation_lock:
            g._last_active_time = time.time() - 300  # 5 minutes ago
        level = g.get_activation_level()
        # After one half-life, should be roughly halved
        self.assertLess(level, 0.5)
        self.assertGreater(level, 0.1)

    def test_activation_status_includes_level(self):
        """Garden status includes activation_level field."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.4)
        status = g.get_status()
        self.assertIn("activation_level", status)
        self.assertGreater(status["activation_level"], 0.0)


class TestGardenResonancePartners(unittest.TestCase):
    """Phase 3: Garden resonance partners — boost/dampen via cascades."""

    def test_boost_cascades_to_partners(self):
        """Boosting a garden boosts its resonance partners (at reduced strength)."""
        from whitemagic.gardens import get_garden
        from whitemagic.gardens.courage import CourageGarden
        # Courage's resonance_partners include "truth"
        g = CourageGarden()
        truth = get_garden("truth")
        if truth is None:
            self.skipTest("Truth garden not available")
        truth_before = truth.get_activation_level()
        g.boost(0.5)
        truth_after = truth.get_activation_level()
        self.assertGreater(truth_after, truth_before)

    def test_no_infinite_recursion_on_circular_partners(self):
        """Circular partner references (courage→truth→courage) don't cause infinite recursion."""
        from whitemagic.gardens import get_garden
        from whitemagic.gardens.courage import CourageGarden
        # courage → truth → courage (circular)
        # This should complete without hanging
        g = CourageGarden()
        level = g.boost(0.5)
        self.assertGreater(level, 0.0)
        # Truth should also be boosted (first level cascade)
        truth = get_garden("truth")
        if truth:
            self.assertGreater(truth.get_activation_level(), 0.0)

    def test_cascading_flag_resets(self):
        """The _cascading flag is properly reset after cascade completes."""
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        g.boost(0.3)
        self.assertFalse(g._cascading)
        # Should be able to boost again
        g.boost(0.3)
        self.assertFalse(g._cascading)


class TestDispatchPipelineGardenBoost(unittest.TestCase):
    """Phase 4: Garden → dispatch pipeline integration."""

    def test_get_garden_for_tool(self):
        """get_garden_for_tool returns a garden name for known tools."""
        from whitemagic.core.engines.registry import get_garden_for_tool
        garden = get_garden_for_tool("capabilities")
        self.assertIsNotNone(garden)

    def test_get_garden_for_gana(self):
        """get_garden_for_gana maps Gana names to gardens."""
        from whitemagic.core.engines.registry import get_garden_for_gana
        garden = get_garden_for_gana("gana_horn")
        self.assertEqual(garden, "courage")

    def test_gana_to_garden_mapping_count(self):
        """All 28 Ganas are mapped to gardens."""
        from whitemagic.core.engines.registry import _GANA_TO_GARDEN
        self.assertEqual(len(_GANA_TO_GARDEN), 28)

    def test_dispatch_boosts_garden(self):
        """Dispatching a tool boosts the associated garden's activation."""
        from whitemagic.core.engines.registry import get_garden_for_tool
        from whitemagic.gardens import get_garden
        from whitemagic.tools.dispatch_table import dispatch

        garden_name = get_garden_for_tool("capabilities")
        if not garden_name:
            self.skipTest("No garden mapping for capabilities")

        garden = get_garden(garden_name)
        if not garden:
            self.skipTest(f"Garden {garden_name} not available")

        # Reset activation to zero for a clean measurement
        with garden._activation_lock:
            garden._activation_level = 0.0
            garden._last_active_time = time.time()
        before = garden.get_activation_level()
        dispatch("capabilities")
        after = garden.get_activation_level()
        self.assertGreater(after, before)


class TestResonanceStats(unittest.TestCase):
    """Phase 5: Resonance metrics."""

    def test_resonance_stats_handler(self):
        """handle_resonance_stats returns valid metrics."""
        from whitemagic.tools.handlers.ganying import handle_resonance_stats
        result = handle_resonance_stats()
        self.assertEqual(result["status"], "success")
        self.assertIn("entropy", result)
        self.assertIn("balance_ratio", result)
        self.assertIn("cascade_stats", result)
        self.assertIn("quadrant_activation", result)
        self.assertIn("activations", result)

    def test_resonance_stats_entropy_range(self):
        """Entropy is between 0 and log2(n_gardens)."""
        import math

        from whitemagic.tools.handlers.ganying import handle_resonance_stats
        result = handle_resonance_stats()
        if result["status"] != "success":
            self.skipTest("Stats handler failed")
        entropy = result["entropy"]
        n = result["garden_count"]
        if n > 1:
            self.assertGreaterEqual(entropy, 0.0)
            self.assertLessEqual(entropy, math.log2(n) + 0.1)

    def test_resonance_stats_quadrant_keys(self):
        """Quadrant activation has the four Wu Xing keys."""
        from whitemagic.tools.handlers.ganying import handle_resonance_stats
        result = handle_resonance_stats()
        if result["status"] != "success":
            self.skipTest("Stats handler failed")
        qa = result["quadrant_activation"]
        self.assertIn("east_wood", qa)
        self.assertIn("south_fire", qa)
        self.assertIn("west_metal", qa)
        self.assertIn("north_water", qa)


class TestCycleDetection(unittest.TestCase):
    """Cycle detection in cascade trigger tables."""

    def setUp(self):
        self.GanYingBus = GanYingBus
        self.EventType = EventType
        self.CascadeTrigger = CascadeTrigger

    def test_safe_table_no_cycles(self):
        """A DAG trigger table should report no cycles."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.CONNECTION_DEEPENED]))
        self.assertTrue(bus._check_cascade_safety())
        self.assertEqual(bus.detect_cycles(), [])

    def test_cyclic_table_detected(self):
        """A cyclic trigger table should be detected."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.JOY_TRIGGERED]))
        self.assertFalse(bus._check_cascade_safety())
        cycles = bus.detect_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertIn("joy_triggered", cycles[0])
        self.assertIn("love_activated", cycles[0])

    def test_cyclic_table_blocks_cascades(self):
        """Cyclic tables should prevent cascade processing."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.JOY_TRIGGERED]))
        bus.emit(ResonanceEvent(
            source="test", event_type=ET.JOY_TRIGGERED, confidence=0.8))
        # Only the original event — no cascades should fire
        self.assertEqual(bus.total_emissions, 1)

    def test_cycle_check_cached(self):
        """Cycle check result should be cached after first call."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        # First call computes and caches
        result1 = bus._check_cascade_safety()
        self.assertIsNotNone(bus._cycle_check_cache)
        # Second call uses cache
        result2 = bus._check_cascade_safety()
        self.assertEqual(result1, result2)
        # Adding a trigger invalidates cache
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.CONNECTION_DEEPENED]))
        self.assertIsNone(bus._cycle_check_cache)
        bus._check_cascade_safety()

    def test_self_loop_detected(self):
        """A trigger that targets itself should be detected as a cycle."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.JOY_TRIGGERED]))
        self.assertFalse(bus._check_cascade_safety())


class TestPyO3Acceleration(unittest.TestCase):
    """PyO3 native cascade acceleration tests."""

    def setUp(self):
        from whitemagic.core.resonance._consolidated import GanYingBus, EventType, CascadeTrigger
        self.GanYingBus = GanYingBus
        self.EventType = EventType
        self.CascadeTrigger = CascadeTrigger

    def test_pyo3_backend_used_when_available(self):
        """PyO3 backend should be used for cascade matching with 1000+ triggers."""
        try:
            import wm_cascade  # noqa: F401
        except ImportError:
            self.skipTest("wm_cascade PyO3 module not installed")
        bus = self.GanYingBus()
        ET = self.EventType
        # Add 1000+ triggers using a star pattern (all point to one target)
        # This guarantees no cycles in the trigger graph
        all_events = list(ET)
        target = all_events[-1]
        for i in range(1010):
            src = all_events[i % (len(all_events) - 1)]  # exclude target itself
            bus.add_cascade(self.CascadeTrigger(
                trigger_event=src,
                target_events=[target],
                amplification=1.0,
                max_cascade_depth=1))
        bus.emit(ResonanceEvent(
            source="test", event_type=all_events[0], confidence=0.8))
        # Backend should be the wm_cascade module (not False)
        self.assertIsNot(bus._cascade_backend, False)
        self.assertIsNotNone(bus._cascade_backend)

    def test_pyo3_fallback_on_failure(self):
        """If PyO3 fails, should fall back to pure Python."""
        bus = self.GanYingBus()
        # Force backend to False to simulate unavailable PyO3
        bus._cascade_backend = False
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED,
            target_events=[ET.LOVE_ACTIVATED],
            amplification=1.0))
        bus.emit(ResonanceEvent(
            source="test", event_type=ET.JOY_TRIGGERED, confidence=0.8))
        # Should still cascade via pure Python
        self.assertEqual(bus.total_emissions, 2)

    def test_pyo3_cascaded_events_correct(self):
        """PyO3 backend should produce correct cascaded events with 1000+ triggers."""
        try:
            import wm_cascade  # noqa: F401
        except ImportError:
            self.skipTest("wm_cascade PyO3 module not installed")
        bus = self.GanYingBus()
        ET = self.EventType
        all_events = list(ET)
        # Add the trigger we want to test first (BEAUTY_DETECTED → JOY + PLAY)
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.BEAUTY_DETECTED,
            target_events=[ET.JOY_TRIGGERED, ET.PLAY_INITIATED],
            amplification=1.3))
        # Add 1000+ more triggers using star pattern to avoid cycles
        target = all_events[-1]
        for i in range(1005):
            src = all_events[i % (len(all_events) - 1)]
            if src == ET.BEAUTY_DETECTED:
                continue  # don't duplicate
            bus.add_cascade(self.CascadeTrigger(
                trigger_event=src,
                target_events=[target],
                amplification=1.0,
                max_cascade_depth=1))
        bus.emit(ResonanceEvent(
            source="test", event_type=ET.BEAUTY_DETECTED, confidence=0.5))
        # Should have cascaded at least 2 events from BEAUTY_DETECTED
        self.assertGreaterEqual(bus.total_emissions, 3)
        stats = bus.get_cascade_stats()
        self.assertGreaterEqual(stats["total_cascades"], 2)
        # Check confidence amplification (0.5 * 1.3 = 0.65)
        history = bus.get_history(limit=20)
        cascaded = [e for e in history if e.event_type in (ET.JOY_TRIGGERED, ET.PLAY_INITIATED)]
        for e in cascaded:
            self.assertAlmostEqual(e.confidence, 0.65, places=2)


class TestPolyglotBridges(unittest.TestCase):
    """Tests for Haskell and Koka polyglot bridge integration."""

    def setUp(self):
        from whitemagic.core.resonance._consolidated import GanYingBus, EventType, CascadeTrigger
        self.GanYingBus = GanYingBus
        self.EventType = EventType
        self.CascadeTrigger = CascadeTrigger

    def test_haskell_graceful_degradation(self):
        """Haskell backend should gracefully degrade when unavailable."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED,
            target_events=[ET.LOVE_ACTIVATED]))
        # Cycle check should still work (via PyO3 or Python DFS)
        self.assertTrue(bus._check_cascade_safety())
        # Haskell backend should be False or a working backend
        self.assertIn(bus._haskell_backend, (None, False))

    def test_koka_graceful_degradation(self):
        """Koka backend should gracefully degrade when unavailable."""
        bus = self.GanYingBus()
        ET = self.EventType
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED,
            target_events=[ET.LOVE_ACTIVATED]))
        bus.emit(ResonanceEvent(
            source="test", event_type=ET.JOY_TRIGGERED, confidence=0.8))
        # Should still cascade even if Koka is unavailable
        self.assertEqual(bus.total_emissions, 2)
        # Koka backend should be False or a working backend
        self.assertIn(bus._koka_backend, (None, False))

    def test_class_level_availability_cache(self):
        """Class-level availability cache should prevent re-discovery."""
        bus = self.GanYingBus()
        # Koka is always attempted (post-cascade), so cache should be set
        self.assertIsNotNone(GanYingBus._koka_available)
        # Haskell may be None if PyO3 handled cycle detection first
        # (Haskell is only attempted when PyO3 is unavailable)

    def test_cascade_safety_tiered_fallback(self):
        """Cycle safety should work with tiered fallback (PyO3 → Haskell → Python)."""
        bus = self.GanYingBus()
        ET = self.EventType
        # Create a safe DAG
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        bus.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.CONNECTION_DEEPENED]))
        self.assertTrue(bus._check_cascade_safety())

        # Create a cycle
        bus2 = self.GanYingBus()
        bus2.add_cascade(self.CascadeTrigger(
            trigger_event=ET.JOY_TRIGGERED, target_events=[ET.LOVE_ACTIVATED]))
        bus2.add_cascade(self.CascadeTrigger(
            trigger_event=ET.LOVE_ACTIVATED, target_events=[ET.JOY_TRIGGERED]))
        self.assertFalse(bus2._check_cascade_safety())

    def test_koka_garden_resonance_returns_none_when_unavailable(self):
        """_try_koka_garden_resonance should return None when Koka unavailable."""
        bus = self.GanYingBus()
        bus._koka_backend = False  # Force unavailable
        result = bus._try_koka_garden_resonance(
            ResonanceEvent(source="test", event_type=self.EventType.JOY_TRIGGERED, confidence=0.8))
        self.assertIsNone(result)

    def test_haskell_cycle_check_returns_false_when_unavailable(self):
        """_try_haskell_cycle_check should return False when Haskell unavailable."""
        bus = self.GanYingBus()
        bus._haskell_backend = False  # Force unavailable
        result = bus._try_haskell_cycle_check()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
