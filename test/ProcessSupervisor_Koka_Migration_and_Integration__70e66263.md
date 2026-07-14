=== MESSAGE 0 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 1 - User ===
Good morning! Let's look over the STRATEGY_CODEBASE_HARDENING_2026.md doc, plan out how we're going to proceed through Phase 5, and when you're ready, let's begin! (rely on cat shell and heredoc fast write techniques whenever possible!)

=== MESSAGE 2 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 3 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 4 - Assistant ===
Good morning! Let me explore the existing native bridge infrastructure before planning Phase 5.

=== MESSAGE 5 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 6 - Tool ===
[CORTEX_STEP_TYPE_FIND_CODE_CONTEXT]

=== MESSAGE 7 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 8 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 9 - Assistant ===
Let me get a fuller picture of all the bridge files and the existing test infrastructure.

=== MESSAGE 10 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 11 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 12 - Tool ===
[CORTEX_STEP_TYPE_FIND]

=== MESSAGE 13 - Tool ===
[CORTEX_STEP_TYPE_FIND]

=== MESSAGE 14 - Assistant ===
Let me look at a few more key bridge files to understand the full pattern duplication.

=== MESSAGE 15 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 16 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 17 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 18 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 19 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 20 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 21 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 22 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 23 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 24 - Assistant ===
Now I have a comprehensive picture. Let me lay out the Phase 5 plan.

## Phase 5 Analysis

### Current State: Duplicated Bridge Patterns

There are **6+ JSON stdio persistent subprocess bridges** that each independently implement the same pattern:

| File | Pattern | Pool | Circuit Breaker |
|---|---|---|---|
| [_rust_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_rust_bridge.py:0:0-0:0) | module-level `_proc` + [_readline_timeout()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:811:4-832:23) | single | none |
| [_julia_yield_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_julia_yield_bridge.py:0:0-0:0) | module-level `_proc` + [_readline_timeout()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:811:4-832:23) | single | none |
| [_elixir_actor_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_elixir_actor_bridge.py:0:0-0:0) | class-level `_proc` + [_readline_timeout()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:811:4-832:23) | single | none |
| [replay_simulation.py::_HaskellBridge](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:41:0-95:63) | class-level `_proc` + `select.select()` | single | none |
| [koka_native_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:0:0-0:0) | pool of procs per module | multi | yes (per module) |
| [koka_batch_client.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_batch_client.py:0:0-0:0) | pool of procs | multi | none |

