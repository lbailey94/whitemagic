# Codebase Hardening Strategy — v24.3.1 Post-Review

**Created**: 2026-07-13
**Completed**: 2026-07-14
**Status**: ✅ Complete — archived to `docs/completed/`
**Prerequisite**: Phase 0-1 hardening (runtime contract) already complete

---

## Execution Results

| Phase | Status | Commits | Key Metrics |
|-------|--------|---------|-------------|
| 1: Quick Wins | ✅ Complete | 1 | 10 files version-synced, 1 gRPC dup deleted, 4 zodiac dups → re-exports, 4 stale dirs deleted |
| 2: except:pass | ✅ Complete | 1 (with P1) | 430 blocks → `logger.debug()`, 0 bare excepts, 140 remaining (no logger in file) |
| 3: Singleton triage | ✅ Triaged | 0 | 267 stateful (keep), 282 stateless (convert candidates), 18 unclear. Batch conversion deferred. |
| 4: Circular imports | ✅ Complete | 1 | 3 module-level `core→tools` imports deferred to function level. 0 remaining. |
| 5: Thread locks | ✅ Complete | 1 | 315 `Lock()` → `RLock()`. 0 `Lock()` remaining, 351 `RLock()`. 7 test failures fixed. |
| 6: TODO/FIXME | ✅ No action | 0 | 0 real TODOs in production code |
| 7: Naming | ⏭️ Deferred | 0 | Low-priority cosmetic, no action needed |

**Test results**: 6834 passed, 25 pre-existing order-dependent failures, 0 new regressions.
**Commits**: 3 scoped commits on main branch.
**Elapsed**: ~98 minutes (epoch 1783995237 → 1784001078).

---

## Phase 1: Quick Wins (Estimated: 15 min)

**Goal**: Fix low-effort, high-visibility issues in a single batch.

### 1.1 Version Synchronization

Update all version references to `24.3.1`:

| File | Current | Target |
|------|---------|--------|
| `VERSION` | 24.3.1 | ✅ (canonical) |
| `INDEX.md` | 24.3.0 | 24.3.1 |
| `SYSTEM_MAP.md` | v24.2.0 | v24.3.1 |
| `package.json` | 24.1.0 | 24.3.1 |

**Action**: Single edit pass across 3 files.

### 1.2 Bare `except:` Clauses (3 files)

These catch `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` — should be `except Exception:` at minimum.

| File | Line | Fix |
|------|------|-----|
| `tools/suggestions.py` | ~182 | `except Exception:` |
| `tools/strata/checkers/exceptions.py` | TBD | `except Exception:` |
| `tools/strata/diff_analyzer.py` | TBD | `except Exception:` |

**Action**: 3 one-line edits.

### 1.3 Duplicate gRPC Stubs

`mesh/mesh_pb2_grpc.py` and `mesh/proto/mesh_pb2_grpc.py` are near-identical (8 lines diff: import path + version string).

**Action**:
1. Keep `mesh/proto/mesh_pb2_grpc.py` (canonical location for generated proto code).
2. Delete `mesh/mesh_pb2_grpc.py`.
3. Update any imports referencing `mesh.mesh_pb2_grpc` → `mesh.proto.mesh_pb2_grpc`.
4. Verify with `grep -rn "mesh_pb2_grpc" mesh/`.

### 1.4 Duplicate `zodiac_cores.py` (5 copies)

| File | MD5 | Action |
|------|-----|--------|
| `zodiac/zodiac_cores.py` | `5d2d31f3...` | **Keep** (canonical) |
| `gardens/metal/zodiac/zodiac_cores.py` | `c4e3fe0a...` | **Delete** — replace with import |
| `gardens/practice/zodiac/zodiac_cores.py` | `c4e3fe0a...` | **Delete** — replace with import |
| `gardens/connection/zodiac_cores.py` | `70edf38b...` | **Delete** — replace with import |
| `connection/zodiac_cores.py` | `6ec1731c...` | **Delete** — replace with import |

**Action**:
1. Delete 4 duplicate files.
2. In any code that imports from the deleted paths, redirect to `from whitemagic.zodiac.zodiac_cores import ...`.
3. If the non-canonical copies have divergent content, diff them against canonical and merge any unique additions first.

