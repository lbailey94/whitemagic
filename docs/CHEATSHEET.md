# WhiteMagic Cheat Sheet

**Quick reference for common operations**

---

## Installation

```bash
# Basic install
pip install whitemagic==2.1.3

# With API support
pip install whitemagic[api]==2.1.3

# Development install
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic && pip install -e ".[api,dev]"

# MCP server
npm install -g whitemagic-mcp
```

---

## CLI Commands

### Create
```bash
# Short-term memory
whitemagic create "Title" --content "Content" --type short_term

# Long-term memory with tags
whitemagic create "Title" --content "Content" --type long_term --tags "tag1,tag2"

# From file
whitemagic create "Title" --file ./notes.txt --type short_term
```

### List
```bash
# All memories
whitemagic list

# By type
whitemagic list --type short_term
whitemagic list --type long_term

# With limit
whitemagic list --limit 10
```

### Search
```bash
# Basic search
whitemagic search "query"

# With tags
whitemagic search "query" --tags "tag1,tag2"

# Specific type
whitemagic search "query" --type short_term

# Exact match
whitemagic search "exact phrase" --exact
```

### Get
```bash
# View memory
whitemagic get FILENAME.md

# Export to file
whitemagic get FILENAME.md > output.txt
```

### Update
```bash
# Update content
whitemagic update FILENAME.md --content "New content"

# Update title
whitemagic update FILENAME.md --title "New Title"

# Add tags
whitemagic update FILENAME.md --add-tags "tag1,tag2"

# Remove tags
whitemagic update FILENAME.md --remove-tags "old_tag"

# Replace all tags
whitemagic update FILENAME.md --tags "new1,new2"
```

### Delete
```bash
# Delete memory
whitemagic delete FILENAME.md

# Force delete (no confirmation)
whitemagic delete FILENAME.md --force
```

### Stats & Info
```bash
# Statistics
whitemagic stats

# List all tags
whitemagic tags

# Version info
whitemagic --version
```

### Backup & Restore
```bash
# Create backup
whitemagic backup

# Create compressed backup
whitemagic backup --compress

# List backups
whitemagic list-backups

# Verify backup
whitemagic verify-backup backup_file.tar.gz

# Restore backup
whitemagic restore-backup backup_file.tar.gz

# Restore with safety backup
whitemagic restore-backup backup_file.tar.gz --create-backup
```

### Consolidation
```bash
# Dry run (preview)
whitemagic consolidate --dry-run

# Consolidate memories older than 30 days
whitemagic consolidate --older-than 30

# Consolidate with confirmation
whitemagic consolidate --older-than 30 --confirm
```

---

## Python SDK

### Basic Usage
```python
from whitemagic import MemoryManager

# Initialize
manager = MemoryManager(base_path="./memory")

# Create
result = manager.create_memory(
    title="Title",
    content="Content",
    memory_type="short_term",
    tags=["tag1", "tag2"]
)

# List
memories = manager.list_memories(memory_type="short_term")

# Search
results = manager.search_memories(
    query="search term",
    memory_type="short_term",
    tags=["tag1"]
)

# Get
memory = manager.get_memory("filename.md")

# Update
manager.update_memory(
    filename="filename.md",
    content="New content",
    add_tags=["new_tag"]
)

# Delete
manager.delete_memory("filename.md")

# Stats
stats = manager.get_stats()

# Context
context = manager.get_context(tier=1)  # 0=minimal, 1=balanced, 2=full
```

### Context Generation
```python
# Tier 0: Minimal (summary only)
context = manager.get_context(tier=0)

# Tier 1: Balanced (recent + important)
context = manager.get_context(tier=1)

# Tier 2: Full (all memories)
context = manager.get_context(tier=2)

print(context['context'])  # Formatted context
print(context['memories_included'])  # Count
```

### Consolidation
```python
from datetime import datetime, timedelta

# Dry run
result = manager.consolidate_memories(
    older_than=datetime.now() - timedelta(days=30),
    dry_run=True
)

# Actual consolidation
result = manager.consolidate_memories(
    older_than=datetime.now() - timedelta(days=30),
    dry_run=False
)

print(f"Archived: {result['archived_count']}")
print(f"Promoted: {result['promoted_count']}")
```

---

## API Endpoints

### Health & Version (Public)
```bash
# Health check
curl http://localhost:8000/health

# Version info
curl http://localhost:8000/version

# Ready check
curl http://localhost:8000/ready
```

### Authentication
```bash
# All API requests need Authorization header
-H "Authorization: Bearer wm_prod_YOUR_API_KEY"
```

### Memories
```bash
# Create
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Title","content":"Content","type":"short_term","tags":["tag1"]}'

# List
curl http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer YOUR_KEY"

# Get
curl http://localhost:8000/api/v1/memories/FILENAME.md \
  -H "Authorization: Bearer YOUR_KEY"

# Update
curl -X PUT http://localhost:8000/api/v1/memories/FILENAME.md \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content":"Updated","add_tags":["new"]}'

# Delete
curl -X DELETE http://localhost:8000/api/v1/memories/FILENAME.md \
  -H "Authorization: Bearer YOUR_KEY"
```

