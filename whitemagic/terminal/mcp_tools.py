"""MCP tools for terminal execution."""

from typing import Any, Dict, List, Optional

from .allowlist import Allowlist, Profile
from .approver import Approver
from .audit import AuditLogger
from .executor import Executor
from .models import ApprovalRequest, ExecutionMode


class TerminalMCPTools:
    """MCP tools for terminal execution."""

    def __init__(
        self,
        profile: Profile = Profile.AGENT,
        audit_enabled: bool = True,
        approver: Optional[Approver] = None,
    ):
        self.executor = Executor()
        self.allowlist = Allowlist(profile)
        self.audit = AuditLogger() if audit_enabled else None
        self.approver = approver or Approver()  # Default approver

    def exec_read(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        stdin: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute read-only command (MCP tool).

        Args:
            cmd: Command to execute
            args: Command arguments
            cwd: Working directory
            env: Environment variables to pass to command
            stdin: Input to pipe to command
            correlation_id: Correlation ID for audit logging
        """
        full_cmd = cmd + (" " + " ".join(args) if args else "")

        # Check allowlist (pass args)
        if not self.allowlist.is_allowed(cmd, args):
            return {"error": "Command not allowed", "command": full_cmd, "allowed": False}

        # Execute with env and stdin support
        result = self.executor.execute(cmd, args, cwd, env=env, stdin=stdin)

        # Audit
        if self.audit:
            run_id = self.audit.log(full_cmd, result.exit_code, result.duration_ms, correlation_id)
        else:
            run_id = None

        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "run_id": run_id,
            "command": full_cmd,
        }

    async def execute_command(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        mode: ExecutionMode = ExecutionMode.READ,
        cwd: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        stdin: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute command with mode support (read or write).

        Write mode requires approval before execution.

        Args:
            cmd: Command to execute
            args: Command arguments
            mode: Execution mode (READ or WRITE)
            cwd: Working directory
            timeout_ms: Timeout in milliseconds
            env: Environment variables to pass to command
            stdin: Input to pipe to command
            correlation_id: Correlation ID for audit logging
        """
        args = args or []
        full_cmd = cmd + (" " + " ".join(args) if args else "")

        # Check allowlist
        if not self.allowlist.is_allowed(cmd, args):
            return {
                "success": False,
                "error": "Command not allowed by allowlist",
                "command": full_cmd,
                "allowed": False,
            }

        # Check if write mode requires approval
        if mode == ExecutionMode.WRITE:
            approval_request = ApprovalRequest(command=full_cmd, mode=mode, cwd=cwd)

            approval = await self.approver.request_approval(approval_request)

            if not approval.approved:
                return {
                    "success": False,
                    "error": f"Operation not approved: {approval.reason}",
                    "command": full_cmd,
                    "approved": False,
                }

        # Execute with env and stdin support
        result = self.executor.execute(cmd, args, cwd, timeout_ms=timeout_ms, env=env, stdin=stdin)

        # Audit
        if self.audit:
            run_id = self.audit.log(full_cmd, result.exit_code, result.duration_ms, correlation_id)
        else:
            run_id = None

        return {
            "success": result.exit_code == 0,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "run_id": run_id,
            "command": full_cmd,
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
                    "description": "Command arguments",
                },
                "cwd": {"type": "string", "description": "Working directory"},
                "correlation_id": {"type": "string", "description": "Correlation ID"},
            },
            "required": ["cmd"],
        },
    }
]
