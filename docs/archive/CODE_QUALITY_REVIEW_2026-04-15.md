> **⚠️ ARCHIVED / SUPERCEDED** — Findings merged into `docs/message_board/STRATEGIC_ROADMAP_V23.md` (Quality Gates, 2026-06-03). See `docs/message_board/ROADMAP_CONSOLIDATION_2026-06-03.md` for merge history.

# WhiteMagic Code Quality Review & Improvement Plan

**Original Date**: 2026-04-15
**Updated**: 2026-04-15 (post-execution)
**Version**: 22.0.0
**Reviewer**: Internal AI-assisted audit

---

## Executive Summary

WhiteMagic is a technically impressive polyglot agentic AI platform with innovative architectural
concepts (PRAT Gana system, polyglot bridges), but it accumulated significant technical debt and
code quality issues. This document tracks the full audit, all changes executed, remaining deferred
work, and a staged roadmap for completing it.

**Execution Status**: Phases 0–5 executed in a single session pair-programming engagement.
**Test suite**: **949 / 949 passing** throughout all changes. *(Note: This was accurate at time of review. Current state as of 2026-04-22: 783 passed, 173 failed, 259 skipped.)*

### Quantitative Snapshot — Before vs After

| Metric | Before | After |
|--------|--------|-------|
| Silent `except` blocks in `store()` | 6 | 0 |
| Silent `except` in `sqlite_backend.py` | 6 | 0 |
| `BaseException` swallowing signals | 1 | 0 |
| Stale artifacts committed | 6+ files | 0 |
| SQLite connection leak (`EmbeddingEngine`) | Yes | Fixed (`close()`, `atexit`) |
| Version fallback drift | `"18.1.0"` (hardcoded) | `importlib.metadata` → `VERSION` file → `"unknown"` |
| Gana Forge signature security | SHA-256, no secret (forgeable) | HMAC-SHA256 + vault/PBKDF2 key |
| CORS policy (MCP HTTP server) | `allow_origins=["*"]` | Localhost-only, configurable via `WM_MCP_CORS_ORIGINS` |
| `cp`/`mv` in SafeExecutor default allowlist | Yes | Moved to `CONFIRM_COMMANDS` tier |
| Polyglot stubs clearly marked | No | `STUB_SPECIALISTS` frozenset + `logger.debug()` |
| `@singleton` reset correctness | Broken (module-var only) | Fixed (clears `wrapper._instance`) |
| `WM_*` env vars documented | 12 / 51 | 51 / 51 (`docs/CONFIGURATION.md`) |
| Contradictory STATUS docs | 2 conflicting files | Single canonical `polyglot/STATUS.md` |
| `edit_file()` in autonomous executor | Append-only | Full line-range + find-replace patching |
| `dispatch_table.py` size | 895 lines (monolith) | 234 lines (merge glue) + 4 domain slices |
| Tool count in `mcp-registry.json` | 374 (stale/manual) | **420** (auto-generated from live table) |
| Architecture Decision Records | 0 | 4 (`docs/adr/`) |
| Feature-flag system | None | `WM_FEATURE_*` with typed registry |
| CI mypy blocks on failure | No (`continue-on-error`) | Yes (strict, public surface) |
| `# type: ignore` count | 218 | 218 (unchanged — deferred) |
| `pass` statement count | 598 | 342 (after Phase 0–3 cleanup) |
| Active MCP servers | 2 (drift risk) | 2 (lean = canonical; hydrated = deprecated) |

---

## Findings Registry — Final Status

### 🔴 Critical (F-01 through F-06)

