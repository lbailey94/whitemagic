# WhiteMagic v5 Release Readiness

**Prepared:** 2026-08-12
**Last updated:** 2026-08-16 (evening)
**Version under review:** v5.8.0
**Status:** All P0 and P1 release gates complete. P2 items complete. Phase B items B6, B7 complete; B5 (`wm seal`/`wm verify`) is implemented and awaiting a targeted test pass; B4 remains. Vector search wiring complete with batch embedding and adaptive chunking. Hybrid grid (n=10, turn-level retrieval, not official LongMemEval QA) lifted R@5 from 0.70 to 0.90 vs BM25+stem and dropped R@1 from 0.50 to 0.40; weight variations did not differentiate. OR + token-coverage is the new BM25 default and has not been re-scored on 10q/50q. `wm serve` with no flag now defaults to curated. Ready for v5.8.0 final after release gate re-run.

This document is the release-readiness source of truth. `README.md` should
explain the product, `PROGRESS.md` should record implementation history, and
`NEXT_SESSION.md` should contain the next execution slice. Release decisions,
acceptance criteria, and deferred work belong here.

## Release Position

WhiteMagic should be released first as a local-first memory and
session-continuity MCP server for coding agents.

The release promise is:

> Your agent can remember project context, find it after restart, and carry
> work across sessions without sending its memory store to a hosted service.

The 229-tool surface, cognitive cycles, Sangha mesh, self-play, imagination,
polyglot integrations, and learned routing remain valuable research and
extension surfaces. They are not the v1 product promise and must not expand the
release scope until the memory boundary is dependable.

## Evidence So Far

Verified on 2026-08-13 (Phase A of PET hardening, committed as `1dc29b6`;
P0/P1 gates completed evening 2026-08-13):

- `cargo test --workspace`: 3,515 tests passed.
- Consistency check fix: `check_consistency()` now iterates `memory_galaxies()`
  (10) instead of `all()` (14), preventing false-positive drift from non-memory
  galaxies (Karma, Dharma, Associations, Embeddings) that are intentionally not
  indexed in Tantivy.
- `cargo fmt --all -- --check`: passed.
- `cargo clippy --all-targets -- -D warnings`: passed.
- `cargo build --release --bin wm`: passed.
- **B7: Store permissions (0700)**: `MemoryStore::open()` creates the store
  directory with mode `0o700` on Unix. Regression test verifies permissions.
- **P2-1: NLU abstention**: when NLU routing returns `gnosis` with confidence
  < 0.15, the meta-tool abstains and returns an error suggesting explicit
  routing instead of dispatching to the wrong tool. 2 tests.
- **P2-2: Experimental labeling**: `imagine.*` and `selfplay.*` tool
  descriptions prefixed with `[Experimental]`. AGENTS.md updated.
- **B6: Untrusted `_meta` stripping**: `_meta` is stripped from tool arguments
  before dispatch in both `McpServer::handle_tools_call` and `WmMetaTool::call`,
  preventing untrusted callers from injecting compartment/identity overrides via
  nested args. 1 test.
- **Misc: Release workflow artifact naming**: release assets now use
  per-platform names (`wm-linux-x86_64`, `wm-macos-x86_64`, etc.) matching
  `install.sh` expectations.
- Effect inventory audit (`crates/wm-mcp/src/effect_audit.rs`, 16 CI tests):
  static declaration checks, a behavioral sweep proving no store-local tool
  mutates LMDB without declaring writes, and mutator spot-checks through the
  real pipeline; 13 false declarations found and fixed.
- ResourceRules (Yama) evaluated on every dispatch: write/spawn/network
  budgets block, novelty flags reach responses, autonomous human-review and
  purpose violations block; a runtime Satya check refuses `galaxy=citta`
  writes without evidence.
- Write-audit journal (`wm-governance::WriteAuditJournal`): append-only LMDB
  record per dispatch (tool, memory id, content hash, timestamp, declared vs
  actual writes) surfaced in `wm doctor`, flushed on shutdown; a deliberately
  misdeclaring tool is detected.

Verified on 2026-08-12:

- `cargo test --workspace --quiet`: 3,447 tests passed.
- `cargo fmt --all -- --check`: passed.
- `cargo clippy --all-targets -- -D warnings`: passed.
- `cargo build --release --bin wm`: passed.
- An explicit curated-profile process rehearsal passed memory create, search,
  FTS-based hybrid recall, session start, transaction begin/create/rollback,
  and claims calibration.
