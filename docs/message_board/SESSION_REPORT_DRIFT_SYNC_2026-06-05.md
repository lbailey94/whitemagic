# Session Report — Drift Sync & Test Hardening (2026-06-05)

**Date**: 2026-06-05  
**Scope**: Fix all remaining test failures, warnings, and prescience/data drift across repo and desktop site.  
**Baseline**: 2,378 passed, 1 skipped, 0 failed (start) → **2,422 passed, 1 skipped, 0 failed** (end)

---

## 1. Test Failures Fixed (2 → 0)

| File | Issue | Fix |
|------|-------|-----|
| `galaxy_api.py` | `HTTPException = None` when FastAPI unavailable caused `TypeError: 'NoneType' object is not callable` | Added `_GalaxyAPIError` fallback class with `status_code`/`detail` attrs |
| `test_galaxy_api.py` | Both security tests (`test_require_api_key_blocks_missing`, `test_require_api_key_rejects_invalid`) failing | Tests now pass with proper fallback exception |

## 2. Warnings Fixed

| File | Warning | Fix |
|------|---------|-----|
| `continuous_executor.py` | `RuntimeWarning: coroutine 'UnifiedNervousSystem.start' was never awaited` | Added `inspect.iscoroutinefunction()` check before sync call |
| `dream_cycle.py` | `DeprecationWarning: old harmony_vector import path` | Updated import to `whitemagic.harmony.vector` |
| `maturity_gates.py` | `DeprecationWarning: get_temporal_scheduler()` + false "operational" gate | Replaced with `GanYingBus` readiness check via `get_bus()` |
| `gnosis.py` | `DeprecationWarning` + latent `AttributeError` (`None.get_stats()`) | Replaced `_temporal_portal()` with safe `get_bus()` fallback |
| `gardens/grief/__init__.py` | `DeprecationWarning: init_listeners() is deprecated` | Removed no-op call (GanYingMixin already wires the bus) |
| `pyproject.toml` | Hypothesis `UserWarning` about `.hypothesis` dir | Added `.hypothesis` to `norecursedirs` |
| `pyproject.toml` | anyio `ResourceWarning` leaks | Added `ResourceWarning` filter for `anyio.streams.memory` |

## 3. Prescience Pipeline Fix (Root Cause of Claim Count Drift)

**Problem**: `seed_validated_claims()` was **append-only** — it inserted new claims by `source_ref` but never updated existing rows when the YAML source changed. The DB held 17 `validated` while the YAML claimed 21 because 4 claims had been upgraded from `pending` → `validated` in the YAML without the DB ever learning about it.

**Fix in `temporal_db.py`**:
- Replaced append-only seeding with a **full sync**: inserts new, updates existing, removes stale
- Added schema migration for `behavioral_confidence` column on existing DBs
- Changed return type from `int` → `dict[str, int]` (`{"inserted": N, "updated": N, "removed": N}`)
- YAML is now the single source of truth; second call updates all rows unconditionally

**Regenerated artifacts**:
- `core/apps/site/public/api/prescience.json` → synced to repo
- `~/Desktop/whitemagic-site/public/api/prescience.json` → copied from repo

**Updated YAML header**:
- Date: 2026-05-29 → **2026-06-05**
- Verified counts: **21 validated | 2 pending | 1 expired | 523 points | 25.0 week avg**

## 4. Doc Drift Baseline Updated

- `check_doc_drift.py` current audit baseline: **2,379 → 2,422**
- All 9 canonical test-count references now use Option C correctly

## 5. Canonical Docs Updated (4 files)

Updated current audit baseline from 2,379 → **2,422** with date **2026-06-05**:
- `README.md`
- `AGENTS.md`
- `AI_PRIMARY.md`
- `SYSTEM_MAP.md`

## 6. Test Updates

- `tests/unit/test_forecasting.py`: Updated to match new `seed_validated_claims()` dict return type and sync behavior

---

## Verification

| Check | Result |
|-------|--------|
| Full test suite | **2,422 passed, 1 skipped, 0 failed** |
| Doc drift (`check_doc_drift.py`) | **9/9 passed** |
| Version check (`check_versions.py`) | **Passed** |
| Prescience JSON output | 24 claims, 21 validated, 523 points, Brier 0.0958 / Index 69.0% |

---

## Remaining

One shutdown artifact outside our control: redis async `__del__` `AttributeError` after event loop teardown — known `redis-py` issue, not a test failure.

---

*Session led by Cascade. All changes verified with full test suite and doc drift checks.*