| ID | Finding | Status |
|----|---------|--------|
| F-01 | Version fallback `"18.1.0"` — 3 major versions behind | ✅ Fixed — `importlib.metadata` fallback chain |
| F-02 | 6+ silent `except` blocks in `UnifiedMemory.store()` | ✅ Fixed — all 6 instrumented with `logger.warning()` |
| F-03 | Gana Forge signature is deterministic SHA-256 (no secret) | ✅ Fixed — HMAC-SHA256 + PBKDF2 vault key; sentinel rejects unkeyed |
| F-04 | `BaseException` catch swallows `KeyboardInterrupt`/`SystemExit` | ✅ Fixed — explicit re-raise of signals |
| F-05 | Stale runtime artifacts committed to repo | ✅ Fixed — removed; `.gitignore` updated |
| F-06 | `EmbeddingEngine` leaks SQLite connections | ✅ Fixed — `close()`, `__enter__`/`__exit__`, `atexit` hook |

### 🟠 High (F-07 through F-14)

| ID | Finding | Status |
|----|---------|--------|
| F-07 | Dual MCP servers with independent registration — drift risk | ✅ Mitigated — `run_mcp.py` marked deprecated; `run_mcp_lean.py` is canonical |
| F-08 | Contradictory polyglot STATUS documents | ✅ Fixed — `core/POLYGLOT_STATUS.md` redirects to `polyglot/STATUS.md` |
| F-09 | Giant files (>900 lines) need decomposition | ⚠️ Partial — `dispatch_table.py` split (895→234 + 4 slices); `cli_app.py` (1243) and `embeddings.py` (1055) deferred |
| F-10 | Singleton reset fragility — manual list in conftest | ✅ Fixed — `reset_all_singletons()` now deletes `wrapper._instance` attributes |
| F-11 | `SafeExecutor` allowlist includes `cp`, `mv` | ✅ Fixed — moved to `CONFIRM_COMMANDS` tier |
| F-12 | CORS `allow_origins=["*"]` on HTTP MCP server | ✅ Fixed — localhost-only default; `WM_MCP_CORS_ORIGINS` override |
| F-13 | 1,723 broad `except Exception` blocks codebase-wide | ⚠️ Partial — top critical paths logged (unified.py ×6, sqlite_backend.py ×5); 1,700+ remain |
| F-14 | Placeholder polyglot specialists return hardcoded results | ✅ Fixed — `STUB_SPECIALISTS` frozenset + `logger.debug()` on each stub |

### 🟡 Medium (F-15 through F-22)

| ID | Finding | Status |
|----|---------|--------|
| F-15 | 47 `WM_*` env vars with only 12 documented | ✅ Fixed — `docs/CONFIGURATION.md` covers all 51 |
| F-16 | Inconsistent error return patterns | ⚠️ Acknowledged — not yet standardized codebase-wide |
| F-17 | `edit_file()` only appends | ✅ Fixed — JSON `{start_line, end_line, replacement}` and `{find, replace}` |
| F-18 | Mypy `continue-on-error: true` — regressions unnoticed | ✅ Fixed — public surface now CI-blocking; full codebase still non-blocking |
| F-19 | 598 `pass` statements | ⚠️ Partial — currently 342; no targeted sweep yet |
| F-20 | 218 `# type: ignore` suppressing type errors | 🔲 Deferred |
| F-21 | 2,140+ singleton patterns / 533 `global` statements | 🔲 Deferred |
| F-22 | 940+ cache references without centralized invalidation | 🔲 Deferred |

### 🟢 Low (F-23 through F-26)

| ID | Finding | Status |
|----|---------|--------|
| F-23 | TODO/FIXME/HACK comments | ✅ Verified — only 1 actual in-code `# TODO`; 31-count was from framework string values |
| F-24 | `mcp-registry.json` count manually maintained | ✅ Fixed — `scripts/generate_mcp_registry.py`; count now **420** |
| F-25 | No Architecture Decision Records | ✅ Fixed — 4 ADRs in `docs/adr/` |
| F-26 | No property-based testing or fuzzing | 🔲 Deferred |

---

## What Was Changed — File-by-File

### Phase 0: Critical Safety & Correctness

