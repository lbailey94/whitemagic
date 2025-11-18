"""Command allowlist system with profiles."""

from enum import Enum
from typing import List, Optional, Set


class Profile(str, Enum):
    """Execution profiles."""

    DEV = "dev"  # Development (relaxed)
    CI = "ci"  # CI/CD
    AGENT = "agent"  # AI agent
    PROD = "prod"  # Production (strict)


class Allowlist:
    """Command allowlist with profiles."""

    # Always blocked
    BLOCKED = {
        "rm",
        "rmdir",
        "dd",
        "mkfs",
        "chmod",
        "chown",
        "sudo",
        "su",
        "shutdown",
        "reboot",
        "halt",
        "kill",
        "killall",
        "pkill",
    }

    # Read-only safe commands
    READ_ONLY = {
        # Basic commands (base only)
        "ls",
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "find",
        "fd",
        "rg",
        "grep",
        "awk",
        "sed",
        "ps",
        "top",
        "df",
        "du",
        "wc",
        "stat",
        "echo",
        "printf",
        "env",
        "which",
        "type",
        "pwd",
        # Git read operations (supports "git log", "git log -5", etc.)
        "git log",
        "git show",
        "git diff",
        "git status",
        "git branch",
        # Patterns for flexible matching
        "git*log*",
        "git*show*",
        "git*diff*",
        "git*status*",
        "git*branch*",
    }

    # Write operations (need approval)
    WRITE_OPS = {
        "git add",
        "git commit",
        "git push",
        "git pull",
        "git clone",
        "cp",
        "mv",
        "mkdir",
        "touch",
        "npm install",
        "pip install",
        "cargo build",
        "make",
    }

    def __init__(self, profile: Profile = Profile.AGENT):
        self.profile = profile

    def is_allowed(self, cmd: str, args: Optional[List[str]] = None) -> bool:
        """Check if command is allowed.

        Supports flexible matching:
        - Base command: "git" allows "git log", "git status", etc.
        - Command + verb: "git log" allows "git log -5", "git log --oneline", etc.
        - Patterns: "git*log*" matches "git log --graph"

        Args:
            cmd: Command name (e.g., "git")
            args: Command arguments (e.g., ["log", "-5"])

        Returns:
            True if command is allowed, False otherwise
        """
        args = args or []

        # Build variants for matching
        base_cmd = cmd
        cmd_with_verb = f"{cmd} {args[0]}" if args else cmd
        full_cmd = cmd + (" " + " ".join(args) if args else "")

        # Always block dangerous commands (check base command)
        if any(base_cmd.startswith(blocked) for blocked in self.BLOCKED):
            return False

        # Helper to check if command matches pattern
        def matches_pattern(pattern: str, test_cmd: str) -> bool:
            """Check if command matches pattern with wildcards."""
            if "*" not in pattern:
                return pattern == test_cmd
            # Simple wildcard matching
            parts = pattern.split("*")
            pos = 0
            for part in parts:
                if not part:
                    continue
                idx = test_cmd.find(part, pos)
                if idx == -1:
                    return False
                pos = idx + len(part)
            return True

        # Check against allowlist
        def is_in_set(cmd_set: Set[str]) -> bool:
            """Check if command matches any entry in set."""
            for allowed in cmd_set:
                # Exact match on full command
                if allowed == full_cmd:
                    return True
                # Base command match
                if allowed == base_cmd:
                    return True
                # Command + verb match
                if allowed == cmd_with_verb:
                    return True
                # Pattern match
                if matches_pattern(allowed, full_cmd):
                    return True
            return False

        # Profile-specific logic
        if self.profile == Profile.PROD:
            # Prod: only explicit READ_ONLY commands
            return is_in_set(self.READ_ONLY)

        if self.profile == Profile.AGENT:
            # Agent: READ_ONLY + WRITE_OPS
            return is_in_set(self.READ_ONLY) or is_in_set(self.WRITE_OPS)

        # Dev and CI allow most things (not blocked)
        return True

    def requires_approval(self, cmd: str, args: Optional[List[str]] = None) -> bool:
        """Check if command requires approval.

        Args:
            cmd: Command name
            args: Command arguments

        Returns:
            True if approval required, False otherwise
        """
        full_cmd = cmd
        if args:
            full_cmd = cmd + " " + " ".join(args)

        return full_cmd in self.WRITE_OPS or cmd in self.WRITE_OPS
