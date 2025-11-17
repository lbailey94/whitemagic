# WhiteMagic Architecture

**Version**: 2.2.7  
**Last Updated**: November 16, 2025

---

## System Overview

### Core Principles

1. **Local-First**: Default to filesystem, cloud optional
2. **Model-Agnostic**: Works with any LLM
3. **Human-Readable**: Markdown + YAML frontmatter
4. **Type-Safe**: 100% Pydantic V2
5. **Multi-Interface**: CLI, API, SDK, MCP
6. **Parallel-Ready**: Built-in I Ching threading tiers (8→256) with scratchpads + sessions

### High-Level Architecture

```text
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
    │ Parallel Pools  │  ◄─ NEW (whitemagic/parallel/*)
    │ Sessions/Scratch│
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

```text
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

```text
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
- `get_parallel_status()` *(v2.2.9 planned)* - Report threading tiers + queues

### Parallel Infrastructure (whitemagic/parallel/)

**Components**:

- `threading_tiers.py` - I Ching tier definitions (8,16,32,64,128,256 threads)
- `pools.py`/`scheduler.py` - Adaptive pools for file/memory tasks
- `fileops.py` / `memoryops.py` - 40x faster file IO and 8x faster search orchestrators
- `sessions/` + `scratchpad/` - Auto-checkpointing, resume, and working memory helpers

**Usage**: Currently invoked by IDE agents; v2.2.9 adds CLI (`whitemagic parallel status/run`) + MCP telemetry so humans can trigger the same flows outside IDEs.

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
- **Frontend**: Vercel (static dashboard) — login temporarily paused; provision API keys via CLI/scripts.
- **Nixpacks + Procfile** for Railway deployment

---

## Future Enhancements

1. **Semantic Search** - pgvector + embeddings (shipping in 2.3.0)
2. **Audit & Docs Automation** - `whitemagic audit`, `docs-check`, `exec plan` (v2.2.8) exposed via CLI + MCP
3. **Parallel CLI Surfaces** - `whitemagic parallel status/run` + scratchpad dashboards (v2.2.9)
4. **Workspaces** - Team collaboration
5. **Nested Learning** - Multi-speed memory tiers

---

See [VISION.md](VISION.md) for strategic philosophy.