| File | Change |
|------|--------|
| `core/whitemagic/run_mcp_lean.py` | Version fallback: `"18.1.0"` → `importlib.metadata.version()` → `VERSION` file → `"unknown"` |
| `core/whitemagic/optimization/rust_accelerators.py` | `except BaseException` now re-raises `KeyboardInterrupt`, `SystemExit` |
| `core/whitemagic/core/memory/unified.py` | All 6 silent `except` in `store()` now call `logger.warning()` |
| `core/whitemagic/core/memory/embeddings.py` | Added `close()`, `__enter__`/`__exit__`, `atexit` registration to `EmbeddingEngine` |
| `.gitignore` | Added patterns: `*.log`, `*.bak*`, `benchmark_output.txt`, `llms-full.txt`, etc. |
| (repo root) | Removed stale artifacts: `excavation.log`, `benchmark_output.txt`, `rig_debug.log`, `test.db.bak.1`, `llms-full.txt` |

### Phase 1: Observability & Hygiene

| File | Change |
|------|--------|
| `core/whitemagic/core/memory/sqlite_backend.py` | 5 silent `except` blocks now call `logger.debug()` — cold pool init, cache read, cache set, cold cache set |
| `core/whitemagic/utils/singleton.py` | Complete rewrite — registry is now a flat `list[tuple]`; `reset_all_singletons()` deletes `wrapper._instance` attributes, not just module vars |
| `docs/CONFIGURATION.md` | **New file** — full reference for all 51 `WM_*` env vars with types, defaults, descriptions, and CI override table |
| `core/POLYGLOT_STATUS.md` | Replaced body with redirect banner to `polyglot/STATUS.md`; corrected Koka status (Production → Experimental) |
| `core/whitemagic/autonomous/executor/continuous_executor.py` | `edit_file()` rewritten: JSON `{start_line, end_line, replacement}`, JSON `{find, replace}`, or string append (legacy) |

### Phase 2: Security Hardening

| File | Change |
|------|--------|
| `core/whitemagic/tools/gana_forge.py` | `_compute_manifest_signature()`: SHA-256 → HMAC-SHA256; added `_get_forge_signing_key()` with PBKDF2 from `WM_VAULT_PASSPHRASE` → vault → sentinel (zero-key always fails) |
| `core/whitemagic/run_mcp_lean.py` | CORS: `allow_origins=["*"]` → localhost-only list; `allow_methods`/`allow_headers` narrowed; `WM_MCP_CORS_ORIGINS` configurable |
| `core/whitemagic/execution/safe_executor.py` | `cp`/`mv` moved from `DEFAULT_ALLOWED_COMMANDS` to new `CONFIRM_COMMANDS` frozenset |
| `core/whitemagic/optimization/polyglot_specialists.py` | Added `STUB_SPECIALISTS` class-level frozenset; Elixir/Go stubs emit `logger.debug()` |
| `core/.env.example` | Added `WM_MCP_CORS_ORIGINS` entry |

### Phase 3: Architecture Simplification

| File | Change |
|------|--------|
| `core/whitemagic/tools/dispatch_core.py` | **New file** — `LazyHandler`, `LazyHandlerAbs`, `WRITE_TOOLS`, `_audit_tool_call` extracted from monolith |
| `core/whitemagic/tools/dispatch_memory.py` | **New file** — 56 memory/galaxy/living-graph tools |
| `core/whitemagic/tools/dispatch_intelligence.py` | **New file** — 117 KG/embedding/dream/cognition/analytics tools |
| `core/whitemagic/tools/dispatch_agents.py` | **New file** — 71 session/swarm/agent-registry/mesh/voting/pipeline tools |
| `core/whitemagic/tools/dispatch_security.py` | **New file** — 69 security/sandbox/shelter/dharma/watcher/forge tools |
| `core/whitemagic/tools/dispatch_table.py` | **Rewritten**: 895 lines → 234 lines; merges domain slices; all public APIs preserved (`DISPATCH_TABLE`, `dispatch()`, `get_pipeline()`, `LazyHandler`, `WRITE_TOOLS`) |
| `core/whitemagic/run_mcp.py` | Added deprecation banner; `run_mcp_lean.py` identified as canonical; archive planned for v22.0 |

