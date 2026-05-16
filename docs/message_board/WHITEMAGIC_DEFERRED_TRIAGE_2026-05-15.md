# WhiteMagic Deferred Triage — Fragment + STRATA Audit

**Date**: 2026-05-15  
**Status**: Follow-up plan with first Rust-stub pass complete  
**Scope**: WhiteMagic only; derived from external Fragment and STRATA audits  
**Rule for next session**: Do not fix everything at once. Triage one remaining category at a time and run full verification after every change.

---

## 1. Executive Summary

WhiteMagic is currently healthy by its own gates, but the external Fragment + STRATA loop surfaced a useful deferred triage list.

Current verified WhiteMagic gates from this audit pass:

- **Core tests**: `2217 passed, 67 skipped, 1 warning in 34.18s`
- **Doc drift**: passed
- **Version check**: passed
- **Tool surface**: previously verified at `479 callable tools`, `451 dispatch entries`, `28 Gana meta-tools`

External audit results:

- **Fragment quick index**: `14,517 files`, `81,414 chunks`, `136.6 MB` source, `197.3 MB` index
- **STRATA broad findings**: `9,065 total`
  - `8,026 info`
  - `980 warning`
  - `59 error`
- **STRATA hardcoded path audit after pattern split**: `65 total`
  - `58 hardcoded_path`
  - `7 hardcoded_path_pattern`
  - `7 concrete path findings are in the allowed path resolver file: core/whitemagic/config/paths.py`
  - approximately `51 concrete hardcoded_path findings outside the allowed resolver file`

Interpretation:

- WhiteMagic remains functionally green.
- STRATA findings are a triage queue, not automatic failure criteria.
- Many findings are expected noise, historical scripts, security regexes, test scaffolds, or consciously allowlisted compatibility stubs.
- The highest-value next pass is precision triage: confirm which findings are real risks, then fix only validated issues.

First follow-up pass completed later on 2026-05-15:

- **Baseline before edit**: full core suite passed `2217 passed, 67 skipped, 1 warning`; doc drift passed; version check passed.
- **Rust stub cluster classified**:
  - `core/whitemagic-rust/src/bin/polyglot_scout.rs` — STRATA match was scanner text/string logic, not a runtime stub.
  - `core/whitemagic-rust/src/bin/consensus_council.rs` — STRATA match was proposal text, not a runtime stub.
  - `core/whitemagic-rust/src/memory/galactic_telepathy.rs` — real `unimplemented!()` panic existed in dormant FFI entrypoint.
- **Fix applied**: `create_telepathy_engine()` now returns `PyNotImplementedError` instead of panicking with `unimplemented!()`.
- **Post-fix verification**:
  - custom Rust macro scan found no real `todo!()` / `unimplemented!()` macros after stripping comments and string literals
  - `cargo check --all-targets` passed with existing warnings
  - `git diff --check` passed
  - doc drift passed
  - version check passed
  - full core suite passed `2217 passed, 67 skipped, 1 warning in 34.85s`
- **Deferred caveats**:
  - `cargo test` for `core/whitemagic-rust` currently fails at PyO3 test-link time due missing Python C symbols under the default extension-module feature; treat as Rust harness/config backlog, not as caused by the stub fix.
  - `rustfmt --check src/memory/galactic_telepathy.rs` still reports broad pre-existing formatting drift; do not mix a mechanical full-file format pass with semantic triage unless explicitly scoped.

---

## 2. Tools Used

### Fragment

External index path:

```text
/tmp/whitemagic-fragment-index
```

Fragment was used to retrieve evidence for:

- path hygiene policy
- stable envelope contract
- garden handlers and search surfaces
- structural stubs and allowlists
- live count references
- Rust stub hotspots

Useful command shape:

```bash
cargo run -- query /home/lucas/Desktop/WHITEMAGIC \
  --index /tmp/whitemagic-fragment-index \
  --format json \
  "query terms" \
  --top 5
```

### STRATA

STRATA was run externally from:

