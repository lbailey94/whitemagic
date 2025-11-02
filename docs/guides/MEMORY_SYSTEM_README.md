# Memory System for Tiered AI Prompts

A lightweight external memory system that provides persistent learning across AI sessions using markdown files and automatic consolidation.

## Architecture Overview

```
whitemagic/
├── TIER_0_CORE.md              # Minimal prompt (~200 tokens)
├── TIER_1_STANDARD.md          # Standard workflow (~500 tokens)
├── UNIFIED_CAPABILITY_PROMPT.md # Full protocol (Tier 2, ~1000+ tokens)
├── memory_manager.py           # Memory management tool
├── memory/
│   ├── short_term/             # Recent memories (7-day retention)
│   ├── long_term/              # Consolidated insights
│   ├── archive/                # Soft-deleted short-term memories with audit trail
│   └── metadata.json           # Memory index, settings, and consolidation log
└── MEMORY_SYSTEM_README.md     # This file
```

## How It Works

### Tier System

**Tier 0 (Core)**: ~200 tokens
- Essential principles only
- For quick queries and simple tasks
- Minimal memory context (last 2 short-term memories)

**Tier 1 (Standard)**: ~500 tokens
- Structured Plan→Do→Check→Act workflow
- Hypothesis-driven research mode
- Standard memory context (5 short-term, 2 long-term)

**Tier 2 (Full Protocol)**: ~1000+ tokens
- Complete multi-role, multi-phase system
- Comprehensive memory architecture
- Full context (10 short-term, 5 long-term)

### Memory Types

**Short-Term Memory** (`memory/short_term/`)
- Recent discoveries, decisions, and context
- Kept for 7 days by default
- Automatically consolidated into long-term storage
- Use for: session insights, temporary context, work-in-progress

**Long-Term Memory** (`memory/long_term/`)
- Distilled knowledge and reusable patterns
- Persistent across sessions
- Contains consolidated short-term memories
- Use for: proven heuristics, domain knowledge, process learnings

**Archive** (`memory/archive/`)
- Retains consolidated short-term files for later review
- Maintains provenance for auditability
- Entries remain searchable when `--include-archived` is used

## Usage

### For AI Models

**1. Starting a Session**
```markdown
Load appropriate tier based on task complexity:
- Simple query → Tier 0 + minimal context
- Standard task → Tier 1 + standard context
- Complex/high-stakes → Tier 2 + full context

Generate context with: `python3 memory_manager.py context <tier>`
```

**2. During Work**
```markdown
Log key insights and decisions as you work:
- "This approach worked because..."
- "Edge case discovered: ..."
- "Heuristic learned: If X, then Y"
```

**3. Ending a Session**
```markdown
Export learnings using memory_manager:
- Create short-term memory for immediate context
- Create long-term memory for reusable insights
- Tag appropriately for future retrieval
```

### For Users (CLI)

**Create a memory:**
```bash
python3 memory_manager.py create \
  --title "Title" \
  --content "Content here" \
  --type short_term \
  --tag tag1 \
  --tag tag2
```

**List all memories:**
```bash
python3 memory_manager.py list
python3 memory_manager.py list --include-archived  # include archive entries
```

**Search memories:**
```bash
python3 memory_manager.py search --query "keyword"
python3 memory_manager.py search --tag debugging --tag heuristic
```

**Consolidate old memories:**
```bash
python3 memory_manager.py consolidate --dry-run   # preview actions
python3 memory_manager.py consolidate             # perform consolidation
```
Archives short-term memories older than 7 days into long-term storage.
Memories tagged with `heuristic`, `pattern`, `proven`, `decision`, or `insight`
are auto-promoted to the long-term store. Source files are moved to the archive
folder rather than deleted, and a consolidation log is appended to metadata.

**Generate context summary:**
```bash
python3 memory_manager.py context 1  # For Tier 1 prompt
python3 memory_manager.py context 2 --output context.md  # write to file
```
Outputs are token-aware and omit YAML front matter.

### Python API

```python
from memory_manager import MemoryManager

manager = MemoryManager()

# Create memory
manager.create_memory(
    title="Discovered Pattern",
    content="When debugging API issues, always check rate limits first",
    memory_type="long_term",
    tags=["debugging", "api", "heuristic"]
)

# Read recent memories
recent = manager.read_recent_memories("short_term", limit=5)

# Search
results = manager.search_memories("debugging")

# Generate context for AI
context = manager.generate_context_summary(tier=1)
print(context)

# Consolidate
manager.consolidate_short_term()
```

## Memory File Format

All memories are markdown files with YAML frontmatter:

```markdown
---
title: Example Memory
created: 2025-10-23T16:49:00
tags: ["example", "pattern", "heuristic"]
---

## Context
Brief description of when/why this insight was discovered.

## Content
The actual insight, decision, or knowledge to preserve.

## Applicability
When to apply this knowledge or pattern.
```

## Configuration

Edit `memory/metadata.json` to customize:

```json
{
  "version": "1.1",
  "short_term_retention_days": 7,
  "consolidation_threshold": 5,
  "memory_index": [],
  "consolidation_log": []
}
```

- `short_term_retention_days`: How long to keep short-term memories before consolidation
- `consolidation_threshold`: Number of old memories to trigger auto-consolidation warning
- `memory_index`: Automatically maintained index of all memories

## Workflow Examples

