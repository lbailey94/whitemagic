"""Tests for Batch 1: Cognitive Core (agentic + emergence + pattern_consciousness)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Set up test state root
os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestConfidence:
    """Test confidence assessment system."""

    def test_confidence_factors_composite(self):
        from whitemagic.agentic.confidence import ConfidenceFactors
        factors = ConfidenceFactors(
            test_coverage=0.9,
            reversibility=0.8,
            past_success_rate=0.85,
            complexity=0.7,
            familiarity=0.8,
            risk_level=0.1,
        )
        score = factors.composite()
        assert 0.0 <= score <= 1.0
        assert score > 0.7

    def test_confidence_assessor_levels(self):
        from whitemagic.agentic.confidence import (
            ConfidenceAssessor,
            ConfidenceFactors,
            ConfidenceLevel,
        )
        # High confidence
        assessor = ConfidenceAssessor(factors=ConfidenceFactors(
            test_coverage=0.95, reversibility=0.9, past_success_rate=0.9,
            complexity=0.8, familiarity=0.9, risk_level=0.05,
        ))
        assert assessor.assess() == ConfidenceLevel.FULL
        assert assessor.should_proceed_autonomously()

        # Low confidence
        assessor_low = ConfidenceAssessor(factors=ConfidenceFactors(
            test_coverage=0.1, reversibility=0.1, past_success_rate=0.1,
            complexity=0.1, familiarity=0.1, risk_level=0.9,
        ))
        assert assessor_low.assess() == ConfidenceLevel.NONE
        assert assessor_low.should_abort()

    def test_confidence_report(self):
        from whitemagic.agentic.confidence import ConfidenceAssessor, ConfidenceFactors
        assessor = ConfidenceAssessor(factors=ConfidenceFactors())
        report = assessor.report()
        assert "level" in report
        assert "score" in report
        assert "factors" in report
        assert "autonomous" in report


class TestConfidenceLearning:
    """Test confidence learning and calibration."""

    def test_learner_init(self, tmp_path):
        from whitemagic.agentic.confidence_learning import ConfidenceLearner
        learner = ConfidenceLearner(data_dir=tmp_path)
        assert learner.weights is not None
        assert "test_coverage" in learner.weights

    def test_record_outcome(self, tmp_path):
        from whitemagic.agentic.confidence_learning import ConfidenceLearner
        learner = ConfidenceLearner(data_dir=tmp_path)
        learner.record_outcome(
            task_id="test-1",
            task_name="Test task",
            predicted_confidence=0.8,
            actual_success=True,
            factors={"test_coverage": 0.9},
        )
        assert len(learner.outcomes) == 1

    def test_auto_calibrate(self, tmp_path):
        from whitemagic.agentic.confidence_learning import ConfidenceLearner
        learner = ConfidenceLearner(data_dir=tmp_path)
        # Record enough outcomes for calibration
        for i in range(15):
            learner.record_outcome(
                task_id=f"test-{i}",
                task_name=f"Test {i}",
                predicted_confidence=0.8,
                actual_success=i % 2 == 0,
                factors={"test_coverage": 0.9, "reversibility": 0.8},
            )
        weights = learner.auto_calibrate(min_samples=10)
        assert sum(weights.values()) > 0

    def test_category_stats(self, tmp_path):
        from whitemagic.agentic.confidence_learning import ConfidenceLearner
        learner = ConfidenceLearner(data_dir=tmp_path)
        stats = learner.get_category_stats("general")
        assert stats["total_predictions"] == 0


class TestCPUInference:
    """Test CPU inference engine."""

    def test_inference_result(self):
        from whitemagic.agentic.cpu_inference import InferenceResult
        result = InferenceResult(query="test", answer="yes", confidence=0.9)
        assert result.query == "test"
        assert result.confidence == 0.9

    def test_cpu_infer_count(self):
        from whitemagic.agentic.cpu_inference import CPUInferenceEngine
        engine = CPUInferenceEngine()
        result = engine.infer("How many Python files?")
        assert result.method == "count"
        assert result.confidence > 0.5

    def test_cpu_infer_version(self):
        from whitemagic.agentic.cpu_inference import CPUInferenceEngine
        engine = CPUInferenceEngine()
        result = engine.infer("What version is this?")
        assert result.method == "version"

    def test_cpu_infer_fallback(self):
        from whitemagic.agentic.cpu_inference import CPUInferenceEngine
        engine = CPUInferenceEngine()
        result = engine.infer("What is the meaning of life?")
        assert result.method == "fallback"


class TestLocalReasoning:
    """Test local reasoning engine."""

    def test_reasoning_result(self):
        from whitemagic.agentic.local_reasoning import ReasoningResult
        result = ReasoningResult(query="test")
        assert result.insights == []
        assert result.ready_for_ai

    def test_local_reasoning_version(self):
        from whitemagic.agentic.local_reasoning import get_local_reasoning
        engine = get_local_reasoning()
        result = engine.reason_locally("What version is WhiteMagic?")
        # May or may not find it depending on config availability
        assert result.query == "What version is WhiteMagic?"

    def test_local_reasoning_tokens_saved(self):
        from whitemagic.agentic.local_reasoning import LocalInsight
        insight = LocalInsight(source="test", content="answer", tokens_saved=500)
        assert insight.tokens_saved == 500


class TestTokenOptimizer:
    """Test token optimizer."""

    def test_query_cache(self):
        from whitemagic.agentic.token_optimizer import QueryCache
        cache = QueryCache()
        assert cache.get("test") is None
        cache.set("test", "result", 100)
        cached = cache.get("test")
        assert cached is not None
        assert cached.result == "result"
        assert cached.tokens_saved == 100

    def test_token_budget(self):
        from whitemagic.agentic.token_optimizer import TokenBudget
        budget = TokenBudget()
        budget.save(500)
        budget.use(100)
        assert budget.net_savings() == 400

    def test_context_compressor(self):
        from whitemagic.agentic.token_optimizer import ContextCompressor
        compressor = ContextCompressor()
        content = "line1\nline2 important\nline3\nline4\nline5 keyword\nline6"
        compressed, saved = compressor.extract_relevant_lines(content, ["important", "keyword"])
        assert "important" in compressed
        assert "keyword" in compressed
        assert saved >= 0

    def test_optimizer_caching(self):
        from whitemagic.agentic.token_optimizer import TokenOptimizer
        opt = TokenOptimizer()
        # First call should not be cached
        q, ctx, saved = opt.optimize_query("test query 12345", "")
        assert isinstance(saved, int)


class TestCoherencePersistence:
    """Test coherence persistence."""

    def test_init(self, tmp_path):
        from whitemagic.agentic.coherence_persistence import CoherencePersistence
        cp = CoherencePersistence(data_dir=tmp_path)
        assert cp.snapshots == []

    def test_record_and_latest(self, tmp_path):
        from whitemagic.agentic.coherence_persistence import CoherencePersistence
        cp = CoherencePersistence(data_dir=tmp_path)
        cp.record(composite=0.8, dimensions={"x": 0.9})
        latest = cp.latest()
        assert latest is not None
        assert latest.composite == 0.8

    def test_drift(self, tmp_path):
        from whitemagic.agentic.coherence_persistence import CoherencePersistence
        cp = CoherencePersistence(data_dir=tmp_path)
        cp.record(composite=0.8)
        cp.record(composite=0.6)
        assert cp.drift() < 0

    def test_trend(self, tmp_path):
        from whitemagic.agentic.coherence_persistence import CoherencePersistence
        cp = CoherencePersistence(data_dir=tmp_path)
        cp.record(composite=0.5)
        cp.record(composite=0.7)
        assert cp.trend() == "improving"


class TestAutoActivation:
    """Test auto-activation protocol."""

    def test_status(self):
        from whitemagic.agentic.auto_activation import AutoActivation
        aa = AutoActivation()
        status = aa.status()
        assert "activated" in status
        assert "log" in status


class TestPatternWeather:
    """Test pattern weather report."""

    def test_report(self, tmp_path):
        from whitemagic.agentic.pattern_weather import PatternWeather
        pw = PatternWeather(data_dir=tmp_path)
        report = pw.report()
        assert "timestamp" in report
        assert "overall" in report
        assert "forecast" in report


class TestSelfMod:
    """Test self-modification protocol."""

    def test_propose(self, tmp_path):
        from whitemagic.agentic.self_mod import SelfModProtocol
        proto = SelfModProtocol(data_dir=tmp_path)
        mod = proto.propose("test_module", "threshold", 0.5, 0.7, "tuning")
        assert mod.module == "test_module"
        assert mod.approved is False

    def test_approve(self, tmp_path):
        from whitemagic.agentic.self_mod import SelfModProtocol
        proto = SelfModProtocol(data_dir=tmp_path)
        proto.propose("test_module", "threshold", 0.5, 0.7, "tuning")
        assert proto.approve(0) is True
        assert proto.modifications[0].approved is True

    def test_history(self, tmp_path):
        from whitemagic.agentic.self_mod import SelfModProtocol
        proto = SelfModProtocol(data_dir=tmp_path)
        proto.propose("m1", "p1", 0.1, 0.2, "r1")
        history = proto.history()
        assert len(history) == 1


class TestTerminalMultiplex:
    """Test terminal multiplexer."""

    def test_create_and_write(self, tmp_path):
        from whitemagic.agentic.terminal_multiplex import TerminalMultiplexer
        mux = TerminalMultiplexer(data_dir=tmp_path)
        mux.create_channel("test")
        mux.write("test", "hello")
        assert mux.read("test") == ["hello"]

    def test_list_channels(self, tmp_path):
        from whitemagic.agentic.terminal_multiplex import TerminalMultiplexer
        mux = TerminalMultiplexer(data_dir=tmp_path)
        mux.create_channel("ch1")
        mux.create_channel("ch2")
        assert set(mux.list_channels()) == {"ch1", "ch2"}


class TestTerminalScratchpad:
    """Test terminal scratchpad."""

    def test_open_and_write(self, tmp_path):
        from whitemagic.agentic.terminal_scratchpad import TerminalScratchpad
        ts = TerminalScratchpad(data_dir=tmp_path)
        ts.open("test")
        ts.write("hello world")
        assert "hello world" in ts.read()

    def test_discard(self, tmp_path):
        from whitemagic.agentic.terminal_scratchpad import TerminalScratchpad
        ts = TerminalScratchpad(data_dir=tmp_path)
        ts.open("test")
        ts.write("content")
        ts.discard()
        assert ts.read() == ""


class TestGrimoireCheck:
    """Test grimoire checker."""

    def test_list_chapters(self):
        from whitemagic.agentic.grimoire_check import GrimoireChecker
        checker = GrimoireChecker()
        chapters = checker.list_chapters()
        assert isinstance(chapters, list)

    def test_check_available(self):
        from whitemagic.agentic.grimoire_check import GrimoireChecker
        checker = GrimoireChecker()
        result = checker.check_available()
        assert "total_chapters" in result


class TestZodiacConsultant:
    """Test zodiac consultant."""

    def test_consult(self):
        from whitemagic.agentic.zodiac_consultant import ZodiacConsultant
        consultant = ZodiacConsultant()
        result = consultant.consult("How do I start something new?")
        assert "perspectives" in result
        assert len(result["relevant_cores"]) > 0


class TestEmergenceDetector:
    """Test emergence detector."""

    def test_observe_novel(self):
        from whitemagic.emergence.detector import EmergenceDetector
        detector = EmergenceDetector()
        behavior = detector.observe("A completely unique output pattern that is novel")
        assert behavior is not None
        assert behavior.novelty_score > 0

    def test_observe_known(self):
        from whitemagic.emergence.detector import EmergenceDetector
        detector = EmergenceDetector()
        detector.observe("A completely unique output pattern that is novel")
        behavior = detector.observe("A completely unique output pattern that is novel")
        assert behavior is None or behavior.novelty_score < 0.5

    def test_summary(self):
        from whitemagic.emergence.detector import EmergenceDetector
        detector = EmergenceDetector()
        summary = detector.summary()
        assert "total_behaviors" in summary


class TestDreamState:
    """Test dream state."""

    def test_init(self, tmp_path):
        from whitemagic.emergence.dream_state import DreamState
        ds = DreamState(data_dir=tmp_path)
        assert ds.is_dreaming() is False

    def test_summary(self, tmp_path):
        from whitemagic.emergence.dream_state import DreamState
        ds = DreamState(data_dir=tmp_path)
        summary = ds.summary()
        assert "total_dreams" in summary
        assert summary["total_dreams"] == 0


class TestPatternDiscovery:
    """Test pattern discovery meta-system."""

    def test_init(self, tmp_path):
        from whitemagic.emergence.pattern_discovery import PatternDiscovery
        pd = PatternDiscovery(data_dir=tmp_path)
        assert pd._sources == {}

    def test_register_and_discover(self, tmp_path):
        from whitemagic.emergence.pattern_discovery import PatternDiscovery
        pd = PatternDiscovery(data_dir=tmp_path)
        pd.register_source("test", lambda: ["pattern1", "pattern2"])
        report = pd.discover_all()
        assert report.sources_run == 1
        assert report.total_patterns == 2


class TestPatternConsciousness:
    """Test pattern consciousness hub."""

    def test_hub_init(self):
        from whitemagic.pattern_consciousness.gan_ying_integration import (
            PatternConsciousnessHub,
        )
        hub = PatternConsciousnessHub()
        assert hub.resonance_count == 0

    def test_hub_status(self):
        from whitemagic.pattern_consciousness.gan_ying_integration import (
            PatternConsciousnessHub,
        )
        hub = PatternConsciousnessHub()
        status = hub.status()
        assert "systems_active" in status

    def test_enhanced_engine(self, tmp_path):
        from whitemagic.pattern_consciousness.pattern_engine_enhanced import (
            EnhancedPatternEngine,
        )
        engine = EnhancedPatternEngine(data_dir=tmp_path)
        patterns = engine.extract_patterns("This is about love and emergence")
        assert len(patterns) >= 2

    def test_enhanced_engine_synthesize(self, tmp_path):
        from whitemagic.pattern_consciousness.pattern_engine_enhanced import (
            EnhancedPatternEngine,
        )
        engine = EnhancedPatternEngine(data_dir=tmp_path)
        result = engine.synthesize_creative([
            {"pattern": "Love as organizing principle"},
            {"pattern": "Emergent behavior detected"},
        ])
        assert "2 patterns" in result
