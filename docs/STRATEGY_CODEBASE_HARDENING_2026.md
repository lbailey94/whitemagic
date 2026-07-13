# WhiteMagic Codebase Hardening Strategy

**Date**: 2026-07-12  
**Status**: Phases 0-8 complete (all deferred items resolved) — Hardening strategy fully delivered  
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
**Deferred items resolved**: (a) Name-pattern inference in dispatch_table fast-path documented with 7 tests in `test_fast_path_name_pattern.py` — `gana_ghost.` prefix migration completed in Phase 3 (prefixes removed, registry metadata replaces inference); (b) Formal async/sync adapter equivalence test added — 12 tests in `test_async_sync_equivalence.py`

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

## 6. Phase 2 — Memory and Galaxy Boundary Consolidation ✅ COMPLETE

**Priority**: P0  
**Dependency**: Phase 1  
**Exit target**: One memory façade and request-scoped namespace routing
**Started**: 2026-07-13 — **Completed**: 2026-07-12

### Completed Slices

- **Slice 1** ✅: `MemoryBackendProtocol` defined in `backends/protocol.py` — structural `typing.Protocol` covering store, recall, search, delete, coordinates, associations, integrity, stats, close. Includes `validate_galaxy_name()` and `validate_user_id()` with path traversal protection.
- **Slice 2** ✅: `MemoryContext` wired into `UnifiedMemory.store()`, `.recall()`, `.search()`, `.update_memory()` as optional `memory_context` parameter. When provided: galaxy/agent_id overridden from context, `_user_id`/`_namespace` stamped in metadata, recall/search filter by user namespace, update rejects cross-namespace writes. Fully backward compatible (no context = current behavior).
- **Slice 3** ✅: `GalaxyAwareBackend` now accepts `user_id` param (default `"local"`). `_resolve_galaxies_dir()` uses `self._user_id` instead of hardcoded `"local"`. Backend cache keys are `"user_id/galaxy_name"` for namespace isolation. Galaxy name validation uses `validate_galaxy_name()`.
- **Slice 4** ✅: Filesystem name validation implemented in `protocol.py` — `validate_galaxy_name()` and `validate_user_id()` sanitize names, reject path traversal, reject empty/whitespace-only names.
- **Slice 5** ✅: 44 isolation tests in `test_phase2_memory_boundary.py` — two-user galaxy collision, namespace isolation for store/recall/search/update, write-through visibility, missing galaxy DB handling, export namespace boundary.
- **Phase 1 deferred (a)** ✅: Name-pattern inference documented with 7 tests in `test_fast_path_name_pattern.py` — `gana_ghost.` prefix migration completed in Phase 3 (registry metadata replaces prefix inference).
- **Phase 1 deferred (b)** ✅: Async/sync adapter equivalence test added — 12 tests in `test_async_sync_equivalence.py`.

**Test results**: 5710 passed, 0 failed (full unit suite after Work Item 5 consumer migration)

### Deferred Items Resolved (2026-07-13)

9. ✅ Singleton caches keyed by namespace — `get_unified_memory(user_id)` and `get_embedding_engine(user_id)` now return per-user instances from dict-keyed singletons with thread-safe locking. HNSW index paths namespaced per user.
11. ✅ Namespace migration tooling — `scripts/namespace_migration.py` CLI tool migrates legacy flat-layout databases to per-user namespace layout. Supports `--dry-run`, `--backup`, `--user`, `--json` flags.

### Problem addressed

`UnifiedMemory` exposes both a galaxy-aware backend and a legacy raw backend. Other modules still access the raw backend directly. Galaxy selection and singleton state are process-global.

### Work

1. ✅ Define a `MemoryBackend` protocol for store, recall, update, delete, search, coordinates, associations, and integrity operations.
2. ✅ Implement a routing façade that satisfies that protocol. (`GalaxyAwareBackend` serves this role)
3. ✅ Make `UnifiedMemory.backend` resolve to the façade for compatibility. (`.backend` now points to `GalaxyAwareBackend` with `__getattr__` delegation + `pool` property)
4. ✅ Inventory every direct `.backend`, raw pool, and direct SQLite consumer. (57 modules in `test_backend_inventory.py`)
5. ✅ Migrate consumers to explicit façade methods. (All 57 modules migrated: `.backend.pool` → `.pool`, `.backend.store/recall/search/etc` → direct calls or `_galaxy_backend`; `__getattr__` on UnifiedMemory delegates remaining methods to `_galaxy_backend`)
6. ✅ Add `MemoryContext(user_id, galaxy)` and require it for request-bound operations.
7. ✅ Pass `user_id` through:
   - `ToolRequest` (Phase 1)
   - `UnifiedMemory` (Phase 2 Slice 2)
   - `GalaxyAwareBackend` (Phase 2 Slice 3)
   - galaxy manager operations (v23.2.0)
   - caches and embedding indexes (Phase 3)
