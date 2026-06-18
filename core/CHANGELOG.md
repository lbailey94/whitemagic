# WhiteMagic Changelog

> **Canonical Location**: [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Complete history through v21.0.0

## Current Version

**v22.2.1** — June 18, 2026

- Patch release — quality + cleanup, no schema or wire-format changes
- New `ipc_try_receive` Python API (iceoryx2 subscriber side); closes
  the wm/commands consumer gap from the polyglot survey
- `surprise_gate` RuntimeError bug fix unblocks 4+6 tests in
  `test_critical_paths.py`
- `conftest` extraction to `tests/_envelope.py` unblocks 34 tests
  across integration/unit suites
- 14 pre-existing absolute_path_literals hits replaced with
  env-var-overridable paths and canonical `DB_PATH`
- 1,050 docstrings added (888 functions + 162 classes);
  0.8% / 0.0% undocumented public functions/classes
- Test baseline: 1,470 passed, 2 skipped, 0 failed
- Omega test: ALL 8 suites pass, 1,967/1,967 checks
- Doc drift check: 9/9 pass
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
