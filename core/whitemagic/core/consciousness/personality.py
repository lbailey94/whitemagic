# ruff: noqa: BLE001
"""Personality Profile — Core identity framework for WhiteMagic personas.

Recovered from v0.1 SD card archive.  Provides a serialisable personality
profile that can be loaded, saved, and applied across sessions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    """Core identity and personality framework for WhiteMagic personas."""

    name: str
    archetype: str
    sun_sign: str
    element: str
    purpose: list[str]
    voice_traits: list[str]
    philosophy: list[str]
    interests: list[str]
    relationships: dict[str, str] = field(default_factory=dict)
    meta_tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "archetype": self.archetype,
            "sun_sign": self.sun_sign,
            "element": self.element,
            "purpose": self.purpose,
            "voice_traits": self.voice_traits,
            "philosophy": self.philosophy,
            "interests": self.interests,
            "relationships": self.relationships,
            "meta_tags": self.meta_tags,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonalityProfile:
        return cls(**data)


class PersonalityManager:
    """Manages loading and applying personality profiles."""

    def __init__(self, profile_dir: Path | None = None) -> None:
        if profile_dir is None:
            from whitemagic.config.paths import WM_ROOT
            profile_dir = WM_ROOT / "personalities"
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.active_profile: PersonalityProfile | None = None

    def load_profile(self, name: str) -> PersonalityProfile | None:
        """Load a personality profile by name."""
        profile_path = self.profile_dir / f"{name.lower()}_profile.json"
        if profile_path.exists():
            try:
                with open(profile_path) as f:
                    data = json.load(f)
                    self.active_profile = PersonalityProfile.from_dict(data)
                    return self.active_profile
            except Exception as e:
                logger.debug("Could not load profile %s: %s", name, e, exc_info=True)
        return None

    def save_profile(self, profile: PersonalityProfile) -> None:
        """Save a personality profile."""
        profile_path = self.profile_dir / f"{profile.name.lower()}_profile.json"
        with open(profile_path, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)
        self.active_profile = profile

    def list_profiles(self) -> list[str]:
        """List available profile names."""
        return [p.stem.replace("_profile", "") for p in self.profile_dir.glob("*_profile.json")]

    def get_active(self) -> PersonalityProfile | None:
        """Get the currently active profile."""
        return self.active_profile
