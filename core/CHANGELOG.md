# WhiteMagic Changelog

> **Canonical Location**: [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Complete history through v21.0.0

## Current Version

**v22.2.3** — June 18, 2026

- Polish marathon release — public-release ready
- **ruff: 1,833 → 0 errors in production (auto-fixed W293, E701,
  I001, UP042, UP035, F541, UP006, UP032, UP045, E741)**
- **mypy: 800 → 0 errors in production (935 source files)**
  - 429 import-not-found + attr-defined via overrides
  - 178 type:ignore added
  - 22 real type issues hand-fixed
- **logger: 814 logger.error/warning calls now have exc_info=True
  inside except blocks** (from 252 in v22.2.2 to 1 legitimate)
- 10 explicit type annotations on empty-collection variables
- All 5 ruff categories fully resolved
- All 11 mypy error categories fully resolved
- Test baseline: 1,470 passed, 2 skipped, 0 failed
- See root `CHANGELOG.md` for detailed release notes.

---

## v22.0.0 — April 16, 2026

- Modular installation tiers: `lite`, `mcp`, `cli`, `api`, `embeddings`, `heavy`
- 28 PRAT Gana meta-tools via MCP protocol
- Rust core with PyO3 bindings, WASM compilation target
- Comprehensive test suite (2,068 tests)
- Safety governance: Governor, input sanitizer, rate limiter, constitutional checks

## v21.0.0 — April 2026

- State-root hardening: Removed repo-local DB fallback, deterministic `~/.whitemagic` default
- Tool contract stabilization: Added `ToolStability` tiers (STABLE/OPTIONAL/EXPERIMENTAL)
- Test tiering: Added `core` pytest marker for release-critical contract tests
- Ship surface cleanup: Expanded MANIFEST.in exclusions for 48+ operational directories

See `docs/CHANGELOG.md` for complete v12-v21 history.
