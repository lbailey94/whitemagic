# WhiteMagic v2.1.7 Release Notes

**Released**: November 15, 2025
**Package Size**: 115 KB wheel, 134 KB source

## Summary

v2.1.7 introduces smart memory features: setup wizard, templates, auto-tagging, relationships, lifecycle management, and analytics dashboard.

## New Features

### Setup Wizard
- Interactive tier-based configuration
- 4 tiers: Personal, Power, Team, Regulated
- Embeddings installation helper
- `whitemagic setup`

### Templates
- 5 built-in YAML templates
- Interactive field prompts
- `whitemagic template-list/show/create`

### Auto-Tagging
- Intelligent tag suggestions
- Version & keyword extraction
- `--no-auto-tag` flag

### Relationships
- 6 relationship types
- `whitemagic relate/related`

### Lifecycle & Stats
- Importance scoring
- Analytics dashboard
- `whitemagic stats`

### MCP Tools
- `read_memory` - Full content retrieval
- `list_memories` - Complete catalog

## Known Issue

Minor import bug in relationship commands (fixed in dev, will release v2.1.8 patch).

## Testing

173/174 tests passing (99.4%)

## Install

```bash
pip install --upgrade whitemagic
```
