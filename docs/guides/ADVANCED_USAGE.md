# Advanced Usage Guide

## Table of Contents

1. [Memory Management](#memory-management)
2. [Tag System](#tag-system)
3. [Sorting and Access Tracking](#sorting-and-access-tracking)
4. [Automation and Scripting](#automation-and-scripting)
5. [Limitations and Best Practices](#limitations-and-best-practices)

---

## Memory Management

### Deleting Memories

**Soft Delete (Archive)**

```bash
# Archives the memory (default behavior)
python3 memory_manager.py delete example_memory.md

# The memory is moved to memory/archive/ and marked as archived
# Can still be viewed with --include-archived flag
```

**Permanent Delete**

```bash
# Permanently removes the memory (cannot be recovered)
python3 memory_manager.py delete example_memory.md --permanent
```

### Updating Memories

**Update Content**

```bash
# From string
python3 memory_manager.py update example_memory.md \
  --content "New updated content"

# From file
python3 memory_manager.py update example_memory.md \
  --content-file updated_notes.md

# From stdin
cat notes.txt | python3 memory_manager.py update example_memory.md --stdin
```

**Update Title**

```bash
python3 memory_manager.py update example_memory.md \
  --title "New Improved Title"
```

**Update Tags**

```bash
# Add tags (keeps existing ones)
python3 memory_manager.py update example_memory.md \
  --add-tag performance \
  --add-tag critical

# Remove specific tags
python3 memory_manager.py update example_memory.md \
  --remove-tag deprecated

# Replace all tags
python3 memory_manager.py update example_memory.md \
  --replace-tags heuristic \
  --replace-tags proven \
  --replace-tags production
```

---

## Tag System

### Tag Normalization

Tags are automatically normalized to **lowercase** for consistency. This prevents fragmentation like `Heuristic`, `heuristic`, and `HEURISTIC` being treated as different tags.

```bash
# These all become "heuristic"
python3 memory_manager.py create --title "Test" --content "..." \
  --tag Heuristic --tag HEURISTIC --tag heuristic
```

### Viewing All Tags

```bash
# List all tags with usage statistics
python3 memory_manager.py list-tags

# Example output:
# === ALL TAGS (8 unique) ===
#
#   heuristic           |   5 memories | long_term, short_term
#   debugging           |   3 memories | short_term
#   performance         |   2 memories | long_term
#   ...

# Include archived memories in count
python3 memory_manager.py list-tags --include-archived

# JSON output for scripting
python3 memory_manager.py list-tags --json
```

### Auto-Promotion Tags

During consolidation, memories with these tags are automatically promoted to long-term storage:

- `heuristic`
- `pattern`
- `proven`
- `decision`
- `insight`

You can customize this:

```bash
python3 memory_manager.py consolidate \
  --promote-tag critical \
  --promote-tag production-ready
```

---

## Sorting and Access Tracking

The system tracks three timestamps for each memory:

- **created**: When the memory was first created
- **last_updated**: When content/metadata was last modified
- **last_accessed**: When the memory was last read

### Sorting Options

```bash
# Sort by creation time (default)
python3 memory_manager.py list --sort-by created

# Sort by most recently updated
python3 memory_manager.py list --sort-by updated

# Sort by most recently accessed (useful for finding frequently referenced memories)
python3 memory_manager.py list --sort-by accessed
```

**Use Cases:**

- `--sort-by accessed`: Find your most-referenced memories
- `--sort-by updated`: See what's been recently modified
- `--sort-by created`: Chronological order (default)

---

## Automation and Scripting

### JSON Output

All commands support `--json` for machine-readable output:

```bash
# Get structured data
python3 memory_manager.py list --json | jq '.short_term[0].filename'
python3 memory_manager.py search --query "cache" --json | jq '.[].score'
python3 memory_manager.py list-tags --json | jq '.tags[] | select(.count > 5)'
```

### Integration Examples

**Automated Memory Creation from Logs**

```bash
#!/bin/bash
# Extract errors from logs and create memories

grep "ERROR" app.log | while read line; do
  python3 memory_manager.py create \
    --title "Error Log Entry" \
    --content "$line" \
    --type short_term \
    --tag error \
    --tag automated
done
```

**Weekly Consolidation Cron Job**

```bash
# Add to crontab (runs every Sunday at 2am)
0 2 * * 0 cd /path/to/whitemagic && python3 memory_manager.py consolidate
```

**Find Stale Memories**

```bash
# List memories not accessed in a while
python3 memory_manager.py list --json --sort-by accessed | \
  jq '.short_term | reverse | .[:5] | .[] | .filename'
```

### Exit Codes

Commands return standard exit codes:

- `0`: Success
- `1`: Operational error (memory not found, etc.)
- `2`: Usage error (invalid arguments)

---

## Limitations and Best Practices

### Known Limitations

1. **YAML Frontmatter Parsing**
   - Simple line-by-line parser
   - Does not support multi-line YAML values
   - Arrays must be JSON format: `tags: ["tag1", "tag2"]`
   - For complex frontmatter, consider using `--meta key=value`

2. **Token Counting**
   - Context limits use **character counts**, not actual model tokens
   - Actual token usage varies by model (GPT-4, Claude, etc.)
   - For precise control, manually inspect context output

3. **Scale Limitations**
   - Optimized for <1000 memories
   - Search is O(n) - scans all files
   - For larger scales, consider adding database backend

4. **Concurrent Access**
   - Not designed for multi-process concurrent writes
   - Use file locking if running multiple instances

### Best Practices

**1. Tag Hygiene**

```bash
# Regularly audit tags
python3 memory_manager.py list-tags

# Fix typos with update
python3 memory_manager.py update old_memory.md \
  --remove-tag "debuging" \
  --add-tag "debugging"
```

**2. Consolidation Strategy**

```bash
# Dry-run first
python3 memory_manager.py consolidate --dry-run

# Review what will be promoted
python3 memory_manager.py consolidate --dry-run --json | \
  jq '.source_files'

# Then commit
python3 memory_manager.py consolidate
```

**3. Archive Management**

```bash
# Periodically review archived memories
python3 memory_manager.py list --include-archived

# Permanently delete old archives if needed
for file in memory/archive/*.md; do
  python3 memory_manager.py delete "$(basename "$file")" --permanent
done
```

**4. Search Efficiency**

```bash
# Use --titles-only for faster searches when you don't need content
python3 memory_manager.py search --query "cache" --titles-only

# Combine tag filters for precision
python3 memory_manager.py search \
  --tag heuristic \
  --tag performance \
  --query "caching"
```

**5. Backup Strategy**

```bash
# The memory directory contains everything
tar -czf memory-backup-$(date +%Y%m%d).tar.gz memory/

# Or use git
git add memory/
git commit -m "Memory snapshot $(date)"
```

**6. Context Generation**

```bash
# Generate and save context for later use
python3 memory_manager.py context 1 --output context_snapshot.md

# Useful for:
# - Reviewing what AI sees
# - Debugging context issues
# - Creating manual prompt combinations
```

---

## Tips for AI Model Integration

### For Models with Tool Use

```python
# Python API example
from memory_manager import MemoryManager

mm = MemoryManager()

# During task execution
result = analyze_code(...)
if result.is_insight:
    mm.create_memory(
        title=f"Insight: {result.pattern_name}",
        content=result.description,
        memory_type="short_term",
        tags=["heuristic", result.domain]
    )

# Load context for next session
context = mm.generate_context_summary(tier=1)
```

### For Models Without Tool Access

```bash
# Pre-generate context as part of prompt
cat TIER_1_STANDARD.md > full_prompt.txt
python3 memory_manager.py context 1 >> full_prompt.txt

# Now feed full_prompt.txt to your model
```

### Access Pattern Analysis

```bash
# See which memories are most useful
python3 memory_manager.py list --sort-by accessed --json | \
  jq '.short_term[0:10] | .[] | {title, last_accessed, tags}'
```

This helps identify:

- Frequently referenced patterns (consider promoting)
- Rarely accessed memories (consider archiving)
- Popular tags (refine taxonomy)

---

## Troubleshooting

### Metadata Out of Sync

```bash
# If metadata.json becomes corrupted
# Rebuild from files (manual process):
python3 << EOF
from memory_manager import MemoryManager
mm = MemoryManager()
# System auto-prunes missing files on init
print(f"Loaded {len(mm._index)} memories")
EOF
```

### Duplicate Memories

```bash
# Find potential duplicates by title
python3 memory_manager.py list --json | \
  jq '.short_term | group_by(.title) | map(select(length > 1))'
```

### Archive Growing Too Large

```bash
# Review old archives
ls -lht memory/archive/ | head -20

# Permanently delete archives older than 90 days
find memory/archive/ -name "*.md" -mtime +90 -exec \
  python3 memory_manager.py delete {} --permanent \;
```

---

## Performance Optimization

For systems with many memories:

1. **Use --titles-only** for searches
2. **Tag strategically** - fewer, well-chosen tags
3. **Consolidate regularly** - keeps short-term lean
4. **Archive aggressively** - move to long-term sooner
5. **JSON + jq** - filter large result sets efficiently

```bash
# Example: Fast tag-based filtering
python3 memory_manager.py search --tag critical --titles-only --json | \
  jq -r '.[].entry.filename'
```
