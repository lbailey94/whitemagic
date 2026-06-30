"""Tests for Neurotransmitter Vector."""

from whitemagic.core.monitoring.neurotransmitter_vector import (
    NeurotransmitterVector,
)


class TestNeurotransmitterVector:
    """Test the neurotransmitter vector signal collection."""

    def test_cold_start_baseline(self):
        """Fresh vector should report baseline values."""
        nt = NeurotransmitterVector()
        snap = nt.snapshot()
        assert snap.dopamine == 0.5
        assert snap.cortisol == 0.5
        assert snap.serotonin == 0.5
        assert snap.dominant in (
            "baseline",
            "dopamine",
        )  # dopamine is first in dict when all equal

    def test_success_increases_dopamine(self):
        """Successful tool calls should increase dopamine."""
        nt = NeurotransmitterVector()
        for _ in range(20):
            nt.record_tool_call(success=True)
        snap = nt.snapshot()
        assert snap.dopamine > 0.5

    def test_error_increases_cortisol(self):
        """Failed tool calls should increase cortisol."""
        nt = NeurotransmitterVector()
        nt.record_tool_call(success=False, result={"tool": "test", "status": "error"})
        snap = nt.snapshot()
        assert snap.cortisol > 0.5

    def test_circuit_breaker_trip_spikes_cortisol(self):
        """Circuit breaker trips should spike cortisol."""
        nt = NeurotransmitterVector()
        nt.record_circuit_breaker_trip()
        snap = nt.snapshot()
        assert snap.cortisol >= 0.9

    def test_creative_bridge_boosts_glutamate(self):
        """Low-confidence creative bridges should boost glutamate."""
        nt = NeurotransmitterVector()
        nt.record_creative_bridge(confidence=0.2)
        snap = nt.snapshot()
        assert snap.glutamate > 0.5

    def test_snapshot_is_json_safe(self):
        """Snapshot should be JSON-serializable."""
        import json

        nt = NeurotransmitterVector()
        nt.record_tool_call(success=True)
        snap = nt.snapshot()
        data = snap.to_dict()
        json.dumps(data)
        assert "timestamp" in data

    def test_interpretation_generated(self):
        """Interpretation should be non-empty."""
        nt = NeurotransmitterVector()
        for _ in range(5):
            nt.record_tool_call(
                success=False, result={"tool": "test", "status": "error"}
            )
        snap = nt.snapshot()
        assert len(snap.interpretation) > 0
        assert (
            "stressed" in snap.interpretation.lower()
            or "baseline" in snap.interpretation.lower()
        )

    def test_singleton(self):
        """get_neurotransmitter_vector should return the same instance."""
        from whitemagic.core.monitoring.neurotransmitter_vector import (
            get_neurotransmitter_vector,
        )

        a = get_neurotransmitter_vector()
        b = get_neurotransmitter_vector()
        assert a is b
