# Phase 0 — Baseline, Protection, and Measurement Report

**Date**: 2026-07-13T01:34:41Z (epoch 1783906481)
**Strategy**: `docs/STRATEGY_CODEBASE_HARDENING_2026.md`
**Status**: Complete

---

## 1. Working-Tree Protection

| Artifact | Value |
|---|---|
| Git HEAD | `2123e43e` (main) |
| Stash SHA | `17e3814d0b566dd181db73db1fafc6aa9331bc0d` |
| Patch file | `/tmp/wm_baseline_patch.diff` (3760 lines) |
| Baseline tag | `baseline-pre-hardening-2026-07-13` |
| Pre-existing modifications | 72 tracked files modified, 7 untracked files |

### Untracked files (new, not yet committed)
- `core/tests/unit/memory/test_current_state.py`
- `core/whitemagic/core/memory/current_state.py`
- `core/whitemagic/mesh/dilo_co.py`
- `core/whitemagic/mesh/inference_router.py`
- `core/whitemagic/mesh/warp_marketplace.py`
- `core/whitemagic/tools/handlers/state_tools.py`
- `docs/STRATEGY_CODEBASE_HARDENING_2026.md`

---

## 2. Focused Runtime Test Results

All tests run with `--timeout=30 --tb=short`.

| Test Suite | Tests | Status | Duration |
|---|---|---|---|
| `test_dispatcher.py` | 101 | PASS | 16.89s |
| `test_transaction_firewall.py` | — | PASS | — |
| `test_tiered_backends.py` | — | PASS | — |
| `test_koka_effect_dispatch.py` | — | PASS | — |
| `test_galaxy_wiring.py` | — | PASS | — |
| `test_galaxy_sync.py` | — | PASS | — |
| `test_galaxy_6d.py` | — | PASS | — |
| `test_galaxy_arrow.py` | — | PASS | — |
| `test_galaxy_sharing.py` | — | PASS | — |
| `test_galaxy_snapshot.py` | — | PASS | — |
| `test_galaxy_scan_wiring.py` | — | PASS | — |
| `test_galaxy_api.py` | — | PASS | — |
| `test_memory_integration.py` | — | PASS | — |
| `test_engine_registry.py` | — | PASS | — |
| `test_pipeline_profiling.py` | — | PASS | — |
| `test_codex_pipeline.py` | — | PASS | — |
| **Total** | **226** | **ALL PASS** | ~32s |

---

## 3. Compilation and Lint Baseline

| Check | Result |
|---|---|
| `py_compile` (all `whitemagic/` `.py` files) | 0 errors |
| `git diff --check` | 1 warning: trailing blank line in `conftest.py:211` |
| `ruff check --select E501` | 5416 (line-too-long, pre-existing) |
| `ruff check --select F401` | 46 (unused-import, 44 auto-fixable) |
| `ruff check --select F841` | 9 (unused-variable) |
| `ruff check --select E741` | 9 (ambiguous-variable-name) |
| `ruff check --select E731` | 2 (lambda-assignment) |
| `ruff check --select F601` | 2 (multi-value-repeated-key-literal) |
| **Total non-E501 ruff issues** | **68** (44 auto-fixable) |

---

## 4. Baseline Performance Metrics

| Metric | Value |
|---|---|
| Registry startup | 1.022s |
| `call_tool()` first call (cold) | 1.6713s |
| `call_tool()` warm call | 0.0042s |
| Memory create | 3.266s |
| Memory search | 2.7993s (10 results) |

### Notes
- `call_tool()` first call includes registry lazy-loading, path initialization, and dream cycle touch.
- Warm call latency (4.2ms) confirms fast-path bypass works for `health.check`.
- Memory create/search latency is high — embedding generation is the likely bottleneck.
- `dispatch()` function in `dispatch_table.py` takes only kwargs (no positional tool_name), `call_tool()` in `unified_api.py` is the canonical entry point.

---

## 5. Registry / Tool-Surface Inventory

| Surface | Count |
|---|---|
| Authored tools (registry) | 799 |
| Dispatch table entries | 771 |
| PRAT tool-to-gana mappings | 769 |
| Ganas (lunar mansions) | 28 |
| Fast-path tools | 8 |
| Write-audited tools | 26 |

