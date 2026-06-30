---
name: wm-judgment
description: "Multi-branch reasoning, ensemble queries, kaizen analysis, wisdom council, optimization"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_three_stars
    tools: [art_of_war_assess, art_of_war_campaign, art_of_war_chapter, art_of_war_plan, bicameral_reason, ensemble_query, ensemble_history, ensemble_status, optimization, kaizen_analyze, kaizen_apply, sabha_convene, sabha_status]
    tags: [judgment, reasoning, ensemble, kaizen, wisdom, council, optimization, bicameral, art_of_war]
---

# Judgment & Synthesis

Multi-branch parallel reasoning, ensemble queries across multiple perspectives, kaizen continuous improvement, and wisdom council deliberation.

## When to Use

- Complex decisions requiring multiple perspectives
- Parallel reasoning across different approaches
- Ensemble queries for robustness
- Continuous improvement (kaizen) analysis
- Convening the wisdom council (sabha) for deliberation
- Optimization problems
- Strategic assessment (Art of War framework)

## How to Invoke

```python
# Bicameral reasoning (two-hemisphere)
wm(thought="reason through this problem from multiple angles")
wm(route="gana_three_stars.bicameral_reason", args={"question": "...", "perspectives": ["analytical", "creative"]})

# Ensemble query
wm(route="gana_three_stars.ensemble_query", args={"question": "...", "models": [...]})

# Kaizen analysis
wm(route="gana_three_stars.kaizen_analyze", args={"area": "..."})

# Convene wisdom council
wm(route="gana_three_stars.sabha_convene", args={"topic": "..."})

# Optimization
wm(route="gana_three_stars.optimization", args={"target": "...", "constraints": [...]})

# Art of War assessment
wm(route="gana_three_stars.art_of_war_assess", args={"situation": "..."})
```