### Search
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"search term","type":"short_term","tags":["tag1"]}'
```

### Context
```bash
curl -X POST http://localhost:8000/api/v1/context \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tier":1}'
```

### Stats & Tags
```bash
# Stats
curl http://localhost:8000/api/v1/stats \
  -H "Authorization: Bearer YOUR_KEY"

# Tags
curl http://localhost:8000/api/v1/tags \
  -H "Authorization: Bearer YOUR_KEY"
```

### Consolidation
```bash
curl -X POST http://localhost:8000/api/v1/consolidate \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true}'
```

---

## MCP Integration

### Natural Language Commands

```
"Create a memory titled 'X' with content 'Y'"
"List all my memories"
"Search my memories for 'Python'"
"Show memories tagged with 'important'"
"Give me tier 1 context"
"Update memory X with new content"
"Delete memory about Y"
"Show memory statistics"
```

### MCP Tools (7)
1. `create_memory` - Create new memory
2. `search_memories` - Search by query/tags
3. `get_context` - Generate context (tier 0-2)
4. `update_memory` - Update existing memory
5. `delete_memory` - Remove memory
6. `get_stats` - Get statistics
7. `consolidate` - Archive old memories

### MCP Resources (4)
1. `memories` - All memories
2. `short-term` - Short-term only
3. `long-term` - Long-term only
4. `tags` - All tags

---

## Environment Variables

### API Server
```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./whitemagic.db
# or
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (optional, for rate limiting)
REDIS_URL=redis://localhost:6379

# Rate limiting
ENABLE_RATE_LIMITING=true

# Security
WM_ENABLE_EXEC_API=false  # KEEP DISABLED

# Logging
WM_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Whop integration (optional)
WHOP_API_KEY=your_key
WHOP_WEBHOOK_SECRET=your_secret
```

### MCP Server
```bash
# Required
WM_BASE_PATH=/path/to/memory/folder

# Optional (for API integration)
WM_API_URL=http://localhost:8000
WM_API_KEY=your_api_key
```

---

## File Structure

```
memory/
├── metadata.json          # Memory catalog
├── short_term/           # Recent memories
│   └── YYYYMMDD_HHMMSS_title.md
├── long_term/            # Important memories
│   └── YYYYMMDD_HHMMSS_title.md
└── archive/              # Archived memories
    └── YYYYMMDD_HHMMSS_title.md
```

### Memory File Format
```markdown
---
title: "Memory Title"
type: "short_term"
tags: ["tag1", "tag2"]
created: "2025-11-12T12:00:00"
---

Memory content goes here...
Can be multiple paragraphs.
```

---

## Common Patterns

### Daily Notes
```bash
whitemagic create "Daily $(date +%Y-%m-%d)" \
  --content "Today's goals..." \
  --tags "daily,notes"
```

### Project Memory
```bash
whitemagic create "Project X" \
  --content "Requirements..." \
  --type long_term \
  --tags "project,important"
```

### Search & Update
```bash
# Find memory
whitemagic search "project X" --exact

# Update it
whitemagic update FILENAME.md --content "Updated info"
```

### Batch Create
```python
from whitemagic import MemoryManager
manager = MemoryManager()

items = [
    {"title": "Item 1", "content": "..."},
    {"title": "Item 2", "content": "..."},
]

for item in items:
    manager.create_memory(
        title=item["title"],
        content=item["content"],
        memory_type="short_term"
    )
```

---

## Keyboard Shortcuts (IDE)

### Windsurf/Cursor
- `Cmd+,` / `Ctrl+,` - Open settings
- `Cmd+Shift+P` / `Ctrl+Shift+P` - Command palette
- Search "MCP" - Find MCP settings

### Claude Desktop
- No shortcuts - Edit config file directly

---

## Quick Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| Command not found | `export PATH="$HOME/.local/bin:$PATH"` |
| Import error | `pip install --force-reinstall whitemagic` |
| MCP won't connect | Check `WM_BASE_PATH` exists |
| API auth fails | Verify `Authorization: Bearer YOUR_KEY` |
| Rate limited | Wait or disable: `ENABLE_RATE_LIMITING=false` |
| Port in use | `lsof -i :8000` then kill or use different port |
| Database locked | Stop all servers, restart one |
| Slow search | `whitemagic consolidate` to reduce size |

---

## Performance Tips

1. **Use specific searches**: Include tags and type
2. **Consolidate regularly**: Archive old memories monthly
3. **Limit results**: Use `--limit` flag
4. **Use PostgreSQL**: For production/large datasets
5. **Enable Redis**: For rate limiting and caching

---

## Security Checklist

- [ ] `WM_ENABLE_EXEC_API=false` in production
- [ ] Strong API keys (use `wm_prod_` prefix)
- [ ] `REDIS_URL` set for rate limiting
- [ ] HTTPS/TLS in production
- [ ] Regular security updates
- [ ] Monitor API logs
- [ ] Backup regularly

---

## Useful Links

- 📖 **Full Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- 🔧 **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 🚀 **MCP Setup**: [guides/QUICK_SETUP_MCP.md](guides/QUICK_SETUP_MCP.md)
- 📚 **API Docs**: http://localhost:8000/docs
- 🐛 **Issues**: https://github.com/lbailey94/whitemagic/issues
- 💬 **Discussions**: https://github.com/lbailey94/whitemagic/discussions

---

**Version**: 2.1.3  
**Last Updated**: November 12, 2025

**Print this page for quick reference!**
