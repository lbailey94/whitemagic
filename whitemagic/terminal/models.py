"""Data models for terminal execution."""
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class ExecutionMode(str, Enum):
    """Execution mode."""
    READ = "read"           # Read-only (safe)
    WRITE = "write"         # Write operations (requires approval)
    INTERACTIVE = "interactive"  # Interactive commands

class ExecutionRequest(BaseModel):
    """Request to execute command."""
    cmd: str = Field(..., description="Command to execute")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    cwd: Optional[str] = Field(None, description="Working directory")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    stdin: Optional[str] = Field(None, description="Standard input")
    timeout_ms: int = Field(30000, description="Timeout in milliseconds")
    mode: ExecutionMode = Field(ExecutionMode.READ, description="Execution mode")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

class ExecutionResponse(BaseModel):
    """Response from command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    run_id: Optional[str] = None
    command: str
    mode: str
    approved: bool = True

class ApprovalRequest(BaseModel):
    """Request for approval."""
    command: str
    mode: ExecutionMode
    cwd: Optional[str] = None
    preview: Optional[str] = None  # Patch preview for write ops

class ApprovalResponse(BaseModel):
    """Approval response."""
    approved: bool
    reason: Optional[str] = None
