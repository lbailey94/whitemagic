# Next Session Handoff - 2026-08-13

> Prepared 2026-08-13 after the post-RC1 hardening batch. The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.8.0, 15 crates, 229 registered tool implementations, 3,515 tests.
- `cargo test --workspace`, format check, clippy (`-D warnings`), and release
  binary build all passed on 2026-08-13 from `cargo clean`.
- **Release gate run complete. Tagged v5.8.0-rc1.** Fresh-install rehearsal
  passed (quickstart + doctor + curated smoke test, all healthy).
- **All P0, P1, and P2 items are now complete.** Phase B items B6 and B7 are
  complete. B5 (store seal/verify) and B4 (sandbox mode) remain.
- Codebase pushed to GitHub (`lbailey94/WMv5`, private). RC1 tag pushed;
  release workflow triggered.
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

All P0/P1/P2 items and Phase B items B6/B7 are complete. Remaining work:

1. **B5: Store seal/verify** (low priority): HMAC over store directory to
   detect tampering. Needs key management design — derive from a per-install
   secret or use a platform keystore. Consider a `wm seal` / `wm verify` CLI
   pair.
2. **B4: Sandbox mode** (low priority): restrict tool execution capabilities
   via seccomp (Linux) or sandbox-exec (macOS). Platform-specific; needs
   careful allowlisting of syscalls for LMDB, Tantivy, and HTTP embedder.
3. **v5.8.0 final release**: re-run the full gate from `cargo clean`, tag
   `v5.8.0`, push to trigger the release workflow with the fixed artifact
   naming.
4. **Optional**: re-run the fresh-install rehearsal with the fixed
   `install.sh` (per-platform artifact names) to verify end-to-end download
   works against a real GitHub Release.

## Hard Blockers

**No hard blockers remain.** All P0 and P1 release gates are complete. P2
items are complete. Phase B items B6 and B7 are complete.

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
- `docs/PET_HARDENING.md`: hardening plan (Phase A complete; Phase B in progress).
- `scripts/collect_shadow_data.py`: router data collection, requiring a live
  embedder endpoint.

## Session History

### Session 2026-08-13 (late evening): post-RC1 hardening batch

Completed 5 items in one session (3,515 tests, 0 clippy warnings, fmt clean):

- **B7: Store permissions (0700)** — `MemoryStore::open()` creates the store
  directory with mode `0o700` on Unix. Regression test added.
- **P2-1: NLU abstention** — when NLU routing returns `gnosis` with confidence
  < 0.15, the meta-tool abstains and returns an error suggesting explicit
  routing. 2 tests.
- **P2-2: Experimental labeling** — `imagine.*` and `selfplay.*` tool
  descriptions prefixed with `[Experimental]`. AGENTS.md updated.
- **B6: Untrusted `_meta` stripping** — `_meta` stripped from tool arguments
  in both `McpServer` and `WmMetaTool` before dispatch. 1 test.
- **Misc: Release workflow artifact naming** — release assets now use
  per-platform names matching `install.sh` expectations.

### Session 2026-08-13 (evening): P0/P1 release gates complete

- P0-1: Destructive-via-NLU sweep test
- P0-2: LMDB/Tantivy consistency contract
- P0-3: Search-health honesty
- P1-4: Operations docs
- P1-5: Install script
- P1-6: Optional features matrix
- Tagged v5.8.0-rc1, fresh-install rehearsal passed

### Session 2026-08-13 (afternoon): Phase A PET hardening

- A1: ResourceRules on the dispatch path
- A2: Effect inventory audit as 16 CI tests; 13 false declarations fixed
- A3: WriteAuditJournal (append-only LMDB journal, `wm doctor` surfacing)

Also use `whitemagic-dev` session.continuity at session start (see AGENTS.md).
