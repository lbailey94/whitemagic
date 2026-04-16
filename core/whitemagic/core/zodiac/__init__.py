"""🌌 Zodiacal Clock Engine — WhiteMagic v22.0
=========================================
Implements the 12-phase Zodiacal Cycle (Enochian Round) as the primary
session-based progression engine, mapping the 28 Lunar Mansions (Ganas)
to traditional astrological signs.

Design:
  - 12 Phases: Aries through Pisces
  - Manual Progression: Shift phases using `astro_shift`
  - Persistence: State stored in `WM_STATE_ROOT/zodiac_state.json`
  - Integration: Provides `astro_status` and `astro_shift` for Gana Dipper.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# The 12 Traditional Zodiac Signs (The Enochain Round)
ZODIAC_PHASES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Mapping of the 28 Lunar Mansions (Ganas) to the 12 Zodiac Signs
# Maintaining symmetry and semantic resonance
MANSION_MAPPING = {
    "Aries": ["Ashwini", "Bharani", "Krittika (part)"],
    "Taurus": ["Krittika (part)", "Rohini", "Mrigashira (part)"],
    "Gemini": ["Mrigashira (part)", "Ardra", "Punarvasu (part)"],
    "Cancer": ["Punarvasu (part)", "Pushya", "Ashlesha"],
    "Leo": ["Magha", "Purva Phalguni", "Uttara Phalguni (part)"],
    "Virgo": ["Uttara Phalguni (part)", "Hasta", "Chitra (part)"],
    "Libra": ["Chitra (part)", "Swati", "Vishakha (part)"],
    "Scorpio": ["Vishakha (part)", "Anuradha", "Jyeshtha"],
    "Sagittarius": ["Mula", "Purva Ashadha", "Uttara Ashadha (part)"],
    "Capricorn": ["Uttara Ashadha (part)", "Shravana", "Dhanishta (part)"],
    "Aquarius": ["Dhanishta (part)", "Shatabhisha", "Purva Bhadrapada (part)"],
    "Pisces": ["Purva Bhadrapada (part)", "Uttara Bhadrapada", "Revati"]
}

# Numerical mapping of the 28 mansions to signs (1-indexed)
# Each sign covers approx 2.3 mansions.
NUMERICAL_MANSION_TO_SIGN = {
    1:  "Aries", 2:  "Aries", 3:  "Aries",   # Ashwini, Bharani, Krittika
    4:  "Taurus", 5:  "Taurus",             # Rohini, Mrigashira
    6:  "Gemini", 7:  "Gemini",             # Ardra, Punarvasu
    8:  "Cancer", 9:  "Cancer",             # Pushya, Ashlesha
    10: "Leo", 11: "Leo", 12: "Leo",        # Magha, Purva Phalguni, Uttara Phalguni
    13: "Virgo", 14: "Virgo",               # Hasta, Chitra
    15: "Libra", 16: "Libra",               # Swati, Vishakha
    17: "Scorpio", 18: "Scorpio",           # Anuradha, Jyeshtha
    19: "Sagittarius", 20: "Sagittarius", 21: "Sagittarius", # Mula, Purva Ashadha, Uttara Ashadha
    22: "Capricorn", 23: "Capricorn",       # Shravana, Dhanishta
    24: "Aquarius", 25: "Aquarius",         # Shatabhisha, Purva Bhadrapada
    26: "Pisces", 27: "Pisces", 28: "Pisces" # Uttara Bhadrapada, Revati, Wall
}

DEFAULT_STATE = {
    "current_phase": "Aries",
    "last_shift": None,
    "total_shifts": 0,
    "session_id": None
}

class ZodiacalClock:
    """Session-based Zodiacal progression engine."""

    def __init__(self, state_root: str | None = None) -> None:
        self.state_root = Path(state_root or os.getenv("WM_STATE_ROOT", "/home/lucas/.gemini/antigravity/state"))
        self.state_file = self.state_root / "zodiac_state.json"
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load zodiac state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.warning(f"ZodiacalClock: failed to load state: {e}")

        # Initialize default state
        state = DEFAULT_STATE.copy()
        state["last_init"] = datetime.now().isoformat()
        return state

    def _save_state(self) -> None:
        """Persist zodiac state to disk."""
        try:
            self.state_root.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.error(f"ZodiacalClock: failed to save state: {e}")

    @property
    def current_phase(self) -> str:
        return self._state.get("current_phase", "Aries")

    @property
    def mansions(self) -> list[str]:
        """Return the Lunar Mansions associated with the current phase."""
        return MANSION_MAPPING.get(self.current_phase, [])

    def status(self) -> dict[str, Any]:
        """Get the current astrological status."""
        return {
            "phase": self.current_phase,
            "index": ZODIAC_PHASES.index(self.current_phase),
            "mansions": self.mansions,
            "next_phase": ZODIAC_PHASES[(ZODIAC_PHASES.index(self.current_phase) + 1) % 12],
            "last_shift": self._state.get("last_shift"),
            "total_shifts": self._state.get("total_shifts", 0)
        }

    def shift(self, target_phase: str | None = None) -> dict[str, Any]:
        """Progress the clock to the next phase or a specific target phase."""
        current_idx = ZODIAC_PHASES.index(self.current_phase)

        if target_phase:
            if target_phase not in ZODIAC_PHASES:
                raise ValueError(f"Invalid zodiac phase: {target_phase}. Must be one of {ZODIAC_PHASES}")
            new_phase = target_phase
        else:
            # Automatic progression to next phase
            new_phase = ZODIAC_PHASES[(current_idx + 1) % 12]

        self._state["current_phase"] = new_phase
        self._state["last_shift"] = datetime.now().isoformat()
        self._state["total_shifts"] = self._state.get("total_shifts", 0) + 1
        self._save_state()

        logger.info(f"🌌 Astro-Shift: {new_phase} (Mansion Alignment: {', '.join(self.mansions)})")
        return self.status()

    def get_resonance_multiplier(self, mansion_num: int) -> float:
        """Calculate the resonance multiplier for a given mansion.
        
        Returns 1.5 if aligned with current Zodiac sign, 1.0 otherwise.
        """
        aligned_sign = NUMERICAL_MANSION_TO_SIGN.get(mansion_num)
        if aligned_sign == self.current_phase:
            return 1.5
        return 1.0

    def is_aligned(self, mansion_num: int) -> bool:
        """Check if a mansion is aligned with the current Zodiac sign."""
        return self.get_resonance_multiplier(mansion_num) > 1.0

_clock_instance: ZodiacalClock | None = None

def get_zodiac_clock() -> ZodiacalClock:
    """Get or create the global ZodiacalClock singleton."""
    global _clock_instance
    if _clock_instance is None:
        _clock_instance = ZodiacalClock()
    return _clock_instance
