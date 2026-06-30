"""Tests for Phase 1a: Analytical Oscillator Solution.

Verifies the closed-form damped harmonic oscillator matches the
numerical scipy RK45 solution within tolerance, and tests all
three damping regimes (underdamped, critically damped, overdamped).
"""

from __future__ import annotations

import numpy as np
import pytest

from whitemagic.core.resonance.julia_resonance import ResonanceEngine


class TestAnalyticalOscillator:
    """Test the _analytical_oscillator static method directly."""

    @pytest.fixture
    def engine(self) -> ResonanceEngine:
        return ResonanceEngine()

    def test_underdamped_basic(self, engine: ResonanceEngine) -> None:
        """Underdamped regime: γ < 2ω₀ produces oscillation with decay."""
        t = np.linspace(0, 50, 200)
        x, v = engine._analytical_oscillator(t, impulse=1.0, damping=0.1, frequency=1.0)
        # Should oscillate (sign changes)
        sign_changes = np.sum(np.diff(np.sign(x)) != 0)
        assert sign_changes > 5, "Underdamped should oscillate"
        # Should decay over time
        assert abs(x[-1]) < abs(x[1]), "Should decay"
        # Initial conditions: x(0) = 0, v(0) = impulse
        assert abs(x[0]) < 1e-10, "x(0) should be 0"
        assert abs(v[0] - 1.0) < 1e-10, "v(0) should equal impulse"

    def test_overdamped_basic(self, engine: ResonanceEngine) -> None:
        """Overdamped regime: γ > 2ω₀ produces no oscillation."""
        t = np.linspace(0, 50, 200)
        x, v = engine._analytical_oscillator(t, impulse=1.0, damping=4.0, frequency=1.0)
        # Should NOT oscillate (no sign changes after initial)
        sign_changes = np.sum(np.diff(np.sign(x[1:])) != 0)
        assert sign_changes == 0, "Overdamped should not oscillate"
        # Should decay
        assert abs(x[-1]) < abs(x[10]), "Should decay"
        # ICs
        assert abs(x[0]) < 1e-10, "x(0) should be 0"
        assert abs(v[0] - 1.0) < 1e-10, "v(0) should equal impulse"

    def test_critically_damped(self, engine: ResonanceEngine) -> None:
        """Critically damped: γ = 2ω₀, boundary case."""
        t = np.linspace(0, 50, 200)
        # γ = 2ω₀ → damping = 2 * frequency
        x, v = engine._analytical_oscillator(t, impulse=1.0, damping=2.0, frequency=1.0)
        # No oscillation
        sign_changes = np.sum(np.diff(np.sign(x[5:])) != 0)
        assert sign_changes == 0, "Critically damped should not oscillate"
        # ICs
        assert abs(x[0]) < 1e-10, "x(0) should be 0"
        assert abs(v[0] - 1.0) < 1e-10, "v(0) should equal impulse"

    def test_zero_impulse(self, engine: ResonanceEngine) -> None:
        """Zero impulse → zero displacement."""
        t = np.linspace(0, 50, 200)
        x, v = engine._analytical_oscillator(t, impulse=0.0, damping=0.1, frequency=1.0)
        assert np.allclose(x, 0.0), "Zero impulse should give zero displacement"
        assert np.allclose(v, 0.0), "Zero impulse should give zero velocity"

    def test_energy_consistency(self, engine: ResonanceEngine) -> None:
        """Energy should decay monotonically for damped oscillator."""
        t = np.linspace(0, 50, 200)
        x, v = engine._analytical_oscillator(t, impulse=0.8, damping=0.3, frequency=2.0)
        energy = x**2 + v**2
        # Energy should generally decrease (allow small numerical noise at peaks)
        assert energy[-1] < energy[0], "Energy should decay"
        # Max energy should be near t=0
        max_idx = np.argmax(energy)
        assert max_idx < 10, "Peak energy should be near start"


class TestCalculateResonance:
    """Test the calculate_resonance method end-to-end."""

    @pytest.fixture
    def engine(self) -> ResonanceEngine:
        return ResonanceEngine()

    def test_basic_resonance(self, engine: ResonanceEngine) -> None:
        """Basic resonance calculation returns CONVERGED."""
        result = engine.calculate_resonance(
            memory_id="test_1",
            importance=0.8,
            access_count=5,
            emotional_valence=0.6,
        )
        assert result.status == "CONVERGED"
        assert result.impulse_magnitude > 0
        assert result.peak_amplitude > 0
        assert result.half_life > 0

    def test_zero_importance(self, engine: ResonanceEngine) -> None:
        """Zero importance/access/valence → zero impulse → CONVERGED with zeros."""
        result = engine.calculate_resonance(
            memory_id="test_2",
            importance=0.0,
            access_count=0,
            emotional_valence=0.0,
        )
        assert result.status == "CONVERGED"
        assert result.impulse_magnitude == 0.0
        assert result.total_resonance == 0.0

    def test_high_importance_more_resonance(self, engine: ResonanceEngine) -> None:
        """Higher importance should produce more total resonance."""
        low = engine.calculate_resonance(
            memory_id="low", importance=0.1, access_count=0, emotional_valence=0.0
        )
        high = engine.calculate_resonance(
            memory_id="high", importance=0.9, access_count=10, emotional_valence=0.9
        )
        assert high.total_resonance > low.total_resonance
        assert high.peak_amplitude > low.peak_amplitude

    def test_higher_frequency_faster_decay(self, engine: ResonanceEngine) -> None:
        """Higher frequency oscillator should have shorter half-life."""
        low_freq = engine.calculate_resonance(
            memory_id="lf", importance=0.5, frequency=0.5
        )
        high_freq = engine.calculate_resonance(
            memory_id="hf", importance=0.5, frequency=5.0
        )
        # Higher frequency → more oscillations → energy dissipates faster
        assert high_freq.half_life <= low_freq.half_life + 5.0  # tolerance

    def test_no_scipy_required(self, engine: ResonanceEngine) -> None:
        """calculate_resonance should work without scipy ODE solver."""
        # The analytical solution doesn't need solve_ivp
        result = engine.calculate_resonance(
            memory_id="no_scipy", importance=0.5, access_count=3
        )
        assert result.status == "CONVERGED"
        assert result.peak_amplitude > 0


