# Art of War Integration Guide

**Version**: 2.2.4  
**Purpose**: Apply Sun Tzu's strategic wisdom to AI workflows

---

## 🎯 Overview

WhiteMagic v2.2.4 integrates **孫子兵法** (The Art of War) principles for strategic planning and tactical execution.

**Sun Tzu**: "Victorious warriors win first and then go to war, while defeated warriors go to war first and then seek to win."

---

## 📋 Core Concepts

### 1. **Task Terrain Analysis** (地形)

Before executing any task, assess its "terrain":

```python
from whitemagic.strategy import TaskTerrain, TerrainAnalysis

terrains = {
    "ACCESSIBLE": "Straightforward, can advance freely",
    "ENTANGLING": "Has dependencies, hard to backtrack",
    "TEMPORIZING": "Need more information first",
    "NARROW": "Must be sequential, no parallelism",
    "PRECIPITOUS": "High risk, careful execution needed",
    "DISTANT": "Long duration, multi-session work"
}
```

**Example**:
- Simple bug fix → ACCESSIBLE
- Refactoring with tests → ENTANGLING  
- Feature needing design → TEMPORIZING
- Database migration → PRECIPITOUS
- Multi-week project → DISTANT

### 2. **Five Factors Assessment** (五事)

Sun Tzu's foundation for any endeavor:

```python
from whitemagic.strategy import FiveFactorsAssessment

factors = FiveFactorsAssessment(
    dao_aligned=True,      # 道 - Aligned with values?
    heaven_favorable=True,  # 天 - Right timing?
    earth_prepared=True,    # 地 - Have resources?
    general_ready=True,     # 將 - Clear strategy?
    law_followed=True       # 法 - Following best practices?
)

if factors.score >= 0.8:
    proceed()
else:
    prepare_more()
```

### 3. **Threading Tiers** (I Ching Aligned)

Parallel execution aligned with ancient patterns:

```python
from whitemagic.threading_tiers import ThreadingTier, get_tier_threads

# Tier 0: 8 threads (8 trigrams ☰☱☲☳☴☵☶☷)
# Tier 1: 16 threads (2 × 8)
# Tier 2: 32 threads (4 × 8)  
# Tier 3: 64 threads (64 hexagrams) ← Sweet spot!
# Tier 4: 128 threads (2 × 64)
# Tier 5: 256 threads (ultimate complexity)

threads = get_tier_threads(tier=3)  # 64 threads
```

---

## 🎨 Practical Usage

### Pre-Task Assessment

```python
# 1. Analyze terrain
terrain = analyze_terrain(
    task="Implement feature X",
    has_dependencies=True,
    is_parallelizable=True,
    estimated_tokens=15000
)

# 2. Check five factors
factors = assess_five_factors(
    task="Implement feature X",
    values_aligned=True,
    timing_good=True,
    resources_available=True,
    strategy_clear=True,
    practices_followed=True
)

# 3. Decide
if factors.recommendation == "PROCEED":
    if terrain.terrain_type == TaskTerrain.ACCESSIBLE:
        execute_parallel(tier=3)  # 64 threads
    elif terrain.terrain_type == TaskTerrain.NARROW:
        execute_sequential()
    else:
        execute_with_caution()
```

---

## ⚔️ Strategic Principles

### From Sun Tzu

**Chapter 1 (Laying Plans)**:
- Assess before acting
- Five factors determine victory
- Plan thoroughly, execute swiftly

**Chapter 10 (Terrain)**:
- Know the ground you fight on
- Adapt to terrain type
- Don't fight on unfavorable terrain

**Chapter 3 (Attack by Stratagem)**:
- Best victory: Win without fighting
- Know when to engage, when to wait
- Preserve resources

---

## 🎯 Decision Framework

```
Task arrives
    ↓
Analyze terrain
    ↓
├─ ACCESSIBLE? → Proceed with confidence
├─ ENTANGLING? → Resolve dependencies first
├─ TEMPORIZING? → Gather information
├─ NARROW? → Sequential execution only
├─ PRECIPITOUS? → Extreme caution, test incrementally
└─ DISTANT? → Plan multi-session, create checkpoints
    ↓
Assess five factors
    ↓
├─ Score ≥ 0.8? → PROCEED
├─ Score ≥ 0.6? → PROCEED_WITH_CAUTION
└─ Score < 0.6? → PREPARE_MORE
    ↓
Select threading tier
    ↓
├─ Simple? → Tier 0-1 (8-16 threads)
├─ Complex? → Tier 3 (64 threads, hexagram level)
└─ Extreme? → Tier 4-5 (128-256 threads)
    ↓
Execute!
```

---

## 💡 Examples

### Example 1: Bug Fix (ACCESSIBLE)

```
Terrain: ACCESSIBLE
- No dependencies
- Clear problem
- Parallelizable testing
→ Tier 1 (16 threads), proceed directly
```

### Example 2: Feature with Research (TEMPORIZING)

```
Terrain: TEMPORIZING
- Need design decisions
- Unclear requirements
- High uncertainty
→ Gather information first, don't code yet
```

### Example 3: Database Migration (PRECIPITOUS)

```
Terrain: PRECIPITOUS
- High risk of data loss
- Cannot easily rollback
- Critical path
→ Sequential execution, test thoroughly, backup first
```

---

## 🌟 Benefits

1. **Strategic thinking** before tactical execution
2. **Risk assessment** built into workflow
3. **Resource optimization** (don't waste tokens on bad terrain)
4. **Ancient wisdom** proven over 2,500 years
5. **Clear decision framework** (no guessing)

---

**Status**: v2.2.4  
**Principle**: "Know your enemy and know yourself" → Know your task and know your resources

**Sun Tzu would approve!** ⚔️
