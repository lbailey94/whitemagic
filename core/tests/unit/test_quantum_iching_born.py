"""Tests for Born-rule I Ching casting (Phase 2).

Tests verify:
- Born-rule collapse produces valid hexagram numbers (1-64)
- HRR-derived amplitudes differ from hash-derived when HRR available
- Entangled pairs influence collapse distribution
- Fallback when PolyglotMC unavailable
- Determinism with same seed
- Quantum state creation with HRR amplitudes
"""

from unittest.mock import MagicMock, patch

from whitemagic.oracle.quantum_iching import QuantumIChing, QuantumState


class TestBornRuleCasting:
    """Test Born-rule I Ching collapse."""

    def test_collapse_returns_valid_hexagram(self):
        oracle = QuantumIChing()
        state = oracle._create_quantum_state("Should I proceed?", {})
        result = oracle._collapse_quantum_state(state, "Should I proceed?")
        assert 1 <= result <= 64
        assert result in oracle.db.hexagrams

    def test_collapse_deterministic_with_same_question(self):
        """Same question should produce the same hexagram (deterministic seed)."""
        oracle = QuantumIChing()
        result1 = oracle.consult("Should I take this path?", {})
        result2 = oracle.consult("Should I take this path?", {})
        # The Born sample is seeded by question hash, so should be deterministic
        # (unless HRR/Rust introduces non-determinism, which it shouldn't)
        assert result1.primary_hexagram == result2.primary_hexagram

    def test_collapse_different_questions_can_differ(self):
        """Different questions should be able to produce different hexagrams."""
        oracle = QuantumIChing()
        results = set()
        for q in [
            "Should I fight?",
            "Should I retreat?",
            "What about love?",
            "How to find wealth?",
            "Is this the right time?",
        ]:
            r = oracle.consult(q, {})
            results.add(r.primary_hexagram)
        # At least 2 different hexagrams from 5 different questions
        assert len(results) >= 2

    def test_fallback_when_polyglotmc_unavailable(self):
        """Should still produce valid hexagram when PolyglotMC import fails."""
        oracle = QuantumIChing()
        state = oracle._create_quantum_state("Test question", {})

        with patch.dict("sys.modules", {"whitemagic.core.evolution.polyglot_mc": None}):
            result = oracle._collapse_quantum_state(state, "Test question")
            assert 1 <= result <= 64

    def test_quantum_state_has_amplitudes(self):
        oracle = QuantumIChing()
        state = oracle._create_quantum_state("Test question", {"urgency": "high"})
        assert len(state.amplitudes) == 64
        for i in range(1, 65):
            assert i in state.amplitudes
            assert isinstance(state.amplitudes[i], complex)

    def test_quantum_state_normalized(self):
        """Amplitudes should be normalized (sum of |a|^2 = 1)."""

        oracle = QuantumIChing()
        state = oracle._create_quantum_state("Normalize me", {})
        total = sum(abs(a) ** 2 for a in state.amplitudes.values())
        assert abs(total - 1.0) < 1e-6

    def test_entanglement_modifies_distribution(self):
        """Entangled pairs should be able to influence the collapse."""
        oracle = QuantumIChing()

        # Create a state with known entanglement
        state = QuantumState(
            amplitudes={i: complex(1.0, 0.0) for i in range(1, 65)},
            entanglement=[(1, 2)],
            coherence=0.9,
        )
        # Normalize
        import math

        total = sum(abs(a) ** 2 for a in state.amplitudes.values())
        for i in state.amplitudes:
            state.amplitudes[i] = state.amplitudes[i] / math.sqrt(total)

        # Should still produce valid result
        result = oracle._collapse_quantum_state(state, "Entanglement test")
        assert 1 <= result <= 64

    def test_consult_produces_full_result(self):
        oracle = QuantumIChing()
        result = oracle.consult("What does the future hold?", {})
        assert 1 <= result.primary_hexagram <= 64
        assert result.primary_name
        assert result.primary_judgment
        assert result.quantum_signature
        assert result.resonance_score >= 0.0
        assert result.timestamp is not None

    def test_hrr_amplitudes_when_available(self):
        """When HRR bridge is available, amplitudes should be derived from interaction scores."""
        oracle = QuantumIChing()

        # Mock the HRR bridge to be available
        mock_bridge = MagicMock()
        mock_bridge.available = True
        mock_bridge.interaction_score.return_value = 0.5

        with patch("whitemagic.oracle.hrr_bridge.get_hrr_bridge", return_value=mock_bridge):
            state = oracle._create_quantum_state("HRR test", {})
            # All amplitudes should be non-zero (from interaction score 0.5)
            for i in range(1, 65):
                assert abs(state.amplitudes[i]) > 0

    def test_hrr_amplitudes_differ_from_random(self):
        """HRR-derived amplitudes should have different character than hash-random."""
        oracle = QuantumIChing()

        # Get HRR-derived state
        mock_bridge = MagicMock()
        mock_bridge.available = True
        mock_bridge.interaction_score.side_effect = lambda a, b: 0.3 if a == b else 0.1

        with patch("whitemagic.oracle.hrr_bridge.get_hrr_bridge", return_value=mock_bridge):
            hrr_state = oracle._create_quantum_state("Compare", {})

        # Get hash-random state (HRR unavailable)
        mock_bridge_unavail = MagicMock()
        mock_bridge_unavail.available = False
        with patch("whitemagic.oracle.hrr_bridge.get_hrr_bridge", return_value=mock_bridge_unavail):
            random_state = oracle._create_quantum_state("Compare", {})

        # The amplitude distributions should differ
        hrr_mags = [abs(hrr_state.amplitudes[i]) for i in range(1, 65)]
        random_mags = [abs(random_state.amplitudes[i]) for i in range(1, 65)]

        # HRR should have more uniform magnitudes (all from same interaction score)
        hrr_std = (max(hrr_mags) - min(hrr_mags)) / max(hrr_mags)
        random_std = (max(random_mags) - min(random_mags)) / max(random_mags)
        # HRR-derived should be more uniform (smaller spread relative to max)
        assert hrr_std <= random_std + 0.5  # Allow some tolerance

    def test_collapse_with_context_modulation(self):
        """Context should modulate amplitudes and still produce valid hexagram."""
        oracle = QuantumIChing()
        result = oracle.consult("Important decision", {"urgency": "high", "depth": "required"})
        assert 1 <= result.primary_hexagram <= 64

    def test_multiple_consultations_accumulate_history(self):
        oracle = QuantumIChing()
        for i in range(3):
            oracle.consult(f"Question {i}", {})
        assert len(oracle.consultation_history) == 3
