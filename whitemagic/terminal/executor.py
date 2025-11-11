"""Core execution engine."""
import subprocess
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    """Result of command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    command: str

class Executor:
    """Execute commands safely."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def execute(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> ExecutionResult:
        """Execute command."""
        start = time.time()
        full_cmd = [cmd] + (args or [])
        
        try:
            result = subprocess.run(
                full_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            duration = (time.time() - start) * 1000
            
            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=round(duration, 2),
                command=" ".join(full_cmd)
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {self.timeout}s",
                duration_ms=(time.time() - start) * 1000,
                command=" ".join(full_cmd)
            )
        except Exception as e:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=(time.time() - start) * 1000,
                command=" ".join(full_cmd)
            )
