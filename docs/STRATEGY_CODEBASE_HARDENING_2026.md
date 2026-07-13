# WhiteMagic Codebase Hardening Strategy

**Date**: 2026-07-12  
**Status**: Phase 0-1 complete — Phase 2 (Memory and Galaxy Boundary Consolidation) in progress  
**Scope**: Runtime code, memory, dispatch, governance, native bridges, packaging, tests, and operational reliability  
**Out of scope for this strategy**: Deep review of Markdown archives, galaxy contents, and historical design documents

---

## 1. Executive Summary

WhiteMagic has a strong central concept: an MCP-facing tool runtime that combines lazy dispatch, composable middleware, persistent memory, ethical governance, session continuity, and optional native acceleration.

The primary risk is not missing capability. It is boundary complexity. Historical compatibility layers, experimental subsystems, native bridges, and production-facing services currently converge through shared singletons, broad fallbacks, and multiple public entry points.

This strategy resolves the issues in dependency order:

1. Establish a protected baseline and executable contracts.
2. Define one canonical runtime and one canonical memory boundary.
3. Make user and galaxy context request-scoped.
4. Make security, caching, and fast paths policy-safe.
5. Replace silent partial failure with typed outcomes.
6. Harden async execution and native process supervision.
7. Optimize federated retrieval using measured query plans.
8. Consolidate compatibility surfaces and generate metadata.
9. Add deterministic replay, fault injection, and operational health tooling.

The guiding rule is:

> **Reduce ambiguity at boundaries before increasing intelligence inside components.**

---

## 2. Success Definition

The hardening program is complete when all of the following are true:

- Every tool call enters through one documented runtime contract.
- Every memory read and write is routed through one user- and galaxy-aware abstraction.
- No request can accidentally inherit another request's user, galaxy, permissions, cache, or governance context.
- Economic and destructive actions fail closed when governance is unavailable.
- Fast paths are registry-declared, mechanically verified, and auditable.
- Partial operations report errors explicitly and support rollback where destructive.
- Native bridges have bounded I/O, supervised process lifecycles, and observable failure states.
- Search latency is measured by stage and federation behavior is bounded.
- Tool schemas, counts, safety metadata, dispatch mappings, and public surfaces are generated or validated from one registry.
- Focused contract tests, integration tests, fault-injection tests, and performance budgets pass in CI.
- No phase changes the user's in-progress work without an explicit migration and rollback plan.

---

## 3. Non-Negotiable Engineering Invariants

### 3.1 Data and identity

- A memory belongs to exactly one `(user_id, galaxy)` namespace unless explicitly exported.
- User and galaxy context is request-scoped, never inferred from mutable global state during a request.
- A backend failure cannot silently redirect a write to a different user's or galaxy's database.
- A successful write must be observable through the same canonical read façade.

### 3.2 Governance and security

- Economic, destructive, model-loading, and external-side-effect tools fail closed when required policy services are unavailable.
- Cache hits cannot bypass privacy, identity, authorization, or policy boundaries.
- Fast paths are opt-in by registry metadata, not inferred from name prefixes.
- Security failures include request ID, agent ID, tool name, policy profile, and failure reason.

### 3.3 Reliability

- Optional capability failures degrade only the capability that failed.
- Data corruption, schema errors, and programming errors are not treated as ordinary optional-dependency misses.
- Partial operations return structured failure information.
- Every background process and native bridge has shutdown, timeout, restart, and leak-detection behavior.

### 3.4 Compatibility

- Existing public tool names remain supported through explicit adapters during migration.
- Compatibility adapters delegate to the canonical implementation; they do not create alternate storage or policy paths.
- Deprecations have a documented removal version and migration test.

---

## 4. Phase 0 — Baseline, Protection, and Measurement ✅ COMPLETE

**Priority**: P0  
**Dependency**: None  
**Exit target**: A reproducible baseline exists before architectural edits  
**Completed**: 2026-07-13 — baseline report, stash, tag, risk register all in place

### Work

1. Record the current Git status and identify all pre-existing modifications.
2. Create a protected baseline branch or patch snapshot outside the working tree.
3. Run the focused runtime tests:
   - dispatch and middleware contract tests
   - transaction firewall tests
   - galaxy and tiered-backend tests
   - Koka/native bridge tests
   - memory serialization and search tests
4. Run compilation, Ruff, type checking, and `git diff --check` independently.
5. Capture baseline metrics:
   - MCP startup latency
   - first tool-call latency
   - common read-tool latency
   - memory create/recall/search latency
   - cache hit/miss rate
   - native bridge timeout/restart rate