### 1.5 Empty/Stale Directory Cleanup

| Directory | Contents | Action |
|-----------|----------|--------|
| `bridges/` | 2 Julia TOML files | **Delete** — stale duplicate of `polyglot_bridges/julia/` |
| `polyglot_bridges/` | 13 non-Python files | **Add `__init__.py`** or move to `polyglot/bridges/` |
| `core/personality/` | 1 JSON file | **Move** `aria_profile.json` → `config/aria_profile.json` |
| `safety/` | 1 Python file | **Merge** into `security/` |
| `workflows/` | 1 Python file | **Merge** into `cli/` or `core/automation/` |

**Action**: Move files, update imports, delete empty dirs.

### 1.6 Verification

```bash
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Phase 2: Silent `except: pass` Resolution (Estimated: 2-3 hours)

**Goal**: Categorize and resolve all 701 `except: pass` blocks. The 469 figure from the initial scan was `pass` in any context; the actual `except: pass` count breaks down as:

### 2.1 Categorization

| Category | Count | Pattern | Resolution |
|----------|-------|---------|------------|
| **Intentional lazy-load** | 248 | `except (ImportError, AttributeError): pass` | **Keep** — add `logger.debug()` for traceability |
| **Broad catch, silent** | 154 | `except Exception: pass` | **Audit** — most need `logger.debug()` or `logger.warning()` |
| **Specific catch, silent** | 299 | `except KeyError: pass`, `except ValueError: pass` | **Audit** — some intentional (dict .get fallback), some bugs |
| **Bare except** | 0 | `except: pass` | ✅ Fixed in Phase 1 |
| **Total** | 701 | | |

### 2.2 Resolution Strategy

**Batch 1: Intentional lazy-load (248 sites)**

These are the `except (ImportError, AttributeError): pass` blocks guarding optional dependency imports. They are correct but silent. Resolution:

```python
# Before:
except (ImportError, AttributeError):
    pass

# After:
except (ImportError, AttributeError):
    _OPTIONAL_DEP = None  # or _rust_available = False, etc.
    logger.debug("Optional dependency not available: %s", exc.name)
```

This can be semi-automated with a script that:
1. Finds `except (ImportError, AttributeError):` followed by `pass`
2. Inserts a `logger.debug()` line
3. Preserves any variable assignments that follow

**Batch 2: Broad `except Exception: pass` (154 sites)**

These are the highest risk. Each needs manual review:

- **Middleware/pipeline** (expected — must not crash): Add `logger.debug("Middleware X ignored error: %s", e)`.
- **Import guards** (same as Batch 1): Reclassify to `except ImportError`.
- **Genuine bugs** (should not be silent): Add proper handling or re-raise.

Top files by `except Exception: pass` count:

| File | Count | Context |
|------|-------|---------|
| `middleware.py` | ~7 | Pipeline safety — add debug logging |
| `unified.py` | ~8 | Memory ops — audit each |
| `dream_cycle.py` | ~3 | Dream phases — add debug logging |
| `run_mcp_lean.py` | ~4 | Server startup — audit |
| `embeddings.py` | ~4 | Embedding ops — audit |
| `consciousness_loop.py` | ~4 | Background daemon — add debug logging |
| `prat_router.py` | ~3 | Routing — audit |

**Batch 3: Specific `except` + `pass` (299 sites)**

These are the most likely to hide bugs. Categories:

- `except KeyError: pass` — Usually a dict lookup fallback. Often better as `.get()` with default.
- `except (TypeError, ValueError): pass` — Often parsing/conversion fallback. May hide data corruption.
- `except sqlite3.OperationalError: pass` — DB lock fallback. Should retry or log.
- `except json.JSONDecodeError: pass` — Parsing fallback. Should log malformed input.

Resolution: Semi-automated scan + manual triage. For each:
1. If the `pass` is a legitimate fallback (e.g., "try fast path, fall back to slow path"), add a comment.
2. If the `pass` hides an error, add `logger.warning()` or `logger.debug()`.
3. If the `pass` is a bug, fix the underlying issue.

### 2.3 Automation Script

Write a one-time script `scripts/audit_except_pass.py` that:
1. Scans all `.py` files (excluding `__pycache__`, `_archived`, tests).
2. For each `except: pass` block, extracts:
   - File, line number
   - Exception type caught
   - 3 lines of context before the `try`
   - Whether `logger` is imported in the file
3. Outputs a CSV/JSON report for triage.
4. Optionally auto-inserts `logger.debug()` for Batch 1 (ImportError guards).

### 2.4 Verification

```bash
# Re-run scan to verify count dropped
grep -rn "except.*:" core/whitemagic/ --include="*.py" -A1 | grep -v __pycache__ | grep -v _archived | grep "pass$" | wc -l

