# RECEIPT — Pre-registration freeze (GEN3-P2-CONTRADICTION-001)

**Status: FROZEN · 2026-09-16.** Recorded with the commit containing this receipt (code state:
`b4513f6` + the seam/instrumentation changes in the same commit). From this point the frozen set
below is **read-only**; any behavioral change re-baselines the experiment with a new receipt.

---

## 1. Frozen artifacts (sha256 at freeze)

| Artifact | sha256 |
|---|---|
| `experiments/contradiction/PRE_REGISTRATION.md` (incl. §4.1 notes) | `f56de3f400e069fe4f5c0d0c45342dbec7441d671d0c0471df7bda9b12ac79f7` |
| `docs/PHASE1_CONTRACTS.md` | `53fa01d22ecae99f9af449799a8c7dcefd282497a9c8213bf3ed926dbab286af` |
| `docs/PHASE1_EXPERIMENT_INTERFACE.md` | `9be4f1d887e83778d1cf72ca69080c0fbf70a12510d3c8bf026212d4fee67c3d` |
| `docs/PHASE2_RUN_JOURNAL.md` (incl. refusal/violation seam) | `89ce487f97a5e3806f570e37de8e9eb798d3d29f93982f8a56e9c47e61b9e972` |
| `docs/PHASE1_SCORE_POLICY.md` (D2 accepted) | `3d3b1223acf605215e9d215c6953dac6d82c21982e68c9b29d4cd979e1dbc1f6` |

Runner/harness/control pins remain as in `PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md`
(control binary `47b5c28e…`, corpus and harness hashes unchanged — re-verified 2026-09-16 in
`PHASE0_VERIFICATION` and again at this freeze via the smoke manifests).

## 2. Frozen configuration

| Item | Value |
|---|---|
| Candidate binary | `wm-gen3` release build of the freeze commit; per-run sha256 recorded in the run manifest. Freeze-time build: `aad716b506e9dc8715d68a427f359e2ca9587540db8a486af80d78d037c08ab7` |
| Control | frozen Gen2 v9.1.7 musl `wm-linux-x86_64-musl`, sha256 `47b5c28e3228a0d5f3b8e733538018d2d40b70bd0beb8f134081335b679621ad` |
| Seeds | `1 2 3 4 5` |
| Categories | scored: **T8 (primary)**, **T1+T6 (secondary)**; guardrails reported but not judged: **T2, T9**; excluded from the scored invocation: T3 T4 T5 T7 T10 |
| Flags | `--limit 10 --candidate-limit 100 --min-score 0 --min-coverage 0`; no `--bm25-only` (flag does not switch routes; documented) |
| Policy | rare divisor 20, floor 2; supersede penalty 0.60; recency weight 0.05; pair budget 200,000; relevance floor 0.01 |
| Rule | `candidacy.v1.shared-rare+value-diff+temporal` |
| Score policy | D2 Option B — idf-weighted query support; property-tested; frozen |
| Ablations | A1 `WM_GEN3_SWEEP=0`; A2 trust-fix, A3 hop-budget 0, A4 symmetric historical, A6 promotion-off — via declared switches only, no code edits |
| Journal | `WM_GEN3_JOURNAL` + `WM_GEN3_JOURNAL_HASH_OUT`; schema per `docs/PHASE2_RUN_JOURNAL.md` |

## 3. Pre-committed interpretation

- T8: a loss is recorded as **product-capability loss (no bridging) + architectural diagnosis
  (missing general semantic bridge)** — not evidence about contradiction machinery; no bridging
  may be added before the A/B concludes (PRE_REG §4.1).
- H1/H2 thresholds, outcome branches, and kill criteria unchanged from the pre-registration.
- H3 direction-aware proposal precision/recall; H6 counts `closure.violation` only.

## 4. Non-evidence smoke (may not be cited as results)

Artifacts + findings: `experiments/contradiction/PREFLIGHT_FINDINGS_2026-09-16.md` and
`experiments/contradiction/smoke/` (control and Gen3, A1-on and A1-off, seed 1).

## 5. Rules after freeze

1. No changes to candidate behavior, constants, contracts, or the journal semantics.
2. The A/B (5 seeds, both arms, pinned invocation) may run; results land with run manifests and
   journals under `experiments/contradiction/`.
3. Any code change — including performance work — invalidates the freeze and requires a new
   pre-registration receipt before scored runs.
