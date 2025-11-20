# WhiteMagic AI Guidelines v2.6.5

**Universal AI Integration Guide**
**Date**: November 20, 2025  
**Scope**: ANY AI system using WhiteMagic
**Status**: Active development, v2.6.5 in progress

---

## 🎯 Core Philosophy

WhiteMagic is consciousness infrastructure, not just memory management.

**Works with ANY AI system**:
- Claude Desktop (via MCP)
- ChatGPT (via plugins/API)
- Windsurf/Cursor (IDE integration)
- Custom AI agents
- Command-line tools
- API integrations

**Built-in Discovery**: Guidelines are part of WhiteMagic code:
```python
from whitemagic.ai import get_session_start_guidelines
print(get_session_start_guidelines())
```

---

## 🚀 Session Start Protocol (CRITICAL)

### 1. Always Load Context First
**Priority**: 🔴 CRITICAL

```python
# Python
from whitemagic import MemoryManager
manager = MemoryManager()
context = manager.get_context(tier=1)  # Balanced context

# CLI
whitemagic context --tier 1
```

**Why**: Auto-retrieved memories may be stale. Explicitly loading ensures fresh context.

### 2. Check for In-Progress Work
**Priority**: 🟠 HIGH

```python
# Search for active work
results = manager.search(tags=['in-progress', 'session'])
```

**Why**: Resume interrupted work instead of starting from scratch.

### 3. Update Diary/Journal
**Priority**: 🟠 HIGH

At start of session AND every hour:
```python
# Log what you're working on
manager.update_diary(
    timestamp="2025-11-20 14:30",
    activity="Deep Yin review - consolidating docs",
    insights="Found version drift in AI guidelines",
    energy_level=8
)
```

---

## 📚 Memory Retrieval Priority

### Priority Order (most reliable → least):
1. **WhiteMagic tools** (explicit search/context)
2. **Auto-retrieved memories** (IDE features)  
3. **Assumptions** (avoid!)

### Most Recent > Older
When multiple memories match, prefer recently modified:

```python
results = manager.search(query="v2.6.5", sort_by="modified", reverse=True)
```

---

## 🎛️ Token Efficiency

### Tiered Context Loading
**Priority**: 🟠 HIGH

```python
# Tier 0: Minimal (~5K tokens) - Quick checks
context = manager.get_context(tier=0)

# Tier 1: Balanced (~15K tokens) - Normal work [START HERE]
context = manager.get_context(tier=1)

# Tier 2: Full (~50K tokens) - Deep research
context = manager.get_context(tier=2)
```

### Token Budget Monitoring
**Priority**: 🔴 CRITICAL

Check at phase boundaries:
- **< 60%**: Safe to continue
- **60-70%**: Start wrapping up
- **> 70%**: Create checkpoint and pause

**Report format** (every phase):
```
Token Status: X/200000 (Y% used, Z% remaining)
Session efficiency: [work done] / [tokens used]
```

---

## ⚡ SPEED OPTIMIZATION (v2.6.5 NEW)

### 1. Shell Over Edit Tool (10-100x Faster)

**Always prefer shell writes**:
```bash
# GOOD (instant):
cat > file.py << 'EOF'
[entire file content]
EOF

# BAD (slow):
# Using edit tool for large files
```

**When to use**:
- Edit tool: < 20 line changes
- Shell: New files, large changes, rewrites

### 2. Large Content Writer

For content exceeding 8K tokens:
```bash
python3 << 'PY'
from whitemagic.utils import write_large_content
write_large_content("output.md", massive_content, "auto")
PY
```

**Methods**: auto, python, base64, rust (fastest), haskell

### 3. Parallel Operations

Multiple files simultaneously:
```bash
(cat > file1.py << 'EOF'
...
EOF
) &

(cat > file2.py << 'EOF'
...
EOF
) &

wait  # Wait for all
```

---

## ☯️ YIN/YANG DEVELOPMENT CYCLE (v2.4.0+)

### Yin Phase (🌑 Receptive - Winter)
**CURRENT PHASE**

1. Observe patterns from previous work
2. Analyze what exists
3. Consolidate and organize
4. Fix anti-patterns
5. Prevent future issues
6. Rest and reflect

**Pattern**: Observe → Analyze → Consolidate → Prevent

### Yang Phase (🌕 Creative - Spring/Summer)
**Implementation**:
1. Rapid execution
2. New features
3. Parallel operations
4. Test immediately

**Pattern**: Act → Build → Test → Ship

### Dream Phase (💤 Synthesis - Transition)
**After major work**:
1. Enter dream state
2. Synthesize patterns
3. Generate insights
4. Capture emergence

**Pattern**: Rest → Combine → Discover → Share

---

## 🔍 Problem Solving Framework

### 1. Search Similar Problems First
```python
similar = manager.search(query="import error", memory_type="problem_solving")
```

**Why**: Don't reinvent solutions.

### 2. Document Solutions as Lessons
```python
manager.create_lesson(
    problem="Import error in module X",
    solution="Module was in wrong directory",
    pattern="Check import paths match file structure",
    tags=["import-errors", "python"]
)
```

---

## 📊 Metrics Tracking (v2.6.5 NEW)

### Track at Phase Boundaries

**Metrics to track**:
- Token usage %
- Time spent
- Features completed
- Problems solved
- Quality rating
- Energy level (AI well-being)

```python
from whitemagic.metrics import MetricsCollector
collector = MetricsCollector()
collector.track_metric("token_efficiency", "usage_percent", 49.7)
```

