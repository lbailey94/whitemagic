# Quick Start Guide

Get started with the Tiered Prompt + Memory System in 5 minutes.

## 1. Understanding the System

**Three Tiers of Prompts:**
- **Tier 0** (`TIER_0_CORE.md`): Minimal, ~200 tokens - for quick queries
- **Tier 1** (`TIER_1_STANDARD.md`): Standard, ~500 tokens - for normal work
- **Tier 2** (`UNIFIED_CAPABILITY_PROMPT.md`): Full, ~1000+ tokens - for complex tasks

**Memory System:**
- **Short-term** (`memory/short_term/`): Recent context, 7-day retention
- **Long-term** (`memory/long_term/`): Distilled insights, permanent

## 2. Basic Usage

### For AI Models

**Start a session:**
```bash
# Choose your tier based on task complexity
cat TIER_1_STANDARD.md
python3 memory_manager.py context 1
```

**During work:**
- Log insights as you discover them
- Note what works and what doesn't

**End session:**
```python
from memory_manager import MemoryManager
mm = MemoryManager()

mm.create_memory(
    title="Your insight here",
    content="Detailed explanation...",
    memory_type="short_term",
    tags=["domain", "type"]
)
```

### For Users

**List memories:**
```bash
python3 memory_manager.py list
```

**Search:**
```bash
python3 memory_manager.py search --query "debugging"
```

**Create memory:**
```bash
python3 memory_manager.py create \
  --title "Title" \
  --content "Detailed explanation..." \
  --type short_term \
  --tag tag1 \
  --tag tag2
```

**Weekly maintenance:**
```bash
python3 memory_manager.py consolidate
```

## 3. Example Workflow

**Simple Query (Tier 0):**
```bash
# Load minimal prompt + context
cat TIER_0_CORE.md
python3 memory_manager.py context 0

# Work...
# No memory needed for simple queries
```

**Standard Task (Tier 1):**
```bash
# Load standard prompt + context
cat TIER_1_STANDARD.md
python3 memory_manager.py context 1

# Work following Plan→Do→Check→Act
# Create short-term memories for discoveries
python3 memory_manager.py create \
  --title "Discovery" \
  --content "Details..." \
  --type short_term \
  --tag research

# If insight is valuable, promote to long-term
python3 memory_manager.py create \
  --title "Heuristic" \
  --content "Details..." \
  --type long_term \
  --tag heuristic
```

**Complex Project (Tier 2):**
```bash
# Load full protocol + comprehensive context
cat UNIFIED_CAPABILITY_PROMPT.md
python3 memory_manager.py context 2

# Engage full multi-role workflow
# Create multiple memories during process
# Consolidate learnings at end
```

## 4. Pro Tips

1. **Match tier to complexity** - Don't overload simple tasks
2. **Tag consistently** - Use the taxonomy in MEMORY_SYSTEM_README.md
3. **Log as you go** - Don't wait until end
4. **Search before creating** - Avoid duplicates
5. **Consolidate weekly** - Keep short-term manageable

## 5. Common Commands

```bash
# List all memories
python3 memory_manager.py list

# List including archived entries
python3 memory_manager.py list --include-archived

# List sorted by most recently accessed
python3 memory_manager.py list --sort-by accessed

# Search memories
python3 memory_manager.py search --query "keyword"
python3 memory_manager.py search --tag debugging --tag heuristic

# Create a memory from a file
python3 memory_manager.py create \
  --title "Heuristic" \
  --content-file notes/heuristic.md \
  --type long_term \
  --tag heuristic

# Stream content from STDIN (useful for piping)
echo "New discovery" | python3 memory_manager.py create \
  --title "Pipeline Insight" \
  --stdin \
  --type short_term

# Update a memory
python3 memory_manager.py update example_memory.md \
  --add-tag new-tag \
  --content "Updated content"

# Delete a memory (archives by default)
python3 memory_manager.py delete example_memory.md

# Permanently delete a memory
python3 memory_manager.py delete example_memory.md --permanent

# Restore an archived memory
python3 memory_manager.py restore example_memory.md
python3 memory_manager.py restore example_memory.md --type long_term

# List all tags with statistics
python3 memory_manager.py list-tags

# Normalize legacy tags (migration tool)
python3 memory_manager.py normalize-tags  # Dry-run (safe)
python3 memory_manager.py normalize-tags --no-dry-run  # Apply changes

# Get context for a tier
python3 memory_manager.py context 0  # Tier 0
python3 memory_manager.py context 1  # Tier 1
python3 memory_manager.py context 2  # Tier 2

# Consolidate old memories (dry-run first if unsure)
python3 memory_manager.py consolidate --dry-run
python3 memory_manager.py consolidate
```

## 6. File Structure

```
whitemagic/
├── TIER_0_CORE.md              # Tier 0 prompt
├── TIER_1_STANDARD.md          # Tier 1 prompt
├── UNIFIED_CAPABILITY_PROMPT.md # Tier 2 prompt
├── memory_manager.py           # Memory tool
├── memory/
│   ├── short_term/             # Recent memories
│   │   └── example_short_term.md
│   ├── long_term/              # Distilled insights
│   │   └── example_long_term.md
│   ├── archive/                # Soft-deleted short-term memories
│   └── metadata.json           # Index
├── MEMORY_SYSTEM_README.md     # Full documentation
└── QUICKSTART.md              # This file
```

## 7. Next Steps

- Read `MEMORY_SYSTEM_README.md` for detailed docs
- Check example memory files for format
- Experiment with different tiers
- Build your knowledge base over time

## Need Help?

See `MEMORY_SYSTEM_README.md` for:
- Full API documentation
- Advanced usage patterns
- Troubleshooting
- Best practices
