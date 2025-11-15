# WhiteMagic v2.2.0 Release Notes

**Release Date**: November 11, 2025  
**Status**: Production Ready

## Overview

Version 2.2.0 represents a major milestone, completing **Phase 2** of the WhiteMagic platform. This release transforms WhiteMagic from a memory system into a complete agentic platform with semantic search and safe terminal execution.

## New Features

### Semantic Search (Phase 2B)
- **Embedding Generation**: OpenAI integration + local placeholders
- **3 Search Modes**: Keyword, semantic, hybrid (RRF)
- **Storage Layer**: PostgreSQL caching with pgvector
- **REST API**: 2 new endpoints for search operations
- **~1,500 lines** of production code

### Terminal Tool (Phase 2C)  
- **Safe Execution**: Allowlist-based command filtering
- **4 Profiles**: dev, ci, agent, prod
- **Audit Logging**: JSONL trail with run IDs
- **Approval Workflow**: Interactive TUI + callbacks
- **CLI Commands**: `wm exec run`, `wm exec audit`
- **REST API**: 2 new endpoints for execution
- **MCP Integration**: `exec_read` tool for AI agents
- **~1,200 lines** of production code

## Statistics

| Metric | Value |
|--------|-------|
| **Total New Code** | 2,700 lines |
| **New Modules** | 20 files |
| **Tests** | 13 passing (terminal 100%) |
| **API Endpoints** | +4 new endpoints |
| **CLI Commands** | +2 new commands |
| **MCP Tools** | +1 new tool |
| **Documentation** | 8 comprehensive guides |

## Breaking Changes

None. All changes are backwards compatible.

## Upgrade Notes

1. Optional: Install pgvector for Tier 2 caching
2. Optional: Set `OPENAI_API_KEY` for semantic search
3. Configure terminal profiles via `~/.whitemagic/terminal_config.json`

## What's Next

- Phase 3: UI/UX improvements
- Phase 4: Advanced features
- Continuous optimization

## Contributors

Built with momentum and care over focused development sessions.
