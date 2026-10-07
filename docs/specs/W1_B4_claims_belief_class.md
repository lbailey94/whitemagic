# Wave-1 spec B4 — Claims / belief class

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `309e111` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Claims / belief class (wave plan §2; `CLEANLY → compile · E18`).
**Wire:** belief-class records + resolution events; **calibration = statutory statistic**.
**Nucleus touch points:** Part 1 invariant 9 (evidence/belief/speculation distinct); N1
(provenance), N4 (journal), N5 (audit discipline); Part 3 (statutory statistics, WEAK stays WEAK).
**Caution carried:** v26 seed sync was **destructive + degenerate** — the spec must exclude both
classes; **calibration names one universe** (four disjoint "calibration" universes exist —
wave-2 §6 lesson; this row's universe is **the claims ledger resolved set**, never the self-model
metric, the v26 runtime ledger, or citta CRPS; errata G-25: the 0.078 figure belongs to Gen2's
live-store ledger).
**Do not re-raise:** errata #25 (Brier identity); claims provenance nits (errata A#5/claims
items) are fixed or recorded.

---

## 1. Frozen behavioral spec

### 1.1 Belief-class records (inputs)

A claim record requires: `statement` · `domain` · `source_date` · `predicted_outcome` ·
`confidence ∈ [0,1]` (**fail-closed bounds**; out-of-range is a structured error, the 9.1.7 #4
class) · `falsification_criteria`. Absent any required field the add is refused, not defaulted
(Gen2's empty-`source_ref` legality is the excluded class). Records are dated, falsifiable,
provenance-carrying; belief ≠ evidence (invariant 9). (SOURCE-IMPLEMENTED; W1 source map §6)

### 1.2 Resolution events (the completeness contract)

`resolve` requires `validated` (bool) + `event` + `event_date`. **Resolution-record completeness:
every resolved claim carries its validation event + date and an actor/provenance pointer; no
resolution without an evidence pointer.** Followed-guidance and outcome are **separable** — no
`action_taken`-in-the-outcome-row encoding (v26 oracle confound excluded). Resolutions are
durable at write time (write-through class; §1.4). Journaled as resolution events (N4).

### 1.3 Calibration — one universe, statutory

- Runs over the **resolved set only**: Brier, signed calibration gap, Wilson 95 interval, and
  empirical-Bayes recalibration (`w = n/(n + 20)`); **raw confidences are never edited** —
  calibrated values are reported alongside (W1 source map §6; live: 2026-08-12 record).
- **Expired handling is pinned once** for this universe (v26 showed the asymmetry: summary
  excludes expired, TZPF scores it 0 — one of the two, named in the receipt, consistently).
- **No post-hoc inputs:** `behavioral_confidence`-style ex-post re-estimates do not enter the
  ledger or its calibration; ex-ante vs ex-post is declared.
- Calibration is a **statutory statistic** (Tier-2): method changes are statute changes, not
  tuning.

### 1.4 Durability + hygiene

- **Write-through:** claims add/resolve are durable at write time — an ungraceful kill loses
  nothing (the WMv9 `16198ea` class generalized; the JSON-store flush-on-graceful-shutdown
  failure mode is excluded).
- **No destructive sync:** curation/seeding may add or update curated rows but **never deletes
  independently recorded rows** (v26 `source_ref`-keyed delete excluded).
- **Declared battery only:** external-validation sourcing (if it ever re-enters) must carry dated
  claim + externally sourced validation event; free-text `validation_ref` strings and
  name-regex scoring (NRS class) are **not evidence** and do not enter metrics.
- **Points accounting:** if any lead-time points total is reported it must be re-derivable
  (`floor(lead_weeks)`-style); non-reproducible hand values are not a claim (v26: 6/52 divergent,
  header drift).
- Reads are read-only (snapshot class; no mutation while listing).

### 1.5 Statutory parameters named (Tier-2)

Required-field set · calibration method + shrinkage weight (w = n/(n+20)) · expired handling ·
resolution completeness requirement. No swept thresholds.

### 1.6 Non-goals

No destructive sync · no ex-post inputs · no name-regex/"external convergence" metrics · no
promotion of any WEAK claim (claim-0003 stays WEAK) · no Brier identity conflation across the
four universes · no new primitive (claims remain a compile target + live Gen2 surface).

---

## 2. Selection history

**Ancestor (Gen1 v26):** `core/whitemagic/forecasting/` — YAML seed as source of truth + SQLite
mirror + CLI + TZPF scorecard + site export. Destructive seed sync deleted rows absent from the
YAML (oracle/time-estimate rows erasable); all-validated seed → degenerate Brier (mean confidence
0.668, BS 0.1149, gap −0.332 recomputed; shipped site snapshot BS 0.0958); points not
reproducible (6/52 rows; stored sum 1,474.3 vs header 1,468); external validation = human
curation with free-text refs; NRS regexed org names inside a string; `expired` had no method
(YAML-only); Brier/CRPS stacks did exist (not just points).

**Runtime cross-check (W0):** v26 runtime ledger 0.2563 overall / 0.0731 `time_estimate`
(127 resolved); citta `calibration.jsonl` = CRPS only; **0.078 = Gen2 live-store ledger**
(errata #25 — do not conflate).

**Selection fate:** function kept in Gen2 as the live claims ledger (Brier + Wilson + EB
shrinkage; raw never edited; write-through committed `16198ea`); Gen3 reading = belief-class
records + resolution events + calibration as statutory statistic; Gen2's `claims.*` stays the
live product surface until earned (E18). External-validation sourcing remains a listed re-entry
candidate with a fair trial (decomposition §4 list), not a plan.

**Evidence levels:** v26 organs SOURCE-IMPLEMENTED; degenerate score recomputed MEASURED-from-
data; Gen2 ledger live (SOURCE-IMPLEMENTED + RUNTIME-OBSERVED); write-through commit tested
(866 tests green, deploy deferred); Gen3 target NAMED.

---

## 3. Adversarial cases

1. **Destructive sync** — seed/curation over a ledger containing independently recorded rows:
   deletion count must be **zero**.
2. **Degenerate calibration** — all-validated and all-falsified sets must disclose their
   degeneracy (no negative/positive outcome class in the denominator) rather than report a
   confident Brier; expired handling pinned and consistent across summary and any secondary view.
3. **Free-text validation** — an uncited `validation_ref` or org-name-rich sentence does not
   count as an external event; NRS-class scoring is absent by construction.
4. **Points not reproducible** — any reported total re-derives from dates; non-floor values fail
   the check.
5. **Oracle confound** — followed-guidance separable from outcome; the resolution row cannot
   encode the guidance decision into the outcome.
6. **Confidence bounds (#4 class)** — −ε/0/.5/1/1+ε boundary: out-of-range refuses fail-closed;
   the update path goes through the same parser.
7. **Durability** — kill -9 after add/resolve; restart: both present (write-through).
8. **Read-only discipline (9.1.8)** — status/list/calibration never mutate the ledger.
9. **Universe naming** — calibration reports name their set; a cross-universe quote (self-model
   metric / v26 runtime / citta CRPS / Gen2 ledger) fails the acceptance.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Resolution events | completeness computable (100 %) | uncomputable | EXECUTED → EFFECTFUL |
| Expired-inclusion rule | gap shift measured (−/+) against excluded set | baseline | EFFECTFUL |
| Destructive-sync path | independent rows survive (count 0 deleted) | v26 class removes them | EFFECTFUL |
| Post-hoc inputs | calibration unchanged with them nulled | metrics inflate | EXECUTED (negative control) |

Rungs: resolution events (EXECUTED), durability across kill (PERSISTENT), calibration reflected
in reported statistics (EFFECTFUL). EXTERNAL not claimed.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Resolution completeness** — every resolved claim has event + date + provenance; generated
   rate = 100 %.
2. **Calibration reproducible** — recompute Brier/gap/Wilson/EB from raw; matches reported;
   raw bytes unchanged after calibration.
3. **No destructive sync fixture** — independent rows survive a seed run.
4. **Expiry universe** — one pinned handling, consistent across views.
5. **Durability** — ungraceful kill loses nothing.
6. **Universe labels** — every calibration output names the claims-ledger resolved set.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_B4_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
