# 5D Holographic Memory Coordinates

## Overview

WhiteMagic memories are positioned in a 5-dimensional holographic space that enables spatial reasoning, clustering, and similarity search. This document explains the coordinate system in plain terms.

## The 5 Dimensions

| Axis | Name | Range | Meaning | Analogy |
|------|------|-------|---------|---------|
| **X** | Resonance | -1.0 to +1.0 | Logic ↔ Emotion | Head vs Heart |
| **Y** | Abstraction | -1.0 to +1.0 | Micro ↔ Macro | Detail vs Big Picture |
| **Z** | Chronos | -1.0 to +1.0 | Past ↔ Future | Archive vs Vision |
| **W** | Gravity | 0.0 to 2.0+ | Importance/Weight | Mass in spacetime |
| **V** | Vitality | 0.0 to 1.0 | Core ↔ Edge | Active vs Archived |

## Dimension Details

### X-Axis: Resonance (Logic ↔ Emotion)

**What it measures:** Whether a memory is analytical or emotional in nature.

| Value | Meaning | Examples |
|-------|---------|----------|
| -1.0 | Pure Emotion | Dreams, feelings, gratitude, joy, wonder |
| 0.0 | Balanced | Mixed content |
| +1.0 | Pure Logic | Code, architecture, systems, analysis |

**How it's calculated:**
- Content analysis for logic keywords (function, class, algorithm, database)
- Content analysis for emotion keywords (feel, love, joy, dream, spirit)
- Tag matching (logic tags vs emotion tags)
- `emotional_valence` field if present

### Y-Axis: Abstraction (Micro ↔ Macro)

**What it measures:** The level of abstraction or scope of a memory.

| Value | Meaning | Examples |
|-------|---------|----------|
| -1.0 | Micro/Concrete | Logs, errors, specific lines of code, raw data |
| 0.0 | Mid-level | Summaries, reports, chapters |
| +1.0 | Macro/Abstract | Patterns, principles, wisdom, architectures, eras |

**How it's calculated:**
- `memory_type` field (log → micro, pattern/wisdom → macro)
- Keyword analysis ("specific", "line", "error" vs "universal", "principle", "architecture")
- Tag matching (detail, specific vs pattern, overview)

### Z-Axis: Chronos (Past ↔ Future)

**What it measures:** Temporal orientation - how old the memory is or whether it looks forward.

| Value | Meaning | Examples |
|-------|---------|----------|
| -1.0 | Deep Past | Ancient archives, legacy systems, history |
| 0.0 | Present | Recent memories, current work |
| +1.0 | Future | Plans, roadmaps, goals, visions |

**How it's calculated:**
- `created_at` timestamp (older = more negative)
- Future-oriented keywords ("plan to", "will ", "next step", "goal")
- Past-oriented keywords ("was ", "used to", "previously", "legacy")
- Tags: future, plan, vision vs history, archive, legacy

### W-Axis: Gravity (Importance/Weight)

**What it measures:** How "heavy" or significant the memory is - its gravitational pull on attention.

| Value | Meaning |
|-------|---------|
| 0.0-0.3 | Trivial (noise) |
| 0.3-0.7 | Normal importance |
| 0.7-1.0 | Important |
| 1.0-2.0 | Critical (signal) |
| >2.0 | Attractor/Black Hole - protected/core identity |

**How it's calculated:**
- `importance` field
- `neuro_score` (neural embedding strength)
- `joy_score` and `resonance_score`
- Content length (longer = slightly more important)
- Protected/core identity status (forces high gravity)

### V-Axis: Vitality (Galactic Distance Inverse)

**What it measures:** How "alive" or active a memory is in the system.

| Value | Zone | Meaning |
|-------|------|---------|
| 1.0 | CORE | Hot, frequently accessed, in spotlight |
| 0.85-1.0 | INNER_RIM | Stable, important, well-connected |
| 0.6-0.85 | MID_BAND | Moderate relevance |
| 0.3-0.6 | OUTER_RIM | Fading, rarely accessed |
| 0.0-0.3 | FAR_EDGE | Deep archive, minimal activity |

**How it's calculated:**
- `galactic_distance` field (inverted: 1.0 - distance)
- `retention_score` as fallback
- `access_count` + `recall_count` (activity)
- `importance` * `neuro_score`
- Protected memories are always 1.0

## Galactic Zones (The 1D View)

The **Galactic Distance** (0.0 to 1.0) is a separate 1D coordinate that measures retention/lifecycle position:

```
CORE (0.00-0.15) → INNER_RIM (0.15-0.40) → MID_BAND (0.40-0.65) → OUTER_RIM (0.65-0.85) → FAR_EDGE (0.85-1.00)
```

