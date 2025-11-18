# WhiteMagic Automation System

**Version**: v2.2.8+  
**Status**: Production Ready  
**Date**: November 18, 2025

---

## Overview

WhiteMagic features a comprehensive automation system that continuously maintains and optimizes your memory system. The automation runs automatically based on triggers, ensuring your knowledge base stays organized without manual intervention.

## Features

### 1. Automated Consolidation

Automatically consolidates short-term memories into long-term storage based on intelligent rules.

**What Gets Consolidated:**
- **Archived**: Memories older than 7 days
- **Merged**: Duplicate memories with >85% similarity
- **Promoted**: Important memories moved to long-term
- **Cleaned**: Old scratchpads (>24 hours)

### 2. Auto-Promotion Logic

Memories are automatically promoted to long-term based on:

#### Tag-Based Promotion
- `#critical` - Critical information
- `#important` - Important references
- `#permanent` - Permanent knowledge
- `#reference` - Reference materials
- `#keep` - Explicitly marked to keep

#### Age-Based Promotion
- Memories older than **30 days** are promoted to long-term

#### Size-Based Promotion
- Comprehensive documents with **>1000 words** are promoted

#### Title-Based Promotion
Keywords in titles trigger promotion:
- "comprehensive"
- "guide"
- "reference"
- "complete"
- "roadmap"

### 3. Scratchpad Cleanup

Scratchpads older than 24 hours are automatically:
1. Converted to permanent memories
2. Deleted from working memory
3. Organized into appropriate categories

### 4. Parallel Processing

Consolidation uses parallel processing (16 threads by default) for:
- Archival operations (>3 memories)
- Duplicate detection
- Promotion analysis

**Performance**: 2-5x faster than sequential processing

---

## Triggers

Consolidation runs automatically when:

### 1. Session End
Consolidates when a session completes (if >20 short-term memories)

### 2. Pre-commit Hook
Consolidates before Git commits (if >35 memories)

### 3. Version Release
Always consolidates on version bumps

### 4. Memory Count Threshold
Triggers at 40+ short-term memories

### 5. Manual Trigger
```bash
whitemagic consolidate [--no-dry-run]
```

---

## Configuration

### Basic Configuration

Create `~/.whitemagic/config.json`:

```json
{
  "consolidation": {
    "max_short_term": 40,
    "max_age_days": 7,
    "similarity_threshold": 0.85,
    "enable_parallel": true,
    "worker_count": 16
  },
  "scratchpad": {
    "cleanup_hours": 24
  },
  "triggers": {
    "session_end": true,
    "pre_commit": true,
    "version_release": true
  }
}
```

### Configuration Options

#### Consolidation Settings

| Option | Default | Description |
|--------|---------|-------------|
| `max_short_term` | 40 | Trigger consolidation at this count |
| `max_age_days` | 7 | Archive memories older than this |
| `similarity_threshold` | 0.85 | Merge threshold for duplicates |
| `enable_parallel` | true | Use parallel processing |
| `worker_count` | 16 | Thread pool size (Tier 1) |

#### Scratchpad Settings

| Option | Default | Description |
|--------|---------|-------------|
| `cleanup_hours` | 24 | Auto-cleanup after this many hours |

#### Trigger Settings

| Option | Default | Description |
|--------|---------|-------------|
| `session_end` | true | Consolidate on session end |
| `pre_commit` | true | Consolidate before Git commits |
| `version_release` | true | Consolidate on version bumps |

---

## CLI Commands

### Check Consolidation Status
```bash
whitemagic consolidate
```

Output:
```
✓ No consolidation needed
  Short-term memories: 7/40
```

### Dry Run (Preview)
```bash
whitemagic consolidate
```

Shows what would be consolidated without executing.

### Execute Consolidation
```bash
whitemagic consolidate --no-dry-run
```

### Force Consolidation
```bash
whitemagic consolidate --force --no-dry-run
```

---

## Pre-commit Hook

Installed at `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# WhiteMagic Pre-commit Hook

# Check memory count
MEMORY_COUNT=$(ls -1 memory/short_term/*.md 2>/dev/null | wc -l)

if [ "$MEMORY_COUNT" -gt 35 ]; then
    echo "🔄 Pre-commit consolidation (${MEMORY_COUNT} memories)..."
    whitemagic consolidate --no-dry-run --quiet
fi

# Version consistency check
CURRENT_VERSION=$(cat VERSION)
whitemagic version "$CURRENT_VERSION" --check

exit 0
```

**What It Does:**
1. Counts short-term memories
2. Consolidates if >35 memories
3. Checks version consistency
4. Allows commit to proceed

---

## Examples

### Example 1: Daily Usage

```bash
# Morning: Start work
whitemagic session start "Feature Development"

# Throughout day: AI creates memories
# (WhiteMagic automatically manages them)

# End of day: Close session
whitemagic session end
# → Auto-consolidation runs
# → Old memories archived
# → Important items promoted
# → Scratchpads cleaned
```

### Example 2: Manual Consolidation

```bash
# Check status
whitemagic consolidate

# Output:
📊 Consolidation Analysis:
  Short-term count: 42/40
  • Count exceeded threshold (42 > 40)
  • 3 old memories found
  • 2 duplicate pairs detected

# Preview changes
🔍 DRY RUN (use --no-dry-run to execute)

Would be Results:
  📦 Archived: 3 memories
     - 20251110_meeting_notes.md (9 days old)
     - 20251109_temp_draft.md (10 days old)
     - 20251108_scratchpad.md (11 days old)
  
  🔗 Merged: 2 memory pairs
     - setup_guide_v1.md + setup_guide_v2.md (92.3%)
  
  ⬆️  Promoted: 1 memories to long-term
     - comprehensive_roadmap.md (comprehensive_doc, size_1247w)

# Execute
whitemagic consolidate --no-dry-run

# Output:
✅ Consolidation complete!
```

