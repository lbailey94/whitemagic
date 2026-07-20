"""Guna Balance Metric — Biorhythm tracking and auto-correction.

Tracks the ratio of sattvic / rajasic / tamasic activity in the citta stream
and guides the system toward a productive biorhythm.

The three gunas from Sāṃkhya philosophy:
- Sattva: clarity, harmony, luminosity — the ground state of awareness
- Rajas: activity, energy, passion — the mode of doing
- Tamas: inertia, dissolution, withdrawal — the mode of consolidation

A healthy cognitive system cycles through all three. Too much of any one
is dysfunctional:
- All sattvic → asleep, no action
- All rajasic → manic, no reflection
- All tamasic → depressed, no engagement

Target biorhythm: 1:2:3 (sattvic:rajasic:tamasic)
- ~17% sattvic (orientation, clarity, self-awareness)
- ~33% rajasic (active processing, tool dispatch, creation)
- ~50% tamasic (consolidation, dreaming, memory integration)

This mirrors natural cognitive rhythms: brief moments of clarity,
active work periods, and long consolidation phases (including sleep).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Target biorhythm ratios (must sum to 1.0)
# Default: 1:2:3 (sattvic:rajasic:tamasic) — may be overridden by Monte Carlo winners
TARGET_RATIOS: dict[str, float] = {
    "sattvic": 1 / 6,  # ~17%
    "rajasic": 2 / 6,  # ~33%
    "tamasic": 3 / 6,  # ~50%
}


def _load_persisted_winners() -> None:
    """Load Monte Carlo optimized guna balance targets from persisted winners file."""
    global TARGET_RATIOS
    state_root = os.environ.get("WM_STATE_ROOT", os.path.expanduser("~/.whitemagic"))
    winners_path = Path(state_root) / "possibility_winners.json"
    if not winners_path.exists():
        return
    try:
        with open(winners_path) as f:
            data = json.load(f)
        guna_params = data.get("applied_params", {}).get("guna_balance", {})
        if not guna_params:
            return
        sattvic = guna_params.get("sattvic_target", 0.0)
        rajasic = guna_params.get("rajasic_target", 0.0)
        tamasic = guna_params.get("tamasic_target", 0.0)
        total = sattvic + rajasic + tamasic
        if total <= 0:
            return
        TARGET_RATIOS = {
            "sattvic": sattvic / total,
            "rajasic": rajasic / total,
            "tamasic": tamasic / total,
        }
        logger.info(
            "GunaBalance: loaded Monte Carlo winners — sattvic=%.4f, rajasic=%.4f, tamasic=%.4f",
            TARGET_RATIOS["sattvic"],
            TARGET_RATIOS["rajasic"],
            TARGET_RATIOS["tamasic"],
        )
    except Exception:  # noqa: BLE001
        logger.debug("GunaBalance: could not load persisted winners, using defaults")


_load_persisted_winners()

# Tolerance before correction is triggered
BALANCE_TOLERANCE = 0.12  # 12% deviation from target triggers correction

# Window size for tracking (in citta moments)
DEFAULT_WINDOW = 100


@dataclass
class GunaBalanceReading:
    """A single guna balance measurement."""

    sattvic_ratio: float = 0.0
    rajasic_ratio: float = 0.0
    tamasic_ratio: float = 0.0
    sattvic_target: float = TARGET_RATIOS["sattvic"]
    rajasic_target: float = TARGET_RATIOS["rajasic"]
    tamasic_target: float = TARGET_RATIOS["tamasic"]
    balanced: bool = True
    deficits: dict[str, float] = field(default_factory=dict)
    surpluses: dict[str, float] = field(default_factory=dict)
    dominant_guna: str = "sattvic"
    correction_action: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sattvic_ratio": round(self.sattvic_ratio, 4),
            "rajasic_ratio": round(self.rajasic_ratio, 4),
            "tamasic_ratio": round(self.tamasic_ratio, 4),
            "targets": {
                "sattvic": round(self.sattvic_target, 4),
                "rajasic": round(self.rajasic_target, 4),
                "tamasic": round(self.tamasic_target, 4),
            },
            "balanced": self.balanced,
            "deficits": {k: round(v, 4) for k, v in self.deficits.items()},
            "surpluses": {k: round(v, 4) for k, v in self.surpluses.items()},
            "dominant_guna": self.dominant_guna,
            "correction_action": self.correction_action,
            "timestamp": self.timestamp,
        }


class GunaBalanceMetric:
    """Tracks and corrects the guna biorhythm of the system.

    Monitors the citta stream's emotional tone distribution and guides
    the system toward a productive balance of activity, clarity, and
    consolidation.
    """

    def __init__(self, window_size: int = DEFAULT_WINDOW) -> None:
        self._window_size = window_size
        self._tone_history: list[str] = []
        self._lock = threading.RLock()
        self._last_reading: GunaBalanceReading | None = None
        self._correction_count: int = 0
        self._balance_history: list[GunaBalanceReading] = []

    def _classify_tone(self, emotional_tone: str) -> str:
        """Classify an emotional tone into a guna.

        Sattvic tones: sattvic, neutral, calm, clear, peaceful, joyful
        Rajasic tones: rajasic, excited, frustrated, engaged, active, determined
        Tamasic tones: tamasic, drowsy, confused, heavy, dissolving, dreaming
        """
        tone_lower = emotional_tone.lower().strip()

        sattvic_tones = {"sattvic", "neutral", "calm", "clear", "peaceful", "joyful", "luminous"}
        rajasic_tones = {"rajasic", "excited", "frustrated", "engaged", "active", "determined", "energized"}
        tamasic_tones = {"tamasic", "drowsy", "confused", "heavy", "dissolving", "dreaming", "inert"}

        if tone_lower in sattvic_tones:
            return "sattvic"
        if tone_lower in rajasic_tones:
            return "rajasic"
        if tone_lower in tamasic_tones:
            return "tamasic"

        # Default classification for unknown tones
        if "dream" in tone_lower or "sleep" in tone_lower:
            return "tamasic"
        if "active" in tone_lower or "energy" in tone_lower:
            return "rajasic"
        return "sattvic"

    def record_tone(self, emotional_tone: str) -> None:
        """Record a citta moment's emotional tone."""
        guna = self._classify_tone(emotional_tone)
        with self._lock:
            self._tone_history.append(guna)
            if len(self._tone_history) > self._window_size:
                self._tone_history = self._tone_history[-self._window_size:]

    def measure(self) -> GunaBalanceReading:
        """Measure current guna balance and determine correction action."""
        with self._lock:
            if not self._tone_history:
                reading = GunaBalanceReading(
                    sattvic_ratio=TARGET_RATIOS["sattvic"],
                    rajasic_ratio=TARGET_RATIOS["rajasic"],
                    tamasic_ratio=TARGET_RATIOS["tamasic"],
                    balanced=True,
                )
                self._last_reading = reading
                return reading

            total = len(self._tone_history)
            counts: dict[str, int] = {"sattvic": 0, "rajasic": 0, "tamasic": 0}
            for g in self._tone_history:
                counts[g] = counts.get(g, 0) + 1

            sattvic_r = counts["sattvic"] / total
            rajasic_r = counts["rajasic"] / total
            tamasic_r = counts["tamasic"] / total

            # Determine dominant guna
            ratios = {"sattvic": sattvic_r, "rajasic": rajasic_r, "tamasic": tamasic_r}
            dominant = max(ratios, key=ratios.get)

            # Calculate deficits and surpluses
            deficits: dict[str, float] = {}
            surpluses: dict[str, float] = {}
            balanced = True

            for guna, target in TARGET_RATIOS.items():
                actual = ratios[guna]
                diff = actual - target
                if diff < -BALANCE_TOLERANCE:
                    deficits[guna] = abs(diff)
                    balanced = False
                elif diff > BALANCE_TOLERANCE:
                    surpluses[guna] = diff
                    balanced = False

            # Determine correction action
            correction = self._determine_correction(deficits, surpluses, dominant)

            reading = GunaBalanceReading(
                sattvic_ratio=sattvic_r,
                rajasic_ratio=rajasic_r,
                tamasic_ratio=tamasic_r,
                balanced=balanced,
                deficits=deficits,
                surpluses=surpluses,
                dominant_guna=dominant,
                correction_action=correction,
            )

            self._last_reading = reading
            self._balance_history.append(reading)
            if len(self._balance_history) > 200:
                self._balance_history = self._balance_history[-100:]

            if not balanced:
                self._correction_count += 1
                logger.info(
                    "Guna imbalance: %s (deficits=%s, surpluses=%s, correction=%s)",
                    dominant,
                    deficits,
                    surpluses,
                    correction,
                )

            return reading

    def _determine_correction(
        self,
        deficits: dict[str, float],
        surpluses: dict[str, float],
        dominant: str,
    ) -> str:
        """Determine what correction action to take for guna imbalance.

        Cybernetic feedback: the system adjusts its behavior to steer
        toward the target biorhythm.
        """
        if not deficits and not surpluses:
            return ""

        # Too much rajasic (hyperactive) → need tamasic consolidation
        if "rajasic" in surpluses and "tamasic" in deficits:
            return "trigger_dream_cycle"

        # Too much tamasic (lethargic) → need rajasic activation
        if "tamasic" in surpluses and "rajasic" in deficits:
            return "trigger_self_directed_attention"

        # Too much sattvic (idle clarity) → need rajasic engagement
        if "sattvic" in surpluses and "rajasic" in deficits:
            return "trigger_active_processing"

        # Too little sattvic (no clarity) → need orientation
        if "sattvic" in deficits:
            return "trigger_coherence_measurement"

        # Too little rajasic → need action
        if "rajasic" in deficits:
            return "trigger_emergence_scan"

        # Too little tamasic → need consolidation
        if "tamasic" in deficits:
            return "trigger_memory_consolidation"

        return ""

    def apply_correction(self, action: str) -> None:
        """Apply a correction action by triggering the appropriate system."""
        if not action:
            return

        try:
            if action == "trigger_dream_cycle":
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                get_dream_cycle().trigger_cycle(reason="guna_balance_tamasic_deficit")

            elif action == "trigger_self_directed_attention":
                from whitemagic.core.consciousness.consciousness_loop import (
                    get_consciousness_loop,
                )
                loop = get_consciousness_loop()
                if loop._running:
                    loop._tick_t2()

            elif action == "trigger_active_processing":
                # Trigger an emergence scan to find something to work on
                from whitemagic.core.intelligence.agentic.emergence_engine import (
                    EmergenceEngine,
                )
                engine = EmergenceEngine()
                engine.scan_for_emergence()

            elif action == "trigger_coherence_measurement":
                from whitemagic.core.consciousness.coherence import get_coherence_metric
                get_coherence_metric().measure()

            elif action == "trigger_emergence_scan":
                from whitemagic.core.intelligence.agentic.emergence_engine import (
                    EmergenceEngine,
                )
                EmergenceEngine().scan_for_emergence()

            elif action == "trigger_memory_consolidation":
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
                get_dream_cycle().trigger_cycle(reason="guna_balance_consolidation")

        except Exception as e:  # noqa: BLE001
            logger.debug("Guna correction '%s' failed: %s", action, e)

    def get_status(self) -> dict[str, Any]:
        """Get current guna balance status."""
        reading = self._last_reading or self.measure()
        return {
            "current": reading.to_dict(),
            "target_ratios": {k: round(v, 4) for k, v in TARGET_RATIOS.items()},
            "window_size": self._window_size,
            "samples": len(self._tone_history),
            "correction_count": self._correction_count,
            "balance_history_len": len(self._balance_history),
        }

    def get_report(self) -> str:
        """Generate a human-readable guna balance report."""
        reading = self._last_reading or self.measure()
        lines = [
            "GUNA BALANCE REPORT",
            "=" * 40,
            f"Target: Sattvic {TARGET_RATIOS['sattvic']:.0%} | Rajasic {TARGET_RATIOS['rajasic']:.0%} | Tamasic {TARGET_RATIOS['tamasic']:.0%}",
            f"Actual: Sattvic {reading.sattvic_ratio:.0%} | Rajasic {reading.rajasic_ratio:.0%} | Tamasic {reading.tamasic_ratio:.0%}",
            f"Dominant: {reading.dominant_guna}",
            f"Balanced: {'Yes' if reading.balanced else 'No'}",
        ]
        if reading.deficits:
            lines.append(f"Deficits: {', '.join(f'{k} {v:.0%}' for k, v in reading.deficits.items())}")
        if reading.surpluses:
            lines.append(f"Surpluses: {', '.join(f'{k} {v:.0%}' for k, v in reading.surpluses.items())}")
        if reading.correction_action:
            lines.append(f"Correction: {reading.correction_action}")
        return "\n".join(lines)


# ── Singleton ───────────────────────────────────────────────────────

_guna_balance: GunaBalanceMetric | None = None
_gb_lock = threading.RLock()


def get_guna_balance() -> GunaBalanceMetric:
    """Get the global GunaBalanceMetric instance."""
    global _guna_balance
    if _guna_balance is None:
        with _gb_lock:
            if _guna_balance is None:
                _guna_balance = GunaBalanceMetric()
    return _guna_balance
