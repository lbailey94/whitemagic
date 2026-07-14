# Deferred Security Objectives — G10, G11, G12

**Date**: 2026-07-14
**Completed**: 2026-07-14
**Status**: ✅ Complete — all 3 gaps implemented, 37 new tests, 0 regressions. Archived to `docs/completed/`.
**Context**: These 3 gaps from the Security Capabilities Assessment were not addressed in the 8-phase integration strategy because they are operational/workflow improvements rather than security integration gaps. All 3 have now been implemented.

---

## G10: FixGenerator → ContestPipeline Integration

**Problem**: `FixGenerator` can generate fixes and create PRs, but doesn't feed back into `ContestPipeline` for tracking. Fix status and bounty claim management are disconnected.

**Current state**:
- `fix_generator.py` (`/core/whitemagic/tools/security/fix_generator.py`) — generates `FixSuggestion` objects, applies fixes, creates GitHub PRs via `gh` CLI, tracks bounty earnings via `track_bounty_earnings()`.
- `contest_pipeline.py` (`/core/whitemagic/tools/security/contest_pipeline.py`) — formats findings for C4/Sherlock/CodeHawks, deduplicates, tracks submission status.
- Both are singletons (`get_contest_pipeline()`, module-level functions in fix_generator).
- **The gap**: No shared state. When a fix is applied and a PR created, the contest pipeline doesn't know. When a contest submission is formatted, the fix generator doesn't know which findings already have fixes.

**Implementation plan** (~0.5 session):
1. Add `fix_status` field to `ContestFinding` (none/pending/applied/pr_created/merged).
2. Add `link_fix(finding_id, fix: FixSuggestion)` method to `ContestPipeline`.
3. Add `link_pr(finding_id, pr_url: str)` method to `ContestPipeline`.
4. Modify `handle_fix_apply()` and `handle_pr_create()` handlers to call `link_fix`/`link_pr` on the contest pipeline.
5. Add `fix_coverage_report()` to `ContestPipeline` — shows which findings have fixes, which don't.
6. Tests: verify fix linking, PR linking, coverage report, status transitions.

**Key files to modify**:
- `core/whitemagic/tools/security/contest_pipeline.py`
- `core/whitemagic/tools/handlers/security_tools.py` (handlers)
- `core/tests/unit/tools/test_security_gap_fill.py` (tests)

---

## G11: ReportScraper Rate Limiting & Politeness

**Problem**: `ReportScraper` scrapes C4/Sherlock/CodeHawks with no rate limiting, robots.txt checking, or caching. Risk of IP bans and redundant scraping.

**Current state**:
- `report_scraper.py` (`/core/whitemagic/tools/security/report_scraper.py`) — 3 platforms, `scrape_url()` does a raw `requests.get()` with 30s timeout and a User-Agent header. No delay between requests, no robots.txt check, no response caching.
- `scrape_to_knowledge_base()` ingests findings into VulnKB.

**Implementation plan** (~0.5 session):
1. Add `RateLimiter` class (token bucket, 1 request per 2s default, configurable per platform).
2. Add `robots.txt` check in `scrape_url()` — fetch and parse `robots.txt` for each platform's base URL, cache for 1h. Skip URLs disallowed for our User-Agent.
3. Add response caching — hash URL to filename, store in `$WM_STATE_ROOT/scraper_cache/`. TTL 6h (configurable). Skip fetch if cached response exists and is fresh.
4. Add `politeness_delay` between requests to same domain (exponential backoff on 429/503).
5. Add `scrape_batch(urls)` method that respects rate limits across the batch.
6. Tests: rate limiting, robots.txt compliance, cache hit/miss, batch scraping, backoff on 429.

**Key files to modify**:
- `core/whitemagic/tools/security/report_scraper.py`
- `core/tests/unit/tools/test_security_gap_fill.py` (TestReportScraper class)

---

## G12: STRATA Secrets Scanning Expansion

