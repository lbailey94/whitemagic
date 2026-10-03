# Gate 9A ratification receipt — 2026-09-22

Status: records the operator's ratification of the closure verdict and the independent reviewer's
sign-off after re-execution. Gate 9A is **closed**. No frozen text was edited; no push was performed.

## 1. Operator ratification (statement)

> I (Lucas, Project Operator) hereby accept and ratify
> `receipts/GATE_9A_CLOSURE_VERDICT_2026-09-22.md`. Gate 9A is officially **CLOSED AND RATIFIED**.
> You are authorized to commit the integrated candidate tree to `main`. Workstreams for Gate 9B
> (Packaging & CLI Ergonomics under PEB-15 §8.2) and Gate 9C (Cognitive Field Recovery & Model
> Requalification) are officially authorized to proceed.

## 2. Independent reviewer sign-off (re-execution on the frozen candidate)

The independent verification lead re-executed the complete battery in-environment on 2026-09-22:

| Suite | Result |
|---|---|
| Workspace test suite (reference-models, ratified skips) | **232 passed, 0 failed**, 1 ignored, 5 filtered |
| Storage suite (`store::tests`) | **13 passed, 0 failed** |
| Static closure scans (3 rules) | **3 of 3 passed** |
| Process-boundary harness scenarios | **9 of 9 passed** |
| Release harness build / default core check | Passed |
| `git diff --check` | Clean |

Both manifests re-verified: implementation `source-manifest.sha256` 37/37
(digest `55c07f661f7f4236b5380307f13865e265fa2f439a6a2a30034546854935571d`), evidence
`evidence-manifest.sha256` (regenerated after this receipt; see the file for its digest).
Evidence class upgraded to **independently re-executed on the frozen candidate**.

## 3. Records and supersessions

- Closure instrument: `receipts/GATE_9A_CLOSURE_VERDICT_2026-09-22.md` (status now ratified/closed).
- Independent review: `docs/GATE_9A_INDEPENDENT_EVIDENCE_REVIEW.md` (source/hash audit +
  re-executed battery).
- Historical claims superseded per errata #67 (`docs/PHASE4_ERRATA.md`): the stale
  "RATIFIED/FROZEN/COMPLETE" preregistration lines, the Sep 20 "167/167" claim, the Sep 19
  "152 tests" claim, and interim Slice 1 counts. The frozen preregistration text was **not** edited.
- Closure transition registered as errata #68; its "pending operator ratification" status is
  resolved by this receipt (the register itself was not edited after certification).
- Scope disclosures remain in force: PEB-15 §8.2 core-vs-packaging split; profile v1 is
  qualification, not capacity; D2(b) volatile usage; D4 disabled no-op; model/evolution and
  cache-GC deferred to 9C; physical power-loss to 9D.

## 4. Transition

Commit of the integrated candidate to `main` is authorized by the operator and was performed by the
coordinator lane (opencode) on 2026-09-22. Gates 9B and 9C are open for planning; no push was
performed at entry time.