**Key issues:**
- [_readline_timeout()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:811:4-832:23) is copy-pasted 5+ times (queue.Queue + threading.Thread pattern)
- No stderr draining (stderr pipes fill up → process hangs)
- No process leases (two concurrent requests can corrupt a single-process bridge's stdin/stdout)
- No graceful shutdown registry (orphan processes on exit)
- No unified health states or stats
- No fallback exposure (bridges silently return `None`)

### Phase 5 Implementation Plan

**Slice 1** — `ProcessSupervisor` core class + `CapabilityState` enum + `BridgeStats` + `BridgeResult`
**Slice 2** — Migrate the 4 simple JSON stdio bridges (Rust, Julia, Elixir, Haskell replay)
**Slice 3** — Migrate Koka bridges (native + batch) to use ProcessSupervisor for pool management
**Slice 4** — Global shutdown registry + `atexit` + orphan cleanup
**Slice 5** — Fault-injection tests (7 scenarios from the strategy doc)

Let me start building.

=== MESSAGE 25 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 26 - Assistant ===
Building Slice 1 — the `ProcessSupervisor` core module. Using cat heredoc for fast write.

=== MESSAGE 27 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 28 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 29 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 30 - Assistant ===
Slice 1 written. Now let me write the fault-injection tests (Slice 5) before migrating bridges — tests first per discipline.

=== MESSAGE 31 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 32 - Assistant ===
Now let me run the tests to verify the ProcessSupervisor works correctly.

=== MESSAGE 33 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 34 - Assistant ===
4 failures — root cause is lock reentrancy deadlock (`_release_process` holds lock → calls [_discard_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:228:4-242:66) which tries to acquire same lock). Also [_get_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:169:4-219:27) → `_start_process` same issue. Fix: use `RLock` instead of `Lock`. Plus stats trim and max_restarts test fixes.

=== MESSAGE 35 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 36 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 37 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 38 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 39 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 40 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 41 - Assistant ===
Now fix the `test_max_restarts_exceeded` test — the issue is that [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:810:4-818:49) calls [close()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:463:4-474:35) which resets `_started=False`, then [_ensure_running()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) starts a new process. But the process exits immediately after printing "started", so by the time [call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:74:4-95:63) runs, the process is dead. The restart count check in [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) uses `_restart_count` but [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:810:4-818:49) increments it after [close()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:463:4-474:35). Let me also fix the pool exhaustion test — the issue is that [_get_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:169:4-219:27) tries to start a new process inside the lock when pool isn't full, but [_start_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:377:4-433:19) also acquires the lock. With RLock this should now work. Let me re-run:

=== MESSAGE 42 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 43 - Assistant ===
Three issues to fix:
1. **Stats trim**: trim triggers at `> 100` leaving 50, then grows back — test expectation wrong
2. **Pool exhaustion**: RLock fixed the deadlock, now all calls succeed within lease wait — test needs shorter timeout
3. **Max restarts**: `>=` should be `>` to allow exactly `max_restarts` restarts before failing

=== MESSAGE 44 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 45 - Assistant ===
Now fix the two test expectations:

=== MESSAGE 46 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 47 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 48 - Assistant ===
I need a different approach for the pool exhaustion test. Instead of an override attribute, I'll make the lease wait timeout configurable in the constructor and use a short one in the test.

=== MESSAGE 49 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 50 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 51 - Assistant ===
I'll add a `lease_wait_timeout` parameter to the constructor and use it in [_get_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:169:4-219:27):

=== MESSAGE 52 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 53 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 54 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 55 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 56 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 57 - Assistant ===
Now update [_get_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:169:4-219:27) to use `self._lease_wait_timeout` instead of the hardcoded default:

=== MESSAGE 58 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 59 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 60 - Assistant ===
Now I need to add the timeout resolution inside [_get_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:169:4-219:27):

=== MESSAGE 61 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 62 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 63 - Assistant ===
Now update [acquire_lease](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:566:4-580:40) similarly:

=== MESSAGE 64 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 65 - Assistant ===
Now fix the pool exhaustion test to use a short `lease_wait_timeout`:

=== MESSAGE 66 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 67 - Assistant ===
Now fix the [test_max_restarts_exceeded](file:///home/lucas/Desktop/WHITEMAGIC/core/tests/unit/hardening/test_phase5_process_supervisor.py:513:4-550:23) test. The issue: [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:814:4-822:49) calls [close()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:463:4-474:35) which resets `_started=False` and clears processes, then calls [_ensure_running()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23). But the mock prints "started" then exits immediately. So [_start_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:377:4-433:19) sees the startup check pass, adds the process, but by the time [call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:74:4-95:63) runs, the process is dead. The call fails, [_discard_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:228:4-242:66) is called, but `_restart_count` isn't incremented by [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) — only [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:814:4-822:49) increments it. Let me look at the test more carefully:

=== MESSAGE 68 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 69 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 70 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 71 - Assistant ===
The test manually resets `_restart_count` to 0, then does [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) which increments to 1, then call fails. Second [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 2, call fails. Third [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 3, but [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) checks `> max_restarts (2)`, so 3 > 2 → unavailable. But [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) itself calls [_ensure_running()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) which starts a process (prints "started" then exits). The [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) returns True because [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) returned a process. Then the third [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 3, calls [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23), 3 > 2 → returns None. So [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) returns False. That should work now with the `>` fix. Let me also check — the first [is_available()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:151:4-167:77) starts a process. Then [call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:74:4-95:63) fails (dead process), which calls [_discard_process](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:228:4-242:66). The process is removed. Then `sup._restart_count = 0` resets. But after the first [call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:74:4-95:63) failure, `_restart_count` is still 0 (only [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments it). So the reset is a no-op. Then [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 1, starts a new process (which exits), returns True. Call fails. [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 2, starts process, returns True. Call fails. [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) increments to 3, [_ensure_running](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:344:4-375:23) checks 3 > 2 → unavailable, returns None. [restart()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:812:4-820:49) returns False. 

Let me run the tests:

=== MESSAGE 72 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 73 - Assistant ===
All 24 tests pass. Let me update the todo and move to Slice 2 — migrating the simple bridges.

=== MESSAGE 74 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 75 - Assistant ===
Now let me read the full Rust bridge to understand the migration surface:

=== MESSAGE 76 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 77 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 78 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 79 - Assistant ===
Now let me read the Haskell replay bridge's [call](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_rust_bridge.py:102:0-126:19) method:

=== MESSAGE 80 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 81 - Assistant ===
Good. Now I have all 4 bridge patterns. The migration strategy is to replace the internal subprocess management with a [ProcessSupervisor](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:225:0-832:9) instance while preserving the public API ([call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_julia_yield_bridge.py:105:0-129:19), [is_available()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_julia_yield_bridge.py:132:0-134:40), [close()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_rust_bridge.py:134:0-144:21)). Let me migrate all 4 bridges using cat heredoc:

=== MESSAGE 82 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 83 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 84 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 85 - Assistant ===
Now the Haskell replay bridge — this one is a class inside [replay_simulation.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:0:0-0:0). I need to modify just the [_HaskellBridge](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:41:0-95:63) class, not the whole file. Let me read the full class:

=== MESSAGE 86 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 87 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 88 - Assistant ===
Now I need to add the [ProcessSupervisor](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:225:0-832:9) import at the top of [replay_simulation.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:0:0-0:0):

=== MESSAGE 89 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 90 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 91 - Assistant ===
Now let me run the existing tests for these bridges to make sure nothing broke:

=== MESSAGE 92 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 93 - Assistant ===
Let me also run any tests that import the Rust/Julia/Elixir bridges:

=== MESSAGE 94 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 95 - Assistant ===
All imports work. Let me run a broader test to check for regressions:

=== MESSAGE 96 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 97 - Assistant ===
One pre-existing failure in `test_gan_ying_cascades.py` — unrelated to our changes (it's about `GanYingBus._koka_available` caching, not our migrated bridges). Let me verify it was pre-existing:

=== MESSAGE 98 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 99 - Assistant ===
Pre-existing failure. Let me restore our changes:

=== MESSAGE 100 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 101 - Assistant ===
Pre-existing failure confirmed. Slice 2 is done. Now Slice 3 — migrate the Koka bridges. These are more complex because they have per-module process pools and circuit breakers already.

=== MESSAGE 102 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 103 - Assistant ===
Let me read the full KokaNativeBridge to understand its structure:

=== MESSAGE 104 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 105 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 106 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 107 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 108 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 109 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 110 - Assistant ===
The KokaNativeBridge is 898 lines with per-module process pools, circuit breakers, and many API methods. I'll refactor it to use [ProcessSupervisor](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:225:0-830:9) per module, replacing the manual pool/circuit-breaker/readline code while preserving all public APIs.

=== MESSAGE 111 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 112 - Assistant ===
Now let me migrate the KokaBatchClient. Let me read it first:

=== MESSAGE 113 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 114 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 115 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 116 - Assistant ===
The KokaBatchClient is more complex — it has batch protocol (send all commands in one write, read all responses). The [ProcessSupervisor.call()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:584:4-710:43) handles single JSON request/response, but batch needs custom write/read. I'll use [acquire_lease](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:568:4-582:40) to get a process, then do the batch I/O manually with the supervisor's [_readline_with_timeout](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_batch_client.py:257:4-284:23) method. Let me refactor:

=== MESSAGE 117 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 118 - Assistant ===
Now let me verify imports and run the Koka-related tests:

=== MESSAGE 119 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 120 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 121 - Assistant ===
All 307 tests pass (the pre-existing gan_ying failure was in a different test filter). Let me also run the Phase 5 tests:

=== MESSAGE 122 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 123 - Assistant ===
All green. Now Slice 4 — wire the global shutdown into `run_mcp_lean.py`:

=== MESSAGE 124 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 125 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 126 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 127 - Assistant ===
I need to add [shutdown_all](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:856:0-865:75) from the process_supervisor registry to the cleanup section. Let me also check the HTTP mode shutdown:

=== MESSAGE 128 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 129 - Assistant ===
I need to add [shutdown_all](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:852:0-861:75) to both the stdio and HTTP shutdown paths:

=== MESSAGE 130 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 131 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 132 - Assistant ===
The edit removed the `def main() -> None:` line. Let me fix:

=== MESSAGE 133 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 134 - Assistant ===
Good. Now let me verify the atexit handler is already in the ProcessSupervisor module:

=== MESSAGE 135 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 136 - Assistant ===
The atexit handler is already wired. Slice 4 is done. Now Slice 6 — update the strategy doc:

=== MESSAGE 137 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 138 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 139 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 140 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 141 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 142 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 143 - Assistant ===
Let me also update the deferred item reference and run a final full test pass:

=== MESSAGE 144 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 145 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 146 - Assistant ===
Also update the sprint 5 reference:

=== MESSAGE 147 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 148 - Assistant ===
Now run the final comprehensive test pass:

=== MESSAGE 149 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 150 - Assistant ===
567 passed, 0 failed. Let me mark the final todo complete:

=== MESSAGE 151 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 152 - Assistant ===
Phase 5 is complete. Here's the summary:

## Phase 5 — Native Bridge and Background Process Supervision: COMPLETE

### What was built

**Core abstraction** — `@/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py` (871 lines):
- [CapabilityState](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:60:0-68:25) enum (6 health states), [BridgeStats](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:71:0-125:9) (metrics), [BridgeResult](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:128:0-144:27) (call wrapper)
- [ProcessSupervisor](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:225:0-832:9) class: process pool with leases, circuit breaker, bounded stderr drain (64KB), supervised readline with timeout, JSON + line protocol support, graceful shutdown/restart
- Global registry with `atexit` handler — [register()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:840:0-849:37), [shutdown_all()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:852:0-861:75), [list_supervisors()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:864:0-867:30)

**6 bridges migrated** (net reduction: 2,598 → 1,435 lines):

| Bridge | File | Before | After |
|--------|------|--------|-------|
| Rust evolution | [_rust_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_rust_bridge.py:0:0-0:0) | 146 | 84 |
| Julia yield | [_julia_yield_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_julia_yield_bridge.py:0:0-0:0) | 149 | 82 |
| Elixir actor | [_elixir_actor_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/evolution/_elixir_actor_bridge.py:0:0-0:0) | 137 | 73 |
| Haskell replay | [replay_simulation.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/memory/replay_simulation.py:0:0-0:0) | ~55 | ~30 |
| Koka native | [koka_native_bridge.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_native_bridge.py:0:0-0:0) | 898 | 563 |
| Koka batch | [koka_batch_client.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/koka_batch_client.py:0:0-0:0) | 581 | 368 |

**Shutdown wiring** — [shutdown_all()](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/core/acceleration/process_supervisor.py:852:0-861:75) added to both stdio and HTTP cleanup paths in [run_mcp_lean.py](file:///home/lucas/Desktop/WHITEMAGIC/core/whitemagic/run_mcp_lean.py:0:0-0:0).

### Tests — 24 fault-injection tests, all passing

`@/home/lucas/Desktop/WHITEMAGIC/core/tests/unit/hardening/test_phase5_process_supervisor.py` (727 lines) covering all 7 strategy scenarios: excessive stderr, init hang, mid-request hang, malformed JSON, pool exhaustion, shutdown during active calls, crash/restart cycles — plus lifecycle, lease, stats, line protocol, and global registry tests.

**567 related tests pass, 0 regressions.** Strategy doc updated with full completion status.

=== MESSAGE 153 - User ===
Incredible work! Thank you. And just to double check - everything from Phase 0 through Phase 5 is all green, right?

=== MESSAGE 154 - Assistant ===
Let me verify both the doc status and the actual test suite.

=== MESSAGE 155 - Tool ===
[CORTEX_STEP_TYPE_GREP_SEARCH]

=== MESSAGE 156 - Assistant ===
Doc shows all phases ✅ COMPLETE. But the header status line is stale — it says "Phase 4 ready to start" but Phase 4 and 5 are both done. Let me fix that, then run the full test suite to confirm green:

=== MESSAGE 157 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 158 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 159 - Assistant ===
**6,107 passed, 0 failed, 0 skipped.** All green across every phase.

| Phase | Status | Tests |
|-------|--------|-------|
| Phase 0 — Baseline, Protection, Measurement | ✅ COMPLETE | Included in 6,107 |
| Phase 1 — Canonical Runtime Contract | ✅ COMPLETE | Included in 6,107 |
| Phase 2 — Memory and Galaxy Boundary Consolidation | ✅ COMPLETE | Included in 6,107 |
| Phase 3 — Governance, Security, Cache, Fast-Path | ✅ COMPLETE | Included in 6,107 |
| Phase 4 — Typed Errors, Partial Operations, Async | ✅ COMPLETE | Included in 6,107 |
| Phase 5 — Native Bridge and Process Supervision | ✅ COMPLETE | 24 fault-injection tests + 0 regressions |

Full suite runs in ~111s. Zero failures, zero skips. The strategy doc header has been updated to reflect Phases 0-5 complete with Phase 6 ready to start.