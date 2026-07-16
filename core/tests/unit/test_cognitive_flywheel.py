"""Tests for Cognitive Action Flywheel Phases 3-5.

Covers:
- Phase 3.1: SignalWeightTracker
- Phase 3.2: Cross-session outcome analysis in get_status()
- Phase 3.3: Emergence insight deduplication
- Phase 3.4: Pattern applicability matching
- Phase 4.1: Citta ignition trigger
- Phase 4.2: Dream cycle emergence feedback
- Phase 4.3: Knowledge gap signal collection
- Phase 4.4: RIL auto-fixable execution
- Phase 5.1: Pareto optimization
- Phase 5.2: Speculative action execution
- Phase 5.3: Action outcome prediction
- Phase 5.4: Cross-agent action locks
- Phase 5.5: Consciousness-driven action selection
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up isolated test state root
os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SKIP_CONSCIOUSNESS_OBSERVE", "1")


# ---------------------------------------------------------------------------
# Phase 3.1: SignalWeightTracker
# ---------------------------------------------------------------------------

class TestSignalWeightTracker:
    """Test the SignalWeightTracker class."""

    def test_default_weight_is_1(self):
        from whitemagic.core.consciousness.cognitive_action_loop import SignalWeightTracker
        tracker = SignalWeightTracker()
        assert tracker.get_weight("unknown_source") == 1.0

    def test_apply_weights_scales_confidence(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        tracker._weights["guna"] = 0.5
        signal = ActionSignal(
            source="guna", signal_id="test", title="T", description="D",
            confidence=0.8, urgency=0.6, action="test",
        )
        result = tracker.apply_weights([signal])
        assert result[0].confidence == 0.4  # 0.8 * 0.5
        assert result[0].urgency == 0.3  # 0.6 * 0.5

    def test_apply_weights_clamps_to_01(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        tracker._weights["emergence"] = 2.0
        signal = ActionSignal(
            source="emergence", signal_id="test", title="T", description="D",
            confidence=0.8, urgency=0.6, action="test",
        )
        result = tracker.apply_weights([signal])
        assert result[0].confidence == 1.0  # clamped
        assert result[0].urgency == 1.0  # clamped

    def test_update_from_outcomes_positive_delta(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        # Feed 3 positive outcomes to trigger weight adjustment
        for _ in range(3):
            outcome = ActionOutcome(
                action_id="a1", signal_source="guna", action="trigger_dream_cycle",
                executed=True, delta={"memories": 5.0, "associations": 2.0},
            )
            tracker.update_from_outcomes([outcome])
        # After 3 positive outcomes, weight should be > 1.0
        weight = tracker.get_weight("guna")
        assert weight > 1.0

    def test_update_from_outcomes_negative_delta(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        for _ in range(3):
            outcome = ActionOutcome(
                action_id="a1", signal_source="coherence", action="trigger_coherence_measurement",
                executed=True, delta={"coherence": -2.0, "quality": -1.0},
            )
            tracker.update_from_outcomes([outcome])
        weight = tracker.get_weight("coherence")
        assert weight < 1.0

    def test_update_from_outcomes_no_delta(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        for _ in range(3):
            outcome = ActionOutcome(
                action_id="a1", signal_source="emergence", action="review_insight",
                executed=True, delta={},
            )
            tracker.update_from_outcomes([outcome])
        # No delta → no_delta counter increments, weight stays near 1.0
        weight = tracker.get_weight("emergence")
        assert 0.3 <= weight <= 1.1

    def test_get_stats_returns_per_source(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            SignalWeightTracker,
        )
        tracker = SignalWeightTracker()
        outcome = ActionOutcome(
            action_id="a1", signal_source="test_stats_source", action="test",
            executed=True, delta={"x": 1.0},
        )
        tracker.update_from_outcomes([outcome])
        stats = tracker.get_stats()
        assert "test_stats_source" in stats
        assert stats["test_stats_source"]["cycles"] >= 1
        assert stats["test_stats_source"]["positive"] >= 1


# ---------------------------------------------------------------------------
# Phase 3.2: Cross-session outcome analysis
# ---------------------------------------------------------------------------

class TestCrossSessionOutcomes:
    """Test get_status() includes cross-session outcome analysis."""

    def test_status_has_signal_weights(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        status = loop.get_status()
        assert "signal_weights" in status

    def test_status_has_cycle_count(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        status = loop.get_status()
        assert status["cycle_count"] == 0
        assert "total_actions_executed" in status
        assert "scheduler_running" in status


# ---------------------------------------------------------------------------
# Phase 3.3: Emergence insight deduplication
# ---------------------------------------------------------------------------

class TestEmergenceDedup:
    """Test emergence insight deduplication via content_hash."""

    def test_persist_insights_skips_duplicates(self):
        from whitemagic.core.intelligence.agentic.emergence_engine import EmergenceInsight
        from whitemagic.config.paths import galaxy_db_path
        from whitemagic.core.memory.db_manager import safe_connect

        # Create a fresh knowledge DB for testing
        db = galaxy_db_path("knowledge")
        db.parent.mkdir(parents=True, exist_ok=True)
        conn = safe_connect(str(db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergence_insights (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                confidence REAL,
                source TEXT,
                timestamp TEXT,
                metadata_json TEXT,
                persisted_at TEXT
            )
        """)
        conn.commit()
        conn.close()

        from whitemagic.core.intelligence.agentic.emergence_engine import EmergenceEngine
        engine = EmergenceEngine()

        insight1 = EmergenceInsight(
            id="test_dedup_1", title="Dedup Test", description="Same content",
            source="tag_cluster", confidence=0.8,
        )
        insight2 = EmergenceInsight(
            id="test_dedup_2", title="Dedup Test", description="Same content",
            source="tag_cluster", confidence=0.8,
        )

        engine._persist_insights([insight1])
        engine._persist_insights([insight2])  # Should be skipped

        conn = safe_connect(str(db), read_only=True)
        count = conn.execute(
            "SELECT COUNT(*) FROM emergence_insights WHERE title = 'Dedup Test'"
        ).fetchone()[0]
        conn.close()

        assert count == 1  # Second insert was skipped

        # Cleanup
        conn = safe_connect(str(db))
        conn.execute("DELETE FROM emergence_insights WHERE id LIKE 'test_dedup_%'")
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Phase 3.4: Pattern applicability matching
# ---------------------------------------------------------------------------

