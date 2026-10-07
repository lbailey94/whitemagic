# Architecture consolidation matrix (2026-09-16)

**Status: synthesis over every scored run to date; updated after GEN3-GATED-S-003 (adds one
run + one claims-ledger action; id mapping corrected 2026-09-17 after the ledger
reconstruction — see note below).**
Purpose: the smallest architecture justified by everything that survived across ecologies.
Sources: `experiments/semantic_projection/RESULTS{_P2C,_P2D,_P2E}_2026-09-16.md`,
`FAILURE_TAXONOMY.md`, `experiments/testbed_ii/REPORT_A.md` (+ `REPORT_PRE_PILOT.md`),
`experiments/testbed_ii/gated/REPORT_GATED.md`, `experiments/testbed_ii/gated2/REPORT_GATED2.md`,
`experiments/testbed_ii/gated3/REPORT_GATED3.md`, claims ledger (wmv9 store, ids restored
2026-09-17: claim-0000 falsified [Phase 2]; claim-0001 P2B, claim-0002 P2C, claim-0004 P2E
falsified; **claim-0005/0006/0007 = GATED-S-001/002/003 — claim-0007 validated, the count
criterion**; claim-0003 = the arbitration claim, pending/WEAK).

> Note on ids (corrected 2026-09-17 — `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md`): ids
> follow the restored chronological mapping — 0001 P2B · 0002 P2C · 0003 the arbitration
> claim (pending/WEAK) · 0004 P2E · 0005/0006/0007 GEN3-GATED-S-001/002/003. The earlier
> "claim-0003 = GATED-S-003" reading was an artifact of the ledger loss (ungraceful restart,
> 2026-09-17 09:28) and is superseded.

---

## 1. The matrix

Legend: **+** positive / supported · **0** null (indistinguishable from baseline) ·
**−** negative (falsified or degrades) · **CL** ceiling-limited (endpoint unmeasurable, ordering
carried) · **NT** not tested in this combination · **(+)** positive only in interaction.

| Mechanism | M 1–5 | M 6–10 | M 11–15 | M 16–20 | TBII 301–310 | TBII 401–410 | TBII 501–510 | TBII 601–610 | Cross-corpus verdict |
|---|---|---|---|---|---|---|---|---|---|
| **R** supersedes candidacy | + | + | + | + | + | + | NT | NT | **Earned** |
| **S** projection, solo | 0 | 0 | NT | NT | 0 | 0 | NT | NT | **Null as standalone** |
| **S** projection, with R | (+)* | (+)** | (+)** | NT | 0 | 0 | +‡‡ | +‡‡‡ | **Ecology-dependent (demonstrated on designed mismatch)** |
| **Structural arbitration** | NT | NT | + (WEAK) | + (baseline) | CL (non-inferior) | NT | NT | NT | **Conditional** |
| **Dispersion weighting** | NT | NT | NT | − (falsified) | NT | NT | NT | NT | **Rejected** |
| **T8 cross-vocabulary bridge** | − | − | − | − | —† | —† | —† | —† | **Rejected as primitive** |
| **S gated activation** (`relevance_floor` 0.01) | NT | NT | NT | NT | NT | 0 / − / NT‡ | − P1₊, P2 / + P1₀, P3′‡‡ | NT | **Falsified (gate-scoped): zero-support detector** |
| **S gated activation (count < 2)** | NT | NT | NT | NT | NT | NT | NT | + (O₀, O₁) / − (O₊₂)‡‡‡ | **Confirmed (gate-scoped): narrow state-resolution sufficiency signal; ≥2 boundary unresolved** |
| **Audit protocol** (v1.2/v1.3) | + | + | + | + | + (20/20, 40/40) | + (20/20, 40/40) | + (20/20, 40/40) | + (20/20, 60/60) | **Earned** |
| **H4 provenance / H6 closures** | + | + | + | + | + | + | + | + | **Earned (standing)** |