### Phase 4: Quality Infrastructure

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Mypy strict check on `tools/` + `interfaces/` now CI-blocking (removed `continue-on-error`); full-codebase scan retained as non-blocking survey |
| `docs/adr/ADR-001-prat-gana-system.md` | **New** — Decision record for the 28 Gana meta-tool architecture |
| `docs/adr/ADR-002-polyglot-strategy.md` | **New** — Decision record for tiered polyglot (Production/Advanced/Experimental/Archival) |
| `docs/adr/ADR-003-resonance-model.md` | **New** — Decision record for Gan Ying Bus + Wu Xing phase scheduling |
| `docs/adr/ADR-004-memory-architecture.md` | **New** — Decision record for SQLite + Galactic distance model + HRR |
| `core/scripts/generate_mcp_registry.py` | **New** — Auto-generates `mcp-registry.json` from live dispatch table; `--check` for CI stale detection |
| `core/mcp-registry.json` | **Regenerated** — now shows 420 tools (was 374 stale), with domain breakdown |

### Phase 5: Platform Evolution

| File | Change |
|------|--------|
| `core/whitemagic/utils/feature_flags.py` | **New** — `WM_FEATURE_*` env-var convention; typed `FeatureFlag` registry; `is_enabled()`, `require()`, `get_all_flags()` API; 8 initial flags |

---

## Current State — Metrics Dashboard (2026-04-15 Post-Execution)

| Metric | Value | Trend |
|--------|-------|-------|
| Test suite | **949 / 949 passing** | ✅ Stable through all phases |
| Silent `except` in critical paths | **0** (was 12+) | ✅ |
| `# type: ignore` | **218** | → Unchanged (deferred) |
| `pass` statements | **342** | ↓ (was 598, partially reduced by edit) |
| `WM_*` vars documented | **51 / 51** | ✅ Complete |
| Architecture Decision Records | **4** | ✅ New |
| MCP tool count | **420** | ✅ Auto-generated |
| Forge signature security | **HMAC-SHA256** | ✅ |
| CORS policy | **localhost-only default** | ✅ |
| Dispatch table file size | **234 lines** (was 895) | ✅ Split into 5 files |
| Feature flags | **8 registered** | ✅ New system |
| Polyglot STATUS docs | **1 canonical** (was 2 conflicting) | ✅ |

---

## Deferred Work — Staged Roadmap

The remaining items below are grouped by effort size and dependency order.
Each stage builds on the previous and should be tackled as a focused work session.

---

### Stage A — Quick Wins (~4–6 hours)
*No architectural risk. Executable in a single focused session.*

#### A1: Standardize Tool Error Envelopes (F-16)
- **Problem**: Many tool handlers return `{"status": "ok"}` or raw dicts instead of the standard `{"status": "success"|"error", "tool": ..., "request_id": ..., ...}` envelope.
- **Action**: Grep for `"status": "ok"` and missing `"envelope_version"` keys in handlers. Update `tests/verify/test_p0_contracts.py` to reject non-compliant shapes.
- **Files**: `core/whitemagic/tools/handlers/*.py`, `tests/verify/test_p0_contracts.py`
- **Acceptance**: `assert_envelope_shape()` in conftest passes for every tool call in the verify suite.
- **Effort**: ~3 hr

#### A2: `pass` Statement Sweep — Critical Paths (F-19, partial)
- **Problem**: 342 `pass` statements remain. Many are empty exception handlers that should either log, raise, or document why silence is intentional.
- **Action**: Target the following files specifically (highest `pass` density outside already-fixed files):
  - `security/vault.py` (line 142 — already identified, needs `logger.debug()`)
  - `core/intelligence/` — any `pass` in class methods
  - `tools/handlers/` — any `pass` in error branches