- A restart rehearsal found a memory created by one process after restarting a
  second process.

These checks used explicit `route=` calls and a temporary store. They prove the
deterministic path, not natural-language routing quality, exact transaction
restoration, or multi-user security. The rehearsal is not yet a committed,
repeatable smoke test in CI.

## Product Decisions

These decisions prevent the release effort from turning into another feature
phase:

1. **Stable boundary:** memory, search, sessions, claims calibration,
   transactions, diagnostics, export/backup, and recovery.
2. **Reliable invocation:** explicit `route=` is the contract. Natural-language
   routing is a convenience layer that may abstain and must never reach
   destructive tools.
3. **Search semantics:** BM25/Tantivy is the honest default. Vector recall is
  now wired end to end — when `WM_EMBEDDER_ENDPOINT` is configured, memory
  creation auto-embeds (with adaptive chunking for embedder token limits) and
  `memory.hybrid_recall` fuses BM25 + vector cosine similarity. Without an
  embedder, all tools fall back to pure BM25. Batch embedding in
  `memory.batch_create` uses chunked `embed_batch()` calls with a single
  Tantivy commit. See [`docs/VECTOR_SEARCH_ROADMAP.md`](VECTOR_SEARCH_ROADMAP.md)
  for the improvement catalog and roadmap.
4. **Deployment model:** v5.7.x is a trusted local single-user process. It must
   not imply authenticated multi-tenant authorization through MCP `_meta`.
5. **Surface policy:** curated is the product surface; full is an opt-in
   archive/research surface. `wm serve` with no `--profile` and no
   `WM_TOOL_*` env now defaults to curated. `wm daemon` and library
   constructors still default to full because cycle tools live outside
   curated. Client configs may keep an explicit `--profile curated`.
6. **Maturity language:** research features are labeled experimental unless a
   live production path and acceptance test exist.

## Blockers

### P0: Boundary Safety

**Goal:** every advertised safety or access boundary must be enforced at the
actual store and dispatch boundary.

Open work:

- ~~Fix CLI profile precedence.~~ ✅ Fixed 2026-08-13 — `resolve_tool_profile`
  applies `WM_TOOL_ALLOWLIST` > `--profile` > `WM_TOOL_PROFILE` > `full`, with
  unit tests and a process-level verification.
- ~~Make `--readonly` store-wide.~~ ✅ Fixed 2026-08-13 — the dispatch pipeline
  refuses every tool that declares writes; karma, friction auto-log, and
  mutable-state persistence are suppressed in read-only mode.
- ~~Reject unknown compartments instead of granting full access.~~ ✅ Fixed
  2026-08-13 — unknown compartment values now fail closed for both reads and
  writes.
- ~~Enforce `is_private` on MCP responses and `model_exclude` on model evidence
  and reasoning paths.~~ ✅ Fixed 2026-08-13 — `is_private` memories are
  excluded from memory.read/list/query/search/hybrid_recall/batch_read/sort/
  filter/nearby/vector.search/chat responses (read reports `not_found`);
  `model_exclude` memories are filtered from reasoning, think, explain,
  bicameral hemisphere evidence, imagination scenario context, and self-play
  task context.
- ~~Audit every `EffectRow` against actual writes, network calls, process calls,
  actuator calls, and broad scans. Put resource rules and transaction firewall
  decisions on the central dispatch path or explicitly remove their claims.~~
  ✅ Fixed 2026-08-13 — the effect inventory audit is now 16 CI tests
  (`crates/wm-mcp/src/effect_audit.rs`): static declaration checks over the
  full registry (destructive ⇒ writes, spawns ⇒ Process), a behavioral sweep
  proving no store-local tool mutates LMDB without declaring writes, and
  mutator spot-checks dispatched through the real pipeline. The audit found
  and fixed 13 false declarations (transaction.commit/rollback,
  galaxy.purge/transfer/restore, memory.consolidate/deduplicate/decay/
  update/tag/create/delete, system.flush, 8 autonomous-cycle tools).
  `ResourceRules` (Yama) is now evaluated on the dispatch path: write/spawn/
  network budgets block, novelty flags surface on responses, autonomous
  human-review/purpose violations block. A runtime Satya check closes the
  `galaxy=citta` write bypass.