*P2B C11: +6 verified, +12 top-5 vs C00; reach 38/40. **P2C holdout: reach interaction
replicated (+8 top-5) but verified interaction −4 and M2 −27.5 pp — ordering dilutes when
semantic candidates enter. ***P2D B1 (S+R naive): 32/40 verified, 40/40 top-5 vs B0 26/40 —
reach contribution again. †Testbed II T8 = within-vocabulary contradiction detection (10/10
every arm incl. control): a *different probe* than MemoraStrict's cross-vocabulary bridge
(0/15). Marked separately — the original bridge claim is untouched and still fails.
‡GEN3-GATED-S-001 (401–410): ordering safe (P2: g1 36 ≥ g0 34, g1 36 ≥ g2 36, n = 40) and net
verified safe (P4: 53 ≥ 51 adjudicated), but the as-registered cost bar failed (g1 total query
wall = 0.901 × g2, bar ≤ 0.3; the harness pays model reload per query in both cells) and
Regime B was opportunity-limited (|O| = 0: no un-flagged T1c/T6 question where g2 adds R@5
reach). Gate fired 7/80, all T2 absent-topic. S-with-R on this corpus (g2 vs g0) was reach-null
and +2 M2 ordering descriptive (conflated with the sweep pair-gating difference; not a
registered endpoint). Research note: dormant gate verifies 0/20 stale-label T1 vs 3/20
always-on (see §4).

‡‡GEN3-GATED-S-002 (501–510, designed customer-support inbox mismatch ecology): **the
opportunity arrived** — |O| = 20 (O₀ zero-overlap 10 q, O₊ partial-overlap 10 q), both
admissible. O₀ transport: gate fires (lex_support_max = 0.0000), recovers 10/10 (mechanical,
g1 ≡ g2) **PASS**. O₊ discrimination: one distractor token yields lex_support_max 0.173–0.295
(17–30× the 0.01 floor), gate dormant, recovery **0/10 FAIL**. P2 ordering **FAIL** (g1 26 <
g2 34 supersession verified; g0 16 — cost of dormancy, not dilution). P3′ pass-scoped cost
**PASS** (2 712 ms vs 17 055 ms = 0.159 ≤ 0.3; captures 84 % of the controllable pass).
P4 **PASS** (46 ≥ 36 adjudicated). Mechanism (F-G2.1): support is `matched_idf/total_idf`, so
any single matched token lands ≫ 0.01 — the floor can only fire at **zero** lexical support:
a zero-support detector, not an insufficiency detector. S-with-R on this designed-mismatch
ecology shows its largest contribution yet (adjudicated g2 53 vs g0 36; S adds R@5 reach on
20/80 questions where R-only fails) — the conditional-lens tier confirmed in the regime it
was designed for, while the 0.01 activation policy is falsified (claim-0002).

‡‡‡GEN3-GATED-S-003 (601–610, fresh mismatch ecology with deliberate incidence variation):
**claim confirmed (gate-scoped, ledger claim-0007 validated).** The count criterion
(`lexical_candidates < 2`) fires exactly on the 0/1-candidate questions (40/100: zero-overlap,
single-incidence, single-record probes, T2) with zero false fires on lexical/stale/T8.
|O| = 30 split cleanly: O₀ 10 (Recovery₀ 10/10, mechanical), **O₁ 10 (Recovery₁ 10/10 — one
lexical candidate is structurally insufficient for state resolution)**, O₊₂ 10
(**MissedOpportunity₊₂ = 1.000 — every ≥2-candidate opportunity missed; the boundary is
disclosed, not solved**). P2a PASS (g1 M2 49 ≥ g0 30 incl. probes); the single-record probe
fired on all 10 with zero degradation (g0 = g1 = g2 = 10/10); P3 CostEfficiency 0.381 ≤ 0.5;
P4 69 ≥ 50. S-with-R contribution on this corpus: g2 75/100 vs g0 50/100 raw. Reading #4 of
the pre-registered table: a narrow, essentially parameter-free state-resolution sufficiency
signal — **not** a general semantic-insufficiency detector. T2 fires (10) are nonproductive
activation and are accounted separately.

