---
name: wm-edge
description: "Edge inference, BitNet, edge rules, and batch processing"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_turtle_beak
    tools: [bitnet_infer, bitnet_status, edge_add_rule, edge_batch_infer, edge_stats]
    tags: [edge, inference, bitnet, rules, batch, precision]
---

# Edge Inference & Precision

Run lightweight inference at the edge using BitNet, manage edge rules for local processing, and batch inference operations.

## When to Use

- Running lightweight inference without full model loading
- Checking BitNet model status
- Adding edge processing rules
- Batch inference for multiple inputs
- Edge statistics and monitoring

## How to Invoke

```python
# BitNet inference
wm(route="gana_turtle_beak.bitnet_infer", args={"input": "...", "model": "..."})

# BitNet status
wm(route="gana_turtle_beak.bitnet_status", args={})

# Add an edge rule
wm(route="gana_turtle_beak.edge_add_rule", args={"pattern": "...", "action": "..."})

# Batch inference
wm(route="gana_turtle_beak.edge_batch_infer", args={"inputs": [...], "model": "..."})

# Edge stats
wm(route="gana_turtle_beak.edge_stats", args={})
```
