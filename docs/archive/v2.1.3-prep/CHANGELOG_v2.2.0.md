# Changelog v2.2.0

## [2.2.0] - 2025-11-11

### Added

#### Phase 2B: Semantic Search
- Embedding generation module with OpenAI provider
- 3 search modes: keyword, semantic, hybrid (RRF)
- PostgreSQL + pgvector caching layer
- POST /api/v1/search/semantic endpoint
- Comprehensive documentation (~30k words)

#### Phase 2C: Terminal Tool
- Core execution engine with timeout handling
- Allowlist system with 4 profiles (dev, ci, agent, prod)
- Audit logging to JSONL files
- Approval workflow with TUI interface
- CLI commands: `wm exec run`, `wm exec audit`
- POST /api/v1/exec and /api/v1/exec/read endpoints
- MCP `exec_read` tool for AI agents
- TerminalConfig with environment variable support

### Changed
- Version bumped from 2.1.0 to 2.2.0
- Updated all documentation for Phase 2 completion

### Fixed
- Test collection issues in pytest
- Module import/export issues
- Syntax errors from markdown escaping

## [2.1.0] - 2025-10-XX

### Added
- Memory management system
- Tiered memory (short-term, long-term)
- MCP server with 7 tools
- REST API endpoints
- Dashboard UI

## [2.0.0] - 2025-09-XX

### Added
- Initial WhiteMagic platform
- Basic memory operations
- API foundation