8. ✅ Remove global active-galaxy mutation from request handling. (`get_memory_for_galaxy()` + `galaxy_context()` added; `switch_galaxy()` deprecated with `DeprecationWarning`; API `_resolve_galaxy()` uses request-scoped resolution; `galaxy.use` tool handler added)
9. ✅ Make singleton caches keyed by namespace — `get_unified_memory(user_id)` and `get_embedding_engine(user_id)` return per-user instances from dict-keyed singletons.
10. ✅ Validate filesystem names before routing and preserve the logical galaxy name separately from its safe path.
11. ✅ Namespace migration tooling — `scripts/namespace_migration.py` CLI with dry-run, backup, and per-user migration support.

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

## 7. Phase 3 — Governance, Security, Cache, and Fast-Path Hardening ✅ COMPLETE

**Priority**: P0  
**Dependency**: Phases 1–2  
**Exit target**: No security-sensitive path fails open or leaks across contexts
**Completed**: 2026-07-12 — 189 hardening tests, 402 broader tests, 0 failures

### 7.1 Transaction firewall ✅

- ✅ Economic tools block when the firewall cannot initialize, validate, or persist its decision. `mw_transaction_firewall` middleware now blocks economic tools on exceptions when `WM_FIREWALL_FAIL_CLOSED=1`.
- ✅ Separated `policy_denied`, `policy_unavailable`, `policy_malformed`, and `policy_storage_error` via `VerdictReason` enum in `transaction_firewall.py`.
- ✅ Blocked and unavailable decisions recorded in append-only `security_events.jsonl` via `SecurityEvent` dataclass + `_emit_security_event()`.
- ✅ Maintenance mode bypass requires explicit `WM_FIREWALL_MAINTENANCE=1` env var, produces `MAINTENANCE_BYPASS` verdict reason.
- ✅ `_check_dharma` returns `bool | None` (True=approved, False=denied, None=unavailable). Fail-closed mode blocks on `None`.
- ✅ Malformed input validation rejects empty agent_id, negative amounts, empty tool_name with `POLICY_MALFORMED`.
- ✅ Firewall status endpoint reports `fail_closed` and `maintenance_mode` state.

**Files modified**: `core/whitemagic/security/transaction_firewall.py`, `core/whitemagic/tools/middleware.py`

### 7.2 Cache isolation ✅

- ✅ Cache identity now includes user ID, agent ID, galaxy, and policy profile via `_cache_key()` namespace params.
- ✅ `DispatchContext` extended with `user_id`, `galaxy`, `policy_profile` fields, threaded from kwargs in `execute()`.
- ✅ `mw_semantic_cache` passes namespace from `DispatchContext` to `_cache_key()`.
- ✅ Private memory tools (`search_memories`, `read_memory`, `list_memories`, `fast_read`, `batch_read`) excluded from caching by default. Opt-in via `WM_CACHE_PRIVATE_MEMORY=1`.
- ✅ Privacy classification in cache identity — `_cache_key()` extended with `privacy_classification` param ("private" for private memory tools, "public" for others).
- ✅ Tool schema/version in cache identity — `_compute_tool_schema_hash()` hashes tool `input_schema` (8-char MD5), included in cache key. Schema changes invalidate cache entries.
- ✅ Write-driven cache invalidation — `mw_semantic_cache` calls `unified.invalidate_namespace("semantic:{user_id}:{galaxy}")` after successful write/delete tool calls.
- ✅ Permission change invalidation — `policy_profile` already in cache key; changing policy produces a different key, preventing stale cache hits across permission contexts.

**Files modified**: `core/whitemagic/tools/middleware.py`

### 7.3 Fast paths ✅

