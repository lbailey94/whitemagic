"""Tests for HRR → Oracle Synthesis bridge (Phase 1).

Tests verify:
- HRRBridge graceful degradation when Rust unavailable
- synergy_for returns correct hexagrams
- OracleSynthesizer includes hrr_resonances in output
- interaction_score symmetry
- superpose_hexagrams returns valid vector
"""


from whitemagic.oracle.hrr_bridge import (
    HRRBridge,
    _get_py_vectors,
    _py_cosine_sim,
    get_hrr_bridge,
)
from whitemagic.oracle.wisdom_synthesis import OracleSynthesizer, SynthesisResult


class TestHRRBridge:
    """Test the HRR bridge directly."""

    def test_bridge_instantiation(self):
        bridge = HRRBridge()
        assert bridge is not None
        assert isinstance(bridge.available, bool)

    def test_synergy_for_returns_list(self):
        bridge = HRRBridge()
        result = bridge.synergy_for(32, threshold=0.3)
        assert isinstance(result, list)
        for item in result:
            assert "hexagram" in item
            assert "similarity" in item
            assert 1 <= item["hexagram"] <= 64
            assert item["hexagram"] != 32  # Should not include self

    def test_synergy_for_sorted_descending(self):
        bridge = HRRBridge()
        result = bridge.synergy_for(1, threshold=-1.0)  # Get all
        sims = [r["similarity"] for r in result]
        assert sims == sorted(sims, reverse=True)

    def test_interaction_score_returns_float(self):
        bridge = HRRBridge()
        score = bridge.interaction_score(1, 2)
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0

    def test_interaction_score_symmetry(self):
        bridge = HRRBridge()
        score_12 = bridge.interaction_score(1, 2)
        score_21 = bridge.interaction_score(2, 1)
        assert abs(score_12 - score_21) < 1e-6

    def test_interaction_score_self_is_one(self):
        bridge = HRRBridge()
        score = bridge.interaction_score(32, 32)
        assert abs(score - 1.0) < 1e-6

    def test_superpose_returns_vector(self):
        bridge = HRRBridge()
        vec = bridge.superpose_hexagrams(1, 2)
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_hexagram_vector_returns_vector(self):
        bridge = HRRBridge()
        vec = bridge.hexagram_vector(1)
        assert isinstance(vec, list)
        assert len(vec) > 0

    def test_interaction_matrix_returns_4096(self):
        bridge = HRRBridge()
        matrix = bridge.interaction_matrix()
        assert len(matrix) == 64 * 64

    def test_synergy_threshold_filters(self):
        bridge = HRRBridge()
        high = bridge.synergy_for(32, threshold=0.8)
        low = bridge.synergy_for(32, threshold=0.0)
        assert len(high) <= len(low)

    def test_get_hrr_bridge_singleton(self):
        b1 = get_hrr_bridge()
        b2 = get_hrr_bridge()
        assert b1 is b2

    def test_python_fallback_cosine_sim(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert abs(_py_cosine_sim(a, b) - 1.0) < 1e-6

        c = [0.0, 1.0, 0.0]
        assert abs(_py_cosine_sim(a, c)) < 1e-6

    def test_python_fallback_vectors(self):
        vectors = _get_py_vectors()
        assert len(vectors) == 64
        for kw in range(1, 65):
            assert kw in vectors
            assert len(vectors[kw]) > 0

    def test_synergy_for_invalid_hexagram(self):
        """Should handle invalid hexagram numbers gracefully."""
        bridge = HRRBridge()
        result = bridge.synergy_for(999, threshold=0.3)
        assert isinstance(result, list)


class TestOracleSynthesizerHRR:
    """Test that OracleSynthesizer includes HRR resonances."""

    def _make_oracle_output(self, hexagram_num=32):
        return {
            "sign": "Leo",
            "element": "fire",
            "modality": "fixed",
            "phase": "yang",
            "wu_xing": "fire",
            "iching_name": "Duration",
            "iching_number": hexagram_num,
            "iching_judgment": "Duration succeeds through constancy.",
            "iching_guidance": "Persevere in right action.",
            "ifa_odu": "Ogbe",
            "ifa_wisdom": "Patience brings blessings.",
            "ifa_ire": "Good fortune through persistence",
            "ifa_osogbo": "Avoid haste",
        }

    def test_synthesize_includes_hrr_resonances(self):
        output = self._make_oracle_output(32)
        result = OracleSynthesizer().synthesize(output)
        assert hasattr(result, "hrr_resonances")
        assert isinstance(result.hrr_resonances, list)

    def test_synthesize_includes_primary_hexagram(self):
        output = self._make_oracle_output(32)
        result = OracleSynthesizer().synthesize(output)
        assert result.primary_hexagram == 32

    def test_synthesize_without_hexagram_number(self):
        """Should still work without iching_number — hrr_resonances empty."""
        output = self._make_oracle_output()
        del output["iching_number"]
        result = OracleSynthesizer().synthesize(output)
        assert result.hrr_resonances == []
        assert result.primary_hexagram is None

    def test_synthesize_with_primary_hexagram_key(self):
        """Should also check 'primary_hexagram' key as fallback."""
        output = self._make_oracle_output()
        del output["iching_number"]
        output["primary_hexagram"] = 50
        result = OracleSynthesizer().synthesize(output)
        assert result.primary_hexagram == 50
        assert isinstance(result.hrr_resonances, list)

    def test_synthesize_hrr_resonances_have_hexagram_and_similarity(self):
        output = self._make_oracle_output(1)
        result = OracleSynthesizer().synthesize(output)
        for r in result.hrr_resonances:
            assert "hexagram" in r
            assert "similarity" in r

    def test_synthesize_result_is_synthesis_result(self):
        output = self._make_oracle_output()
        result = OracleSynthesizer().synthesize(output)
        assert isinstance(result, SynthesisResult)
        assert result.unified_message
        assert result.narrative is not None
        assert result.resonances is not None
