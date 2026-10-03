# RECEIPT — B5 recall-side scope view acceptance demonstrated (2026-09-17)

**Status: evidence — acceptance demonstrated; one disclosed criterion finding (F-1, score bound);
row exit not claimed, operator disposition pending.** AI session
`6c634017-b18a-454f-9b06-67baa2355f32` (opencode) executed and attests. Registration
`W1_B5_RECALL_VIEW_REGISTRATION` frozen (`receipts/W1_B5_RECALL_VIEW_REGISTRATION_2026-09-17.md`).
Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_b5_recall_view_2026-09-17/` |
| **SHA256SUMS** | `edf7be535bff612ded8970c0588283cd8c1166a9fd245b71cf4867b6a5623472` |
| Candidate binary | `target/release/wm-gen3` @ `10b48d8` (implementation freeze), sha256 `0c4b1d87…` |
| Reference binary | worktree build of pre-change tip `9b1a61c`, sha256 `ee39c37f…` |
| Drivers | `driver_b5_regression.py` (stage B 0-diff), `driver_b5_campaign.py` (view campaign) |
| Tests | core 48/0/1 + doc 5 (6 new B5 tests); closures PASS; release build clean |

## 2. Acceptance (registration §3)

| # | Item | Result |
|---|---|---|
| 1 | Fresh 0-diff regression (the gate) | **ordering/metrics 0 diffs** (160 queries, C00+C01, ordered (id,rank), candidate_count, recall@1/5, mrr, first_match_rank exact); journal integrity exact; **score bound finding F-1 (§4)** |
| 2 | View correctness | **campaign**: 24 labels (> Gen2 cap 20); scoped recall exact per label; shared-token pair no bleed; label-less/malformed-provenance records selectable by no view |
| 3 | Filter-not-scorer | **campaign**: unscoped order restricted to `multi` == scoped order |
| 4 | Cross-scope crowd-out | **campaign**: `candidate_limit=1`, 3 higher-support out-of-scope records → in-view record still returned (filter-before-selection demonstrated, not just intended) |
| 5 | Unknown/empty label | **campaign + journal**: `results []`, `abstained: true`, `reason: insufficient_evidence`, `cause: no_candidates_in_scope`, `scope` present, `scope_considered: 0` |
| 6 | Malformed selector | **campaign**: `scope=""` and `scope="a:b"` → status error (`invalid scope selector…`), **no journal entry** |
| 7 | Explicit-only | **source scan**: no env/config scope path; no `WM_GEN3_SCOPE` in `crates/`; default path journal carries no `scope` field (regression check) |
| 8 | Bare bytes | **campaign**: `data.mdb` sha256 unchanged across scoped reads (ingest-phase hash vs post-campaign hash); store file set `{data.mdb, lock.mdb}` |

## 3. Adversarial cases (registration §5)

1 unbounded scope names ✓ (24 labels, no per-name resources) · 2 isolation asymmetry — N/A
(no classes; disclosed) · 3 explicit-selection creep ✓ (scan + default-path journal) ·
4 capability typos — N/A · 5 tier degradation — N/A · 6 cap bypass — closed by absence ·
7 membership-vs-authz — declared · 8 fail-open-on-error — N/A; empty view disclosed, not widened ·
9 narrative guard — cited · 10 malformed provenance ✓ (label-less record visible unscoped only) ·
11 malformed selector ✓ (typed refusal, no journal).

## 4. Finding F-1 — score-stability bound (disclosed; disposition pending)

- Registered criterion: scores ≤ 1 f32 ULP (registration §3.1; protocol §9).
- Observed: candidate vs reference scores — 531/650 **exact**, 103 at 1 ULP, **16 at 2 ULP**;
  ordering and all metrics exact; the strict driver assertion fired at max 2 > 1.
- Attribution (measured, `noise_baseline.results.txt`): same-binary reruns of either binary
  already differ by 1 ULP (ref 18 entries; cand 34 entries; ordering identical) — f32
  summation-order nondeterminism in the scorer — and cross-build FP lowering adds the second ULP
  in 16/650 entries. Not a semantic change; no ordering or metric effect.
- Options for the operator (recorded, not decided here): (a) accept with this receipt + an errata
  correcting the score-wording to a measured noise band (baselines pinned per comparison);
  (b) require a determinism registration (e.g., ordered summation for `total_idf`) before exit.
  The row exit is **not** claimed; the registration's exit block stays open until disposition.

## 5. Disclosures

- No code change was required by the slice; no hidden coupling added (scope is a population
  filter only; no env switch, no scoring change on the default path).
- Label views remain **views, not boundaries**: no isolation, registry, or authorization
  semantics (B5 §1 clauses restated by the campaign).
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK; ledger unchanged.

## 6. Attestation

AI session `6c634017` implemented the registered feature (`10b48d8`), built the source-frozen
reference, ran the fresh 0-diff regression and the fresh campaign, measured the noise baselines,
and recorded all artifacts and the finding above. Ratification of the exit (or the F-1
disposition) is an operator act; this receipt records the evidence.
