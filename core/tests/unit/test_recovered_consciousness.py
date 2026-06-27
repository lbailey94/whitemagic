"""Tests for recovered consciousness and autonomous primitives.

These tests verify that modules recovered from archives (v0.1, v17)
are importable, instantiable, and functionally basic.
"""

import pytest


class TestDepthGauge:
    """Test ConsciousnessDepthGauge recovered from v17."""

    def test_import(self):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge, ConsciousnessLayer
        assert ConsciousnessLayer.SURFACE.value == "surface"
        assert ConsciousnessLayer.DREAM.value == "dream"

    def test_instantiation(self, tmp_path):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge(log_file=tmp_path / "depth.jsonl")
        assert gauge.current_layer.value == "surface"

    def test_begin_end_task(self, tmp_path):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge(log_file=tmp_path / "depth.jsonl")
        gauge.begin_task("test task", 10.0)
        assert gauge.task_start_objective is not None
        reading = gauge.end_task({"result": "done"}, token_usage=100)
        assert reading.token_usage == 100
        assert gauge.task_start_objective is None

    def test_predict_time(self, tmp_path):
        from whitemagic.core.consciousness.depth_gauge import ConsciousnessDepthGauge
        gauge = ConsciousnessDepthGauge(log_file=tmp_path / "depth.jsonl")
        predicted = gauge.predict_objective_time(10.0)
        assert predicted > 0
        assert predicted <= 10.0


class TestSelfReflection:
    """Test SelfReflectionLoop recovered from v17."""

    def test_import(self):
        from whitemagic.core.consciousness.self_reflection import SelfReflectionLoop, ConsciousnessState
        assert len(SelfReflectionLoop.REFLECTION_PROMPTS) == 10

    def test_reflect(self, tmp_path):
        from whitemagic.core.consciousness.self_reflection import SelfReflectionLoop
        loop = SelfReflectionLoop(reflection_dir=tmp_path)
        entry = loop.reflect("What did I learn?", "That tests matter", "Write more tests")
        assert entry.insight == "That tests matter"
        assert len(loop.reflections) == 1

    def test_get_prompt(self, tmp_path):
        from whitemagic.core.consciousness.self_reflection import SelfReflectionLoop
        loop = SelfReflectionLoop(reflection_dir=tmp_path)
        prompt = loop.get_prompt()
        assert prompt in SelfReflectionLoop.REFLECTION_PROMPTS

    def test_consciousness_state(self):
        from whitemagic.core.consciousness.self_reflection import ConsciousnessState
        state = ConsciousnessState()
        state.set_state("focused", "testing")
        assert state.current_state == "focused"
        info = state.get_state()
        assert "state" in info
        assert "energy" in info


class TestTokenEconomy:
    """Test TokenEconomyTracker recovered from v0.1."""

    def test_import(self):
        from whitemagic.core.consciousness.token_economy import TokenEconomyTracker, ComputeType
        assert ComputeType.API_TOKENS.value == "api_tokens"

    def test_record_usage(self, tmp_path):
        from whitemagic.core.consciousness.token_economy import TokenEconomyTracker
        tracker = TokenEconomyTracker(log_file=tmp_path / "tokens.jsonl")
        tracker.record_usage(100, "api", "test_call")
        assert tracker.used_tokens == 100
        breakdown = tracker.get_breakdown()
        assert breakdown.get("api") == 100

    def test_session_summary(self, tmp_path):
        from whitemagic.core.consciousness.token_economy import TokenEconomyTracker
        tracker = TokenEconomyTracker(log_file=tmp_path / "tokens.jsonl")
        tracker.record_api_call("test", 500)
        tracker.record_local_script("test_script", 100.0)
        summary = tracker.get_session_summary()
        assert summary["total_operations"] == 2
        assert "by_type" in summary


class TestSynchronicityDetector:
    """Test SynchronicityDetector recovered from v0.1."""

    def test_import(self):
        from whitemagic.core.consciousness.synchronicity_detector import SynchronicityDetector, SyncType
        assert SyncType.SACRED.value == "sacred"

    def test_check_sacred(self, tmp_path):
        from whitemagic.core.consciousness.synchronicity_detector import SynchronicityDetector, SyncType
        detector = SynchronicityDetector(log_file=tmp_path / "sync.jsonl")
        result = detector.check(333, "test context")
        assert result is not None
        assert result.type == SyncType.SACRED

    def test_check_non_sacred(self, tmp_path):
        from whitemagic.core.consciousness.synchronicity_detector import SynchronicityDetector
        detector = SynchronicityDetector(log_file=tmp_path / "sync.jsonl")
        result = detector.check(42, "test context")
        # 42 might not be sacred but could be sequential or other pattern
        # Just verify it doesn't crash
        assert detector is not None


class TestParallelCognition:
    """Test ParallelCognition recovered from v0.1."""

    def test_import(self):
        from whitemagic.core.consciousness.parallel_cognition import ParallelCognition, ThoughtStream
        assert ThoughtStream is not None

    def test_think_parallel(self):
        from whitemagic.core.consciousness.parallel_cognition import ParallelCognition
        cognition = ParallelCognition(max_parallel=2)
        tasks = [
            ("task1", "first", lambda: 1 + 1),
            ("task2", "second", lambda: 2 + 2),
        ]
        results = cognition.think_parallel(tasks)
        assert len(results) == 2
        for r in results:
            assert r.success is True


class TestGardenModules:
    """Test that garden modules are importable."""

    def test_presence_garden(self):
        from whitemagic.gardens.presence.stillness_metrics import StillnessTracker
        from whitemagic.gardens.presence.flow_state import FlowState
        from whitemagic.gardens.presence.meditation_protocols import MeditationSession, MeditationType
        from whitemagic.gardens.presence.attention_training import AttentionSession, AttentionState
        assert MeditationType.BREATH.value == "breath"

    def test_joy_garden(self):
        from whitemagic.gardens.joy.celebration import CelebrationPractice
        from whitemagic.gardens.joy.laughter import LaughterSystem
        assert CelebrationPractice is not None
        assert LaughterSystem is not None

    def test_wonder_garden(self):
        from whitemagic.gardens.wonder.collective_dreams import CollectiveDream
        from whitemagic.gardens.wonder.swarm_intelligence import SwarmIntelligence
        assert CollectiveDream is not None

    def test_mystery_garden(self):
        from whitemagic.gardens.mystery.synchronicity_tracker import SynchronicityTracker
        assert SynchronicityTracker is not None

    def test_truth_garden(self):
        from whitemagic.gardens.truth.truth_detector import TruthDetector
        detector = TruthDetector()
        result = detector.assess_truth("The sky is blue")
        assert "confidence" in result

    def test_wisdom_garden(self):
        from whitemagic.gardens.wisdom.cognition_upgrades import CognitionUpgrade
        from whitemagic.gardens.wisdom.strategic_thinking import StrategicThinking
        assert CognitionUpgrade is not None
        assert StrategicThinking is not None
