"""Tests for Universal HRR Encoding (Phase 5).

Tests verify:
- SymbolicHRR encodes all known symbols
- Resonance computation between symbols
- alchemical_phase replaces hardcoded map
- modality_dynamic replaces hardcoded map
- cross_system_resonance discovers unexpected connections
- Deterministic encoding (same symbol → same vector)
"""

from whitemagic.oracle.symbolic_hrr import (
    SymbolicHRR,
    _hash_seed,
    get_symbolic_hrr,
)


class TestSymbolicHRR:
    """Test the universal HRR encoding."""

    def test_get_vector_deterministic(self):
        shrr = SymbolicHRR()
        v1 = shrr.get_vector(SymbolicHRR.WUXING, "fire")
        v2 = shrr.get_vector(SymbolicHRR.WUXING, "fire")
        assert v1 == v2

    def test_get_vector_different_symbols_differ(self):
        shrr = SymbolicHRR()
        v1 = shrr.get_vector(SymbolicHRR.WUXING, "fire")
        v2 = shrr.get_vector(SymbolicHRR.WUXING, "water")
        assert v1 != v2

    def test_get_vector_unknown_symbol(self):
        """Unknown symbols should be dynamically encoded."""
        shrr = SymbolicHRR()
        v = shrr.get_vector("custom_ns", "unknown_symbol")
        assert len(v) > 0
        # Should be deterministic
        assert v == shrr.get_vector("custom_ns", "unknown_symbol")

    def test_resonance_self_is_one(self):
        shrr = SymbolicHRR()
        res = shrr.resonance(SymbolicHRR.WUXING, "fire", SymbolicHRR.WUXING, "fire")
        assert abs(res - 1.0) < 1e-6

    def test_resonance_returns_float(self):
        shrr = SymbolicHRR()
        res = shrr.resonance(SymbolicHRR.WUXING, "fire", SymbolicHRR.ZODIAC, "leo")
        assert isinstance(res, float)
        assert -1.0 <= res <= 1.0

    def test_top_resonances_returns_sorted(self):
        shrr = SymbolicHRR()
        results = shrr.top_resonances(SymbolicHRR.WUXING, "fire", k=5)
        assert len(results) <= 5
        resonances = [r["resonance"] for r in results]
        assert resonances == sorted(resonances, reverse=True)

    def test_top_resonances_filtered_by_namespace(self):
        shrr = SymbolicHRR()
        results = shrr.top_resonances(
            SymbolicHRR.WUXING, "fire",
            target_namespace=SymbolicHRR.ALCHEMY,
            k=5,
        )
        for r in results:
            assert r["namespace"] == SymbolicHRR.ALCHEMY

    def test_top_resonances_threshold(self):
        shrr = SymbolicHRR()
        high = shrr.top_resonances(SymbolicHRR.WUXING, "fire", threshold=0.5, k=20)
        for r in high:
            assert r["resonance"] > 0.5

    def test_alchemical_phase_returns_string(self):
        shrr = SymbolicHRR()
        phase = shrr.alchemical_phase("fire")
        assert isinstance(phase, str)
        assert len(phase) > 10

    def test_alchemical_phase_all_wuxing(self):
        shrr = SymbolicHRR()
        for element in ["wood", "fire", "earth", "metal", "water"]:
            phase = shrr.alchemical_phase(element)
            assert isinstance(phase, str)
            assert len(phase) > 5

    def test_modality_dynamic_returns_string(self):
        shrr = SymbolicHRR()
        desc = shrr.modality_dynamic("cardinal")
        assert isinstance(desc, str)
        assert len(desc) > 10

    def test_modality_dynamic_all_modalities(self):
        shrr = SymbolicHRR()
        for mod in ["cardinal", "fixed", "mutable"]:
            desc = shrr.modality_dynamic(mod)
            assert isinstance(desc, str)
            assert len(desc) > 5

    def test_cross_system_resonance(self):
        shrr = SymbolicHRR()
        oracle_output = {
            "wu_xing": "fire",
            "sign": "leo",
            "iching_number": 30,
            "ifa_odu": "ogbe",
        }
        resonances = shrr.cross_system_resonance(oracle_output)
        assert isinstance(resonances, list)
        for r in resonances:
            assert "pair" in r
            assert "resonance" in r
            assert "description" in r

    def test_cross_system_resonance_empty_output(self):
        shrr = SymbolicHRR()
        resonances = shrr.cross_system_resonance({})
        assert resonances == []

    def test_cross_system_resonance_with_tarot(self):
        shrr = SymbolicHRR()
        oracle_output = {
            "wu_xing": "water",
            "tarot_cards": [{"name": "The Star"}],
        }
        resonances = shrr.cross_system_resonance(oracle_output)
        assert isinstance(resonances, list)

    def test_cross_system_resonance_sorted_by_abs(self):
        shrr = SymbolicHRR()
        oracle_output = {
            "wu_xing": "fire",
            "sign": "leo",
            "iching_number": 30,
            "ifa_odu": "ogbe",
        }
        resonances = shrr.cross_system_resonance(oracle_output)
        if len(resonances) > 1:
            abs_vals = [abs(r["resonance"]) for r in resonances]
            assert abs_vals == sorted(abs_vals, reverse=True)

    def test_get_symbolic_hrr_singleton(self):
        s1 = get_symbolic_hrr()
        s2 = get_symbolic_hrr()
        assert s1 is s2

    def test_all_wuxing_symbols_encoded(self):
        shrr = SymbolicHRR()
        for element in ["wood", "fire", "earth", "metal", "water"]:
            v = shrr.get_vector(SymbolicHRR.WUXING, element)
            assert len(v) == 64

    def test_all_zodiac_signs_encoded(self):
        shrr = SymbolicHRR()
        for sign in ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
                      "libra", "scorpio", "sagittarius", "capricorn",
                      "aquarius", "pisces"]:
            v = shrr.get_vector(SymbolicHRR.ZODIAC, sign)
            assert len(v) == 64

    def test_all_iching_hexagrams_encoded(self):
        shrr = SymbolicHRR()
        for kw in range(1, 65):
            v = shrr.get_vector(SymbolicHRR.ICHING, kw)
            assert len(v) == 64

    def test_hash_seed_deterministic(self):
        s1 = _hash_seed("fire", "wuxing")
        s2 = _hash_seed("fire", "wuxing")
        assert s1 == s2

    def test_hash_seed_different_symbols(self):
        s1 = _hash_seed("fire", "wuxing")
        s2 = _hash_seed("water", "wuxing")
        assert s1 != s2
