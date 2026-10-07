# Wave-2 spec 03 — Currentness strata

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Currentness strata (wave plan §3; **compile (native)** · N2).
**Wire:** structural strata 0/1/2 (already frozen, N2).
**Nucleus touch points:** N2 (admitted mechanism); Part 3 arbitration-mode statute.
**Caution carried:** **runtime behavior, not env knobs** — Gen2's strata are an enum + dream-only
sweep behind `WM_VALIDITY_SWEEP`/`WM_VALIDITY_ENFORCE`; a request-time derived relation is the
contract target (divergence W2-6).
**Do not re-raise:** F4 (duplicate proposals — nucleus §5; guard applies here); P2D claim stays
WEAK (S3).

---

## 1. Frozen behavioral spec

### 1.1 Derivation is request-time

- Strata are computed **at recall** from the live supersedes relation: **0 = current** (source of
  a live `Supersedes` edge) · **2 = superseded** (has `superseded_by`) · **1 = unresolved**
  (everything else) (`ops.rs:496-504,625-634`). `include_historical: true` sets all strata to 1
  (deliberate uniformity, not missing data). (SOURCE-IMPLEMENTED; RUNTIME-OBSERVED, C2/C5)
- **No environment variable gates the derivation or enforcement.** Statutory switches that may
  exist (`WM_GEN3_SWEEP` proposal side; arbitration mode ordering side) do not change the
  semantics above; a knob-dependent strata state is the excluded class.
- The relation side is A3's contract (candidacy v1, direction, F4 guard); this row owns the
  **derivation + ordering semantics** at request time.

### 1.2 Ordering semantics

- Structural mode: stratum asc, then lexical desc → semantic desc → recency desc → id desc
  (`ops.rs:642-648`; B1 owns the within-stratum key). Default `PenaltyMultiplier` orders by key
  and is **not** the strata mechanism; a spec/acceptance quoting strata must name the mode.
- Current-value questions prefer the newest value-bearing statement; non-state queries keep score
  order (A3 §1.2).

### 1.3 Relation identity and phantom states

- **F4 guard binds this row:** duplicate relation rows for one endpoint pair must not create
  phantom current/superseded states; strata derive from the endpoint pair's effective relation
  (recall applies the last relation per F4), and any relation-count metric dedupes endpoints
  (A3 guard, nucleus §5). A duplicate must never make a record appear in two strata.

### 1.4 Evidence and disclosure

- The journal carries `stratum` and `superseded_by` per selected result (B1/A2 vocabulary);
  inspect exposes the tier map (W2_07). No silent adjudication: unresolved holds contradictions
  (A3).
- Cold records: cold rotation removes a relation's cold state from candidacy; cold reads
  disclose (row 02).

### 1.5 Statutory parameters named (Tier-2)

Arbitration mode (default `PenaltyMultiplier`; `structural` = the frozen experimental mode — S6:
this spec does not change the default) · candidacy parameters (NUCLEUS §3, A3-owned).

### 1.6 Non-goals

No new strata values · no env-gated enforcement · no score nudges for freshness · no
adjudication of contradictions · no change to the arbitration claim (WEAK).

---

## 2. Selection history

**Ancestor (Gen1 v26):** `temporal_kg.py` derived `is_current = valid_to is None and
superseded_by is None` — a **stored** currentness field in a fact table (A3 owns that history).

**Gen2:** `ValidityState` in memory metadata; a **dream-only** `validity_sweep` derives
`superseded` from edges under `WM_VALIDITY_SWEEP=1` (exact match); request-time enforcement off
unless `WM_VALIDITY_ENFORCE=1` (recall.rs:1003). No first-class `supersedes` on the serving path
(divergence W2-6/W1-3).

**Gen3:** R + structural strata earned cross-ecology (N2): ordering flip under `WM_GEN3_SWEEP=0`
(C2); TBII state resolution 54/60 adjudicated vs control 34/60; P2D cell 32/40 (claim WEAK).

**Evidence levels:** v26 field SOURCE-IMPLEMENTED; Gen2 knobs SOURCE-IMPLEMENTED (defaults off —
UNVERIFIED runtime); Gen3 derivation SOURCE-IMPLEMENTED + RUNTIME-OBSERVED (canaries) + MEASURED
(corpora).

---

## 3. Adversarial cases

1. **No-knob test** — with the environment cleared (no `WM_VALIDITY_*`-class variables), strata
   still derive and enforce at request time; a knob that flips strata semantics fails.
2. **Uniform historical mode** — `include_historical: true` yields all-stratum-1 and full
   history; asserted, not treated as absence.
3. **F4 phantom test** — duplicate relations on one endpoint pair: one effective state; the
   record appears in exactly one stratum; deduped metrics.
4. **Direction test** — src is stratum 0, dst is stratum 2; a direction flip changes who is
   current.
5. **Mode naming** — artifacts quoting strata name the arbitration mode; a `PenaltyMultiplier`
   run is not presented as strata evidence.
6. **No freshness nudges** — the only supersession effect on ordering is strata + the statutory
   candidacy penalty; no ±freshness term reappears in the retrieval path (B1 case 4).

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Sweep (`WM_GEN3_SWEEP=0`) | relations + strata ordering (C2: `[1 stratum 0, 0 stratum 2]`) | flat strata 1 (`[0,1]`), zero proposals | RE-ENTERS |
| Structural vs PenaltyMultiplier | stratum-first ordering | key ordering | EFFECTFUL (ordering delta measured) |
| include_historical | all stratum 1, history visible | current-preferred order | EFFECTFUL |

No inert passengers: a strata implementation whose ordering never differs from the default mode
fails the teeth check.

---

## 5. Acceptance + owner

Wrapper-side:

1. **C2 template** — ordering flip on/off.
2. **No-knob derivation** — environment-cleared run reproduces strata.
3. **F4 guard** — phantom-state test + deduped metrics.
4. **Journal fields** — `stratum`/`superseded_by` present per result; ordering reconstructible.
5. **Mode disclosure** — every strata claim names the arbitration mode.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_03_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