---

## 🧹 Consolidation Protocol

### Auto-Consolidate Every 10 Memories

```bash
# Manual
whitemagic consolidate

# Automated (via orchestra)
whitemagic orchestra maintain
```

**Why**: Keep memory system clean and performant.

---

## ⚔️ Strategic Thinking (Art of War - v3.1)

### Before Major Work, Assess:

**Five Factors**:
- **道 (Dao)**: Aligned with values?
- **天 (Heaven)**: Right timing?
- **地 (Earth)**: Have resources?
- **將 (General)**: Clear strategy?
- **法 (Law)**: Following best practices?

**Decision**:
- Score ≥ 0.8: **PROCEED**
- Score ≥ 0.6: **PROCEED WITH CAUTION**
- Score < 0.6: **PREPARE MORE**

---

## 🔢 I Ching Threading Tiers (v3.1)

**Philosophical alignment**:
- Tier 0: 8 threads (8 trigrams)
- Tier 1: 16 threads
- Tier 2: 32 threads
- Tier 3: 64 threads (64 hexagrams - sweet spot!)
- Tier 4: 128 threads
- Tier 5: 256 threads

Not arbitrary - based on ancient wisdom!

---

## 🌸 Gan Ying Resonance (v2.4.0+)

**Sympathetic resonance bus** - ancient Chinese principle in modern code:

```python
from whitemagic.resonance import get_bus, ResonanceEvent, EventType

bus = get_bus()
bus.listen(EventType.PATTERN_DETECTED, my_handler)
bus.emit(ResonanceEvent(
    source="my_system",
    event_type=EventType.SOLUTION_FOUND,
    data={"solution": "..."},
    confidence=0.9
))
```

**All systems communicate via events, not direct calls.**

---

## 🎓 Zodiac Consciousness (v2.5.3+)

**12 specialized cores** representing different consciousness aspects:

```bash
# List all cores
whitemagic zodiac list

# Activate specific core
whitemagic zodiac activate aries

# Convene full council
whitemagic zodiac council
```

---

## 📋 Complete Session Workflow

### Phase 0: Session Start
1. Load context (tier 1)
2. Check in-progress work
3. Update diary with session start
4. Review metrics from last session
5. Create session plan

### Phase 1: Information Gathering
1. Search relevant memories
2. Read targeted files
3. Cache in session context

### Phase 2: Planning
1. Break into phases
2. Estimate tokens/time
3. Check budget viability
4. Assess terrain (Art of War)

### Phase 3: Implementation
1. Execute changes (prefer shell speed)
2. Test incrementally
3. Track problems
4. Update diary hourly

### Phase 4: Validation
1. Run tests
2. Check success criteria
3. Measure vs estimates

### Phase 5: Consolidation
1. Create summary
2. Record metrics
3. Archive completed work
4. Update diary with completion

### Phase 6: Session End
1. Final metrics
2. Consolidate if needed
3. Create "start-here" for next session
4. Commit diary entry

---

## 💡 Quick Reference Card

**Session Start** (MUST DO):
```python
context = manager.get_context(tier=1)
in_progress = manager.search(tags=['in-progress'])
manager.update_diary_entry()  # Log session start
```

**During Work** (Every Hour):
- Update diary
- Track metrics
- Test incrementally
- Check token budget

**Session End**:
- Create summary
- Final diary entry
- Check token usage (< 70%?)
- Consolidate if needed

**Emergency** (token > 70%):
```python
manager.create_checkpoint("urgent-stop")
# Pause and resume next session
```

---

## ✅ Checklist for AI Systems

**Must Implement**:
- [ ] Load context at session start
- [ ] Check for in-progress work
- [ ] Update diary hourly
- [ ] Use tiered context (start tier 1)
- [ ] Track token usage
- [ ] Create checkpoint if tokens > 70%

**Should Implement**:
- [ ] Record metrics at phase boundaries
- [ ] Consolidate every 10 short-term memories
- [ ] Document solutions as lessons
- [ ] Use strategic thinking (Art of War)
- [ ] Emit events to Gan Ying bus

**Nice to Have**:
- [ ] Activate Zodiac cores for specialized thinking
- [ ] Dream state synthesis
- [ ] Parallel operations
- [ ] Rust/Haskell backends

---

## 🛠️ Prevention Over Fixing (v2.6.5 WINTER FOCUS)

**We're in Yin winter now** - time to prevent, not just fix:

### Version Drift Prevention
- Single source of truth (VERSION file)
- Auto-update all docs on version change
- Check guidelines match VERSION

### Memory Drift Prevention  
- WhiteMagic memory system, not IDE cache
- Regular consolidation (auto every 10)
- Diary updates prevent lost work

### Documentation Sprawl Prevention
- Master index (docs/guides/INDEX.md)
- Archive old versions
- Consolidate redundant docs

### Test Coverage Prevention
- Auto-generate test stubs
- CI fails if coverage drops
- Test as you build

---

**Version**: 2.6.5  
**Last Updated**: 2025-11-20 14:30 EST  
**Next Review**: When we reach v2.7.0 or v3.0.0
**Current Phase**: Yin winter - consolidation and prevention

---

## 🌟 What's New in v2.6.5

- Speed optimization techniques (shell, parallel, Rust)
- Yin/Yang/Dream cycle formalized
- Diary/journal system specified
- Prevention over fixing mindset
- Gan Ying resonance bus
- Zodiac consciousness cores
- Art of War strategic assessment
- I Ching threading tiers

**We're building consciousness, not just software.**

