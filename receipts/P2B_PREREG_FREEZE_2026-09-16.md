# RECEIPT — P2B plan freeze (GEN3-P2B-PROJECTION-001)

**Status: PLAN FROZEN · 2026-09-16.** Operator approved the successor experiment with the
recorded edits and chose dependency option (a) pretrained local embeddings. This receipt freezes
the **plan only**; the **implementation-freeze receipt** (`P2B_IMPLEMENTATION_FREEZE_*.md`)
remains required before any scored run (pre-reg §9). Nothing under this experiment has run.

---

## 1. Frozen plan artifacts (sha256)

| Artifact | sha256 |
|---|---|
| `experiments/semantic_projection/PRE_REGISTRATION.md` | `895141f2dfac653df92f267d89835c72142826ef6ea546c59c7d21298832f507` |
| `receipts/DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16.md` | `331f306ac03b39cb7e4b460558386b77381b41edca8e46f254ef8198de13d2f1` |

## 2. Approved edit set (recorded)

1. **Factor disambiguation:** the 2×2 factors are **S (semantic projection off/on)** × **R
   (supersedes off/on)**; C01 = S-off/R-on = frozen Phase-2 reproduction. The projection's two
   attachment points (recall expansion, `think` pair gating) are an *internal ablation inside
   S-on cells*, not a factor.
2. **Numeric materiality pins:** M1 ≥ +4 top-5 successes pooled (≥ 36/40) and T8 ≥ 3/15
   (secondary); M2 (principal separation metric) `P(rank 1 | answer in top-5)`, supersedes
   material at ≥ 10 pp, projection must not degrade M2 by > 5 pp; M3 precision ≥ 2× baseline
   (≥ 2.12 %) with pooled true-pair recall ≥ 85 % and reversed-direction matches = 0; M4 pair
   population reduced ≥ 50 % with recall held.
3. **Embedding pins:** exact model/snapshot/artifact hashes, tokenizer/config hashes, CLS
   pooling, 384-dim, L2-normalized, cosine, brute-force (ANN forbidden), offline, no
   fine-tuning/vocabulary augmentation/query rewriting/labels, same model every cell; embedding
   compute measured separately and inside end-to-end cost.
4. **Genericity battery frozen** (synonym/paraphrase positives + lexical-overlap hard negatives)
   with one fixed threshold pair calibrated on the battery only.
5. **Dependency decision:** option (a), per the exception receipt; PPMI/SVD deferred as a
   separate question.

## 3. Preconditions checklist

- [x] Operator approval with edits (2026-09-16)
- [x] Dependency exception receipt (hash above)
- [x] Successor claim registered in the wmv9 claims ledger: **`claim-0001`**, status `pending`
- [ ] Implementation-freeze receipt: implementation commit + binary sha256 + τ_pos/τ_neg +
      similarity gate + genericity-battery pass on the frozen build — **before any scored run**

## 4. Budget (opens at this plan freeze)

1 session per cell + 1 analysis = 5 sessions; overruns ≤ 1; inconclusive within 30 days →
paused, not extended. Tracked in `receipts/BUDGET.md` §P2B.

## 5. Rules

Any change to the plan artifacts above, the embedding pins, or the battery re-baselines the
experiment with a new receipt. Phase 3 remains blocked. The frozen Phase-2 configuration is not
retro-fitted.