### Example 1: Quick Query (Tier 0)
```bash
# User: "What's the best way to handle API rate limits?"

# 1. Load Tier 0 prompt + minimal context
python3 memory_manager.py context 0

# 2. AI responds using core principles
# 3. No memory creation needed for simple query
```

### Example 2: Standard Development Task (Tier 1)
```bash
# User: "Build a user authentication system"

# 1. Load Tier 1 prompt + standard context
python3 memory_manager.py context 1

# 2. AI follows Plan→Do→Check→Act
# 3. During work, discovers JWT is best for this use case
# 4. Create short-term memory:
python3 memory_manager.py create \
    --title "Auth Pattern for Stateless APIs" \
    --content "JWT tokens work well for microservices because..." \
    --type short_term \
    --tag auth \
    --tag jwt \
    --tag pattern

# 5. After testing confirms pattern, promote to long-term:
python3 memory_manager.py create \
    --title "Stateless Auth Heuristic" \
    --content "For microservices: prefer JWT over sessions..." \
    --type long_term \
    --tag auth \
    --tag heuristic \
    --tag proven
```

### Example 3: Complex Architecture Design (Tier 2)
```bash
# User: "Design a scalable multi-tenant SaaS architecture"

# 1. Load Tier 2 (full protocol) + comprehensive context
python3 memory_manager.py context 2

# 2. AI engages full multi-role, multi-phase workflow
# 3. Creates multiple short-term memories during process:
#    - Research findings on tenant isolation strategies
#    - Design decisions with rationale
#    - Security considerations discovered
#    - Performance trade-offs analyzed

# 4. At end, consolidates key learnings to long-term:
#    - "Multi-Tenancy Design Patterns"
#    - "Database Isolation Strategies Compared"
#    - "Cost-Performance Trade-offs for SaaS"

# 5. Weekly: Run consolidation to archive old context
python3 memory_manager.py consolidate
```

## Best Practices

### For AI Models
1. **Match tier to task complexity** - Don't use Tier 2 for simple queries
2. **Load context early** - Start with relevant memories
3. **Log as you work** - Don't wait until end to create memories
4. **Tag thoughtfully** - Use consistent taxonomy (domain, type, status)
5. **Distinguish insight types**:
   - **Observations**: What happened
   - **Decisions**: What was chosen and why
   - **Heuristics**: Reusable rules ("If X, then Y")
   - **Patterns**: Recurring structures or approaches

### For Users
1. **Regular consolidation** - Run weekly to keep short-term manageable
2. **Search before creating** - Avoid duplicate memories
3. **Review long-term** - Periodically validate if insights still hold
4. **Curate ruthlessly** - Delete obsolete or wrong memories
5. **Version prompts** - Track which tier versions work best

## Memory Taxonomy (Suggested Tags)

**By Domain:**
- `coding`, `debugging`, `architecture`, `testing`, `security`
- `research`, `analysis`, `creative`, `planning`

**By Type:**
- `heuristic` (reusable rule)
- `pattern` (recurring structure)
- `decision` (choice made + rationale)
- `insight` (new understanding)
- `failure` (what didn't work)

**By Status:**
- `proven` (validated across multiple uses)
- `experimental` (needs more testing)
- `deprecated` (no longer applicable)

**By Context:**
- `project_name` (specific to a project)
- `general` (broadly applicable)

## Maintenance

### Weekly Tasks
```bash
# Consolidate old short-term memories
python3 memory_manager.py consolidate

# Review and clean up
python3 memory_manager.py list --include-archived
# Manually delete outdated memories
```

### Monthly Tasks
```bash
# Search for deprecated patterns
python3 memory_manager.py search --query "deprecated"

# Review long-term memory quality
# Consider splitting large consolidated files
```

## Integration with AI Tools

### For Chat Interfaces
Paste relevant context at start of conversation:
```bash
python3 memory_manager.py context 1 > context.txt
# Copy context.txt into chat
```

### For IDE Assistants
Use context command in system prompt or workspace settings:
```json
{
  "systemPrompt": "$(cat TIER_1_STANDARD.md) \n\n $(python3 memory_manager.py context 1)"
}
```

### For API Integrations
```python
# Prepend context to user messages
context = manager.generate_context_summary(tier=1)
messages = [
    {"role": "system", "content": tier_1_prompt + "\n\n" + context},
    {"role": "user", "content": user_query}
]
```

## Advanced: Custom Memory Types

Extend the system by creating specialized memory subfolders:

```bash
mkdir -p memory/patterns    # Code/design patterns
mkdir -p memory/failures    # Things that didn't work
mkdir -p memory/projects    # Project-specific context
```

Modify `memory_manager.py` to support additional types.

## Troubleshooting

**Memory files not created:**
- Check file permissions on `memory/` directories
- Ensure Python has write access

**Context too large for token limit:**
- Reduce tier level
- Manually select specific memories
- Increase consolidation frequency

**Memories not relevant:**
- Improve tagging consistency
- Use search to validate before creating
- Delete or update stale memories

## Future Enhancements

- [ ] Semantic search using embeddings
- [ ] Automatic relevance scoring for context selection
- [ ] Memory decay (weight by recency and access frequency)
- [ ] Cross-memory linking and knowledge graphs
- [ ] Integration with vector databases
- [ ] A/B testing framework for prompt effectiveness

---

**Version**: 1.0  
**Last Updated**: 2025-10-23  
**Maintainer**: Cascade AI Memory System
