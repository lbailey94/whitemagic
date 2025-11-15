# WhiteMagic Project Architecture (v2.1.5)

## Overview
WhiteMagic is a production-ready tiered memory management system for AI agents with native MCP + REST support.

## Core Components

### 1. Memory Management (/whitemagic/)
- **File-based storage**: Markdown files with YAML frontmatter
- **Tiers**: short_term, long_term, archive
- **Metadata**: JSON-based metadata.json for fast queries
- **Manager**: MemoryManager class handles all CRUD operations

### 2. API Layer (/whitemagic/api/)
- **FastAPI**: REST API on port 8000
- **Auth**: API key-based authentication
- **Endpoints**: CRUD, search, exec, api-keys
- **Database**: SQLite (local) / PostgreSQL (production)

### 3. Embeddings (/whitemagic/embeddings/)
- **Providers**: Local (sentence-transformers) + OpenAI
- **Models**: all-MiniLM-L6-v2 (88MB, 384 dimensions)
- **Async**: Event loop-friendly with asyncio.to_thread
- **Config**: Provider selection via ~/.whitemagic/config.yaml

### 4. Terminal Tool (/whitemagic/terminal/)
- **Executor**: Subprocess wrapper with safety checks
- **Allowlist**: Command filtering by profile (PROD/AGENT)
- **Approver**: Interactive approval workflow for write operations
- **Audit**: All executions logged with correlation IDs

### 5. Search (/whitemagic/search/)
- **Semantic**: Vector similarity search with embeddings
- **Keyword**: Full-text search with tag filtering
- **Hybrid**: Combined approach for best results

### 6. CLI (/whitemagic/cli_app.py)
- **Commands**: create, list, search, update, delete, restore, backup
- **Rich formatting**: Tables, panels, progress bars
- **Async support**: Non-blocking operations with spinners

### 7. MCP Server (/whitemagic-mcp/)
- **TypeScript**: Native MCP implementation
- **Tools**: 7 tools (create, search, update, delete, etc.)
- **Resources**: 4 resources (stats, memories, etc.)
- **Clients**: Cursor, Windsurf, Claude Desktop, VS Code

## File Structure
```
whitemagic/
├── api/              # FastAPI REST API
├── cli/              # CLI utilities
├── config/           # Configuration system
├── embeddings/       # Embedding providers
├── search/           # Search implementations
├── terminal/         # Terminal tool
├── backup.py         # Backup/restore
├── cli_app.py        # Main CLI entry point
├── constants.py      # Global constants
└── manager.py        # Memory manager

whitemagic-mcp/       # MCP server (TypeScript)
├── src/
│   ├── index.ts      # Main server
│   └── tools.ts      # Tool definitions
└── package.json
```

## Key Design Decisions

1. **File-based storage**: Simple, portable, git-friendly
2. **Modular installation**: Core (~50MB) + optional extras (embeddings +2.5GB)
3. **Security by default**: Terminal tool read-only, exec API disabled
4. **Async-first**: Non-blocking I/O throughout
5. **Type-safe**: 100% type hints, Pydantic models

## Dependencies

### Core (required)
- FastAPI, Uvicorn (API server)
- SQLAlchemy, aiosqlite (database)
- Pydantic (validation)
- Rich (CLI formatting)

### Optional
- sentence-transformers, torch (local embeddings)
- OpenAI (cloud embeddings)

## Current State (Nov 15, 2025)
- Version: 2.1.5
- Tests: 223 passing (196 Python + 27 MCP)
- Grade: A+ (99/100)
- Security: All critical vulnerabilities patched
- Deployment: Railway + Vercel (successful)
