"""WhiteMagic Terminal Tool - Structured execution for agents."""

from .executor import Executor, ExecutionResult
from .allowlist import Allowlist, Profile
from .audit import AuditLogger, AuditLog
from .mcp_tools import TerminalMCPTools, TOOLS
from .models import ExecutionMode, ExecutionRequest, ExecutionResponse

__all__ = [
    "Executor",
    "ExecutionResult",
    "Allowlist",
    "Profile",
    "AuditLogger",
    "AuditLog",
    "TerminalMCPTools",
    "TOOLS",
    "ExecutionMode",
    "ExecutionRequest",
    "ExecutionResponse",
]

__version__ = "0.1.0"
