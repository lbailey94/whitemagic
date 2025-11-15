# WhiteMagic Architecture

**Version**: 2.1.5  
**Last Updated**: November 14, 2025

---

## System Overview

### Core Principles

1. **Local-First**: Default to filesystem, cloud optional
2. **Model-Agnostic**: Works with any LLM
3. **Human-Readable**: Markdown + YAML frontmatter
4. **Type-Safe**: 100% Pydantic V2
5. **Multi-Interface**: CLI, API, SDK, MCP

### High-Level Architecture

```
┌────────────────────────────────────────────────┐
│            Client Layer                         │
├───────┬──────────┬──────────┬─────────────────┤
│  CLI  │   MCP    │   API    │   Python SDK    │
└───┬───┴────┬─────┴────┬─────┴────┬────────────┘
    │        │          │          │
    └────────┴──────────┴──────────┘
             │
    ┌────────▼────────┐
    │  MemoryManager  │
    │   (core.py)     │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Local Storage   │
    │  (markdown)     │
    └─────────────────┘
```

---

## Memory Architecture

### Tiered Storage

```
memory/
├── short_term/     # Working memory (days-weeks)
├── long_term/      # Permanent knowledge
└── archive/        # Historical data
```

### File Format

```yaml
---
id: mem_abc123
title: "API Design Notes"
type: short_term
status: active
tags: [api, architecture]
created_at: "2025-11-14T12:00:00Z"
---

# Content in markdown...
```

### Memory Lifecycle

```
CREATE → ACTIVE → [PROMOTED to long_term | ARCHIVED]
                 ↓
              RESTORED
```

---

## Core Components

### MemoryManager (whitemagic/core.py)

**Key Methods**:
- `create_memory()` - Create with validation
- `list_memories()` - List with filters
- `search_memories()` - Full-text search
- `get_context()` - Generate tiered context
- `consolidate_memories()` - Archive old, promote important

### API (whitemagic/api/)

**FastAPI application** with:
- Auth middleware (API keys)
- Rate limiting (Redis)
- Quota enforcement
- CORS controls
- Audit logging

**Key Endpoints**:
- `POST /api/v1/memories` - Create
- `GET /api/v1/memories` - List
- `POST /api/v1/search` - Search
- `POST /api/v1/context` - Context generation

### MCP Server (whitemagic-mcp/)

**TypeScript implementation** exposing:
- 7 tools (create, search, context, etc.)
- 4 resources (short_term, long_term, tags, stats)
- Works with Cursor/Windsurf/Claude Desktop

---

## Security Model

### Layers

1. HTTPS/TLS
2. API key authentication
3. Rate limiting (per-user)
4. Quota enforcement (plan-based)
5. Input validation (Pydantic)
6. CORS (controlled origins)
7. Audit logging

### Guardrails

- **No CORS wildcards** in production (CI enforced)
- **Exec API disabled** by default
- **Security guards** run in pre-commit hooks

---

## Deployment

### Local Dev
```bash
uvicorn whitemagic.api.app:app --reload
```

### Production (Railway + Vercel)

- **Backend**: Railway (FastAPI + PostgreSQL + Redis)
- **Frontend**: Vercel (static dashboard)
- **Nixpacks + Procfile** for Railway deployment

---

## Future Enhancements

1. **Semantic Search** - pgvector + embeddings
2. **Terminal Tool** - Safe command execution
3. **Workspaces** - Team collaboration
4. **Nested Learning** - Multi-speed memory tiers

---

See [VISION.md](VISION.md) for strategic philosophy.
