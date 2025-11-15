# Terminal Tool Usage Guide

**Version**: 0.1.0  
**Status**: Production Ready

---

## Quick Start

### Installation

Terminal tool is included with WhiteMagic. No additional setup required for basic usage.

```bash
pip install whitemagic  # Includes terminal tool
```

### Basic Usage

```bash
# Execute a read-only command
wm exec run ls -la

# Check audit log
wm exec audit --days 7

# Execute with specific profile
wm exec run git status --profile dev
```

---

## Profiles

Terminal tool supports 4 execution profiles:

| Profile | Use Case | Restrictions |
|---------|----------|--------------|
| **dev** | Development | Minimal restrictions |
| **ci** | CI/CD pipelines | Moderate restrictions |
| **agent** | AI agents (default) | Read-only + approved writes |
| **prod** | Production | Read-only only |

### Setting Profile

```bash
# Via CLI
wm exec run ls --profile prod

# Via environment
export WM_EXEC_PROFILE=dev

# Via config file
echo '{"default_profile": "ci"}' > ~/.whitemagic/terminal_config.json
```

---

## Configuration

### Environment Variables

```bash
# Profile (dev, ci, agent, prod)
export WM_EXEC_PROFILE=agent

# Timeout in seconds
export WM_EXEC_TIMEOUT=30

# Auto-approve write operations (use with caution\!)
export WM_AUTO_APPROVE=false

# Enable/disable audit logging
export WM_AUDIT_ENABLED=true
```

### Config File

Location: `~/.whitemagic/terminal_config.json`

```json
{
  "default_profile": "agent",
  "default_timeout": 30,
  "auto_approve": false,
  "audit_enabled": true,
  "require_approval_for_write": true,
  "custom_blocked": ["dangerous-cmd"],
  "custom_allowed": ["safe-cmd"]
}
```

---

## Allowlist System

### Blocked Commands (Always)

- `rm`, `rmdir`, `dd`, `mkfs`
- `chmod`, `chown`, `sudo`, `su`
- `shutdown`, `reboot`, `halt`
- `kill`, `killall`, `pkill`

### Read-Only Commands (Safe)

- File: `ls`, `cat`, `head`, `tail`, `less`, `more`
- Search: `find`, `fd`, `rg`, `grep`, `awk`, `sed`
- Git: `git log`, `git show`, `git diff`, `git status`
- System: `ps`, `top`, `df`, `du`, `wc`, `stat`
- Misc: `echo`, `printf`, `env`, `which`, `type`

### Write Operations (Require Approval)

- Git: `git add`, `git commit`, `git push`
- Files: `cp`, `mv`, `mkdir`, `touch`
- Packages: `npm install`, `pip install`, `cargo build`

---

## API Usage

### REST API

```bash
# Execute read-only command
curl -X POST http://localhost:8000/api/v1/exec/read \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "cmd": "ls",
    "args": ["-la"],
    "cwd": "/workspace",
    "mode": "read"
  }'

# Execute write command (requires confirmation header)
curl -X POST http://localhost:8000/api/v1/exec \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Confirm-Write-Operation: confirmed" \
  -d '{
    "cmd": "git",
    "args": ["commit", "-m", "Update docs"],
    "mode": "write"
  }'
```

### Python SDK

```python
from whitemagic.terminal import TerminalMCPTools, Profile

# Create executor
tools = TerminalMCPTools(profile=Profile.AGENT)

# Execute command
result = tools.exec_read("ls", ["-la"], cwd="/workspace")

print(f"Exit code: {result['exit_code']}")
print(f"Output: {result['stdout']}")
print(f"Run ID: {result['run_id']}")
```

---

## Audit Log

### Viewing Logs

```bash
# Last 7 days
wm exec audit

# Last 30 days
wm exec audit --days 30

# Limit results
wm exec audit --limit 100
```

### Log Format

Logs are stored in `~/.whitemagic/audit/*.jsonl` (one file per day).

```json
{
  "run_id": "abc12345",
  "correlation_id": "task_xyz",
  "command": "git status",
  "exit_code": 0,
  "duration_ms": 42.5,
  "timestamp": "2025-11-11T13:45:00",
  "user": "alice"
}
```

---

## Examples

### Example 1: Search Code

```bash
wm exec run rg TODO --json
```

### Example 2: Git Operations

```bash
wm exec run git log --oneline -10
wm exec run git diff main..HEAD
```

### Example 3: File Inspection

```bash
wm exec run cat src/main.py
wm exec run head -20 README.md
```

### Example 4: System Info

```bash
wm exec run ps aux
wm exec run df -h
```

---

## Safety Best Practices

1. **Use Appropriate Profile**: Start with `prod` or `agent`, not `dev`
2. **Review Audit Logs**: Check `wm exec audit` regularly
3. **Never Auto-Approve in Production**: Keep `WM_AUTO_APPROVE=false`
4. **Limit Scope**: Use `--cwd` to restrict working directory
5. **Custom Allowlist**: Add your blocked commands to config

---

## Troubleshooting

### Command Blocked

```
❌ Error: Command not allowed
```

**Solution**: Check if command is in blocked list. Use appropriate profile or add to `custom_allowed` in config.

### Timeout

```
Timeout after 30s
```

**Solution**: Increase timeout via `WM_EXEC_TIMEOUT` or `--timeout` flag.

### Permission Denied

```
Exit code: 1, Permission denied
```

**Solution**: Check file permissions. Terminal tool runs with user's permissions.

---

## MCP Integration

Terminal tool provides MCP tools for AI agents:

```python
# MCP tool definition
{
  "name": "exec_read",
  "description": "Execute read-only command",
  "inputSchema": {
    "type": "object",
    "properties": {
      "cmd": {"type": "string"},
      "args": {"type": "array"},
      "cwd": {"type": "string"}
    }
  }
}
```

---

## Next Steps

- Read [API Documentation](./TERMINAL_TOOL_API.md)
- See [Examples](../examples/terminal_tool_examples.py)
- Check [Design Document](./TERMINAL_TOOL_DESIGN.md)
