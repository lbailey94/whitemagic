# RSI Phase 2 Strategy: Outward Spiral — 2026-08-06

## Context

The RSI Phase 1 system (friction logging, improve proposals, redteam proposals)
is functional and demonstrated end-to-end value in its first real-world test:
8 friction entries → 2 improvement proposals → 1 fix applied (tool discovery).

However, the current system has five gaps that prevent it from becoming an
outward spiral (v2 was a circular loop — same friction, same fixes):

1. **Thin friction data** — only 3 fields captured (tool, error, latency)
2. **No deduplication** — 6 of 8 entries are duplicates
3. **Karma and friction are independent** — no feedback between governance and RSI
4. **Improve cycle is manual-only** — user must call `improve.proposals`
5. **No resolution verification** — can't distinguish "fixed" from "stopped"

## Architecture: The Outward Spiral

```
     ┌──────────────────────────────────────────────────────────┐
     │                                                          │
     ▼                                                          │
 Dispatch ──→ Rich Telemetry ──→ Deduplicated Friction Log      │
     │              │                    │                       │
     │              │                    ├──→ Karma Bridge       │
     │              │                    │      (debt signal)    │
     │              │                    │                       │
     │              │                    ▼                       │
     │              │           Improve Cycle (autonomous)       │
     │              │                    │                       │
     │              │                    ▼                       │
     │              │           Proposals (rsi:proposal)         │
     │              │                    │                       │
     │              │                    ▼                       │
     │              │           Human Review + Fix               │
     │              │                    │                       │
     │              │                    ▼                       │
     │              │           friction.resolve (verify)        │
     │              │                    │                       │
     │              │                    ├──→ Karma reduction     │
     │              │                    ├──→ Workspace reward    │
     │              │                    │                       │
     │              └────────────────────┘                       │
     │                                                           │
     └───── NEW friction at higher level (spiral outward) ───────┘
```

Key difference from v2 circular thinking: each loop iteration produces
*novel* friction at a higher level because:
- Resolved friction doesn't repeat (dedup + resolved tag)
- Re-appearance after resolution escalates severity
- Rich telemetry reveals new dimensions of friction not visible before
- Karma bridge ensures governance debt influences RSI priority

## Workstreams

### WS-1: Rich Friction Envelope — ✅ COMPLETE (2026-08-06)

**Goal**: Capture all telemetry already computed in the dispatch path.

**Changes**:
- `crates/wm-tools/src/expansion/rsi.rs`: Add `DispatchTelemetry` struct
- `crates/wm-tools/src/expansion/rsi.rs`: Expand `FrictionAutoLogTool::log_error()`
  to accept `&DispatchTelemetry` and store it as JSON in the friction memory's
  content (structured section)
- `crates/wm-tools/src/expansion/rsi.rs`: Add `log_anomaly()` method for
  successful dispatches with anomalous metrics (latency > P99, effectiveness
  < 0.3, karma debt > 0.5)
- `crates/wm-mcp/src/server.rs`: Construct `DispatchTelemetry` from existing
  data in the dispatch path and pass it to the friction auto-logger
- `crates/wm-consciousness/src/autonomous.rs`: Update `run_improve()` to
  parse telemetry from friction entries and group by new dimensions
  (brain_wave, confidence_band, effectiveness_quartile)

**New friction entry format**:
```json
{
  "tool": "memory.search",
  "success": false,
  "latency_ms": 45.3,
  "error": "Tantivy index not found",
  "brain_wave": "Beta",
  "effectiveness": 0.42,
  "karma_debt": 0.15,
  "self_model_confidence": 0.58,
  "drive_bias_confidence": 0.71,
  "tool_stats": {
    "call_count": 23,
    "success_count": 19,
    "p50_latency_ns": 12000000,
    "p99_latency_ns": 89000000,
    "cpu_time_ns": 276000000,
    "lmdb_pages_touched": 142
  },
  "routed_via_wm": true,
  "arg_size_bytes": 156,
  "response_size_bytes": 0
}
```

**Estimated effort**: ~200 LOC across 3 files. No new dependencies.

