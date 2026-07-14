"""Unit tests for citta introspection MCP tools (vector, trajectory, coherence)."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_cit_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.consciousness.citta_cycle import get_citta_cycle  # noqa: E402
from whitemagic.tools.handlers.neuro_cognitive import (  # noqa: E402
    handle_citta_coherence,
    handle_citta_trajectory,
    handle_citta_vector,
)


class TestCittaVectorTool:
    def test_vector_no_moments(self):
        cycle = get_citta_cycle()
        cycle.reset()
        result = handle_citta_vector()
        assert result["status"] == "success"
        assert result["vector"] is None

    def test_vector_with_moment(self):
        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(
            gana="test", coherence=0.85, emotional_tone="neutral",
            neuro_signals={},
        )
        result = handle_citta_vector()
        assert result["status"] == "success"
        assert result["vector"] is not None
        assert "components" in result["vector"]
        assert "coherence_dims" in result
        assert "depth_layer" in result
        assert "valence" in result
        assert "arousal" in result
        assert "overall_coherence" in result
        assert result["overall_coherence"] > 0.8

    def test_vector_has_all_8_coherence_dims(self):
        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(gana="test", coherence=0.7, emotional_tone="neutral", neuro_signals={})
        result = handle_citta_vector()
        dims = result["coherence_dims"]
        assert len(dims) == 8
        assert "memory_accessibility" in dims
        assert "goal_alignment" in dims


class TestCittaTrajectoryTool:
    def test_trajectory_empty(self):
        cycle = get_citta_cycle()
        cycle.reset()
        result = handle_citta_trajectory()
        assert result["status"] == "success"
        assert result["trajectory_length"] == 0
        assert result["vectors"] == []

    def test_trajectory_with_vectors(self):
        cycle = get_citta_cycle()
        cycle.reset()
        for i in range(5):
            cycle.advance(
                gana="test", coherence=0.5 + i * 0.1, emotional_tone="neutral",
                neuro_signals={},
            )
        result = handle_citta_trajectory()
        assert result["status"] == "success"
        assert result["trajectory_length"] == 5
        assert len(result["vectors"]) == 5
        assert len(result["velocities"]) == 4  # 5 vectors = 4 velocities
        assert result["avg_velocity"] >= 0.0

    def test_trajectory_limit(self):
        cycle = get_citta_cycle()
        cycle.reset()
        for i in range(10):
            cycle.advance(gana="test", coherence=0.5, emotional_tone="neutral", neuro_signals={})
        result = handle_citta_trajectory(limit=3)
        assert len(result["vectors"]) == 3


class TestCittaCoherenceTool:
    def test_coherence_empty_stream(self):
        cycle = get_citta_cycle()
        cycle.reset()
        result = handle_citta_coherence()
        assert result["status"] == "success"
        assert result["overall_coherence"] == 1.0  # Default
        assert result["per_dimension"] == {}
        assert "dharma_conservative_mode" in result

    def test_coherence_with_moments(self):
        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(gana="test", coherence=0.8, emotional_tone="neutral", neuro_signals={})
        cycle.advance(gana="test", coherence=0.8, emotional_tone="neutral", neuro_signals={})
        result = handle_citta_coherence()
        assert result["status"] == "success"
        assert result["overall_coherence"] > 0.7
        assert len(result["per_dimension"]) == 8
        assert "memory_accessibility" in result["per_dimension"]
        assert "coherence_drift" in result
        assert "stream_length" in result
        assert result["stream_length"] == 2

    def test_coherence_includes_dharma_status(self):
        cycle = get_citta_cycle()
        cycle.reset()
        cycle.advance(gana="test", coherence=0.3, emotional_tone="neutral", neuro_signals={})
        cycle.advance(gana="test", coherence=0.3, emotional_tone="neutral", neuro_signals={})
        result = handle_citta_coherence()
        assert "dharma_conservative_mode" in result
        assert isinstance(result["dharma_conservative_mode"], bool)