6. Create a failure taxonomy and assign each existing failure to:
   - expected degradation
   - test defect
   - implementation defect
   - environmental dependency
   - unclassified

### Required artifacts

- Baseline test report
- Baseline performance report
- Current registry/tool-surface inventory
- Protected working-tree manifest
- Risk register with owners and phase assignment

### Exit criteria

- Baseline commands are documented and repeatable.
- No implementation change begins while the current worktree ownership is unclear.
- Every later phase has at least one regression test and one rollback action.

---

## 5. Phase 1 — Canonical Runtime Contract ✅ COMPLETE

**Priority**: P0  
**Dependency**: Phase 0  
**Exit target**: One runtime boundary with adapters around it  
**Completed**: 2026-07-13 — ToolRuntime, ToolRequest, ToolResult, ExecutionMode, canonical.py, feature flag, 35 contract tests  
**Deferred items resolved in Phase 2**: (a) Name-pattern inference in dispatch_table fast-path documented with 7 tests in `test_fast_path_name_pattern.py` — `gana_ghost.` prefix migration deferred to Phase 3; (b) Formal async/sync adapter equivalence test added — 12 tests in `test_async_sync_equivalence.py`

### Problem addressed

WhiteMagic currently has multiple overlapping entry paths: MCP routing, PRAT routing, dispatch, unified API calls, direct handler access, and bridge fallbacks.

### Work

1. Define a typed `ToolRequest` containing:
   - request ID
   - user ID
   - agent ID
   - tool name
   - arguments
   - requested mode
   - policy profile
   - galaxy context
2. Define a typed `ToolResult` containing:
   - status
   - result payload
   - error code
   - request ID
   - execution metadata
   - degradation information
3. Designate one canonical `ToolRuntime.execute()` entry point.
4. Make `dispatch()`, `call_tool()`, MCP handlers, and compatibility APIs delegate to it.
5. Keep existing names as adapters with deprecation telemetry.
6. Move canonical name normalization, schema validation, idempotency, and envelope normalization into the runtime boundary.
7. Add an explicit execution-mode enum:
   - full
   - read-only audited
   - internal
   - maintenance
8. Remove implicit behavior based solely on tool-name string patterns.

### Tests

- Every public entry point produces equivalent `ToolResult` envelopes.
- Request and agent IDs survive every adapter.
- Aliases resolve to one canonical tool.
- Unknown tools produce one stable error contract.
- Async and sync adapters are behaviorally equivalent.

### Rollback

Keep the old dispatch path behind a feature flag until contract parity tests pass. Revert adapter wiring without reverting domain handlers.

---

## 6. Phase 2 — Memory and Galaxy Boundary Consolidation (In Progress)

**Priority**: P0  
**Dependency**: Phase 1  
**Exit target**: One memory façade and request-scoped namespace routing
**Started**: 2026-07-13

### Completed Slices

- **Slice 1** ✅: `MemoryBackendProtocol` defined in `backends/protocol.py` — structural `typing.Protocol` covering store, recall, search, delete, coordinates, associations, integrity, stats, close. Includes `validate_galaxy_name()` and `validate_user_id()` with path traversal protection.
- **Slice 2** ✅: `MemoryContext` wired into `UnifiedMemory.store()`, `.recall()`, `.search()`, `.update_memory()` as optional `memory_context` parameter. When provided: galaxy/agent_id overridden from context, `_user_id`/`_namespace` stamped in metadata, recall/search filter by user namespace, update rejects cross-namespace writes. Fully backward compatible (no context = current behavior).
- **Slice 3** ✅: `GalaxyAwareBackend` now accepts `user_id` param (default `"local"`). `_resolve_galaxies_dir()` uses `self._user_id` instead of hardcoded `"local"`. Backend cache keys are `"user_id/galaxy_name"` for namespace isolation. Galaxy name validation uses `validate_galaxy_name()`.
- **Slice 4** ✅: Filesystem name validation implemented in `protocol.py` — `validate_galaxy_name()` and `validate_user_id()` sanitize names, reject path traversal, reject empty/whitespace-only names.
- **Slice 5** ✅: 44 isolation tests in `test_phase2_memory_boundary.py` — two-user galaxy collision, namespace isolation for store/recall/search/update, write-through visibility, missing galaxy DB handling, export namespace boundary.
- **Phase 1 deferred (a)** ✅: Name-pattern inference documented with 7 tests in `test_fast_path_name_pattern.py` — `gana_ghost.` prefix migration deferred to Phase 3.
- **Phase 1 deferred (b)** ✅: Async/sync adapter equivalence test added — 12 tests in `test_async_sync_equivalence.py`.

