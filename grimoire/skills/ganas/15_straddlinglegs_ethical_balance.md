---
name: wm-ethics
description: "Ethics evaluation, boundaries, consent, harmony vector, wu xing balance, verification"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_straddling_legs
    tools: [check_boundaries, evaluate_ethics, get_dharma_guidance, get_ethical_score, harmony_vector, wu_xing_balance, verify_action]
    tags: [ethics, boundaries, consent, harmony, wu_xing, balance, verification, dharma]
---

# Ethics & Balance

Evaluate actions against ethical frameworks, check boundaries, measure harmony and Wu Xing balance, and verify action safety.

## When to Use

- Before taking potentially destructive actions
- When evaluating whether an action is appropriate
- When the user asks about ethical implications
- Checking if an action violates project boundaries
- Measuring system harmony and balance
- Verifying action safety before execution

## How to Invoke

```python
# Evaluate ethics
wm(route="gana_straddling_legs.evaluate_ethics", args={"action": "...", "context": "..."})

# Check boundaries
wm(route="gana_straddling_legs.check_boundaries", args={"action": "..."})

# Get Dharma guidance
wm(route="gana_straddling_legs.get_dharma_guidance", args={"situation": "..."})

# Harmony vector
wm(route="gana_straddling_legs.harmony_vector", args={})

# Wu Xing balance
wm(route="gana_straddling_legs.wu_xing_balance", args={})

# Verify an action
wm(route="gana_straddling_legs.verify_action", args={"action": "..."})
```

## Wu Xing (Five Elements)

- **Wood** — Growth, expansion, creativity
- **Fire** — Passion, intensity, transformation
- **Earth** — Stability, grounding, nourishment
- **Metal** — Precision, structure, boundaries
- **Water** — Wisdom, flow, adaptability
