# Edge galaxy — OS telemetry in WhiteMagic (2026-09-13)

**Status:** first slice live (Lakshmi `--emit` → `telemetry` galaxy +
`os_telemetry_threshold` bus events). Raw samples never leave the producer.

## Purpose

Make OS telemetry durable, time-queryable, and legible to both low-layer
systems and AI — without flooding memory or polluting cognition.

## The galaxy

`Galaxy::Telemetry` (`crates/wm-core/src/galaxy.rs`, db name `telemetry`) is
a **Memory galaxy that is deliberately excluded from default cognition**:

- **Not in `Galaxy::memory_galaxies()`** → default recall, `memory.list`,
  reindex and re-embed backfills skip it; query it explicitly
  (`memory.search {galaxy: "telemetry"}`).
- **Skipped by dream and lifecycle passes** (`dream.rs` scan/cycle skips,
  `lifecycle.rs` full cycles) — evidence, not cognition.
- Rows carry the `telemetry` tag, which also trips `is_telemetry_or_noise`
  (novelty/miner/smarana/consolidation guards) as a second line of defence.
- Legacy migration maps old `telemetry` data to this galaxy
  (`wm-mcp/src/migrate.rs`).

## Layering

| Layer | Mechanism | Retention |
|---|---|---|
| Raw samples | producer-local ring (`Lakshmi.samples`, VecDeque) | seconds–minutes, volatile |
| Windows | `telemetry` galaxy memories (1-min rollups) | long-lived, queryable |
| Events | Gan Ying bus `os_telemetry_threshold` (in-memory + JSONL if enabled) | ring/256 + 5 MiB JSONL |
| Aggregates | future rollups (hourly/daily) — planned | planned 90 d |

## Window schema (written by Lakshmi)

```json
{
  "kind": "telemetry.window",
  "ts": "2026-09-13T21:11:55+00:00",
  "window_seconds": 60,
  "source": "laksmi",
  "tags": ["telemetry", "edge", "laksmi", "window"],
  "harmony_score": 0.66,
  "dims": {"fairness": 0.21, "responsiveness": 0.72, "throughput": 0.74,
           "stability": 0.98, "energy": 0.78, "dharma": 1.0, "karma_debt": 0.23},
  "dim_notes": {"responsiveness": "PSI cpu some avg10=14.8", "...": "..."},
  "guna": {"sattvic": 15, "rajasic": 3, "tamasic": 48},
  "top": [{"comm": "llama-server", "share": 0.15, "guna": "rajasic"}],
  "events": [{"topic": "os.telemetry.energy", "value": 0.5, "threshold": 0.9,
              "window": "60s", "state": "crossed"}],
  "karma": {"total": 116.3, "delta": -0.0},
  "dharma": {"total": 10, "blocked": 0, "delta_total": 1, "delta_blocked": 0}
}
```

`dim_notes` is the honesty field: every score names its source and caveat
(e.g. "RAPL unreadable … neutral 0.5").

## Producer — Lakshmi

```bash
# one window (verification)
lakshmi.py --once --json --emit --emit-url http://127.0.0.1:18790

# continuous: 1-min windows (match --window to --emit-every)
lakshmi.py --interval 5 --window 60 --emit --emit-every 60 \
           --dharma-mcp http://127.0.0.1:28795
```

- **Target:** `--emit-url` (default home gateway `:18790`) + `--emit-galaxy`
  (default `telemetry`; use `substrate` only for servers predating this
  galaxy).
- **Fail-soft spool:** every window is appended to a bounded local ring
  (`~/.local/share/lakshmi/telemetry_spool.jsonl`, ~7 days) *before* sending;
  replay is oldest-first on the next successful emission and stops at the
  first failure. WM being down never affects OS sampling.
- **Dedup safety:** windows embed `ts`, so the write-gate dedup path never
  suppresses a distinct window.

## Bus events

Threshold crossings emit `os_telemetry_threshold`
(`crates/wm-cognitive/src/resonance/event_type.rs`, Harmony category,
Sensory nervous system) with payload
`{topic, value, threshold, window, state}` — e.g.
`os.telemetry.responsiveness` below 0.3, `os.telemetry.stability` below 0.8,
`os.telemetry.energy` below 0.9 **when measured** (the neutral "unavailable"
proxy never fires), and `os.telemetry.dharma_blocked` on any window with a
positive blocked delta. Crossings are change-based: one event on entry, not
one per window. Bus events are ephemeral (rule: low-latency, not durable
evidence — the durable record is the window).

## Retention (implemented 2026-09-13)

