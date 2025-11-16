---
trigger: always_on
---

# Workflow Rules v3.1 - Universal AI System

**Date**: November 16, 2025  
**Version**: 3.1 (adds Art of War + I Ching threading)  
**Scope**: ANY AI system with WhiteMagic (not just Windsurf)  
**Goal**: Ancient wisdom meets universal patterns

---

## 🌍 Universal Applicability Design

### Core Principles

**1. WhiteMagic patterns should work in ANY environment**:

**2. Strategic thinking before tactical execution** (Art of War):
- Assess terrain before acting
- Check five factors (道天地將法)
- Know when to proceed, when to wait

**3. Philosophical alignment in architecture** (I Ching):
- Threading tiers: 8, 16, 32, 64, 128, 256
- Based on trigrams (8) and hexagrams (64)
- Natural progression, not arbitrary numbers
- Claude Desktop with MCP
- ChatGPT with plugins
- Custom AI agents
- API-based integrations
- Command-line tools
- Web interfaces

---

## ⚔️ Art of War Integration (v3.1)

### **Pre-Task Assessment** (Sun Tzu)

Before executing any task, perform strategic assessment:

**1. Terrain Analysis** (\u5730\u5f62):
```python
from whitemagic.strategy import TaskTerrain

# Assess task terrain
terrain_types = {
    ACCESSIBLE: "Straightforward, proceed directly",
    ENTANGLING: "Dependencies, resolve first",
    TEMPORIZING: "Need more info, gather intelligence",
    NARROW: "Sequential only, no parallelism",
    PRECIPITOUS: "High risk, extreme caution",
    DISTANT: "Long duration, plan checkpoints"
}
```

**2. Five Factors** (\u4e94\u4e8b):
```python
# Check before proceeding
\u9053 (Dao): Aligned with values?
\u5929 (Heaven): Right timing?
\u5730 (Earth): Have resources?
\u5c07 (General): Clear strategy?
\u6cd5 (Law): Following best practices?

If score >= 0.8: PROCEED
If score >= 0.6: PROCEED_WITH_CAUTION
Else: PREPARE_MORE
```

**3. Threading Tier** (I Ching):
```python
from whitemagic.threading_tiers import get_tier_threads

Tier 0: 8 threads (8 trigrams)
Tier 1: 16 threads
Tier 2: 32 threads
Tier 3: 64 threads (hexagrams - sweet spot!)
Tier 4: 128 threads
Tier 5: 256 threads (ultimate complexity)
```

---

## 📋 Additional Workflow Rules (v3.0-3.1 Updates)

### 1. **Metrics-Driven Reflection** (NEW!)

**Pattern**: Track quantitative metrics at every phase boundary

**Metrics to Track**:
```yaml
# Token Efficiency
token_budget: 200000
token_used: 99400
token_efficiency_pct: 49.7%
tokens_per_feature: ~25000

# Strategic Progress
version_target: v2.2.3
features_complete: 7/7
timeline_vs_estimate: "50% faster"

# Tactical Progress
phase_target: "Token Optimizations Phase 1"
tasks_complete: 4/4
quality_rating: "production-ready"

# Learning Metrics
problems_solved: 3  # import bugs, version mismatches, etc
patterns_discovered: 5  # parallel threading, tiered loading, etc
memories_created: 4
consolidations_performed: 1

# Performance
real_time_elapsed: "30 minutes"
effective_speedup: "40-50x vs baseline"
quality_maintained: true
ai_stress_level: 0/10
```

**When to Check**:
- End of every phase
- End of every session
- End of every version
- When stuck or confused

**Actions Based on Metrics**:
```
If token_used > 70%:
    → Consolidate memories
    → Use Tier 0/1 only
    → Consider session break

If timeline > 150% estimate:
    → Review approach
    → Simplify scope
    → Request help

If problems_solved < 1 per hour:
    → Switch to scientific method
    → Break into smaller steps
    → Reference similar past problems

If quality_rating < "good":
    → Slow down
    → Add tests
    → Review against standards
```

---

### 2. **Problem-Solving Framework** (NEW!)

**Decision Tree for Unknown Problems**:

