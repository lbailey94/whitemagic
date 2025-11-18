"""Terminal execution API endpoints."""

from fastapi import APIRouter, HTTPException, Request

from ...terminal import ExecutionMode, Profile, TerminalMCPTools
from ...terminal.approver import Approver
from ...terminal.models import ExecutionRequest, ExecutionResponse
from ..dependencies import CurrentUser

router = APIRouter(prefix="/exec", tags=["Terminal"])

# Separate instance for read-only operations
_terminal_tools_readonly = TerminalMCPTools(profile=Profile.PROD)


@router.post("/read", response_model=ExecutionResponse)
async def execute_read(request: ExecutionRequest, user: CurrentUser):
    """Execute read-only command using PROD profile (strict read-only allowlist)."""
    if request.mode != ExecutionMode.READ:
        raise HTTPException(400, "Only READ mode allowed on this endpoint")

    result = _terminal_tools_readonly.exec_read(
        cmd=request.cmd,
        args=request.args,
        cwd=request.cwd,
        env=request.env,
        stdin=request.stdin,
        correlation_id=request.correlation_id,
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
        mode="read",
    )


@router.post("/", response_model=ExecutionResponse)
async def execute_command_full(
    payload: ExecutionRequest,
    http_request: Request,
    user: CurrentUser,
):
    """
    Execute command (read or write with approval).

    Write operations require X-Confirm-Write-Operation: confirmed header.
    """
    # For read-only, delegate to read endpoint
    if payload.mode == ExecutionMode.READ:
        return await execute_read(payload, user)

    # Write mode requires confirmation header
    # (In API context, this replaces interactive approval)
    if payload.mode == ExecutionMode.WRITE:
        confirmed = http_request.headers.get("X-Confirm-Write-Operation", "").lower() == "confirmed"
        if not confirmed:
            raise HTTPException(
                403,
                "Write operations require header X-Confirm-Write-Operation: confirmed",
            )

        tools = TerminalMCPTools(profile=Profile.AGENT, approver=Approver(auto_approve=True))
        result = await tools.execute_command(
            cmd=payload.cmd,
            args=payload.args,
            mode=payload.mode,
            cwd=payload.cwd,
            timeout_ms=payload.timeout_ms,
            env=payload.env,
            stdin=payload.stdin,
            correlation_id=payload.correlation_id,
        )

        if not result.get("success"):
            error_msg = result.get("error", "Command execution failed")
            if "not approved" in error_msg.lower():
                raise HTTPException(403, error_msg)
            elif "not allowed" in error_msg.lower():
                raise HTTPException(403, error_msg)
            else:
                raise HTTPException(500, error_msg)

        return ExecutionResponse(
            exit_code=result["exit_code"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            duration_ms=result["duration_ms"],
            run_id=result["run_id"],
            command=result["command"],
            mode="write",
            approved=True,
        )
