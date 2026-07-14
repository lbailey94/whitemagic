"""Tests for Objective G — Galactic Zone Lifecycle for Hypotheses."""

from __future__ import annotations

from whitemagic.core.evolution.galactic_hypothesis import (
    ZONE_ORDER,
    HypothesisGalacticMap,
    HypothesisState,
    HypothesisZone,
)


class TestHypothesisZone:
    def test_zone_order(self):
        assert ZONE_ORDER[0] == HypothesisZone.CORE
        assert ZONE_ORDER[-1] == HypothesisZone.FAR_EDGE
        assert len(ZONE_ORDER) == 5


class TestHypothesisState:
    def test_defaults(self):
        state = HypothesisState(hypothesis_id="h1")
        assert state.zone == HypothesisZone.CORE
        assert state.outcome_count == 0
        assert state.success_rate == 0.0

    def test_success_rate(self):
        state = HypothesisState(hypothesis_id="h1", outcome_count=4, success_count=3)
        assert abs(state.success_rate - 0.75) < 1e-6

    def test_drift_rate_unvalidated(self):
        state = HypothesisState(hypothesis_id="h1", outcome_count=0, confidence=0.5)
        # 1 / (1 + 0 * 0.5) = 1.0
        assert abs(state.drift_rate - 1.0) < 1e-6

    def test_drift_rate_validated(self):
        state = HypothesisState(hypothesis_id="h1", outcome_count=10, confidence=0.8)
        # 1 / (1 + 10 * 0.8) = 1/9
        assert state.drift_rate < 0.15


class TestHypothesisGalacticMap:
    def test_register(self):
        gmap = HypothesisGalacticMap()
        state = gmap.register("h1", confidence=0.7)
        assert state.zone == HypothesisZone.CORE
        assert state.confidence == 0.7

    def test_get_state(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        assert gmap.get_state("h1") is not None
        assert gmap.get_state("h2") is None

    def test_record_success_stays_core(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        zone = gmap.record_outcome("h1", success=True)
        assert zone == HypothesisZone.CORE

    def test_record_failure_demotes(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1", confidence=0.1)  # Low confidence = high drift rate
        # Need multiple failures to demote (drift_rate is probabilistic)
        zone = HypothesisZone.CORE
        for _ in range(20):
            zone = gmap.record_outcome("h1", success=False)
        # Should have moved out of core
        assert zone != HypothesisZone.CORE

    def test_success_promotes_from_inner_rim(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        # Manually set to INNER_RIM via failures
        state = gmap.get_state("h1")
        state.zone = HypothesisZone.INNER_RIM
        zone = gmap.record_outcome("h1", success=True)
        assert zone == HypothesisZone.CORE

    def test_supersede(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.supersede("h1", by_id="h2")
        state = gmap.get_state("h1")
        assert state.zone == HypothesisZone.OUTER_RIM
        assert state.metadata["superseded_by"] == "h2"

    def test_deprecate(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.deprecate("h1")
        state = gmap.get_state("h1")
        assert state.zone == HypothesisZone.FAR_EDGE

    def test_zone_counts(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.register("h2")
        gmap.deprecate("h2")
        counts = gmap.get_zone_counts()
        assert counts["core"] == 1
        assert counts["far_edge"] == 1

    def test_active_hypotheses(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.register("h2")
        gmap.deprecate("h2")
        active = gmap.get_active_hypotheses()
        assert "h1" in active
        assert "h2" not in active

    def test_archived_hypotheses(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.register("h2")
        gmap.supersede("h2", by_id="h1")
        archived = gmap.get_archived_hypotheses()
        assert "h2" in archived
        assert "h1" not in archived

    def test_get_stats(self):
        gmap = HypothesisGalacticMap()
        gmap.register("h1")
        gmap.register("h2")
        gmap.deprecate("h2")
        stats = gmap.get_stats()
        assert stats["total_hypotheses"] == 2
        assert stats["active_count"] == 1
        assert stats["archived_count"] == 1
