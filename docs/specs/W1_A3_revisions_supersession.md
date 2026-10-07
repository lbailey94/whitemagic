# Wave-1 spec A3 — Revisions/supersession

**Status: FROZEN rev 1 (2026-09-17, sha256 `3adedac0…`) · rev 2 amendment drafted 2026-09-17
(case 1 disposition — operator-ratified; pending receipt).** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `b7565ee` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: Lucas Bailey (operator)** — assigned at ratification. Rev 2 is additive to
rev 1 and takes effect at `receipts/W1_SPEC_A3_AMEND_2026-09-17.md`. Docs-only: no code, no gates,
no verdicts, no thresholds.

**Row:** Revisions/supersession (wave plan §2 row: `CLEANLY → compile · E2, E3 †`).
**Wire (Gen3 expression):** `supersedes` relation + structural strata + provenance.
**Nucleus touch points:** N2 (supersedes relation + currentness ordering; R + structural strata —
the one cross-ecology survivor), N1/N3/N4 (provenance, explanations, journal-as-evidence); Part 3
statutes (candidacy rule v1 + parameters; arbitration mode); S3 (the arbitration claim stays
WEAK — nothing here promotes it).
**Caution carried (wave plan):** Gen2 has **no first-class `supersedes` relation** —
currentness there is hash-chain revisions + episodic change-marker anchoring. Gen2 is behavior,
not relation; Gen3's R is the relation-form. **Do not claim Gen2 agreement** (W1 §3).
**Carry from the nucleus:** F4 — duplicate proposals within one sweep (`existing` snapshotted
pre-loop, `crates/wm-gen3-core/src/ops.rs:751`); relation counts inflated, direction/ordering
unaffected; flagged for a future registration, **not a blocker**, and no acceptance metric may
silently paper over it (nucleus §5).

---

## 1. Frozen behavioral spec

Observable behavior, inputs/outputs, journal events, statutory parameters named (Tier-2). Nothing
benchmark-derived.

### 1.1 The relation contract

- **Mechanism:** R — a rule-derived `supersedes` relation over durable records, plus structural
  currentness strata. Candidacy rule v1 = `candidacy.v1.shared-rare+value-diff+temporal`: a shared
  rare token + a value difference + temporal precedence yields a `supersedes` edge. (N2;
  SOURCE-IMPLEMENTED) **Rev 2 note:** `value-diff` is implemented as *distinctive-rare-token
  presence* — a lexical reading (measured: predicate-sense collisions link; §3 case 1).
- **Statutory parameters (Tier-2, named — none swept):** rare divisor 20 · floor 2 · pair budget
  200,000 · supersede penalty 0.60 · recency weight 0.05 (NUCLEUS §3; PREREG §2). The sweep is
  budget-fail-closed; `WM_GEN3_SWEEP` default on (`0` = the A1 ablation switch).
- **Sweep event:** `think` emits `think.sweep` + `relation.proposed` (canary C6 verb→event
  inventory). Proposals are promotions/demotions of directed candidate edges; nothing is
  adjudicated silently. (RUNTIME-OBSERVED)
- **No extraction stage, no score nudges.** Unlike v26's `extract_and_assert` pipeline, R derives
  relations from what was remembered; retrieval scores are never adjusted by fact freshness (the
  v26 FAMA +0.15 / −0.20 class is not inherited — see §2).

### 1.2 The ordering contract (currentness)

- **Structural strata 0/1/2 = current / unresolved / superseded**; within-stratum order = lexical →
  semantic → recency → id (`ops.rs:642-648`, `Arbitration::Structural`). (SOURCE-IMPLEMENTED;
  MEASURED behavior: canary C2, TBII.)
- **Current-value questions prefer the newest value-bearing statement**; non-state queries keep
  score order. Recall applies the *current* value in the direction read: hits carry
  `superseded_by`, and applied relations are recorded (`ops.rs:661-676`). (RUNTIME-OBSERVED)