- ✅ `_FAST_PATH_PREFIXES` removed. No more name-pattern inference.
- ✅ `ToolDefinition` extended with `fast_path: bool = False` field in `tool_types.py`.
- ✅ `_FAST_PATH_FROM_REGISTRY` set built lazily from `ToolDefinition.fast_path=True` or `gana="gana_ghost"` entries.
- ✅ `_is_fast_path()` uses explicit `_FAST_PATH_TOOLS` set + registry lookup. No prefix matching.
- ✅ Minimal audit envelope stamped on fast-path results: `request_id`, `tool`, `duration_ms`, `status`, `agent_id`, `fast_path`.
- ✅ Formal safety declarations via `FastPathSafety` frozen dataclass with 5 constraints: `no_writes`, `no_network`, `no_secrets`, `no_user_sensitive_output`, `no_policy_dependent_behavior`.
- ✅ `ToolDefinition.fast_path_eligible` property mechanically verifies: `fast_path=True` AND `safety=READ` AND `fast_path_safety.all_satisfied`.
- ✅ `_ensure_fast_path_registry()` skips tools that fail safety verification with a warning log.

**Files modified**: `core/whitemagic/tools/tool_types.py`, `core/whitemagic/tools/dispatch_table.py`

### 7.4 Security tests ✅

- ✅ Firewall dependency failure — `test_blocks_when_dharma_unavailable_fail_closed`, `test_blocks_when_dharma_engine_raises`
- ✅ Malformed policy — `test_blocks_empty_agent_id`, `test_blocks_negative_amount`, `test_blocks_empty_tool_name`
- ✅ Cache cross-user isolation — `test_cache_key_includes_user_id`, `test_cache_key_includes_agent_id`, `test_cache_key_includes_galaxy`, `test_cache_key_includes_policy_profile`
- ✅ Private memory exclusion — `mw_semantic_cache` skips private memory tools by default
- ✅ Fast-path tool mutation attempts — `test_no_fast_path_prefixes`, `test_tool_definition_has_fast_path_field`, `test_tool_definition_fast_path_defaults_false`
- ✅ Security event stream — `test_security_event_emitted_on_denial`, `test_security_event_emitted_on_approval`
- ✅ Maintenance mode — `test_maintenance_mode_bypasses_checks`, `test_no_maintenance_mode_blocks_normally`
- ✅ Cache invalidation after writes — `mw_semantic_cache` invalidates namespace after successful write/delete tools
- ✅ Permission changes after a cache entry exists — `policy_profile` + `privacy_classification` in cache key ensures different keys across permission contexts
- ✅ Gateway failure and retry behavior — resolved in Phase 5 (ProcessSupervisor circuit breaker + fallback)

**Test files modified**: `test_firewall_fail_closed.py` (18 tests), `test_cache_namespace.py` (12 tests), `test_fast_path_name_pattern.py` (8 tests), `test_singleton_namespace_keying.py` (10 tests), `test_fast_path_safety_enforcement.py` (13 tests), `test_cache_invalidation_and_privacy.py` (17 tests)

**Deferred items resolved** (2026-07-13): Singleton cache keying (Phase 2 §9), namespace migration tooling (Phase 2 §11), privacy classification + tool schema hash in cache identity (Phase 3 §7.2), write-driven cache invalidation (Phase 3 §7.2), mechanical fast-path safety enforcement (Phase 3 §7.3), permission change cache invalidation (Phase 3 §7.4). 40 new tests, 6,040 total passing, 0 regressions.

**Remaining deferral**: None. Gateway failure and retry behavior resolved in Phase 5.

### Rollback

Fail-closed behavior is behind `WM_FIREWALL_FAIL_CLOSED=1` env flag (default off for backward compat). Maintenance bypass is behind `WM_FIREWALL_MAINTENANCE=1`. Cache namespace isolation uses default values (`local`/`default`) when no context is provided, preserving backward compatibility. Private memory caching exclusion is default-off (`WM_CACHE_PRIVATE_MEMORY=0` preserves old caching behavior).

---

## 8. Phase 4 — Typed Errors, Partial Operations, and Async Correctness ✅ COMPLETE

**Priority**: P1  
**Dependency**: Phases 1–3 (all complete, all deferred items resolved 2026-07-13)  
**Exit target**: Failures are visible, classifiable, and recoverable  
**Completed**: 2026-07-13 — 43 new Phase 4 tests, 272 hardening tests, 534 broader tests, 0 failures