### WS-2: Friction Deduplication — ✅ COMPLETE (2026-08-06)

**Goal**: Prevent duplicate friction entries; update existing entries instead.

**Changes**:
- `crates/wm-tools/src/expansion/rsi.rs`: Add `friction_hash()` function
  (SHA-256 of `tool_name + category + severity + first 200 chars of error`)
- `crates/wm-tools/src/expansion/rsi.rs`: In `log_error()` and
  `FrictionLogTool::call()`, compute hash, scan Codex for matching
  `rsi:hash:{hash}` tag, increment `duplicate_count` on existing entry
  or create new
- `crates/wm-tools/src/expansion/rsi.rs`: Add `last_seen` timestamp to
  friction memory metadata
- `crates/wm-consciousness/src/autonomous.rs`: Update `run_improve()` to
  weight by `duplicate_count` (higher dup count = higher pattern strength)

**Behavior**:
- First occurrence: create entry with `rsi:hash:{hash}`, `duplicate_count: 1`
- Second occurrence: update entry, `duplicate_count: 2`, update `last_seen`
- Nth occurrence: `duplicate_count: N`, `last_seen: now`
- `friction.review` shows `duplicate_count` and `last_seen` in summary

**Estimated effort**: ~120 LOC across 2 files.

### WS-3: Karma-to-Friction Bridge — ✅ COMPLETE (2026-08-06)

**Goal**: Wire governance (karma) and RSI (friction) into a bidirectional feedback loop.

**Changes**:
- `crates/wm-mcp/src/server.rs`: After `karma_ledger.record()`, check if
  `total_debt > FRICTION_KARMA_THRESHOLD` (0.5). If so, call
  `friction_auto_log.log_error()` with category "governance", severity
  mapped from debt level (0.5→medium, 0.8→high)
- `crates/wm-tools/src/expansion/rsi.rs`: In `log_error()`, after storing
  friction entry, call `karma_ledger.record()` with a synthetic
  "friction_signal" entry (small debt delta: 0.01 per friction entry)
- `crates/wm-governance/src/karma_ledger.rs`: Add `record_friction_signal()`
  method that records a minimal karma entry with `tool: "__rsi__"` and
  a small debt delta

**Feedback dynamics**:
- Tool accumulates karma debt → friction entry generated → improve cycle
  sees governance friction → proposal to investigate the tool
- Friction entries → small karma debt → cumulative debt → governance
  friction → higher priority proposal
- Resolved friction → karma debt reduction (WS-5) → tool health improves

**Estimated effort**: ~100 LOC across 3 files.

### WS-4: Proactive Improvement Surfacing — ✅ COMPLETE (2026-08-06)

**Goal**: Run Improve cycle autonomously during idle periods; surface proposals without manual invocation.

**Changes**:
- `crates/wm-mcp/src/server.rs`: Add `improve_dispatch_count` atomic counter
  alongside existing `dispatch_count`. Trigger Improve cycle every 50
  dispatches OR on brain-wave transition to Theta/Delta (idle states)
- `crates/wm-mcp/src/server.rs`: When Improve cycle produces proposals,
  store them as Codex memories with tag `rsi:proposal` + `rsi:proposal:active`
- `crates/wm-mcp/src/server.rs`: Emit workspace event with high salience
  (0.8) when proposals are generated, so they appear in `bus.recent`
- `crates/wm-tools/src/expansion/rsi.rs`: Add `improve.active_proposals` tool
  that retrieves active (unresolved) proposals from Codex
- `crates/wm-consciousness/src/autonomous.rs`: `run_improve()` should
  check for existing `rsi:proposal:active` entries and skip duplicate
  proposals (use signature comparison)

**Safety**:
- Improve cycle still requires human review — no autonomous action
- SpiralTracker prevents circular proposals (same signature → suspended)
- Only runs during idle brain-wave states (Theta/Delta) or every 50 dispatches
- Proposals are stored as memories, not executed

**Estimated effort**: ~180 LOC across 3 files.

### WS-5: Friction Resolution Verification — ✅ COMPLETE (2026-08-06)

**Goal**: Close the loop — mark friction as resolved, verify fixes, escalate on re-appearance.

