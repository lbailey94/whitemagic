---
name: wm-codebase
description: "Codebase analysis via STRATA, archaeology, and codegenome tools"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [codebase, strata, archaeology, codegenome, analysis, static]
    related_skills: [wm-research]
  whitemagic:
    gana: gana_chariot
---

# WhiteMagic Codebase Analysis

Analyze codebases using STRATA static analysis, archaeology for history, and codegenome for pattern detection.

## When to Use

- Understanding a new codebase
- Finding bugs and code smells
- Tracking code evolution over time
- Identifying patterns and anti-patterns
- Pre-release audits

## How to Use

### STRATA Analysis
```
wm(thought="run STRATA analysis on this codebase")
```

### Archaeology (code history)
```
wm(route="gana_chariot.archaeology", args={"repo_path": "..."})
```

### Find Changed Files
```
wm(route="gana_chariot.archaeology_find_changed", args={})
```

### Codegenome Validation
```
wm(route="gana_chariot.codegenome", args={"action": "validate"})
```

### Daily Digest
```
wm(route="gana_chariot.archaeology_daily_digest", args={})
```
