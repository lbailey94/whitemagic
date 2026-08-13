# WhiteMagic v5 Release Readiness

**Prepared:** 2026-08-12
**Target session:** 2026-08-13
**Version under review:** v5.7.7
**Status:** Feature phases complete; release stabilization is not complete

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
   optional until the write, persistence, restart, and query paths are wired
   end to end.
4. **Deployment model:** v5.7.x is a trusted local single-user process. It must
   not imply authenticated multi-tenant authorization through MCP `_meta`.
5. **Surface policy:** curated is the product surface; full is an opt-in
   archive/research surface. If changing the historical default is deferred
   for compatibility, all release configurations must still select curated
   explicitly.
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
- Audit every `EffectRow` against actual writes, network calls, process calls,
  actuator calls, and broad scans. Put resource rules and transaction firewall
  decisions on the central dispatch path or explicitly remove their claims.

Acceptance criteria:

- ✅ A negative test proves every mutating registered tool fails in read-only mode.
- ✅ Unknown compartment values fail closed.
- ✅ Private memories never appear in MCP read/search/list/query results.
- ✅ Excluded memories never enter model context or reasoning evidence.
- A generated or tested effect inventory matches the registered tool behavior.
- Natural-language calls cannot reach destructive tools, including rollback.

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
- Define the LMDB/Tantivy consistency contract. If indexing is asynchronous or
  best-effort, expose degraded index state and provide a safe rebuild path.
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
- Search health reports stale or unavailable indexes instead of silently saying
  the system is healthy.

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
- Decide whether `memory.hybrid_recall` means FTS plus metadata or true vector
  plus FTS fusion. Align the name, description, implementation, and tests.
- Add generated or native argument schemas for the curated tools. The generic
  `args` object is acceptable internally but weak for client onboarding.
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
- Add release checksums and a short install path for the published binaries.
- Compile and test the optional Python, ONNX, LanceDB, and other supported
  feature combinations in a separate compatibility job.
- Repair the benchmark comparison job before treating performance regressions as
  gated.

Acceptance criteria:

- ✅ One documented command creates a fresh store and completes the smoke test.
- ✅ Release CI exercises at least one Linux release binary end to end.
- Client configuration examples launch the same versioned binary that was built.
- Optional features are either tested or explicitly marked unsupported for the
  release.

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

## Tomorrow's Execution Order

The next session should be a stabilization sprint in this order:

1. Add regression tests for profile precedence, read-only writes, unknown
   compartments, and exact route/profile discovery.
2. Fix the profile and read-only boundary so the release smoke test has a
   truthful foundation.
3. Implement exact, failure-safe transaction restore and add identity/metadata
   assertions.
4. Fix secondary-index update semantics and filtered reindex behavior.
5. Add the committed curated process smoke test and wire it into CI/release.
6. Update client configs, README, Python documentation, and the changelog to
   match verified behavior.
7. Only if the blockers are green, run the embedder shadow set and decide
   whether NLU needs an abstention or description-quality iteration.

If the full list does not fit in one session, stop after the first green release
gate rather than starting another research subsystem. The correct partial
outcome is a smaller, safer release candidate with clearly deferred features.

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
- Release configuration launch test

The release candidate may ship without a live embedder, LLM endpoint, daemon,
Sangha mesh, self-play adapter training, or polyglot runtime. Those capabilities
must either be tested in their own feature matrix or clearly labeled optional
and experimental.

## Documentation Plan

- `README.md`: product promise, curated surface, honest maturity language, and
  release-readiness link.
- `docs/RELEASE_READINESS.md`: this plan, gates, and decisions.
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