**Changes**:
- `crates/wm-tools/src/expansion/rsi.rs`: Add `FrictionResolveTool`:
  - Takes `friction_id` (required) + `resolution_note` (required) +
    `resolution_method` (code_fix/config_change/doc_update/workaround)
  - Tags the entry with `rsi:resolved` + `rsi:resolved_method:{method}`
  - Records `resolved_at` timestamp
  - Calls `karma_ledger.record_friction_resolved()` to reduce debt
  - Emits workspace Reward event
- `crates/wm-tools/src/expansion/rsi.rs`: In dedup logic (WS-2), if a new
  entry matches a hash that has `rsi:resolved` tag:
  - Escalate severity by one level (low→medium→high→critical)
  - Add `rsi:regression` tag
  - Create a new entry (not dedup) with reference to the original resolved ID
- `crates/wm-governance/src/karma_ledger.rs`: Add `record_friction_resolved()`
  that reduces debt by 0.05 per resolution
- `crates/wm-tools/src/expansion/rsi.rs`: Update `friction.review` to show
  resolution status, regression count, and time-to-resolve metrics

**The outward spiral in action**:
1. Tool X fails → friction logged (severity: medium)
2. Tool X fails again → dedup, duplicate_count: 2
3. Improve cycle → proposal generated
4. Human fixes → `friction.resolve` called → debt reduced, workspace reward
5. Tool X fails again after fix → **regression detected** → severity escalated
   to high → new friction entry with `rsi:regression` tag → improve cycle
   sees regression → higher-priority proposal with different approach
6. Tool X fixed properly → no new friction → spiral moves to next issue

**Estimated effort**: ~250 LOC across 3 files.

## Implementation Order

```
WS-1 (Rich Friction) ──→ WS-2 (Dedup) ──→ WS-3 (Karma Bridge)
                                              │
                                              ▼
WS-5 (Resolution) ←── WS-4 (Proactive Surfacing)
```

1. **WS-1 first** — richer data is the foundation for everything else
2. **WS-2 second** — deduplication makes the data stream clean
3. **WS-3 third** — karma bridge requires clean friction data
4. **WS-4 fourth** — proactive surfacing requires all above
5. **WS-5 last** — resolution verification closes the loop

## Testing Strategy

- WS-1: Unit test that `DispatchTelemetry` is correctly serialized into
  friction memory content; verify all fields round-trip
- WS-2: Unit test that duplicate friction entries are deduplicated;
  verify `duplicate_count` increments and `last_seen` updates
- WS-3: Integration test that karma debt threshold triggers friction;
  verify friction entries cause small karma debt increase
- WS-4: Integration test that Improve cycle runs on dispatch count
  threshold; verify proposals are stored as `rsi:proposal:active`
- WS-5: Unit test that `friction.resolve` tags entry correctly;
  verify regression detection on re-appearance after resolution

## Impact on Existing Systems

- **No breaking changes** — all new fields are additive
- **No new dependencies** — uses existing SHA-256, LMDB, serde
- **No new crates** — changes confined to wm-tools, wm-mcp, wm-governance,
  wm-consciousness
- **Performance**: Dedup hash computation adds ~1 µs per friction log
  (SHA-256 of ~200 bytes). Friction logging is not on the hot path
  (only on errors/anomalies), so this is negligible.
- **Storage**: Rich friction entries are ~500 bytes vs ~200 bytes current.
  At 8 entries/day, this is 4 KB/day — negligible.

## Success Metrics

After implementation:
- ✅ Friction entries carry 15+ telemetry fields (vs 3 current)
- ✅ Zero duplicate entries in friction log (vs 6/8 current)
- ✅ Karma debt > 0.5 auto-generates governance friction entries
- ✅ Improve cycle runs autonomously every 50 dispatches
- ✅ `friction.resolve` available as MCP tool
- ✅ Regression detection on re-appearance after resolution
- ✅ `improve.proposals` produces proposals grouped by new dimensions

**All 5 workstreams complete.** 2,781 tests, 171 tools, 0 clippy warnings, fmt clean.