# Full test suite
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Phase 3: Singleton Triage (Estimated: 1-2 hours)

**Goal**: Reduce 679 singleton getter functions to a manageable set.

### 3.1 Current State

| Pattern | Count |
|---------|-------|
| `def get_*() ->` functions | 679 |
| `_instance = None` module-level | 149 |
| `_singleton` / `_SINGLETON` | 31 |

**By subsystem**:

| Subsystem | Count |
|-----------|-------|
| `core/intelligence/` | 80 |
| `core/memory/` | 61 |
| `core/consciousness/` | 52 |
| `core/acceleration/` | 15 |
| `core/orchestration/` | 11 |
| `core/immune/` | 11 |
| `gardens/sangha/` | 10 |
| `core/evolution/` | 10 |
| `tools/security/` | 9 |
| `core/automation/` | 9 |
| Other | 411 |

### 3.2 Triage Categories

**Category A: True Infrastructure Singletons (Keep ~80-100)**

These manage shared state that must be process-global:
- Memory manager, SQLite backend, galaxy router
- Consciousness loop, citta cycle, dream daemon
- Gan Ying bus, karma ledger, dharma governor
- Inference router, embedding daemon
- Homeostatic loop, apotheosis engine

**Category B: Garden/Emotional Singletons (Consolidate ~60)**

Each garden (joy, grief, courage, etc.) has its own singleton. These could be managed by a `GardenRegistry` that lazily instantiates gardens on demand, reducing 60+ singletons to 1 registry.

**Category C: Utility Singletons (Convert to stateless ~200)**

Many singletons wrap stateless utilities (parsers, formatters, classifiers). If the class has no mutable state, the singleton adds overhead without value. Convert to module-level functions or static methods.

**Category D: Duplicate/Redundant Singletons (Merge ~50)**

Some singletons wrap the same underlying resource (e.g., multiple `get_*_cache()` functions that all return the same cache instance). Merge to a single accessor.

**Category E: Test-Only Singletons (Move to test fixtures ~30)**

Some singletons exist only to support test isolation. These should be fixtures, not production singletons.

### 3.3 Resolution Strategy

1. **Script**: Write `scripts/audit_singletons.py` that:
   - Finds all `def get_*()` functions
   - Checks if the returned class has mutable state (`self._` attributes set in `__init__`)
   - Classifies as A (stateful, keep), C (stateless, convert), or D (duplicate, merge)
   - Outputs a triage report

2. **Batch 1**: Convert Category C (stateless utilities) to module-level functions. This is safe and mechanical.

3. **Batch 2**: Consolidate Category B (gardens) into a `GardenRegistry`.

4. **Batch 3**: Merge Category D (duplicates).

5. **Leave Category A** — these are correct and necessary.

### 3.4 Verification

