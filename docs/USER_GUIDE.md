# WhiteMagic User Guide

**Complete guide from beginner to advanced usage**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Level 1: CLI Basics](#level-1-cli-basics-beginner)
4. [Level 2: MCP Integration](#level-2-mcp-integration-intermediate)
5. [Level 3: API Usage](#level-3-api-usage-intermediate)
6. [Level 4: Python SDK](#level-4-python-sdk-advanced)
7. [Level 5: Production Deployment](#level-5-production-deployment-advanced)
8. [Common Workflows](#common-workflows)
9. [Best Practices](#best-practices)

---

## Introduction

WhiteMagic is a tiered memory management system for AI agents. It provides:
- **Short-term memory**: Recent, active information
- **Long-term memory**: Important, permanent knowledge
- **Archive**: Historical data for reference

### Who Is This For?

- **Level 1 (Beginner)**: Use CLI for quick memory management
- **Level 2 (Intermediate)**: Connect to IDEs via MCP
- **Level 3 (Intermediate)**: Use REST API for integrations
- **Level 4 (Advanced)**: Build Python applications
- **Level 5 (Advanced)**: Deploy production systems

---

## Installation

### Quick Install
```bash
pip install whitemagic==2.1.3
```

### With API Support
```bash
pip install whitemagic[api]==2.1.3
```

### Development Install
```bash
git clone https://github.com/lbailey94/whitemagic.git
cd whitemagic
pip install -e ".[api,dev]"
```

### Verify Installation
```bash
whitemagic --version
# Expected: WhiteMagic CLI v2.1.3

python -c "from whitemagic import VERSION; print(VERSION)"
# Expected: 2.1.3
```

---

## Level 1: CLI Basics (Beginner)

**Time to Learn**: 10 minutes  
**Prerequisites**: Python 3.10+

### Creating Your First Memory

```bash
# Create a short-term memory
whitemagic create "My First Memory" --content "Hello WhiteMagic!" --type short_term

# Expected output:
# ✓ Created: 20251112_120000_my_first_memory.md
```

### Listing Memories

```bash
# List all memories
whitemagic list

# List only short-term
whitemagic list --type short_term

# List only long-term
whitemagic list --type long_term
```

### Viewing a Memory

```bash
# View specific memory
whitemagic get 20251112_120000_my_first_memory.md

# Expected output shows title, content, tags, timestamps
```

### Searching Memories

```bash
# Search by content
whitemagic search "Python"

# Search with tags
whitemagic search --tags "important,work"

# Search in specific type
whitemagic search "meeting" --type short_term
```

### Updating Memories

```bash
# Update content
whitemagic update 20251112_120000_my_first_memory.md \
  --content "Updated content here"

# Add tags
whitemagic update 20251112_120000_my_first_memory.md \
  --add-tags "important,reviewed"

# Update title
whitemagic update 20251112_120000_my_first_memory.md \
  --title "New Title"
```

### Deleting Memories

```bash
# Delete a memory
whitemagic delete 20251112_120000_my_first_memory.md

# Confirm deletion when prompted
```

### Getting Memory Stats

```bash
whitemagic stats

# Expected output:
# Short-term: 5 memories
# Long-term: 2 memories
# Total: 7 memories
# Tags: 12 unique tags
```

### CLI Quick Reference

| Command | Purpose |
|---------|---------|
| `create TITLE` | Create new memory |
| `list` | List all memories |
| `get FILENAME` | View memory details |
| `search QUERY` | Search memories |
| `update FILENAME` | Update memory |
| `delete FILENAME` | Delete memory |
| `stats` | Show statistics |
| `tags` | List all tags |

---

## Level 2: MCP Integration (Intermediate)

**Time to Learn**: 15 minutes  
**Prerequisites**: Windsurf/Cursor/Claude Desktop

### Setup MCP Server

See [Quick Setup MCP Guide](guides/QUICK_SETUP_MCP.md) for detailed instructions.

**Quick version**:
```bash
npm install -g whitemagic-mcp
```

Then add to your IDE settings with `WM_BASE_PATH` configured.

### Using WhiteMagic in Your IDE

Once connected, ask your AI assistant natural language questions:

#### Creating Memories
```
"Create a short-term memory titled 'Project Requirements' with the following content: [paste requirements]"
```

#### Searching and Retrieving
```
"Search my memories for anything about Python testing"
"Show me all memories tagged with 'urgent'"
"Get me the memory about the API design"
```

#### Context Generation
```
"Give me tier 1 context about this project"
"Generate full context for my current work"
```

#### Memory Management
```
"Show me my memory statistics"
"List all my tags"
"Update the memory about X with this new information"
```

### MCP Tools Available

1. **create_memory** - Create new memories
2. **search_memories** - Search by query and tags
3. **get_context** - Generate context packages
4. **update_memory** - Update existing memories
5. **delete_memory** - Remove memories
6. **get_stats** - Get memory statistics
7. **consolidate** - Archive old memories

### MCP Resources Available

1. **memories** - List all memories
2. **short-term** - Short-term memories only
3. **long-term** - Long-term memories only
4. **tags** - All available tags

---

## Level 3: API Usage (Intermediate)

**Time to Learn**: 20 minutes  
**Prerequisites**: Python 3.10+, Redis (optional)

### Starting the API Server

```bash
# Install with API support
pip install whitemagic[api]

# Start server
uvicorn whitemagic.api.app:app --reload

# Server runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Environment Configuration

Create `.env`:
```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./whitemagic.db

# Redis (optional, for rate limiting)
REDIS_URL=redis://localhost:6379

# Security
WM_ENABLE_EXEC_API=false

# Logging
WM_LOG_LEVEL=INFO
```

### Authentication

1. **Create User** (via CLI or direct DB):
```bash
# Coming soon - user creation via CLI
```

2. **Get API Key** (stored in database)

3. **Use in requests**:
```bash
curl http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer wm_prod_YOUR_KEY_HERE"
```

### API Examples

#### Create Memory
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Test Memory",
    "content": "Created via API",
    "type": "short_term",
    "tags": ["api", "test"]
  }'
```

#### List Memories
```bash
curl http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Search Memories
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python",
    "type": "short_term"
  }'
```

#### Get Context
```bash
curl -X POST http://localhost:8000/api/v1/context \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tier": 1}'
```

### API Endpoints Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check (public) |
| GET | `/version` | Version info (public) |
| POST | `/api/v1/memories` | Create memory |
| GET | `/api/v1/memories` | List memories |
| GET | `/api/v1/memories/{id}` | Get memory |
| PUT | `/api/v1/memories/{id}` | Update memory |
| DELETE | `/api/v1/memories/{id}` | Delete memory |
| POST | `/api/v1/search` | Search memories |
| POST | `/api/v1/context` | Get context |
| GET | `/api/v1/stats` | Get statistics |
| GET | `/api/v1/tags` | List tags |

Full API documentation: http://localhost:8000/docs

---

## Level 4: Python SDK (Advanced)

**Time to Learn**: 30 minutes  
**Prerequisites**: Python programming experience

### Basic Usage

```python
from whitemagic import MemoryManager

# Initialize
manager = MemoryManager(base_path="./my_memories")

# Create memory
result = manager.create_memory(
    title="SDK Example",
    content="Created via Python SDK",
    memory_type="short_term",
    tags=["sdk", "example"]
)
print(f"Created: {result['filename']}")

# List memories
memories = manager.list_memories()
for memory in memories:
    print(f"- {memory['title']}")

# Search
results = manager.search_memories(query="Python", memory_type="short_term")
for result in results:
    print(f"Found: {result['title']} (score: {result['score']})")

# Get specific memory
memory = manager.get_memory(result['filename'])
print(memory['content'])

# Update memory
manager.update_memory(
    filename=result['filename'],
    content="Updated content",
    add_tags=["updated"]
)

# Delete memory
manager.delete_memory(result['filename'])
```

### Advanced: Context Generation

```python
from whitemagic import MemoryManager

manager = MemoryManager()

# Generate tier 1 context (balanced)
context = manager.get_context(tier=1)
print(context['context'])

# Generate full context
full_context = manager.get_context(tier=2)
print(f"Included {full_context['memories_included']} memories")
```

### Advanced: Memory Consolidation

```python
from whitemagic import MemoryManager
from datetime import datetime, timedelta

manager = MemoryManager()

# Consolidate memories older than 30 days (dry run)
cutoff = datetime.now() - timedelta(days=30)
result = manager.consolidate_memories(
    older_than=cutoff,
    dry_run=True
)
print(f"Would archive {result['archived_count']} memories")

# Actually consolidate
result = manager.consolidate_memories(
    older_than=cutoff,
    dry_run=False
)
print(f"Archived {result['archived_count']} memories")
```

### Advanced: Async API Client

```python
import asyncio
from whitemagic.api.client import WhiteMagicClient

async def main():
    client = WhiteMagicClient(
        base_url="http://localhost:8000",
        api_key="YOUR_API_KEY"
    )
    
    # Create memory
    memory = await client.create_memory(
        title="Async Example",
        content="Created asynchronously",
        memory_type="short_term"
    )
    
    # Search
    results = await client.search_memories(query="async")
    
    await client.close()

asyncio.run(main())
```

---

## Level 5: Production Deployment (Advanced)

**Time to Learn**: 1 hour  
**Prerequisites**: Docker, cloud platform experience

### Docker Deployment

```bash
# Build image
docker build -t whitemagic:2.1.3 .

# Run with environment
docker run -d \
  --name whitemagic-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/whitemagic \
  -e REDIS_URL=redis://redis:6379 \
  -e WM_LOG_LEVEL=INFO \
  whitemagic:2.1.3
```

### Docker Compose Setup

```yaml
version: '3.8'

services:
  api:
    image: whitemagic:2.1.3
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/whitemagic
      REDIS_URL: redis://redis:6379
      ENABLE_RATE_LIMITING: "true"
      WM_LOG_LEVEL: INFO
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: whitemagic
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Production Checklist

- [ ] Set strong `DATABASE_URL` with PostgreSQL
- [ ] Configure `REDIS_URL` for rate limiting
- [ ] Set `WM_LOG_LEVEL=WARNING` or `ERROR`
- [ ] Ensure `WM_ENABLE_EXEC_API=false`
- [ ] Set up SSL/TLS termination
- [ ] Configure CORS properly
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure backups
- [ ] Set rate limits appropriately
- [ ] Test failover scenarios

See [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) for complete instructions.

---

## Common Workflows

### Workflow 1: Daily Note-Taking

```bash
# Morning: Create daily note
whitemagic create "Daily $(date +%Y-%m-%d)" \
  --content "Today's goals:..." \
  --tags "daily,todo"

# Throughout day: Update
whitemagic search "Daily $(date +%Y-%m-%d)" --exact
# Get filename, then:
whitemagic update FILENAME --content "Updated progress..."

# Evening: Archive old notes
whitemagic consolidate --dry-run
```

### Workflow 2: Project Documentation

```bash
# Create project memory
whitemagic create "Project XYZ" \
  --content "Project goals, requirements..." \
  --type long_term \
  --tags "project,xyz,important"

# Add meeting notes
whitemagic create "XYZ Meeting 2024-11-12" \
  --content "Discussed..." \
  --tags "project,xyz,meeting"

# Search project info
whitemagic search "XYZ" --tags "project"
```

### Workflow 3: Research Organization

```python
from whitemagic import MemoryManager

manager = MemoryManager()

# Collect research papers
papers = [
    {"title": "Paper 1", "content": "Summary...", "tags": ["research", "ml"]},
    {"title": "Paper 2", "content": "Summary...", "tags": ["research", "nlp"]},
]

for paper in papers:
    manager.create_memory(
        title=paper["title"],
        content=paper["content"],
        memory_type="long_term",
        tags=paper["tags"]
    )

# Generate research context
context = manager.get_context(tier=2)
print(context['context'])
```

---

## Best Practices

### Memory Organization

1. **Use Descriptive Titles**
   - ✅ Good: "Project Alpha - API Design Meeting Notes"
   - ❌ Bad: "Notes"

2. **Tag Consistently**
   - Use lowercase tags
   - Be specific: `python-api` not just `api`
   - Include category tags: `project`, `personal`, `work`

3. **Choose Appropriate Type**
   - **Short-term**: Daily notes, temporary info, work in progress
   - **Long-term**: Important decisions, documentation, permanent knowledge
   - **Archive**: Historical data, completed projects

4. **Keep Content Focused**
   - One topic per memory
   - Include relevant context
   - Add timestamps for time-sensitive info

### Performance Tips

1. **Batch Operations**
   ```python
   # Good: Batch create
   for item in items:
       manager.create_memory(...)
   
   # Better: Use async API for high volume
   ```

2. **Use Specific Searches**
   - Include tags to narrow results
   - Specify memory type
   - Use exact phrases when possible

3. **Regular Consolidation**
   - Archive old memories monthly
   - Keep short-term lean
   - Move important items to long-term

### Security Best Practices

1. **Protect API Keys**
   - Never commit to git
   - Use environment variables
   - Rotate regularly

2. **Validate Input**
   - Sanitize user-provided content
   - Check file paths
   - Validate memory types

3. **Monitor Access**
   - Review API logs
   - Track rate limit hits
   - Monitor failed auth attempts

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for complete guide.

**Quick fixes**:
- Memory not found → Check filename spelling
- Search returns nothing → Try broader query
- API auth fails → Verify API key format
- Server won't start → Check port 8000 availability

---

## Next Steps

- **Cheat Sheet**: [CHEATSHEET.md](CHEATSHEET.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **API Reference**: http://localhost:8000/docs
- **MCP Setup**: [guides/QUICK_SETUP_MCP.md](guides/QUICK_SETUP_MCP.md)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Support

- 📖 **Documentation**: [docs/INDEX.md](INDEX.md)
- 🐛 **Issues**: https://github.com/lbailey94/whitemagic/issues
- 💬 **Discussions**: https://github.com/lbailey94/whitemagic/discussions
- 🔒 **Security**: See [SECURITY.md](../SECURITY.md)

---

**Last Updated**: November 12, 2025  
**Version**: 2.1.3  
**Status**: Production Ready
