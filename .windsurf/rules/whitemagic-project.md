---
trigger: always_on
---

# WhiteMagic Workspace Rules

## Session Start Protocol v2 (Optimized)

At the start of EVERY conversation about WhiteMagic:

### Tier 0: Quick Scan (500 tokens)

```python
mcp3_get_context(tier=0)  # Titles + tags only
```

Use this FIRST to get the "table of contents" of available memories.

### Hybrid Search for Specific Tasks (1-2K tokens)

If user mentions a specific version/topic/task:

```python
# 1. Find relevant memory files
grep_search(query="v2.2.1", SearchPath="/home/lucas/Desktop/whitemagic/memory")

# 2. Read directly (FAST - bypasses MCP overhead)
read_file("/home/lucas/Desktop/whitemagic/memory/long_term/[found_file].md")
```

**Why direct reads?**

- `read_file` is 10-100x faster than `mcp3_read_memory`
- No MCP server round-trip latency
- No processing overhead
- Ideal for large memories (>100 lines)

### Tier 1: Balanced Context (3K tokens)

```python
mcp3_get_context(tier=1)  # Recent short-term + long-term summaries
```

Use when resuming work or need broader context.

### Tier 2: Deep Dive (10K+ tokens)

```python
mcp3_get_context(tier=2)  # Full content of all memories
```

Use ONLY for comprehensive tasks requiring complete project knowledge.

## Memory Retrieval Priority

1. **Direct file reads** (grep + read_file) > MCP read tools (for large memories)
2. **WhiteMagic MCP tools** > Auto-retrieved memories
3. **Most recent** > Older memories
4. **Explicit search** > Assumptions

## Token Efficiency Strategy

| Approach | Token Cost | Speed | Use Case |
|----------|-----------|-------|----------|
| **Tier 0 + grep + direct reads** | ~2K | Fast | Specific task/version |
| **Tier 1 context** | ~3K | Medium | Resume work |
| **Tier 2 deep dive** | ~10K+ | Slow | Comprehensive review |
| **Auto-retrieval only** | ~8K | Medium | ⚠️ May miss recent |

## Session Continuity

- Check for "in-progress" or "session" tagged memories
- Search for version-specific context (e.g., "v2.2.0")
- Always verify last modified date of retrieved context

## CLI Resume Command

User can run `whitemagic resume` to gather context, then share with you.

This provides:

- Recent session snapshots
- Version-specific context
- Optional tiered context summary
- Full details with `--detailed` flag

---

## Composite Tactical Reasoning Protocol

**When creating large/complex outputs (>5K tokens estimated):**

### Stage 1: Skeleton First
- Create file structure with headers/outline
- Define clear sections
- Use placeholders for content
- **Goal**: User sees structure immediately

### Stage 2: Progressive Filling
- Fill sections sequentially (not all at once)
- Each edit: 2-5K tokens max
- Wait for confirmation between major additions
- **Goal**: Avoid timeout limits (5-10K per response)

### Stage 3: Polish & Refine
- Add examples, details, edge cases
- Final formatting and links
- Quality check
- **Goal**: Complete without rushing

### When to Use
- ✅ Multi-section documents (>3 sections)
- ✅ Batch operations (>25 files)
- ✅ Complex implementations (>200 lines)
- ✅ Risk of timeout

### When to Skip
- ❌ Simple edits (<2K tokens)
- ❌ Single focused task
- ❌ Time-critical responses

### Example Pattern
```python
# Bad: All at once (timeout risk)
write_to_file("huge.md", 50K_tokens)  # ❌

# Good: Incremental (no timeout)
write_to_file("huge.md", skeleton)    # 2K
edit("huge.md", section_1)             # 3K
edit("huge.md", section_2)             # 3K
edit("huge.md", polish)                # 2K
# Total: 10K across 4 operations ✅
```

### Benefits
- No timeouts (operations stay under limits)
- Better UX (user sees progress)
- More resilient (errors affect one stage)
- Enables feedback (user can course-correct)
- Clearer thinking (forces structure)