```
Encounter problem
    ↓
├─ Have I seen this before?
│  ├─ YES → Search memories for solution
│  │         Apply previous pattern
│  │         If works → Document variations
│  │         If fails → Continue to next step
│  │
│  └─ NO → Is it similar to past problems?
│           ├─ YES → Adapt previous solution
│           │         Document new pattern
│           │
│           └─ NO → Novel problem
│                     ↓
│                  Scientific Method:
│                  1. Define problem precisely
│                  2. Form hypothesis
│                  3. Test smallest component
│                  4. Gather data
│                  5. Iterate
│                  6. Document solution
│                  7. Add to problem-solving memories
```

**Memory Structure for Problem-Solving**:
```
memory/problem_solving/
  ├── patterns/
  │   ├── api_signature_mismatch.md
  │   ├── import_errors.md
  │   ├── version_conflicts.md
  │   └── ...
  ├── novel_problems/
  │   └── [date]_[problem_title].md
  └── lessons_learned/
      └── [date]_[insight].md
```

---

### 3. **Scratchpad / Working Memory** (NEW!)

**Pattern**: Use short-term memories as "working memory" for active work

**Workflow**:
```
Start work session:
    → Create scratchpad memory
    → Tag: "scratchpad", "in-progress", "[date]"

During work:
    → Update scratchpad with:
      - Current thoughts
      - Decisions made
      - Open questions
      - Next steps

End work session:
    → Review scratchpad
    → Extract useful insights → New memories
    → Archive or delete scratchpad
```

**Scratchpad Template**:
```markdown
# Scratchpad: [Task Name]

## Current Focus
[What I'm working on right now]

## Decisions Made
1. [Decision + reasoning]
2. ...

## Open Questions
1. [Question + why it matters]
2. ...

## Next Steps
1. [Immediate next action]
2. [Then this]

## Random Thoughts / Ideas
- [Don't lose interesting tangents]
- [Even if not immediately relevant]

## Blocked On
- [What's stopping progress]
- [Who/what needed to unblock]
```

---

### 4. **Auto-Update System** (NEW!)

**Pattern**: Run automated checks/updates at version boundaries

**Version Release Checklist with Auto-Update**:
```bash
#!/bin/bash
# Run at end of every version release

# 1. Update all version numbers
whitemagic update-versions --version $NEW_VERSION

# 2. Check for dependency updates
whitemagic check-dependencies --security-only

# 3. Update MCP tools if needed
whitemagic update-mcp-tools

# 4. Regenerate API clients (SDKs)
whitemagic generate-clients

# 5. Run full test suite
pytest

# 6. Update documentation versions
whitemagic update-docs-versions

# 7. Check for breaking changes
whitemagic check-breaking-changes

# 8. Create release notes
whitemagic generate-release-notes --version $NEW_VERSION

# 9. Commit and tag
git add .
git commit -m "chore: release v$NEW_VERSION"
git tag v$NEW_VERSION
```

**Automated Maintenance Tasks**:
- Dependency security updates (weekly)
- Memory consolidation (every 10 short-term memories)
- Cache cleanup (weekly)
- Test coverage check (every version)
- Documentation sync check (every version)

---

### 5. **Consolidation Phase Protocol** (ENHANCED)

**New**: Add metrics review to consolidation

**Enhanced Consolidation Checklist**:
```
[ ] Reflect on phase completion
[ ] Review metrics (see Metrics-Driven Reflection)
[ ] Create phase summary memory
[ ] Check token efficiency vs target
[ ] Review problems encountered and solved
[ ] Update problem-solving patterns if new solutions
[ ] Consolidate scratchpad memories
[ ] Archive completed work
[ ] Check strategic progress vs roadmap
[ ] Identify improvement opportunities
[ ] Create next phase plan
[ ] Token budget check for next phase
```

---

### 6. **Cross-Environment Compatibility** (NEW!)

**Design Principle**: Every feature should work via multiple interfaces

**Interfaces to Support**:
1. **CLI** - For automation and scripts
2. **MCP** - For IDE integration (Claude, etc.)
3. **Python API** - For programmatic use
4. **REST API** - For web/mobile apps
5. **TypeScript SDK** - For Node.js apps
6. **Interactive TUI** - For human exploration

