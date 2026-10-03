# Wave-2 spec 07 — Self-model / inspect

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Self-model / inspect (wave plan §3; **link + compile (inspect)** · E18).
**Wire:** tier-map / selection explanations (N3).
**Nucleus touch points:** N3 (inspect), N4 (journal), N5 (audit discipline); Part 1 invariant 6
(truthful surfaces).
**Caution carried:** **"calibration" names four disjoint universes** — this spec names **one**:
the **self-model metric series** (journaled per-metric). It is explicitly not the conformal tool
store (`calibration_store.json`), not the env-gated recall conformal (which refuses honestly when
unconfigured), and not the claims ledger (B4 owns that universe).
**Corrections carried:** G-26 (CORRECT fired in the dream log; "never CORRECT" is
artifact-qualified); possibility-winners overwrote boot constants (excluded class).

---

## 1. Frozen behavioral spec

### 1.1 Inspect contract (compile side)

- `inspect` answers, per state: **tier · authority · explanation** — the selection-explanation
  obligations (N3), covering the tier map and the relation/strata state (A3/W2_03), and it is
  **read-only** (no mutation while inspecting; snapshot discipline — 9.1.8).
- Inspect never certifies: it reports state and evidence pointers; certification language is
  excluded (C6: inspect → tier map, an inventory, not a verdict).

### 1.2 The one calibration universe (named)

- This row's calibration = the **self-model metric series**: per-metric observations journaled,
  forecasts/alerts derived from them, thresholds **statutory** (Tier-2). A calibration claim must
  name this universe; cross-universe quotes are failures (wave-2 lesson).
- **Feeder discipline:** the series is fed only by observed metrics; the v26 model had exactly
  one feeder (an operator/tool call) and no automatic observer — an **unfed model is
  display-only** and must disclose that (no forecast claims without ≥ the declared minimum
  points).

### 1.3 Durable actions, not in-memory theater

- Any graduated action (OBSERVE→ADVISE→CORRECT→INTERVENE class) is **durably journaled** when it
  fires; v26's action list was in-memory only (`harmony/activity_log.jsonl` = 55 rows, all READ —
  but the dream log carries 361 CORRECT lines; qualify by artifact, G-26).
- Alarms that act (tier upgrade, proactive consolidation) require the series + statutory
  thresholds; acting without them is excluded.

### 1.4 Optimizer outputs are proposals, never silent constants

- Resumed optimizer targets carry provenance; declared values change only via their own
  registration (v26 winners rewrote boot constants with no outcome verification — excluded).

### 1.5 The link boundary

- Gen2's self-model persists `self_model.json`; the conformal tool store is its own universe;
  recall conformal is env-gated and **refuses honestly when unconfigured** (the honesty
  reference: `memory.recall_feedback` refusal). The link states which surface shows what; a
  display-only surface is never presented as a working loop.

### 1.6 Statutory parameters named (Tier-2)

Series window · alert thresholds · minimum points for forecasts · action-eligibility rules.
Nothing swept.

### 1.7 Non-goals

No cross-universe calibration quotes · no unfed-model claims · no in-memory action claims · no
silent constant replacement · no certification via inspect · no conformal/claims conflation.

---

## 2. Selection history

**Ancestor (Gen1 v26):** `self_model.py` — in-memory deques (window 100), linear-regression
forecasts + threshold alerts; **no state file** in either state root; readers that act (router
tier upgrade on error-rate, fusion proactive dream on falling energy, army) existed; only feeder
found = `gnosis.record_metric` (operator/tool); no automatic observer; no forecast ever fired
live (UNVERIFIED). Possibility winners: self-scored fitness rewrote `guna_balance` targets
(sattvic 0.169 / rajasic 0.327 / tamasic 0.518) with no outcome verification. Identity proposals
103/103 unapplied (adjacent, not this row).

**Gen2:** `SelfModel` live (persisted `self_model.json`; confidence injected into dispatch
context); conformal classifier/regressor + `calibration_store.json`; env-gated recall conformal;
four calibration universes (divergence W2-5). E18: PRESERVE IMPL. → link; calibrate only over
resolved claims (that half belongs to B4).

**Evidence levels:** v26 model SOURCE-IMPLEMENTED; fed-live UNVERIFIED; winners file persisted
(MEASURED artifact); Gen2 selfmodel/conformal live (SOURCE-IMPLEMENTED); recall conformal
refusal-honest (SOURCE-IMPLEMENTED + tested); Gen3 inspect target NAMED (N3/C6 template).

---

## 3. Adversarial cases

1. **Unfed model** — disclose display-only status; no forecast claims below minimum points.
2. **Cross-universe quote** — a calibration claim not naming the self-model series fails.
3. **In-memory actions** — actions not durably logged are not actions; CORRECT/INTERVENE claims
   are artifact-qualified (G-26).
4. **Silent constant replacement** — optimizer outputs need provenance + registration.
5. **Certification creep** — inspect reports state; it never certifies (C6 boundary).
6. **Acting alarms** — tier-upgrade/consolidation triggers require series + statutory thresholds.
7. **Read-only inspect (9.1.8)** — inspection leaves store/journal bytes unchanged.
8. **Starvation** — inspect reads stay open; a degraded self-model is disclosed, not hidden.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Metric series (journaled) | forecasts/alerts computable | uncomputable | EXECUTED → EFFECTFUL |
| Feeder | model fed | display-only (must disclose) | RE-ENTERS |
| Graduated actions | durably logged firing | no durable evidence → not counted | PERSISTENT |
| Winners/targets file (v26 class) | overrides present | declared defaults return; measurable? else decoration | EFFECTFUL |

No inert passengers: an alert with no statutory threshold and no logged firing is decoration.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Inspect answers** — tier/authority/explanation per state; read-only.
2. **Universe labeling** — every calibration output names the self-model series.
3. **Durable action log** — graduated actions journaled (or absent, disclosed).
4. **Feeder disclosure** — fed vs display-only stated.
5. **No silent constants** — provenance for every resumed target.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_07_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
