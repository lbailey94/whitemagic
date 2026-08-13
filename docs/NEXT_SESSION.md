# Next Session Handoff - 2026-08-13

> Prepared 2026-08-12 after the release-readiness audit. The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.7.7, 15 crates, 229 registered tool implementations, 3,447 tests.
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

1. Add regression tests for profile precedence, read-only writes, unknown
   compartments, and profile-aware discovery.
2. Fix the profile and read-only boundaries.
3. Make transaction rollback exact and failure-safe, preserving IDs and all
   metadata.
4. Fix secondary-index overwrite behavior and filtered reindexing.
5. Add the committed curated process smoke test, then wire it into CI and the
   release workflow.
6. Update client configurations and v5 documentation from verified behavior.
7. Only after the release gates are green, retest the embedding router and add
   abstention if the labeled results justify it.

## Hard Blockers

- `--readonly` currently protects the Tantivy writer but does not prevent every
  LMDB mutation.
- Transaction rollback snapshots are bounded and do not preserve exact records.
- Unknown compartments fail open, and privacy/model-exclusion flags are not
  consistently enforced on read paths.
- `WM_TOOL_PROFILE=curated` is overwritten by the CLI's default `full` value.
- Tool discovery contains hardcoded full-surface counts and a dead curated route.
- LMDB secondary indexes and Tantivy can diverge after updates or maintenance.

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
- `scripts/collect_shadow_data.py`: router data collection, requiring a live
  embedder endpoint.