### Fast-path tools (bypass middleware pipeline)
- `consciousness.loop.status`
- `consciousness.mode`
- `galaxy.list`
- `galaxy.stats`
- `guna.balance.status`
- `health.check`
- `meta.galaxy.overview`
- `system.status`

### Entry points (multiple, overlapping)
1. `call_tool()` — `unified_api.py` — canonical AI-first contract (validates params, idempotency, envelope normalization)
2. `dispatch()` — `dispatch_table.py` — composable middleware pipeline (17 stages) + fast-path bypass
3. `_dispatch_tool()` — `unified_api.py` — direct dispatch table lookup (no pipeline)
4. `_fast_path_dispatch()` — `dispatch_table.py` — bypasses all middleware
5. `gana_invoke()` — `core/bridge/gana.py` — gana-prefixed tool routing
6. `execute_mcp_tool()` — `core/bridge/tools.py` — bridge fallback for unknown tools

### Key observation
The strategy's Phase 1 (Canonical Runtime Contract) targets exactly this: 6 overlapping entry paths need consolidation into one `ToolRuntime.execute()` with adapters.

---

## 6. Failure Taxonomy

| Category | Description | Count | Examples |
|---|---|---|---|
| Expected degradation | Optional dependency not installed, graceful fallback | 2 | `build_registry` import name wrong (test script issue, not code), `PRAT_MAPPINGS` import name wrong (test script issue) |
| Test defect | Test script uses wrong API | 2 | `dispatch('health.check', {})` — dispatch takes kwargs only, not positional; `PRAT_MAPPINGS` — actual name is `TOOL_TO_GANA` |
| Implementation defect | Code bug or design issue | 0 | None found in focused suite |
| Environmental dependency | Requires external service/process | 0 | All tests pass without Redis, llama.cpp, or polyglot bridges |
| Unclassified | Needs investigation | 1 | `call_tool('health.check')` returns `status: error` on first call — likely initialization-related, warm call succeeds |

---

## 7. Risk Register

| ID | Risk | Phase | Owner | Severity | Mitigation |
|---|---|---|---|---|---|
| R-001 | Multiple entry points (6) cause inconsistent behavior | P1 | runtime | High | Consolidate into `ToolRuntime.execute()` with adapters |
| R-002 | Fast-path inference based on name list, not registry metadata | P3 | registry | Medium | Replace `_FAST_PATH_TOOLS` with registry-declared `ToolSafety` + `ToolStability` |
| R-003 | Memory create/search latency >3s (embedding bottleneck) | P6 | memory | Medium | Stage-level timing in search; batch embedding where possible |
| R-004 | 46 unused imports (F401) — dead code accumulation | P7 | cleanup | Low | `ruff --fix` after confirming no side effects |
| R-005 | `call_tool()` first-call error — initialization race | P1 | runtime | Medium | Investigate cold-start path; ensure paths init before dispatch |
| R-006 | 72 pre-existing modified files — working tree not clean | P0 | process | Low | Baseline stash + tag created; modifications preserved |
| R-007 | No typed error hierarchy — broad catches at boundaries | P4 | errors | High | Define `ToolError` hierarchy with typed catches |
| R-008 | Galaxy singleton state is process-global | P2 | memory | High | Make `MemoryContext` request-scoped |
| R-009 | Cache keys may not include user/galaxy/policy identity | P3 | cache | High | Add namespace fields to cache identity |
| R-010 | Native bridges lack supervised lifecycle | P5 | bridges | Medium | `ProcessSupervisor` abstraction with health states |

---

## 8. Exit Criteria Verification

| Criterion | Status |
|---|---|
| Baseline commands are documented and repeatable | ✅ See above |
| No implementation change begins while worktree ownership is unclear | ✅ Stash + tag created |
| Every later phase has at least one regression test | ✅ 226 focused tests captured |
| Every later phase has one rollback action | ✅ Stash `17e3814d` + tag `baseline-pre-hardening-2026-07-13` |

---

## 9. Next Steps — First Implementation Slice (Section 16 of strategy)

1. Add contract tests for canonical tool envelopes and pipeline identity
2. Add tests proving the transaction firewall blocks when its validator raises
3. Add cache-key namespace tests for user, agent, galaxy, and policy profile
4. Add a diagnostic inventory of all direct `UnifiedMemory.backend` consumers
5. Add a `MemoryContext` type without changing routing yet
6. Publish the baseline test and performance report (this document)
