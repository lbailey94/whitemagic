# Phase 1 — Score Policy Memo (D2 detail)

**Status: ACCEPTED 2026-09-16** (Option B, idf-weighted query support) · companion to
`PHASE1_CONTRACTS.md` §6 (D2) and `PHASE1_EXPERIMENT_INTERFACE.md` (I8). Sign-off condition met:
the property tests exist in `wm-gen3-core::ops::tests` (`d2_zero_overlap_abstains`,
`d2_full_support_scores_one`, `d2_irrelevant_terms_do_not_improve`, `d2_token_order_irrelevant`,
`d2_deterministic`) and pass. **This policy is now frozen with the pre-registration; do not
touch it again.**

D2 fixed the *requirements*: `score ∈ [0,1]`, irrelevant → `< 0.01`, **no per-query or
per-corpus min/max normalization**, corpus-independent, constant pinned at freeze. This memo
resolves the remaining choice: what exactly maps to `score`.

---

## 1. What the harness actually does with `score`

Only one consumer: **abstention accounting** (`verify_abstention` / `strict_abstention` —
"no results, or top-3 scores < 0.01"). Rank, coverage and T8 set-matching never read `score`.
So `score` is *evidence-of-relevance for abstention*, not necessarily the ranking key. That
frees ranking policy (relations, current-preferred ordering, trust) from having to fit a
[0,1] scale.

## 2. Options

**Option A — saturating BM25.** `s = raw / (raw + K)`, K pinned at freeze.
Pro: `score` is the ranking key itself. Con: `raw` BM25 is unbounded and corpus/parameter
dependent (`k1`, `b`, field length); K is arbitrary, and the `<0.01` floor silently becomes a
raw-score cutoff (`raw < K/99`) with no principled meaning. A single constant is asked to encode
both scale and floor.

**Option B — idf-weighted query support (recommended).**
```
s = Σ idf(t) for t ∈ query_terms ∩ record_terms   /   Σ idf(t) for t ∈ query_terms
```
Zero overlap → `0.0`; full rare-term support → `1.0`; common terms contribute little by
construction. No free constant. Corpus-independent (idf is computed from the store's own
document frequencies). Directly interpretable as "how much of the query's information mass this
record supports" — i.e., exactly what abstention semantics want.

Pro: no constant to pin; floor semantics stable (`<0.01` = essentially no informative support);
zero normalization; ordering untouched (selection policy ranks; journal records both rank and
score, so disagreements are inspectable).
Con: `score` is not the ranking key (documented and disclosed per result); requires term
document-frequency maintenance (Tantivy already keeps per-term stats; or a store-level df map).

## 3. Recommendation

**Option B.** It removes the only arbitrary constant from the frozen configuration, keeps the
abstention floor meaningful across corpora, and keeps ranking policy honest and separable —
consistent with the contract's "score is evidence, selection is policy" split. If the
implementation session prefers A, the constant K must still be pinned pre-freeze and the floor
justification documented; B is strictly simpler to defend.

## 4. Non-negotiable boundaries (both options)

1. No per-query normalization of any kind (contract §6 D2); a best-irrelevant-document must never
   read `1.0`.
2. `score` must never be tuned against MemoraStrict outcomes; the smoke run validates plumbing
   (shape, range, floor reachable) only.
3. Journal records `score` and final `rank` for every selected result so any rank/score
   divergence is auditable after the fact.
4. Thresholds requested by the harness (`min_score`, `min_coverage` — pinned at `0.0` for the
   A/B) are selection thresholds in Gen3 terms, applied to the same support scale.

## 5. Decision

**Accepted (Option B).** Recorded in the pre-reg freeze receipt as a pinned configuration
value; property tests above are the enforcement. No further edits.
