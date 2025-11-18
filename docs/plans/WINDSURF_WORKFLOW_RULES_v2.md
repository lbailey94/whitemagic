# Windsurf Workflow Rules v2.0 - Optimized for Parallel Threading

**Date**: November 16, 2025  
**Status**: Active - Reflects breakthrough efficiency capabilities  
**Version**: 2.0 (replaces v1.0 sequential workflows)

---

## 🎯 Core Principles (Updated)

### 1. **Parallel-First Execution**
```
OLD: Sequential exploration → Synthesis → Action
NEW: Parallel exploration → Real-time synthesis → Parallel action
```

**When to use**:
- ✅ Information gathering (grep, read, search)
- ✅ Independent file operations
- ✅ Documentation audits
- ✅ Multi-file analysis

**When NOT to use**:
- ❌ Dependent operations (edit requires read first)
- ❌ Sequential logic flows (test → fix → test)
- ❌ Single critical path tasks

### 2. **Tiered Memory Consolidation**
```
Phase end    → Create phase summary memory
Version end  → Consolidate version memories
Session end  → Create session snapshot + consolidate short-term
```

**Consolidation triggers**:
- Every phase completion
- Every version release (v2.2.x → v2.3.0)
- Every 3-4 hour session
- After major breakthroughs

**Benefits**: Compounding context clarity over time

### 3. **Constant Memory Creation**
```
After significant thought → Create memory
After breakthrough → Create memory
After phase/version → Create consolidation memory
```

**Memory is cheap** (~200 tokens to create, 10-100x savings on retrieval with summaries)

**Pattern**:
1. Complete meaningful work unit
2. Create memory immediately
3. Tag appropriately
4. Continue work
5. Consolidate every N memories (N=5-10)

---

## 📋 Phase-Based Workflow

### **Phase Start**
1. Check context tier needed (0/1/2)
2. Load memories at appropriate tier
3. Set clear objectives
4. Identify parallelizable tasks
5. Create plan with update_plan

### **Phase Execution**
1. **Parallel exploration** - Fire all independent reads/searches
2. **Real-time synthesis** - Process results as they arrive
3. **Parallel implementation** - Execute independent changes
4. **Incremental validation** - Test each unit
5. **Memory capture** - Create memories for insights

### **Phase End** (NEW!)
1. **Create phase summary memory** (long-term)
2. **Update plan** - Mark phase complete
3. **Brief reflection** - What worked? What didn't?
4. **Token check** - Are we on budget?
5. **Consolidation check** - Need to merge short-term memories?

---

## 🎛️ Tiered Context Loading (NEW!)

### Decision Tree
```
Quick task (< 5 min):
    → Tier 0 (titles scan) - 500 tokens

Normal task (5-30 min):
    → Tier 1 (summaries + top 5 full) - 3-13K tokens
    → Use query to target relevant memories

Deep task (30-60 min):
    → Tier 2 (medium summaries + top 10 full) - 15-35K tokens

Comprehensive audit:
    → Tier 3 (everything) - 50K+ tokens
    → Only for major planning/refactoring
```

### Implementation
```python
# Quick scan
loader.get_context(tier=0)

# Targeted work
loader.get_context(tier=1, query="v2.2.3 features")

# Deep dive
loader.get_context(tier=2, query="architecture design")

# Full exhaustive (rare)
manager.get_context(tier=2)  # Fallback to original
```

---

## 📝 Memory Management Rules (NEW!)

### **Create Memories Frequently**
```
Breakthrough insight     → Long-term memory
Phase completion         → Long-term memory
Version milestone        → Long-term memory
Useful pattern/decision  → Short-term memory
Session notes           → Short-term memory
Bug fix with learning   → Short-term memory
```

### **Consolidation Triggers**
```
5-10 short-term memories   → Consolidate to 1-2 long-term
End of version            → Archive outdated, merge related
End of session            → Quick consolidation pass
Memory count > 50         → Major cleanup
```

### **Memory Lifecycle**
```
Create → Tag → Use → Consolidate → Archive
   ↓       ↓     ↓        ↓           ↓
  20T    10T   0T*      -50T        -80T

*Reading is FREE with summary cache (Tier 0/1)
```

---

## 🚀 Token Optimization Workflows (NEW!)

### **File Reading Strategy**
```python
# 1. Check size first
if file < 300 lines:
    read_file(full)  # ~1.5-4.5K tokens
else:
    # 2. Grep for patterns
    grep_results = grep_search(pattern)
    
    # 3. Read context windows
    if matches < 5:
        read_file_context(line, before=50, after=50)  # 70-90% savings
    else:
        # Summary approach
        read_file(offset=1, limit=100)  # Header
        read_multiple_contexts(top_5_matches)  # Targeted
        read_file(offset=-50)  # Footer
```

### **Multi-File Analysis**
```python
# OLD (sequential - wasteful)
for file in files:
    content = read_file(file)
    analyze(content)

# NEW (parallel + cached)
session_ctx = SessionContext()

# Parallel read (first time)
results = parallel_read([read_file_smart(f, session_ctx) for f in files])

# Later in same session - free from cache!
cached = [read_file_smart(f, session_ctx) for f in files]  # 0 tokens!
```