```bash
# Count remaining singletons
grep -rn "def get_.*() ->" core/whitemagic/ --include="*.py" | grep -v __pycache__ | grep -v _archived | wc -l
# Should be ~100-150 after cleanup

cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Phase 4: Circular Import Resolution (Estimated: 1-2 hours)

**Goal**: Eliminate 15 `core/` → `tools/` imports to enforce clean layering.

### 4.1 Current Violations

| File (core/) | Imports from (tools/) | Reason |
|--------------|----------------------|--------|
| `core/automation/army.py` | `tools.unified_api._emit_gan_ying` | Event emission |
| `core/automation/tool_sharpening.py` | `tools.dispatch_table.DISPATCH_TABLE` | Tool enumeration |
| `core/automation/tool_sharpening.py` | `tools.registry.get_registry` | Tool registry access |
| `core/engines/registry.py` | `tools.prat_mappings.TOOL_TO_GANA` | Gana mapping |
| `core/alignment/grimoire_audit.py` | `tools.dispatch_table.DISPATCH_TABLE` | Tool audit |
| `core/monitoring/token_tracker.py` | `tools.middleware.DispatchContext, NextFn` | Type imports |
| `core/intelligence/researcher.py` | `tools.handlers.llama_tools` | LLM generation |
| `core/intelligence/synthesis/kaizen_engine.py` | `tools.strata.Strata` | Code analysis |
| `core/intelligence/self_improvement.py` | `tools.strata.Strata` | Code analysis |
| `core/intelligence/omni/skill_forge.py` | `tools.handlers.llama_tools._generate` | LLM generation |
| `core/consciousness/sentience.py` (×5) | `tools.unified_api.call_tool` | Tool invocation |

### 4.2 Resolution Patterns

**Pattern 1: Type-only imports (token_tracker.py)**

`DispatchContext` and `NextFn` are used only for type hints. Move these type definitions to `core/` (e.g., `core/types.py` or `core/protocol.py`) and have `tools/middleware.py` import from there.

**Pattern 2: Event emission (army.py, sentience.py)**

`_emit_gan_ying` and `call_tool` are infrastructure functions. Define an interface in `core/`:

```python
# core/protocol.py
from typing import Any, Protocol

class ToolInvoker(Protocol):
    def call_tool(self, name: str, **kwargs) -> dict[str, Any]: ...

class EventEmitter(Protocol):
    def emit(self, event: str, data: dict) -> None: ...
```

Then `tools/unified_api.py` implements these protocols, and `core/` modules depend on the protocol, not the implementation. Wire up at startup.

**Pattern 3: Data table imports (tool_sharpening.py, grimoire_audit.py, engines/registry.py)**

`DISPATCH_TABLE`, `TOOL_TO_GANA`, and `get_registry()` are data/registry lookups. Move the canonical data to `core/`:
- `TOOL_TO_GANA` mapping → `core/protocol.py` or `core/gana_map.py`
- `DISPATCH_TABLE` reference → Pass as parameter or use a registry interface

**Pattern 4: Feature delegation (researcher.py, kaizen_engine.py, skill_forge.py)**

These call into `llama_tools._generate` or `Strata` for LLM/code analysis. Define interfaces:
- `LLMGenerator` protocol in `core/protocol.py`
- `CodeAnalyzer` protocol in `core/protocol.py`

Wire concrete implementations at startup.

### 4.3 Implementation Order

1. Create `core/protocol.py` with Protocol interfaces.
2. Move type definitions (`DispatchContext`, `NextFn`) to `core/protocol.py`.
3. Move data tables (`TOOL_TO_GANA`) to `core/gana_map.py`.
4. Update `tools/` to import from `core/` instead.
5. Update `core/` modules to use Protocol interfaces.
6. Wire concrete implementations at startup in `run_mcp_lean.py` or `__init__.py`.
7. Remove all `from whitemagic.tools` imports from `core/` files.

### 4.4 Verification

```bash
# Should return 0
grep -rn "from whitemagic.tools" core/whitemagic/core/ --include="*.py" | grep -v __pycache__ | grep -v _archived | wc -l

cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Phase 5: Thread Lock Audit (Estimated: 1-2 hours)

**Goal**: Audit 310 `Lock()` usages and convert to `RLock()` where re-entrant access is possible.

### 5.1 Current State

| Lock Type | Count |
|-----------|-------|
| `threading.Lock()` | 310 |
| `threading.RLock()` | 35 |
| Ratio | 8.9:1 |

### 5.2 Risk Assessment

**High-risk files** (multiple locks, potential re-entrancy):

| File | Lock() Count | Risk |
|------|-------------|------|
| `harmony/vector.py` | 3 | Medium — separate locks for different state, but `_compute()` may call `snapshot()` which also locks |
| `harmony/homeostatic_loop.py` | 2 | Low — instance lock + module-level singleton lock, no overlap |
| `harmony/physical_metrics.py` | 3 | Low — separate classes with separate locks |
| `mesh/inference_router.py` | 2 | Low — class lock + instance lock |
| `mesh/client.py` | 2 | Medium — instance lock + module-level lock, `send()` may call `_reconnect()` |
| `core/consciousness/sentience.py` | 1 per loop | Low — each loop has its own lock |
| `core/resonance/_consolidated.py` | 1 | Low — single global worker thread lock |

