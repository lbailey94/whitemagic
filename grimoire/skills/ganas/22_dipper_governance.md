---
name: wm-strategy
description: "Cognitive modes, homeostasis, maturity assessment, starter packs, strategy"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_dipper
    tools: [astro_shift, astro_status, cognitive_hints, cognitive_mode, homeostasis_check, homeostasis_status, maturity_assess, starter_pack_get, starter_pack_list, starter_pack_suggest]
    tags: [strategy, cognitive, homeostasis, maturity, starter_packs, astro, modes]
---

# Strategy & Cognitive Modes

Manage cognitive modes, check homeostasis, assess maturity, and access starter packs for onboarding.

## When to Use

- Checking or switching cognitive modes
- Homeostasis monitoring (system balance)
- Maturity assessment for feature readiness
- Getting starter packs for new users or agents
- Astrological status (zodiac round position)
- Cognitive hints for current context

## How to Invoke

```python
# Cognitive mode
wm(route="gana_dipper.cognitive_mode", args={"mode": "analytical"})

# Cognitive hints
wm(route="gana_dipper.cognitive_hints", args={})

# Homeostasis check
wm(route="gana_dipper.homeostasis_check", args={})

# Maturity assessment
wm(route="gana_dipper.maturity_assess", args={"feature": "..."})

# Starter pack suggestions
wm(route="gana_dipper.starter_pack_suggest", args={"context": "..."})

# Astro status
wm(route="gana_dipper.astro_status", args={})
```
