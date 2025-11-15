"""Tests for terminal execution."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure local package is used even if another version is installed
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
        assert al.is_allowed("git", ["status"])
        assert al.is_allowed("cat")
    
    def test_write_operations(self):
        al = Allowlist(Profile.AGENT)
        
        assert al.requires_approval("git", ["commit"])
        assert al.requires_approval("npm install")
    
    def test_profiles(self):
        prod = Allowlist(Profile.PROD)
        dev = Allowlist(Profile.DEV)
        
        # Prod is stricter
        assert prod.is_allowed("ls")
        assert not prod.is_allowed("git", ["commit"])
        
        # Dev is more permissive
        assert dev.is_allowed("ls")
        assert dev.is_allowed("git", ["commit"])
    
    def test_prod_blocks_git_write(self):
        prod = Allowlist(Profile.PROD)
        
        assert not prod.is_allowed("git", ["commit"])
        assert prod.is_allowed("git", ["status"])

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
    
    @pytest.mark.asyncio
    async def test_write_requires_approval(self):
        tools = TerminalMCPTools(profile=Profile.AGENT)
        result = await tools.execute_command("ls", mode=ExecutionMode.WRITE)
        assert result["success"] is False
        assert "approved" in result["error"].lower()
        
        from whitemagic.terminal.approver import Approver
        approved_tools = TerminalMCPTools(
            profile=Profile.AGENT,
            approver=Approver(auto_approve=True)
        )
        approved = await approved_tools.execute_command(
            "echo",
            args=["ok"],
            mode=ExecutionMode.WRITE
        )
        assert approved["success"] is True

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