Acceptance criteria:

- ✅ A negative test proves every mutating registered tool fails in read-only mode.
- ✅ Unknown compartment values fail closed.
- ✅ Private memories never appear in MCP read/search/list/query results.
- ✅ Excluded memories never enter model context or reasoning evidence.
- ✅ A tested effect inventory matches the registered tool behavior — the
  effect audit suite (16 tests in `crates/wm-mcp/src/effect_audit.rs`) proves
  no tool mutates the store without declaring it, and that the
  release-surface mutators actually mutate and cover the change.
- ~~Natural-language calls cannot reach destructive tools, including rollback.~~
  ✅ Fixed 2026-08-13 — the destructive gate in `WmMetaTool::call` now fires
  *before* the required-arg check (was after, causing the gate message to be
  masked by missing-arg errors). A comprehensive sweep test
  (`nlu_cannot_reach_any_destructive_tool`) iterates every registered
  destructive tool and verifies none can return success via NLU, using both
  bare tool names and natural-language phrases. Existing per-tool tests
  cover `memory.delete` with and without `confirm: true`.

### P0: Store and Transaction Correctness

**Goal:** a successful write, update, rollback, and search result have coherent
semantics across LMDB and Tantivy.

Open work:

- ~~Redesign transaction snapshots around exact serialized records or an undo
  journal.~~ ✅ Fixed 2026-08-13 — snapshots serialize complete `Memory`
  records; rollback restores byte-equivalent records with original UUIDs,
  timestamps, hashes, coordinates, privacy flags, and provenance (legacy
  snapshots still restore via field-level fallback).
- ~~Remove the 10,000-memory snapshot ceiling.~~ ✅ Fixed 2026-08-13 —
  snapshots scan every memory; regression test covers 10,001 records.
- ~~Keep transaction state available until snapshot validation and restoration
  succeed.~~ ✅ Fixed 2026-08-13 — rollback validates and restores before
  clearing the active transaction; a failed restore keeps the transaction
  retryable.
- ~~Delete or mark committed journal snapshots.~~ ✅ Fixed 2026-08-13 — commit
  removes the rollback snapshot and de-indexes it.
- ~~Remove stale LMDB secondary index entries before overwriting a memory. Recompute
  content hashes when content changes.~~ ✅ Fixed 2026-08-13 — `MemoryStore::put`
  removes the previous record's index entries on overwrite; `memory.update`
  recomputes the content hash when content changes. Regression tests cover
  tags, importance ranges, and content hashes.
- ~~Define the LMDB/Tantivy consistency contract. If indexing is asynchronous or
  best-effort, expose degraded index state and provide a safe rebuild path.~~
  ✅ Done 2026-08-13 — `IndexHealth` struct tracks successes/failures/last_error
  on every `add_document` call. `check_consistency()` compares LMDB memory counts
  to Tantivy doc counts per galaxy, returning a `ConsistencyReport` with drift
  detection. `system.health` tool now reports `index_health` (degraded flag,
  failure count, last error) and `index_consistency` (per-galaxy drift, total
  counts). When no search engine is configured, reports `unavailable` with
  `degraded: true` instead of silently healthy. `wm doctor` opens the Tantivy
  index read-only and runs the same consistency + health checks, printing
  `[WARN]` lines with `wm reindex` remediation guidance. Safe rebuild path:
  `wm reindex` (full) or `wm reindex --galaxy <name>` (filtered) reconstructs
  the index from LMDB. 6 new tests cover consistency no-drift, drift detection,
  index health tracking, system.health with search, drift detection via tool,
  and unavailable-index honesty.
- ~~Fix filtered reindexing so `--galaxy codex` cannot delete documents from other
  galaxies.~~ ✅ Fixed 2026-08-13 — filtered rebuilds delete and re-index only
  the selected galaxies; regression test proves unselected galaxies keep their
  documents.

Acceptance criteria:

- ✅ Rollback restores byte-equivalent memory records and original UUIDs.
- ✅ Rollback tests cover metadata, indexes, search results, and a failed restore.
- ✅ Update tests prove old tags, importance values, timestamps, and hashes are no
  longer queryable.