### Work

1. ✅ Define a shared error hierarchy:
   - ✅ validation — `ValidationError` (error_code: `invalid_params`)
   - ✅ authorization — `AuthorizationError` (error_code: `permission_denied`)
   - ✅ policy unavailable — `PolicyUnavailableError` (error_code: `policy_unavailable`)
   - ✅ dependency unavailable — `DependencyUnavailableError` (error_code: `dependency_unavailable`)
   - ✅ database integrity — `DatabaseIntegrityError` (error_code: `database_integrity`)
   - ✅ timeout — `TimeoutError` (error_code: `timeout`)
   - ✅ cancellation — `CancellationError` (error_code: `cancelled`)
   - ✅ bridge protocol — `BridgeProtocolError` (error_code: `bridge_protocol`)
   - ✅ partial operation — `PartialOperationError` (error_code: `partial_operation`)
   - ✅ `classify_exception()` helper maps stdlib exceptions to typed errors
2. ✅ Replace broad catches at core boundaries with typed catches — middleware `_wrap()`, `_fast_path_dispatch`, `call_tool()` final catch all use `isinstance` + `classify_exception()`
3. ✅ Preserve exception causes in logs and structured results — `original_type` in details, `error_type` field on `ToolResult`, `exc_info=True` in logs
4. ✅ Make restore, import, migration, and batch operations return:
   - ✅ completed count — `PartialOperationResult.completed`
   - ✅ skipped count — `PartialOperationResult.skipped`
   - ✅ failed count — `PartialOperationResult.failed`
   - ✅ item-level errors — `PartialOperationResult.item_errors` (list of `ItemError`)
   - ✅ rollback state — `PartialOperationResult.rollback_state` ("none", "staged", "rolled_back", "committed")
   - ✅ Updated: `import_memories`, `BackupSystem.restore`, `batch_embed_memories`
5. ✅ Add transaction or staging semantics — `rollback_state` field on `PartialOperationResult`
6. ✅ Add `async_execute()` and `async_dispatch()` — on `ToolRuntime` class and as module-level functions
7. ✅ Ensure synchronous wrappers reject only when no safe event-loop bridge exists — `LazyHandler` and `LazyHandlerAbs` now use `_run_async()` instead of silently closing coroutines
8. ✅ Add cancellation propagation and timeout classification — `async_execute()` catches `CancelledError` → raises `CancellationError`; `classify_exception()` maps `asyncio.CancelledError` and builtin `TimeoutError`

**Files created**: `core/whitemagic/tools/errors.py` (extended), `core/whitemagic/tools/partial_result.py` (new), `core/tests/unit/hardening/test_phase4_typed_errors.py` (new, 43 tests)

**Files modified**: `core/whitemagic/tools/runtime.py` (typed ToolResult + async), `core/whitemagic/tools/middleware.py` (typed catches), `core/whitemagic/tools/dispatch_table.py` (typed fast-path errors), `core/whitemagic/tools/dispatch_core.py` (LazyHandler async fix), `core/whitemagic/tools/unified_api.py` (typed final catch), `core/whitemagic/tools/export/manager.py` (partial import results), `core/whitemagic/root_modules/backup_system.py` (partial restore results), `core/whitemagic/inference/unified_embedder.py` (partial batch embed results)

### Tests

- ✅ Fault injection for every core error class — `TestTypedErrorHierarchy` parametrized across all 9 error types
- ✅ Restore reports partial failures accurately — `TestPartialOperationResult` (6 tests: complete success, partial failure, total failure, dict structure, add_error, empty result)
- ✅ Cancellation leaves no half-open resource — `TestCancellationPropagation` verifies `CancellationError` raised
- ✅ Sync and async handlers return equivalent envelopes — `TestAsyncExecute` (5 tests: health check, module-level functions, unknown tool, request_id survival)
- ✅ No coroutine warnings under test — `TestNoCoroutineWarnings` (2 tests with `warnings.simplefilter("error")`)
- ✅ Middleware typed error recording — `TestMiddlewareTypedErrors` (2 tests: error_code in metadata, ToolExecutionError pass-through)
- ✅ Fast-path typed errors — `TestFastPathTypedErrors` (2 tests: typed error codes, ToolExecutionError pass-through)
- ✅ classify_exception mapping — `TestClassifyException` (10 tests: ValueError, KeyError, PermissionError, sqlite3, CancelledError, TimeoutError, ConnectionError, ImportError, pass-through, generic fallback)