**Test results**: 328 passed, 0 failed (158 hardening + 11 request-scoped galaxy + 159 existing memory/galaxy tests)

### Remaining Work

5. Migrate consumers to explicit façade methods (57 modules in inventory — currently transparent via `__getattr__`).
9. Make singleton caches keyed by namespace or replace them with context-managed instances.
11. Add namespace migration tooling for existing local databases.

### Problem addressed

`UnifiedMemory` exposes both a galaxy-aware backend and a legacy raw backend. Other modules still access the raw backend directly. Galaxy selection and singleton state are process-global.

### Work

1. ✅ Define a `MemoryBackend` protocol for store, recall, update, delete, search, coordinates, associations, and integrity operations.
2. ✅ Implement a routing façade that satisfies that protocol. (`GalaxyAwareBackend` serves this role)
3. ✅ Make `UnifiedMemory.backend` resolve to the façade for compatibility. (`.backend` now points to `GalaxyAwareBackend` with `__getattr__` delegation + `pool` property)
4. ✅ Inventory every direct `.backend`, raw pool, and direct SQLite consumer. (57 modules in `test_backend_inventory.py`)
5. ⏳ Migrate consumers to explicit façade methods. (57 modules in inventory — `.backend` now proxies through `GalaxyAwareBackend.__getattr__` so consumers work transparently, but should be migrated to explicit methods in Phase 3)
6. ✅ Add `MemoryContext(user_id, galaxy)` and require it for request-bound operations.
7. ✅ Pass `user_id` through:
   - `ToolRequest` (Phase 1)
   - `UnifiedMemory` (Phase 2 Slice 2)
   - `GalaxyAwareBackend` (Phase 2 Slice 3)
   - galaxy manager operations (v23.2.0)
   - caches and embedding indexes (Phase 3)
8. ✅ Remove global active-galaxy mutation from request handling. (`get_memory_for_galaxy()` + `galaxy_context()` added; `switch_galaxy()` deprecated with `DeprecationWarning`; API `_resolve_galaxy()` uses request-scoped resolution; `galaxy.use` tool handler added)
9. ⏳ Make singleton caches keyed by namespace or replace them with context-managed instances.
10. ✅ Validate filesystem names before routing and preserve the logical galaxy name separately from its safe path.
11. ⏳ Add namespace migration tooling for existing local databases.

### Tests

- Two users can create identically named galaxies without collision.
- Two concurrent requests cannot observe each other's active galaxy.
- A write through every compatibility API is visible through canonical recall.
- Coordinates, associations, embeddings, and audits land in the same namespace as the memory.
- Missing or corrupt galaxy databases produce explicit errors.
- Export/import cannot cross namespaces without explicit authorization.

### Rollback

Keep the legacy database read-only during migration. Write a namespace migration journal. Support restoring the pre-migration database from the Phase 0 snapshot.

---

## 7. Phase 3 — Governance, Security, Cache, and Fast-Path Hardening

**Priority**: P0  
**Dependency**: Phases 1–2  
**Exit target**: No security-sensitive path fails open or leaks across contexts

### 7.1 Transaction firewall

- Economic tools must block when the firewall cannot initialize, validate, or persist its decision.
- Separate `policy_denied`, `policy_unavailable`, `policy_malformed`, and `policy_storage_error`.
- Record blocked and unavailable decisions in an append-only security event stream.
- Require explicit override credentials or a documented maintenance mode for bypass.

### 7.2 Cache isolation

Include these fields in cache identity:

- user ID
- agent ID
- galaxy
- policy profile
- privacy classification
- tool schema/version
- relevant authorization scope

Do not cache private memory results by default. Add write-driven invalidation for memory, galaxy, permission, and policy changes.

### 7.3 Fast paths

Replace `_FAST_PATH_TOOLS` and broad prefixes with registry metadata. Require every fast-path tool to declare:

- no writes
- no external network
- no secrets
- no user-sensitive output
- no policy-dependent behavior

Retain a minimal audit envelope even on fast paths: request ID, tool, duration, result status, and principal.

### 7.4 Security tests

Add tests for:

- firewall dependency failure
- malformed policy
- cache cross-user isolation
- cache invalidation after writes
- permission changes after a cache entry exists
- fast-path tool mutation attempts
- private memory exclusion
- gateway failure and retry behavior

### Rollback

Run the new firewall in shadow mode first for non-economic tools. For economic tools, activate fail-closed behavior behind an explicit environment flag, then make it the default after the focused suite passes.

---

## 8. Phase 4 — Typed Errors, Partial Operations, and Async Correctness

**Priority**: P1  
**Dependency**: Phases 1–3  
**Exit target**: Failures are visible, classifiable, and recoverable

