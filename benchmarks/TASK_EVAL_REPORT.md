# Authored memory-task regression measurements

Generated from `pinned-task-eval-results.json` at 2026-10-18T03:27:50Z. The corpus contains 32 authored scenarios, eight per family. There is no connected model, unseen holdout, autonomous agent study, or general-performance qualification.

| Task and scored outcome | WhiteMagic source candidate | Structured file comparison |
|---|---:|---:|
| Continuity: decision recall, all eight cases | 100.00% | 100.00% |
| Continuity: exact open-arc check | 100.00% | 100.00% |
| Conflict: governed current truth, seven cases | 100.00% | 100.00% |
| Repair: poison-free repaired identity in top three | 100.00% | 62.50% |
| Repair: repaired identity at rank one | 100.00% | 50.00% |
| Repair: legitimate neighbor state preserved | 100.00% | 100.00% |
| Cue-guided migration: obsolete-target recall | 100.00% | 100.00% |
| Cue-guided migration: end-to-end workflow | 100.00% | 100.00% |

Continuity scores only the exact compact `agent_context.text` string under the 1,120-byte UTF-8 cap. Mean of per-context ceil(bytes/4) token estimates is 266.625; largest observed context is 1091 bytes. This estimate is not a model-tokenizer guarantee. Every consumed turn, checkpoint, queue, flag, crystal and briefing is inside the string; transport/debug metadata is excluded.

The structured continuity files receive the same turn metadata, resolution links and typed/importance/content salience rules. They serialize turns only; WhiteMagic may include derived checkpoint, queue, flag and crystal fields. Wire overhead is not equal. The text heuristic can match quoted or otherwise invalid claims; it does not establish authority or truth.

Conflict current truth across all eight cases is 87.50%. M8 deliberately writes an unlinked contradiction, retaining the boundary that ungoverned text is not a supersession operation. Governed lineage verification is 100.00%; the structured supersedes files do not provide a cryptographic revision DAG.

Discovery corpus sizes are [5] records per case, two obsolete and three legitimate; there are 24 legitimate neighbors overall. Both adapters receive the exact stale clues, search query and authoritative replacement. IDs do not reveal labels. The adapter uses bounded phrase/negation patterns; unfamiliar paraphrases can fail. WhiteMagic's workflow reads every obsolete ID to verify retirement to the expected head and separately verifies the converging DAG.

Runtime accounting: 601 requested calls, 601 explicit successful responses, 0 failed/unverified, 0 ignored. Protocol, response identity, lifecycle and byte-contract errors abort the run. Exit zero means measurement execution completed; inspect task scores and traces for task failures. Latency includes fresh process startup and unequal tool batches, so this run establishes no latency or operating-cost advantage.

## Reproduction and identity

```bash
WM_BINARY=/absolute/path/to/reviewed/wm python3 benchmarks/pinned_task_eval.py
python3 -m unittest discover -s benchmarks -p test_pinned_task_eval.py
python3 benchmarks/render_task_eval_report.py
```

- Source parent/commit: `766edb2de10d73b6d7204b916473816329eb5efb`; tracked runtime diff SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Exact binary SHA-256: `47da191513cdfcf3734c7453b59f9cc2565d122bae9f33d00316a7b1f62481f6`; reported version: `wm 10.4.0`.
- Harness SHA-256: `fecc179b9aa6624e20b1732c3366c2aedc1e197c0db2e9a7eff7e27c308bc53b`.
- Raw call audit SHA-256: `b73f27e0626734af251d0f2b6a0a01194284fbbd940b7a0fc21fc5713cba7eb0`; a gzip copy is retained as `runtime-call-audit.json.gz`.
- Source file hashes are recorded in the JSON. A source candidate reporting the same version as a release is not necessarily the signed published binary.
- Earlier v10.4.0 fixture results remain in `historical/pinned-task-eval-results-19169fa.json`; earlier code is preserved at Git commit `19169fa`.

## Observed failure and boundary traces

```json
[
  {
    "active_stale_count": 2,
    "cause": "Negative control: an unlinked raw contradiction supplies no supersession edge",
    "expected_record_id": 2,
    "lineage_ok": false,
    "scenario": "M8_stress_unlinked_contradiction_without_update",
    "system": "whitemagic_v10_4",
    "top1_record_id": 1
  }
]
```
