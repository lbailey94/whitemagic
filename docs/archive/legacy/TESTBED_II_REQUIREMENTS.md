# Testbed II — requirements for a different-distribution audited corpus

**Status: requirements draft for operator decision · 2026-09-16 · not a registration.**
Purpose: carry the *surviving frozen mechanisms* (R, S, structural arbitration — unchanged) into
a genuinely different audited testbed, to separate **substrate properties** from **MemoraStrict
ecology**. Claim-0003 stays WEAK; no seeds 21–25 confirmation.

---

## 1. What must differ (the point of the exercise)

| Axis | MemoraStrict (I) | Testbed II must… |
|---|---|---|
| Wording | generator templates ("My favorite X is Y", "I've been really into…") | use different phrasing and question forms; no template mirroring |
| Topic structure | persona preferences, ~4 topics/seed, heavy recurrence of topic words | different subject structure (e.g., project/work logs, procedural state, diary vs dialogue) |
| Temporal patterns | change statements scattered across 20 sessions; chronology vs label conflicts | explicit or different time semantics; label/track conflicts handled by the audit protocol |
| Provenance | one synthetic generator built for Gen2 | independently constructed (separate generator authored fresh, or an external dataset family with adapters) |
| Scale | 5 seeds × 8 T1/T6 | enough questions for headroom-aware endpoints (≥ 4 misses on the control cell where reach is an endpoint) |

## 2. Non-negotiables

1. **Audit protocol mandatory** (v1.2 semantics; new revision only with its own frozen protocol;
   report raw + adjudicated + flag list).
2. **Frozen mechanisms only**: supersedes candidacy (rule v1), projection (bge-small, τ = 0.694),
   structural arbitration, score policy D2 — no changes, no new primitives.
3. **Harness contract unchanged** (stdio JSON-RPC, pinned flags) so the same runner applies.
4. **Headroom-aware reach endpoint**: use `H = (R_exp − R_base)/(N − R_base)` only when the
   baseline has ≥ 4 misses; otherwise classify ceiling-limited and let ordering carry the claim.
5. **A3 carried as diagnostic**: measure ungated cosines for failures; do not wire
   projection-agreement into behavior in this experiment.

## 3. Questions Testbed II answers (run frozen, one batch)

| # | Question | Design |
|---|---|---|
| Q1 | Does supersession still improve conditional ordering? | R-off vs R-on (existing switch semantics; adapt cells to the corpus) |
| Q2 | Does projection become useful only with relational structure? | S-off/R-on vs S-on/R-on vs S-on/R-off |
| Q3 | Does structural arbitration preserve reach and improve rank? | naive-max vs structural cells (B1/B2 analogues) |
| Q4 | Do the lexical pathologies recur? | failure taxonomy applied to Testbed II; compare class prevalence (LEX_TAU, TIE) |

## 4. Options for construction (operator choice)

| Option | Description | Pros | Cons |
|---|---|---|---|
| **(A) Fresh independent generator** | Author a new synthetic corpus generator (different templates, topics, temporal scheme) with its own audit-friendly metadata; freeze before use | Full provenance difference; audit-friendly; controlled size | Authoring effort; risk of accidentally reproducing I's pathologies by design choice |
| **(B) External memory-benchmark family** | Adapt an existing public dataset family with a different origin (adapters for LongMemEval/LoCoMo-style data already existed in Gen1's tree) | Genuinely different authorship/ecology; credibility | Licensing/dependency review; answer keys may need audit; format work |
| **(C) Hybrid** | A small hand-authored audited corpus (few dozen scenarios) + one external subset | Fast to ship; provenance clearly distinct | Small n; may underpower reach endpoints (ordering endpoints still usable) |

Recommendation to the operator: **(A)**, with **(C)** as a fast pre-pilot; avoid spending the
next experiments inside the current generator family.

## 5. Explicitly out of scope here

No implementation of new primitives (including projection-agreement or Pareto selection);
no changes to claims; no reuse of scored seeds; Phase 3 remains blocked.
