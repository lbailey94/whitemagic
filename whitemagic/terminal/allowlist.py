"""Command allowlist system with profiles."""
from typing import List, Set, Optional
from enum import Enum

class Profile(str, Enum):
    """Execution profiles."""
    DEV = "dev"          # Development (relaxed)
    CI = "ci"            # CI/CD
    AGENT = "agent"      # AI agent
    PROD = "prod"        # Production (strict)

class Allowlist:
    """Command allowlist with profiles."""
    
    # Always blocked
    BLOCKED = {
        "rm", "rmdir", "dd", "mkfs",
        "chmod", "chown", "sudo", "su",
        "shutdown", "reboot", "halt",
        "kill", "killall", "pkill",
    }
    
    # Read-only safe commands
    READ_ONLY = {
        "ls", "cat", "head", "tail", "less", "more",
        "find", "fd", "rg", "grep", "awk", "sed",
        "git log", "git show", "git diff", "git status",
        "ps", "top", "df", "du", "wc", "stat",
        "echo", "printf", "env", "which", "type",
    }
    
    # Write operations (need approval)
    WRITE_OPS = {
        "git add", "git commit", "git push",
        "cp", "mv", "mkdir", "touch",
        "npm install", "pip install", "cargo build",
    }
    
    def __init__(self, profile: Profile = Profile.AGENT):
        self.profile = profile
    
    def is_allowed(self, cmd: str) -> bool:
        """Check if command is allowed."""
        # Always block dangerous commands
        if any(cmd.startswith(blocked) for blocked in self.BLOCKED):
            return False
        
        # Profile-specific logic
        if self.profile == Profile.PROD:
            return cmd in self.READ_ONLY
        
        if self.profile == Profile.AGENT:
            return cmd in self.READ_ONLY or cmd in self.WRITE_OPS
        
        # Dev and CI allow most things
        return True
    
    def requires_approval(self, cmd: str) -> bool:
        """Check if command requires approval."""
        return cmd in self.WRITE_OPS