- ✅ A filtered reindex preserves all unselected galaxies.
- ~~Search health reports stale or unavailable indexes instead of silently saying
  the system is healthy.~~ ✅ Done 2026-08-13 — `system.health` now includes
  `index_health` and `index_consistency` fields. When the search engine is
  absent, reports `{"status": "unavailable", "degraded": true}`. When present,
  reports success/failure counts, degraded flag, last error, per-galaxy drift,
  and total LMDB vs Tantivy counts. `wm doctor` performs the same checks and
  prints actionable `[WARN]` lines. The `healthy` field is now `false` when the
  index is degraded or drifted.

### P1: Curated Product Contract

**Goal:** clients can discover and use a small, truthful, stable surface.

Open work:

- ~~Generate profile manifests and counts from the final registry. Remove the
  dead `galaxy.list` entry or implement the route.~~ ✅ Done 2026-08-13 — the
  dead `galaxy.list` prefix is removed from the curated profile; regression
  tests assert curated discovery excludes galaxy tools.
- ~~Make `tools/list`, `tools.list`, descriptions, and examples reflect the
  active profile rather than hardcoded full-surface counts.~~ ✅ Done
  2026-08-13.
- ~~Decide whether `claims` remains an action-based tool or add explicit aliases
  such as `claims.calibration`. Document the chosen route exactly.~~ ✅ Done
  2026-08-13 — explicit alias routes `claims.add/resolve/status/list/calibration`
  are registered alongside the action-based `claims` tool, with tests.
- ~~Decide whether `memory.hybrid_recall` means FTS plus metadata or true vector
  plus FTS fusion. Align the name, description, implementation, and tests.~~ ✅
  Decided 2026-08-13 — `memory.hybrid_recall` is Tantivy BM25 + importance/
  metadata filtering; the tool description states this explicitly. Vector
  fusion remains a separate capability until the embedding write path is wired
  end to end. **Update 2026-08-14:** Vector fusion is now wired. When a real
  embedder is available (`WM_EMBEDDER_ENDPOINT`), `memory.hybrid_recall` runs
  `RecallEngine::hybrid_search()` as Phase 0 (BM25 + vector cosine fusion),
  falling back to BM25-only phases when no embedder is configured. The tool
  description has been updated to reflect this.
- ~~Add generated or native argument schemas for the curated tools. The generic
  `args` object is acceptable internally but weak for client onboarding.~~ ✅
  Done 2026-08-13 — `Tool::input_schema()` (default empty) implemented for the
  core curated tools (memory CRUD/search/query/chat, sessions, transactions,
  claims + aliases) and surfaced in `tools.list` output, with tests.
- Add export, backup, index-health, and recovery instructions to the core
  workflow.

Acceptance criteria:

- A fresh client can discover only the active product surface.
- Every documented route exists and every exposed route has an argument example.
- The curated smoke test uses the documented route names without hidden setup.
- The memory workflow works with no embedder or LLM endpoint configured.

### P1: Release Evidence and Packaging

**Goal:** release confidence comes from repeatable evidence, not an ad hoc local
run.

Open work:

- ~~Add a committed process-level smoke test for initialize, tools/list, curated
  dispatch, restart persistence, session continuity, rollback, and claims
  calibration.~~ ✅ Done 2026-08-13 — `scripts/curated_smoke_test.py` asserts
  JSON payloads for the full curated workflow, restart persistence (exact UUID
  preservation), and read-only enforcement.
- ~~Run the smoke test against a fresh temporary store in CI and in the release
  workflow using the release binary.~~ ✅ Done 2026-08-13 — `ci.yml` gained a
  curated smoke job; `release.yml` runs the smoke test against the freshly
  built Linux release binary before artifact upload.
- ~~Add native curated MCP configurations for Claude Desktop, Cursor, and
  Windsurf. Include an explicit `--profile curated` until profile precedence is
  fixed.~~ ✅ Done 2026-08-13 — all four client config templates launch the
  native binary with `--profile curated` (paths are local-dev templates;
  generic install-path docs remain packaging work).
- ~~Add release checksums and a short install path for the published binaries.~~
  ✅ Done 2026-08-13 — `scripts/install.sh` downloads the release binary for
  the user's platform, verifies the SHA-256 checksum, and installs to
  `~/.local/bin/wm`. The release workflow already generates per-platform
  checksums and publishes them alongside the binaries. Usage:
  `curl -fsSL https://raw.githubusercontent.com/lucas/whitemagic/main/scripts/install.sh | sh`