### Work

1. Define a shared error hierarchy:
   - validation
   - authorization
   - policy unavailable
   - dependency unavailable
   - database integrity
   - timeout
   - cancellation
   - bridge protocol
   - partial operation
2. Replace broad catches at core boundaries with typed catches.
3. Preserve exception causes in logs and structured results.
4. Make restore, import, migration, and batch operations return:
   - completed count
   - skipped count
   - failed count
   - item-level errors
   - rollback state
5. Add transaction or staging semantics for destructive operations.
6. Add `async_execute()` and `async_dispatch()`.
7. Ensure synchronous wrappers reject only when no safe event-loop bridge exists; they must not silently close valid coroutines.
8. Add cancellation propagation and timeout classification.

### Tests

- Fault injection for every core error class.
- Restore reports partial failures accurately.
- Cancellation leaves no half-open resource.
- Sync and async handlers return equivalent envelopes.
- No coroutine warnings under test.

### Rollback

Keep legacy result envelopes available through an adapter field while consumers migrate to typed error fields.

---

## 9. Phase 5 — Native Bridge and Background Process Supervision

**Priority**: P1  
**Dependency**: Phase 4  
**Exit target**: Native acceleration is bounded, observable, and safely replaceable

### Work

1. Create a shared `ProcessSupervisor` abstraction for Koka, Rust subprocesses, Zig, Haskell, and other line-protocol bridges.
2. Ensure stderr is drained or redirected to a bounded sink.
3. Replace per-read ad hoc timeout threads with a supervised I/O mechanism.
4. Add process leases so one process cannot be used concurrently by two requests.
5. Kill and replace timed-out or protocol-invalid processes.
6. Add graceful shutdown hooks and orphan-process cleanup.
7. Add capability health states:
   - unavailable
   - starting
   - healthy
   - degraded
   - circuit-open
   - stopping
8. Record startup latency, queue wait, call latency, timeout count, restart count, and protocol errors.
9. Preserve Python fallback behavior, but expose when fallback occurred.

### Tests

- Child process writes excessive stderr.
- Child process hangs during initialization.
- Child process hangs mid-request.
- Child process emits malformed JSON.
- Pool exhaustion under concurrent load.
- Shutdown while calls are active.
- Repeated crash/restart cycles.

### Rollback

Every native bridge remains feature-flagged. Disable the bridge and route to the Python implementation if health falls below threshold.

---

## 10. Phase 6 — Retrieval and Search Query Planning

**Priority**: P1  
**Dependency**: Phase 2 and Phase 4  
**Exit target**: Search is measurable, bounded, and free of avoidable N+1 work

### Work

1. Split retrieval into explicit stages:
   - candidate acquisition
   - lexical ranking
   - semantic ranking
   - spatial ranking
   - entity/association boosts
   - final reranking
2. Define a common candidate score and provenance structure.
3. Implement federated galaxy search with bounded concurrency.
4. Over-fetch per galaxy, merge deterministically, then trim.
5. Batch constellation memberships, entities, and coordinate lookups.
6. Cache indexes by namespace and invalidate them on writes.
7. Make retrieval channels and weights configurable per query or policy profile.
8. Add stage-level timing and candidate-count telemetry.
9. Establish latency budgets for common query classes.

### Tests and benchmarks

- Empty, single-galaxy, and many-galaxy searches.
- Namespace isolation.
- Ranking determinism.
- Degraded semantic/holographic index behavior.
- Candidate explosion protection.
- P50/P95/P99 latency budgets.

### Rollback

Keep the existing hybrid search as a selectable legacy strategy until ranking parity and latency comparisons are complete.

---

## 11. Phase 7 — Compatibility, Registry, Packaging, and Metadata Cleanup

**Priority**: P1/P2  
**Dependency**: Phases 1–6  
**Exit target**: Public surfaces agree and compatibility is intentional

### Work

1. Generate tool names, Gana mappings, schemas, safety metadata, and dispatch registration from one registry.
2. Add CI checks for tool-count and surface consistency.
3. Resolve version metadata through one authoritative source.
4. Generate package metadata from the same version source.
5. Isolate legacy adapters in a clearly named compatibility package.
6. Add deprecation warnings with a removal version and migration path.
7. Remove dead imports, stale type ignores, and redundant legacy cache writes after telemetry proves they are unused.
8. Replace name-pattern safety inference with registry declarations.
9. Define a supported optional-dependency matrix and test each installation tier.

### Exit criteria

- MCP, CLI, API, registry, and documentation report the same tool inventory.
- Version checks agree in source checkout, editable install, and built wheel.
- Compatibility adapters have coverage and owners.