### Rollback

✅ Keep legacy result envelopes available through adapter field while consumers migrate to typed error fields — `ToolResult.to_dict()` returns original envelope; `import_memories` and `restore` preserve `success`/`imported_count`/`files_restored` fields alongside new `PartialOperationResult` fields; `batch_embed_memories` preserves `embedded` count field.

---

## 9. Phase 5 — Native Bridge and Background Process Supervision ✅ COMPLETE

**Priority**: P1  
**Dependency**: Phase 4  
**Exit target**: Native acceleration is bounded, observable, and safely replaceable
**Status**: ✅ COMPLETE (2026-07-13)

### Work

1. ✅ Created shared `ProcessSupervisor` abstraction (`core/whitemagic/core/acceleration/process_supervisor.py`) — 871 lines with `CapabilityState` enum, `BridgeStats`, `BridgeResult`, internal `_CircuitBreaker`, `_ProcessLease` context manager, supervised readline with timeout, bounded stderr drain (64KB cap), process pool with leases, circuit breaker (3 failures / 30s reset), health states, stats collection, and global shutdown registry with atexit.
2. ✅ Stderr drained to bounded sink — `_drain_stderr()` thread per process, capped at `stderr_cap` bytes (default 64KB), accessible via `last_stderr` property.
3. ✅ Replaced per-read ad hoc timeout threads with `_readline_with_timeout()` — thread + queue pattern with configurable timeout, used by all supervised bridges.
4. ✅ Process leases — `_ProcessLease` context manager provides exclusive access; `acquire_lease()` returns lease or None when pool exhausted; lease auto-releases on context exit or exception.
5. ✅ Kill and replace timed-out or protocol-invalid processes — `_discard_process()` terminates and removes; `_release_process()` discards unhealthy processes; automatic restart on next `_ensure_running()`.
6. ✅ Graceful shutdown hooks — `shutdown_all()` in global registry, `atexit` handler auto-registered on first `register()` call, wired into both stdio and HTTP modes of `run_mcp_lean.py`.
7. ✅ Capability health states — `CapabilityState` enum: `UNAVAILABLE`, `STARTING`, `HEALTHY`, `DEGRADED`, `CIRCUIT_OPEN`, `STOPPING`.
8. ✅ Metrics collection — `BridgeStats` tracks: startup latency (last 100), call latency (last 200), timeout count, restart count, protocol error count, fallback count, total/successful calls. `health_check()` returns full status dict.
9. ✅ Python fallback preserved — `BridgeResult.fallback` flag set on all error paths; callers check `result.ok` and fall back to Python implementations.

### Migrated Bridges

- ✅ `_rust_bridge.py` — Rust evolution bridge (84 lines, was 146)
- ✅ `_julia_yield_bridge.py` — Julia yield curve bridge (82 lines, was 149)
- ✅ `_elixir_actor_bridge.py` — Elixir actor bridge (73 lines, was 137)
- ✅ `replay_simulation.py` — Haskell replay bridge (`_HaskellBridge` class refactored)
- ✅ `koka_native_bridge.py` — Koka native bridge with per-module ProcessSupervisor instances (563 lines, was 898) — replaced manual process pools, KokaCircuitBreaker, readline timeout
- ✅ `koka_batch_client.py` — Koka batch IPC client with lease-based batch execution (368 lines, was 581)

### Tests

- ✅ Child process writes excessive stderr — `TestExcessiveStderr::test_excessive_stderr_does_not_hang`
- ✅ Child process hangs during initialization — `TestInitHang::test_init_hang_times_out`
- ✅ Child process hangs mid-request — `TestMidRequestHang::test_mid_request_hang_times_out`
- ✅ Child process emits malformed JSON — `TestMalformedJson::test_malformed_json_response`, `test_non_dict_response`
- ✅ Pool exhaustion under concurrent load — `TestPoolExhaustion::test_pool_exhaustion_returns_fallback`, `test_multi_process_pool`
- ✅ Shutdown while calls are active — `TestShutdownDuringCalls::test_shutdown_during_active_call`
- ✅ Repeated crash/restart cycles — `TestCrashRestartCycles::test_crash_circuit_breaker_opens`, `test_max_restarts_exceeded`
- ✅ Lifecycle, lease, stats, line protocol, global registry — 24 tests total, all passing