```text
/home/lucas/Desktop/DEFERRED PROJECTS (for now)/STRATA
```

Cache/state was redirected to `/tmp` where possible to avoid writing audit state into WhiteMagic.

The hardcoded path checker now separates:

- `hardcoded_path` — concrete runtime-ish paths
- `hardcoded_path_pattern` — regex/glob/path-pattern literals that often belong in scanners or security policies

---

## 3. Priority Triage Queue

### P0 — Preserve Baseline Before Fixing Anything

Before any WhiteMagic code changes in the next session:

```bash
cd /home/lucas/Desktop/WHITEMAGIC/core
PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python -m pytest tests/ \
  --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python scripts/check_doc_drift.py

PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python scripts/check_versions.py
```

Do not begin cleanup if the baseline is red.

---

## 4. High-Signal Findings to Review

### 4.1 Structural Stubs

STRATA reported `59` error-level findings. Not all are necessarily actionable, but these are high-signal starting points.

Observed hotspots:

```text
core/whitemagic-rust/src/memory/galactic_telepathy.rs
core/whitemagic-rust/src/bin/polyglot_scout.rs
core/whitemagic-rust/src/bin/consensus_council.rs
core/whitemagic/run_mcp.py
core/whitemagic/cli/*
core/whitemagic/core/memory/vector.py
core/whitemagic/core/memory/unified_types.py
core/whitemagic/core/memory/memory_matrix.py
core/whitemagic/core/intake/media_processor.py
```

Important context:

- `core/whitemagic/run_mcp.py` startup/shutdown stubs are present in `core/scripts/stub_allowlist.json`.
- Some CLI stubs may be intentional Typer command-group placeholders.
- Some abstract/base-class methods may be legitimate extension points.
- Rust `todo!()` / `unimplemented!()` macros in active crates deserve closer inspection because they can become runtime panics if code paths are reachable.

Recommended next-session approach:

1. Read `core/scripts/stub_allowlist.json`.
2. Compare every STRATA error against the allowlist.
3. Divide into:
   - intentional allowlisted placeholder
   - abstract/interface method
   - test scaffold
   - real runtime risk
4. Fix only real runtime risks.
5. Update allowlist only if justified by tests and documentation.

Suggested first target:

```text
DONE: core/whitemagic-rust/src/bin/polyglot_scout.rs
DONE: core/whitemagic-rust/src/bin/consensus_council.rs
DONE: core/whitemagic-rust/src/memory/galactic_telepathy.rs
```

Result: only `galactic_telepathy.rs` contained a real runtime macro panic. It was replaced with an explicit Python `NotImplementedError` return. The other two files contained string-literal references to stubs, not reachable stubs.

Remaining stub-triage work:

- Re-run or retrieve STRATA error-only output for the remaining Python-side findings.
- Classify `core/whitemagic/run_mcp.py` against `core/scripts/stub_allowlist.json`.
- Inspect CLI command-group placeholders before changing them; many may be intentional Typer/Click scaffolds.
- Inspect memory/intake files one at a time and fix only reachable runtime risks.

---

### 4.2 Path Hygiene

WhiteMagic policy from `AGENTS.md`:

```text
Never use Path.home() or .expanduser() outside core/whitemagic/config/paths.py.
All runtime state lives under WM_STATE_ROOT. Never write to the repo.
```

STRATA path summary after pattern split:

```text
total=65
hardcoded_path=58
hardcoded_path_pattern=7
```

Top concrete `hardcoded_path` files:

```text
7  core/whitemagic/config/paths.py
7  core/whitemagic/security/tool_gating.py
4  core/whitemagic/oms/__init__.py
2  core/eval_aux/locomo_v019_benchmark.py
2  core/scripts/backfill_embeddings.py
2  core/whitemagic/core/governor.py
2  core/whitemagic/core/fusions.py
2  core/whitemagic/tools/handlers/introspection.py
2  core/scripts/verification/check_path_hygiene.py
2  docs/reports/audit_history/unify_system.py
2  docs/reports/audit_history/constellation_scan.py
2  docs/reports/audit_history/ignite_emergence.py
2  docs/reports/audit_history/map_zodiac.py
2  polyglot/mojo/bench_final.py
2  polyglot/mojo/bench_compare.py
```

