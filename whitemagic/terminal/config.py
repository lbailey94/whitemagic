"""Configuration for terminal tool."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class TerminalConfig(BaseModel):
    """Terminal tool configuration."""

    # Execution settings
    default_profile: str = Field("agent", description="Default execution profile")
    default_timeout: int = Field(30, description="Default timeout in seconds")
    auto_approve: bool = Field(False, description="Auto-approve write operations")

    # Audit settings
    audit_enabled: bool = Field(True, description="Enable audit logging")
    audit_dir: Optional[Path] = Field(None, description="Audit log directory")

    # Allowlist customization
    custom_blocked: List[str] = Field(
        default_factory=list, description="Additional blocked commands"
    )
    custom_allowed: List[str] = Field(
        default_factory=list, description="Additional allowed commands"
    )

    # Safety settings
    require_approval_for_write: bool = Field(True, description="Require approval for write ops")
    allow_interactive: bool = Field(False, description="Allow interactive commands")

    @classmethod
    def from_env(cls) -> "TerminalConfig":
        """Load configuration from environment."""
        return cls(
            default_profile=os.getenv("WM_EXEC_PROFILE", "agent"),
            default_timeout=int(os.getenv("WM_EXEC_TIMEOUT", "30")),
            auto_approve=os.getenv("WM_AUTO_APPROVE", "false").lower() == "true",
            audit_enabled=os.getenv("WM_AUDIT_ENABLED", "true").lower() == "true",
        )

    def save(self, path: Optional[Path] = None):
        """Save configuration to file."""
        if path is None:
            path = Path.home() / ".whitemagic" / "terminal_config.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "TerminalConfig":
        """Load configuration from file."""
        if path is None:
            path = Path.home() / ".whitemagic" / "terminal_config.json"

        if not path.exists():
            return cls.from_env()

        with open(path) as f:
            return cls.model_validate_json(f.read())
