# WhiteMagic Changelog

> **Canonical Location**: [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Complete history through v21.0.0

## Current Version

**v22.2.2** — June 18, 2026

- Patch release — quality, security, doc-freshness, no schema
  or wire-format changes
- CI guardrail for bare `except` blocks (`BLE001`); 1,328 -> 0
  violations suppressed via file-level markers
- 15 file version-drift fixes (release_readiness test was
  failing 3 + check_versions.py flagged 12)
- `AGENTS.md` test-baseline figures refreshed (2,063/2,243/2,379
  -> 1,470, v22.2.0 -> v22.2.2)
- `AI_PRIMARY.md` 30-day re-verification block added; prescience
  claims #7/#8/#9 re-affirmed via AGT v4 / Anthropic Memory /
  Cloudflare Project Think convergence
- `EVIDENCE_MAP.md` Claim 1 re-verified (v1.0.0 -> v1.1.0)
- Test baseline: 1,470 passed, 2 skipped, 0 failed
- Omega test: ALL 8 suites pass
- Doc drift + check_versions: 0 errors
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
