---
name: wm-introspection
description: "Self-awareness, consciousness, and introspection — system state, coherence, capabilities"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_ghost
    tools: [gnosis, telemetry, capabilities, capability_matrix, capability_status, capability_suggest, self_model_forecast, narrative_compress, surprise_stats, watchers]
    tags: [introspection, self-model, consciousness, coherence, capabilities, telemetry]
---

# Introspection & Self-Model

Inspect the system's own state — capabilities, coherence metrics, self-model forecasts, narrative compression, and surprise statistics.

## When to Use

- Getting a unified system snapshot (gnosis)
- Checking what capabilities are available
- Forecasting system behavior
- Detecting anomalies via surprise stats
- Compressing long narratives into summaries
- Monitoring watchers and alerts

## How to Invoke

```python
# Full gnosis (unified snapshot)
wm(thought="introspect my current state")
wm(route="gana_ghost.gnosis", args={"compact": true})

# Capabilities matrix
wm(route="gana_ghost.capability_matrix", args={})

# Self-model forecast
wm(route="gana_ghost.self_model_forecast", args={"horizon": 10})

# Surprise statistics
wm(route="gana_ghost.surprise_stats", args={})

# Narrative compression
wm(route="gana_ghost.narrative_compress", args={"text": "..."})

# Telemetry
wm(route="gana_ghost.telemetry", args={})
```

## Gnosis Output

The gnosis call returns a unified consciousness state including:
- Coherence level (8 dimensions)
- Active gardens and their states
- Yin-yang balance
- Zodiac round position
- Session duration and depth
- Time of day awareness