Fixed by design (not ablated): score policy D2 (idf-weighted query support), supersedes rule
v1 (`shared-rare+value-diff+temporal`, divisor 20 / floor 2), τ = 0.694 (battery-derived).
R1 pair gating: **NT / paused** (HANDOFF §4 rule 8).

## 2. Reach vs resolution (the hidden comparison)

| Cell (TBII) | Raw R@5 | Adjudicated verified |
|---|---|---|
| control (Gen2) | **70/80** (slightly higher) | 34/60 (56.7 %) |
| c11 (Gen3) | 67/80 | **54/60 (90.0 %)** |

The control finds the relevant material *more often*; Gen3 reconstructs *which state is
current* far better. Gen3's earned advantage is **state resolution, not recall** — "does not
remember more; resolves temporal state better once evidence is present." Same shape on M 1–5
(Gen2 40/40 T1+T6 vs Gen3 20/40) and on M 16–20 (control excluded by design; D0 34/40
adjudicated-verified). This reframes "who scored higher" as two different behavioral profiles,
not one ranking.

## 3. Failure-taxonomy transfer (Q4 + Phase 2)

| Class | Phase 2 (M 1–15+16–20, 42 failures) | Testbed II (c11, 22 failures) |
|---|---|---|
| LEX_TAU | **18** | **1** (on 40 correct-label Q) |
| LEX | 8 | 0 |
| LABEL | 6 | 16 (all audit-flagged stale-label T1 — expected) |
| TIE | 4 | 1 |
| STRAT / STATE2 / REACH / SEM / MIXED | uniques (2/2/2/1/…) | REACH 3, SEM 1, TIE 1 |

**Reading:** the dominant Phase-2 class was distribution-specific, not substrate-universal.
The taxonomy is a valid instrument; the pathology was largely an ecosystem artifact. This also
re-contextualizes **P2E**: the dispersion diagnosis was real, but promoting its remedy would
have fossilized an ecology-specific quirk (claim-0004 correctly falsified).

The g1 taxonomy on 401–410 reads the same (LABEL 19 audit-flagged, LEX_TAU 4, REACH 1;
`projection_silent` in every case) — consistent with |O| = 0: the gate never fired on any
T1/T6 question because the topic token is present verbatim in the haystack by F1.

## 4. Three-tier verdict

| Tier | Pieces | Evidence |
|---|---|---|
| **Earned (constitutional)** | provenance/closures (H4/H6), audit discipline, **R** (supersession/current-state ordering) | R positive on all 5 corpora; audit 20/20+40/40 on a second corpus family; stale-label suppression is a clean behavioral signature (1/20 vs 8/20) |
| **Conditional (promising)** | **S** (projection) as an optional lens + the **count < 2 activation signal**, structural arbitration | S null solo but contributes reach in interaction; on 501–510 S adds R@5 reach on 20/80 questions where R-only fails; **on 601–610 the count gate is confirmed (Recovery₁ 10/10, probes safe, CostEfficiency 0.381) while the ≥2 boundary stays unresolved**; arbitration best-ever on M 11–15 but headroom-impossible there and ceiling-limited on TBII — the arbitration claim correctly stays WEAK |
| **Rejected as general primitives (so far)** | cross-vocabulary semantic bridging (T8), hard pair gating (R1), stable positive S×R interaction, dispersion weighting, the 0.01 floor as an activation policy (both as cost transport and as recovery trigger) | falsified ledger claims 0000–0002; the arbitration claim stays WEAK; nothing promoted by narrative |

**Research note (not a claim): dormant-gate stale-label dividend.** In GEN3-GATED-S-001 the
gated cell verified 0/20 stale-label T1 vs 3/20 for always-on S: a projection pass that never
fires cannot re-rank a superseded value into the top-5. Mechanistically intuitive; recorded as
a design observation favoring "expensive lenses stay dormant unless needed", not elevated to a
claim (it was not a pre-registered endpoint).

## 5. The layered architecture (earned, not chosen)

The experiments suggest mechanisms do not share one constitutional depth:

```
1. durable records + provenance            (H4/H6 — standing, every run)
2. relations describing changes in state  (R — the one cross-ecology survivor)
3. minimal selection/currentness semantics (structural strata; ordering above reach)
4. optional projections/lenses             (S, and possibly others — only when evidence
                                            demonstrates need; ~60× cost argues for
                                            earned activation)
```

Supersession is fundamental because changing state is intrinsic to persistent memory.
Projection is an optional lens. Arbitration matters only when multiple lenses are active.
Dispersion is an ecological adaptation. This is the original Gen3 intuition
(radical simplification outside, depth inside) now backed by ablation evidence.

**Update after GEN3-GATED-S-001/002.** The activation-policy question was tested twice with
the mechanism frozen. On the work-log ecology (001) the 0.01 floor was behaviorally safe but
cost-falsified as registered and its recovery regime never engaged (|O| = 0). On the
designed-mismatch ecology (002) the opportunity arrived (|O| = 20) and split cleanly:
transport PASS (O₀ 10/10, mechanical), discrimination FAIL (O₊ 0/10, dormant), ordering FAIL
(g1 < g2), pass-scoped cost PASS. The activation question is now **closed for this gate**:
the 0.01 floor cannot in principle fire on nonzero lexical support, so it cannot
operationalize insufficiency. **Update after GEN3-GATED-S-003 (601–610, fresh holdout):** a
*new* primitive was declared and confirmed — the count criterion (`lexical_candidates < 2`),
a state-resolution sufficiency heuristic. Recovery₁ = 10/10 on single-incidence questions,
single-record probes fired with zero degradation, CostEfficiency 0.381, claims-ledger
claim-0007 validated. The harder boundary (≥2 misleading candidates) remains explicitly
unresolved (MissedOpportunity₊₂ = 1.000) — the signal is conservative and narrow, and
anything catching the ≥2 regime is still undeclared. Projection-agreement stays dormant.

## 6. What this does NOT claim

- Claims-ledger actions (restored mapping, 2026-09-17;
  `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md`): claim-0000 falsified (Phase 2);
  claim-0001/0002/0004 falsified (P2B/P2C/P2E); **claim-0005/0006 falsified
  (GATED-S-001/002); claim-0007 validated (the count criterion)**; claim-0003 (the
  historical arbitration claim) remains WEAK/pending. The
  stale-label dividend is a research note, not a claim.
- T8 on Testbed II is **not** evidence for the cross-vocabulary bridge (different probe).
- S is not promoted anywhere; its activation is a design question, not a result.
- No thresholds/weights changed; nothing re-run or re-tuned. (Phase 3 has since closed — entry
  decision and compile pass ratified 2026-09-17 (`PHASE3_ENTRY_DECISION`, `PHASE3_COMPILE_PASS`);
  this matrix's verdicts are unaffected.)

## 7. Smallest architecture justified (open question)

Candidate: provenance + R + structural currentness strata (earned tier) with a *cold* S
path that activates only when lexical reach is insufficient (conditional tier). Whether such a
gated path beats the always-on organism — and how to define "insufficient" without tuning — is
a question for a future registration with its own holdout, not tonight.

**Update (post-GEN3-GATED-S-003).** The cold-S path was implemented and tested three times
with the mechanism frozen. 001 (`bf5c0a0`) confirmed behavioral safety, failed the
as-registered cost bar (harness-bound), no opportunity (|O| = 0). 002 (`9fa5fda`) produced
opportunity (|O| = 20) and the split: transport PASS, discrimination FAIL (a single
distractor token gives support 17–30× the floor), ordering FAIL, pass-scoped cost PASS. 003
(`bb25c1f`) declared the count criterion and confirmed it on fresh seeds (|O| = 30; O₀ 10/10,
**O₁ 10/10**, O₊₂ all missed; probes safe; CostEfficiency 0.381) — **the earned activation
policy is now: fire the semantic lens when fewer than two lexical candidates exist.** The
≥2-candidate insufficiency boundary is the recorded open question (needs a different,
undeclared primitive); projection-agreement remains dormant.