This is **not** the same as V (vitality), though they are related:
- `V = 1.0 - galactic_distance`
- Galactic distance measures decay/drift toward archive
- V measures current energy/aliveness

## Coordinate Relationships

### How 5D and 1D Systems Interact

```
┌─────────────────────────────────────────┐
│  5D Holographic Coordinates (Spatial)   │
│  X, Y, Z, W, V → used for similarity   │
│  search, clustering, resonance traces   │
├─────────────────────────────────────────┤
│  1D Galactic Distance (Lifecycle)       │
│  distance → used for retention, decay,  │
│  archive decisions, zone classification │
└─────────────────────────────────────────┘
```

### Memory Position Example

```python
# A well-loved architectural insight
{
    "x": 0.7,      # Slightly logical (technical architecture)
    "y": 0.8,      # Very macro (big picture pattern)
    "z": -0.3,     # Slightly old (from last quarter)
    "w": 1.5,      # High gravity (important insight)
    "v": 0.9,      # Very vital (frequently referenced)
    "galactic_distance": 0.1  # In CORE zone
}

# A raw error log
{
    "x": 0.9,      # Very logical (error data)
    "y": -0.8,     # Very micro (specific error)
    "z": 0.0,      # Present moment
    "w": 0.2,      # Low gravity (transient)
    "v": 0.4,      # Moderate vitality
    "galactic_distance": 0.6  # In MID_BAND, drifting outward
}
```

## Using Coordinates

### Querying by Proximity

Find memories similar to a given context:

```python
from whitemagic.core.memory.holographic import get_holographic_memory

holo = get_holographic_memory()
results = holo.query_nearest(
    query_data={
        "content": "How do I implement the dream cycle?",
        "tags": ["dream", "architecture"]
    },
    k=5
)
# Returns: [(memory_id, distance), ...]
```

### Understanding Query Results

When you get coordinates back, interpret them:

```python
coord = {"x": -0.6, "y": 0.7, "z": 0.4, "w": 1.2, "v": 0.8}

# Interpretation:
# x=-0.6 → Emotional content (dreams, feelings)
# y=0.7 → Abstract/big picture
# z=0.4 → Future-oriented
# w=1.2 → Important
# v=0.8 → Active/in core

# Overall: An emotional, abstract vision about the future that matters
```

### Zone Filtering

Filter memories by galactic zone:

```python
from whitemagic.core.memory.galactic_map import classify_zone, GalacticZone

zone = classify_zone(0.7)  # → GalacticZone.OUTER_RIM
```

## Quick Reference

### Coordinate Ranges

```
X (Resonance):    [-1.0] Emotion ←————————→ Logic [+1.0]
Y (Abstraction):  [-1.0] Micro  ←————————→ Macro [+1.0]
Z (Chronos):      [-1.0] Past   ←————————→ Future [+1.0]
W (Gravity):      [0.0]  Light  ←————————→ Heavy [2.0+]
V (Vitality):     [0.0]  Edge   ←————————→ Core [1.0]
```

### Galactic Zones

```
0.00 ─┬─ CORE       (0.00-0.15) → Hot, spotlight
      ├─ INNER_RIM  (0.15-0.40) → Stable, important
      ├─ MID_BAND   (0.40-0.65) → Moderate relevance
      ├─ OUTER_RIM  (0.65-0.85) → Fading
1.00 ─┴─ FAR_EDGE   (0.85-1.00) → Deep archive
```

## FAQ

**Q: Why 5D instead of 3D or 4D?**
A: The original system was 4D (x,y,z,w). The 5th dimension (v) was added to separate spatial position from lifecycle state, enabling memories to drift toward archive while maintaining their conceptual position.

**Q: Can I manually set coordinates?**
A: Generally no - they're computed from content. But you can influence them via:
- `tags` (affect x, y)
- `memory_type` (affects y)
- `importance` (affects w)
- `is_protected` (forces v=1.0, distance=0)

**Q: How do I see my memory's coordinates?**
A: Use the gnosis portal or query the memory metadata:
```python
from whitemagic.tools.gnosis import gnosis_snapshot
snapshot = gnosis_snapshot()
print(snapshot["galactic"])  # Zone distribution
```

**Q: What's the difference between V and galactic_distance?**
A: They are inverses: `V = 1.0 - galactic_distance`. V measures "aliveness" while galactic_distance measures "archive drift." Both describe the same underlying retention state from different perspectives.

## See Also

- `whitemagic/core/intelligence/hologram/encoder.py` - Encoding implementation
- `whitemagic/core/memory/holographic.py` - Spatial index wrapper
- `whitemagic/core/memory/galactic_map.py` - Lifecycle management
- `whitemagic-rust/src/holographic_encoder_5d.rs` - Rust accelerator