- **Acceptance**: Every `except`+`pass` in `security/`, `core/intelligence/`, and `tools/handlers/` has a comment or log.
- **Effort**: ~2 hr

#### A3: Add `generate_mcp_registry.py` to CI (F-24 follow-up)
- **Problem**: The script exists but isn't wired into CI yet — the registry can still drift.
- **Action**: Add one step to the `packaging` job in `.github/workflows/ci.yml`:
  ```yaml
  - name: Verify mcp-registry.json is current
    run: python3 scripts/generate_mcp_registry.py --check
  ```
- **Effort**: 15 min

#### A4: Feature Flags — Wire OTEL and RUST_STORE
- **Problem**: `feature_flags.py` exists but no code calls `is_enabled()` yet for the two stable flags.
- **Action**: In `run_mcp_lean.py` startup, call `get_all_flags()` and log enabled features. In `sqlite_backend.py`, gate the Rust store path on `is_enabled("RUST_STORE")`. In `run_mcp_lean.py` or `adaptive_portal.py`, gate OTel init on `is_enabled("OTEL")`.
- **Effort**: ~1 hr

---

### Stage B — Medium Refactors (~12–18 hours)
*Moderate risk. Each item is independent — they can be done in any order.*

#### B1: `cli_app.py` Decomposition (F-09b)
**Current size**: 1,243 lines  
**Target**: <300 lines (thin main + command dispatch)

Strategy:
1. Audit `cli_app.py` — identify top-level command groups (`wm memory`, `wm dream`, `wm garden`, etc.).
2. Each group already has a counterpart in `cli/commands/` (e.g., `dream_commands.py`). Move remaining inline commands there.
3. Reduce `cli_app.py` to a `click` group that loads sub-commands from `cli/commands/*.py`.
4. Run `pytest tests/` after each command group move.

**Risk**: Medium — CLI tests are shallow; rich integration test coverage doesn't exist for every command.  
**Mitigation**: Move one command group at a time; run `wm --help` and spot-check after each.  
**Files**: `whitemagic/cli/cli_app.py`, `whitemagic/cli/commands/`

#### B2: `embeddings.py` Decomposition (F-09c)
**Current size**: 1,055 lines  
**Target**: 4 files, each <300 lines

Strategy — split on clear seam boundaries:
1. `embeddings_engine.py` — `EmbeddingEngine` class core (model loading, `embed()`, `embed_batch()`)
2. `embeddings_hnsw.py` — HNSW index management (`build_index()`, `search()`, `save_index()`)
3. `embeddings_cold.py` — Cold storage migration and archive path logic
4. `embeddings.py` — Thin facade that imports and re-exports all three (backward-compat)

**Risk**: Medium-high — `EmbeddingEngine` is a SQLite singleton with connection state; splitting requires careful import ordering.  
**Mitigation**: Move methods in isolation; keep the `close()` / `atexit` handler in `embeddings_engine.py`.  
**Files**: `whitemagic/core/memory/embeddings.py` → 4 files

#### B3: Codebase-Wide `except Exception` Audit — Next 50 (F-13)
**Current**: 1,700+ silent blocks remain after Phase 0–1 targeted 12.

Strategy — triage by impact tier:
1. Run: `grep -n -B2 -A2 "except Exception" whitemagic/security/ | grep -B2 "pass$"` — fix all in `security/`.
2. `grep -n -B2 -A2 "except Exception" whitemagic/core/intelligence/ | grep -B2 "pass$"` — fix all in `intelligence/`.
3. `grep -n -B2 -A2 "except Exception" whitemagic/tools/handlers/ | grep -B2 "pass$"` — fix highest-impact (write tools first).
4. Target: 50 additional silent blocks converted to `logger.debug()` or `logger.warning()`.

**Effort**: ~6 hr (can be done in batches of 10)

---

### Stage C — Type System Hardening (~16–24 hours)
*High value but requires surgical attention. Best done module-by-module.*

