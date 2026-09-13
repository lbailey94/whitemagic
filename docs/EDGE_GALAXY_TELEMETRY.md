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

## Retention (current state and plan)

- **Today:** `galaxy.cold_rotate` archives and (with confirm) deletes only
  `is_telemetry_or_noise` rows — telemetry is exactly its remit; `galaxy.purge`
  exists for hard resets (`{"confirm": true}` required). Write budget ledger
  has a 90-day horizon.
- **Planned policy** (not yet wired): ring 5 min / windows 7 d / hourly
  rollups 90 d; a per-galaxy retention entry on the galaxy taxonomy so the
  policy is declared once, versioned, and attributable.

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