- **Round-trip:** relation kinds/endpoints survive process restart byte-identically (canary C5:
  `kind: Supersedes, src: 1, dst: 0, state: Candidate`; recall still applies `superseded_by: 4`).
  (RUNTIME-OBSERVED)
- **Arbitration mode is statutory:** the frozen experimental mode is `structural` (set explicitly
  in every scored run); the Tier-2 default remains `PenaltyMultiplier` (NUCLEUS switch table, S6).
  This spec does not change the default.
- **History persists:** supersession orders, never deletes. `include_historical: true` restores
  superseded rows; authorized erasure (Part 1 invariant 2) is the operator's separate right, not
  a sweep behavior.
- **Contradictions are preserved, never adjudicated:** the unresolved stratum (1) holds
  contradictions; no silent resolution. (Gen2's bundle `conflicts{count,pairs}` is the link-side
  disclosure of the same discipline.)

### 1.3 Direction and proposal scoring

- Supersession is **directed** (src superseded by dst). Direction-aware proposal scoring (H3) is
  part of acceptance: a direction flip in a fixture must register in the scoring metric, or
  direction awareness is inert.

### 1.4 Boundary — what is Gen2's and what is Gen3's (divergence #3 resolution)

- **Gen2 (capability source, link side):** hash-chain revision history
  `{seq, timestamp, old_hash, new_hash, actor_*}` with `verify_chain` (seq + hash linkage + head
  match) and `memory.revisions` list|verify (`wm-memory/src/revision.rs:1-18,26-47,73-107`;
  `store.rs:1575,1610`; `memory_ops.rs:684-724`), plus episodic current-cue reordering and
  session-turn `superseded-by:` tags. This is the **history/verification side**.
- **Gen3 (this spec, compile side):** the `supersedes` **relation** + structural strata + the
  currentness ordering described above. Gen2 has no first-class supersedes relation; **no Gen2
  agreement is claimed.**
- **Session-turn interaction:** `session.record`'s `supersedes` tag mechanism belongs to the
  sessions row (batch B). Where both could apply to the same records, a disclosed precedence rule
  is required before either side double-applies silently.

### 1.5 Statutory parameters named (Tier-2, none swept)

Candidacy rule v1 + parameters (§1.1) · arbitration mode (§1.2) · `WM_GEN3_SWEEP` (ablation
switch, default on) · import tier fixed `persistent` (horizons).

### 1.6 Journal events owned by this spec

`think.sweep` · `relation.proposed` · `selection.decision` (strata fields: `stratum`,
`superseded_by`) · `provenance.chain` (per hit). Acceptance metrics over proposals must dedupe
identical endpoints (F4 guard, §3 case 5).

### 1.7 Non-goals

No extraction stage · no fact table · no score nudges · no `changes_since`-style API surface
reproduction (the capability compiled ≠ the historical API reproduced — decomposition row note †)
· no promotion of the arbitration claim (S3) · no destructive remediation of superseded records.

---

## 2. Selection history

### 2.1 Ancestor (Gen1 v26)

`core/memory/temporal_kg.py` — the Temporal Knowledge Graph ("Gap C"), with the fact vocabulary in
`unified_types.py` (`LinkType`: `related · extends · contradicts · supersedes · temporal · causal ·
cascade`). Facts stored as `(subject, predicate, object, valid_from, valid_to, superseded_by)` in
a dedicated SQLite table (`temporal_kg.db`); `is_current = valid_to is None and superseded_by is
None`.

### 2.2 Observed behavior

- `assert_fact(..., supersede=True)` marks existing current facts for the same key superseded;
  queries `get_current_facts` / `get_fact_history` / `changes_since(date)`.
- **Search coupling (FAMA):** fresh facts get a temporal boost +0.15, superseded facts a penalty
  −0.20; `get_superseded_memory_ids()` lets retrieval exclude them.