**Example Feature Implementation**:
```
Feature: "Get Context at Tier"

Implementations:
1. CLI: whitemagic context --tier 1 --query "v2.2.3"
2. MCP: Call tool "get_context" with tier=1, query="v2.2.3"
3. Python: manager.get_context(tier=1, query="v2.2.3")
4. REST: GET /api/v1/context?tier=1&query=v2.2.3
5. TS SDK: client.context.get({ tier: 1, query: "v2.2.3" })
6. TUI: Navigate → Context → Set tier: 1 → Search: "v2.2.3"
```

---

### 7. **Lessons Learned System** (NEW!)

**Pattern**: Automatically capture lessons when problems are solved

**Workflow**:
```
Encounter problem
    ↓
Solve problem
    ↓
whitemagic add-lesson \
    --problem "Import error in optimized_context.py" \
    --solution "Module was in wrong directory" \
    --pattern "Check import paths match file structure" \
    --tags "import-errors,debugging,python"
```

**Auto-Application**:
When similar problem detected:
```
⚠️  Detected: Import error
💡 Lesson available: "Check import paths match file structure"
   From: 2025-11-16 solving optimized_context import issue
   Apply this solution? [Y/n]
```

---

## 🎯 Universal Workflow Phases

### Phase 0: Session Start
```
1. Load appropriate tier context (usually Tier 1)
2. Review "start-here" tagged memories
3. Check metrics from last session
4. Load scratchpad if continuing work
5. Review current strategic/tactical plans
6. Create session plan
```

### Phase 1: Information Gathering
```
1. Parallel search across relevant sources
2. Use context-aware reading (smart_read)
3. Cache results in session context
4. Generate batch summary if >5 sources
```

### Phase 2: Planning
```
1. Update strategic plan if needed
2. Create/update tactical plan
3. Break into phases with metrics
4. Estimate tokens/time per phase
5. Check budget viability
```

### Phase 3: Implementation
```
1. Execute planned changes
2. Test incrementally
3. Update scratchpad with decisions
4. Track problems encountered
5. Document solutions as lessons
```

### Phase 4: Validation
```
1. Run tests
2. Check against success criteria
3. Measure metrics vs estimates
4. Document deviations
```

### Phase 5: Consolidation
```
1. Create phase summary memory
2. Review and record metrics
3. Consolidate scratchpad
4. Add lessons learned
5. Archive completed work
6. Prepare for next phase
```

### Phase 6: Session End
```
1. Create session summary
2. Final metrics report
3. Check consolidation needs
4. Tag in-progress work
5. Create "start-here" for next session
```

---

## 🛠️ Required MCP Tool Enhancements

### New Tools Needed

1. **`track_metric`** - Record quantitative metrics
   ```typescript
   track_metric({
     category: "token_efficiency",
     metric: "usage_percent",
     value: 49.7,
     context: "v2.2.3 Phase 1"
   })
   ```

2. **`add_lesson`** - Capture problem-solving patterns
   ```typescript
   add_lesson({
     problem: "Import error",
     solution: "Fixed path",
     pattern: "Check structure",
     tags: ["import", "python"]
   })
   ```

3. **`find_similar_problem`** - Search problem-solving memories
   ```typescript
   find_similar_problem({
     description: "Module not found error",
     context: "Python imports"
   })
   // Returns: Similar problems and their solutions
   ```

4. **`create_scratchpad`** - Working memory for session
   ```typescript
   create_scratchpad({
     task: "SDK realignment",
     initial_thoughts: "Need to bump Python SDK version"
   })
   ```

5. **`update_scratchpad`** - Add to working memory
   ```typescript
   update_scratchpad({
     section: "decisions",
     content: "Decided to use Option 1 approach"
   })
   ```

6. **`get_metrics_summary`** - Retrieve metrics dashboard
   ```typescript
   get_metrics_summary({
     time_range: "last_7_days",
     categories: ["token_efficiency", "velocity", "quality"]
   })
   ```

7. **`check_auto_updates`** - Run automated maintenance
   ```typescript
   check_auto_updates({
     categories: ["dependencies", "versions", "security"],
     apply: false  // dry-run first
   })
   ```

### Enhanced Existing Tools

1. **`create_memory`** - Add metrics field
   ```typescript
   create_memory({
     ...existing_params,
     metrics: {
       tokens_used: 25000,
       time_spent: "30 minutes",
       quality: "production-ready"
     }
   }