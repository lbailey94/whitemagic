# Next Session Handoff - 2026-08-17

> Prepared 2026-08-17 after research closeout and retrieval development planning.
> The canonical plan is
> [`docs/RELEASE_READINESS.md`](RELEASE_READINESS.md). This file contains only
> the next execution slice.

## Current State

- Research phase closed. Development plan: [`docs/RETRIEVAL_DEVELOPMENT_PLAN.md`](RETRIEVAL_DEVELOPMENT_PLAN.md).
- Archive findings: [`docs/ARCHIVE_FINDINGS.md`](ARCHIVE_FINDINGS.md).
- Current accepted retrieval baseline after token-coverage alignment: 50q
  turn-level R@1=0.64, R@5=0.82, R@10=0.82, MRR=0.7150, query p50 about 56ms.
- Naive two-turn composites and blanket field weighting were measured and
  rejected. Do not port either into the production index.

- v5.8.0, 15 crates, 229 registered tool implementations, 3,513 tests.
- **Release gates passed 2026-08-16**: fmt clean, clippy clean (`-D warnings`),
  3,513 tests pass, release build clean. Includes uncommitted work:
  `tools.usage_report`, daemon checkpoint interval, batch embedding fixes,
  grid-search results.
- **Release gate run complete. Tagged v5.8.0-rc1.** Fresh-install rehearsal
  passed (quickstart + doctor + curated smoke test, all healthy).
- **All P0, P1, and P2 items are now complete.** Phase B items B5–B7 are
  implemented (B5 is HMAC seal/verify, not a root of trust). B4 remains.
  `wm serve` defaults to curated.
- **Vector search wiring complete (2026-08-14):** `RecallEngine` is shared via
  `Arc<RecallEngine>` with `MemoryCreateTool`, `MemoryBatchCreateTool`, and
  `MemoryHybridRecallTool`. When `WM_EMBEDDER_ENDPOINT` is set, memory creation
  auto-embeds and `memory.hybrid_recall` fuses BM25 + vector cosine similarity.
  Without an embedder, all tools fall back to pure BM25. See
  [`docs/VECTOR_SEARCH_ROADMAP.md`](VECTOR_SEARCH_ROADMAP.md).
- **Batch embedding fix (2026-08-15):** Three bugs fixed in batch embedding
  (Tantivy writer lock conflict, embedder token limit, fallback writer).
- **Grid search completed (2026-08-15/16):** 4 successful weight
  combinations with live embedder (n=10, turn-level retrieval, not official
  LongMemEval QA). Hybrid lifted R@5 from 0.70 → 0.90 vs BM25+stem and
  dropped R@1 from 0.50 → 0.40. Weights did not differentiate. Three
  leftover `grid_*_10q.json` files plus the original combined summary were
  all-zero from the broken first pass; `grid_search_weights.json` was
  reconstructed 2026-08-16 from the four good runs. The current OR +
  token-coverage 50q baseline is R@1=0.64, R@5=0.82, R@10=0.82,
   MRR=0.7150, query p50 about 56ms. See `docs/ARCHIVE_FINDINGS.md` for
   rejected composite and field-weight experiments.
- **Evaluator/context A-B completed 2026-08-17:** the hardened evaluator
  retrieves 100 candidates and separately reports candidate presence and
  expected-session evidence. The no-context result reproduced
  R@1/R@5/R@10=0.64/0.82/0.82, MRR=0.7150, candidate presence=0.78, and
  session presence=0.84. Adjacent-turn terms raised candidate presence to 0.80
  but reduced R@1/R@5/MRR to 0.54/0.80/0.6523 and increased ingest/query
  latency. The contextual tag prototype is rejected; see
  `docs/ARCHIVE_FINDINGS.md`.
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

Release stabilization remains separate from the retrieval development slice.
The next development session should:

1. Start with the continuity protocol in `docs/RETRIEVAL_DEVELOPMENT_PLAN.md`.
2. Evaluate selective deterministic scoring over the existing broad candidate
   set; do not promote the rejected contextual tag prototype.
3. Compare optional hybrid and selective reranking only after candidate recall
   is understood.
4. Keep the fixed 50q evaluator as the regression protocol and report candidate
   presence, text evidence, and session evidence with every ranking experiment.

Release work remains:

5. Commit the existing release-candidate work as a separate slice.
6. Re-run the full v5.8.0 release gate from `cargo clean`.
7. Tag and publish v5.8.0 after the release checklist is clean.

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
