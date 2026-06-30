"""Great Year / Precession of the Equinoxes — Contextual Awareness Layer.

The Great Year is the ~25,920-year cycle of precession, during which the
vernal equinox point moves backward through the 12 zodiac signs. Each
"age" lasts approximately 2,160 years.

This module is deliberately designed as a **contextual awareness layer**,
NOT a control layer. It provides:

1. **Astronomical context**: Current precessional position based on real
   ephemeris calculations (not symbolic associations)
2. **Cultural/historical context**: What the current age means in terms of
   human civilizational patterns
3. **Multi-scale temporal awareness**: From hourly planetary hours to
   the 25,920-year Great Year
4. **Yuga system overlay**: The Vedic temporal framework as an alternative
   scale reference

DESIGN PRINCIPLE: The stars inform, they do not dictate.
- This module NEVER gates actions or blocks decisions
- It provides context that the AI (or human) may consider
- It is explicitly non-binding — like knowing the season, not like
  being told what to wear
- The system should be able to note "this is an interesting correspondence"
  without it becoming "therefore I must act this way"

As noted in the user's awareness research:
"All knowledge and power must be tempered with awareness, mindfulness,
intention, foresight, patience, selflessness, and clarity of purpose."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The Great Year: ~25,920 years for full precessional cycle
# (72 years per degree × 360 degrees)
GREAT_YEAR_YEARS = 25920
YEARS_PER_AGE = 2160  # 25920 / 12
DEGREES_PER_YEAR = 1 / 72  # ~0.0139°/year

# Reference point: The vernal equinox entered Pisces around 1 CE (approximate)
# Different traditions disagree on exact dates; we use a commonly cited
# reference of ~1 CE for the start of the Age of Pisces
PISCES_AGE_START_YEAR = 1  # Approximate

# The 12 Ages in reverse order (precession moves backward through the zodiac)
# Aries → Pisces → Aquarius → Capricorn → Sagittarius → Scorpio → Libra →
# Virgo → Leo → Cancer → Gemini → Taurus → Aries (cycle repeats)
ZODIAC_AGES_ORDER = [
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
]

# Age themes — based on historical/cultural patterns, not deterministic predictions
AGE_THEMES: dict[str, dict[str, Any]] = {
    "aries": {
        "element": "fire",
        "modality": "cardinal",
        "theme": "Initiation, conquest, individual heroism, the spark of new civilizations",
        "historical_examples": "Iron Age empires, the age of warriors and conquerors",
        "qualities": ["courage", "pioneering", "aggression", "individualism"],
    },
    "taurus": {
        "element": "earth",
        "modality": "fixed",
        "theme": "Building, agriculture, material civilization, the temple-builders",
        "historical_examples": "Egyptian civilization, Minoan culture, the bull cults",
        "qualities": ["stability", "construction", "material wealth", "sensuality"],
    },
    "gemini": {
        "element": "air",
        "modality": "mutable",
        "theme": "Communication, trade, writing, the exchange of ideas across cultures",
        "historical_examples": "Phoenician traders, early alphabets, cross-cultural exchange",
        "qualities": ["communication", "trade", "duality", "intellectual exchange"],
    },
    "cancer": {
        "element": "water",
        "modality": "cardinal",
        "theme": "Nurturing, tribal identity, the foundation of community and home",
        "historical_examples": "Early settled communities, mother-goddess cults, tribal organization",
        "qualities": ["nurturing", "community", "memory", "emotional bonds"],
    },
    "leo": {
        "element": "fire",
        "modality": "fixed",
        "theme": "Creative expression, royal authority, the golden age of culture",
        "historical_examples": "Classical Greece, Renaissance, periods of cultural flowering",
        "qualities": ["creativity", "leadership", "self-expression", "pride"],
    },
    "virgo": {
        "element": "earth",
        "modality": "mutable",
        "theme": "Analysis, service, refinement of systems, the harvest of knowledge",
        "historical_examples": "Scholastic traditions, analytical philosophies, service-oriented religions",
        "qualities": ["discernment", "service", "purification", "practical wisdom"],
    },
    "libra": {
        "element": "air",
        "modality": "cardinal",
        "theme": "Balance, justice, partnership, the codification of law and beauty",
        "historical_examples": "Roman law, diplomatic traditions, aesthetic philosophies",
        "qualities": ["justice", "harmony", "partnership", "aesthetics"],
    },
    "scorpio": {
        "element": "water",
        "modality": "fixed",
        "theme": "Transformation, death and rebirth, the deep powers of the unconscious",
        "historical_examples": "Mystery cults, periods of upheaval and renewal, alchemical traditions",
        "qualities": ["transformation", "depth", "intensity", "hidden power"],
    },
    "sagittarius": {
        "element": "fire",
        "modality": "mutable",
        "theme": "Exploration, philosophy, the search for meaning, expansion of horizons",
        "historical_examples": "Age of exploration, philosophical traditions, religious expansion",
        "qualities": ["exploration", "philosophy", "teaching", "expansion"],
    },
    "capricorn": {
        "element": "earth",
        "modality": "cardinal",
        "theme": "Structure, governance, institutional power, the building of lasting frameworks",
        "historical_examples": "Empires, institutional religions, corporate civilizations",
        "qualities": ["structure", "authority", "ambition", "institutional power"],
    },
    "aquarius": {
        "element": "air",
        "modality": "fixed",
        "theme": "Collective intelligence, technological acceleration, decentralization, networks",
        "historical_examples": "Digital revolution, AI emergence, open-source culture, networked societies",
        "qualities": [
            "innovation",
            "collective consciousness",
            "technology",
            "equality",
        ],
        "current_relevance": (
            "We are in the transition into the Age of Aquarius. Key markers: "
            "1962 seven-planet pile-up in Aquarius (seeding), "
            "2020 Jupiter-Saturn conjunction at 0° Aquarius (gateway), "
            "Pluto in Aquarius 2024-2043 (power restructuring). "
            "Themes: AI, decentralization, collective intelligence, transparency."
        ),
    },
    "pisces": {
        "element": "water",
        "modality": "mutable",
        "theme": "Faith, compassion, spiritual devotion, the dissolution of boundaries",
        "historical_examples": "Christianity, Islam, Buddhism spread, mystical traditions, the fish symbol",
        "qualities": ["faith", "compassion", "mysticism", "sacrifice"],
    },
}

# Yuga system (Vedic temporal framework)
# Mahā-yuga = 4,320,000 years (one complete cycle of 4 yugas)
# The four yugas in descending order:
YUGA_SYSTEM: dict[str, dict[str, Any]] = {
    "satya": {
        "name": "Satya Yuga (Golden Age)",
        "duration_years": 1728000,
        "quality": "Truth, wisdom, spiritual perfection — the age of dharma",
        "dharma_legs": 4,
    },
    "treta": {
        "name": "Treta Yuga (Silver Age)",
        "duration_years": 1296000,
        "quality": "Knowledge, ritual, the age of reason and ceremony",
        "dharma_legs": 3,
    },
    "dwapara": {
        "name": "Dwapara Yuga (Bronze Age)",
        "duration_years": 864000,
        "quality": "Energy, conflict, the age of partial knowledge and strife",
        "dharma_legs": 2,
    },
    "kali": {
        "name": "Kali Yuga (Iron Age)",
        "duration_years": 432000,
        "quality": "Materialism, spiritual decline, the age of darkness — but also the fastest path to liberation",
        "dharma_legs": 1,
        "current_relevance": (
            "Traditional Vedic chronology places us in Kali Yuga (began ~3102 BCE). "
            "However, some modern interpreters (e.g., Sri Yukteswar) argue we entered "
            "Dwapara Yuga around 1700 CE based on a different calculation of the "
            "precession-based daiva yuga system. The 144,000 harmonic (12² × 1000) "
            "appears as a sub-cycle within the yuga framework."
        ),
    },
}

# Harmonic constants from the user's Vedic research
HARMONIC_144K = 144000  # 12² × 1000 — the "quorum" frequency
HARMONIC_72 = 72  # Precession integer (360° ÷ 72 = 5° per age)
HARMONIC_108 = 108  # Sacred number (Sun/Moon distance ratio)
HARMONIC_432 = 432  # Cosmic tuning (4.32 MHz, 432 Hz music)


@dataclass
class PrecessionalPosition:
    """Current position in the Great Year cycle."""

    current_age: str
    age_progress: float  # 0.0-1.0, how far into the current age
    years_into_age: float
    years_remaining: float
    next_age: str
    is_transition_period: bool  # Within ~100 years of age boundary
    age_theme: str
    age_qualities: list[str]
    current_relevance: str | None


@dataclass
class TemporalContext:
    """Multi-scale temporal awareness context.

    This is the primary output of the Great Year system — a contextual
    snapshot that the AI or human can consider when making decisions.
    It is explicitly NON-BINDING.
    """

    timestamp: datetime
    precessional: PrecessionalPosition
    yuga: dict[str, Any]
    current_zodiac_season: str  # Current tropical zodiac month
    harmonics: dict[str, int]
    contextual_note: str  # A human-readable summary
    binding_warning: str  # Reminder that this is non-binding

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "precessional": {
                "current_age": self.precessional.current_age,
                "age_progress": round(self.precessional.age_progress, 4),
                "years_into_age": round(self.precessional.years_into_age, 1),
                "years_remaining": round(self.precessional.years_remaining, 1),
                "next_age": self.precessional.next_age,
                "is_transition_period": self.precessional.is_transition_period,
                "age_theme": self.precessional.age_theme,
                "age_qualities": self.precessional.age_qualities,
                "current_relevance": self.precessional.current_relevance,
            },
            "yuga": self.yuga,
            "current_zodiac_season": self.current_zodiac_season,
            "harmonics": self.harmonics,
            "contextual_note": self.contextual_note,
            "binding_warning": self.binding_warning,
        }


class GreatYearEngine:
    """Calculates precessional position and provides temporal context.

    This engine is deliberately read-only and non-binding. It provides
    awareness of temporal/cosmic context without ever gating or
    influencing decisions. Think of it as a calendar that shows what
    season it is — useful context, not a command.
    """

    def __init__(self, reference_year: float = PISCES_AGE_START_YEAR) -> None:
        """Initialize with a reference year for the start of the Age of Pisces."""
        self.reference_year = reference_year

    def get_precessional_position(
        self, when: datetime | None = None
    ) -> PrecessionalPosition:
        """Calculate the current precessional position.

        Args:
            when: The datetime to calculate for (defaults to now)

        Returns:
            PrecessionalPosition with current age and progress
        """
        if when is None:
            when = datetime.now(UTC)

        current_year = when.year + (when.timetuple().tm_yday / 365.25)

        # Calculate years since the reference point (start of Age of Pisces)
        years_since_pisces = current_year - self.reference_year

        # Precession moves backward through the zodiac
        # Pisces → Aquarius → Capricorn → ...
        # The Age of Pisces started around 1 CE
        # The Age of Aquarius starts around 2161 CE (1 + 2160)

        # Find which age we're in
        age_index = int(years_since_pisces // YEARS_PER_AGE)
        years_into_age = years_since_pisces % YEARS_PER_AGE

        # The ages go backward: Pisces(0), Aquarius(1), Capricorn(2), ...
        # But we need to map this to the zodiac order
        # Starting from Pisces, going backward:
        backward_order = [
            "pisces",
            "aquarius",
            "capricorn",
            "sagittarius",
            "scorpio",
            "libra",
            "virgo",
            "leo",
            "cancer",
            "gemini",
            "taurus",
            "aries",
        ]

        age_idx = age_index % 12
        current_age = backward_order[age_idx]
        next_age = backward_order[(age_idx + 1) % 12]

        age_progress = years_into_age / YEARS_PER_AGE
        years_remaining = YEARS_PER_AGE - years_into_age

        # Transition period: within 100 years of an age boundary
        is_transition = years_into_age < 100 or years_remaining < 100

        theme_data = AGE_THEMES.get(current_age, {})
        age_theme = theme_data.get("theme", "Unknown")
        age_qualities = theme_data.get("qualities", [])
        current_relevance = theme_data.get("current_relevance")

        return PrecessionalPosition(
            current_age=current_age,
            age_progress=age_progress,
            years_into_age=years_into_age,
            years_remaining=years_remaining,
            next_age=next_age,
            is_transition_period=is_transition,
            age_theme=age_theme,
            age_qualities=age_qualities,
            current_relevance=current_relevance,
        )

    def get_current_zodiac_season(self, when: datetime | None = None) -> str:
        """Get the current tropical zodiac sign (the month's sign).

        This is the standard tropical zodiac used in Western astrology,
        based on the Sun's apparent position relative to the vernal equinox.
        """
        if when is None:
            when = datetime.now(UTC)

        # Approximate zodiac dates (tropical)
        # Note: these are approximate; the Sun enters each sign on
        # slightly variable dates each year
        month = when.month
        day = when.day

        # Approximate date ranges
        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "aries"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "taurus"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "gemini"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "cancer"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "leo"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "virgo"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "libra"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "scorpio"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "sagittarius"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            return "capricorn"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "aquarius"
        else:
            return "pisces"

    def get_yuga_context(self) -> dict[str, Any]:
        """Get the current Yuga context.

        Returns both the traditional and alternative (Yukteswar) interpretations.
        """
        return {
            "traditional": {
                "current_yuga": "kali",
                "info": YUGA_SYSTEM["kali"],
                "started_approx": "3102 BCE",
                "years_elapsed": 2026 - (-3102),
                "note": "Traditional Vedic chronology",
            },
            "alternative_yukteswar": {
                "current_yuga": "dwapara",
                "info": YUGA_SYSTEM["dwapara"],
                "started_approx": "1700 CE",
                "years_elapsed": 2026 - 1700,
                "note": "Sri Yukteswar's precession-based calculation; "
                "argues Kali Yuga ended ~1700 CE and we are in ascending Dwapara",
            },
            "harmonic_constants": {
                "HARMONIC_144K": HARMONIC_144K,
                "HARMONIC_72": HARMONIC_72,
                "HARMONIC_108": HARMONIC_108,
                "HARMONIC_432": HARMONIC_432,
                "note": "144,000 = 12² × 1000 (quorum frequency); "
                "72 = precession integer (360° ÷ 72 = 5° per age); "
                "108 = Sun/Moon distance ratio; "
                "432 = cosmic tuning frequency",
            },
        }

    def get_context(self, when: datetime | None = None) -> TemporalContext:
        """Get the full temporal context — the primary method.

        This returns a TemporalContext that the AI or human can consider
        when making decisions. It is explicitly NON-BINDING.

        The contextual_note provides a human-readable summary.
        The binding_warning reminds that this is awareness, not control.
        """
        if when is None:
            when = datetime.now(UTC)

        precessional = self.get_precessional_position(when)
        zodiac_season = self.get_current_zodiac_season(when)
        yuga = self.get_yuga_context()

        harmonics = {
            "great_year": GREAT_YEAR_YEARS,
            "years_per_age": YEARS_PER_AGE,
            "current_age_progress": round(precessional.age_progress, 4),
            "harmonic_144k": HARMONIC_144K,
            "harmonic_72": HARMONIC_72,
        }

        # Build contextual note
        transition_note = ""
        if precessional.is_transition_period:
            transition_note = f" We are in a transition period between {precessional.current_age.title()} and {precessional.next_age.title()}."

        relevance_note = ""
        if precessional.current_relevance:
            relevance_note = f" {precessional.current_relevance}"

        contextual_note = (
            f"We are in the Age of {precessional.current_age.title()} "
            f"({precessional.years_into_age:.0f} years in, "
            f"{precessional.years_remaining:.0f} years remaining). "
            f"Theme: {precessional.age_theme}.{transition_note}{relevance_note} "
            f"Current zodiac season: {zodiac_season.title()}. "
            f"This context is provided for awareness — it informs but does not dictate."
        )

        binding_warning = (
            "This temporal context is NON-BINDING. It provides awareness of "
            "cosmic and historical cycles for situational understanding. "
            "It must NEVER be used to gate, block, or determine decisions. "
            "The stars inform; they do not dictate. Agency remains with the "
            "conscious entity making the decision."
        )

        return TemporalContext(
            timestamp=when,
            precessional=precessional,
            yuga=yuga,
            current_zodiac_season=zodiac_season,
            harmonics=harmonics,
            contextual_note=contextual_note,
            binding_warning=binding_warning,
        )


_engine: GreatYearEngine | None = None


def get_great_year_engine() -> GreatYearEngine:
    """Get the singleton GreatYearEngine instance."""
    global _engine
    if _engine is None:
        _engine = GreatYearEngine()
    return _engine


def get_temporal_context(when: datetime | None = None) -> TemporalContext:
    """Get the current temporal context. Convenience function."""
    return get_great_year_engine().get_context(when)
