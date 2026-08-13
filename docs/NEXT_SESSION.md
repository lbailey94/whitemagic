# Next Session Handoff - 2026-08-13

> Prepared 2026-08-12 after the release-readiness audit. The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.8.0, 15 crates, 229 registered tool implementations, 3,510 tests.
- `cargo test --workspace`, format check, clippy (`-D warnings`), and release
  binary build all passed on 2026-08-13.
- **All P0 and P1 release gates are now complete.** P2 (NLU abstention,
  router labeling) is post-release. Phase B (v5.9 PET hardening) is the next
  major theme.
- Phase A of PET hardening (A1–A3) is complete and committed (`1dc29b6`):
  ResourceRules on the dispatch path, the effect inventory audit as CI tests,
  and the append-only write-audit journal.
- The curated process smoke test (`scripts/curated_smoke_test.py`) is wired
  into `ci.yml` and `release.yml`; the rehearsal is a committed, repeatable
  CI gate.
- The worktree contains one pre-existing untracked analysis note:
  `docs/notes/cpu-gpu-agentic-memory-2026-08-12.md`. Do not overwrite it.

## Release Position

The release target is a local-first memory and session-continuity MCP server for
coding agents. The curated surface is the product boundary. The full surface,
daemon, NLU promotion, learned routing, imagination, self-play, Sangha, and
polyglot features remain optional or experimental until their live behavior is
verified.

## Next Steps

All P0 and P1 release gates are complete. The next session should:

1. **Run the full release gate** on a clean build (`cargo clean && cargo build --release`).
2. **Tag the release candidate** (`v5.8.0-rc1`) and push to trigger the release workflow.
3. **Fresh-install rehearsal**: run `scripts/install.sh` against the RC, then `wm doctor`, then `scripts/curated_smoke_test.py`.
4. **P2 items** (post-release): NLU abstention, router labeling, self-play/imagination labeling.
5. **Phase B** (v5.9): B4 sandbox, B5 store seal/verify, B6 untrusted `_meta`, B7 store permissions.

## Hard Blockers

- ~~Some effect declarations still understate real side effects (effect inventory
  audit remains open).~~ ✅ Closed 2026-08-13 — the audit is 16 CI tests; 13
  false declarations fixed.
- ~~The curated contract still needs export/backup/index-health workflow docs.~~
  ✅ Closed 2026-08-13 — `docs/OPERATIONS.md` covers the full workflow.

**No hard blockers remain.** All P0 and P1 release gates are complete.

## Verification Commands

```bash
cargo fmt --all -- --check
cargo test --workspace --all-targets
cargo clippy --all-targets -- -D warnings
cargo build --release --bin wm
wm doctor --store ~/Desktop/WMdata/live
python3 scripts/curated_smoke_test.py --binary target/release/wm
```

The smoke test is a committed repository script (`scripts/curated_smoke_test.py`).
It uses a fresh temporary store, explicit curated routing, restarts the binary,
and asserts JSON results rather than only process exit code.

## Defer

- Do not add more v26 tools.
- Do not expand Sangha, self-play, imagination, or autonomous learning.
- Do not prioritize the `McpServer` split, routing-table consolidation, or a
  scaffolding macro over the release gates.
- Do not promote embedding NLU based on disagreement metrics alone.

## Useful Existing Evidence

- `docs/notes/shadow-mode-analysis-2026-08-10.md`: embedding-router quality data.
- `docs/PROGRESS.md`: implementation history and verified phase work.
- `docs/RELEASE_READINESS.md`: blockers, acceptance criteria, and no-go gates.
- `docs/PET_HARDENING.md`: next-session hardening plan (Phase A: ResourceRules
  wiring, effect inventory audit, write-audit trail).
- `scripts/collect_shadow_data.py`: router data collection, requiring a live
  embedder endpoint.

## Next Session Start

~~Begin with Phase A of `docs/PET_HARDENING.md`.~~ ✅ Phase A (A1–A3)
complete 2026-08-13, committed as `1dc29b6`:

- A1: `ResourceRules` evaluated on the dispatch path (budgets block, novelty
  flags reach responses, autonomous review/purpose gates block).
- A2: effect inventory audit as 16 CI tests (`crates/wm-mcp/src/effect_audit.rs`);
  13 false declarations fixed, plus a runtime Satya check for `galaxy=citta`.
- A3: `WriteAuditJournal` (append-only LMDB journal, `wm doctor` surfacing,
  shutdown flush).

Remaining release gates, in order, before Phase B (v5.9 PET hardening):

1. ~~**P0**: prove natural-language calls cannot reach destructive tools (the
   acceptance line is still open — the structural gate exists, the test does
   not).~~ ✅ Done 2026-08-13 — destructive gate moved before required-arg
   check; comprehensive sweep test covers all destructive tools.
2. ~~**P0**: define the LMDB/Tantivy consistency contract — expose degraded
   index state and a safe rebuild path.~~ ✅ Done 2026-08-13 — `IndexHealth`
   tracks successes/failures; `check_consistency()` detects LMDB/Tantivy drift;
   `system.health` and `wm doctor` report degraded state.
3. ~~**P0**: search health must report stale or unavailable indexes instead of
   silently saying healthy.~~ ✅ Done 2026-08-13 — `system.health` reports
   `index_health` and `index_consistency`; `wm doctor` prints `[WARN]` with
   remediation guidance.
4. ~~**P1**: export, backup, index-health, and recovery workflow docs.~~
   ✅ Done 2026-08-13 — `docs/OPERATIONS.md` covers export (galaxy.export,
   galaxy.backup, training data), backup (cold + hot), index health (wm doctor,
   system.health, consistency model), and recovery (corruption, map full,
   Tantivy rebuild, restore from backup).
5. ~~**P1**: release checksums and a short install path for published binaries;
   client config examples that launch the same versioned binary.~~ ✅ Done
   2026-08-13 — `scripts/install.sh` downloads, verifies SHA-256, and installs
   to `~/.local/bin/wm`. Release workflow already generates per-platform
   checksums.
6. ~~**P1**: optional features (Julia/Python/LanceDB/ONNX) tested or explicitly
   marked unsupported for the release.~~ ✅ Done 2026-08-13 — feature support
   matrix in `RELEASE_READINESS.md` documents CI status and release status for
   all optional features.
7. **P2** (post-release): NLU abstention, router labeling, self-play/imagination
   labeling.

Phase B (v5.9 theme): B4 sandbox mode, B5 store seal/verify, B6 untrusted
`_meta` by default, B7 store permission hygiene (`0700`).

Also use `whitemagic-dev` session.continuity at session start (see AGENTS.md).