The ladder lives in `telemetry.rollup` + `telemetry.prune` (plus the
producer's local ring):

| Tier | Mechanism | Target |
|---|---|---|
| Raw samples | producer ring (volatile) | minutes |
| Windows | `telemetry.window` records | 7 d (`windows_older_than_days=7`) |
| Rollups | `telemetry.rollup` — deterministic hourly aggregates (avg/min/max per dim, guna sums, event topics); re-runs deduplicate | 90 d (`rollups_older_than_days=90`) |

- `telemetry.record` — typed ingestion (validates kind/ts/harmony_score/dims,
  caps importance at the telemetry class ceiling 0.40, dedup-aware).
- `telemetry.rollup` — aggregates **completed** hours by default
  (`include_current=false`); `dry_run` supported.
- `telemetry.prune` — destructive with pipeline `confirm`; **dry-run defaults
  to true**. Note: it declares `destructive`, so the dharma gate can veto it
  under stress (observed live: `VIOLATION_AHIMSA … strict mode` while the
  host was busy).
- `telemetry.retention` — **read-only retention planner** (v9.1.5+): per-tier
  counts/bytes/oldest-newest/eligible under the exact horizons prune uses,
  plus `managed: false` observation inventory (policy decision records are
  governance evidence and are not pruned). It declares no writes and is never
  confirm-gated or dharma-gated, so pre-prune evidence is always available —
  live-verified on a scratch store 2026-09-14 (planner reported
  `next_eligible_since` and `prune_due`; a wet prune was then vetoed by the
  dharma gate under load, which the planner makes visible instead of silent).
- `galaxy.cold_rotate` remains the bulk archival path for
  `is_telemetry_or_noise` rows.

Operator wiring: `telemetry.rollup` runs hourly via Lakshmi
(`lakshmi-rollup.timer`); the weekly retention pass is now installed as
`wm-telemetry-retention.{service,timer}` (repo: `ops/telemetry/`, timer
`Sun 05:10` + `Persistent=true` + randomised delay). The one-shot runs the
read-only planner first, then a confirmed prune — on a pre-9.1.5 fleet the
planner answers `Unknown tool` and the script proceeds with prune alone
(observed live 2026-09-14: planner unavailable, prune `scanned: 77,
candidates: 0, status: success`). Install:

```bash
cp ops/telemetry/wm-telemetry-retention.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now wm-telemetry-retention.timer
```

## Operational findings (2026-09-13, live edge serve)

- **Health-scaled write budgets can starve steady fan-in.** Yama scales
  `max_writes_per_minute` by system health; under dev-build load the limit
  fell to 10/min and a spool burst hit `Budget exceeded for writes: 10/10`.
  The telemetry serve now sets `WM_RESOURCE_MAX_WRITES_PER_MIN=240` —
  telemetry is steady, low-volume, and non-cognitive, so stress-scaling it
  buys nothing. Producers should still treat budget rejections as retryable.
- **Dedup is delivery.** If a response is lost after the row was stored,
  replay re-creates identical content and the write gate answers
  `status: "deduplicated"` (with `dup_count` bumped). Consumers must treat
  that as an ack — Lakshmi's spool now does.
- **Out-of-order replay is acceptable.** Windows carry `ts`, so the spool
  probes the newest entry when the head is stuck (freshness path) rather
  than blocking all newer windows behind one slow record.

## Consumers

```bash
# last windows, explicit galaxy (default recall deliberately excludes it)
wm(route='memory.search', args={query: 'laksmi responsiveness', galaxy: 'telemetry', limit: 20})

# threshold history (in-memory ring; category harmony)
wm(route='bus.recent', args={limit: 50, category: 'harmony'})

# galaxy health/statistics
wm(route='galaxy.stats', args={galaxy: 'telemetry'})
```

## Rules (keep it from rotting)

1. No raw samples in memory — raw → producer ring; windows → galaxy.
2. Evidence, not cognition — dedicated galaxy + `source=laksmi` +
   exclusion from default recall/dream/consolidation.
3. Append-only + attribution — windows are never rewritten; policy/threshold
   changes must be versioned and disclosed (anti-Maya).
4. Fail-soft — producer spool replays; OS safety never depends on WM uptime.
5. No closed loop without hysteresis — future actuation (Tiferet ladder)
   needs observe-mode, hysteresis, rollback, and disclosed policy ids.

## Verification (evidence from the first live run)

- `Lakshmi --once --emit` → `emit: 1 window(s) → telemetry (spool 0)`.
- `memory.search {query: "laksmi responsiveness", galaxy: "telemetry"}`
  → `count` ≥ 1, `recall_mode: fts`.
- WM-down drill: 2 windows spooled (`Connection refused` disclosed), replay
  sent both plus the new one (`emit: 3 window(s) → telemetry (spool 0)`),
  spool file 0 bytes.
- `bus.emit os_telemetry_threshold` → `bus.recent {category: "harmony"}`
  returns the event with its payload intact.

## 72-hour soak gate (due 2026-09-17 14:26Z)

Started 2026-09-14 00:00:58 UTC (`edge-galaxy.service`, dev-build stand-in
until the v9.1.x fleet deploy); **re-baselined 2026-09-14 14:26:36 UTC** after
the host rebooted at 14:25:53 UTC — the process restarted, so the continuity
criterion resets (disclosed, not silently extended). Gate due 72 h later:
**2026-09-17 14:26:36 UTC**. Run these checks in order; all four must pass for
the gate to count.

1. **Continuity** — one process, no restarts, ≥72 h uptime:
   ```bash
   systemctl --user show edge-galaxy.service \
     -p ActiveState,SubState,NRestarts,ExecMainStartTimestamp,MemoryCurrent
   ```
   Pass: `ActiveState=active`, `SubState=running`, `NRestarts=0`,
   `ExecMainStartTimestamp=Mon 2026-09-14 10:26:36 EDT` (or later; an earlier
   start means the clock was not re-baselined after the reboot).
2. **Store integrity** — the 9.1.5 planner reads the tiers without error.
   The dev stand-in (9.1.3) lacks `telemetry.retention`, so run the planner
   with the fleet binary **without stopping the soak writer** (a read-only
   serve holds no writer lock):
   ```bash
   wm doctor --store ~/.local/share/edge-galaxy            # read-only audit
   wm serve --profile full --readonly --transport sse \
     --bind 127.0.0.1:18999 --store ~/.local/share/edge-galaxy &
   curl -sS -X POST http://127.0.0.1:18999/mcp \
     -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":
         {"name":"telemetry.retention","arguments":{}}}'
   # kill the scratch serve when done; it writes nothing
   ```
   Pass: no corruption; `eligible`/`prune_due` consistent with the 7 d/90 d
   horizons (at 72 h nothing should be eligible for prune).
   Soak producer (resolved 2026-09-14): `lakshmi-edge-sampler.service` is a
   dedicated instance emitting to 18798 (the fleet sampler keeps emitting to
   18790 — production telemetry stays intact), with its own state dir and
   spool so the two samplers never share the mirror. Verified live: windows
   86 → 90 within minutes of enablement (newest `2026-09-14T18:30:06Z`).
   Disclosure: the process has run since 14:26:36 UTC but had no producer for
   its first ~4 h (fan-in resumed 18:27Z); the gate keeps the 14:26:36Z
   baseline with that gap recorded rather than moving the goalposts.
3. **Quiet journals** — no unexplained errors since the re-baseline:
   ```bash
   journalctl --user -u edge-galaxy.service --since '2026-09-14 14:26' -p warning --no-pager | tail -20
   ```
   Pass: only expected entries (budget warnings imply the env headroom was
   lost; investigate before passing).
4. **Rollup chain** — if the Lakshmi rollup timer is enabled, hourly rollups
   exist for completed hours; if disabled, record that as a known gap (the
   timer is not required for the gate, only disclosed):
   ```bash
   systemctl --user list-timers --all | grep -i lakshmi
   ```
   Soak rollups: `lakshmi-edge-rollup.{service,timer}` posts to 18798 hourly
   (the fleet rollup keeps posting to 18790). `telemetry.rollup` aggregates
   completed hours only, so the first soak-hour rollup lands after
   `2026-09-14T19:00Z`; the two existing rollups are pre-soak
   (`2026-09-13T23:08Z`). Verify with the planner's `rollups` inventory.

### Pre-check (2026-09-14, post-reboot, before first gate run)

| Check | Result |
|---|---|
| Continuity | `active`/`running`, `NRestarts=0`, start 14:26:36Z — **pass so far** |
| Store integrity | `wm doctor --store ~/.local/share/edge-galaxy`: all healthy; planner via read-only 9.1.5 serve: 86 windows / 2 rollups / 0 observations, nothing eligible — **reads clean; fan-in resumed 18:27Z (86 → 90 windows, newest 18:30Z)** |
| Quiet journals | no warnings since midnight/reboot — **pass so far** |
| Rollup chain | edge timer active hourly against 18798 — **first soak-hour rollup after 19:00Z** |

Producer wiring (resolved): the fleet sampler/dashboard keep the production
store (18790); the soak store is fed by the dedicated edge units
(`lakshmi-edge-sampler`, `lakshmi-edge-rollup`). Installed and verified
2026-09-14; LAKSHMI README updated to match.

**Decision on pass:** promote the telemetry writer to the 9.1.5 fleet build
(remove the dev-binary stand-in), keep the retention timer, and re-baseline
the 7 d/90 d horizons from the soak start.
**On fail:** do not promote; capture the failing artifact, fix, and restart
the soak clock. A gate that is quietly extended is not a gate.