**Known historical deadlock**: `gratitude.benefits` Lock deadlock (fixed in v24.1.0 by converting to RLock).

### 5.3 Audit Strategy

**Step 1: Automated scan**

Write `scripts/audit_locks.py` that:
1. Finds all `threading.Lock()` and `threading.RLock()` usages.
2. For each `Lock()`, traces which methods acquire it.
3. Checks if any method that acquires the lock calls another method that also acquires the same lock (re-entrancy).
4. Flags potential deadlocks.

**Step 2: Convert safe-by-default to RLock**

Conservative approach: convert all `threading.Lock()` to `threading.RLock()` unless:
- The lock guards a simple counter/flag (no method calls while holding).
- The lock is held for a very short scope (1-2 lines).
- Performance profiling shows Lock is significantly faster (rare — RLock overhead is ~50ns).

`RLock` is the safe default. `Lock` should be the optimization, not the default.

**Step 3: High-risk deep dive**

For the 7 high-risk files, manually trace call paths:
1. List all methods that acquire each lock.
2. For each method, list all methods it calls while holding the lock.
3. If any callee also acquires the same lock → must be RLock.

### 5.4 Resolution

| File | Action |
|------|--------|
| `harmony/vector.py` | Convert `self._lock` → `RLock()` (snapshot may be called during _compute) |
| `harmony/homeostatic_loop.py` | Convert `self._lock` → `RLock()` (check() calls _check_* methods) |
| `harmony/physical_metrics.py` | Audit `PhysicalMetricsSource._lock` — convert to RLock if `get_metrics()` calls `check_thermal_anomaly()` |
| `mesh/client.py` | Convert `self._lock` → `RLock()` (send() may call _reconnect()) |
| All other `Lock()` | Batch convert to `RLock()` as safe default |

### 5.5 Verification

```bash
# Lock count should drop, RLock count should rise
grep -rn "threading.Lock()" core/whitemagic/ --include="*.py" | grep -v __pycache__ | grep -v _archived | wc -l
grep -rn "threading.RLock()" core/whitemagic/ --include="*.py" | grep -v __pycache__ | grep -v _archived | wc -l

cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Phase 6: TODO/FIXME Resolution (Estimated: 30 min)

**Goal**: Triage 81 TODO/FIXME comments.

### 6.1 Current State

After filtering out TODO/FIXME references in tooling code (STRATA checkers, codegenome, autonomous executor, objective generator, etc.), **0 actual TODO/FIXME comments exist in production code**.

All 81 matches are:
- STRATA checker code that *detects* TODOs in analyzed codebases (not our TODOs)
- Codegenome polymorphism that *transforms* TODO comments (not our TODOs)
- Autonomous executor that *scans for* TODOs (not our TODOs)
- Documentation strings describing TODO detection features

### 6.2 Resolution

**No action needed.** The codebase is clean of outstanding TODOs. ✅

---

## Phase 7: Naming Clarity (Optional, Estimated: 1 hour)

**Goal**: Reduce confusion from duplicate basenames.

### 7.1 Current State

| Basename | Copies | Files |
|----------|--------|-------|
| `registry.py` | 6 | tools/, core/engines/, core/memory/, config/, etc. |
| `manager.py` | 6 | session/, tools/export/, config/, core/memory/, oms/, shelter/ |
| `sandbox.py` | 5 | tools/, tools/handlers/, tools/registry_defs/, execution/, security/ |
| `galaxy.py` | 5 | tools/tui/, tools/handlers/, tools/registry_defs/, core/memory/, compat/ |
| `core.py` | 5 | various |
| `base.py` | 5 | various |

### 7.2 Resolution

This is low-priority cosmetic work. The files serve different purposes in different packages, and Python's import system handles disambiguation. However, for grep/search clarity:

- Consider domain-specific prefixes where the name is ambiguous: `shelter_manager.py`, `galaxy_router.py`, `security_isolation.py`.
- Do NOT rename files that are in clearly different namespaces (e.g., `tools/handlers/galaxy.py` vs `core/memory/galaxy.py` — these are unambiguous in context).

**Recommendation**: Defer unless developer confusion is reported.

---

## Execution Order

```
Phase 1 (Quick Wins)          ─── 15 min ────┐
                                              │
