"""Terminal execution API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from ...terminal import (
    TerminalMCPTools,
    Profile,
    ExecutionMode
)
from ...terminal.models import ExecutionRequest, ExecutionResponse
from ..dependencies import CurrentUser

router = APIRouter(prefix="/exec", tags=["Terminal"])

# Global instance (can be configured per-user later)
_terminal_tools = TerminalMCPTools(profile=Profile.AGENT)

@router.post("/read", response_model=ExecutionResponse)
async def execute_read(
    request: ExecutionRequest,
    user: CurrentUser
):
    """Execute read-only command."""
    if request.mode \!= ExecutionMode.READ:
        raise HTTPException(400, "Only READ mode allowed on this endpoint")
    
    result = _terminal_tools.exec_read(
        cmd=request.cmd,
        args=request.args,
        cwd=request.cwd,
        correlation_id=request.correlation_id
    )
    
    if "error" in result:
        raise HTTPException(403, result["error"])
    
    return ExecutionResponse(
        exit_code=result["exit_code"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        duration_ms=result["duration_ms"],
        run_id=result["run_id"],
        command=result["command"],
        mode="read"
    )

@router.post("/", response_model=ExecutionResponse)
async def execute_command(
    request: ExecutionRequest,
    user: CurrentUser
):
    """Execute command (read or write with approval)."""
    # For now, delegate to exec_read for read-only
    if request.mode == ExecutionMode.READ:
        return await execute_read(request, user)
    
    # Write mode requires approval (Phase 2C.5)
    raise HTTPException(501, "Write mode not yet implemented")
