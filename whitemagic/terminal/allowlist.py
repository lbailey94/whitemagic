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
    
    def is_allowed(self, cmd: str, args: Optional[List[str]] = None) -> bool:
        """Check if command is allowed.
        
        Args:
            cmd: Command name (e.g., "git")
            args: Command arguments (e.g., ["status"])
        
        Returns:
            True if command is allowed, False otherwise
        """
        # Normalize command: join cmd + args for matching
        full_cmd = cmd
        if args:
            full_cmd = cmd + " " + " ".join(args)
        
        # Always block dangerous commands (check base command)
        if any(cmd.startswith(blocked) for blocked in self.BLOCKED):
            return False
        
        # Profile-specific logic
        if self.profile == Profile.PROD:
            # Prod: only explicit READ_ONLY commands
            return full_cmd in self.READ_ONLY or cmd in self.READ_ONLY
        
        if self.profile == Profile.AGENT:
            # Agent: READ_ONLY + WRITE_OPS
            return (full_cmd in self.READ_ONLY or cmd in self.READ_ONLY or 
                    full_cmd in self.WRITE_OPS or cmd in self.WRITE_OPS)
        
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
