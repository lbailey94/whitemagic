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

Current claim backed by these files: **LongMemEval-S 50q retrieval
R@1 = 0.80, R@5 ≥ 0.98, MRR ≈ 0.88–0.89** on the reference machine.

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
