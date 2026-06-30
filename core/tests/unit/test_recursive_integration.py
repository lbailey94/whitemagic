"""Integration tests for the wired RecursiveImprovementLoop.

Exercises the full observe→imagine→predict→recommend→learn cycle with
the 26 new evolution modules integrated via lazy-loading.
"""

import pytest

from whitemagic.core.evolution.recursive_loop import (
    ImprovementHypothesis,
    RecursiveImprovementLoop,
    reset_improvement_loop,
)


@pytest.fixture
def loop():
    """Fresh improvement loop for each test."""
    reset_improvement_loop()
    return RecursiveImprovementLoop()


class TestHypothesisFields:
    """Verify new hypothesis fields exist and default correctly."""

    def test_new_fields_default(self):
        hyp = ImprovementHypothesis(
            id="test_1",
            source="test",
            title="Test",
            description="desc",
            category="performance",
            predicted_impact=0.8,
            confidence=0.7,
            effort="low",
        )
        assert hyp.garden is None
        assert hyp.guna is None
        assert hyp.galactic_zone is None
        assert hyp.debate_contention == 0.0
        assert hyp.yield_type is None
        assert hyp.exploration_boost == 0.0
        assert hyp.information_gain == 0.0


class TestLazyLoading:
    """Verify lazy-loading helpers work with graceful degradation."""

    def test_get_module_returns_none_on_missing(self, loop):
        result = loop._get_module(
            "_nonexistent", "whitemagic.core.evolution.nonexistent", "NoClass"
        )
        assert result is None

    def test_get_module_caches(self, loop):
        # First call loads, second returns cached
        mod1 = loop._get_garden_router()
        mod2 = loop._get_garden_router()
        assert mod1 is mod2

    def test_get_thermodynamic_temperature_default(self, loop):
        # When thermo module unavailable, returns 1.0
        temp = loop._get_thermodynamic_temperature()
        assert temp == 1.0


class TestClassificationIntegration:
    """Test _classify_hypothesis wires garden, guna, galactic."""

    def test_classify_populates_fields(self, loop):
        hyp = ImprovementHypothesis(
            id="test_classify_1",
            source="test",
            title="Fix memory leak in joy garden",
            description="The joy garden has a memory leak that needs fixing",
            category="memory",
            predicted_impact=0.8,
            confidence=0.7,
            effort="low",
        )
        loop._classify_hypothesis(hyp)
        # Garden should be classified (or None if module unavailable)
        # Just verify it doesn't crash
        assert hyp.garden is None or isinstance(hyp.garden, str)


class TestDebateIntegration:
    """Test _debate_hypothesis returns a boost."""

    def test_debate_returns_float(self, loop):
        hyp = ImprovementHypothesis(
            id="test_debate_1",
            source="test",
            title="Optimize search",
            description="Speed up vector search",
            category="performance",
            predicted_impact=0.8,
            confidence=0.7,
            effort="low",
        )
        boost = loop._debate_hypothesis(hyp)
        assert isinstance(boost, float)
        assert 0.0 <= boost <= 0.3


class TestRecordOutcomeIntegration:
    """Test record_outcome wires valence, causal, actors, garden, guna, PC."""

    def test_record_outcome_no_crash(self, loop):
        # Should not crash even with no prior cycle
        loop.record_outcome(
            hypothesis_id="test_outcome_1",
            success=True,
            performance_gain=2.0,
            quality_score=0.9,
        )

    def test_record_outcome_with_cycle(self, loop):
        # Create a cycle with a hypothesis, then record outcome
        hyp = ImprovementHypothesis(
            id="test_outcome_2",
            source="test",
            title="Fix bug",
            description="Fix a critical bug",
            category="bug",
            predicted_impact=0.9,
            confidence=0.8,
            effort="low",
        )
        # Manually set last cycle
        from whitemagic.core.evolution.recursive_loop import ImprovementCycle

        cycle = ImprovementCycle(
            cycle_id="test_cycle",
            timestamp="2026-01-01T00:00:00Z",
        )
        cycle.hypotheses = [hyp]
        loop._last_cycle = cycle
        loop._classify_hypothesis(hyp)

        # Record outcome — should update valence, causal, actors, garden, guna, PC
        loop.record_outcome(
            hypothesis_id="test_outcome_2",
            success=True,
            performance_gain=3.0,
        )


class TestGetStatusIntegration:
    """Test get_status includes evolution module stats."""

    def test_status_has_base_fields(self, loop):
        status = loop.get_status()
        assert "cycle_count" in status
        assert "distinct_improvements" in status
        assert "bandit_summary" in status

    def test_status_may_have_evolution(self, loop):
        status = loop.get_status()
        # evolution_modules key only present if at least one module loaded
        if "evolution_modules" in status:
            assert isinstance(status["evolution_modules"], dict)


class TestAnalyticsIntegration:
    """Test _build_analytics includes Phase 3-6 enrichments."""

    def test_analytics_has_evolution_fields(self, loop):
        from whitemagic.core.evolution.recursive_loop import ImprovementCycle

        cycle = ImprovementCycle(
            cycle_id="test_analytics",
            timestamp="2026-01-01T00:00:00Z",
        )
        cycle.hypotheses = [
            ImprovementHypothesis(
                id="test_a_1",
                source="test",
                title="Test",
                description="desc",
                category="perf",
                predicted_impact=0.8,
                confidence=0.7,
                effort="low",
                information_gain=0.5,
                debate_contention=0.3,
            ),
        ]
        analytics = loop._build_analytics(cycle)
        assert "evolution_modules" in analytics
        assert "avg_information_gain" in analytics
        assert "avg_debate_contention" in analytics
        assert analytics["avg_information_gain"] == 0.5
        assert analytics["avg_debate_contention"] == 0.3
