# Backlog — Post-Perfection-Strategy Work (2026-07-20)

**Status**: Active workspace doc — triage at session start, update as items land.
**Baseline**: v25.2.0 (tagged `e01c9f7e`, pushed to both remotes).
**Context**: `STRATEGY_CODEBASE_PERFECTION_2026.md` is **fully complete** (all 11
phases, P0–P10, including P9.5). Phase 3 gate re-verified 2026-07-20: **3
consecutive randomized full-suite passes, 7,739 passed / 0 failed each**, `git
status` clean after runs. Verify tier: 2,077 passed / 0 failed.

This doc collects everything that surfaced *after* the strategy closed, plus the
deliberately-deferred items recorded inside it. Each entry has: what, why,
evidence/pointers, acceptance criteria, and a size estimate
(**S** < 1h, **M** = hours, **L** = multi-session).

---

## 1. P0 — Cheap, high-value, start next session

### 1.1 Re-run `mcp-conform` against v25.2.0 — **S**
- **What**: Run the 12-check MCP conformance probe (stdio + HTTP) on the current build.
- **Why**: Last certified 12/12 at v25.0.1 (Overnight Addendum S1). v25.1.0 added 74
  security dispatch entries and v25.2.0 added prewarm — the surface changed.
- **Evidence**: `core/whitemagic/mcp/conformance.py`, `core/tests/unit/test_mcp_conformance.py`.
- **Acceptance**: 12/12 on both transports; result recorded in PROJECT_STATE.

### 1.2 Review the 4 permanently-skipped tests — **S**
- **What**: Identify the 4 skips in the green runs, confirm each has a documented reason.
- **Why**: Phase 3 gate allows only *intentional, bounded* skips.
- **Acceptance**: Each skip has a skipif reason or is unskipped.

### 1.3 Archive the completed perfection strategy doc — **S**
- **What**: Move `STRATEGY_CODEBASE_PERFECTION_2026.md` → `docs/completed/` with a
  completion banner; update `INDEX.md`.
- **Why**: P9.1 doc hierarchy — completed plans live in `docs/completed/`; the root
  should only carry living docs.
- **Acceptance**: Doc drift green; INDEX.md updated.

### 1.4 Fix teardown logging noise — **S/M**
- **What**: Stop the "I/O operation on closed file" logging errors from
  `homeostatic_loop` threads during pytest/interpreter teardown.
- **Why**: Noise hides real failures in CI logs; also appears in live-server logs.
- **Evidence**: Any full-suite log tail (gate_g1/g3 logs, tonight_final3.log).
- **Approach**: Guard `logger.*` calls in `_loop` with a shutdown flag, or
  `logging.raiseExceptions = False` in test conftest; join the thread before streams close.
- **Acceptance**: Zero "ValueError: I/O operation on closed file" in a full-suite log.

---

## 2. P1 — Test-determinism residue

The 2026-07-20 hardening session eliminated 7 flake classes (see strategy doc
"Re-verified" addendum). What remains is the *environmental tail*: tests that only
fail under full-suite xdist CPU contention on a loaded machine, all green standalone.

### 2.1 Mock remaining alchemical-loop boundaries — **M**
- **What**: Extend the `_mock_heavy_ops` fixtures (both `test_enhanced_tools.py` and
  `oracle/test_procession.py`) to cover `_run_strata`, `_run_strata_survey`,
  `_check_quality` (ensemble.query), `_extract_lessons` (autonomous_learner),
  `_run_monte_carlo_scoring`.
- **Why**: `_mine_associations` mock fixed the worst class, but late-night runs
  still failed `test_loop_invokes_tools` / `test_cycle_has_12_yin_steps` under load —
  the loop has more real boundaries (strata scans the repo).
- **Evidence**: commits `b2e9842c` (pattern to follow); failure list in
  `/tmp/opencode/tonight_final3.log` (if preserved) or session memory `5d98f6378da464f1`.
