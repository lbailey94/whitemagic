"""Tests for Objective Q — Thermodynamic Resource Allocation."""
from __future__ import annotations

from whitemagic.core.evolution.thermodynamic import (
    ThermodynamicState,
    boltzmann_probabilities,
    boltzmann_select,
)


class TestThermodynamicState:
    def test_defaults(self):
        s = ThermodynamicState()
        assert s.temperature == 1.0
        assert s.cooling_rate == 0.95
        assert s.exploration_phase == "hot"

    def test_cool(self):
        s = ThermodynamicState(temperature=1.0, cooling_rate=0.9)
        s.cool()
        assert abs(s.temperature - 0.9) < 1e-6
        assert s.cycle_count == 1

    def test_cool_respects_min(self):
        s = ThermodynamicState(temperature=0.05, cooling_rate=0.5, min_temperature=0.1)
        s.cool()
        assert s.temperature == 0.1

    def test_reheat(self):
        s = ThermodynamicState(temperature=0.5, reheat_amount=0.3)
        s.reheat(1.0)
        assert abs(s.temperature - 0.8) < 1e-6

    def test_reheat_respects_max(self):
        s = ThermodynamicState(temperature=1.9, reheat_amount=0.3, max_temperature=2.0)
        s.reheat(1.0)
        assert s.temperature == 2.0

    def test_adapt_cooling(self):
        s = ThermodynamicState(temperature=1.0, cooling_rate=0.9)
        s.adapt(discovery_rate=0.5)
        assert s.temperature < 1.0
        assert s.cycle_count == 1

    def test_adapt_faster_cooling_on_decline(self):
        s = ThermodynamicState(temperature=1.0, cooling_rate=0.9)
        s.adapt(discovery_rate=0.8)
        temp_after_increase = s.temperature
        s.adapt(discovery_rate=0.2)  # Discovery drops
        # Should have cooled faster
        assert s.temperature < temp_after_increase * 0.9

    def test_adapt_reheat_on_emergence(self):
        s = ThermodynamicState(temperature=0.3, reheat_amount=0.5)
        s.adapt(discovery_rate=0.1, emergence_signal=0.8)
        assert s.temperature > 0.3

    def test_exploration_phases(self):
        s = ThermodynamicState()
        assert s.exploration_phase == "hot"

        s.temperature = 0.5
        assert s.exploration_phase == "warm"

        s.temperature = 0.1
        assert s.exploration_phase == "cold"


class TestBoltzmannSelect:
    def test_empty(self):
        assert boltzmann_select([], [], 1.0) == []

    def test_single_item(self):
        result = boltzmann_select(["a"], [0.5], 1.0)
        assert result == ["a"]

    def test_selects_best_at_low_temp(self):
        """At low temperature, should almost always pick lowest energy."""
        items = ["bad", "good", "medium"]
        energies = [0.9, 0.1, 0.5]
        # Run many times at low temperature
        selections = {"bad": 0, "good": 0, "medium": 0}
        for _ in range(100):
            result = boltzmann_select(items, energies, temperature=0.01, k=1)
            selections[result[0]] += 1
        # "good" (lowest energy) should dominate
        assert selections["good"] > selections["bad"]
        assert selections["good"] > selections["medium"]

    def test_uniform_at_high_temp(self):
        """At high temperature, selection should be roughly uniform."""
        items = ["a", "b", "c"]
        energies = [0.1, 0.5, 0.9]
        counts = {"a": 0, "b": 0, "c": 0}
        for _ in range(300):
            result = boltzmann_select(items, energies, temperature=100.0, k=1)
            counts[result[0]] += 1
        # At high temp, all should be roughly equal (within 30% of each other)
        values = list(counts.values())
        assert max(values) - min(values) < 120  # Not too skewed

    def test_select_k(self):
        items = ["a", "b", "c", "d", "e"]
        energies = [0.2, 0.4, 0.6, 0.8, 0.1]
        result = boltzmann_select(items, energies, temperature=0.5, k=3)
        assert len(result) == 3
        assert len(set(result)) == 3  # No duplicates


class TestBoltzmannProbabilities:
    def test_empty(self):
        assert boltzmann_probabilities([], 1.0) == []

    def test_sums_to_one(self):
        probs = boltzmann_probabilities([0.1, 0.5, 0.9], 1.0)
        assert abs(sum(probs) - 1.0) < 1e-6

    def test_lower_energy_higher_prob(self):
        probs = boltzmann_probabilities([0.1, 0.9], 0.5)
        assert probs[0] > probs[1]

    def test_uniform_at_high_temp(self):
        probs = boltzmann_probabilities([0.1, 0.9], 100.0)
        assert abs(probs[0] - probs[1]) < 0.1
