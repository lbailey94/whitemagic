# WhiteMagic Compatibility Policy

**Version**: 25.1.0
**Updated**: 2026-07-20

## Semantic Versioning

WhiteMagic follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (e.g., 26.0.0): Breaking changes to stable tool API, memory schema, or configuration
- **MINOR** (e.g., 25.1.0): New tools, new galaxies, new features (backward-compatible)
- **PATCH** (e.g., 25.0.2): Bug fixes, performance improvements, documentation (backward-compatible)

## Stable Tool List

The stable surface is generated from canonical sources via `scripts/generate_facts.py`:

- **57 stable tools** = 28 Gana meta-tools + 29 promoted foundational tools
- Stable tools have `stability = STABLE` in their `ToolDefinition`
- Stable tools are listed in `stable_surface.py:STABLE_TOOL_NAMES`
- Stable tools cannot be removed without a major version bump

### Promoted Foundational Tools (29)

Memory (7): `create_memory`, `search_memories`, `recall`, `update_memory`, `delete_memory`, `batch_recall`, `memory_stats`

Session (4): `session.record`, `session.recall`, `session.replay`, `session.search`

Introspection (5): `capabilities`, `manifest`, `state.current`, `state.update`, `state.context`

Galaxy (4): `galaxy.canonical_taxonomy`, `galaxy.export_tutorial`, `galaxy.list`, `galaxy.stats`

Governance (5): `karmic.effects`, `karmic.debt`, `karmic.verify`, `mandala.status`, `mandala.templates`

Consciousness (4): `consciousness.loop.status`, `citta.advance`, `citta.state`, `citta.history`

## Deprecation Policy

- **Deprecated galaxy aliases** are mapped but not routed to:
  - `insight` → `knowledge`
  - `self_learning` → `knowledge`
  - `self_discovery` → `knowledge`
  - `translation` → `codex`
  - `test` → `archive`
- Deprecated tools remain callable for one minor version cycle
- Deprecation is signaled via `deprecated_aliases` field on `ToolDefinition`
- Migration warnings are logged on first use of deprecated names

## Memory Migration Support

- Memory schema migrations are forward-compatible within a major version
- Galaxy taxonomy changes include dry-run and rollback support
- `batch_recall` works across deprecated galaxy names via compatibility mapping
- Migration tests are part of the release gate (Lane D)

## Platform Matrix

| Platform | Python | Node | Status |
|----------|--------|------|--------|
| Linux x86_64 | 3.12 | 20 LTS | ✅ Supported |
| macOS x86_64 | 3.12 | 20 LTS | ✅ Supported |
| macOS ARM64 | 3.12 | 20 LTS | ✅ Supported |
| Windows x86_64 | 3.12 | 20 LTS | ✅ Supported (seed binary) |
| Linux ARM64 | 3.12 | — | ✅ Seed binary only |

## Security Reporting

- Report security vulnerabilities via GitHub Security Advisories
- Do not file public issues for security vulnerabilities
- Response time: within 48 hours
- PGP key available in `.well-known/` on whitemagic.dev

## MCP Registry Publishing Checklist

Before publishing to MCP registries (ChatGPT/Claude app directories):

- [ ] `server.json` manifest with `$schema` pointing to the 2025-12-11 server schema
- [ ] Correct tool count and metadata in `server.json`
- [ ] Reverse-DNS namespace registration (`io.github.lbailey94.whitemagic`)
- [ ] PyPI ownership verification (`mcp-name: io.github.lbailey94.whitemagic` in README)
- [ ] Every tool has `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`, and `title` annotations
- [ ] `mcp-conform` compliance check passes with zero warnings
- [ ] Tool schemas validated against MCP spec (no extra fields, correct types)
- [ ] `server.json` `packages` entry with `registryType: "pypi"`, correct `identifier` and `version`