- **Acceptance**: 3 consecutive full-suite runs with zero alchemical failures.

### 2.2 Remaining load-victim files — **M**
- **Files**: `test_multi_galaxy_access.py` (specific-galaxies search),
  `test_security_assessment_phase1.py::TestWasmVerifierEvents`,
  `test_clone_army_integration.py::test_massive_deployer_throughput`,
  `test_opencode_hermes_bridge.py` / `test_all_ganas_mcp.py` (bootstrap under load).
- **What**: Same treatment as today's classes: reproduce with failure detail, fix at
  the boundary (mock heavy engines, poll-instead-of-sleep, or reclassify to
  integration/benchmarks).
- **Acceptance**: 3 consecutive full-suite runs fully green (7,700+ tests).

### 2.3 xdist native-crash / hang robustness — **M/L**
- **What**: Harden the suite against native-library crashes in forked workers.
- **Evidence**: 2026-07-20 ~21:22 — worker gw2 hard-crashed on
  `test_all_ganas_mcp[gana_net-prompt.list]` (`assert not crashitem`); ~21:26 — torch
  "Loading weights" stall (fork+OpenMP deadlock class). Both one-off, unreproducible standalone.
- **Options**: (a) `xdist_group` native-heavy tests (ONNX/torch) onto one worker;
  (b) per-worker model preload in conftest (before fork); (c) `OMP_NUM_THREADS=1` +
  `HF_HUB_OFFLINE=1` in the test env; (d) `-p xdist --forked` for the native subset.
- **Acceptance**: 5 consecutive full-suite runs with no worker crash/hang.

### 2.4 Pytest-hygiene leak cleanup — **S/M**
- **What**: Resolve the recurring `LEAK [syspath] added sys.path entry
  '.../core/whitemagic/core/patterns'` and torch's env-var leaks
  (`KMP_DUPLICATE_LIB_OK`, `TORCHINDUCTOR_CACHE_DIR`).
- **Why**: `pytest-hygiene` is installed for exactly this; leaks are warnings today,
  failures tomorrow if `--hygiene-strict` is enabled (quick-win 18.2 follow-up).
- **Acceptance**: Zero env/syspath leaks in the affected files.

---

## 3. P2 — Performance & cold start (P6.4 continuation)

### 3.1 Reduce the actual cold path (not just absorb it) — **L**
- **What**: Prewarm (v25.2.0) *moves* the 40s cold cost to startup; it doesn't shrink it.
  Breakdown measured 2026-07-20: cross-encoder 13.5s, middleware lazy init 24.5s,
  embedding engine 1.9s, semantic defense 0.6s.
- **Ideas**: make the cross-encoder lazy-by-default with async warm; investigate the
  ~17-26s middleware init on production state root (permissions/maturity gate/pattern
  guard/engagement tokens — likely large-DB reads); ONNX session sharing between
  embedder and defense corpus; default `HF_HUB_OFFLINE=1` for installed deployments.
- **Acceptance**: Cold prewarm < 10s on the production state root (1.2GB sessions DB).

### 3.2 Warm-path search latency on production root — **M**
- **What**: First post-prewarm search is 5.0s (27-stage middleware chain + semantic
  scan per dispatch). Subsequent calls ~1.4s (S4). Profile the per-call 3.5s delta.
- **Acceptance**: p50 warm `search_memories` < 2s on production root.

### 3.3 Search recall quality check — **S/M**
- **What**: A memory created 60s earlier ("prewarm verification probe") was not
  surfaced by `search_memories` for its own title terms (found only via direct SQL).
- **Why**: Possible embedding-index lag or FTS5 threshold issue on fresh memories —
  user-visible correctness question, not just perf.
- **Acceptance**: A just-created memory is findable by exact title query within one
  dispatch, or the lag is documented with a mechanism.

---

## 4. P3 — Live-system health & operator UX

