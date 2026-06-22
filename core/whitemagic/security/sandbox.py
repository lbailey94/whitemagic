"""Adaptive Code Execution Sandbox.

Provides a secure micro-virtualized adapter (via Docker)
for agents to execute and test untrusted generated code safely.
"""

import asyncio
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SandboxResult:
    """Result from a sandbox execution."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timeout: bool = False
    error: str | None = None

class AdaptiveSandbox:
    """Wrapper around Docker-based ephemeral sandboxes for AI Code Execution."""

    def __init__(
        self,
        image: str = "python:3.11-alpine",
        max_cpus: float = 0.5,
        max_memory: str = "256m",
        network_disabled: bool = True,
        default_timeout_sec: float = 10.0,
    ):
        """Initialize the sandbox environment constraints."""
        self.image = image
        self.max_cpus = max_cpus
        self.max_memory = max_memory
        self.network_disabled = network_disabled
        self.default_timeout_sec = default_timeout_sec

    async def execute_python(self, code: str, timeout_sec: float | None = None) -> SandboxResult:
        """Execute a Python script securely in an isolated container.

        Args:
            code: The raw python source code to execute.
            timeout_sec: Execution termination TTL.

        Returns:
            SandboxResult with stdout, stderr, and exit_code.
        """
        timeout = timeout_sec or self.default_timeout_sec
        container_name = f"wm_sandbox_{uuid.uuid4().hex[:8]}"

        # We need a secure, temporary directory to drop the code in
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "agent_payload.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Build Docker command
            cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                f"--cpus={self.max_cpus}",
                f"--memory={self.max_memory}",
            ]

            if self.network_disabled:
                cmd.append("--network=none")

            # Read-only mount of the script into the container
            cmd.extend([
                "-v", f"{script_path}:/app/agent_payload.py:ro",
                "-w", "/app",
                self.image,
                "python", "/app/agent_payload.py"
            ])

            start_time = asyncio.get_event_loop().time()
            try:
                # Execute asynchronously
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    end_time = asyncio.get_event_loop().time()

                    return SandboxResult(
                        stdout=stdout_bytes.decode(errors='replace'),
                        stderr=stderr_bytes.decode(errors='replace'),
                        exit_code=process.returncode or 0,
                        execution_time_ms=(end_time - start_time) * 1000,
                    )

                except TimeoutError:
                    # Kill the runaway container directly via docker stop
                    kill_cmd = await asyncio.create_subprocess_exec(
                        "docker", "rm", "-f", container_name,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await kill_cmd.communicate()
                    end_time = asyncio.get_event_loop().time()

                    return SandboxResult(
                        stdout="",
                        stderr="Execution halted: Time limit exceeded (Sandbox Timeout)",
                        exit_code=-1,
                        execution_time_ms=(end_time - start_time) * 1000,
                        timeout=True
                    )

            except (FileNotFoundError, PermissionError) as e:
                # Docker not installed or permission issues
                end_time = asyncio.get_event_loop().time()
                logger.error("Docker error in sandbox: %s", e)
                return SandboxResult(
                    stdout="",
                    stderr=f"Docker unavailable: {str(e)}",
                    exit_code=-2,
                    execution_time_ms=(end_time - start_time) * 1000,
                    error=f"Docker error: {type(e).__name__}"
                )
            except OSError as e:
                # Process creation or execution errors
                end_time = asyncio.get_event_loop().time()
                logger.error("Process error in sandbox: %s", e)
                return SandboxResult(
                    stdout="",
                    stderr=f"Process error: {str(e)}",
                    exit_code=-3,
                    execution_time_ms=(end_time - start_time) * 1000,
                    error=f"Process error: {type(e).__name__}"
                )
            except Exception as e:
                # Unexpected error - log and return
                end_time = asyncio.get_event_loop().time()
                logger.exception("Unexpected error in sandbox execution")
                return SandboxResult(
                    stdout="",
                    stderr=f"Unexpected sandbox error: {type(e).__name__}",
                    exit_code=-4,
                    execution_time_ms=(end_time - start_time) * 1000,
                    error=f"Unexpected error: {type(e).__name__}"
                )

# Singleton accessible instance
_default_sandbox = None

def get_sandbox() -> AdaptiveSandbox:
    """Retrieve or initialize the active isolated sandbox singleton."""
    global _default_sandbox
    if _default_sandbox is None:
        _default_sandbox = AdaptiveSandbox()
    return _default_sandbox
