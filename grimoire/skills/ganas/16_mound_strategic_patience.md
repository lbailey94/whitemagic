---
name: wm-metrics
description: "Metrics tracking, caching, yin-yang balance, hologram view, and green scoring"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_mound
    tools: [cache_flush, cache_status, get_metrics_summary, get_yin_yang_balance, hologram_view, green_score]
    tags: [metrics, caching, yin_yang, hologram, green, score, performance]
---

# Metrics & Caching

Track system metrics, manage caches, measure yin-yang balance, view holographic projections, and calculate green scores.

## When to Use

- Checking system performance metrics
- Managing cache state (flush, status)
- Measuring yin-yang balance of operations
- Viewing holographic memory projections
- Calculating green score (efficiency/sustainability)
- Performance tuning and analysis

## How to Invoke

```python
# Metrics summary
wm(route="gana_mound.get_metrics_summary", args={})

# Cache status
wm(route="gana_mound.cache_status", args={})

# Flush cache
wm(route="gana_mound.cache_flush", args={})

# Yin-yang balance
wm(route="gana_mound.get_yin_yang_balance", args={})

# Hologram view
wm(route="gana_mound.hologram_view", args={"memory_id": "..."})

# Green score
wm(route="gana_mound.green_score", args={})
```
