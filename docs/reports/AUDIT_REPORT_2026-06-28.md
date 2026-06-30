# Codebase Audit Report — 2026-06-28

## Summary

Four detection systems run across the full WhiteMagic codebase:

| System | Findings | Errors | Warnings | Info |
|--------|----------|--------|----------|------|
| **check_stubs.py** | 24 | — | — | — |
| **check_duplicates.py** | 538 (193 groups) | — | — | — |
| **STRATA** | 4,476 | 2 | 103 | 4,371 |
| **ruff (active source)** | 622 | — | — | — |
| **ruff (F841/F401 only)** | 12 | — | — | — |

## 1. Stub Audit (check_stubs.py) — 24 findings across 15 files

### Real stubs (need fixing):
- `codex/__init__.py:99,112,125` — 3x NotImplementedError (embed, index, export)
- `core/consciousness/continuous_audit.py:258` — `_fix_issue` empty body
- `core/evolution/adaptive_system.py:161,167` — `_optimize_pathway`, `_strengthen_pathway` stub docstrings
- `core/intelligence/synthesis/kaizen_engine.py:200` — `_analyze_codebase` stub docstring
- `core/intelligence/synthesis/title_generator.py:62` — `_generate_evocative_name` stub docstring
- `core/memory/akashic.py:113` — `_save_field` empty body
- `embeddings/__init__.py:32` — `get_embedding_provider` stub docstring
- `inference/router.py:572` — `_cloud_handler` stub docstring

### Intentional / allowlisted:
- `plugins/base.py:48,57,118,126,134,151` — Plugin hooks (intentional empty overrides)
- `core/plugin/base.py:31,34` — Plugin base (deactivate, configure)
- `interfaces/terminal/__init__.py:23` — `__getattr__` lazy import
- `tools/handlers/anomaly.py:20` — handler stub
- `tools/handlers/misc.py:9` — test fixture
- `tools/strata/checkers/stubs.py:213` — the checker itself
- `root_modules/comprehensive_review.py:26` — `__init__` docstring

## 2. Duplicate Detection (check_duplicates.py) — 538 duplicates in 193 groups

### Major patterns:
- **27 singleton getters** (`get_*_garden()`) — all gardens have identical `get_xxx_garden()` pattern. **False positive** — these are factory functions with different types.
- **6 handler wrappers** (`handle_starter_packs`, `handle_anomaly`, etc.) — identical dispatch wrapper structure. **Real duplication** — could use a shared handler factory.
- **6 `_connect_to_gan_ying()`** — identical bus connection code across gardens. **Real duplication** — should be a shared utility.
- **5 `_emit()` patterns** — identical event emission across handlers. **Real duplication**.
- **4 `_run_async()` patterns** — identical asyncio bridge across browser/research modules. **Real duplication**.
- **3 I Ching singletons** — `get_i_ching()` in 3 different locations. **Real duplication** — should be one canonical instance.
- **3 `__new__()` singleton patterns** — identical metaclass-like singleton in 3 classes. **Real duplication** — should use a shared decorator.

### Verdict:
~150 of the 538 are real duplications worth addressing. The rest are singleton getters that are structurally identical but semantically distinct (different types).

## 3. STRATA — 4,476 findings

### By category (top 10):
1. **copy_paste**: 932 (INFO — file-level heuristic, high false positive rate)
2. **dead_code**: 789 (INFO — potentially unused functions)
3. **broad_except**: 573 (INFO — bare `except Exception`)
4. **type_hint_drift**: 418 (INFO — missing type hints)
5. **logging_fstring**: 404 (INFO — f-strings in logging calls)
6. **rust_panic_risk**: 340 (INFO — Rust panic!() calls)
7. **rust_debug_print**: 238 (INFO — println! in Rust)
8. **rust_clone_in_loop**: 190 (INFO — .clone() in loops)
9. **ts_missing_return_type**: 87 (INFO — TypeScript functions without return types)
10. **go_debug_print**: 63 (INFO — fmt.Println in Go)

### ERROR-level (2):
- `core/memory/akashic.py:113` — `_save_field` structural stub
- `core/consciousness/continuous_audit.py:258` — `_fix_issue` structural stub

### WARNING-level (103):
- **19 shadowed_builtin** — functions named `set`, `list`, `map`, `filter`, `open`, `id` shadowing Python builtins
- **7 go_ignored_marshal** — unchecked json.Marshal errors in Go
- **6 shell_hardcoded_path** — `~` in echo statements (cosmetic, not functional)
- **6 rust_unsafe** — unsafe blocks in Rust
- **5 orphan_module** — modules without clear ownership
- **3 compat_shim** — intentional no-ops (already allowlisted)
- **2 hardcoded_path_pattern** — hardcoded paths in Python
- **1 zig_bare_panic** — bare @panic() in Zig
- **1 js_eval** — eval() in JavaScript
- **1 rust_panic_macro** — panic! macro in Rust
- **1 intentional_noop** — title_generator stub

## 4. Ruff — 622 findings (active source only)

### High-value findings (F841/F401 — 12 total):
- 4 unused local variables (`F841`)
- 4 unused imports (`F401`)
- 1 unused import in fast_write.py (our change — `os` no longer needed)
- 1 unused import in homeostatic_loop.py (ConsciousnessDepthGauge)
- 1 unused import in strata/__init__.py (checkers)
- 1 unused import in dream_commands.py (Markdown)

### Bulk findings:
- ~300 `I001` (import sorting) — auto-fixable with `ruff --fix`
- ~200 `BLE001` (broad exception) — existing pattern, low priority
- ~100 `W293` (whitespace) — auto-fixable

## Priority Action Items

### P0 — Fix now (real issues):
1. Fix `fast_write.py:24` unused `os` import (our regression)
2. Fix 2 STRATA ERROR structural stubs (`akashic.py`, `continuous_audit.py`)
3. Fix 4 ruff F401 unused imports
4. Fix 4 ruff F841 unused variables

### P1 — Address soon (code quality):
5. Add allowlist entries for 8 real stubs in STUB_REGISTRY.md
6. Fix 19 shadowed_builtin warnings (rename `set` → `set_value`, etc.)
7. Fix 7 Go ignored marshal errors
8. Deduplicate `_connect_to_gan_ying()` (6 copies → 1 shared utility)
9. Deduplicate `_emit()` pattern (5 copies → 1 shared utility)
10. Deduplicate `_run_async()` pattern (4 copies → 1 shared utility)

### P2 — Technical debt cleanup:
11. Consolidate 3 I Ching singletons into one canonical module
12. Extract singleton `__new__()` pattern into shared decorator
13. Auto-fix ~300 I001 import sorting issues with `ruff --fix`
14. Auto-fix ~100 W293 whitespace issues with `ruff --fix`
15. Address 789 dead_code findings (remove or wire up unused functions)

### P3 — Long-term:
16. Reduce 573 broad_except patterns (narrow exception types)
17. Add type hints for 418 type_hint_drift findings
18. Fix 404 logging_fstring issues (convert to %s format)
19. Address Rust/Go/Zig/TS/JS findings in polyglot code
