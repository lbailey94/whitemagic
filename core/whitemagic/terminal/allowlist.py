# ruff: noqa: BLE001
"""Command allowlist system with profiles."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Profile(StrEnum):
    """Execution profiles."""
    RESTRICTED = "restricted"
    STANDARD = "standard"
    ELEVATED = "elevated"


PROFILE_COMMANDS: dict[Profile, set[str]] = {
    Profile.RESTRICTED: {"ls", "cat", "head", "tail", "wc", "grep", "find", "echo"},
    Profile.STANDARD: {"ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
                       "python", "pip", "git", "ruff", "pytest", "mkdir", "cp", "mv"},
    Profile.ELEVATED: {"ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
                       "python", "pip", "git", "ruff", "pytest", "mkdir", "cp", "mv",
                       "rm", "chmod", "chown", "curl", "wget", "ssh", "scp"},
}


class Allowlist:
    """Command allowlist with profile-based access control."""

    def __init__(self, profile: Profile = Profile.STANDARD) -> None:
        self.profile = profile
        self._allowed: set[str] = set(PROFILE_COMMANDS.get(profile, set()))
        self._blocked: set[str] = set()

    def is_allowed(self, command: str) -> bool:
        """Check if a command is allowed."""
        base = command.split()[0] if command.split() else ""
        if base in self._blocked:
            return False
        return base in self._allowed

    def add(self, command: str) -> None:
        """Allow a command."""
        self._allowed.add(command)

    def block(self, command: str) -> None:
        """Block a command."""
        self._blocked.add(command)

    def set_profile(self, profile: Profile) -> None:
        """Change the execution profile."""
        self.profile = profile
        self._allowed = set(PROFILE_COMMANDS.get(profile, set()))

    def summary(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "allowed_count": len(self._allowed),
            "blocked_count": len(self._blocked),
        }