### **Memory Loading Strategy**
```python
# Quick check
context = loader.get_context(tier=0)  # 500 tokens
scan_for_relevant_memories(context)

# Targeted load
context = loader.get_context(tier=1, query="current task")  # 3-13K tokens
load_top_relevant_full(context)

# Deep dive (rare)
context = loader.get_context(tier=2, query="full context")  # 15-35K tokens
```

---

## 🔄 Version Release Workflow (Enhanced)

### **Pre-Release**
1. Run test suite (parallel if possible)
2. Update version numbers
3. Update CHANGELOG
4. Create version memory (long-term)
5. Consolidate version-specific memories
6. Tag all related memories with version

### **Release**
1. Build package
2. Run integration tests
3. Create git tag
4. Push to repository
5. Update documentation

### **Post-Release**
1. **Memory consolidation** - Merge short-term into long-term
2. **Archive old version memories** - Keep only key learnings
3. **Update roadmap** - Reflect completed work
4. **Create release memory** - What shipped, what learned
5. **Session snapshot** - Capture state for next session

---

## 📊 Session Management (NEW!)

### **Session Start Protocol**
```
1. Load Tier 0 context (quick scan)
2. Search for relevant memories (query-based)
3. Load Tier 1 for found memories
4. Check for "in-progress" tags
5. Review last session snapshot
6. Create session plan
```

### **Mid-Session Checkpoints** (every 30-60 min)
```
1. Token check (are we on budget?)
2. Progress update (update_plan)
3. Brief memory creation (capture insights)
4. Cache stats (are optimizations working?)
```

### **Session End Protocol**
```
1. Create session summary memory
2. Consolidate short-term memories (if >5 new)
3. Update progress documents
4. Tag in-progress work
5. Token usage report
6. Reflection capture
```

---

## 🎯 Parallel Threading Guidelines

### **Safe to Parallelize**
```
✅ grep_search across multiple directories
✅ read_file for independent files
✅ list_dir for different paths
✅ find_by_name in separate folders
✅ Independent code_search queries
✅ Memory searches with different queries
```

### **Must Stay Sequential**
```
❌ read → edit → verify (dependency chain)
❌ create file → populate file (logical order)
❌ test → fix → test (iterative loop)
❌ build → install → test (process dependency)
```

### **Hybrid Approach**
```
✓ Parallel exploration → Sequential synthesis
✓ Parallel reads → Sequential edits
✓ Parallel searches → Sequential implementation
✓ Parallel validation → Sequential fixes
```

---

## 🧪 Quality Assurance

### **Token Budget Monitoring**
```
Every phase end: Check usage
    < 50% used → Continue freely
    50-70% used → Optimize next phase
    70%+ used → Pause, consolidate, resume

Every session: Create budget report
    Include: Start, checkpoints, end
    Track: Actual vs projected
    Learn: What burned tokens? Optimize!
```

### **Effectiveness Metrics**
```
Track per session:
    - Time to completion
    - Token efficiency (actual vs projected)
    - Cache hit rate
    - Parallel vs sequential breakdown
    - Quality of outputs

Compare across sessions:
    - Are we getting faster?
    - Are we using fewer tokens?
    - Is quality maintained/improving?
```

---

## 🌟 Best Practices (Updated)

### **1. Think Parallel**
- Default to parallel for independent operations
- Only sequence when dependencies exist
- Use session cache to eliminate duplicate reads

### **2. Memory as First-Class Citizen**
- Create memories liberally (cheap with summaries)
- Consolidate regularly (prevent overload)
- Use tiered loading (90-95% token savings)

### **3. Progressive Enhancement**
- Start with Tier 0 scan
- Escalate to Tier 1 if needed
- Only Tier 2/3 for comprehensive work

### **4. Continuous Optimization**
- Reflect at phase boundaries
- Consolidate at version boundaries
- Optimize at session boundaries

### **5. Measure Everything**
- Token usage per phase
- Cache hit rates
- Parallel speedups
- Quality metrics

---

## 📚 Reference Commands

### **Memory Management**
```bash
# Quick context
whitemagic context --tier 0

# Targeted search
whitemagic search "query" --limit 5

# Consolidation
whitemagic consolidate --dry-run false

# Cache stats
whitemagic stats
```

### **Optimization Tools**
```python
# Session-cached reading
from whitemagic.smart_read import SessionContext, read_file_smart
ctx = SessionContext()
content = read_file_smart(path, ctx)

# Tiered memory loading
from whitemagic.optimized_context import OptimizedMemoryLoader
loader = OptimizedMemoryLoader(manager)
context = loader.get_context(tier=1, query="task")
```

---

## 🔮 Future Enhancements

### **Phase 2 (Next Version)**
- Batch summarization after parallel reads
- LLM-powered summary generation
- Auto-tier selection based on task complexity

### **Phase 3 (Later)**
- Predictive caching (anticipate next reads)
- Adaptive parallelism (auto-tune thread count)
- Cross-session memory optimization

---

**Status**: Active and proven  
**Effectiveness**: 40-50x vs baseline workflows  
**Next Review**: After v2.2.3 release

**Last Updated**: November 16, 2025, 9:15 AM
