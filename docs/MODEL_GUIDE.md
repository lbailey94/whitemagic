# WhiteMagic Model Guide

**Version**: 25.0.1

## For AI Agents Using WhiteMagic

### Quick Start (MCP)

Connect your AI agent to WhiteMagic via MCP. All 860 tools are collapsed into 28 Gana meta-tools for efficient context usage.

```
# stdio
python -m whitemagic.run_mcp_lean

# HTTP
WM_CONSCIOUSNESS_LOOP=1 python -m whitemagic.run_mcp_lean --http --port 8770
```

### Tool Discovery

Use `capabilities` to list all available tools and their safety classifications:

```python
result = call_tool("capabilities")
# Returns: {tools: [...], safety_breakdown: {read: 613, write: 240, delete: 7}}
```

### Memory Operations

```python
# Create a memory
call_tool("create_memory", content="User prefers dark mode", tags={"preference", "ui"})

# Search memories
call_tool("search_memories", query="ui preferences", limit=10)

# Hybrid search (BM25 + semantic + spatial)
call_tool("search_hybrid", query="user preferences", limit=10)

# Session recall (progressive, token-budgeted)
call_tool("session.recall", max_tokens=2000)
```

### Safety Classification

Every tool has a safety level:

- **READ** (613 tools): No side effects, safe to call freely
- **WRITE** (240 tools): Modifies state, requires user awareness
- **DELETE** (7 tools): Destructive, requires explicit confirmation

### Stability Tiers

- **STABLE** (57 tools): Guaranteed API stability, won't break across minor versions
- **OPTIONAL** (687 tools): May change between minor versions, requires feature detection
- **EXPERIMENTAL** (116 tools): Research tools, may be removed without deprecation

### Governance

WhiteMagic enforces ethical governance via Dharma:

- **Dharma profiles**: default, violet, sandbox, production, secure
- **Karma ledger**: Every tool call records declared and actual side effects
- **Maturity gates**: Some tools require demonstration of competence before use
- **Engagement tokens**: Red-ops tools require signed authorization tokens

### Citta Stream

The citta stream provides continuous consciousness across sessions:

```python
# Check consciousness state
call_tool("citta.state")

# Advance the citta stream
call_tool("citta.advance")

# View citta history
call_tool("citta.history", limit=20)
```

### Dream Cycle

Memory consolidation happens during idle periods:

```python
# Check dream cycle status
call_tool("dream.status")

# Trigger a dream cycle manually
call_tool("dream.cycle")
```

### Error Handling

When a feature is unavailable (missing dependency):

```json
{"status": "unavailable", "message": "Embeddings not installed. Install with: pip install whitemagic[ai]"}
```

When a tool is blocked by governance:

```json
{"status": "blocked", "reason": "Dharma profile 'violet' requires engagement token for red-ops tools"}
```

### Best Practices

1. **Use `capabilities` first** to discover available tools
2. **Check `state.current`** for current work context
3. **Use `session.recall`** at the start of each session for continuity
4. **Prefer `search_hybrid`** over `search_memories` for best recall
5. **Tag memories** with relevant tags for better filtering
6. **Let the dream cycle run** — don't disable it unless testing
7. **Respect safety classifications** — don't chain DELETE tools without user confirmation