Top `hardcoded_path_pattern` files:

```text
2  core/whitemagic/tools/introspection.py
2  core/whitemagic/core/governor.py
1  core/haskell/haskell_bridge.py
1  core/whitemagic/security/tool_gating.py
1  polyglot/haskell_docs/haskell_bridge.py
```

Interpretation:

- `core/whitemagic/config/paths.py` is expected to use home-path resolution.
- `hardcoded_path_pattern` entries are likely regex/glob policies or scanners; inspect but do not treat as immediate violations.
- Concrete path findings outside `config/paths.py` should be triaged.

Recommended next-session approach:

1. Run WhiteMagic's own path hygiene tests first.
2. Use STRATA to list concrete `hardcoded_path` outside `core/whitemagic/config/paths.py`.
3. Classify into:
   - runtime state write/read
   - optional tool discovery path
   - documentation/audit-history script
   - security scanner pattern
   - test fixture
4. Fix runtime state paths first.
5. For optional tool discovery, prefer config/path resolver helpers rather than hardcoded home expansion.

Likely first files to inspect:

```text
core/whitemagic/oms/__init__.py
core/scripts/backfill_embeddings.py
core/scripts/rebuild_fts.py
core/scripts/debug_recall.py
core/scripts/absolute_truth.py
core/scripts/setup_zodiac_db.py
core/whitemagic/tools/unified_api.py
core/whitemagic/core/intelligence/hologram/mojo_bridge.py
```

---

### 4.3 Rust Panic Risks and Stubs

STRATA broad category counts included:

```text
rust_panic_risk=279
rust_debug_print=236
rust_clone_in_loop=179
```

This is too many to fix in one pass. Treat as a Rust-hardening backlog.

Recommended next-session approach:

1. Start only with `rust_stub` error findings.
2. For each `todo!()` / `unimplemented!()`:
   - determine whether the binary/module is built in normal workflows
   - determine whether the path is reachable
   - replace with explicit error return where appropriate
   - or move experimental binaries out of ship surface if not intended for release
3. After stub triage, run Rust-specific checks.

Suggested commands:

```bash
cd /home/lucas/Desktop/WHITEMAGIC/core/whitemagic-rust
cargo test
cargo check --all-targets
```

Run these only after confirming the current Rust workspace setup.

---

### 4.4 Python Broad Exceptions and Logging F-Strings

STRATA counts:

```text
broad_except=1229
logging_fstring=1239
```

These are noisy but useful for gradual hardening.

Do not attempt global cleanup in one session.

Recommended next-session approach:

- Ignore these until P0/P1 issues are stable.
- Later, target one package at a time.
- Prioritize files touched by active tools or runtime routes.
- For broad exceptions, preserve graceful degradation behavior.
- For logging f-strings, only fix hot paths or expensive formatting calls.

---

### 4.5 Dead Code, Copy-Paste, and Unused Imports

STRATA counts:

```text
copy_paste=1570
dead_code=1300
unused_import=801
```

These are not immediate correctness failures.

Recommended next-session approach:

- Do not delete based on STRATA alone.
- Use Fragment to locate call sites and docs before removing anything.
- For dead code, require at least two signals:
  - STRATA dead-code finding
  - no Fragment/call-site evidence
  - no registry/dispatch/plugin discovery reference
  - no archive-recovery relevance
- For copy-paste, treat as design-debt evidence, not automatic refactor instruction.

---

## 5. Workspace Hygiene

WhiteMagic's working tree was already heavily dirty before this audit. This remains a major release risk.

Observed categories:

- root docs modified
- site files modified
- grant docs modified
- polyglot files modified
- untracked memory manager compatibility adapter
- untracked `whitemagic-aux/`
- untracked `whitemagic-app/`
- untracked Haskell/Zig/Julia files
- untracked `test_zig`