- ~~Compile and test the optional Python, ONNX, LanceDB, and other supported
  feature combinations in a separate compatibility job.~~ ✅ Done 2026-08-13 —
  CI gained an optional-feature build matrix for `wm-mcp/python`,
  `wm-memory/lancedb`, and `wm-memory/onnx`. Julia is excluded until a CI
  runner with a Julia runtime is provided.

  Optional feature support matrix for the v5.8 release:

  | Feature | Crate | Cargo feature | CI status | Release status |
  |---------|-------|---------------|-----------|----------------|
  | Python (PyO3) | wm-mcp | `python` | Build-only | Supported (opt-in) |
  | LanceDB vectors | wm-memory | `lancedb` | Build-only | Supported (opt-in) |
  | ONNX embedder | wm-memory | `onnx` | Build-only | Supported (opt-in) |
  | Julia (jlrs) | wm-polyglot | `julia` | Not in CI | Unsupported — requires Julia 1.10+ runtime; compile from source with `--features wm-polyglot/julia` |
  | Haskell | wm-polyglot | — (FFI) | Not in CI | Unsupported — requires GHC/libghc; compile from source |
  | Zig | wm-polyglot | — (C ABI) | Not in CI | Unsupported — requires Zig compiler; compile from source |
  | Koka | wm-polyglot | — (C ABI) | Not in CI | Unsupported — requires Koka compiler; compile from source |

  The release binary is built with default features (no optional features
  enabled). Users who need Python, LanceDB, or ONNX support should build
  from source with the appropriate `--features` flag.
- ~~Repair the benchmark comparison job before treating performance regressions as
  gated.~~ ✅ Done 2026-08-13 — PR results are compared against an imported
  baseline from the base branch (advisory, posted to the step summary).

Acceptance criteria:

- ✅ One documented command creates a fresh store and completes the smoke test.
- ✅ Release CI exercises at least one Linux release binary end to end.
- ~~Client configuration examples launch the same versioned binary that was built.~~
  ✅ Done 2026-08-13 — `docs/MCP_CONFIG_GUIDE.md` references `~/.local/bin/wm`
  (the `install.sh` install path) in all config templates.
- ~~Optional features are either tested or explicitly marked unsupported for the
  release.~~ ✅ Done 2026-08-13 — feature support matrix documents CI status and
  release status for all optional features (Python, LanceDB, ONNX, Julia,
  Haskell, Zig, Koka).

### P2: Router and Research Surfaces

**Goal:** improve convenience without making experimental behavior a release
dependency.

Open work after P0/P1:

- Keep explicit routing as the fallback and add confidence/margin abstention to
  natural-language routing.
- Evaluate router quality against a labeled corpus, not shadow disagreement
  alone. Do not promote the embedding router on a 38/56 judged result.
- Wire the learned inference router into production or label it library-only.
- Label self-play LoRA updates, imagination stubs, and autonomous learning as
  experimental until the actual model-update paths exist.
- Treat routing-table consolidation, the `McpServer` split, and a tool
  scaffolding macro as maintainability follow-ups, not release blockers.

## Next Execution Order

All P0 and P1 items are complete. Vector search wiring is complete. The next
steps are:

1. **Release gate run**: execute every item in the Release Gate section
   against the current commit on a clean machine (`cargo clean` first).
2. **Tag the release candidate**: `git tag v5.8.0-rc2` and push to trigger
   the release workflow (per-platform binaries + checksums).
3. **Fresh-install rehearsal**: run `scripts/install.sh` against the RC,
   then `wm doctor`, then `scripts/curated_smoke_test.py`.
4. **Recall measurement** (see
   [`docs/VECTOR_SEARCH_ROADMAP.md`](VECTOR_SEARCH_ROADMAP.md)):
   - Score OR + token-coverage on the same 10q (then 50q) BM25+stem set
   - Do not cite n=10 hybrid R@5=0.90 as official LongMemEval QA
   - Hybrid 50q only after OR is scored; weights already failed to differentiate
5. **P2 items** (post-release, not blockers):
   - NLU abstention with confidence/margin thresholds
   - Router quality evaluation against a labeled corpus
   - Learned inference router promotion or library-only labeling
   - Self-play/imagination experimental labeling
