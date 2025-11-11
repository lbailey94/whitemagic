"""Tests for terminal execution."""
import pytest
from pathlib import Path
import tempfile

from whitemagic.terminal import (
    Executor,
    Allowlist,
    Profile,
    AuditLogger,
    TerminalMCPTools,
    ExecutionMode
)

class TestExecutor:
    """Test Executor class."""
    
    def test_execute_success(self):
        executor = Executor(timeout=5)
        result = executor.execute("echo", ["test"])
        
        assert result.exit_code == 0
        assert "test" in result.stdout
        assert result.duration_ms > 0
        assert "echo test" in result.command
    
    def test_execute_failure(self):
        executor = Executor(timeout=5)
        result = executor.execute("false")
        
        assert result.exit_code != 0
    
    def test_timeout(self):
        executor = Executor(timeout=1)
        result = executor.execute("sleep", ["10"])
        
        assert result.exit_code == -1
        assert "Timeout" in result.stderr

class TestAllowlist:
    """Test Allowlist class."""
    
    def test_blocked_commands(self):
        al = Allowlist(Profile.AGENT)
        
        assert not al.is_allowed("rm")
        assert not al.is_allowed("sudo")
        assert not al.is_allowed("shutdown")
    
    def test_safe_commands(self):
        al = Allowlist(Profile.AGENT)
        
        assert al.is_allowed("ls")
        assert al.is_allowed("git status")
        assert al.is_allowed("cat")
    
    def test_write_operations(self):
        al = Allowlist(Profile.AGENT)
        
        assert al.requires_approval("git commit")
        assert al.requires_approval("npm install")
    
    def test_profiles(self):
        prod = Allowlist(Profile.PROD)
        dev = Allowlist(Profile.DEV)
        
        # Prod is stricter
        assert prod.is_allowed("ls")
        assert not prod.is_allowed("git commit")
        
        # Dev is more permissive
        assert dev.is_allowed("ls")
        assert dev.is_allowed("git commit")

class TestAuditLogger:
    """Test AuditLogger class."""
    
    def test_log_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(Path(tmpdir))
            run_id = logger.log("echo test", 0, 15.5, "corr_123", "user")
            
            assert run_id is not None
            assert len(run_id) == 8
            
            # Check log file exists
            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) == 1

class TestTerminalMCPTools:
    """Test TerminalMCPTools class."""
    
    def test_exec_read_success(self):
        tools = TerminalMCPTools()
        result = tools.exec_read("echo", ["test"])
        
        assert result["exit_code"] == 0
        assert "test" in result["stdout"]
        assert "run_id" in result
    
    def test_exec_read_blocked(self):
        tools = TerminalMCPTools()
        result = tools.exec_read("rm", ["-rf", "/"])
        
        assert "error" in result
        assert not result["allowed"]
    
    def test_profile_enforcement(self):
        prod_tools = TerminalMCPTools(profile=Profile.PROD)
        
        # Read-only should work
        result = prod_tools.exec_read("ls")
        assert result["exit_code"] == 0

class TestModels:
    """Test Pydantic models."""
    
    def test_execution_request(self):
        from whitemagic.terminal.models import ExecutionRequest
        
        req = ExecutionRequest(cmd="ls", args=["-la"])
        assert req.mode == ExecutionMode.READ
        assert req.timeout_ms == 30000
    
    def test_execution_mode(self):
        assert ExecutionMode.READ.value == "read"
        assert ExecutionMode.WRITE.value == "write"
        assert ExecutionMode.INTERACTIVE.value == "interactive"