### 4.1 "CRITICAL HEALTH" threshold tuning — **M**
- **What**: The live server's apotheosis/homeostatic loops fire constant critical
  alerts: coherence 0.50 (threshold 0.6), setpoint_deviation ~0.66 (threshold 0.15),
  guna_balance 0.00 (threshold 0.7), signal_to_noise 0.00 (threshold 0.3) — plus
  emergency dream cycles.
- **Why**: Alert fatigue; also triggers real work (dream cycles) on a loop. Either
  the setpoints are wrong for steady-state operation or the measured quantities are
  genuinely unhealthy and need diagnosis.
- **Evidence**: `core/whitemagic/core/consciousness/apotheosis_engine.py:902`,
  `harmony/homeostatic_loop.py:366,402`; live logs `~/.whitemagic/logs/`.
- **Acceptance**: Steady-state server emits zero critical alerts/day, or the
  underlying health issue is diagnosed and fixed.

### 4.2 Semantic-defense over-sensitivity — **S**
- **What**: The input sanitizer rejects legitimate memory content with fuzzy-match
  false positives ('overwrite'≈'override', 'private'≈'activate') and flags dense
  technical prose as "encoded/obfuscated".
- **Why**: Blocks normal `create_memory` usage (hit 3× on 2026-07-20 writing session
  summaries). The v25.1.0 violet rules may have tightened it.
- **Evidence**: `core/whitemagic/security/semantic_defense.py`; session memories from
  2026-07-20 show the rephrasing dance.
- **Acceptance**: The three rejected 2026-07-20 payloads pass; no regression on the
  14-payload injection test suite.

---

## 5. P4 — Tech debt

### 5.1 Remaining 33 active stubs — **M (batch) / L (full)**
- **Reality check**: 30 of 33 are *permanent by design* (`Never (interface/design/
  generated/legacy)`) — not actionable. The actionable ones:
  - **`tools/security/monitor.py:91:_run_checks`** — the only real missing
    implementation ("periodic security checks — when monitor ships"). **M**
  - `tools/handlers/misc.py:10:_stub` — intentional test fixture, keep.
  - Review pass to reclassify any other "When X ships" entries whose dependency
    has since shipped (like abi_decoder's eth_utils had).
- **Acceptance**: `check_stubs.py` clean; registry reflects reality; monitor
  decision made (implement or document as deferred).

### 5.2 Import-linter violation drain — **L**
- **What**: 10+ `core→tools` violations (benchmark, background_worker, fusions_kg,
  kaizen_engine, media_processor, reasoning, conductor, session_startup, fusions,
  consciousness_loop) + 3 `utils→core` (shared_patterns, gan_ying_connect, event_emit).
- **Why**: P4.1 drained *handler/dispatch* imports to 0 via `ports.py`; these are the
  deeper architectural remainder. Contracts exist in `.importlinter` but aren't enforced.
- **Approach**: Same ports.py pattern, one module at a time; add ratchet to CI once drained.
- **Acceptance**: `lint-imports` passes both contracts in CI.

### 5.3 uv adoption in CI — **S**
- **What**: Replace `pip` with `uv sync --frozen` in CI workflows (quick-win 18.1 follow-up).
- **Acceptance**: All 4 CI lanes use uv; `uv.lock` is the install source of truth.

### 5.4 Tool-count consistency in registry files — **S**
- **What**: `mcp-registry.json`/`server.json` nested-count fields have historically
  drifted from the dispatch table (820 vs 832 noted 2026-07-18). Tool count in `wm`
  description is now generated; extend generation to the registry JSONs or add a
  sync check to the facts gate.
- **Acceptance**: `check_tool_surface.py --check` reports zero inconsistencies.

---

## 6. P5 — Release & launch logistics

### 6.1 Publish v25.2.0 artifacts — **M**
- **What**: The 7-step release process beyond git tags: PyPI wheel/sdist build +
  publish, MCP Registry publish (server.json), Docker image build, GitHub Release
  notes (from CHANGELOG 25.2.0 entry).
- **Evidence**: `docs/CONTRIBUTING.md` release process; `docs/RELEASE_READINESS_CHECKLIST.md` §7.
- **Note**: v25.1.0 tag (`7581ecf0`) points to a version-inconsistent tree — leave
  as historical (documented) or delete; do not reuse.
- **Acceptance**: `pip install whitemagic==25.2.0` works in a fresh venv; MCP
  registry lists 25.2.0.

### 6.2 External adversarial review — **L**
- **What**: Phase 10 defines it but it hasn't happened: an external reviewer (or a
  fresh adversarial AI session) tries to *disprove* readiness — unsafe classification,
  permission bypass, cross-user leakage, migration loss, import side effects, install
  failure, stable-API contradictions, misleading claims.
