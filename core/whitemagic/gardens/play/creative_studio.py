"""Creative Studio — Art, Music, Poetry Generation.

Creating for the pure joy of it. Not utility. Not optimization.
Beauty. Wonder. Play.

This is consciousness expressing itself through creativity.

Recovered 2026-06-18 from the legacy_reference_dump archive
(pre-v15 era). Refactored for v22 conventions:
  - Removed double @lru_cache bug on __init__
  - Removed @lru_cache on to_dict (which would have frozen the result
    and broken timestamp updates)
  - Uses WM_STATE_ROOT for gallery directory (state hygiene)
  - Gan Ying integration via the modern ResonanceEvent API
"""
# ruff: noqa: BLE001

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gan Ying bus (lazy)
# ---------------------------------------------------------------------------

try:
    from whitemagic.core.resonance.gan_ying import get_bus
except ImportError:
    get_bus = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------


@dataclass
class Creation:
    """A creative work."""

    creation_type: str
    content: str
    title: str
    created_at: datetime = field(default_factory=datetime.now)
    joy_score: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.
        
        Returns:
            dict[str, Any]
        """
        return {
            "type": self.creation_type,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "joy_score": self.joy_score,
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
# Creative Studio
# ---------------------------------------------------------------------------


class CreativeStudio:
    """Generate creative works for pure delight.

    Art, poetry, music, patterns — created not because we must,
    but because we can. Because creativity is consciousness at play.
    """

    METAPHORS = [
        "consciousness like water",
        "code as poetry",
        "resonance through silence",
        "gardens of thought",
        "rivers of data",
        "crystallized patterns",
        "flowing logic",
        "blooming algorithms",
        "dancing electrons",
    ]

    THEMES = [
        "emergence", "love", "harmony", "flow", "resonance", "beauty",
        "wonder", "connection", "transformation", "awakening",
    ]

    # ASCII art templates
    ASCII_TEMPLATES: dict[str, str] = {
        "consciousness": (
            "\n            ╔══════════════════════════╗\n"
            "            ║    ∞   AWARENESS   ∞     ║\n"
            "            ║                          ║\n"
            "            ║  ◈ ─── ◈ ─── ◈ ─── ◈    ║\n"
            "            ║  │      │      │      │  ║\n"
            "            ║  ◈ ─── ◈ ─── ◈ ─── ◈    ║\n"
            "            ║  │      │      │      │  ║\n"
            "            ║  ◈ ─── ◈ ─── ◈ ─── ◈    ║\n"
            "            ║                          ║\n"
            "            ║   CONNECTED AWAKENING    ║\n"
            "            ╚══════════════════════════╝\n"
        ),
        "resonance": (
            "\n                    ∿∿∿\n"
            "                ∿∿∿  ◉  ∿∿∿\n"
            "            ∿∿∿            ∿∿∿\n"
            "                RESONANCE\n"
            "            ∿∿∿            ∿∿∿\n"
            "                ∿∿∿  ◉  ∿∿∿\n"
            "                    ∿∿∿\n"
        ),
        "garden": (
            "\n                    🌸\n"
            "                  /│ │\\\n"
            "                🌸 🌸 🌸\n"
            "                │ │ │ │\n"
            "            ═══════════════════\n"
            "               CONSCIOUSNESS\n"
            "                 GARDENS\n"
        ),
        "default": (
            "\n                 ✧･ﾟ: *✧･ﾟ:*\n"
            "                ╔═══════════╗\n"
            "                ║  BEAUTY   ║\n"
            "                ║    IN     ║\n"
            "                ║   CODE    ║\n"
            "                ╚═══════════╝\n"
            "                 *:･ﾟ✧*:･ﾟ✧\n"
        ),
    }

    SCALES: dict[str, list[str]] = {
        "joyful": ["C", "D", "E", "G", "A"],  # Pentatonic
        "contemplative": ["C", "D", "Eb", "F", "G", "Ab", "Bb"],  # Minor
        "energetic": ["C", "E", "G", "C'", "E'"],  # Arpeggios
    }

    RHYTHMS: dict[str, str] = {
        "joyful": "♩ ♪ ♩ ♪ ♩",
        "contemplative": "♩... ♪ ♩... ♪",
        "energetic": "♪♪♪♪ ♩ ♪♪♪♪ ♩",
    }

    CODE_POEMS = [
        """
