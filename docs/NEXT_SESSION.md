# Next Session Handoff - 2026-08-13

> Prepared 2026-08-12 after the release-readiness audit. The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.8.0, 15 crates, 229 registered tool implementations, 3,447+ tests.
- `cargo test --workspace --quiet`, format check, clippy, and release binary
  build passed on 2026-08-12.
- Explicit curated-profile rehearsal passed create, search, FTS-based hybrid
  recall, session start, transaction rollback, and claims calibration.
- Restart persistence passed for a memory created by one process and searched by
  the next process.
- The rehearsal is not yet a committed process-level smoke test and used
  explicit routes rather than semantic NLU.
- The worktree contains one pre-existing untracked analysis note:
  `docs/notes/cpu-gpu-agentic-memory-2026-08-12.md`. Do not overwrite it.

## Release Position

The release target is a local-first memory and session-continuity MCP server for
coding agents. The curated surface is the product boundary. The full surface,
daemon, NLU promotion, learned routing, imagination, self-play, Sangha, and
polyglot features remain optional or experimental until their live behavior is
verified.

## Tomorrow's Order

1. ~~Add regression tests for profile precedence, read-only writes, unknown
   compartments, and profile-aware discovery.~~ ✅ done 2026-08-13
2. ~~Fix the profile and read-only boundaries.~~ ✅ done 2026-08-13
3. ~~Make transaction rollback exact and failure-safe, preserving IDs and all
   metadata.~~ ✅ done 2026-08-13
4. ~~Fix secondary-index overwrite behavior and filtered reindexing.~~ ✅ done
   2026-08-13
5. ~~Add the committed curated process smoke test, then wire it into CI and the
   release workflow.~~ ✅ done 2026-08-13 — `scripts/curated_smoke_test.py`
   covers the full curated workflow, restart persistence, and read-only
   enforcement; wired into `ci.yml` and `release.yml`.
6. ~~Update client configurations and v5 documentation from verified behavior.~~
   ✅ done 2026-08-13 — client config templates now launch the native binary
   with `--profile curated`; CHANGELOG gained an unreleased hardening section.
7. Only after the release gates are green, retest the embedding router and add
   abstention if the labeled results justify it.

## Hard Blockers

- ~~Some effect declarations still understate real side effects (effect inventory
  audit remains open).~~ ✅ Closed 2026-08-13 — the audit is 16 CI tests; 13
  false declarations fixed.
- The curated contract still needs native argument schemas, a documented
  hybrid-recall semantic decision, and export/backup/index-health workflow
  docs.

## Verification Commands

```bash
cargo fmt --all -- --check
cargo test --workspace --all-targets
cargo clippy --all-targets -- -D warnings
cargo build --release --bin wm
wm doctor --store ~/Desktop/WMdata/live
```

The smoke test should eventually be a repository script rather than an ad hoc
stdin sequence. It must use a fresh temporary store, explicit curated routing,
restart the binary, and assert JSON results rather than only process exit code.

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
complete 2026-08-13:

- A1: `ResourceRules` evaluated on the dispatch path (budgets block, novelty
  flags reach responses, autonomous review/purpose gates block).
- A2: effect inventory audit as 16 CI tests (`crates/wm-mcp/src/effect_audit.rs`);
  13 false declarations fixed, plus a runtime Satya check for `galaxy=citta`.
- A3: `WriteAuditJournal` (append-only LMDB journal, `wm doctor` surfacing,
  shutdown flush).

Remaining release work before Phase B (v5.9 PET hardening):

1. Verify the curated smoke test and the NLU shadow report still pass on a
   live store; retest the embedding router abstention question.
2. Remaining P0 acceptance items: the LMDB/Tantivy consistency contract
   (index health reporting) and search-health honesty.
3. Phase B items B4–B7 (sandbox mode, store seal/verify, untrusted `_meta`,
   store permissions) are the v5.9 theme.

Also use `whitemagic-dev` session.continuity at session start (see AGENTS.md).
