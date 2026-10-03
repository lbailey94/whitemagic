# RECEIPT — B1 acceptance demonstrated (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests; no operator act required (no freeze, no verdict). B1 spec frozen rev 1 (`9b293d01…`,
receipt `W1_SPEC_B1_FREEZE_2026-09-17`). Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_b1_acceptance_2026-09-17/` (129 files) |
| **SHA256SUMS** | `6504cf44bf1ed5a79130e1bc5bf3892200b5225488e44176626a1bf22eb918c8` |
| Candidate | `target/release/wm-gen3`, sha256 `76083d050e94e707b480f431418ae155392ec126facfcd48c076fe25d9df5f82` (release built at `c12179d`; no code change since — docs/receipts only) |
| Reference | source-frozen rebuild of nucleus-freeze commit `7ff9181`, sha256 `7838106ee6228e1a3003fb91ae3e2e080012f94723fcb2b671a4c81aada42be5` (pinned toolchain 1.98.0; see §3 disclosures) |
| Corpora | `experiments/semantic_projection/holdout` seeds 6-10 — 10 files MANIFEST-verified; recorded cells `results_p2c/{C00,C01}` (binary `93c667ec…`, runner `df9d42c2…` — current harness hash matches the recorded manifest) |
| Tip at run | `726ccfa`, tree clean |

## 2. What was demonstrated (spec W1_B1 §3–§5)

| # | Acceptance | Result |
|---|---|---|
| 1 | **Frozen-corpus regression (§5.1)** | Stage A: reference vs recorded cells — **C00 (all switches off)** and **C01 (defaults)**: 80 queries each, **ordering + metrics 0 diffs** (scores within 1 f32 ULP). Stage B: candidate vs reference on the gate-neutralized corpus — **C00** and **C01**: 80 queries each, **0 diffs**. Candidate intake on the deduped corpus: no refusals, no violations, `written == items` |
| 2 | **C2/C3 templates (§5.2)** | Canary re-run `C1–C6` 12/12 PASS (receipt `CANARY_RERUN_2026-09-17`): R-ablation ordering flip and count-gate fired sets reproduced on the current tip |
| 3 | **Rank-field audit (§5.3)** | every selected entry carries `rank_key/score/semantic_support/stratum/superseded_by/rank`; ordering reconstructible from the journal (`rank_key` desc, `id` desc) and identical to the response order; ranks 1..n; complete `provenance.chain` per hit; `rank_key >= score` for non-superseded |
| 4 | **Floor boundary table (§3 case 5)** | fail-closed floor validation lives on the same `recall` path — demonstrated in `IMPL_A2_FLOOR_BOUNDS_2026-09-17` (NaN/±Inf/out-of-range refused, no journal events) |
| 5 | **No-planner proof (§5.5)** | syntax: forbidden organs absent from core+harness source (`rrf`, `reciprocal_rank`, `cross_encoder`, `jaccard`, `qfhrr`, `planner`, `rerank`, `entity_boost`, `importance_boost`, …); the rank key has exactly one assignment and one multiplicative step (recency 0.05, supersede 0.60, statutory values); `cargo tree` has no `wm-*` crate; closure static scans PASS. Behavioral: any unregistered ordering term fails the §5.1 0-diff |

## 3. Disclosures

- **A1-gate boundary (why "gate-neutralized").** The recorded cells predate the A1 exact-hash gate
  (`8c5e32f`). The frozen corpora contain same-session repeated turns (e.g., seed 6: 776 turns →
  527 gate-admissible), so the current binary refuses them `duplicate_exact` by spec — the raw
  comparison would measure an intake change (A1), not the ranking path (B1). Stage B therefore
  uses a corpus deduplicated by the gate identity (session, role, `has_answer`, content); the
  derivation is scripted in `driver_regression.py`, source files are MANIFEST-verified, and the
  derived corpus sha256 is recorded (`regression/corpus_dedup.sha256`). The derived corpus files
  are not committed (size, ~11 MB); regeneration is deterministic from the frozen source.
- **Build non-reproducibility.** Two fresh builds of the same frozen source produced different
  binaries (`7838106e…` vs `32026dad…`); the historical nucleus binary `b1c66fec…` was **not**
  reproduced. The regression is therefore behavioral (ordering + metrics exact; scores bounded).
- **Score variation is 1 f32 ULP.** ~5–8 % of per-hit scores differ by at most one ULP at the
  core's f32 precision between builds; ordering, ranks, candidate counts and recall metrics are
  unaffected in every compared run. Counts are in `regression.results.txt`.
- **Reference validity.** Stage A is the anchor: the rebuild reproduces both recorded cells'
  ordering exactly, so stage B's 0-diff transfers to the frozen cells modulo the A1 intake change.
- No verdict, claim, gate, or threshold movement; counts generated, never narrated.

## 4. Consequences

B1's acceptance items are wired and demonstrated (item 4 cited from A2; items 1/2/3/5 executed
here). Remaining row-exit item is operator review. The A1-gate boundary is recorded as a
regression-methodology fact: recorded all-off cells are only comparable on gate-neutralized
corpora from here on.
