# Benchmark data

Datasets are **not vendored** in this repository (2026-10-01). The
LongMemEval-S canonical subset is fetched locally, not committed, because it
contains third-party content that does not belong in a public repo.

## LongMemEval-S

Expected at the sibling path `../benchmarks/data/longmemeval_s/` (relative to
this repository root), or point `LONGMEMEVAL_DATA` / `WM_DATASET` / `--dataset`
at it:

```bash
# from the repo root, with the dataset fetched from the upstream LongMemEval release
python3 scripts/longmemeval_bench.py --dataset ../benchmarks/data/longmemeval_s
bash scripts/eval_matrix.sh            # honors WM_DATASET
```

Upstream: <https://github.com/xiaowu0162/LongMemEval> (see its license and
terms before redistributing). The `cleaned/` subdirectory is generated locally
and is gitignored.

`memorastrict/` and `t1-fixture/` are first-party fixtures and remain tracked.
