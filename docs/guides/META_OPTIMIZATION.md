# Meta-Optimization Guide (v2.2.5)

WhiteMagic v2.2.5 introduces **meta-optimization**: a hierarchical context loading system that reduces token burn by 60-97% while maintaining task relevance. This guide shows you how to leverage it.

---

## 1. Problem Statement

Traditional AI workflows load entire codebases or memory systems into context, consuming 50K-100K+ tokens before any real work begins. This:

- Exhausts token budgets quickly
- Slows response times
- Incurs unnecessary costs
- Limits session longevity

**Meta-optimization solves this** by intelligently loading only what you need, when you need it.

---

## 2. Core Concepts

### 2.1 Tiered Loading

WhiteMagic uses three context tiers:

| Tier | Purpose | Token Usage | Speed |
| --- | --- | --- | --- |
| **0 (Scan)** | Quick overview, minimal details | 2-3K tokens (97% savings) | Fastest |
| **1 (Balanced)** | Task-aware, selective loading | 3-6K tokens (90-94% savings) | Fast |
| **2 (Full)** | Comprehensive context | 10-15K tokens (75-85% savings) | Normal |

**Rule of thumb**: Start with Tier 0, escalate only when needed.

### 2.2 Task-Aware Filtering

The system analyzes your task description to identify relevant:

- File patterns (e.g., "auth bug" → `*auth*.py`, `*login*.js`)
- Directories (e.g., "API routes" → `api/`, `routes/`)
- Memory tags (e.g., "deployment" → memories tagged `deployment`, `production`)

This happens automatically—you just describe what you're doing.

### 2.3 Lazy Loading

Large files and memory collections aren't loaded until explicitly requested. The system provides:

- Summaries (1-2 lines per item)
- Metadata (path, size, tags)
- Expansion hooks (load full content on demand)

---

## 3. Using Meta-Optimization

### 3.1 Via CLI

```bash
# Generate Tier 0 context (quick scan)
whitemagic context --tier 0

# Generate Tier 1 with task filter
whitemagic context --tier 1 --query "fix authentication bug"

# Full context (Tier 2)
whitemagic context --tier 2
```

### 3.2 Via MCP (Windsurf/Claude Desktop)

```typescript
// Quick start - Tier 1 is default
const ctx = await mcp.getContext({ tier: 1 });

// Task-specific context
const ctx = await mcp.getContext({
  tier: 1,
  query: "optimize database queries"
});

// Minimal scan
const scan = await mcp.getContext({ tier: 0 });
```

### 3.3 Via Python API

```python
from whitemagic import load_workspace_for_task

# Tier 1 with task description
ctx = load_workspace_for_task(
    workspace_path="/path/to/project",
    task_description="Add user registration endpoint",
    tier=1
)

# Tier 0 quick scan
scan = load_workspace_for_task(
    workspace_path="/path/to/project",
    tier=0
)
```

---

## 4. Real-World Results

### 4.1 Validated Benchmarks

From `test_token_optimizations.py` (validated 2025-11-16):

```
Baseline (traditional full load): 63,345 tokens
Tier 0 (scan):                     1,883 tokens  (97.0% reduction)
Tier 1 (balanced):                 3,530 tokens  (94.4% reduction)
Tier 1 + query:                    6,120 tokens  (90.3% reduction)
```

### 4.2 Real Session Impact

**Before meta-optimization**:

- Session budget: 200K tokens
- Initial context: 63K tokens (31.5% consumed)
- Work remaining: 137K tokens (68.5%)

**After meta-optimization (Tier 1)**:

- Session budget: 200K tokens
- Initial context: 3.5K tokens (1.75% consumed)
- Work remaining: 196.5K tokens (98.25%)

**Result**: 18x more budget available for actual work!

---

## 5. Best Practices

### 5.1 Session Start Protocol

1. **Always start with Tier 0 or 1** unless you have a specific reason to load everything
2. **Use task descriptions** - they're not optional! "Fix auth bug" loads different context than "Add feature"
3. **Escalate only when stuck** - if Tier 1 doesn't have enough info, then load Tier 2

### 5.2 Progressive Loading Pattern

```python
# Start minimal
ctx = load_workspace_for_task(workspace, task, tier=0)

# Review summary - do you have enough?
if "authentication.py" in ctx.file_summaries:
    # Load that specific file
    content = read_file("src/authentication.py")
else:
    # Escalate to Tier 1 for more details
    ctx = load_workspace_for_task(workspace, task, tier=1)
```