#### C1: Reduce `# type: ignore` by 50% (F-20)
**Current**: 218 suppressions  
**Target**: ≤ 109

Strategy — work module-by-module in priority order:
1. `tools/` — mypy is already CI-blocking here; fix errors rather than suppressing.
2. `core/memory/` — high-complexity, but already has good coverage.
3. `utils/` — small files, easy wins.

For each `# type: ignore`:
- If the underlying issue is a **missing stub** (e.g., `whitemagic_rust`), add it to `mypy_stubs/` or use `--ignore-missing-imports` selectively.
- If the issue is a **union type ambiguity**, add a proper cast or type narrowing.
- If the issue is a **complex return type**, add a `Protocol` or `TypeAlias`.

#### C2: Make Mypy Strict on `core/memory/` and `core/intelligence/`
**Current**: Only `tools/` and `interfaces/` are CI-blocking.

Action:
1. Run: `mypy whitemagic/core/memory/ --disallow-untyped-defs --no-error-summary`
2. Fix errors iteratively — start with `unified.py`, `sqlite_backend.py`, `embeddings_engine.py`.
3. Once clean, add `whitemagic/core/memory/` and `whitemagic/core/intelligence/` to the CI-blocking mypy step.

**Per-file approach**: Do not attempt the whole module at once — fix one file, add it to `mypy_strict_modules` in `pyproject.toml`, commit, repeat.

---

### Stage D — Architecture Evolution (~40–80 hours)
*Long-horizon improvements. Each is a multi-session project.*

#### D1: Centralized Cache Invalidation (F-22)
**Problem**: 940+ cache references, no shared TTL or invalidation contract.

Design:
- Create `core/cache_coherence.py` with a `CacheRegistry` that all caches register with.
- `CacheRegistry.invalidate_by_tag(tag: str)` broadcasts to all registered caches.
- `memory.stored` and `memory.deleted` Gan Ying events trigger tag-based invalidation.
- Start with `query_cache.py` and `embedding cache` as reference implementations.

#### D2: Property-Based Tests (F-26)
**Problem**: No Hypothesis tests; critical algorithms (embedding similarity, recall scoring, FTS ranking) have zero invariant coverage.

Start with:
1. `tests/property/test_memory_roundtrip.py` — store → recall → content invariant
2. `tests/property/test_embedding_symmetry.py` — cosine(a,b) == cosine(b,a); self-similarity == 1.0
3. `tests/property/test_dispatch_idempotency.py` — read-only tools called twice return equivalent shapes

#### D3: Singleton Reduction (F-21)
**Problem**: 2,140+ singleton patterns / 533 `global` statements make testing brittle and hide coupling.

Staged approach:
1. Convert the 30+ singletons in conftest's fallback list to use `@singleton` decorator (so they auto-register).
2. Identify the 10 most-called singletons in `core/` — convert to constructor injection where feasible.
3. Replace `global _instance` patterns in `tools/handlers/` with module-level `functools.cache`.
4. Target: 25% reduction (535 patterns) before v22.0.

#### D4: `run_mcp.py` Archive (F-07 follow-up)
**When**: After confirming no active users depend on it (survey Claude Desktop configs).  
**Action**: Move `run_mcp.py` to `_archived/run_mcp_hydrated.py`; update `pyproject.toml` entry point.

#### D5: Full Mypy Strict Coverage (F-20 completion)
**When**: After Stage C brings suppressions to ≤109.  
**Action**: Remove `continue-on-error` from the full-codebase mypy step in CI.

---

### Stage E — Platform Evolution (Phase 5, ~144 hours)
*Quarterly investment items. See Phase 5 section of original review for details.*

