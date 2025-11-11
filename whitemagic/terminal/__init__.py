"""WhiteMagic Terminal Tool - Structured execution for agents."""

from .executor import Executor, ExecutionResult
from .allowlist import Allowlist, Profile
from .audit import AuditLogger, AuditLog
from .mcp_tools import TerminalMCPTools, TOOLS

__all__ = [
    "Executor",
    "ExecutionResult",
    "Allowlist",
    "Profile",
    "AuditLogger",
    "AuditLog",
    "TerminalMCPTools",
    "TOOLS",
]

__version__ = "0.1.0"
