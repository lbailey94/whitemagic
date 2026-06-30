---
name: wm-resilience
description: "Grimoire spells, oracle casting, rate limiting, and fool guard resilience"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_willow
    tools: [cast_oracle, grimoire_spells, grimoire_suggest, grimoire_cast, grimoire_walkthrough, fool_guard_dare_to_die, fool_guard_ralph, fool_guard_status, rate_limiter_status]
    tags: [grimoire, spells, oracle, resilience, rate_limit, fool_guard]
---

# Resilience & Grimoire

Cast oracle readings, invoke grimoire spells, manage rate limiting, and monitor fool guard resilience systems.

## When to Use

- Casting I Ching oracle readings for decision support
- Looking up grimoire spells for specific situations
- When the system is under rate limiting pressure
- Checking fool guard status (circuit breaker)
- Getting spell suggestions based on context

## How to Invoke

```python
# Cast oracle
wm(thought="cast an oracle reading about this decision")
wm(route="gana_willow.cast_oracle", args={"question": "..."})

# Grimoire spell suggestions
wm(route="gana_willow.grimoire_suggest", args={"context": "..."})

# Cast a specific spell
wm(route="gana_willow.grimoire_cast", args={"spell": "..."})

# Spell walkthrough
wm(route="gana_willow.grimoire_walkthrough", args={"spell": "..."})

# Rate limiter status
wm(route="gana_willow.rate_limiter_status", args={})

# Fool guard status
wm(route="gana_willow.fool_guard_status", args={})
```

## Oracle System

The oracle uses the complete 64-hexagram I Ching system with Gan Ying integration. Readings auto-persist to the dreams galaxy for future reference.
