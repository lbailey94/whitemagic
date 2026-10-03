# WMv9 mutable JSON-store persistence audit (2026-09-17)

**Status: read-only audit (ops fold-in #5; "remaining JSON-store write-through").** Executed by
explore agent + session `68c17d3b` against WMv9 `c27b36a`. Read-only; no WMv9 changes made.
Paths relative to `~/Desktop/WHITEMAGIC/WMv9/`.

**Lane rule (operator, 2026-09-17):** fixes to this inventory are **WMv9 (Gen2) tree changes** and
land through the Gen2 release process — never mixed into Gen3-lane commits. This audit is a
Gen3-lane artifact; the fix scope queues with the Gen2 lane. The deployed 9.1.8 artifact (built
12:06) **predates** the claims write-through (`16198ea`, 18:01), so the read-only hole in §4.1 is a
source-tree (9.1.9-dev) finding, not a live fleet one.

**Trigger:** the 2026-09-17 ledger-loss incident (JSON stores flushed only in
`McpServer::shutdown()`; ungraceful replacement lost mutations). Claims fixed write-through
(`16198ea`); this audit inventories what remains.

## 1. `save_mutable_state()` inventory (`crates/wm-mcp/src/server.rs:2414-2651`)

12 stores: `mutable_gana_registry.json` · `mutable_dynamic_galaxies.json` ·
`mutable_learned_dream.json` · `mutable_shadow_stats.json` · `mutable_tool_stats.json` ·
`mutable_oats.json` · `conformal_store.json` · `calibration_store.json` · `claims_ledger.json`
(now WT) · `self_model.json` · `escalation_queue.json` · `tx_firewall_policy.json`.

**`wm serve` has no periodic checkpoint** — every one of these is lost since process start on
ungraceful replacement. The daemon mode checkpoints every 300 s (`daemon.rs:1130-1136`).

## 2. Behavior table (persistence)

| Store | Behavior | Mutation entry (file:line) | Freq |
|---|---|---|---|
| GanaRegistry | SD/DEB | `wm-dispatch/src/pipeline.rs:1030` (every dispatch) | high |
| ToolStats | SD/DEB | `pipeline.rs:958,990` (every dispatch) | high |
| ShadowModeStats | SD/DEB | `wm-tools/src/lib.rs:3029` (every NLU classify) | high |
| OATS stats | SD/DEB | `wm-tools/src/lib.rs:3690,3696` (`wm thought=` paths) | high |
| SelfModel | SD/DEB | `server.rs:2835-2841` (per request), `:3778-3780` (per dispatch) | high |
| ConformalStore | SD/DEB | `conformal.rs:238,246,327,339` + fits/import | low |
| CalibrationStore | SD/DEB | `simulation_tools.rs:396,422` (`simulation.calibrate`) | low |
| EscalationQueue | SD/DEB | `dharma.rs:440,581` | low |
| TxFirewall | SD/DEB | `firewall.rs:196` | low |
| ClaimsLedger | **WT** `claims_tools.rs:77` | `claims_tools.rs:181,227` | low |
| RecallConformal | **WT after fit** `recall_conformal.rs:131` | `recall.rs:332` (`memory.recall_feedback`) | medium |
| Resonance events | JRNL WT `bus.rs:482-491` | every `emit` | high |
| Bounty board / ledger | WT | `bounty_connector.rs:406`, `bounty_ledger.rs:108-112` | low |
| Code leases | WT (tmp+rename) | `coordination.rs:211-213` | medium |
| Learned cycles | DEB (daemon-owned) | `autonomous.rs:774` | low-med |
| Dynamic galaxies / learned dream | SD/DEB | `autonomous.rs:1050`, `dream.rs:599` | low |
| `write_budget.json` | atomic WT (5-min throttle) | `wm-substrate/src/write_budget.rs:219-237` | medium |

## 3. Recommended fix shapes

- **Low-frequency, write-through like claims (atomic tmp+rename):** conformal, calibration,
  escalation, tx_firewall. Serialization helpers already exist (`to_json`/`from_json`).
- **High-frequency, debounced write-through (or LMDB):** self_model, tool_stats, OATS,
  shadow_stats, gana_registry. `save_oats`/`load_oats` exist but `save_oats` is shutdown-only.
- **Leave + document:** learned dream / dynamic galaxies (daemon-debounced, low mutation), learned
  cycles (daemon-owned), `stats_history.jsonl` (derived rollup).

## 4. Findings beyond write-through (read-only holes; UNVERIFIED reach)

1. **Claims base route declares read-only effects** (`claims_tools.rs:51`) while aliases declare
   writes (`:358-361`) — on a `--readonly` server the gate permits `claims` add/resolve and the
   new write-through **writes to disk**, bypassing the "read-only must not write state files"
   guard (`server.rs:2123-2125`). Live defect class.
2. Under-declared in-memory mutators: `dharma.escalate` (`dharma.rs:372` pure),
   `conformal.fit_*`/`import` (`conformal.rs:199,280,374,458,528` pure), `simulation.calibrate`
   (`simulation_tools.rs:336` read-only). No disk write on readonly (save suppressed), but the
   read-only contract is violated in memory.
3. Plain `--readonly` still writes `resonance_events.jsonl` (`server.rs:938-941`) and violet key
   files (`expansion/mod.rs:614-621`); only `preservation_readonly` suppresses them.
4. `recall_conformal.json` persists only after fit (≥ 10 samples); early samples and failed-fit
   samples are lost on restart; not in `save_mutable_state`.
5. `episodic_aliases.json` has a reader but no writer in the repo (UNVERIFIED provenance).

**No verdict/claim movement.** Fix scope is an operator decision; the audit changes nothing by
itself.