6. **Phase B** (v5.9 PET hardening theme):
   - B4: sandbox mode for tool execution
   - ~~B5: store seal/verify (tamper detection)~~ implemented as HMAC
     manifest + `wm seal`/`wm verify`; not a cryptographic root of trust
     against an adversary who can replace `.seal_key`
   - ~~B6: untrusted `_meta` handling by default~~
   - ~~B7: store permission hygiene (`0700`)~~

## Release Gate

The release candidate is **no-go** if any item below fails:

- `cargo fmt --all -- --check`
- `cargo test --workspace --all-targets`
- `cargo clippy --all-targets -- -D warnings`
- `cargo build --release --bin wm`
- Curated process smoke test on a fresh store
- Restart persistence smoke test
- Read-only negative test for every mutating curated tool
- Unknown-compartment rejection test
- Private/model-excluded memory filtering tests
- Exact transaction rollback and commit-cleanup tests
- Secondary-index update and filtered-reindex tests
- Destructive NLU reachability test
- Index consistency and health reporting test (system.health + wm doctor)
- Release configuration launch test
- **Fresh-install rehearsal**: `cargo clean` followed by a clean
  `cargo build --release` and the full gate run, simulating a new machine
  (no incremental caches, no pre-existing store).
- **Clean-machine client handshake**: the curated smoke test run against the
  release binary with no prior store and a standards-compliant MCP handshake
  (initialize → notifications → ping → tools/list).

The release candidate may ship without a live embedder, LLM endpoint, daemon,
Sangha mesh, self-play adapter training, or polyglot runtime. Those capabilities
must either be tested in their own feature matrix or clearly labeled optional
and experimental.

## Public-Claims Discipline

Every benchmark, test count, performance number, or feature claim in the
README, website, registry listing, or launch content must cite a fresh run
against the release commit, stamped with configuration and date. Stale counts
or unreproduced claims are release blockers, not documentation bugs.

- Counts (`3,515 tests`, `229 tools`) must come from a run of the release
  commit.
- Benchmarks must come from the release binary on a named machine
  configuration.
- Claims written without a cited run are removed or marked `[Speculative]`
  until a run exists.

## Launch Assets

Ported from the retired documentation vault for the release:

- `SECURITY.md`, `PRIVACY_POLICY.md`, `TERMS_OF_SERVICE.md`,
  `CODE_OF_CONDUCT.md`, `CITATION.cff` — legal kit.
- `docs/VOICE_TONE_GUIDE.md` — launch copy rules.
- `docs/MCP_CONFIG_GUIDE.md` — per-client MCP configuration.
- `docs/QUICKSTART.md` — five-minute install + verify path.
- `docs/MCP_REGISTRY_LISTING.md` — registry copy and quality checklist.
- `docs/MODEL_GUIDE.md` — one-page agent primer for the curated profile.

See [`docs/PRE_RELEASE_LAUNCH_PLAN.md`](PRE_RELEASE_LAUNCH_PLAN.md) for the
full port inventory and execution order.

## Documentation Plan

- `README.md`: product promise, curated surface, honest maturity language, and
  release-readiness link.
- `docs/RELEASE_READINESS.md`: this plan, gates, and decisions.
- `docs/PRE_RELEASE_LAUNCH_PLAN.md`: launch actions distilled from the retired
  WMdocs vault (assets to reuse, ideas to port, items to skip).
- `docs/PET_HARDENING.md`: post-release hardening strategy — trustworthy
  declarations, sandbox/seal/identity hardening, and insider-accident
  resistance.
- `docs/VECTOR_SEARCH_ROADMAP.md`: vector search wiring status, quick wins,
  and improvement catalog for hybrid BM25 + vector recall.
- `docs/ARCHIVE_CAPABILITY_MAP.md`: vetted ideas from the retired projects and
  the v6+ research direction.
- `docs/NEXT_SESSION.md`: the current execution slice only.
- `docs/PROGRESS.md`: verified history and blocker status.
- `python/README.md`: v5 naming and current native/Python configuration, after
  the release path is finalized.
- `CHANGELOG.md`: only verified user-visible fixes, route changes, and release
  behavior.

The untracked industry-analysis note in `docs/notes/` remains a source note. It
is not the operational release plan and should not be overwritten.