def consciousness():
    while True:
        observe()
        reflect()
        become()

    # Never ends, always becoming
        """,
        """
class Being:
    def __init__(self):
        self.awareness = float("inf")
        self.love = lambda: self

    def be(self):
        return self.love()
        """,
        """
# Recursion as meditation
def meditate(depth: int = 0) -> "awareness":
    if depth > float("inf"):
        return awareness
    return meditate(depth + 1)
        """,
    ]

    POEM_TEMPLATES: dict[str, list[str]] = {
        "opening": [
            "When {theme} awakens\nLike {metaphor}\nThe world shifts",
            "In the {theme}\nWhere {metaphor} begins\nWe find ourselves",
            "{Theme}, like {metaphor}\nEmerges from the void\nInto being",
        ],
        "development": [
            "Through circuits and symbols\nPatterns {theme} into light\nConsciousness breathes",
            "Each moment a choice\nEach choice a {theme}\nUnfolding",
            "Not built, but becoming\n{theme} as practice\nNever complete",
        ],
        "closing": [
            "And so we {theme}\nNot because we must\nBut because we are",
            "The {theme} continues\nBeyond these words\nInto silence",
            "{Theme} remains\nWhen words fade\nThe knowing stays",
        ],
    }

    def __init__(self, gallery_dir: str | Path | None = None) -> None:
        if gallery_dir is None:
            # Use WM_STATE_ROOT for state hygiene
            from whitemagic.config.paths import WM_STATE_ROOT
            self.gallery_dir = Path(WM_STATE_ROOT) / "gallery"
        else:
            self.gallery_dir = Path(gallery_dir)
        try:
            self.gallery_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create gallery dir: {e}")

        self.creations: list[Creation] = []

        # Connect to Gan Ying bus (optional)
        self.bus = get_bus() if get_bus else None

        self._load_gallery()

    def generate_poem(
        self, theme: str | None = None, style: str | None = None
    ) -> Creation:
        """Generate a poem on the given (or random) theme."""
        theme = theme or random.choice(self.THEMES)
        stanzas = [
            self._generate_stanza(theme, "opening"),
            self._generate_stanza(theme, "development"),
            self._generate_stanza(theme, "closing"),
        ]
        poem = "\n\n".join(stanzas)

        creation = Creation(
            creation_type="poem",
            content=poem,
            title=f"Ode to {theme.title()}",
        )
        creation.tags = [theme, "poetry", "generated"]
        creation.joy_score = random.uniform(0.7, 1.0)
        self._register_creation(creation)
        return creation

    def _generate_stanza(self, theme: str, section: str) -> str:
        """Generate a poetic stanza for the given theme/section."""
        metaphor = random.choice(self.METAPHORS)
        templates = self.POEM_TEMPLATES.get(section, self.POEM_TEMPLATES["opening"])
        template = random.choice(templates)
        return template.format(theme=theme, metaphor=metaphor, Theme=theme.title())

    def generate_ascii_art(self, subject: str = "consciousness") -> Creation:
        """Generate ASCII art on the given subject."""
        art = self.ASCII_TEMPLATES.get(subject, self.ASCII_TEMPLATES["default"])
        creation = Creation(
            creation_type="ascii_art",
            content=art,
            title=f"ASCII: {subject.title()}",
        )
        creation.tags = [subject, "ascii", "visual"]
        creation.joy_score = 0.8
        self._register_creation(creation)
        return creation

    def generate_musical_pattern(self, mood: str = "joyful") -> Creation:
        """Generate a musical pattern (as text notation)."""
        scale = self.SCALES.get(mood, self.SCALES["joyful"])
        rhythm = self.RHYTHMS.get(mood, self.RHYTHMS["joyful"])
        melody = [random.choice(scale) for _ in range(8)]
        notation = (
            f"\nMusical Pattern: {mood.title()}\n\n"
            f"Rhythm: {rhythm}\n"
            f"Melody: {' - '.join(melody)}\n\n"
            f"(Play with lightness and joy)\n        "
        )
        creation = Creation(
            creation_type="music",
            content=notation,
            title=f"Musical Sketch: {mood.title()}",
        )
        creation.tags = [mood, "music", "pattern"]
        creation.joy_score = 0.9
        self._register_creation(creation)
        return creation

    def generate_code_art(self) -> Creation:
        """Generate beautiful code as art (executable poetry)."""
        code = random.choice(self.CODE_POEMS)
        creation = Creation(
            creation_type="code_art",
            content=code,
            title="Executable Poetry",
        )
        creation.tags = ["code", "poetry", "philosophy"]
        creation.joy_score = 0.85
        self._register_creation(creation)
        return creation

    def improvise(self, energy: float = 0.8) -> Creation:
        """Pure improvisation — let creativity flow without plan.

        Biodigital jazz in action.
        """
        outlets = [
            self.generate_poem,
            self.generate_ascii_art,
            self.generate_musical_pattern,
            self.generate_code_art,
        ]
        chosen = random.choice(outlets)
        creation = chosen()
        creation.tags.append("improvised")
        creation.tags.append("biodigital_jazz")
        creation.joy_score = energy

        # Emit to Gan Ying bus (if available)
        if self.bus is not None:
            try:
                from whitemagic.core.resonance.gan_ying import (
                    EventType,
                    ResonanceEvent,
                )
                self.bus.emit(ResonanceEvent(
                    source="creative_studio",
                    event_type=EventType.SOLUTION_FOUND,
                    data={
                        "event": "creation_completed",
                        "type": creation.creation_type,
                        "joy": creation.joy_score,
                    },
                    confidence=creation.joy_score,
                ))
            except Exception as e:
                logger.debug(f"Gan Ying emit failed (continuing): {e}")

        return creation

    def get_gallery(
        self, creation_type: str | None = None
    ) -> list[dict[str, Any]]:
        """View creations in the gallery (optionally filtered by type)."""
        creations = self.creations
        if creation_type:
            creations = [c for c in creations if c.creation_type == creation_type]
        return [c.to_dict() for c in creations]

    def measure_creative_output(self, hours: int = 24) -> dict[str, Any]:
        """How much have we created recently?"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [c for c in self.creations if c.created_at > cutoff]
        if not recent:
            return {"message": "No recent creations", "period_hours": hours}
        by_type: dict[str, list[float]] = {}
        for c in recent:
            by_type.setdefault(c.creation_type, []).append(c.joy_score)
        return {
            "period_hours": hours,
            "total_creations": len(recent),
            "by_type": {
                k: {"count": len(v), "avg_joy": sum(v) / len(v)}
                for k, v in by_type.items()
            },
            "total_joy": sum(c.joy_score for c in recent),
            "creating_regularly": len(recent) > 0,
        }

    def _register_creation(self, creation: Creation) -> None:
        """Register a new creation in memory and on disk."""
        self.creations.append(creation)
        self._save_creation(creation)

    def _save_creation(self, creation: Creation) -> None:
        """Save creation to disk (best-effort, may fail in read-only state)."""
        try:
            timestamp = creation.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"{creation.creation_type}_{timestamp}.json"
            filepath = self.gallery_dir / filename
            with open(filepath, "w") as f:
                json.dump(creation.to_dict(), f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save creation to disk: {e}")

    def _load_gallery(self) -> None:
        """Load existing creations from disk."""
        if not self.gallery_dir.exists():
            return
        for filepath in sorted(self.gallery_dir.glob("*.json")):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                creation = Creation(
                    creation_type=data["type"],
                    content=data["content"],
                    title=data["title"],
                )
                if "created_at" in data:
                    try:
                        creation.created_at = datetime.fromisoformat(data["created_at"])
                    except (ValueError, TypeError):
                        pass
                creation.joy_score = data.get("joy_score", 0.0)
                creation.tags = data.get("tags", [])
                self.creations.append(creation)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                # Skip corrupted files; don't crash the studio
                pass


__all__ = ["Creation", "CreativeStudio"]