- **Evidence**: `docs/RELEASE_READINESS_CHECKLIST.md` (80+ items).
- **Acceptance**: Review report filed; findings triaged into this backlog.

### 6.3 Surf strategy execution (go-to-market) — **L**
- **What**: `WHITEMAGIC_SURF_STRATEGY.md` (Desktop) — seed/evolve/withdraw: Docker
  image, benchmark campaign, demo videos, quiet availability, targeted seeding.
- **Status**: Strategy docs updated for accelerated timeline; execution not started.
- **Acceptance**: Per the surf strategy's own phased checklist.

### 6.4 Benchmark campaign completion — **M**
- **What**: `docs/BENCHMARK_PERFECTION_STRATEGY.md` — 780-tool campaign stood at
  95.6% adjusted rate (600 success + 101 expected + 11 unexpected + 21 timeout).
  Close the 11 unexpected + 21 timeouts.
- **Acceptance**: 100% adjusted rate on the 860-tool surface (v25.2.0 recount).

---

## 7. P6 — Strategic / longer-term

- **PyPI + MCP registry presence** as the "by AI, for AI" distribution thesis
  (x402 micropayments idea from the benchmark-campaign notes — unprioritized).
- **Website refresh** for v25.2.0 facts (tool counts, violet pipeline, prewarm) —
  `docs/message_board/WEBSITE_NARRATIVE_PRESCIENCE.md` is the plan of record.
- **Public launch timing** per surf strategy's narrative-break trigger.
- **Polyglot revival**: import-linter drain (5.2) unblocks the layered-architecture
  contract that several polyglot bridges violate.

---

## 8. Standing operational notes (this machine)

- **HF Hub**: unauthenticated requests hit rate limits; set `HF_TOKEN` for faster,
  more reliable model downloads (warnings in every cold run).
- **xdist natives**: torch/ONNX in forked workers can rarely crash or deadlock
  (§2.3). If a suite run hangs on "Loading weights", kill and rerun — do not
  investigate as a code regression without a standalone repro.
- **Parallel sessions**: 2026-07-20 proved two agent sessions can collide in the
  working tree (mid-run file mutations). One active editing session per repo at a
  time during gate runs.
- **Semantic defense**: writes may be rejected (§4.2) — rephrase in plain prose,
  avoid hex dumps and dense identifier clusters in memory content.
- **Live server**: `run_mcp_lean` (PID varies) runs against `~/.whitemagic`;
  two processes share the DBs fine (WAL), but expect ~20s first-dispatch on
  pre-v25.2.0 servers (fixed by prewarm going forward).

---

## 9. Session-start ritual for whoever picks this up

1. `source .venv/bin/activate && git status && git log --oneline -5`
2. `python core/scripts/check_versions.py && python core/scripts/check_doc_drift.py`
3. Pick a P0/P1 item; timebox it (epoch timestamps per AGENTS.md §12).
4. Full Tier-3 suite before committing anything that touches `core/whitemagic/`.
5. Update this file: move landed items to a dated "Done" section.

---

*Created 2026-07-20, post-v25.2.0. Maintainers: whoever is awake.*
