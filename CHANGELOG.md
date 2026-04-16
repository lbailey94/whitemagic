# Changelog

All notable changes to WhiteMagic will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [22.0.0] - 2026-04-16

### Added
- Modular installation tiers: `lite`, `mcp`, `cli`, `api`, `embeddings`, `heavy`
- 28 PRAT Gana meta-tools via MCP protocol
- Rust core with PyO3 bindings (memory, search, embeddings, graph, safety)
- WASM compilation target for browser/edge deployment
- Polyglot bridges: Koka, Mojo, Haskell
- CI/CD workflow (GitHub Actions)
- Comprehensive test suite (2259 tests)
- Safety governance: Governor, input sanitizer, rate limiter, constitutional checks
- MCP health endpoint (`whitemagic://health`) for liveness checks
- CLI command registration registry pattern for better decoupling
- Batch embedding backfill script for 93K memories without embeddings
- Exception block narrowing automation scripts

### Changed
- Removed SD card path fallback from `paths.py`
- Consolidated stub packages (removed 6 unused: cache, db, search, monitoring, parallel, plugins)
- Moved frontend to separate project
- Archived `campaigns_public_backup` to legacy
- Removed duplicate contributing guide
- Resonance subsystem consolidated to single module with backward-compatible shim packages
- Fixed 537 except Exception blocks (45% of total) with specific exception types
- Fixed 212 ruff errors automatically
- Updated justfile setup targets to use correct extras
- Fixed Aria manifest paths (290 entries updated)

### Removed
- SD card fallback in path resolution
- Unused stub packages
- Duplicate `docs/community/CONTRIBUTING.md`
- Koka and Rust build binaries (now gitignored)
- Non-existent Rust lazy modules (embeddings, data_lake, bindings) from _LAZY_MODULES
- Incomplete agentic module from lazy loading
