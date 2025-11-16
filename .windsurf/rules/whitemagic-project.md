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
