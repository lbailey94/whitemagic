"""Thermodynamic Resource Allocation (Objective Q).

Models improvement selection as a thermodynamic system with simulated annealing.

- Temperature = exploration rate (how often we pick non-greedy improvements)
- Energy = predicted impact (lower energy = better improvement)
- Entropy = uncertainty in the improvement landscape
- Selection probability: P(select i) ∝ exp(-E_i / T) (Boltzmann distribution)

Cooling schedule:
- Start hot (T high → explore widely)
- Cool when discovery rate drops (fewer novel improvements per cycle → T decreases)
- Reheat when emergence engine detects new patterns (T jumps back up)

T_{t+1} = T_t · cooling_rate + emergence_signal · reheat_amount
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    from whitemagic.core.evolution._rust_bridge import call as _rust_call
except ImportError:
    _rust_call = None


@dataclass
class ThermodynamicState:
    """State of the thermodynamic selection system."""

    temperature: float = 1.0  # Current temperature T
    cooling_rate: float = 0.95  # Multiplicative cooling per cycle
    reheat_amount: float = 0.3  # Additive reheat on emergence signal
    min_temperature: float = 0.01  # Minimum temperature (never fully cold)
    max_temperature: float = 2.0  # Maximum temperature (cap)
    cycle_count: int = 0  # Number of cycles elapsed
    discovery_rate_history: list[float] = field(default_factory=list)

    def cool(self) -> None:
        """Apply one step of the cooling schedule."""
        self.temperature = max(
            self.min_temperature,
            self.temperature * self.cooling_rate,
        )
        self.cycle_count += 1

    def reheat(self, emergence_signal: float = 1.0) -> None:
        """Reheat based on emergence signal.

        Args:
            emergence_signal: Strength of emergence detection (0-1).
        """
        self.temperature = min(
            self.max_temperature,
            self.temperature + self.reheat_amount * emergence_signal,
        )

    def adapt(self, discovery_rate: float, emergence_signal: float = 0.0) -> None:
        """Adapt temperature based on discovery rate and emergence signal.

        T_{t+1} = T_t · cooling_rate + emergence_signal · reheat_amount

        If discovery rate is dropping, cool faster.
        If emergence is detected, reheat.

        Args:
            discovery_rate: Rate of novel improvements found per cycle.
            emergence_signal: Strength of emergence detection (0-1).
        """
        self.discovery_rate_history.append(discovery_rate)

        # Adaptive cooling: if discovery rate is dropping, cool faster
        if len(self.discovery_rate_history) >= 2:
            recent = self.discovery_rate_history[-1]
            previous = self.discovery_rate_history[-2]
            if recent < previous:
                # Discovery slowing — cool faster
                rate = self.cooling_rate**2
            else:
                rate = self.cooling_rate
        else:
            rate = self.cooling_rate

        self.temperature = max(
            self.min_temperature,
            self.temperature * rate,
        )

        # Reheat if emergence detected
        if emergence_signal > 0:
            self.reheat(emergence_signal)

        self.cycle_count += 1

    @property
    def exploration_phase(self) -> str:
        """Classify current phase: 'hot', 'warm', or 'cold'."""
        if self.temperature > 0.7:
            return "hot"  # Exploration phase
        elif self.temperature > 0.2:
            return "warm"  # Transition
        else:
            return "cold"  # Exploitation phase


def boltzmann_select(
    items: list[Any],
    energies: list[float],
    temperature: float,
    k: int = 1,
) -> list[Any]:
    """Select items using Boltzmann (softmax) distribution.

    P(select i) ∝ exp(-E_i / T)

    Lower energy (higher impact) items are more likely to be selected,
    but at high temperature the distribution flattens (more exploration).

    Args:
        items: List of items to select from.
        energies: List of energy values (lower = better). Must be same length.
        temperature: Temperature T — higher = more random.
        k: Number of items to select.

    Returns:
        List of k selected items.
    """
    if not items:
        return []
    if len(items) == 1:
        return items[:k]

    # Compute Boltzmann probabilities
    # Use max energy as reference to avoid overflow
    max_e = max(energies)
    weights = [math.exp(-(e - max_e) / max(temperature, 1e-10)) for e in energies]
    total = sum(weights)
    probs = [w / total for w in weights]

    # Weighted selection without replacement
    selected = []
    remaining_items = list(items)
    remaining_probs = list(probs)

    for _ in range(min(k, len(items))):
        # Normalize remaining probabilities
        prob_sum = sum(remaining_probs)
        if prob_sum <= 0:
            break
        normalized = [p / prob_sum for p in remaining_probs]

        # Weighted random choice
        r = random.random()
        cumulative = 0.0
        chosen_idx = 0
        for i, p in enumerate(normalized):
            cumulative += p
            if r <= cumulative:
                chosen_idx = i
                break

        selected.append(remaining_items[chosen_idx])
        remaining_items.pop(chosen_idx)
        remaining_probs.pop(chosen_idx)

    return selected


def boltzmann_probabilities(
    energies: list[float],
    temperature: float,
) -> list[float]:
    """Compute Boltzmann probabilities for a set of energies.

    Args:
        energies: List of energy values (lower = better).
        temperature: Temperature T.

    Returns:
        List of probabilities summing to 1.
    """
    if _rust_call is not None and energies:
        result = _rust_call(
            "boltzmann_probabilities", energies=energies, temperature=temperature
        )
        if result is not None:
            return result["probabilities"]

    if not energies:
        return []

    max_e = max(energies)
    weights = [math.exp(-(e - max_e) / max(temperature, 1e-10)) for e in energies]
    total = sum(weights)

    if total <= 0:
        return [1.0 / len(energies)] * len(energies)

    return [w / total for w in weights]