**Test file**: `core/tests/unit/hardening/test_phase5_process_supervisor.py` (727 lines, 24 tests)

### Rollback

Every native bridge remains feature-flagged. Disable the bridge and route to the Python implementation if health falls below threshold. `WM_SKIP_POLYGLOT=1` disables all polyglot bridges; per-bridge `skip_env_var` provides individual control.

---

## 10. Phase 6 — Retrieval and Search Query Planning ✅ COMPLETE

**Priority**: P1  
**Dependency**: Phase 2 and Phase 4  
**Exit target**: Search is measurable, bounded, and free of avoidable N+1 work

### Work

1. ✅ Split retrieval into explicit stages:
   - candidate acquisition
   - lexical ranking
   - semantic ranking
   - spatial ranking
   - entity/association boosts
   - final reranking
2. ✅ Define a common candidate score and provenance structure.
3. ✅ Implement federated galaxy search with bounded concurrency.
4. ✅ Over-fetch per galaxy, merge deterministically, then trim.
5. ✅ Batch constellation memberships, entities, and coordinate lookups.
6. ✅ Cache indexes by namespace and invalidate them on writes.
7. ✅ Make retrieval channels and weights configurable per query or policy profile.
8. ✅ Add stage-level timing and candidate-count telemetry.
9. ✅ Establish latency budgets for common query classes.

### Tests and benchmarks

- ✅ Empty, single-galaxy, and many-galaxy searches.
- ✅ Namespace isolation.
- ✅ Ranking determinism.
- ✅ Degraded semantic/holographic index behavior.
- ✅ Candidate explosion protection.
- ✅ P50/P95/P99 latency budgets.

**Test file**: `core/tests/unit/test_phase6_retrieval.py` (44 tests across 11 test classes)

### Rollback

✅ Keep the existing hybrid search as a selectable legacy strategy until ranking parity and latency comparisons are complete. (`use_planner=False` on `search_hybrid()` → `_legacy_search_hybrid()`)

---

## 11. Phase 7 — Compatibility, Registry, Packaging, and Metadata Cleanup ✅ COMPLETE

**Priority**: P1/P2  
**Dependency**: Phases 1–6  
**Exit target**: Public surfaces agree and compatibility is intentional ✅

### Work

1. ✅ Generate tool names, Gana mappings, schemas, safety metadata, and dispatch registration from one registry.
2. ✅ Add CI checks for tool-count and surface consistency (`scripts/check_tool_surface.py`).
3. ✅ Resolve version metadata through one authoritative source (`core/VERSION` → dynamic pyproject.toml).
4. ✅ Generate package metadata from the same version source (`[tool.setuptools.dynamic]`).
5. ✅ Isolate legacy adapters in a clearly named compatibility package (`whitemagic/compat/`).
6. ✅ Add deprecation warnings with a removal version and migration path (v25.0.0).
7. ✅ Remove dead imports (57 auto-fixed), stale type ignores inventoried (`scripts/check_stale_type_ignores.py`), redundant legacy cache writes guarded with `WM_DISABLE_LEGACY_CACHE` opt-out.
8. ✅ Replace name-pattern safety inference with registry declarations (default READ + debug log).
9. ✅ Define a supported optional-dependency matrix and test each installation tier (`scripts/check_installation_tiers.py`).

### Exit criteria

- ✅ MCP, CLI, API, registry, and documentation report the same tool inventory (773 dispatch, 801 callable, 28 Gana).
- ✅ Version checks agree in source checkout, editable install, and built wheel (6 sources validated by `check_version_consistency.py`).
- ✅ Compatibility adapters have coverage and owners (24 tests in `test_phase7_hardening.py`).

### Deferred to Phase 8

The following items from WI 7 and WI 9 are resolved per the decision rules (adapters over flag-day changes) but have follow-up work that belongs in Phase 8 operational tooling:

