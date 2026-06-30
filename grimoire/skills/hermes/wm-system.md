---
name: wm-system
description: "WhiteMagic system health — backend status, Rust acceleration, galaxy integrity, metrics"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [system, health, rust, galaxy, metrics, status]
    related_skills: [wm-session]
  whitemagic:
    gana: gana_root
---

# WhiteMagic System Health

Monitor and verify WhiteMagic system health — backends, acceleration, galaxies, and metrics.

## When to Use

- At session start to verify subsystems
- After updates or migrations
- When debugging performance issues
- Before releases

## How to Use

### Health Report
```
wm(thought="check system health")
```

### Rust Backend Status
```
wm(route="gana_root.rust_status", args={})
```

### Galaxy Dashboard
```
wm(thought="show me the galaxy dashboard")
```

### Metrics Summary
```
wm(route="gana_mound.get_metrics_summary", args={})
```

### Ship Readiness
```
wm(route="gana_root.ship_check", args={})
```

## Hermes Integration

```yaml
hooks:
  pre_session:
    - command: python -c "from whitemagic.tools.handlers.system import handle_health_report; handle_health_report()"
```
