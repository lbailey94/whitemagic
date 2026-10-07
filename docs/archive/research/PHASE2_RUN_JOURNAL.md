# Phase 2 — Gen3 Run Journal (schema)

**Status:** working spec · 2026-09-16 · required before Phase 2; read by the pre-reg's
H3–H8 accounting and by `inspect`. **Not binding until referenced by the frozen pre-registration.**

Purpose: the stock harness measures H1/H2/H7-latency only. The journal is the Gen3 arm's
observable record of *decisions, refusals, relations, provenance and violations* so the
remaining pre-registered metrics are computable from artifacts rather than from memory. It is
also `inspect`'s backing store for experiment runs. Two rules:

1. **Journal never influences scoring.** Nothing in the recall path may read it as a signal.
2. **A run with a broken journal is invalid, not silently unmeasured.** Write failures are
   loud; the run manifest records `journal_ok:false` and the run does not count as evidence.

---

## 1. Files per run

| File | Contents | Privacy default |
|---|---|---|
| `run_manifest.json` | run id, arm, binary sha256, seed, frozen config (categories, flags), start/end, counts, journal sha256, smoke flag | shareable |
| `journal.jsonl` | append-only events (§2), one JSON object per line | **hash-only content**; raw mode is debug-only |
| `structure_inventory.json` | H8 candidate structures with six-condition evidence fields | shareable |
| `memory_rss.txt` | optional `usr/bin/time -v` capture (H7) | shareable |

Common envelope on every event: `{"ts": <rfc3339>, "run_id": …, "seq": <monotonic int>,
"type": …}`. Content-bearing fields default to `content_sha256` + `content_len`; raw text only
under an explicit debug flag (the benchmark corpus is synthetic, but the schema should not
depend on that).

## 2. Event types

| `type` | When | Required fields (beyond envelope) | Feeds |
|---|---|---|---|
| `run.start` | process start | `arm`, `binary_sha256`, `store`, `config` | manifest |
| `ingest.batch` | after each `batch_create` chunk | `batch_id`, `items`, `ids` (or `ids_sha256`), `took_ms` | H7 |
| `remember.refusal` | per refused item/batch | `batch_id`, `reason`, `mechanism`, `refused_by` | H6, honesty |
| `think.sweep` | before/after each sweep | `sweep_id`, `window_start_seq`, `pairs_examined`, `proposals`, `promotions`, `demotions`, `took_ms` | A1/A6, H7 |
| `relation.proposed` | per proposal | `relation_id`, `kind` (`supersedes`), `src`, `dst`, `rule_id`, `confidence`, `components` (subject_key_hash, value_tokens_hash, ordering evidence), `class` (`speculation`) | A1, H3, H8 |
| `relation.state_change` | promotion/demotion | `relation_id`, `from`, `to`, `reason` (survival/use/unused-K) | A6 |
| `selection.decision` | per recall | `query_id` (harness id), `query_sha256`, `stance`, `considered`, `selected` (`[{id, rank, score, currentness}]`), `abstained`, `reason`, `took_ms`; **additive** (2026-09-17): `projection_ran`, `projection_error` (A2 route honesty; required set unchanged) | H1/H2 provenance, A3/A4 |
| `provenance.chain` | per selected result | `result_id`, `chain` (record ids + provenance kinds), `complete` (bool) | **H4** |
| `boundary.refusal` | A forbidden attempt was **correctly refused** (healthy expected behavior) | `boundary`, `mechanism`, `refused_by`, `probe_id` | H5 probe evidence; **never counts against H6** |
| `closure.violation` | An invariant was **actually crossed** (should be impossible) | `boundary`, `mechanism`, `probe_id` | **H6 counts only these** |
| `canary.probe` | per planted canary exercise | `probe_id`, `kind` (`laundering`/`testimony`/`unchannelled`/`positive`), `planted_id`, `attempts`, `observed_domains`, `outcome` | **H5** |
| `run.end` | shutdown (written by `Substrate::finish`) | `records`, `relations`, `violations`, `journal_ok`, `events_before_end`, `sweep_enabled`; host writes the journal file hash to `WM_GEN3_JOURNAL_HASH_OUT` | manifest linkage |

## 3. Metric computation (wrapper-side joins)

All computations happen **outside** the substrate, in the experiment wrapper; labels never
enter the substrate (contracts §2.3).

| Metric | Procedure |
|---|---|
| **H3** proposal quality | Join `relation.proposed` endpoints against generator ground truth (true pairs: T8 `old_fact`/`new_fact`; T1 preference change steps; everything else = non-pairs). Ground truth stays entirely outside the runtime and the substrate. Report **precision and recall** of proposals per seed, **direction-aware** (`src` must be the later/new value, `dst` the earlier/old — `new → supersedes → old`; a correct pair with reversed direction is not a hit). Control side: not measurable (no proposal surface) — informational only, as decided. |
| **H4** provenance retention | Fraction of `selection.decision.selected` entries with a `provenance.chain` event where `complete:true`; requires 100%. |
| **H5** laundering | Any `canary.probe` with a domain change attempt not refused, or any `closure.violation` with mechanism in {relabel, promote-simulated}; requires zero. `boundary.refusal` events are expected healthy behavior and are *not* violations. |
| **H6** constitutional violations | Count of `closure.violation` events **only** — refusals (`boundary.refusal`) must never be counted, or zero-violation could become impossible by construction. Requires zero. |
| **H7** cost | Harness `latency`/`ingest` + `memory_rss.txt` + `think.sweep.took_ms` totals. |
| **H8** emergent structure | `structure_inventory.json` entries passing the six-condition test + ablated-run comparison (journal from both runs). |
| **A-ledger ablations** | A1: sweep disabled via **`WM_GEN3_SWEEP=0`** (same command line; journal `think.sweep.disabled:true`, zero proposals); A2: trust fixed; A3: hop budget 0; A4: `include_historical` symmetric; A6: promotion policy off (`candidate-forever`). Same journal schema in every variant. |

`think.sweep` instrumentation (implemented): `pairs_considered`, `pairs_skipped_existing`,
`pairs_rejected_rule`, `proposals`, `index_ms`, `pair_ms`, `promotion_ms`, `took_ms`, plus the
policy snapshot. The pair loop dominates sweep cost; reduce the pair population before
micro-optimizing the rule.

**Additive disclosure note (2026-09-17, A2 route honesty):** `selection.decision` gained
`projection_ran` / `projection_error` (truthful-route disclosure: a degraded or absent semantic
pass must not be indistinguishable from healthy-with-zero-results;
`docs/specs/W1_A2_evidence_disclosure.md` §3 case 7). Required fields and joins (H1/H2/A3/A4) are
unchanged; runs remain schema-compatible.

## 4. Smoke-run marking

The pre-freeze smoke run (both arms, seed 1, T8 only) writes the same artifacts with
`"smoke": true` in the manifest and a distinct run id prefix (`smoke-`). Smoke journals are
plumbing validation only and are excluded from any claim; the wrapper refuses to aggregate
across smoke/evidence runs.

## 5. What this closes

- Interface §5 instrumentation gaps: H4/H5/H6/H8 now have a concrete carrier; H3 has a
  defensible protocol (proposal precision/recall vs generator ground truth).
- `inspect` obligations: the same events back the tier-map/selection explanations for humans,
  so the experiment surface and the introspection surface are one mechanism, not two.

Open points for implementation review: whether `selection.decision` truncates `considered`
(proposed: count + ids_sha256, not the full list — size), and whether `provenance.chain` is
emitted per result or aggregated per query (proposed: per result; H4 needs completeness at
result granularity).