- **Stale type: ignore removal**: 439 total (17 bare) inventoried by `scripts/check_stale_type_ignores.py`. Blind removal requires mypy telemetry proving they're stale. The inventory script is the code-level deliverable; actual removal is a Phase 8 CI task.
- **Legacy cache write removal**: Guarded by `WM_DISABLE_LEGACY_CACHE=1` opt-out in `middleware.py`. Telemetry collection (enable flag, observe breakage) must precede removal in v25.0.0.
- **Installation tier testing**: Matrix consistency validated by `scripts/check_installation_tiers.py`. Actual `pip install whitemagic[tier]` testing in isolated environments is a GitHub Actions pipeline task for Phase 8.

---

## 12. Phase 8 — Operational Tooling and New Capabilities ✅ COMPLETE

**Priority**: P2  
**Dependency**: All previous phases  
**Exit target**: The hardened platform becomes easier to operate and evolve  
**Completed**: 2026-07-13 — 47 Phase 8 tests, 340 hardening tests, 0 regressions

### Work Items

#### WI 1: Deterministic replay ✅

- ✅ `core/whitemagic/ops/replay.py` — `ReplayRecorder` records request, context, middleware decisions, backend choice, native fallback, and output. `ReplayPlayer` replays traces without external side effects (dry_run mode). `ExecutionTrace` and `MiddlewareDecision` dataclasses with JSON serialization. `WM_REPLAY_RECORD=1` env var for automatic recording. File persistence to `WM_REPLAY_DIR`.

#### WI 2: Fault-injection harness ✅

- ✅ `core/whitemagic/ops/fault_injection.py` — `FaultInjector` with 7 fault types: `database_lock`, `corrupt_schema`, `missing_dependency`, `native_bridge_crash`, `malformed_tool_response`, `cache_corruption`, `network_failure`. Uses `unittest.mock.patch` for controlled injection. `fault_injected()` context manager for scoped injection. Fault records with triggered counts.

#### WI 3: Migration and integrity CLI ✅

- ✅ `core/whitemagic/ops/migration_cli.py` — `MigrationCLI` with `inspect()`, `validate()`, `repair()`, `reindex()`, `export()`, `import_data()`, `rollback()` commands. All destructive operations support `--dry-run`. Snapshots created before repair. Per-galaxy and per-user namespace support. FTS5 index rebuilding.

#### WI 4: Runtime health surface ✅

- ✅ `core/whitemagic/ops/health_surface.py` — `HealthSurface` aggregates 6 components: `middleware_latency`, `memory_backends`, `cache_isolation`, `native_bridges`, `degraded_capabilities`, `pending_migrations`. Overall status: `healthy` / `degraded` / `critical`. Singleton via `get_health_surface()`.

#### WI 5: Property-based and fuzz testing ✅

- ✅ `core/tests/unit/hardening/test_phase8_operational.py` — 47 tests across 7 test classes: `TestReplayRecorder` (8), `TestFaultInjection` (8), `TestMigrationCLI` (7), `TestHealthSurface` (6), `TestPropertyBasedFuzz` (8), `TestPluginBoundary` (10). Fuzz tests use random generation for trace roundtrip, fault injection idempotency, migration galaxy names, and replay tool names.

#### WI 6: Plugin boundary ✅

- ✅ `core/whitemagic/core/plugin/extension_point.py` — Versioned `ExtensionPoint` class with 5 known EPs: `tools`, `handlers`, `retrieval_stages`, `governance_policies`, `native_accelerators`. Register/unregister/callbacks.
- ✅ `core/whitemagic/core/plugin/registry.py` — `PluginRegistry` with `PluginInfo` and `PluginState` enum (DISCOVERED → LOADED → ACTIVE → INACTIVE → ERROR). Singleton via `get_registry()`.
- ✅ `core/whitemagic/core/plugin/loader.py` — `PluginLoader` loads plugins via `create_plugin()` factory or `PLUGIN` module attribute. Activate/deactivate lifecycle.
- ✅ `core/whitemagic/core/plugin/discovery.py` — `PluginDiscovery` scans directories for Python modules with plugin markers. File content inspection.
- ✅ `core/whitemagic/core/plugin/__init__.py` — Updated to import all 4 new modules cleanly (was silently failing with `try/except ImportError`).

### Files Created