- Facts do not enter themselves: population requires an extraction step (`extract_and_assert`).
- Evidence: SOURCE-IMPLEMENTED (file/symbol); runtime reach UNVERIFIED (no Gen1 DB on this host).

### 2.3 Selection fate

- v26 needed (a) an extraction stage, (b) a separate fact DB, (c) an inline score adjustment.
  None of the three is inherited.
- Gen2 kept revision chains and currentness as *behavior* (hash-chain revisions; episodic
  current-cue reordering; `superseded-by:` tags) with no extraction stage.
- Gen3's R earned currentness as a **derived relation** (`shared-rare + value-diff + temporal` →
  `supersedes` edges + structural strata) with **no extraction stage and no score nudges**. The
  homology is "prefer the current value when state changed"; the organs differ completely.

### 2.4 Evidence-level register (per statement, protocol §3)

| Statement | Level |
|---|---|
| v26 `temporal_kg.py` organs + FAMA constants | SOURCE-IMPLEMENTED; runtime UNVERIFIED |
| Gen2 revision chain / verify / episodic currentness | SOURCE-IMPLEMENTED + RUNTIME-OBSERVED (status: live) |
| R positive on all five corpora (cross-ecology survivor) | MEASURED (consolidation §4/§5) |
| TBII state resolution 54/60 adjudicated vs control 34/60 | MEASURED (c11; consolidation §2) |
| P2D ordering cell 32/40, M2 85 % | MEASURED — the P2D *claim* stays WEAK (S3) |
| A1/A4 sweep ablation ordering flip; C2/C5 canaries | RUNTIME-OBSERVED/MEASURED (canary bundle) |
| Gen2 first-class supersedes relation | **absent** (divergence #3; do not claim agreement) |

---

## 3. Adversarial cases

Each case must exist as a runnable acceptance assertion before the row exits; no inert passengers.

**From the findings (row 3 battery):**

1. **Predicate-sense collision (rev 2 — declared property, measured).** The frozen candidacy rule
   v1 is **lexical**: a shared rare token + distinctive rare tokens + temporal precedence proposes
   a directed edge regardless of predicate sense. Measured fixture (2026-09-17,
   `IMPL_A3_ACCEPTANCE_2026-09-17`): `"I prefer Rust over Python for systems work"` /
   `"I wrote Rust last year for a course"` → **1 proposal**. This class is **declared and
   disclosed**, not excluded: the edge is a supersedes relation, recall applies the statutory
   penalty + `superseded_by` while still returning both records, and audit flags stay visible.
   A stricter **value-replacement rule (rule v2)** is registered as a **gated candidate** in
   `archive/research/PHASE4_ERRATA.md` — re-entry requires its own registration + a full corpus re-baseline; no
   execution is authorized by this spec.
2. **Temporal absence** — facts with no temporal anchor: R must not propose on missing time;
   temporal-absence is tested explicitly (v26 FAMA degraded to no signal here).
3. **Labeled answer is the superseded value (LABEL/state-conflict class)** — keep testbed-audit
   flags visible; **no** −0.20-style penalty or tuning against the labels.
4. **Window queries** — `changes_since`-style windows must be answerable from the journal
   (journal-as-evidence, N4) without a fact table.
5. **F4 carry (nucleus §5)** — duplicate proposals within one sweep inflate relation counts on
   identical endpoints. Acceptance metrics must dedupe endpoints; the underlying fix is a future
   registration — do not fix by narrative, and do not let inflated counts become a metric.

**From the 9.1.7 audit fix list (Tier 1), as applicable:**

6. **Atomic vs partial (#6)** — a sweep that partially applies relations must disclose
   all-or-explicit-partial; a truncated sweep is never "success".
7. **Drift disclosure (#5)** — a revision-verify reading a store whose index drifted must yield
   coherent verification or explicit degraded state.

**From the 9.1.8 additions (delta §3.2), as applicable:**

8. **Read-only discipline** — revision/chain verification never locks, temps, or mutates what it
   verifies (snapshot-read class); a live writer must not block verification, and verification must
   not prune expiry it merely observes.
9. **Starvation-vs-refusal distinction** — a sweep refused under starvation is typed (refusal),
   not reported as "no proposals found"; zero-proposals and refused-sweep are different outcomes.

**Not applicable here (declared, not padded):** strict-mode refusal (coordination row), signed-only
beacon ingest (mesh), no-subprocess discovery (coordination, 9.1.9 F3).

---

## 4. Ablation

Disabling the mechanism must change a measured outcome; the journal is the instrument (rungs 4–8,
protocol §1).

**Mechanism ablated: R (the sweep).** `WM_GEN3_SWEEP=0` on a fresh store.

| Measure | Sweep on | Sweep off | Rung evidenced |
|---|---|---|---|
| Ordering on a state-change fixture | current first, superseded ordered after (C2: `[1 stratum 0, 0 stratum 2 superseded_by 4]`) | both stratum 1 (`[0,1]`), no current-preferred order | EXECUTED → EFFECTFUL |
| `relation.proposed` count | > 0 | 0 | EXECUTED |
| `superseded_by` applied on recall | applied | absent | EFFECTFUL |
| Relation round-trip across processes | byte-identical (C5) | n/a | PERSISTENT |

**Mechanism ablated: strata (structural arbitration).** Switch to `PenaltyMultiplier` on the same
fixture → ordering delta on state-resolution corpora; `selection.decision` strata fields are the
instrument. If ordering is unchanged, the strata mechanism is inert and the row fails its teeth
check.

**Direction check:** direction-flipped fixture must register in H3 proposal scoring; unchanged =
inert.

Not claimed: EXTERNAL — this row requires no outside-system consequence; and no ordering claim is
made beyond what the frozen corpora measured (WEAK stays WEAK).

---

## 5. Acceptance + owner

Wrapper-side evaluation (harness reads journals + scored corpora; counts generated, never
narrated):

1. **Strata ordering ablation (C2 template)** — sweep on/off reproduces the ordering flip on a
   fresh store.
2. **Direction-aware proposal scoring (H3)** — direction flips register.
3. **Round-trip (C5 template)** — relation kinds/endpoints byte-identical across processes; recall
   still applies `superseded_by`.
4. **F4 guard** — proposal/relation metrics dedupe identical endpoints; a raw counter is reported
   alongside with the inflation disclosed, never as a headline.
5. **No score nudges** — the supersede penalty 0.60 is a candidacy-rule constant, not a retrieval
   score adjustment; a retrieval-level delta caused by a freshness nudge is a failure, not a
   gain.
6. **History-lossless** — `include_historical: true` returns superseded rows; nothing vanished.
7. **State-resolution wrapper** — the TBII template (54/60 adjudicated vs control 34/60) remains
   the acceptance corpora shape; raw + adjudicated reported (N5).

**Owner:** Lucas Bailey (operator) — assigned at ratification, rev 1.
**Exit criteria (wave plan §2):** frozen spec + adversarial cases wired + ablation designed and,
where implemented, demonstrated + journal events declared (above) + receipt; **no inert acceptance
test**.

## 5.1 Revision history

- **rev 1** — frozen 2026-09-17, sha256 `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69`;
  receipt `receipts/W1_SPEC_A3_FREEZE_2026-09-17.md`.
- **rev 2** — amendment 2026-09-17: case 1 reworded to the **declared, measured** lexical property
  of rule v1 (operator-ratified disposition: spec amendment + gated rule-v2 note; rule v2 not
  authorized). Additive to rev 1; receipt `receipts/W1_SPEC_A3_AMEND_2026-09-17.md`.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_A3_FREEZE_<date>.md` (spec sha256 + verified pins +
      session attestation)

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; the spec text changes by a new frozen revision with its
own receipt. Nothing in this spec authorizes code by itself; implementation follows the row's
gate.
