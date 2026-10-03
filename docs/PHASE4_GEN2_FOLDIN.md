# Phase 4 — Gen2 9.1.8 fold-in register

**Status: working register · 2026-09-17 · compiles dispositions from existing evidence; assigns
no verdicts, changes no gates.** One screen answering "what do we still owe from 9.1.8?"
Sources: `PHASE4_GEN2_DELTA.md` §2 (the 9.1.7→9.1.8 ledger), `docs/findings/W1_gen2_source_map.md`
+ `W2_gen2_source_map.md` (file:line pointers), `PHASE4_WAVE_PLAN.md`, the frozen specs
(`docs/specs/W1_*`, `W2_*`), `PHASE4_ERRATA.md`. Capability-source reference stays **9.1.8**;
experimental control stays **9.1.7 forever** (delta §0). When v9.1.9 tags, append the delta.

**Disposition key:** **folded** — already expressed in a frozen spec · **fold-now** — open task,
no new registration · **link** — stays Gen2-side; Gen3 states the boundary · **gated** — waits on
its named gate · **watch** — future release.

| # | 9.1.8 capability / change | Evidence | Gen3 destination | Disposition | Precondition |
|---|---|---|---|---|---|
| 1 | Typed coordination effects (`CoordinationLease`/`Release`; strict `VIOLATION_AHIMSA`; exact-owner release always admitted) | delta §2.1 `42cb1f5`; `effects.rs:38-42,180-195`; `dharma_gate.rs:265-278` | B3 §1.1 | folded (spec) | — |
| 2 | Snapshot-readonly ledger reads (`check`/`list`; no lock/temp/prune; expired logically absent, still reportable) | delta §2.1; `coordination.rs:225-236,678,902` | B3 §1.1; W2_03 §3 | folded + **fold-now** audit | audit of Gen3 recall/inspect read paths |
| 3 | Root binding (`release` refuses alternate/escaping root) | delta §2.1; `coordination.rs:750-800` | B3 §1.1 | folded (spec) | — |
| 4 | `session.checkpoint_nodiscovery` (exact fields; no discovery/FS/subprocess; strict-admitted) | delta §2.1; `session.rs:376-492` | B2 §1.3 (rhythm) | **fold-now (post-deploy)** | 9.1.8 deploy |
| 5 | Git-capturing checkpoint declares reads/spawns, refused under strict | delta §2.1 | B2 §1.3 | folded (spec) | — |
| 6 | Signed-only mesh discovery (freshness 2×interval, rate limit, replay cache, TOFU bind) | delta §2.2 `8804b53` | Wave-5 mesh gate | gated | two-gate + egress/consent hook (handoff note B) |
| 7 | HKDF purpose-scoped key separation (`WM_MESH_KEY`) | delta §2.2 | Wave-5 | gated | own manifest receipt |
| 8 | Contract declarations 70→85 (manifest truth) | delta §2.3 | surface-comparison baseline | link | comparisons cite 85 |
| 9 | Onboarding surface (`wm grimoire load`, ingest ledger, `--dry-run`/`--redact`) | delta §2.4 `c4bcbde`/`cff34a0` | metabolism / stranger lane | link | not owed for alpha |
| 10 | Startup-under-stress fixtures (governance refusal vs first-run starvation kept distinct) | delta §2.4 | A1 case 9; B3 case 10; W2_02 case 7 | folded (adversarial) | fixtures wired with acceptance slices |
| 11 | Truth hygiene (release entry, test counts, docs-vs-shipped) | delta §2.5 | protocol §5 (already law) | folded (discipline) | — |
| 12 | Claims write-through (`16198ea`; durable on add/resolve) | W1 map §6; `receipts/IMPL_*` lineage | B4 §1.4 | folded (Gen2-side done) | remaining JSON stores = fold-now (ops) |
| 13 | Evidence-bundle v0 disclosure fields | W1 map §2; `memory_ops.rs:45-183` | A2 §1.4 (link boundary) | folded + **fold-now** parity check | bundle↔journal join check |
| 14 | Session write-time indexing (9.1.7 carry) | 9.1.7 Tier-1; delta | B2 case 7 | link (Gen2 behavior) | — |
| 15 | Per-file SHA-256 ingest ledger (`ingest_ledger.jsonl`) | W1 map §1; delta §2.4 | A1 §1.2 template | link + folded (spec template) | — |
| 16 | Read-open-under-starvation posture (`WM_HOMEOSTASIS_FROZEN` distinct from refusal) | delta §2.1/§2.4 | A2 case 9; B3 case 10 | folded (adversarial) | fixtures wired with acceptance slices |
| 17 | Mesh quarantine/bad-apple enforced at ingest | delta §2.2 | Wave-5 | gated | transport adoption receipt |
| 18 | 9.1.9-dev drift (F5–F8 slices on `main`; 303/86 vs tag 302/85) | errata #17; `main` commits | delta §0 reference rule | watch | append delta when `v9.1.9` tags |

## Fold-now shortlist (deploy-window checklist)

1. **9.1.8 deploy** — **done** 2026-09-17: artifact verified (`wm 9.1.8`, 303/86, sha256
   `cc5b4004…`), installed at `~/.local/bin/wm` (backup `wm.bak-9.1.7-20260917`), systemd fleet
   restarted (9 `wm-serve@` stores + gateway + mesh node, 11/11 active).
2. **Switch the WMgen3 session rhythm** to `checkpoint_nodiscovery` — **done**: reachable via the
   gateway; skill updated; effective at this session's close (caller-supplied commit/branch/
   tests_green/next_queue/open_flags; no discovery — ends the WMv9-HEAD capture quirk).
3. **Bundle↔journal parity check** — **done** (`docs/BUNDLE_JOURNAL_PARITY.md`;
   `OPS_FOLDIN_PARITY_AUDIT_2026-09-17`).
4. **Read-path discipline audit** — **done** (`docs/READ_PATH_AUDIT.md`;
   `OPS_FOLDIN_PARITY_AUDIT_2026-09-17`).
5. **Remaining JSON-store write-through** (WMv9 side; claims done at `16198ea`) — **audited**
   2026-09-17 (`docs/WMV9_JSON_STORE_AUDIT_2026-09-17.md`). **Lane rule:** these are WMv9 (Gen2)
   tree changes and land through the Gen2 release process — never mixed into Gen3-lane commits;
   the deployed 9.1.8 artifact (12:06) predates the claims write-through (18:01), so the
   read-only hole is a source-tree finding, not a live fleet one. Queued for the Gen2 lane:
   claims read-only declaration fix, atomic WT for conformal/calibration/escalation/tx_firewall,
   debounced WT for self_model/tool_stats/OATS/shadow_stats/gana_registry.
6. **Wire the stress fixtures** (#10/#16) — A1 case 9 is covered (`IMPL_A2_DISCIPLINE` +
   `IMPL_A1_FIXTURES` partial); B3 case 10 / W2_02 case 7 fixtures wire with their acceptance
   slices (not yet built).

## Explicit non-folds

Gen2 architects (planners, RRF, reranker chain — behavior under test; nucleus rule 1) · engine
catalogs/alchemical counters (wave-2 §3) · the caller-asserted RSI loop as-is (W2_06 requires an
independent witness first) · unsigned mesh transports (#6/#7/#17 stay gated) · curated-profile
exclusions smuggled through links. Nothing here resurrects a verdict; WEAK stays WEAK.