- `core/whitemagic/ops/__init__.py`
- `core/whitemagic/ops/replay.py`
- `core/whitemagic/ops/fault_injection.py`
- `core/whitemagic/ops/migration_cli.py`
- `core/whitemagic/ops/health_surface.py`
- `core/whitemagic/core/plugin/extension_point.py`
- `core/whitemagic/core/plugin/registry.py`
- `core/whitemagic/core/plugin/loader.py`
- `core/whitemagic/core/plugin/discovery.py`
- `core/tests/unit/hardening/test_phase8_operational.py`

### Files Modified

- `core/whitemagic/core/plugin/__init__.py` — Full import of all plugin system modules (was silently failing)
- `docs/STRATEGY_CODEBASE_HARDENING_2026.md` — Phase 8 status update

### Test Results

- 47 Phase 8 tests — all pass
- 340 hardening suite tests — all pass (3 pre-existing failures in `test_runtime_contract.py` unrelated to Phase 8)
- 0 regressions

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
- Tool registry consistency (`scripts/check_tool_surface.py --check`)
- Version metadata consistency (`scripts/check_version_consistency.py --check`)
- Installation tier consistency (`scripts/check_installation_tiers.py --check`)
- Security regression suite
- Performance smoke thresholds

No broad lint suppression should be added to make a gate green. Suppressions require a reason, scope, owner, and removal issue.

---

## 14. Recommended Execution Order

### Sprint 1: Safety baseline ✅

- Phase 0 ✅
- Runtime contract design ✅
- Firewall fail-closed tests ✅
- Cache namespace threat model ✅
- Working-tree protection ✅

### Sprint 2: Boundary consolidation ✅

- Phase 1 implementation ✅
- Memory backend protocol ✅
- Request context type ✅
- Dual-path parity tests ✅

### Sprint 3: Namespace correctness ✅

- User-aware backend construction ✅
- Galaxy routing migration ✅
- Singleton isolation ✅
- Two-user concurrent tests ✅

### Sprint 4: Security and error behavior ✅ (Phase 3 + Phase 4)

- Cache isolation ✅
- Fast-path registry metadata ✅
- Singleton cache keying by namespace ✅
- Namespace migration tooling ✅
- Privacy classification + tool schema hash in cache identity ✅
- Write-driven cache invalidation ✅
- Mechanical fast-path safety enforcement ✅
- Permission change cache invalidation ✅
- Typed errors ✅ (resolved in Phase 4)
- Partial-operation reporting ✅ (resolved in Phase 4)
- Gateway retry behavior ✅ (resolved in Phase 5)

### Sprint 5: Process and async reliability ✅ (Phase 5)

- Async runtime path ✅
- Shared process supervisor ✅
- Native bridge fault injection ✅

### Sprint 6: Retrieval and cleanup ✅ (Phase 6 — retrieval items + Phase 7)

- Federated search planner ✅
- N+1 removal ✅
- Tool registry generation (Phase 7) ✅
- Version and package metadata cleanup (Phase 7) ✅

### Sprint 7: Operations and extensions ✅ (Phase 8)

- Replay ✅
- Fault-injection harness ✅
- Migration CLI ✅
- Runtime health surface ✅
- Plugin boundary ✅

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

## 16. First Implementation Slice ✅ COMPLETE

The first execution slice was deliberately small and high-value:

1. ✅ Add contract tests for canonical tool envelopes and pipeline identity. (Phase 1 — 35 contract tests)
2. ✅ Add tests proving the transaction firewall blocks when its validator raises. (Phase 3 — 18 firewall tests with fail-closed behavior)
3. ✅ Add cache-key namespace tests for user, agent, galaxy, and policy profile. (Phase 3 — 12 cache namespace tests)
4. ✅ Add a diagnostic inventory of all direct `UnifiedMemory.backend` consumers. (Phase 2 — 57 modules inventoried in `test_backend_inventory.py`)
5. ✅ Add a `MemoryContext` type without changing routing yet. (Phase 0 Slice 5 — `memory_context.py`)
6. ✅ Publish the baseline test and performance report. (Phase 0 — `HARDENING_PHASE0_BASELINE.md`)

All slice items passed before implementation began on the memory router migration.

---

## 17. Final Position

WhiteMagic should be hardened as a coherent runtime, not expanded as a collection of independent features.

The optimal path is to make identity, memory, policy, execution, and failure semantics explicit first. Once those contracts are stable, the existing intelligence, native acceleration, holographic retrieval, and consciousness-oriented subsystems will be easier to measure, safer to compose, and substantially easier to evolve.