### 5.3 Token Budget Management

Monitor token usage throughout your session:

```bash
# Track tokens consumed
whitemagic track token_efficiency usage_percent 12.5 "Post Tier 1 load"

# Check summary
whitemagic summary token_efficiency
```

If usage exceeds 60-70%, consider:

- Consolidating memories
- Ending session and resuming fresh
- Using more targeted queries

---

## 6. Advanced: Workspace Loader Internals

### 6.1 Architecture

```
load_workspace_for_task()
    ↓
Task Analysis
    ├─ Extract keywords
    ├─ Infer file patterns
    └─ Identify relevant paths
    ↓
Tiered Loading Strategy
    ├─ Tier 0: Count + list only
    ├─ Tier 1: Summaries + metadata
    └─ Tier 2: Full content (filtered)
    ↓
Output Generation
    ├─ Markdown formatting
    ├─ Lazy load markers
    └─ Token estimation
```

### 6.2 Customization

```python
from whitemagic.workspace_loader import WorkspaceLoader

loader = WorkspaceLoader(
    workspace_path="/path/to/project",
    max_depth=3,              # How deep to traverse
    exclude_patterns=[".git", "node_modules"],
    file_size_limit_kb=500    # Skip files larger than this
)

# Custom tier definitions
loader.set_tier_limits(
    tier_0_files=5,
    tier_1_files=20,
    tier_2_files=100
)

ctx = loader.load_for_task("Add GraphQL endpoint", tier=1)
```

---

## 7. Integration with Symbolic Reasoning

Meta-optimization pairs with symbolic reasoning (v2.2.5) to further compress context:

```python
from whitemagic import SymbolicMemoryBuilder

# Load Tier 1 context
ctx = load_workspace_for_task(workspace, task, tier=1)

# Compress using Chinese characters (30-50% additional savings)
builder = SymbolicMemoryBuilder()
symbolic_ctx = builder.build_symbolic_memory(
    content=ctx.to_markdown(),
    concepts=["authentication", "tokens", "sessions"]
)

# Now symbolic_ctx uses ~2K tokens instead of 3.5K
```

---

## 8. Troubleshooting

### Issue: "Tier 1 doesn't have the file I need"

**Solution**: Use more specific task descriptions or escalate to Tier 2

```bash
# Too generic
whitemagic context --tier 1 --query "bug"

# Better - specific enough to match relevant files
whitemagic context --tier 1 --query "user authentication login validation bug"
```

### Issue: "Token usage still high with Tier 1"

**Check**:

1. Are you loading Tier 1 multiple times? Cache results!
2. Is your workspace huge? Set `max_depth` and `file_size_limit`
3. Do you have massive memory collections? Consolidate first

### Issue: "Context missing critical information"

**Solution**: Tier 0/1 optimize for speed. If completeness matters:

- Use Tier 2 for comprehensive tasks
- Manually specify critical files
- Combine Tier 1 + targeted file reads

---

## 9. Metrics & Validation

Track your optimization effectiveness:

```bash
# Before using meta-optimization
whitemagic track baseline_tokens value 63000 "Traditional load"

# After Tier 1
whitemagic track optimized_tokens value 3500 "Tier 1 meta-opt"

# Calculate improvement
whitemagic summary token_efficiency
```

Expected results:

- **Tier 0**: 30-35x efficiency gain
- **Tier 1**: 15-20x efficiency gain
- **Tier 2**: 5-10x efficiency gain

---

## 10. Future Enhancements (v2.2.7+)

Planned improvements:

- **Adaptive tiers**: System learns optimal tier for different task types
- **Semantic caching**: Reuse contexts across similar tasks
- **Predictive loading**: Pre-fetch likely-needed files based on task patterns
- **Multi-workspace**: Load from multiple repos efficiently

---

## Summary

Meta-optimization is **the** foundational efficiency technique in WhiteMagic v2.2.5+:

✅ **Start with Tier 0 or 1** - save 90-97% tokens
✅ **Use task descriptions** - get relevant context automatically
✅ **Escalate progressively** - load more only when needed
✅ **Monitor token usage** - stay within budget
✅ **Combine with symbolic reasoning** - compress even further

With meta-optimization, your 200K token sessions can accomplish 10-20x more work. Use it!

---

**See also**:

- `SYMBOLIC_REASONING.md` - Compress context further with Chinese characters
- `WU_XING_AND_METRICS.md` - Track optimization effectiveness
- `QUICKSTART.md` - Basic usage patterns
