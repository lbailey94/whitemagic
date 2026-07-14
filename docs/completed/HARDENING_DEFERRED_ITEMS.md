# Hardening Deferred Items — Resolution Plan

**Created**: 2026-07-14
**Context**: Follow-up from `docs/completed/CODEBASE_HARDENING_STRATEGY.md`
**Last Updated**: 2026-07-14
**Status**: ✅ All actionable items complete. Items 1 & 3 deferred with justification. Ready for archival.

---

## 1. Stateless Singleton Conversion (282 candidates)

**What**: 282 singleton getter functions wrap classes with no `self._*` mutable state. The singleton pattern adds overhead (global variable, None-check, lock) without value when the underlying class is stateless.

**Why deferred**: Converting each singleton to module-level functions requires updating every call site. The 282 candidates span ~200 files with potentially thousands of call sites. High regression risk for cosmetic benefit.

**Resolution steps**:
1. Run the audit script (Appendix A.2 in the archived strategy) to get the full list with file/func/class triples.
2. For each candidate, grep for call sites: `grep -rn "get_<func>()" core/whitemagic/ --include="*.py"`.
3. Convert the class to module-level functions (or `@staticmethod` on the class, keeping the class as a namespace).
4. Replace `get_<func>().method(args)` call sites with `<module>.method(args)` or `<Class>.method(args)`.
5. Delete the singleton getter and its global variable.
6. Run full test suite after each batch of 10-20 conversions.

**Priority**: Low. Current singletons work correctly; this is a code cleanliness improvement.

**Estimated effort**: 4-6 hours (mechanical but tedious, needs careful call-site updates).

**Status**: Deferred. No developer confusion reported. The 282 stateless singletons are harmless overhead (a None-check + lock per call, ~50ns). Recommend revisiting only if profiling shows singleton overhead as a bottleneck or if the codebase is being prepared for external contributors who may find the pattern confusing.

**Note**: 7 new `threading.Lock()` calls were found in v24.3.x code (koka_batch_client, session_recorder, corpus_callosum, pattern_engine, zodiac_ledger, speculative_decoder, local_embedder). These were converted to `threading.RLock()` as part of this hardening pass, maintaining the Phase 5 gate of 0 `threading.Lock()` in production code. Final count: 0 `threading.Lock()`, 360 `threading.RLock()`, 7 `asyncio.Lock()` (async, not threading).

---

## 2. Remaining `except: pass` Without Logger (140 blocks)

**What**: 140 `except: pass` blocks remain in files that don't have `logger` defined. These couldn't be auto-fixed by the batch script that added `logger.debug()` to the other 430 blocks.

**Why deferred**: Each file needs `import logging` + `logger = logging.getLogger(__name__)` added before the `except: pass` can be replaced with `logger.debug(...)`. The batch script only touched files that already had logger.

**Resolution steps**:
1. Re-run the AST scanner to get the exact 140 file/line list.
2. For each file without `import logging`:
   - Add `import logging` to imports.
   - Add `logger = logging.getLogger(__name__)` after imports.
   - Replace `pass` with `logger.debug("Ignored <ExceptionType> in <file>:<line>")`.
3. Verify with: `grep -rn "except.*:" core/whitemagic/ --include="*.py" -A1 | grep "pass$" | wc -l` — target 0.

**Priority**: Medium. Silent error swallowing hides bugs. The remaining 140 are a mix of `except Exception: pass` (high risk) and `except KeyError: pass` (low risk).

**Estimated effort**: 1-2 hours (semi-automated, same script pattern as Phase 2 but with import injection).

**Status**: ✅ **Complete** (2026-07-14). All 140 `except: pass` blocks resolved.

### Execution Results

