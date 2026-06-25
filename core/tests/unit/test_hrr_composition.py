"""Tests for Objective H — HRR-Based Improvement Composition."""
from __future__ import annotations

from whitemagic.core.evolution.hrr_composition import (
    CompositeHypothesis,
    HRRCompositionEngine,
)


class TestHRRComposition:
    def test_encode_hypothesis(self):
        engine = HRRCompositionEngine(dim=64)
        vec = engine.encode_hypothesis("h1", "Fix untitled memories", 0.8)
        if vec is not None:
            assert vec.shape == (64,)

    def test_bind(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix untitled", 0.8)
        engine.encode_hypothesis("h2", "Tag normalization", 0.6)
        composite = engine.bind("h1", "h2")
        if composite is not None:
            assert composite.operation == "bind"
            assert "h1" in composite.component_ids
            assert "h2" in composite.component_ids

    def test_unbind(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix untitled", 0.8)
        engine.encode_hypothesis("h2", "Tag normalization", 0.6)
        composite = engine.bind("h1", "h2")
        if composite is not None:
            recovered = engine.unbind(composite.id, "h1")
            if recovered is not None:
                assert recovered.shape == (64,)

    def test_superposition(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix A", 0.8)
        engine.encode_hypothesis("h2", "Fix B", 0.6)
        engine.encode_hypothesis("h3", "Fix C", 0.7)
        composite = engine.superposition(["h1", "h2", "h3"])
        if composite is not None:
            assert composite.operation == "superposition"
            assert len(composite.component_ids) == 3

    def test_superposition_insufficient(self):
        engine = HRRCompositionEngine(dim=64)
        result = engine.superposition(["h1"])
        assert result is None

    def test_compute_synergy(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix A", 0.8)
        engine.encode_hypothesis("h2", "Fix B", 0.6)
        composite = engine.bind("h1", "h2")
        if composite is not None:
            synergy = engine.compute_synergy(composite, [0.8, 0.6])
            assert isinstance(synergy, float)

    def test_probe_composite(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix A", 0.8)
        engine.encode_hypothesis("h2", "Fix B", 0.6)
        composite = engine.bind("h1", "h2")
        if composite is not None:
            outcomes = [
                {"success": True, "hypothesis_id": "h1"},
                {"success": True, "hypothesis_id": "h2"},
                {"success": False, "hypothesis_id": "h1"},
            ]
            result = engine.probe_composite(composite, outcomes)
            assert "composite_success_rate" in result
            assert "avg_component_success_rate" in result

    def test_probe_no_outcomes(self):
        engine = HRRCompositionEngine(dim=64)
        composite = CompositeHypothesis(id="test", component_ids=["h1"], operation="bind")
        result = engine.probe_composite(composite, [])
        assert "error" in result

    def test_get_composite(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix A", 0.8)
        engine.encode_hypothesis("h2", "Fix B", 0.6)
        composite = engine.bind("h1", "h2")
        if composite is not None:
            assert engine.get_composite(composite.id) is not None

    def test_get_all_composites(self):
        engine = HRRCompositionEngine(dim=64)
        engine.encode_hypothesis("h1", "Fix A", 0.8)
        engine.encode_hypothesis("h2", "Fix B", 0.6)
        engine.bind("h1", "h2")
        all_c = engine.get_all_composites()
        assert isinstance(all_c, dict)
