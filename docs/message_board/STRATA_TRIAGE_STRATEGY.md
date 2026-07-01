# STRATA Triage Strategy — 2026-06-30

## Context

We ran aislop, desloppify, and slopsentinel against both repos. Key findings:
- aislop score: 4/100 (both repos) — dominated by trivial comments and swallowed exceptions
- desloppify strict score: 20.3/100 — objective score 81.2% (mechanical only)
- slopsentinel score: 0/100 — dominant fingerprints: copilot, claude
- Security: 100/100 across all tools

**Decision**: Instead of relying on external tools (which broke noqa: F401 imports
3 times), we upgraded STRATA with 10 new checkers to detect all the same patterns
in-house. STRATA now finds 11,191 findings across 59 categories.

## New STRATA Checkers Added (10)

| Checker | Category | Findings | Auto-fixable? |
|---------|----------|----------|---------------|
| `trivial_comments.py` | trivial_comment | 1,970 | Yes (comment removal) |
| `swallowed_exception.py` | swallowed_exception | 1,275 | Manual (add logging) |
| `print_debug.py` | print_debug | 922 | Yes (→ logger) |
| `complexity.py` | function_too_long | 1,156 | Manual (refactor) |
| `complexity.py` | file_too_large | 176 | Manual (split) |
| `complexity.py` | deep_nesting | 174 | Manual (refactor) |
| `complexity.py` | too_many_params | 64 | Manual (config object) |
| `narrative_comments.py` | narrative_comment | 255 | Yes (comment removal) |
| `narrative_comments.py` | meta_comment | 4 | Yes (comment removal) |
| `thin_wrapper.py` | thin_wrapper | 57 | Manual (inline or add logic) |
| `hardcoded_url.py` | hardcoded_url | 35 | Manual (→ config) |
| `range_len_loop.py` | range_len_loop | 22 | Yes (→ enumerate) |
| `isinstance_ladder.py` | isinstance_ladder | 13 | Manual (→ handler map) |
| `mutable_default.py` | mutable_default | 0 | Yes (→ None default) |
| `silent_recovery.py` | silent_recovery | 8 | Manual (add exc var to log) |

## Triage Tiers

### Tier 1: Auto-fixable (batch processing, low risk)

These can be fixed mechanically with scripts or STRATA's own fix mode:

1. **trivial_comment (1,970)** — Remove comments that restate code
2. **print_debug (922)** — Replace `print(...)` with `logger.debug(...)` or remove
3. **narrative_comment (255)** — Remove decorative separators and step markers
4. **meta_comment (4)** — Remove AI-agent meta comments
5. **range_len_loop (22)** — Convert to `for item in x:` or `for i, item in enumerate(x):`
6. **mutable_default (0)** — Convert `def f(x=[])` to `def f(x=None)` + `if x is None: x = []`

**Estimated impact**: 3,173 findings eliminated
**Risk**: Low — comment removal and print→logger are behavior-preserving
**Approach**: Write a STRATA fix mode that applies these automatically

### Tier 2: Semi-automated (pattern-based, medium risk)

These require judgment but follow clear patterns:

7. **swallowed_exception (1,275)** — Add `logger.exception(...)` to empty catch blocks
   - Many are intentional (graceful degradation) — need to triage which are real
   - Filter: skip handlers that set feature flags or return defaults
8. **silent_recovery (8)** — Add exception variable to log messages
   - Simple: add `exc_info=True` or include `%s` with the exception
9. **hardcoded_url (35)** — Move to config
   - Most are in API client modules — centralize URL config

**Estimated impact**: 1,318 findings addressed
**Risk**: Medium — need to verify each swallowed exception is truly a bug
**Approach**: Manual triage with STRATA findings as guide

### Tier 3: Manual refactoring (high effort, high value)

These require real engineering work:

10. **function_too_long (1,156)** — Extract helper functions
    - Focus on functions > 100 lines first (highest impact)
11. **deep_nesting (174)** — Flatten with early returns or extract helpers
12. **file_too_large (176)** — Split into smaller modules
    - Focus on files > 1000 lines first
13. **too_many_params (64)** — Group into config objects/dataclasses
14. **thin_wrapper (57)** — Inline or add meaningful logic
15. **isinstance_ladder (13)** — Convert to handler maps

**Estimated impact**: 1,640 findings addressed
**Risk**: Higher — refactoring can introduce bugs
**Approach**: File-by-file, one module at a time, with tests as guardrail

### Tier 4: Existing findings (already tracked)

These were already in STRATA before the new checkers:

16. **copy_paste (1,605)** — Duplicate code detection
17. **dead_code (805)** — Unreachable code
18. **broad_except (628)** — Overly broad exception handlers
19. **type_hint_drift (422)** — Missing type hints on public APIs
20. **logging_fstring (225)** — f-strings in logging calls
21. **fstring_no_placeholder (109)** — f-strings without interpolation
22. **unused_import (33)** — Imports not referenced
23. **repetitive_dispatch (11)** — if/elif ladders → table lookups
24. **equality_comparison (7)** — == True/False/None → is/is not
25. **chained_get (4)** — .get().get() fallback chains

**Approach**: Continue existing desloppification pass

## Execution Plan

### Phase 1: STRATA Fix Mode (automated)
- Add `Strata.fix()` method that applies Tier 1 fixes automatically
- Run on both repos
- Verify with test suite
- Commit

### Phase 2: Swallowed Exception Triage
- Export all swallowed_exception findings to a report
- Categorize: real bug vs intentional graceful degradation
- Fix real bugs with `logger.exception(...)` or re-raise
- Suppress intentional ones with `# strata: ignore swallowed_exception`

### Phase 3: Complexity Reduction
- Start with the 10 largest files
- Extract helper functions from the 10 longest functions
- Flatten deep nesting in the 10 most nested functions
- One commit per file, tests must pass

### Phase 4: Structural Fixes
- Convert isinstance ladders to handler maps
- Inline thin wrappers or add meaningful logic
- Move hardcoded URLs to config
- Fix range-len loops

### Phase 5: Polish
- Fix remaining logging_fstring findings
- Fix remaining fstring_no_placeholder findings
- Clean up unused imports
- Verify equality_comparison and chained_get findings

## Score Targets

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| aislop score | 4/100 | 70+ | Tier 1+2 fixes |
| desloppify strict | 20.3 | 85+ | All tiers |
| desloppify objective | 81.2 | 95+ | Tier 1+2 |
| STRATA findings | 11,191 | <500 | All tiers |
| Security | 100 | 100 | Maintain |

## Key Lesson

**Never use aislop fix --safe again.** It removes `# noqa: F401` side-effect
imports despite them being explicitly marked. This caused regressions 3 times
across 2 sessions. STRATA's own checkers respect noqa comments and understand
the WhiteMagic codebase patterns (graceful degradation, dispatch envelopes,
optional imports).
