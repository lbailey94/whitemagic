# ruff: noqa: BLE001
"""Local User Profiles — Multi-user isolation for WhiteMagic.

Provides per-user state isolation without external authentication.
Each user gets their own namespace under ``WM_ROOT/users/<user_id>/`` with
separate galaxy databases, profiles, and memory spaces.

Design:
- No passwords, no API keys — purely local identification
- Default user is ``"local"`` (backward compat with single-user mode)
- User IDs are sanitized for filesystem safety
- Profile data stored as JSON at ``WM_ROOT/users/<user_id>/profile.json``
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

_DEFAULT_USER = "local"


def _sanitize_user_id(user_id: str) -> str:
    """Sanitize a user ID for filesystem safety.

    Allows alphanumeric, hyphens, underscores. Everything else becomes ``_``.
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)[:64] or _DEFAULT_USER


def get_users_dir() -> Path:
    """Return the root directory for all user state."""
    return WM_ROOT / "users"


def get_user_dir(user_id: str) -> Path:
    """Return the state directory for a specific user."""
    return get_users_dir() / _sanitize_user_id(user_id)


@dataclass
class UserProfile:
    """Local user profile — no auth, just identity."""

    user_id: str
    display_name: str = ""
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    galaxies_created: int = 0
    preferences: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UserProfile:
        """Deserialize from dict."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def user_dir(self) -> Path:
        """Filesystem directory for this user."""
        return get_user_dir(self.user_id)

    @property
    def profile_path(self) -> Path:
        """Path to this user's profile JSON."""
        return self.user_dir / "profile.json"

    @property
    def galaxies_dir(self) -> Path:
        """Directory for this user's galaxy databases."""
        return self.user_dir / "galaxies"

    @property
    def memory_dir(self) -> Path:
        """Directory for this user's memory databases."""
        return self.user_dir / "memory"


class LocalProfileManager:
    """Manages local user profiles with filesystem isolation.

    Singleton — one instance per process.
    """

    _instance: LocalProfileManager | None = None

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._load_all_profiles()

    @classmethod
    def get_instance(cls) -> LocalProfileManager:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_all_profiles(self) -> None:
        """Load all existing user profiles from disk."""
        users_dir = get_users_dir()
        if not users_dir.exists():
            return
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
            profile_path = user_dir / "profile.json"
            if profile_path.exists():
                try:
                    data = _json_loads(profile_path.read_text(encoding="utf-8"))
                    profile = UserProfile.from_dict(data)
                    self._profiles[profile.user_id] = profile
                except Exception as e:
                    logger.debug("Failed to load profile in %s: %s", user_dir, e)

    def get_or_create(self, user_id: str | None = None) -> UserProfile:
        """Get an existing profile or create a new one.

        Args:
            user_id: User identifier. Defaults to ``"local"`` if None or empty.

        Returns:
            UserProfile for the given user.
        """
        uid = _sanitize_user_id(user_id or _DEFAULT_USER)
        if uid in self._profiles:
            profile = self._profiles[uid]
            profile.last_active = time.time()
            self._save_profile(profile)
            return profile

        # Create new profile
        profile = UserProfile(
            user_id=uid,
            display_name=uid,
        )
        profile.user_dir.mkdir(parents=True, exist_ok=True)
        profile.galaxies_dir.mkdir(parents=True, exist_ok=True)
        profile.memory_dir.mkdir(parents=True, exist_ok=True)
        self._profiles[uid] = profile
        self._save_profile(profile)
        logger.info("Created local profile for user '%s'", uid)
        return profile

    def _save_profile(self, profile: UserProfile) -> None:
        """Persist a single profile to disk."""
        try:
            profile.user_dir.mkdir(parents=True, exist_ok=True)
            profile.profile_path.write_text(
                _json_dumps(profile.to_dict(), indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save profile for '%s': %s", profile.user_id, e)

    def list_profiles(self) -> list[dict[str, Any]]:
        """List all known user profiles."""
        return [
            p.to_dict() for p in sorted(self._profiles.values(), key=lambda x: x.user_id)
        ]

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Get a profile by user ID, or None if not found."""
        uid = _sanitize_user_id(user_id)
        return self._profiles.get(uid)

    def delete_profile(self, user_id: str) -> bool:
        """Remove a user profile from memory (does NOT delete files on disk).

        Args:
            user_id: User to remove.

        Returns:
            True if the profile was found and removed.
        """
        uid = _sanitize_user_id(user_id)
        if uid == _DEFAULT_USER:
            raise ValueError("Cannot delete the default 'local' user profile")
        return self._profiles.pop(uid, None) is not None

    @property
    def default_user_id(self) -> str:
        """Return the default user ID."""
        return _DEFAULT_USER


def get_profile_manager() -> LocalProfileManager:
    """Get the global LocalProfileManager singleton."""
    return LocalProfileManager.get_instance()


def resolve_user_id(user_id: str | None) -> str:
    """Resolve a user ID, defaulting to 'local' if None or empty.

    Args:
        user_id: Raw user ID from header, parameter, or None.

    Returns:
        Sanitized user ID string.
    """
    return _sanitize_user_id(user_id or _DEFAULT_USER)