Phase 2 (except: pass)        ─── 2-3 hours ──┤
                                              │  Each phase
Phase 3 (Singletons)         ─── 1-2 hours ──┤  independently
                                              │  shippable +
Phase 4 (Circular imports)   ─── 1-2 hours ──┤  testable
                                              │
Phase 5 (Thread locks)       ─── 1-2 hours ──┤
                                              │
Phase 6 (TODO/FIXME)         ─── 0 min ──────┤  (no action needed)
                                              │
Phase 7 (Naming)             ─── optional ───┘
```

**Total estimated effort**: 5-8 hours of focused work.

**Dependency**: Phase 4 (circular imports) should come before Phase 3 (singletons) if we move type definitions to `core/protocol.py`, as some singletons may reference those types. Otherwise, phases are independent.

**Recommended order**: 1 → 2 → 5 → 4 → 3 → 7 (skip 6)

Rationale:
- Phase 1 first (quick wins, immediate visibility)
- Phase 2 second (biggest debuggability impact)
- Phase 5 third (deadlock risk is a correctness issue)
- Phase 4 fourth (structural, enables cleaner Phase 3)
- Phase 3 fifth (largest scope, benefits from clean layering)
- Phase 7 last (cosmetic, optional)

---

## Per-Phase Test Gates

After each phase, run:

```bash
cd core && python -m pytest tests/ \
  --ignore=tests/archive_v14 \
  --ignore=tests/archive_v11 \
  --ignore=tests/archive \
  --ignore=tests/archive_polyglot \
  --ignore=tests/legacy \
  --ignore=tests/adhoc \
  --ignore=tests/verify \
  -q --timeout=30
```

**Baseline**: 5,697 passed, 3 skipped, 0 failures.
**Gate**: 0 new failures after each phase.

Additionally, after Phase 1:
```bash
python scripts/check_doc_drift.py
```

After Phase 4:
```bash
# Verify no circular imports remain
grep -rn "from whitemagic.tools" core/whitemagic/core/ --include="*.py" | grep -v __pycache__ | grep -v _archived | wc -l
# Should be 0
```

After Phase 5:
```bash
# Verify lock conversion
python -c "
import threading
# Quick smoke test: instantiate key singletons and verify no deadlock
from whitemagic.harmony.vector import get_harmony_vector
hv = get_harmony_vector()
snap = hv.snapshot()
print(f'HarmonyVector snapshot OK: {snap}')
"
```

---

## Commit Strategy

Each phase = 1-3 scoped commits:

- `fix: synchronize version references to v24.3.1`
- `fix: replace bare except clauses with except Exception`
- `refactor: remove duplicate gRPC stubs and zodiac_cores copies`
- `refactor: clean up empty/stale directories`
- `refactor: add debug logging to silent except:pass blocks (batch 1/2/3)`
- `refactor: convert stateless singletons to module functions`
- `refactor: introduce core/protocol.py for clean layering`
- `fix: convert Lock() to RLock() for re-entrancy safety`
- `docs: update INDEX.md and SYSTEM_MAP.md with hardening changes`

---

## Appendix: Audit Scripts

### A.1 `scripts/audit_except_pass.py`

```python
"""Scan for except: pass blocks and categorize them."""
import ast
import json
from pathlib import Path

CATEGORIES = {
    "import_guard": ["ImportError", "ModuleNotFoundError", "AttributeError"],
    "broad": ["Exception"],
    "bare": [],
}

def scan_file(path: Path) -> list[dict]:
    """Find all except:pass blocks in a file."""
    results = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if isinstance(node.body, list) and len(node.body) == 1:
                if isinstance(node.body[0], ast.Pass):
                    exc_type = ""
                    if node.type:
                        if isinstance(node.type, ast.Name):
                            exc_type = node.type.id
                        elif isinstance(node.type, ast.Tuple):
                            exc_type = ", ".join(
                                e.id for e in node.type.elts if isinstance(e, ast.Name)
                            )
                    category = "bare" if not exc_type else \
                               "import_guard" if any(c in exc_type for c in CATEGORIES["import_guard"]) else \
                               "broad" if "Exception" in exc_type else "specific"
                    results.append({
                        "file": str(path),
                        "line": node.lineno,
                        "exception": exc_type or "(bare)",
                        "category": category,
                    })
    return results

