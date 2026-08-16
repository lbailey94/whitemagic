# Next Session Handoff - 2026-08-16

> Prepared 2026-08-16 after gate re-run with uncommitted work.
> The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- v5.8.0, 15 crates, 229 registered tool implementations, 3,513 tests.
- **Release gates passed 2026-08-16**: fmt clean, clippy clean (`-D warnings`),
  3,513 tests pass, release build clean. Includes uncommitted work:
  `tools.usage_report`, daemon checkpoint interval, batch embedding fixes,
  grid-search results.
- **Release gate run complete. Tagged v5.8.0-rc1.** Fresh-install rehearsal
  passed (quickstart + doctor + curated smoke test, all healthy).
- **All P0, P1, and P2 items are now complete.** Phase B items B6 and B7 are
  complete. B5 (store seal/verify) and B4 (sandbox mode) remain.
- **Vector search wiring complete (2026-08-14):** `RecallEngine` is shared via
  `Arc<RecallEngine>` with `MemoryCreateTool`, `MemoryBatchCreateTool`, and
  `MemoryHybridRecallTool`. When `WM_EMBEDDER_ENDPOINT` is set, memory creation
  auto-embeds and `memory.hybrid_recall` fuses BM25 + vector cosine similarity.
  Without an embedder, all tools fall back to pure BM25. See
  [`docs/VECTOR_SEARCH_ROADMAP.md`](VECTOR_SEARCH_ROADMAP.md).
- **Batch embedding fix (2026-08-15):** Three bugs fixed in batch embedding
  (Tantivy writer lock conflict, embedder token limit, fallback writer).
- **Grid search completed (2026-08-15/16):** 7 weight combinations ran with
  live embedder (n=10). Hybrid search lifted R@5 from 0.70 → 0.90 vs
  BM25-only stem baseline, but weight variations did not differentiate
  recall on this sample. R@1 dropped from 0.50 → 0.40 with hybrid.
  BM25-only stem 50q baseline: R@1=0.62, R@5=0.72, MRR=0.667.
- Codebase pushed to GitHub (`lbailey94/WMv5`, private). RC1 tag pushed;
  release workflow triggered. HEAD is 1 commit ahead of origin (not pushed).
- Phase A of PET hardening (A1–A3) is complete and committed (`1dc29b6`).
- The curated process smoke test (`scripts/curated_smoke_test.py`) is wired
  into `ci.yml` and `release.yml`; the rehearsal is a committed, repeatable
  CI gate.

## Release Position

The release target is a local-first memory and session-continuity MCP server for
coding agents. The curated surface is the product boundary. The full surface,
daemon, NLU promotion, learned routing, imagination, self-play, Sangha, and
polyglot features remain optional or experimental until their live behavior is
verified.

## Next Steps

All P0/P1/P2 items and Phase B items B6/B7 are complete. Release gates passed
2026-08-16 (3,513 tests, fmt/clippy/release build clean). Remaining work:

1. **Commit uncommitted work** — 13 files changed: `tools.usage_report` tool,
   daemon checkpoint interval, batch embedding fixes, public-claims drift
   fixes (README, PROGRESS, RELEASE_READINESS, NEXT_SESSION), grid-search
   results.
2. **Push and tag v5.8.0-rc2** — push HEAD + new commit to origin, tag rc2.
3. **Recall quality** (product promise): R@1 gap analysis — OR + token-coverage
   as primary strategy, inspect persistent miss queries (Glass Menagerie,
   Serenity Yoga, February 14th), field-weight tuning. See
   [`docs/VECTOR_SEARCH_ROADMAP.md`](VECTOR_SEARCH_ROADMAP.md).
4. **B5: Store seal/verify** (low priority): HMAC over store directory to
   detect tampering. Needs key management design — derive from a per-install
   secret or use a platform keystore. Consider a `wm seal` / `wm verify` CLI
   pair.
5. **B4: Sandbox mode** (low priority): restrict tool execution capabilities
   via seccomp (Linux) or sandbox-exec (macOS). Platform-specific; needs
   careful allowlisting of syscalls for LMDB, Tantivy, and HTTP embedder.
6. **v5.8.0 final release**: re-run the full gate from `cargo clean`, tag
   `v5.8.0`, push to trigger the release workflow with the fixed artifact
   naming.
7. **Optional**: re-run the fresh-install rehearsal with the fixed
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

### Session 2026-08-15 (early morning): batch embedding bug fixes

Fixed three bugs preventing vector search from activating during grid search:

1. **Tantivy writer lock conflict** in `MemoryBatchCreateTool::call`
   (`crates/wm-tools/src/lib.rs`): The tool acquired a Tantivy writer at line
   277, then `RecallEngine::store_batch_with_embedding` tried to acquire
   another writer at line 337. Tantivy only allows one writer at a time, so
   the embedding path always failed and fell back to BM25-only storage
   (without embeddings). Fix: only acquire `writer_guard` when
   `self.recall.is_none()`.
2. **Embedder token limit exceeded** in `RecallEngine::store_batch_with_embedding`
   (`crates/wm-memory/src/recall.rs`): The method sent all items in a single
   `embed_batch()` call. With 50+ real conversation turns (~883 chars avg),
   this exceeded the embedder's 512-token context limit (llama-server with
   bge-small-en-v1.5). Fix: adaptive chunking with
   `MAX_CHARS_PER_CHUNK = 1500` and `MAX_CHARS_PER_ITEM = 1500` (truncation
   for items exceeding the limit).
3. **Fallback path missing writer** in `MemoryBatchCreateTool::call`: When
   `store_batch_with_embedding` failed, the fallback path tried to use
   `writer_guard` which was now `None` (due to fix #1). Fix: lazily acquire a
   fallback writer in the error path.

Validation: 9/9 batch_create calls succeed with embeddings (0 warnings),
hybrid_recall returns 10 fused BM25 + vector results. Grid search was started
but interrupted for the night.

### Session 2026-08-14 (afternoon): vector search wiring

Completed vector search integration into MCP server tool path (626 tests, 0 clippy warnings):

- **`ConversationalSearch`** changed to hold `Arc<RecallEngine>` for shared ownership
- **`RecallEngine::embedder_is_real()`** added to detect stub vs real embedder
- **`McpServer::with_defaults()`** constructs `Arc<RecallEngine>` with `RecallConfig::from_env()`,
  shares with `ConversationalSearch` and memory tools via `recall_for_tools: Option<Arc<RecallEngine>>`
- **`MemoryCreateTool`** uses `recall.store_with_embedding()` when available, falls back to
  plain LMDB + Tantivy when no embedder
- **`MemoryBatchCreateTool`** same pattern, per-item embedding with fallback
- **`MemoryHybridRecallTool`** runs `recall.hybrid_search()` as Phase 0 (BM25 + vector fusion)
  when embedder available, falls back to existing BM25-only phases
- **`register_all` / `register_expansion`** updated to thread `recall` parameter
- All test call sites updated for new signatures
- Docs updated: `RELEASE_READINESS.md`, `NEXT_SESSION.md`, new `VECTOR_SEARCH_ROADMAP.md`

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
