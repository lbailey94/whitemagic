# Research notes — selection among imperfect signals (multi-view problem)

**Status: research note · 2026-09-16 · not a claim, not a plan of record.** Captures the pattern
that five falsifications have converged on. Nothing here is implemented or registered.

---

## 1. The pattern

Across five experiments (`claim-0000`…`claim-0004`; falsified ×4, WEAK ×1), the primitives
themselves look simple, while **selection among imperfect signals is the hard part**:

| Signal | Useful when | Harmful when |
|---|---|---|
| Semantic projection (bge-small, τ = 0.694) | relational structure exists (reach +6…+8 top-5, replicated) | alone (behaviorally inert); it can also displace rank 1 (seed 6–10 corpus) |
| Lexical rarity (idf) | distinguishes topics | confuses global rarity with contextual specificity → LEX_TAU class (18/42 failures) |
| Temporal relations (supersedes) | robust ordering benefit (replicated) | insufficient alone; can mark the labeled answer as superseded (label/state conflicts) |
| Contextual dispersion | unblocks 4/6 template-blocked questions | net redistribution — breaks legitimate questions; median margin barely moves |
| Structural arbitration | retains reach, improves ordering (P2D, WEAK) | ceiling-limited confirmation; within-stratum competitions remain unsolved |

## 2. The reframing

The recurring question is not “what is the right score?” but:

> **How does a system preserve several partially trustworthy views of the same evidence without
> prematurely collapsing them into one scalar judgment?**

Observed needs pointing the same way:

- Failures under arbitration are **within-stratum evidence competitions** — multiple plausible
  signals disagree and one scalar key decides prematurely (LEX_TAU, TIE classes).
- The audit protocol showed that one of the signals (benchmark labels) is itself fallible; the
  system sometimes reconstructs chronology *better* than the key.
- Projection agreement is a *third* view whose latent information is present but gated out
  (10/12 measured failures).
- Naive fusion (`max(L,S)`) and governed strata both still collapse evidence into an order
  before the disagreement is represented.

## 3. Candidate directions (recorded, not chosen)

1. **Evidence bundles as first-class** — return ranked *sets with per-view support and
   disagreement flags* rather than a single scalar order (extends the existing evidence-bundle
   machinery from retrieval to selection).
2. **Pareto selection** — keep the front of candidates not dominated across views
   (lexical, semantic, currentness, provenance), let the caller/next stage resolve ties.
3. **Context-dependent arbitration** — stratum precedence (already in place) generalized to
   per-context view precedence, chosen by declared conditions rather than learned weights.
4. **Projection-agreement as an ordering view** — carry the A3 diagnostic into a different
   distribution and test whether the signal reappears before any behavior change.

Constraint that survives from all prior work: **no blended score, no fitted weights**; any
mechanism must be declared, ablatable, and pass genericity checks.

## 4. What is explicitly not happening

- No new mechanism registered now; claim-0003 stays WEAK/unresolved.
- No projections/arbitration changes on the current generator family.
- No reuse of scored seeds (1–5 / 6–10 / 11–15 / 16–20) for confirmation.
- Phase 3 remains blocked.
