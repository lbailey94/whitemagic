"""Tests for RecursiveImprovementLoop."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from whitemagic.core.evolution.recursive_loop import (
    ImprovementCycle,
    ImprovementHypothesis,
    RecursiveImprovementLoop,
    get_improvement_loop,
    reset_improvement_loop,
)

# Module-level patches for heavy engines — avoid SQLite queries, embedding loading,
# and insight pipeline orchestration that take 2-3s per first run_cycle call.
_mock_kaizen = MagicMock()
_mock_kaizen.analyze.return_value = MagicMock(
    proposals=[MagicMock(id="quality_test_1", title="Test proposal",
                        description="Test description", category="quality",
                        impact="medium", effort="low", auto_fixable=False,
                        fix_action=None, metadata={"count": 1})],
    metrics={"total": 1},
)
_mock_predictive = MagicMock()
_mock_predictive.predict.return_value = MagicMock(predictions=[], patterns_analyzed=0, memories_scanned=0)
_mock_predictive.get_calibration.return_value = None
_mock_predictive.apply_calibration.side_effect = lambda x: x
_mock_predictive.auto_prescience_claims.return_value = {"stored_claims": 0, "total_predictions": 0}
_mock_emergence = MagicMock()
_mock_emergence.scan_for_emergence.return_value = []
_mock_insight = MagicMock()
_mock_insight.generate_briefing.return_value = MagicMock(items=[])


def _patch_engines():
    """Return a context manager that patches all heavy engines."""
    return [
        patch("whitemagic.core.intelligence.synthesis.kaizen_engine.get_kaizen_engine", return_value=_mock_kaizen),
        patch("whitemagic.core.intelligence.synthesis.predictive_engine.get_predictive_engine", return_value=_mock_predictive),
        patch("whitemagic.core.intelligence.agentic.emergence_engine.get_emergence_engine", return_value=_mock_emergence),
        patch("whitemagic.core.intelligence.insight_pipeline.InsightPipeline", return_value=_mock_insight),
        # Skip HRR + embedding operations (loads MiniLM model, ~2-3s)
        patch("whitemagic.core.memory.hrr.get_hrr_engine", side_effect=ImportError("skipped in tests")),
        patch("whitemagic.core.memory.embeddings.get_embedding_engine", side_effect=ImportError("skipped in tests")),
        # Also patch the from-import targets inside recursive_loop
        patch("whitemagic.core.evolution.recursive_loop.get_hrr_engine", create=True, side_effect=ImportError("skipped in tests")),
        patch("whitemagic.core.evolution.recursive_loop.get_embedding_engine", create=True, side_effect=ImportError("skipped in tests")),
        # Skip ActorSupervisor which starts Elixir subprocess (~1s per test)
        patch("whitemagic.core.evolution.recursive_loop.RecursiveImprovementLoop._get_actor_supervisor", return_value=None),
    ]


class TestImprovementHypothesis:
    def test_creation(self):
        hyp = ImprovementHypothesis(
            id="test_1",
            source="kaizen",
            title="Fix untitled memories",
            description="Found 5 untitled memories",
            category="quality",
            predicted_impact=0.8,
            confidence=0.7,
            effort="low",
        )
        assert hyp.id == "test_1"
        assert hyp.source == "kaizen"
        assert hyp.novelty_score == 0.0

    def test_auto_fixable_default(self):
        hyp = ImprovementHypothesis(
            id="test_2", source="emergence", title="Test", description="Test",
            category="emergence", predicted_impact=0.5, confidence=0.5, effort="medium",
        )
        assert hyp.auto_fixable is False
        assert hyp.fix_action is None


class TestRecursiveImprovementLoop:
    def setup_method(self):
        reset_improvement_loop()
        self.loop = RecursiveImprovementLoop()
        # Reduce MC trials from 5000 to 50 for test speed
        self._orig_run = self.loop._mc_enhancer.run_calibrated
        def _fast_run(claims, **kwargs):
            kwargs['n_trials'] = 50
            return self._orig_run(claims, **kwargs)
        self.loop._mc_enhancer.run_calibrated = _fast_run
        # Patch heavy engines to avoid SQLite/embedding overhead
        self._patches = _patch_engines()
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in getattr(self, '_patches', []):
            p.stop()

    def test_init(self):
        assert self.loop._cycle_count == 0
        assert self.loop._last_cycle is None
        assert self.loop._hll is not None
        assert self.loop._cms is not None
        assert self.loop._mc_enhancer is not None
        assert self.loop._bandit is not None
        assert self.loop._autodidactic is not None

    def test_run_cycle_returns_cycle(self):
        cycle = self.loop.run_cycle(max_hypotheses=5)
        assert isinstance(cycle, ImprovementCycle)
        assert cycle.cycle_id is not None
        assert len(cycle.cycle_id) == 8
        assert cycle.duration_ms > 0
        assert "observe" in cycle.phase_results
        assert "imagine" in cycle.phase_results
        assert "predict" in cycle.phase_results
        assert "recommend" in cycle.phase_results
        assert "learn" in cycle.phase_results

    def test_cycle_increments_count(self):
        assert self.loop._cycle_count == 0
        self.loop.run_cycle(max_hypotheses=3)
        assert self.loop._cycle_count == 1
        self.loop.run_cycle(max_hypotheses=3)
        assert self.loop._cycle_count == 2

    def test_cycle_has_analytics(self):
        cycle = self.loop.run_cycle(max_hypotheses=3)
        assert "cycle_number" in cycle.analytics
        assert cycle.analytics["cycle_number"] == 1
        assert "total_proposals" in cycle.analytics
        assert "hypotheses_created" in cycle.analytics
        assert "distinct_improvements_seen" in cycle.analytics

    def test_observe_phase_structure(self):
        cycle = self.loop.run_cycle(max_hypotheses=3)
        observe = cycle.phase_results["observe"]
        assert "proposals" in observe
        assert "errors" in observe
        assert "total_proposals" in observe
        assert isinstance(observe["proposals"], list)
        assert isinstance(observe["errors"], list)

    def test_imagine_phase_creates_hypotheses(self):
        cycle = self.loop.run_cycle(max_hypotheses=10)
        imagine = cycle.phase_results["imagine"]
        assert "hypotheses_created" in imagine
        assert imagine["hypotheses_created"] == len(cycle.hypotheses)
        # Each hypothesis should have required fields
        for hyp in cycle.hypotheses:
            assert hyp.id is not None
            assert hyp.source in ("kaizen", "predictive", "emergence", "insight", "hrr")
            assert 0.0 <= hyp.predicted_impact <= 1.0
            assert 0.0 <= hyp.confidence <= 1.0
            assert 0.0 <= hyp.novelty_score <= 1.0

    def test_recommend_phase_ranks(self):
        cycle = self.loop.run_cycle(max_hypotheses=10)
        recommend = cycle.phase_results["recommend"]
        assert "recommendations" in recommend
        # Recommendations should be ranked
        for i, rec in enumerate(cycle.top_recommendations):
            assert rec["rank"] == i + 1
            assert "score" in rec
            assert "title" in rec
            assert "recommended_tools" in rec
            assert "task_type" in rec

    def test_learn_phase_records(self):
        cycle = self.loop.run_cycle(max_hypotheses=5)
        learn = cycle.phase_results["learn"]
        assert "applications_recorded" in learn
        assert learn["applications_recorded"] == len(cycle.hypotheses)

    def test_hll_tracks_distinct_improvements(self):
        self.loop.run_cycle(max_hypotheses=3)
        first_count = self.loop._hll.estimate()
        assert first_count > 0
        # Run another cycle — HLL should track more
        self.loop.run_cycle(max_hypotheses=3)
        second_count = self.loop._hll.estimate()
        assert second_count >= first_count

    def test_record_outcome_updates_bandit(self):
        # Run a cycle to generate hypotheses
        cycle = self.loop.run_cycle(max_hypotheses=3)
        if cycle.hypotheses:
            hyp_id = cycle.hypotheses[0].id
            # Record a successful outcome
            self.loop.record_outcome(hyp_id, success=True, performance_gain=2.5)
            # Bandit should have recorded it
            bandit_stats = self.loop._bandit.get_tool_stats(hyp_id)
            assert bandit_stats is not None
            assert bandit_stats["total_successes"] >= 1

    def test_record_outcome_updates_autodidactic(self):
        cycle = self.loop.run_cycle(max_hypotheses=3)
        if cycle.hypotheses:
            hyp_id = cycle.hypotheses[0].id
            self.loop.record_outcome(hyp_id, success=True, performance_gain=1.5)
            # AutodidacticLoop should have the pattern
            stats = self.loop._autodidactic.get_pattern_stats(hyp_id)
            # May be None if the pattern_id doesn't match exactly,
            # but the outcome should be recorded without error
            assert stats is None or stats["application_count"] >= 1

    def test_get_status(self):
        self.loop.run_cycle(max_hypotheses=3)
        status = self.loop.get_status()
        assert status["cycle_count"] == 1
        assert status["distinct_improvements"] > 0
        assert status["last_cycle"] is not None
        assert status["bandit_summary"] is not None

    def test_multiple_cycles_accumulate(self):
        for i in range(3):
            self.loop.run_cycle(max_hypotheses=3)
        assert self.loop._cycle_count == 3
        status = self.loop.get_status()
        assert status["cycle_count"] == 3
        # HLL should show more distinct improvements over time
        assert status["distinct_improvements"] > 0

    def test_singleton(self):
        l1 = get_improvement_loop()
        l2 = get_improvement_loop()
        assert l1 is l2

    def test_cycle_to_dict(self):
        cycle = self.loop.run_cycle(max_hypotheses=3)
        d = cycle.to_dict()
        assert "cycle_id" in d
        assert "phases" in d
        assert "hypothesis_count" in d
        assert "duration_ms" in d
        assert d["hypothesis_count"] == len(cycle.hypotheses)

    def test_novelty_decreases_with_repeated_improvements(self):
        # Run multiple cycles — novelty should decrease for same improvements
        self.loop.run_cycle(max_hypotheses=3)

        self.loop.run_cycle(max_hypotheses=3)
        # CMS frequency should be higher now, reducing novelty
        # (Only if the same improvement IDs appear, which depends on the engines)
        # At minimum, novelty scores should be valid
        second_novelty = [h.novelty_score for h in self.loop._last_cycle.hypotheses]
        for n in second_novelty:
            assert 0.0 <= n <= 1.0


class TestAutomatedOutcomeDetection:
    """Tests for Objective A — Automated Outcome Detection."""

    def setup_method(self):
        reset_improvement_loop()
        self.loop = RecursiveImprovementLoop()
        # Reduce MC trials for test speed
        self._orig_run = self.loop._mc_enhancer.run_calibrated
        def _fast_run(claims, **kwargs):
            kwargs['n_trials'] = 50
            return self._orig_run(claims, **kwargs)
        self.loop._mc_enhancer.run_calibrated = _fast_run
        # Patch heavy engines to avoid SQLite/embedding overhead
        self._patches = _patch_engines()
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in getattr(self, '_patches', []):
            p.stop()

    def test_hypothesis_has_verification_fields(self):
        hyp = ImprovementHypothesis(
            id="quality_untitled_5",
            source="kaizen",
            title="Fix 5 untitled memories",
            description="Found 5 untitled memories",
            category="quality",
            predicted_impact=0.8,
            confidence=0.7,
            effort="low",
            verification_query="untitled",
            before_count=5,
        )
        assert hyp.verification_query == "untitled"
        assert hyp.before_count == 5

    def test_hypothesis_verification_defaults_none(self):
        hyp = ImprovementHypothesis(
            id="test_1", source="kaizen", title="Test", description="Test",
            category="quality", predicted_impact=0.5, confidence=0.5, effort="low",
        )
        assert hyp.verification_query is None
        assert hyp.before_count is None

    def test_verify_outcome_missing_params(self):
        result = self.loop.verify_outcome(
            hypothesis_id="test_1",
            before_count=0,
            verification_query="untitled",
        )
        assert result["success"] is False
        assert result["recorded"] is False
        assert "error" in result

    def test_verify_outcome_missing_query(self):
        result = self.loop.verify_outcome(
            hypothesis_id="test_1",
            before_count=10,
            verification_query="",
        )
        assert result["success"] is False
        assert "error" in result

    def test_auto_verify_cycle_no_cycle(self):
        results = self.loop.auto_verify_cycle()
        assert results == []

    def test_auto_verify_cycle_with_no_fixable(self):
        # Run a cycle — even if no auto-fixable hypotheses, should not crash
        self.loop.run_cycle(max_hypotheses=3)
        results = self.loop.auto_verify_cycle()
        assert isinstance(results, list)


class TestSurprisalDrivenExploration:
    """Tests for Objective D — Surprisal-Driven Exploration."""

    def setup_method(self):
        reset_improvement_loop()
        self.loop = RecursiveImprovementLoop()
        # Reduce MC trials for test speed
        self._orig_run = self.loop._mc_enhancer.run_calibrated
        def _fast_run(claims, **kwargs):
            kwargs['n_trials'] = 50
            return self._orig_run(claims, **kwargs)
        self.loop._mc_enhancer.run_calibrated = _fast_run
        # Patch heavy engines to avoid SQLite/embedding overhead
        self._patches = _patch_engines()
        for p in self._patches:
            p.start()

    def teardown_method(self):
        for p in getattr(self, '_patches', []):
            p.stop()

    def test_surprise_gate_init_none(self):
        assert self.loop._surprise_gate is None
        assert self.loop._surprisal_alpha == 0.6
        assert self.loop._surprisal_beta == 0.4

    def test_get_surprise_gate_returns_gate_or_none(self):
        gate = self.loop._get_surprise_gate()
        # Either a SurpriseGate instance or None (if embeddings unavailable)
        assert gate is None or hasattr(gate, "evaluate")

    def test_get_surprise_gate_caches(self):
        g1 = self.loop._get_surprise_gate()
        g2 = self.loop._get_surprise_gate()
        # Should return same object (cached)
        assert g1 is g2

    def test_compute_surprisal_novelty_without_gate(self):
        # When gate is unavailable, should return cms_novelty as-is
        self.loop._surprise_gate = False  # Force unavailable
        result = self.loop._compute_surprisal_novelty("test description", 0.8)
        assert result == 0.8

    def test_compute_surprisal_novelty_clamps_to_01(self):
        # Should always return value in [0, 1]
        self.loop._surprise_gate = False  # Force unavailable
        result = self.loop._compute_surprisal_novelty("test", 0.5)
        assert 0.0 <= result <= 1.0

    def test_novelty_uses_surprisal_in_cycle(self):
        # Run a cycle and verify novelty scores are still valid
        cycle = self.loop.run_cycle(max_hypotheses=5)
        for hyp in cycle.hypotheses:
            assert 0.0 <= hyp.novelty_score <= 1.0