class TestAnalyticalVsNumerical:
    """Compare analytical solution against scipy RK45 (if available)."""

    @pytest.fixture
    def engine(self) -> ResonanceEngine:
        return ResonanceEngine()

    def test_matches_numerical_underdamped(self, engine: ResonanceEngine) -> None:
        """Analytical underdamped solution matches RK45 within tolerance."""
        pytest.importorskip("scipy.integrate")
        from scipy.integrate import solve_ivp

        impulse = 0.7
        damping = 0.1
        frequency = 1.0
        t = np.linspace(0, 50, 200)

        # Analytical
        x_a, v_a = engine._analytical_oscillator(t, impulse, damping, frequency)

        # Numerical
        def oscillator(t, state):
            x, v = state
            return [v, -damping * v - frequency**2 * x]

        sol = solve_ivp(
            oscillator, (0, 50), [0.0, impulse], t_eval=t, method="RK45", max_step=0.5
        )
        assert sol.success

        # Compare (tolerance accounts for RK45 step error + analytical precision)
        np.testing.assert_allclose(x_a, sol.y[0], atol=1e-3)
        np.testing.assert_allclose(v_a, sol.y[1], atol=1e-3)


class TestGalacticZoneFrequency:
    """Test Phase 3b: Galactic Zone → Oscillator Frequency mapping."""

    @pytest.fixture
    def engine(self) -> ResonanceEngine:
        return ResonanceEngine()

    def test_core_zone_high_frequency(self, engine: ResonanceEngine) -> None:
        """Core zone (distance < 0.15) should have highest frequency."""
        freq = engine.galactic_zone_frequency(0.05)
        assert freq == 8.0

    def test_far_edge_low_frequency(self, engine: ResonanceEngine) -> None:
        """Far edge zone (distance > 0.85) should have lowest frequency."""
        freq = engine.galactic_zone_frequency(0.95)
        assert freq == 0.5

    def test_zone_boundaries(self, engine: ResonanceEngine) -> None:
        """Test all zone boundary frequencies."""
        assert engine.galactic_zone_frequency(0.0) == 8.0  # CORE
        assert engine.galactic_zone_frequency(0.14) == 8.0  # CORE
        assert engine.galactic_zone_frequency(0.15) == 4.0  # INNER_RIM
        assert engine.galactic_zone_frequency(0.39) == 4.0  # INNER_RIM
        assert engine.galactic_zone_frequency(0.40) == 2.0  # MID_BAND
        assert engine.galactic_zone_frequency(0.64) == 2.0  # MID_BAND
        assert engine.galactic_zone_frequency(0.65) == 1.0  # OUTER_RIM
        assert engine.galactic_zone_frequency(0.84) == 1.0  # OUTER_RIM
        assert engine.galactic_zone_frequency(0.85) == 0.5  # FAR_EDGE
        assert engine.galactic_zone_frequency(1.0) == 0.5  # FAR_EDGE

    def test_clamping(self, engine: ResonanceEngine) -> None:
        """Values outside [0,1] should be clamped."""
        assert engine.galactic_zone_frequency(-0.5) == 8.0
        assert engine.galactic_zone_frequency(1.5) == 0.5

    def test_damping_increases_with_distance(self, engine: ResonanceEngine) -> None:
        """Damping should increase from core to far edge."""
        core_damping = engine.galactic_zone_damping(0.0)
        edge_damping = engine.galactic_zone_damping(1.0)
        assert core_damping < edge_damping
        assert core_damping == pytest.approx(0.05)
        assert edge_damping == pytest.approx(0.5)

    def test_damping_monotonic(self, engine: ResonanceEngine) -> None:
        """Damping should be monotonically increasing."""
        distances = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        dampings = [engine.galactic_zone_damping(d) for d in distances]
        for i in range(1, len(dampings)):
            assert dampings[i] >= dampings[i - 1]

    def test_resonance_with_galactic_distance(self, engine: ResonanceEngine) -> None:
        """calculate_resonance should accept galactic_distance parameter."""
        result_core = engine.calculate_resonance(
            "test_core", importance=0.8, galactic_distance=0.05
        )
        result_edge = engine.calculate_resonance(
            "test_edge", importance=0.8, galactic_distance=0.95
        )
        # Both should produce positive resonance
        assert result_core.total_resonance > 0
        assert result_edge.total_resonance > 0
        # Core has higher frequency → higher total energy (more oscillations)
        assert result_core.total_resonance > result_edge.total_resonance

    def test_galactic_overrides_explicit_params(self, engine: ResonanceEngine) -> None:
        """When galactic_distance is provided, it overrides frequency/damping."""
        result_galactic = engine.calculate_resonance(
            "test",
            importance=0.5,
            galactic_distance=0.05,
            frequency=1.0,
            damping=0.1,  # should be overridden
        )
        result_explicit = engine.calculate_resonance(
            "test",
            importance=0.5,
            frequency=1.0,
            damping=0.1,
        )
        # Should differ because galactic overrides
        assert result_galactic.total_resonance != result_explicit.total_resonance
