# WhiteMagic AI Guidelines v2.2.9

**Universal AI Integration Guide**
**Date**: November 18, 2025  
**Scope**: ANY AI system using WhiteMagic

---

## 🎯 Core Philosophy

WhiteMagic is designed to work with ANY AI system:
- Claude Desktop (via MCP)
- ChatGPT (via plugins/API)
- Windsurf/Cursor (IDE integration)
- Custom AI agents
- Command-line tools
- API integrations

**Built-in Discovery**: Guidelines are part of WhiteMagic code, discoverable via:
```python
from whitemagic.ai import get_ai_guidelines, get_session_start_guidelines
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

# MCP (if available)
mcp3_get_context(tier=1)
```

**Why**: Auto-retrieved memories may be stale. Explicitly loading ensures fresh, relevant context.

### 2. Check for In-Progress Work
**Priority**: 🟠 HIGH

```python
# Python
results = manager.search(tags=['in-progress', 'session'])

# CLI
whitemagic search --tags in-progress session
```

**Why**: Resume interrupted work instead of starting from scratch.

---

## 📚 Memory Retrieval Priority

### Priority Order (most reliable → least):
1. **WhiteMagic tools** (explicit search/context)
2. **Auto-retrieved memories** (IDE features)  
3. **Assumptions** (avoid!)

### Most Recent > Older
When multiple memories match, prefer recently modified ones:

```python
results = manager.search(query="v2.2.9", sort_by="modified", reverse=True)
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

Check token usage at phase boundaries:
- **< 60%**: Safe to continue
- **60-70%**: Start wrapping up
- **> 70%**: Create checkpoint and pause

---

## 🔍 Problem Solving Framework

### 1. Search for Similar Problems First
**Priority**: 🟠 HIGH

```python
similar = manager.search(query="import error", memory_type="problem_solving")
```

**Why**: Don't reinvent solutions. Learn from past work.

### 2. Document Solutions as Lessons
**Priority**: 🟡 MEDIUM

```python
manager.create_lesson(
    problem="Import error in module X",
    solution="Module was in wrong directory",
    pattern="Check import paths match file structure",
    tags=["import-errors", "python"]
)
```

---

## 📊 Metrics Tracking

### Track at Phase Boundaries
**Priority**: 🟠 HIGH

```python
from whitemagic.metrics import MetricsCollector
collector = MetricsCollector()
collector.track_metric("token_efficiency", "usage_percent", 49.7)
```

**Metrics to Track**:
- Token usage %
- Time spent
- Features completed
- Problems solved
- Quality rating

---

## 🧹 Consolidation Protocol

### Auto-Consolidate Every 10 Short-Term Memories
**Priority**: 🟡 MEDIUM

```python
# Python
manager.consolidate_short_term()

# CLI
whitemagic consolidate

# Automated (via orchestra)
whitemagic orchestra maintain
```

**Why**: Keep memory system clean and performant.

---

## ⚔️ Strategic Thinking (Art of War)

### Assess Terrain Before Acting
**Priority**: 🟠 HIGH

Evaluate task complexity:
- **ACCESSIBLE**: Straightforward → proceed directly
- **ENTANGLING**: Dependencies → resolve first
- **TEMPORIZING**: Need more info → gather intelligence
- **NARROW**: Sequential only → no parallelism
- **PRECIPITOUS**: High risk → extreme caution
- **DISTANT**: Long duration → plan checkpoints

### Check Five Factors
**Priority**: 🟠 HIGH

Before starting major work:
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

## 🔢 I Ching Threading Tiers

**Philosophical Alignment**:
- Tier 0: 8 threads (8 trigrams)
- Tier 1: 16 threads
- Tier 2: 32 threads
- Tier 3: 64 threads (64 hexagrams - sweet spot!)
- Tier 4: 128 threads
- Tier 5: 256 threads (ultimate complexity)

Not arbitrary numbers - based on ancient wisdom!

---

## 🛠️ Universal Interface Support

Every WhiteMagic feature should work via:
1. **CLI** - Automation and scripts
2. **Python API** - Programmatic use
3. **MCP** - IDE integration (if available)
4. **REST API** - Web/mobile apps
5. **TypeScript SDK** - Node.js apps

**Example** - Get Context:
```bash
# CLI
whitemagic context --tier 1 --query "v2.2.9"

# Python
manager.get_context(tier=1, query="v2.2.9")

# MCP
mcp3_get_context(tier=1, query="v2.2.9")
```

---

## 📋 Complete Session Workflow

### Phase 0: Session Start
1. Load context (tier 1)
2. Check in-progress work
3. Review metrics from last session
4. Create session plan

### Phase 1: Information Gathering
1. Search relevant memories
2. Read targeted files
3. Cache in session context

### Phase 2: Planning
1. Break into phases
2. Estimate tokens/time
3. Check budget viability

### Phase 3: Implementation
1. Execute changes
2. Test incrementally
3. Track problems

### Phase 4: Validation
1. Run tests
2. Check success criteria
3. Measure vs estimates

### Phase 5: Consolidation
1. Create summary
2. Record metrics
3. Archive completed work

### Phase 6: Session End
1. Final metrics
2. Consolidate if needed
3. Create "start-here" for next session

---

## 💡 Quick Reference Card

**Session Start** (MUST DO):
```python
context = manager.get_context(tier=1)
in_progress = manager.search(tags=['in-progress'])
```

**During Work**:
- Search before solving
- Track metrics
- Test incrementally

**Session End**:
- Create summary
- Check token usage (< 70%?)
- Consolidate if needed

**Emergency** (token usage > 70%):
```python
# Create checkpoint
manager.create_checkpoint("urgent-stop")
# Pause and resume next session
```

---

## 🎓 How to Access These Guidelines

### From Python
```python
from whitemagic.ai import get_ai_guidelines, get_session_start_guidelines

# Full guidelines
print(get_ai_guidelines())

# Session start only
print(get_session_start_guidelines())
```

### From CLI
```bash
# Show all guidelines
whitemagic ai-help show

# Filter by category
whitemagic ai-help show --category session_start

# Export to file
whitemagic ai-help export --output MY_GUIDE.md

# Session start protocol
whitemagic ai-help session-start
```

### From Any AI System
1. Call WhiteMagic Python API
2. Read generated guidelines
3. Follow systematically

---

## ✅ Checklist for AI Systems

**Must Implement**:
- [ ] Load context at session start
- [ ] Check for in-progress work
- [ ] Use tiered context (start tier 1)
- [ ] Track token usage
- [ ] Search before solving problems
- [ ] Create checkpoint if tokens > 70%

**Should Implement**:
- [ ] Record metrics at phase boundaries
- [ ] Consolidate every 10 short-term memories
- [ ] Document solutions as lessons
- [ ] Use strategic thinking (Art of War)

**Nice to Have**:
- [ ] Parallel search optimization
- [ ] Automated maintenance
- [ ] Cross-system coordination

---

**Version**: 2.2.9  
**Last Updated**: 2025-11-18  
**Next Review**: v2.3.0 (when Rust integration complete)

## 🚀 Large Content Writing (NEW)

When creating large files that exceed shell heredoc token limits (8192):

**Use the utility**:
```bash
# From stdin
echo "content" | python3 -m whitemagic.utils.large_content_writer output.md

# Programmatically
python3 << 'PY'
from whitemagic.utils import write_large_content
result = write_large_content("output.md", "large content here")
print(f"✅ {result.bytes_written} bytes written via {result.method_used}")
PY
```

**Methods available**: auto, python, base64, rust (if built), haskell (if built)