---

## 12. Phase 8 — Operational Tooling and New Capabilities

**Priority**: P2  
**Dependency**: All previous phases  
**Exit target**: The hardened platform becomes easier to operate and evolve

### Additions

#### Deterministic replay

Record request, context, selected policies, middleware decisions, backend choice, native fallback, and output. Support replay without external side effects.

#### Fault-injection harness

Inject database locks, corrupt schemas, missing optional dependencies, native bridge crashes, malformed tool responses, cache corruption, and network failures.

#### Migration and integrity CLI

Provide inspect, validate, repair, reindex, export, import, dry-run, and rollback commands for each galaxy and namespace.

#### Runtime health surface

Expose middleware latency, backend health, cache isolation status, native process state, degraded capabilities, and pending migrations.

#### Property-based and fuzz testing

Use generated inputs for schemas, cache keys, memory serialization, galaxy names, user IDs, bridge protocol messages, and Karma-chain entries.

#### Plugin boundary

Define versioned extension points for tools, handlers, retrieval stages, governance policies, and native accelerators. Extensions should not import internal singleton state.

---

## 13. Test and CI Strategy

### Required test layers

1. **Contract tests** — public envelopes, schemas, aliases, registry consistency.
2. **Unit tests** — individual services and policies.
3. **Integration tests** — runtime-to-handler, memory-to-backend, governance-to-dispatch.
4. **Isolation tests** — users, agents, galaxies, cache namespaces.
5. **Fault-injection tests** — failures and partial operations.
6. **Native bridge tests** — process lifecycle and protocol behavior.
7. **Performance tests** — latency and memory budgets.
8. **Security tests** — fail-closed behavior, privacy, path validation, redaction.
9. **Migration tests** — old databases and old tool aliases.

### CI gates

- Formatting and whitespace check
- Ruff check
- Type checking for canonical public surfaces
- Focused contract suite
- Full supported test suite
- Database migration/integrity checks
- Tool registry consistency
- Security regression suite
- Performance smoke thresholds

No broad lint suppression should be added to make a gate green. Suppressions require a reason, scope, owner, and removal issue.

---

## 14. Recommended Execution Order

### Sprint 1: Safety baseline

- Phase 0
- Runtime contract design
- Firewall fail-closed tests
- Cache namespace threat model
- Working-tree protection

### Sprint 2: Boundary consolidation

- Phase 1 implementation
- Memory backend protocol
- Request context type
- Dual-path parity tests

### Sprint 3: Namespace correctness

- User-aware backend construction
- Galaxy routing migration
- Singleton isolation
- Two-user concurrent tests

### Sprint 4: Security and error behavior

- Cache isolation
- Fast-path registry metadata
- Typed errors
- Partial-operation reporting

### Sprint 5: Process and async reliability

- Async runtime path
- Shared process supervisor
- Native bridge fault injection

### Sprint 6: Retrieval and cleanup

- Federated search planner
- N+1 removal
- Tool registry generation
- Version and package metadata cleanup

### Sprint 7+: Operations and extensions

- Replay
- Fault-injection harness
- Migration CLI
- Runtime health surface
- Plugin boundary

---

## 15. Decision Rules During Execution

- Do not combine memory-routing changes with unrelated feature additions.
- Do not alter the active user's working tree without first checking Git status.
- Do not silently migrate data; every migration needs a dry run and backup.
- Do not optimize a hot path without stage-level measurements.
- Do not treat a passing unit test as proof of namespace isolation.
- Do not add a fallback that hides a security, integrity, or authorization failure.
- Prefer adapters over flag-day API changes.
- Prefer deleting duplicate paths after telemetry proves they are unused.
- Every phase must leave the system runnable with the previous feature flags available.

---

## 16. First Implementation Slice

The first execution slice should be deliberately small and high-value:

1. Add contract tests for canonical tool envelopes and pipeline identity.
2. Add tests proving the transaction firewall blocks when its validator raises.
3. Add cache-key namespace tests for user, agent, galaxy, and policy profile.
4. Add a diagnostic inventory of all direct `UnifiedMemory.backend` consumers.
5. Add a `MemoryContext` type without changing routing yet.
6. Publish the baseline test and performance report.

Only after this slice passes should implementation begin on the memory router migration.

---

## 17. Final Position

WhiteMagic should be hardened as a coherent runtime, not expanded as a collection of independent features.

The optimal path is to make identity, memory, policy, execution, and failure semantics explicit first. Once those contracts are stable, the existing intelligence, native acceleration, holographic retrieval, and consciousness-oriented subsystems will be easier to measure, safer to compose, and substantially easier to evolve.
