---
name: wm-security
description: "Security, sandboxing, resource locks, MCP integrity, and immune system"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_room
    tools: [anti_loop_check, hermit_assess, hermit_check_access, hermit_mediate, sandbox_execute, sandbox_inspect, mcp_integrity, security_monitor]
    tags: [security, sandbox, resource, locks, integrity, immune, hermit]
---

# Security & Resource Management

Protect the system through sandboxing, resource locks, MCP integrity checks, and immune-system-style monitoring.

## When to Use

- Before executing untrusted code or commands
- When checking for recursive loops or runaway processes
- To verify MCP server integrity
- When setting up sandboxed execution environments
- To mediate resource conflicts between agents
- For hermit crab mode (isolated execution)

## How to Invoke

```python
# Check for anti-loop issues
wm(route="gana_room.anti_loop_check", args={})

# Sandbox execution
wm(route="gana_room.sandbox_execute", args={"command": "...", "timeout": 30})

# MCP integrity check
wm(route="gana_room.mcp_integrity", args={})

# Hermit crab access check
wm(route="gana_room.hermit_check_access", args={"resource": "..."})

# Security monitor
wm(route="gana_room.security_monitor", args={})
```

## Security Layers

1. **Sandbox** — Isolated execution for untrusted code
2. **Resource Locks** — Prevent concurrent access conflicts
3. **MCP Integrity** — Verify MCP server authenticity
4. **Anti-Loop** — Detect and break recursive tool calls
5. **Hermit Crab** — Isolated mode for sensitive operations
6. **Immune System** — Pattern detection for anomalies
