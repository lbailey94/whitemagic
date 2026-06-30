---
name: wm-dream
description: "WhiteMagic dream cycle — background insight generation and memory consolidation"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [dream, cycle, consolidation, serendipity, insight]
    related_skills: [wm-memory]
  whitemagic:
    gana: gana_abundance
---

# WhiteMagic Dream Cycle

Run the 12-phase dream cycle for background processing, memory consolidation, and serendipity discovery.

## When to Use

- After a long work session — let the system consolidate
- Before starting a new session — surface overnight insights
- When looking for unexpected connections
- For creative problem-solving via serendipity

## How to Use

### Start a Dream Cycle
```
wm(thought="start a dream cycle")
```

### Check Dream Status
```
wm(route="gana_abundance.dream_status", args={})
```

### Surface Serendipity
```
wm(thought="surface serendipitous connections")
```

### Get Dream Output
```
wm(route="gana_abundance.dream_now", args={})
```

## 12 Phases

Triage → Consolidation → Serendipity → Governance → Narrative → Kaizen → Oracle → Decay → Constellation → Prediction → Enrichment → Harmonize

## Hermes Integration

Schedule dream cycles between Hermes sessions:
```yaml
hooks:
  post_session:
    - command: python -c "from whitemagic.tools.handlers.dreaming import handle_dream_start; handle_dream_start()"
```