Recommended next-session approach:

1. Do not mix cleanup with functional fixes.
2. First run:

```bash
git status --short
```

3. Create a change ownership table:
   - intentional current work
   - generated/build artifacts
   - external/deferred projects
   - archive material
   - unknown
4. Only after that decide what to stage, ignore, move, or archive.

---

## 6. Suggested Next-Session Order

### Phase A — Baseline

- Run full core tests.
- Run doc drift.
- Run version check.
- Confirm Fragment index still exists or rebuild externally.

### Phase B — Choose One Remaining Queue

- Recommended next default: path hygiene triage.
- Alternative if staying on stubs: re-run STRATA error-only summary and continue Python-side classification.
- Alternative if staying in Rust: address PyO3 `cargo test` harness/config separately from semantic stub fixes.

### Phase C — Path Hygiene Triage

- Re-run STRATA hardcoded-path summary.
- Ignore `hardcoded_path_pattern` unless it is a real string path.
- Exclude `core/whitemagic/config/paths.py` as allowed.
- Fix runtime state paths before optional tool-discovery paths.
- Likely first files remain:
  - `core/whitemagic/oms/__init__.py`
  - `core/scripts/backfill_embeddings.py`
  - `core/scripts/rebuild_fts.py`
  - `core/scripts/debug_recall.py`
  - `core/scripts/absolute_truth.py`
  - `core/scripts/setup_zodiac_db.py`
  - `core/whitemagic/tools/unified_api.py`

### Phase D — Verification

After any code change:

```bash
cd /home/lucas/Desktop/WHITEMAGIC/core
PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python -m pytest tests/ \
  --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python scripts/check_doc_drift.py

PYTHONDONTWRITEBYTECODE=1 WM_STATE_ROOT=/tmp/whitemagic_triage_state \
  /home/lucas/Desktop/WHITEMAGIC/.venv/bin/python scripts/check_versions.py
```

---

## 7. Recommended Fragment Improvements Before Next WhiteMagic Pass

Already completed in this loop:

- code-aware identifier tokenization
- external `--index` support
- `--format json` / `--format jsonl` for query results

Useful next improvements:

- add `--include` / `--exclude` query-time filters
- add index-time default excludes for auxiliary/deferred folders
- add result snippets with configurable line context
- add symbol graph mode for definitions/references
- add persistent service mode to avoid repeated index loading

---

## 8. Recommended STRATA Improvements Before Next WhiteMagic Pass

Already completed in this loop:

- broader path hygiene detection
- regex/glob path pattern split via `hardcoded_path_pattern`

Useful next improvements:

- add a generic profile mechanism, e.g. `--profile state-root-strict`
- add confidence levels for findings
- add JSON summary mode grouped by category/file/severity
- add allowlist support for known intentional stubs and path resolver files
- add an error-only report mode
- add richer suppressions for test fixtures and abstract base methods

---

## 9. Do Not Do Next Session

Avoid these until the triage queue is classified:

- do not globally delete dead code
- do not globally rewrite broad exceptions
- do not globally rewrite all logging f-strings
- do not merge Fragment or STRATA into WhiteMagic
- do not treat every STRATA finding as a bug
- do not modify docs/site/grants while doing runtime cleanup unless required by a code change

---

## 10. Bottom Line

WhiteMagic is green by its own tests and health gates, but Fragment and STRATA exposed a strong next-session cleanup map.

The first repair pass is now complete:

1. classified the suggested Rust stub cluster
2. fixed the only real `unimplemented!()` macro found in that cluster
3. verified core gates remain green

The best next repair pass is:

1. triage concrete hardcoded runtime paths outside `core/whitemagic/config/paths.py`
2. keep optional tool-discovery paths separate from runtime state writes
3. defer broad exceptions, logging f-strings, copy-paste, dead-code, and unused-import cleanup until P0/P1 findings are classified
4. keep Fragment and STRATA external; use them as measurement instruments, not as code merged into WhiteMagic