- **Script**: `scripts/fix_except_pass.py` — AST-based scanner that:
  1. Finds all `except: pass` blocks (inline and multiline, including `pass  # comment` patterns)
  2. Adds `import logging` after the last import in the file (using AST for correct insertion point)
  3. Adds `logger = logging.getLogger(__name__)` after all imports, before first real statement
  4. Replaces `pass` with `logger.debug("Ignored <ExceptionType> in <file>:<line>")`
  5. Converts bare `except:` to `except Exception:` before adding logging

- **Files modified**: 68 files across `core/whitemagic/`
- **Blocks fixed**: 140 total (77 in files without logger + 63 in files that already had logger)
- **Remaining `except: pass` blocks**: **0** (verified via AST scan)
- **Bare `except:` clauses**: **0** (all converted to `except Exception:`)

### Test Impact

- **Before changes**: 105 failures, 6721 passed (baseline with pre-existing issues)
- **After changes**: 26 failures, 6878 passed
- **Net effect**: +157 tests passing, -79 failures (adding `import logging` to 42 files resolved import errors that were causing pre-existing test failures)
- **New regressions**: 0
- **All 26 remaining failures are pre-existing** (dream cycle phase count, sensorium keys, LlamaCpp backend, security checker registration, path hygiene, forecasting, etc.)

### Verification

```bash
# Verify zero except:pass blocks remain
python -c "
import ast; from pathlib import Path
root = Path('core/whitemagic')
total = sum(1 for py in root.rglob('*.py')
            if '__pycache__' not in str(py) and '_archived' not in str(py)
            for node in ast.walk(ast.parse(py.read_text()))
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.body, list) and len(node.body) == 1
            and isinstance(node.body[0], ast.Pass))
print(f'except:pass blocks: {total}')  # Should print 0
"
```

---

## 3. Naming Clarity (Phase 7)

**What**: 6 basenames have 5+ copies across different packages: `registry.py` (6), `manager.py` (6), `sandbox.py` (5), `galaxy.py` (5), `core.py` (5), `base.py` (5).

**Why deferred**: Python's import system handles disambiguation via package paths. The duplication only causes confusion in grep/search results, not at runtime. The strategy document explicitly recommended deferring unless developer confusion is reported.

**Resolution steps**:
1. For each duplicated basename, evaluate whether the files serve genuinely different purposes (most do).
2. For ambiguous cases, rename with domain-specific prefixes (e.g., `shelter_manager.py`, `galaxy_router.py`, `security_isolation.py`).
3. Update all import paths.
4. Do NOT rename files in clearly different namespaces (e.g., `tools/handlers/galaxy.py` vs `core/memory/galaxy.py` — unambiguous in context).

**Priority**: Low. Cosmetic. No functional impact.

**Estimated effort**: 2-3 hours if pursued (mostly import path updates).

**Status**: Deferred. No developer confusion reported. All 6 duplicated basenames serve genuinely different purposes in clearly different namespaces. Python's import system handles disambiguation via package paths. Renaming would break imports across the codebase for cosmetic grep clarity only. Recommend revisiting if external contributors report confusion.

---

## Verification Command

After addressing any of these items, run:

```bash
cd core && source ../.venv/bin/activate && python -m pytest tests/ \
  --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive \
  --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc \
  --ignore=tests/verify -q --timeout=30
```

**Gate**: 0 new failures.

---

## Final Verification (2026-07-14)

```
Phase 2: except:pass resolution
  except:pass blocks:  0  (target: 0)
  bare except: clauses: 0  (target: 0)

Phase 5: Thread lock safety
  threading.Lock():  0  (target: 0)
  threading.RLock(): 360
  asyncio.Lock():    7  (OK — async, not threading)

Phase 3: Singleton triage → Deferred (282 stateless, low priority)
Phase 7: Naming clarity → Deferred (6 basenames, cosmetic)

Overall: ✅ ALL CHECKS PASS
```

**Test results**: 6878 passed, 26 pre-existing failures, 0 new regressions.
**Files modified**: 75 files (68 for except:pass, 7 for Lock→RLock).
**Script**: `scripts/fix_except_pass.py` (reusable for future regressions).
