# Benchmark Results Index

Every JSON in this directory is a raw benchmark run retained as evidence.
This file indexes the landmark runs and explains which numbers back which
claims. All runs: Lenovo ThinkPad T480s, local store, no cloud services.

## LongMemEval-S, 50 questions (retrieval quality)

Canonical series: `longmemeval_s_v*_50q*.json`. Metric = retrieval recall of
the evidence-bearing session (R@k) and mean reciprocal rank (MRR).

| Date | Run | R@1 | R@5 | MRR | What it proved |
|---|---|---|---|---|---|
| 2026-08-14 | `v5_50q` | 0.60 | 0.68 | 0.637 | v5 lexical baseline |
| 2026-08-17 | `v6_50q_episodic_bounded` | 0.66 | 0.86 | 0.740 | episodic route + bounded candidates |
| 2026-08-18 | `v6_50q_coverage_grace` | 0.74 | 0.98 | 0.840 | role-aware coverage scoring |
| 2026-08-18 | `v6_50q_keys_planner` | 0.68 | 0.86 | 0.756 | keys+planner A/B (kept; see session log) |
| 2026-08-18 | `v6_50q_scoring_tuned` | 0.68 | 0.90 | 0.765 | cross-key matching + aliases |
| 2026-08-18 | **`v6_50q_ucla_fix`** | **0.80** | **1.00** | **0.890** | temporal anchor fix — best full-provenance run |
| 2026-08-18 | `v6_50q_grace2_final` | 0.80 | 0.98 | 0.880 | grace2 config, reproducible |
| 2026-08-27 | **`v6_50q_dupsort_sidecar`** | **0.86** | **1.00** | **0.923** | DUP_SORT postings sidecar; in-process 25k profile: ingest 6.5s→1.9s, no-match 4.4s→~0ms (see V6_EPISODIC_PERFORMANCE_PLAN.md) |
| 2026-08-29 | **`v6_50q_dupsort_sidecar_rerun_alpha6`** | **0.86** | **1.00** | **0.923** | Clean re-run on the v7.0.0-alpha.6 binary — the 0.86 claim CONFIRMED (≥ 0.84 threshold; no revert to 0.80). Same protocol, same 50q canonical dataset. |
| 2026-08-29 | **`v6_50q_splitwindows_alpha6`** | **0.86** | **1.00** | **0.923** | Harness timing-window split (spawn vs ingest vs search). True search-only latency: **p50 74ms / p95 235ms** — the earlier conflated "search p50 6649ms" was batch round-trip noise. Retrieval quality unchanged across three consecutive runs. |
| 2026-08-31 | **`v6_50q_dupsort_sidecar_rerun_alpha8`** | **0.86** | **1.00** | **0.923** | Re-run on the v7.0.0-alpha.8 release binary (`c1bf519`) after the write gate, tier stamps/typology, envelope v2, and content repair touched the store path — **retrieval quality did not move** (R@1/R@5/MRR byte-identical to baseline; ≥ 0.84 threshold held). Search latency improved: p50 57.9ms / p95 155.2ms (vs 74/235 on alpha.6). The honest post-memory-line confirmation; unblocks the S8 comparative run (knobs >0 vs this baseline). |
| 2026-09-01 | **`v6_50q_s8_fresh_baseline`** | **0.86** | **1.00** | **0.923** | S8 fresh baseline on the post-reset main (`19f92f9`: alpha.8 + doctor `--network` + CLI session parity) — retrieval byte-identical again (fourth consecutive 0.86/1.00/0.923). Search p50 55.1ms / p95 125.4ms (same band, slightly better than alpha.8's 57.9/155.2). Dataset path note: the repo-local `benchmarks/data/longmemeval_s/longmemeval_s_50q_canonical.json` is the canonical input now (the script's parent-dir default predates the single-commit reset). |
| 2026-09-01 | **`v6_50q_s8_trust03_episodic_neutral`** | **0.86** | **1.00** | **0.923** | S8 acceptance run: episodic route with `WM_TRUST_WEIGHT=0.3` (>0) — **byte-identical to baseline**. The trust knob is inert on the episodic route by construction (fusion untouched); measured, not assumed. Search p50 55.2ms. The "knob>0 vs the 0.86 baseline" acceptance is MET by this run. |
| 2026-09-01 | **`v6_50q_s8_hybrid_knobs_off`** | 0.64 | 0.82 | 0.715 | Hybrid-route reference, knobs off. **Honest protocol note:** the deployed configuration runs a stub embedder, and the server only wires `RecallEngine` into tools when the embedder is real — so this run exercised the tool's **BM25-fallback path** (`source: fts`), not vector fusion. The 0.64-vs-0.86 gap is the measured form of the recall-mode-honesty board item (route quality differs; results must disclose their mode). |
| 2026-09-01 | **`v6_50q_s8_hybrid_trust05_labels`** | 0.64 | 0.82 | **0.7217** | Trust A/B on the same path with `WM_TRUST_WEIGHT=0.5` + corrected stamps (`--trust-labels`: needle-session turns `source=user`/1.0, distractors 0.7). MRR +0.007 — trust weighting reorders meaningfully; head-of-list recall unchanged at this knob. |
| 2026-09-01 | **`v6_50q_s8_hybrid_trust10_labels`** | **0.68** | 0.82 | **0.7417** | Knob at 1.0 (factor span 0.65–1.3): R@1 +4 pts and MRR +0.027 vs knobs-off — **monotonic in the knob** on the deployed (BM25-fallback) path. Trust-into-fusion behaves as designed where it lives. |
| 2026-09-01 | **`v6_50q_s8_conformal_alpha01`** | 0.48 | 0.76 | — | Conformal plumbing run (`WM_RECALL_CONFORMAL_ALPHA=0.1`, persistent store — accumulating corpus, NOT protocol-comparable to the fresh-store rows above; expect degradation, the claim here is plumbing not quality). The calibrated-loop evidence lives in the live verification: honest `uncalibrated` disclosure → `memory.recall_feedback` ≥10 samples → `active` with threshold 0.85 + per-result `in_conformal_set` + write-through persistence. Harness coverage metric needs a fix (conformal_set capture fired only when status was active at search time) — parked with the ONNX follow-up below. |
| — | *parked: ONNX hybrid A/B + coverage* | — | — | — | Real-fusion runs (baseline / trust / conformal coverage on vector+BM25) are parked until the fleet actually deploys a real embedder — the shipped configuration is stub-embedder (see the honest note above), so those numbers would describe a configuration nobody runs. Harness additions (`--trust-labels`, `--conformal`) are landed and ready for that day. |

