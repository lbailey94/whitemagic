---
name: wm-acceleration
description: "SIMD acceleration, cascade execution, hexagram dispatch, and polyglot queries"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_tail
    tools: [execute_cascade, hexagram_boltzmann_select, hexagram_dispatch, hexagram_simd_execute, simd_cosine, simd_batch_distance, simd_batch_dot, simd_batch_top_k]
    tags: [simd, acceleration, cascade, hexagram, polyglot, performance]
---

# Performance & Acceleration

Rust SIMD acceleration for vector operations, cascade execution for multi-step tool chains, and hexagram-based dispatch for parallel work.

## When to Use

- Batch vector operations (cosine similarity, Euclidean distance, dot product, top-k)
- Multi-step tool cascades that can be parallelized
- Performance-critical embedding comparisons
- Polyglot query dispatch across language runtimes

## How to Invoke

```python
# SIMD cosine similarity
wm(route="gana_tail.simd_cosine", args={"vec_a": [...], "vec_b": [...]})

# Batch distance computation
wm(route="gana_tail.simd_batch_distance", args={"query": [...], "candidates": [[...], ...]})

# Batch top-k selection
wm(route="gana_tail.simd_batch_top_k", args={"query": [...], "candidates": [...], "k": 10})

# Cascade execution
wm(route="gana_tail.execute_cascade", args={"steps": [...]})

# Hexagram dispatch
wm(route="gana_tail.hexagram_dispatch", args={"pattern": "..."})
```

## Fallback Behavior

All SIMD operations fall back to Python implementations if the Rust backend is not compiled. Performance is ~10-50x slower in Python fallback mode but functionally identical.