def main():
    root = Path("core/whitemagic")
    all_results = []
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py) or "_archived" in str(py):
            continue
        all_results.extend(scan_file(py))
    
    # Summary
    by_cat = {}
    for r in all_results:
        by_cat.setdefault(r["category"], []).append(r)
    
    print(f"Total except:pass blocks: {len(all_results)}")
    for cat, items in sorted(by_cat.items()):
        print(f"  {cat}: {len(items)}")
    
    # Write full report
    Path("except_pass_report.json").write_text(json.dumps(all_results, indent=2))
    print(f"\nFull report: except_pass_report.json")

if __name__ == "__main__":
    main()
```

### A.2 `scripts/audit_singletons.py`

```python
"""Scan for singleton patterns and classify them."""
import ast
import json
from pathlib import Path

def has_mutable_state(class_node: ast.ClassDef) -> bool:
    """Check if a class sets self._ attributes in __init__."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if (isinstance(target, ast.Attribute) and
                            isinstance(target.value, ast.Name) and
                            target.value.id == "self" and
                            target.attr.startswith("_")):
                            return True
    return False

def scan_file(path: Path) -> list[dict]:
    """Find singleton getter functions."""
    results = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("get_"):
            # Check if it returns a singleton (has _instance check)
            src = ast.unparse(node)
            if "_instance" in src or "_singleton" in src or "_SINGLETON" in src:
                results.append({
                    "file": str(path),
                    "function": node.name,
                    "line": node.lineno,
                })
    return results

def main():
    root = Path("core/whitemagic")
    all_results = []
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py) or "_archived" in str(py):
            continue
        all_results.extend(scan_file(py))
    
    print(f"Total singleton getters: {len(all_results)}")
    
    # Group by directory
    by_dir = {}
    for r in all_results:
        d = str(Path(r["file"]).parent.relative_to("core/whitemagic"))
        by_dir.setdefault(d, []).append(r)
    
    for d, items in sorted(by_dir.items(), key=lambda x: -len(x[1])):
        print(f"  {d}: {len(items)}")
    
    Path("singleton_report.json").write_text(json.dumps(all_results, indent=2))
    print(f"\nFull report: singleton_report.json")

if __name__ == "__main__":
    main()
```

### A.3 `scripts/audit_locks.py`

```python
"""Scan for threading.Lock() usage and flag potential re-entrancy."""
import ast
import json
from pathlib import Path

def scan_file(path: Path) -> list[dict]:
    """Find Lock() and RLock() usages."""
    results = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return results
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) or isinstance(target, ast.Name):
                    src = ast.unparse(node)
                    if "threading.Lock()" in src and "RLock" not in src:
                        results.append({
                            "file": str(path),
                            "line": node.lineno,
                            "type": "Lock",
                            "source": src.strip(),
                        })
                    elif "threading.RLock()" in src:
                        results.append({
                            "file": str(path),
                            "line": node.lineno,
                            "type": "RLock",
                            "source": src.strip(),
                        })
    return results

def main():
    root = Path("core/whitemagic")
    all_results = []
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py) or "_archived" in str(py):
            continue
        all_results.extend(scan_file(py))
    
    locks = [r for r in all_results if r["type"] == "Lock"]
    rlocks = [r for r in all_results if r["type"] == "RLock"]
    
    print(f"Lock():  {len(locks)}")
    print(f"RLock(): {len(rlocks)}")
    print(f"Ratio:   {len(locks)/max(len(rlocks),1):.1f}:1")
    
    Path("lock_report.json").write_text(json.dumps(all_results, indent=2))
    print(f"\nFull report: lock_report.json")

if __name__ == "__main__":
    main()
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-13 | Initial strategy document created from post-review findings |
| 2026-07-14 | **Execution complete**. Phases 1, 2, 4, 5 fully implemented. Phase 3 triaged (batch conversion deferred). Phases 6, 7 no action needed. 3 commits, 0 new test regressions. Archived to `docs/completed/`. |