**Problem**: `python_security.py` checker scans for hardcoded secrets but the checker name and category imply Python-only. However, looking at the actual code, `check_python_secrets` already scans `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.yaml`, `.yml`, `.env`, `.json`, `.toml`, `.cfg`, `.ini` files. The gap is more nuanced:

1. The checker name (`check_python_secrets`) and category (`py_hardcoded_secret`) are misleading — it's not Python-only.
2. No `.env` file-specific patterns (e.g., `KEY=value` without quotes).
3. No `.properties` file support (Java/Spring configs).
4. No `.xml` file support (Spring configs, Maven POMs).
5. No `.sh`/`.bash` script support (export KEY=value).
6. Missing patterns: Stripe (`sk_live_`), Twilio (`SK...`), SendGrid (`SG.`), generic bearer tokens.

**Current state**:
- `python_security.py` (`/core/whitemagic/tools/strata/checkers/python_security.py`) — 10 secret patterns, scans 12 file extensions, skips comments and test/dummy/example values.
- `diff_analyzer.py` has a separate `_check_hardcoded_secrets()` with 4 patterns (subset of the above).

**Implementation plan** (~0.5 session):
1. Rename checker to `check_hardcoded_secrets` (keep `check_python_secrets` as alias for backward compat).
2. Add `.properties`, `.xml`, `.sh`, `.bash`, `.zsh` to `files_by_extension()` call.
3. Add unquoted `KEY=value` pattern for `.env` and `.sh` files (e.g., `API_KEY=abc123notquoted`).
4. Add new patterns: Stripe (`sk_live_[A-Za-z0-9]{24}`), Twilio (`SK[0-9a-fA-F]{32}`), SendGrid (`SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}`), generic bearer (`Bearer [A-Za-z0-9_\-\.]{20,}`), Cloudflare (`v1\.0-[A-Za-z0-9_\-]{40,}`).
5. Update category from `py_hardcoded_secret` to `hardcoded_secret` (keep old category as alias).
6. Tests: new file types, new patterns, no false positives on test/example values.

**Key files to modify**:
- `core/whitemagic/tools/strata/checkers/python_security.py`
- `core/whitemagic/tools/strata/diff_analyzer.py` (sync patterns)
- `core/tests/unit/tools/test_strata.py` or similar (tests)

---

## Summary

| Gap | Effort | Priority | Type | Status |
|-----|--------|----------|------|--------|
| G10 | 0.5 session | Low | Workflow integration | ✅ Complete (10 tests) |
| G11 | 0.5 session | Low | Operational improvement | ✅ Complete (11 tests) |
| G12 | 0.5 session | Low | Checker expansion | ✅ Complete (16 tests) |

Total: ~1.5 sessions. All three are self-contained, low-risk changes that don't touch the security pipeline or middleware. Can be done independently or as a batch.

---

## Execution Results

**Date**: 2026-07-14
**Tests**: 37 new tests (10 G10 + 11 G11 + 16 G12), 81 total in `test_security_gap_fill.py`, 0 regressions.
**Files modified**:
- `core/whitemagic/tools/security/contest_pipeline.py` — `fix_status` field, `link_fix()`, `link_pr()`, `fix_coverage_report()`, `status()` updated
- `core/whitemagic/tools/handlers/security_tools.py` — `handle_fix_apply` and `handle_pr_create` wired to contest pipeline
- `core/whitemagic/tools/security/report_scraper.py` — `RateLimiter`, `robots.txt` check, response caching, exponential backoff, `scrape_batch()`
- `core/whitemagic/tools/strata/checkers/python_security.py` — Renamed to `check_hardcoded_secrets`, 5 new patterns, 5 new file extensions, unquoted secret detection
- `core/whitemagic/tools/strata/diff_analyzer.py` — Synced secret patterns (5 new patterns added)
- `core/tests/unit/tools/test_security_gap_fill.py` — 37 new tests across 3 test classes
