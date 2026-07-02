"""Unit tests for neuro-cognitive sensorium."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_sensorium_"))
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

from whitemagic.core.consciousness.neuro_sensorium import NeuroSensorium, get_neuro_sensorium  # noqa: E402


class TestNeuroSensorium:
    def test_compute_sensorium(self):
        s = NeuroSensorium()
        state = s.compute_sensorium()
        assert "thalamic_context" in state
        assert "neuro_da" in state
        assert "composite_novelty" in state
        assert "composite_stability" in state
        assert "composite_attention" in state
        assert "composite_cognitive_load" in state

    def test_citta_enrichment(self):
        s = NeuroSensorium()
        enrichment = s.get_citta_enrichment()
        # All 8 coherence dimensions + 2 composites
        assert "memory_accessibility" in enrichment
        assert "identity_stability" in enrichment
        assert "context_continuity" in enrichment
        assert "relationship_awareness" in enrichment
        assert "temporal_orientation" in enrichment
        assert "capability_awareness" in enrichment
        assert "emotional_attunement" in enrichment
        assert "goal_alignment" in enrichment
        assert "cognitive_load" in enrichment
        assert "novelty" in enrichment
        # All values should be 0-1
        for v in enrichment.values():
            assert 0.0 <= v <= 1.0

    def test_stats(self):
        s = NeuroSensorium()
        s.compute_sensorium()
        stats = s.stats()
        assert "total_updates" in stats
        assert stats["total_updates"] >= 1

    def test_singleton(self):
        s1 = get_neuro_sensorium()
        s2 = get_neuro_sensorium()
        assert s1 is s2

    def test_signals_are_numeric(self):
        s = NeuroSensorium()
        state = s.compute_sensorium()
        assert isinstance(state["neuro_da"], (int, float))
        assert isinstance(state["composite_novelty"], (int, float))
        assert 0.0 <= state["neuro_da"] <= 1.0