Current claim backed by these files: **LongMemEval-S 50q retrieval
R@1 = 0.86, R@5 = 1.00, MRR ≈ 0.92** (`v6_50q_dupsort_sidecar`, 2026-08-27,
confirmed twice on 2026-08-29 by `..._rerun_alpha6` and `..._splitwindows_alpha6`)
on the reference machine. Search latency claim: **p50 ≈ 74ms, p95 ≈ 235ms
search-only** (`..._splitwindows_alpha6`); the pre-split conflated p50
(6.6s) must not be cited as search latency.

Caveats:

- `v5_50q_episodic.json` reports R@1 0.86 / MRR 0.9233 but contains **zero
  per-query records** — treat as unprovenanced until re-run with per-query
  output. Do not cite it.
- Answer-level LongMemEval "overall" scores (~50%) are a different metric
  (answer correctness, not retrieval) tracked in the MemoraStrict/V6 docs.

## Internal v6 suite, 50 questions

`v6_50q_phase*_final.json` — same shape, different question mix and scoring
experiments. Best: `phase3_final` (2026-08-20) R@1 0.86, R@5 1.0,
MRR 0.923. Used for fast iteration; not comparable to LongMemEval numbers.

## MemoraStrict (answer accuracy)

Raw seed files live in `benchmarks/data/memorastrict/`; aggregated scorecards
in `memorastrict_*_aggregated.json` here and in `docs/V6_NEXT_SESSION.md`.
Headline (5 seeds × 43 questions, abstention on): see V6_NEXT_SESSION.md —
T-series fixes took verification from 0%→100% and aggregation 0%→86.7%.

## Scale artifacts

`scale_1000/`, `scale_10000/` under `benchmarks/data/memorastrict/` are
generated noise-padded stores from the T7 scale generator (`--scale-turns`),
for latency/scaling runs. Regenerable; not evidence.

## Rules

1. Never cite a number without naming its file.
2. Never edit an old result file; add a new run.
3. Runs missing `per_query` provenance are marked unprovenanced and cannot
   back public claims.
