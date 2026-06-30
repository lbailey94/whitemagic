---
name: wm-patterns
description: "Pattern mining, association discovery, causal analysis, learning, and emergence detection"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_extended_net
    tools: [association_mine, association_mine_semantic, causal_mine, causal_stats, pattern_search, cluster_stats, coherence_boost, resonance_trace, learning_apply]
    tags: [patterns, associations, causal, learning, emergence, resonance, clusters]
---

# Patterns & Learning

Mine associations, discover causal relationships, detect emergence, and apply learned patterns across the memory graph.

## When to Use

- Finding hidden connections between memories
- Discovering causal relationships in event sequences
- Detecting emergent patterns across sessions
- Boosting coherence between related memories
- Applying learned patterns to new situations
- Tracing resonance chains through the system

## How to Invoke

```python
# Mine associations
wm(route="gana_extended_net.association_mine", args={"depth": 3})

# Semantic association mining
wm(route="gana_extended_net.association_mine_semantic", args={"query": "..."})

# Causal analysis
wm(route="gana_extended_net.causal_mine", args={"event": "..."})

# Pattern search
wm(route="gana_extended_net.pattern_search", args={"pattern": "..."})

# Coherence boost
wm(route="gana_extended_net.coherence_boost", args={"memory_id": "..."})

# Apply learning
wm(route="gana_extended_net.learning_apply", args={"pattern_id": "..."})
```
