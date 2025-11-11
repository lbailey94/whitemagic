"""MCP tools for terminal execution."""
from typing import Optional, List, Dict, Any
from .executor import Executor
from .allowlist import Allowlist, Profile
from .audit import AuditLogger

class TerminalMCPTools:
    """MCP tools for terminal execution."""
    
    def __init__(
        self,
        profile: Profile = Profile.AGENT,
        audit_enabled: bool = True
    ):
        self.executor = Executor()
        self.allowlist = Allowlist(profile)
        self.audit = AuditLogger() if audit_enabled else None
    
    def exec_read(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute read-only command (MCP tool)."""
        full_cmd = cmd + (" " + " ".join(args) if args else "")
        
        # Check allowlist
        if not self.allowlist.is_allowed(cmd):
            return {
                "error": "Command not allowed",
                "command": full_cmd,
                "allowed": False
            }
        
        # Execute
        result = self.executor.execute(cmd, args, cwd)
        
        # Audit
        if self.audit:
            run_id = self.audit.log(
                full_cmd,
                result.exit_code,
                result.duration_ms,
                correlation_id
            )
        else:
            run_id = None
        
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "run_id": run_id,
            "command": full_cmd
        }

# Tool definitions for MCP server
TOOLS = [
    {
        "name": "exec_read",
        "description": "Execute read-only command (ls, cat, git status, etc)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "Command to execute"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command arguments"
                },
                "cwd": {"type": "string", "description": "Working directory"},
                "correlation_id": {"type": "string", "description": "Correlation ID"}
            },
            "required": ["cmd"]
        }
    }
]
