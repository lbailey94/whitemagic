# WhiteMagic Workspace Rules

## Session Start Protocol

At the start of EVERY conversation about WhiteMagic:

1. **Use `mcp3_get_context(tier=1)` first** for balanced context
2. **If specific task mentioned**, use `mcp3_search_memories(query="[task]")`
3. **DO NOT rely solely on auto-retrieved memories** (may be stale)

## Memory Retrieval Priority

- WhiteMagic MCP tools > Auto-retrieved memories
- Most recent > Older memories
- Explicit search > Assumptions

## Token Efficiency

- Use tiered context: tier 0 (quick), tier 1 (normal), tier 2 (deep)
- Only read full memories when specifically needed
- Prefer targeted searches over broad retrieval

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