### Example 3: Customized Config

```python
from whitemagic.automation.consolidation import ConsolidationEngine
from whitemagic.core import MemoryManager

# Custom configuration
config = {
    "max_short_term": 30,      # More aggressive
    "max_age_days": 5,          # Shorter retention
    "similarity_threshold": 0.90,  # Stricter merging
    "worker_count": 32          # More parallel processing
}

manager = MemoryManager()
engine = ConsolidationEngine(manager, config=config)

# Run with custom settings
results = engine.auto_consolidate(dry_run=False)
```

---

## Monitoring

### Check Consolidation Metrics

```bash
whitemagic stats --consolidation
```

Output:
```
📊 Consolidation Metrics (Last 7 Days)

Automated Runs: 12
  ├─ Session end: 8
  ├─ Pre-commit: 3
  └─ Manual: 1

Actions Taken:
  ├─ Archived: 24 memories
  ├─ Merged: 8 pairs
  ├─ Promoted: 12 memories
  └─ Scratchpads: 5 cleaned

Performance:
  ├─ Avg duration: 2.3s
  ├─ Parallel speedup: 3.2x
  └─ Success rate: 100%
```

### View Consolidation Logs

```bash
tail -f ~/.whitemagic/logs/consolidation.log
```

---

## Troubleshooting

### Issue: Consolidation Not Running

**Check:**
1. Trigger settings: `cat ~/.whitemagic/config.json`
2. Memory count: `whitemagic stats`
3. Logs: `tail ~/.whitemagic/logs/consolidation.log`

**Solution:**
```bash
# Manual trigger
whitemagic consolidate --no-dry-run

# Force trigger
whitemagic consolidate --force --no-dry-run
```

### Issue: Too Aggressive Consolidation

**Adjust thresholds:**
```json
{
  "consolidation": {
    "max_short_term": 60,    // Increase trigger
    "max_age_days": 14       // Keep memories longer
  }
}
```

### Issue: Slow Consolidation

**Enable/increase parallelism:**
```json
{
  "consolidation": {
    "enable_parallel": true,
    "worker_count": 32      // More threads
  }
}
```

---

## Best Practices

### 1. Regular Monitoring
- Check stats weekly: `whitemagic stats`
- Review archived memories monthly
- Adjust thresholds based on usage

### 2. Tag Important Memories
Use promotion tags:
```bash
whitemagic tag "memory_file.md" --add important
whitemagic tag "reference_doc.md" --add permanent
```

### 3. Session Management
Always use sessions:
```bash
whitemagic session start "Task Name"
# ... work ...
whitemagic session end
# → Auto-consolidation runs
```

### 4. Pre-commit Hook
Keep the hook enabled for continuous maintenance.

### 5. Backup Before Major Changes
```bash
whitemagic backup create
whitemagic consolidate --no-dry-run
```

---

## API Usage

### Python API

```python
from whitemagic.automation.consolidation import ConsolidationEngine
from whitemagic.core import MemoryManager

# Initialize
manager = MemoryManager()
engine = ConsolidationEngine(manager)

# Check if needed
check = engine.should_consolidate()
if check["should_consolidate"]:
    print(f"Reasons: {check['reasons']}")
    
    # Run consolidation
    results = engine.auto_consolidate(dry_run=False)
    
    print(f"Archived: {len(results['archived'])}")
    print(f"Promoted: {len(results['promoted'])}")
    print(f"Merged: {len(results['merged'])}")
    print(f"Scratchpads: {len(results['scratchpads_cleaned'])}")
```

### Scratchpad Cleanup

```python
from whitemagic.scratchpad.manager import ScratchpadManager
import asyncio

async def cleanup():
    manager = ScratchpadManager()
    results = await manager.cleanup_old(hours=24, dry_run=False)
    print(f"Cleaned {len(results['cleaned'])} scratchpads")

asyncio.run(cleanup())
```

---

## Architecture

### Components

```
whitemagic/automation/
├── consolidation.py      # Main engine
├── triggers.py           # Trigger system
└── __init__.py

whitemagic/scratchpad/
├── manager.py            # Scratchpad management
└── __init__.py

.git/hooks/
└── pre-commit            # Git integration
```

### Flow Diagram

```
Trigger Detected
      ↓
Should Consolidate?
      ↓
   [YES]
      ↓
Parallel Processing:
  ├─ Archive old (7d+)
  ├─ Merge duplicates (85%+)
  ├─ Promote important
  └─ Clean scratchpads
      ↓
Update Stats
      ↓
   [DONE]
```

---

## Version History

### v2.2.8 (November 18, 2025)
- ✨ Enhanced auto-promotion (4 rules)
- ✨ Scratchpad auto-cleanup
- ⚡ Parallel consolidation (16 threads)
- 📝 Comprehensive documentation

### v2.2.7 (Previous)
- ✅ Basic consolidation
- ✅ Simple triggers
- ✅ Manual execution

---

## Related Documentation

- [Memory Management Guide](MEMORY_MANAGEMENT.md)
- [Session Guide](SESSIONS.md)
- [Configuration Reference](CONFIGURATION.md)
- [API Documentation](API.md)

---

**Questions?** Check [FAQ](../FAQ.md) or [GitHub Issues](https://github.com/lbailey94/whitemagic/issues)
