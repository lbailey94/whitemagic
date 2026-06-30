---
name: wm-system-health
description: "System health checks, Rust backend status, state inspection, and ship readiness"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_root
    tools: [check, health_report, rust_audit, rust_status, rust_compress, state_summary, ship_check]
    tags: [system, health, rust, status, audit, ship]
---

# System Health

Monitor and verify WhiteMagic system health — backend status, Rust acceleration, state integrity, and release readiness.

## When to Use

- At session start to verify all subsystems operational
- After updates or migrations to check integrity
- Before releases to verify ship readiness
- When debugging performance or connectivity issues
- To audit Rust backend compilation status

## How to Invoke

```python
# Full health report
wm(thought="check system health")
wm(route="gana_root.health_report", args={})

# Quick status check
wm(route="gana_root.check", args={})

# Rust backend status
wm(route="gana_root.rust_status", args={})

# Ship readiness check
wm(route="gana_root.ship_check", args={})

# State summary
wm(route="gana_root.state_summary", args={})
```

## What It Checks

- SQLite database integrity and connection
- Rust acceleration backend (compiled, loaded, functional)
- HNSW vector index status
- Redis broker connectivity (if configured)
- Memory store consistency
- Galaxy taxonomy integrity
- Embedding engine availability
- Tool registry completeness
