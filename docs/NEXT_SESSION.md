# Next Session Handoff - 2026-08-13

> Prepared 2026-08-12 after the release-readiness audit. The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.8.0, 15 crates, 229 registered tool implementations, 3,504 tests.
- `cargo test --workspace`, format check, clippy (`-D warnings`), and release
  binary build all passed on 2026-08-13.
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
- The curated contract still needs export/backup/index-health workflow docs
  (native argument schemas and the hybrid-recall semantic decision are
  settled).

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
complete 2026-08-13, committed as `1dc29b6`:

- A1: `ResourceRules` evaluated on the dispatch path (budgets block, novelty
  flags reach responses, autonomous review/purpose gates block).
- A2: effect inventory audit as 16 CI tests (`crates/wm-mcp/src/effect_audit.rs`);
  13 false declarations fixed, plus a runtime Satya check for `galaxy=citta`.
- A3: `WriteAuditJournal` (append-only LMDB journal, `wm doctor` surfacing,
  shutdown flush).

Remaining release gates, in order, before Phase B (v5.9 PET hardening):

1. **P0**: prove natural-language calls cannot reach destructive tools (the
   acceptance line is still open — the structural gate exists, the test does
   not).
2. **P0**: define the LMDB/Tantivy consistency contract — expose degraded
   index state and a safe rebuild path.
3. **P0**: search health must report stale or unavailable indexes instead of
   silently saying healthy.
4. **P1**: export, backup, index-health, and recovery workflow docs.
5. **P1**: release checksums and a short install path for published binaries;
   client config examples that launch the same versioned binary.
6. **P1**: optional features (Julia/Python/LanceDB/ONNX) tested or explicitly
   marked unsupported for the release.
7. **P2** (post-release): NLU abstention, router labeling, self-play/imagination
   labeling.

Phase B (v5.9 theme): B4 sandbox mode, B5 store seal/verify, B6 untrusted
`_meta` by default, B7 store permission hygiene (`0700`).

Also use `whitemagic-dev` session.continuity at session start (see AGENTS.md).
