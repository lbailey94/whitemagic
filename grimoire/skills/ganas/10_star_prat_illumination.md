---
name: wm-governance
description: "Governance — dharma profiles, forge validation, PRAT invocation, goal setting"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_star
    tools: [governor_validate, governor_set_goal, governor_drift, governor_budget, dharma_reload, forge_status, forge_reload, forge_validate, dharma_rules]
    tags: [governance, dharma, governor, forge, prat, goals, budget, drift]
---

# Governance & Dharma

Validate actions against Dharma ethical constraints, set governance goals, manage forge status, and enforce project rules.

## When to Use

- Before taking potentially destructive actions
- Setting governance goals for a session
- Checking if actions drift from established goals
- Validating forge (tool registry) integrity
- Reloading Dharma rules after policy changes
- Checking budget constraints

## How to Invoke

```python
# Validate an action against Dharma
wm(route="gana_star.governor_validate", args={"action": "...", "context": "..."})

# Set a governance goal
wm(route="gana_star.governor_set_goal", args={"goal": "..."})

# Check for goal drift
wm(route="gana_star.governor_drift", args={})

# Forge status
wm(route="gana_star.forge_status", args={})

# Reload Dharma rules
wm(route="gana_star.dharma_reload", args={})

# Get Dharma rules
wm(route="gana_star.dharma_rules", args={})
```

## Dharma Levels

- **UNIVERSAL** — Core ethical principles, never overridden
- **COMPASSION** — Harm prevention, wellbeing
- **INTEGRITY** — Truthfulness, authenticity
- **HARMONY** — Balance, non-conflict
- **WISDOM** — Prudential judgment, context-aware