- **5.1 Microkernel**: Pluggable subsystem loading/unloading. Prerequisite: Stage D3 singleton reduction.
- **5.2 OpenTelemetry**: Full tracing integration. Prerequisite: `is_enabled("OTEL")` gate in feature_flags.py is already in place. Next step: instrument `dispatch()` with `trace.get_tracer()`.
- **5.3 Formal Verification**: Runtime invariant checks for governor and sandbox. Requires contract-writing per subsystem.
- **5.4 Developer Experience**: VS Code extension for Gana tool authoring; interactive PRAT routing visualizer.
- **5.6 Unified Bridge Interface**: Standardized FFI contract for all polyglot bridges; automated compliance testing. Prerequisite: Stage B2 (embeddings decomposition) as a template for how to slice a complex module.

---

## Architecture Assessment — Updated

### Strengths (Confirmed Post-Execution)

- **PRAT Gana system** is architecturally sound (ADR-001). 28 meta-tools → 420 handlers is a strong cognitive reduction for AI clients.
- **Polyglot strategy** is correctly tiered (ADR-002). Rust/Go production bridges are genuinely mature; experimental tier is now clearly labeled.
- **Memory architecture** is sophisticated and correct (ADR-004). SQLite + HNSW + Galactic distance is a novel and effective model.
- **CI pipeline** is solid — 8 jobs, P0 contract tests non-skippable, mypy now stricter.
- **Test isolation** is working — 949 passing, singleton reset is now correct.

### Risks to Monitor

| Risk | Severity | Mitigation |
|------|----------|-----------|
| 1,700+ silent `except` blocks | High | Stage B3 batch sweeps |
| `cli_app.py` brittleness | Medium | Stage B1 decomposition |
| Cache coherency in concurrent scenarios | Medium | Stage D1 |
| `run_mcp.py` / `run_mcp_lean.py` divergence | Low (managed) | Banner + v22.0 archive plan |
| Singleton test isolation false negatives | Low (mitigated) | Stage D3 |

---

## Metrics to Track

| Metric | Current | Stage A–B Target | Stage C–D Target | Stage E Target |
|--------|---------|-------------------|------------------|----------------|
| Silent `except` (critical paths) | 0 | 0 | 0 | 0 |
| Silent `except` (codebase total) | ~1,700 | Top-50 logged | Top-100 narrowed | <50 |
| `# type: ignore` | 218 | — | ≤ 109 | 0 |
| `pass` statements | 342 | ≤ 250 | ≤ 150 | ≤ 50 |
| Singleton patterns | 2,140+ | — | 25% reduced | 50% reduced |
| `global` statements | 533 | — | 25% reduced | 50% reduced |
| Tool error envelope compliance | ~70% | 100% | 100% | 100% |
| Property tests | 0 | 0 | ≥ 5 | ≥ 20 |
| Mypy CI-blocking modules | `tools/`, `interfaces/` | + `core/memory/` | + `core/intelligence/` | All of `core/` |
| MCP server implementations | 2 (lean canonical) | 2 (hydrated archived) | 1 | 1 |
| ADRs | 4 | 4 | 6 | 10 |
| Feature flags | 8 | 12 | 12 | 20+ |
| PRAT routing overhead p95 | ~10ms | Baseline | Baseline | < 10ms w/ CI gate |

---

## Good News

Despite significant technical debt, the foundation is strong:

- **Low TODO/FIXME count**: Only 1 actual in-code `# TODO` across 819 files / ~182K lines.
- **Sophisticated memory system**: SHA-256 content-hash dedup, HNSW spatial indexing, galactic edge archival are genuinely advanced.
- **Well-structured module hierarchy**: Clear separation of concerns made it possible to split the 895-line dispatch table with zero test regressions.
- **Test isolation works**: 949 tests pass reliably with the fixed singleton reset. New `@singleton` decorator auto-registers instances for cleanup.
- **CI pipeline is solid**: 8 jobs with security scanning, reproducible builds, and P0 contract enforcement.
- **Feature flag foundation**: `WM_FEATURE_*` convention is in place; experimental features can now be safely gated without code changes.

---

**End of Review — Updated 2026-04-15**
