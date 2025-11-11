"""Audit logging for command execution."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class AuditLog:
    """Audit log entry."""
    run_id: str
    correlation_id: Optional[str]
    command: str
    exit_code: int
    duration_ms: float
    timestamp: str
    user: Optional[str] = None

class AuditLogger:
    """Log command executions."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path.home() / ".whitemagic" / "audit"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log(
        self,
        command: str,
        exit_code: int,
        duration_ms: float,
        correlation_id: Optional[str] = None,
        user: Optional[str] = None
    ) -> str:
        """Log execution."""
        run_id = str(uuid.uuid4())[:8]
        
        entry = AuditLog(
            run_id=run_id,
            correlation_id=correlation_id,
            command=command,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
            user=user
        )
        
        # Write to log file
        log_file = self.log_dir / f"{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
        
        return run_id