class TestPatternMatching:
    """Test _match_patterns_to_signals."""

    def test_match_attaches_applicable_patterns(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        # Create mock report with patterns
        mock_pattern = MagicMock()
        mock_pattern.title = "Fix coherence emotional_attunement dimension"
        mock_pattern.description = "Run coherence measurement to improve emotional_attunement"
        mock_pattern.confidence = 0.85

        mock_report = MagicMock()
        mock_report.solutions = [mock_pattern]
        mock_report.heuristics = []
        mock_report.optimizations = []

        signal = ActionSignal(
            source="coherence", signal_id="test", title="Low coherence emotional_attunement",
            description="emotional_attunement dimension below threshold",
            confidence=0.8, urgency=0.5, action="trigger_coherence_measurement",
        )

        loop._match_patterns_to_signals([signal], mock_report)
        assert "applicable_patterns" in signal.metadata
        assert len(signal.metadata["applicable_patterns"]) >= 1
        assert "emotional_attunement" in signal.metadata["applicable_patterns"][0]["matched_keywords"]

    def test_match_skips_pattern_signals(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        mock_report = MagicMock()
        mock_report.solutions = []
        mock_report.heuristics = []
        mock_report.optimizations = []

        pattern_signal = ActionSignal(
            source="pattern", signal_id="p1", title="A pattern",
            description="Some description", confidence=0.5, urgency=0.1, action="surface_pattern",
        )

        loop._match_patterns_to_signals([pattern_signal], mock_report)
        assert "applicable_patterns" not in pattern_signal.metadata

    def test_match_no_patterns_does_nothing(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        mock_report = MagicMock()
        mock_report.solutions = []
        mock_report.heuristics = []
        mock_report.optimizations = []

        signal = ActionSignal(
            source="guna", signal_id="g1", title="Test", description="Test",
            confidence=0.5, urgency=0.5, action="test",
        )

        loop._match_patterns_to_signals([signal], mock_report)
        assert "applicable_patterns" not in signal.metadata


# ---------------------------------------------------------------------------
# Phase 4.1: Citta ignition trigger
# ---------------------------------------------------------------------------

class TestCittaIgnitionTrigger:
    """Test citta cycle → action loop trigger on ignition clusters."""

    def test_check_ignition_trigger_exists(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        assert hasattr(CittaCycle, "_check_ignition_trigger")

    def test_ignition_check_initialized_to_zero(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        cycle = CittaCycle()
        assert cycle._last_ignition_check == 0

    def test_ignition_check_skips_under_20_advances(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        cycle = CittaCycle()
        cycle._current_position = 10
        cycle._last_ignition_check = 0
        # Should return early — not enough advances
        cycle._check_ignition_trigger()
        # _last_ignition_check should NOT update (still 0)
        assert cycle._last_ignition_check == 0

    def test_reset_clears_ignition_check(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        cycle = CittaCycle()
        cycle._last_ignition_check = 50
        cycle.reset()
        assert cycle._last_ignition_check == 0

    def test_ignition_trigger_calls_action_loop(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        cycle = CittaCycle()
        cycle._current_position = 25
        cycle._last_ignition_check = 0

        # Mock trajectory to return 5+ ignitions
        mock_traj = MagicMock()
        mock_traj.ignition_events.return_value = [{"pos": i} for i in range(6)]
        cycle._trajectory = mock_traj

        with patch("whitemagic.core.consciousness.cognitive_action_loop.get_action_loop") as mock:
            mock_loop = MagicMock()
            mock_loop._scheduler_running = False
            mock.return_value = mock_loop
            cycle._check_ignition_trigger()
            mock_loop.run_cycle.assert_called_once_with(max_actions=1)

    def test_ignition_trigger_skips_when_scheduler_running(self):
        from whitemagic.core.consciousness.citta_cycle import CittaCycle
        cycle = CittaCycle()
        cycle._current_position = 25
        cycle._last_ignition_check = 0

        mock_traj = MagicMock()
        mock_traj.ignition_events.return_value = [{"pos": i} for i in range(6)]
        cycle._trajectory = mock_traj

        with patch("whitemagic.core.consciousness.cognitive_action_loop.get_action_loop") as mock:
            mock_loop = MagicMock()
            mock_loop._scheduler_running = True  # Scheduler already running
            mock.return_value = mock_loop
            cycle._check_ignition_trigger()
            mock_loop.run_cycle.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 4.2: Dream cycle emergence feedback
# ---------------------------------------------------------------------------

class TestDreamEmergenceFeedback:
    """Test dream cycle → emergence feedback loop."""

    def test_trigger_cycle_has_pre_dream_count(self):
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        # Mock all phase handlers to do nothing
        dc._phases = []
        results = dc.trigger_cycle(reason="test")
        # pre_dream_emergence_count is always set (defaults to 0 if DB doesn't exist)
        assert "pre_dream_emergence_count" in results or "emergence_feedback" in results

    def test_trigger_cycle_has_emergence_feedback(self):
        from whitemagic.core.dreaming.dream_cycle import DreamCycle
        dc = DreamCycle()
        dc._phases = []
        results = dc.trigger_cycle(reason="test")
        assert "emergence_feedback" in results
        feedback = results["emergence_feedback"]
        assert "pre_dream_count" in feedback
        assert "post_dream_count" in feedback
        assert "new_insights" in feedback
        assert "effective" in feedback


# ---------------------------------------------------------------------------
# Phase 4.3: Knowledge gap signal collection
# ---------------------------------------------------------------------------

class TestKnowledgeGapSignals:
    """Test knowledge gap → action loop signal wiring."""

    def test_collect_signals_has_knowledge_gap_source(self):
        import inspect
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        source = inspect.getsource(CognitiveActionLoop._collect_signals)
        assert "knowledge_gap" in source
        assert "KnowledgeGapActionLoop" in source


# ---------------------------------------------------------------------------
# Phase 4.4: RIL auto-fixable execution
# ---------------------------------------------------------------------------

class TestRILAutoFixable:
    """Test recursive improvement → action loop execution."""

    def test_execute_auto_fixable_exists(self):
        from whitemagic.core.evolution.recursive_loop import RecursiveImprovementLoop
        assert hasattr(RecursiveImprovementLoop, "_execute_auto_fixable")

    def test_execute_auto_fixable_no_proposals(self):
        from whitemagic.core.evolution.recursive_loop import RecursiveImprovementLoop
        loop = RecursiveImprovementLoop()
        # Create a mock cycle with no auto-fixable proposals
        mock_cycle = MagicMock()
        mock_cycle.phase_results = {"observe": {"proposals": []}}
        # Should return without error
        loop._execute_auto_fixable(mock_cycle)

    def test_execute_auto_fixable_with_proposals(self):
        from whitemagic.core.evolution.recursive_loop import RecursiveImprovementLoop
        loop = RecursiveImprovementLoop()

        mock_cycle = MagicMock()
        mock_cycle.phase_results = {
            "observe": {
                "proposals": [
                    {
                        "id": "prop_1",
                        "description": "Fix guna imbalance",
                        "fix_action": "trigger_dream_cycle",
                        "auto_fixable": True,
                        "confidence": 0.8,
                        "category": "guna_imbalance",
                    },
                    {
                        "id": "prop_2",
                        "description": "Not auto-fixable",
                        "fix_action": None,
                        "auto_fixable": False,
                        "confidence": 0.5,
                        "category": "other",
                    },
                ]
            }
        }

        with patch("whitemagic.core.consciousness.cognitive_action_loop.get_action_loop") as mock:
            mock_loop = MagicMock()
            mock_outcome = MagicMock()
            mock_outcome.executed = True
            mock_outcome.delta = {"memories": 1.0}
            mock_loop._execute_and_measure.return_value = mock_outcome
            mock.return_value = mock_loop
            loop._execute_auto_fixable(mock_cycle)
            # Should only call for the auto_fixable proposal
            mock_loop._execute_and_measure.assert_called_once()
            call_args = mock_loop._execute_and_measure.call_args[0][0]
            assert call_args.action == "trigger_dream_cycle"
            assert call_args.source == "recursive_improvement"


# ---------------------------------------------------------------------------
# Phase 5.1: Pareto optimization
# ---------------------------------------------------------------------------

class TestParetoOptimization:
    """Test multi-objective Pareto optimization."""

    def test_pareto_prioritize_returns_sorted(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        s1 = ActionSignal(source="guna", signal_id="1", title="A", description="D",
                          confidence=0.9, urgency=0.9, action="trigger_dream_cycle")
        s2 = ActionSignal(source="emergence", signal_id="2", title="B", description="D",
                          confidence=0.3, urgency=0.1, action="review_insight")

        result = loop._pareto_prioritize([s2, s1])
        # s1 should rank higher (higher urgency + confidence)
        assert result[0] is s1
        assert result[1] is s2

    def test_pareto_novelty_boost(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        # Mark "review_insight" as already seen
        loop._action_history_seen.add("review_insight")

        s_seen = ActionSignal(source="emergence", signal_id="1", title="A", description="D",
                               confidence=0.7, urgency=0.5, action="review_insight")
        s_novel = ActionSignal(source="emergence", signal_id="2", title="B", description="D",
                               confidence=0.7, urgency=0.5, action="surface_pattern")

        result = loop._pareto_prioritize([s_seen, s_novel])
        # Novel action should rank higher due to novelty boost
        assert result[0] is s_novel

    def test_pareto_learning_value_boost(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        s_with_patterns = ActionSignal(
            source="coherence", signal_id="1", title="A", description="D",
            confidence=0.5, urgency=0.5, action="trigger_coherence_measurement",
            metadata={"applicable_patterns": [{"title": "X"}]},
        )
        s_without = ActionSignal(
            source="coherence", signal_id="2", title="B", description="D",
            confidence=0.5, urgency=0.5, action="trigger_coherence_measurement",
        )

        result = loop._pareto_prioritize([s_without, s_with_patterns])
        # Signal with applicable_patterns should rank higher (learning=0.9 vs 0.5)
        assert result[0] is s_with_patterns

    def test_pareto_empty_list(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        assert loop._pareto_prioritize([]) == []


# ---------------------------------------------------------------------------
# Phase 5.2: Speculative action execution
# ---------------------------------------------------------------------------

class TestSpeculativeExecution:
    """Test speculative action execution during idle time."""

    def test_start_stop_speculative(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        assert not loop._speculative_running
        loop.start_speculative()
        assert loop._speculative_running
        loop.stop_speculative()
        assert not loop._speculative_running

    def test_start_speculative_idempotent(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        loop.start_speculative()
        thread1 = loop._speculative_thread
        loop.start_speculative()  # Should not start a second thread
        assert loop._speculative_thread is thread1
        loop.stop_speculative()


# ---------------------------------------------------------------------------
# Phase 5.3: Action outcome prediction
# ---------------------------------------------------------------------------

class TestOutcomePrediction:
    """Test action outcome prediction model."""

    def test_predict_negative_impact_no_data(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        assert loop._predict_negative_impact("unknown_action") is False

    def test_predict_negative_impact_under_threshold(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        # Feed 5 negative outcomes
        for _ in range(5):
            outcome = ActionOutcome(
                action_id="a", signal_source="test", action="bad_action",
                executed=True, delta={"x": -1.0, "y": -2.0},
            )
            loop._update_predictor("bad_action", outcome)

        assert loop._predict_negative_impact("bad_action") is True

    def test_predict_negative_impact_above_threshold(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        # Feed 5 positive outcomes
        for _ in range(5):
            outcome = ActionOutcome(
                action_id="a", signal_source="test", action="good_action",
                executed=True, delta={"x": 1.0, "y": 2.0},
            )
            loop._update_predictor("good_action", outcome)

        assert loop._predict_negative_impact("good_action") is False

    def test_predict_negative_impact_needs_5_observations(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        # Only 4 negative outcomes — should not block yet
        for _ in range(4):
            outcome = ActionOutcome(
                action_id="a", signal_source="test", action="weak_bad",
                executed=True, delta={"x": -1.0},
            )
            loop._update_predictor("weak_bad", outcome)

        assert loop._predict_negative_impact("weak_bad") is False  # Needs 5+

    def test_update_predictor_no_delta(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionOutcome,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        outcome = ActionOutcome(
            action_id="a", signal_source="test", action="no_delta_action",
            executed=True, delta={},
        )
        loop._update_predictor("no_delta_action", outcome)
        stats = loop._outcome_predictor["no_delta_action"]
        assert stats["count"] == 1
        assert stats["positive"] == 0  # No positive delta


# ---------------------------------------------------------------------------
# Phase 5.4: Cross-agent action locks
# ---------------------------------------------------------------------------

class TestActionLocks:
    """Test cross-agent action coordination with locks."""

    def test_get_action_lock_returns_lock(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        lock = loop._get_action_lock("test_action")
        assert hasattr(lock, "acquire")
        assert hasattr(lock, "release")

    def test_get_action_lock_caches(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        lock1 = loop._get_action_lock("cached_action")
        lock2 = loop._get_action_lock("cached_action")
        assert lock1 is lock2

    def test_get_action_lock_different_actions(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        lock1 = loop._get_action_lock("action_a")
        lock2 = loop._get_action_lock("action_b")
        assert lock1 is not lock2

    def test_lock_acquire_release(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        loop = CognitiveActionLoop()
        lock = loop._get_action_lock("lockable_action")
        assert lock.acquire(blocking=False) is True
        # Second acquire should fail (non-blocking)
        assert lock.acquire(blocking=False) is False
        lock.release()
        # Now should be acquirable again
        assert lock.acquire(blocking=False) is True
        lock.release()


# ---------------------------------------------------------------------------
# Phase 5.5: Consciousness-driven action selection
# ---------------------------------------------------------------------------

class TestConsciousnessAdjustment:
    """Test consciousness-driven action selection."""

    def test_consciousness_adjust_exists(self):
        from whitemagic.core.consciousness.cognitive_action_loop import CognitiveActionLoop
        assert hasattr(CognitiveActionLoop, "_consciousness_adjust")

    def test_consciousness_adjust_returns_signals(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()
        signals = [
            ActionSignal(source="guna", signal_id="1", title="T", description="D",
                         confidence=0.5, urgency=0.5, action="trigger_dream_cycle"),
        ]
        result = loop._consciousness_adjust(signals)
        assert result is signals  # Returns same list (modified in place)

    def test_consciousness_adjust_boosts_on_ignition(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        signal = ActionSignal(
            source="citta", signal_id="1", title="T", description="D",
            confidence=0.5, urgency=0.4, action="analyze_ignition_pattern",
        )
        original_urgency = signal.urgency

        with patch("whitemagic.core.consciousness.citta_cycle.get_citta_cycle") as mock:
            mock_cycle = MagicMock()
            mock_traj = MagicMock()
            mock_traj.avg_velocity.return_value = 0.3
            mock_traj.ignition_events.return_value = [{"pos": i} for i in range(6)]
            mock_cycle.get_trajectory.return_value = mock_traj
            mock_cycle._last_depth = "surface"
            mock.return_value = mock_cycle

            loop._consciousness_adjust([signal])
            # Urgency should be boosted by 1.5x for ignition analysis
            assert signal.urgency > original_urgency
            assert signal.urgency == min(1.0, original_urgency * 1.5)

    def test_consciousness_adjust_boosts_deep_state(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        signal = ActionSignal(
            source="guna", signal_id="1", title="T", description="D",
            confidence=0.5, urgency=0.4, action="trigger_dream_cycle",
        )
        original_urgency = signal.urgency

        with patch("whitemagic.core.consciousness.citta_cycle.get_citta_cycle") as mock:
            mock_cycle = MagicMock()
            mock_traj = MagicMock()
            mock_traj.avg_velocity.return_value = 0.3
            mock_traj.ignition_events.return_value = []
            mock_cycle.get_trajectory.return_value = mock_traj
            mock_cycle._last_depth = "deep"  # Deep state
            mock.return_value = mock_cycle

            loop._consciousness_adjust([signal])
            # Urgency should be boosted by 1.3x for consolidation in deep state
            assert signal.urgency > original_urgency

    def test_consciousness_adjust_boosts_high_velocity(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        signal = ActionSignal(
            source="guna", signal_id="1", title="T", description="D",
            confidence=0.5, urgency=0.4, action="trigger_emergence_scan",
        )
        original_urgency = signal.urgency

        with patch("whitemagic.core.consciousness.citta_cycle.get_citta_cycle") as mock:
            mock_cycle = MagicMock()
            mock_traj = MagicMock()
            mock_traj.avg_velocity.return_value = 0.7  # High velocity
            mock_traj.ignition_events.return_value = []
            mock_cycle.get_trajectory.return_value = mock_traj
            mock_cycle._last_depth = "surface"
            mock.return_value = mock_cycle

            loop._consciousness_adjust([signal])
            # Urgency should be boosted by 1.3x for emergence in high velocity
            assert signal.urgency > original_urgency

    def test_consciousness_adjust_no_boost_for_unrelated(self):
        from whitemagic.core.consciousness.cognitive_action_loop import (
            ActionSignal,
            CognitiveActionLoop,
        )
        loop = CognitiveActionLoop()

        signal = ActionSignal(
            source="guna", signal_id="1", title="T", description="D",
            confidence=0.5, urgency=0.4, action="review_insight",  # Not a boosted action
        )
        original_urgency = signal.urgency

        with patch("whitemagic.core.consciousness.citta_cycle.get_citta_cycle") as mock:
            mock_cycle = MagicMock()
            mock_traj = MagicMock()
            mock_traj.avg_velocity.return_value = 0.7
            mock_traj.ignition_events.return_value = [{"pos": i} for i in range(6)]
            mock_cycle.get_trajectory.return_value = mock_traj
            mock_cycle._last_depth = "deep"
            mock.return_value = mock_cycle

            loop._consciousness_adjust([signal])
            # review_insight is not in any boost category
            assert signal.urgency == original_urgency
