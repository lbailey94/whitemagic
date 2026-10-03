# System One Temperature Refit — 2026-10-03

Status: **applied** · model config sha256 `5788b55e4a63324d49308e4304f7b970978d2272d64a6e3f458902785d08845e`
Report sha256: `0ee528f7a127fa243ad323bac3840a99d1555d21819fe33b7570624f14bad6e8`

## Data

- Source: `~/Desktop/trust-without-cloud/fast-decisions` (17 domains)
- Sample: 25 states/file, deterministic seed `20261003` → 425 states, 625 single-label choice questions
- Raw probabilities collected with temperature disabled (`t=1`, `temperature_by_options={}`) via `laya-serve` CPU f32
- Split: deterministic 70/30 by question id (SHA-256)

## Method

`q(t) = normalize(p_raw^(1/t))`; per (type, option-count) bucket `t` fitted by minimizing train NLL, then evaluated on held-out. Shipped checkpoint values baselined as `t_old` from `rl_agent_config.json`.

## Results (held-out)

| bucket | n_train | n_test | t_old | t_fit | acc | NLL raw | NLL shipped | NLL fit | ECE raw | ECE shipped | ECE fit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| choice:2 | 119 | 56 | 1.906 | 34.500 | 0.571 | 1.718 | 1.048 | 0.687 | 0.389 | 0.300 | 0.044 |
| choice:3-5 | 97 | 53 | 1.760 | 2.479 | 0.585 | 1.436 | 1.038 | 0.951 | 0.265 | 0.164 | 0.133 |
| choice:6-10 | 91 | 34 | 1.000 | 3.271 | 0.559 | 1.919 | 1.919 | 1.304 | 0.308 | 0.308 | 0.228 |
| choice:11+ | 120 | 55 | 0.101 | 2.819 | 0.364 | 3.694 | 15.897 | 2.456 | 0.444 | 0.625 | 0.155 |

## Findings

1. The shipped `choice:11+` temperature (0.1006) produced near-one-hot outputs (NLL 15.90, ECE 0.625). Refit to 2.819: NLL 2.456, ECE 0.155. Single largest defect found.
2. Binary choices were heavily overconfident on this corpus (ECE 0.300 → 0.044). `t=34.5` is near-uniform; the encoder's binary signal here is close to chance (acc 0.571), so honest confidence is ~0.5–0.57.
3. Accuracy is modest overall (0.364–0.585): calibration is not capability. This corpus is out-of-distribution relative to Laya's training mix; refit again on the 68-route receipts corpus as it accumulates.
4. `noul` and `score` temperatures were left as shipped — no labeled data of those types in this corpus.

## Verification

- Live server with applied config matches offline simulation: max drift ≤ 0.0003 for 3/4 buckets; 0.045 on `choice:6-10` (k=9) attributable to 4-decimal wire rounding amplified by the exponent (documented; not a config fault).
- `wm decision` before/after on the sample ticket: same choice `billing`, confidence 0.7246 → 0.4919.
- Full workspace and `systemone`-feature test suites green (2026-10-03).

## Config change (choice buckets only)

| key | shipped | refit |
|---|---|---|
| choice:2 | 1.9064 | 34.5000 |
| choice:3-5 | 1.7602 | 2.4790 |
| choice:6-10 | 1.0000 | 3.2706 |
| choice:11+ | 0.1006 | 2.8191 |

Backups: `rl_agent_config.json.shipped.bak` (original), `rl_agent_config.json.raw.bak` (t=1 collection config).

## Repro

- `scripts/systemone/s1_collect.py` (run against `laya-serve` with the t=1 config) → raw probabilities
- `scripts/systemone/s1_fit.py` → report
- `scripts/systemone/s1_apply.py` → config
- `scripts/systemone/s1_verify.py` → served-vs-offline check
- Raw data: `receipts/systemone_raw_probs_2026-10-03.jsonl` (244K)
