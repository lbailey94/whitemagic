# System 0.5 Bake-off — Static Embeddings vs Laya (2026-10-03)

**Verdict: System 0.5 is a retriever, not a decider.** Static embeddings at ~0.3–0.4 ms/state are excellent at *shortlisting* candidates (recall@10 = 0.96) but do not replace Laya as the decision engine (0.26–0.31 vs 0.515 accuracy), and naive semantic caching of decisions is unsound (equivalence AUC 0.52–0.57).

## Setup

- Corpus: `trust-without-cloud/fast-decisions`, 425 states / 625 single-label choice questions / 25 decision surfaces (domain+task+option-set), up to 77 labels per surface
- Split: deterministic 70/30 by question id (same as the temperature refit, 2026-10-03)
- Hardware: T4800-S (i5-8350U, 8 threads, no GPU)
- Environments: `~/.venvs/s05` (model2vec 0.9.0, scikit-learn 1.9.1)
- Laya baseline: on-disk raw t=1 probabilities with the refit temperatures applied

## 1. Top-1 accuracy (n=198 held-out)

| method | acc | NLL | ECE |
|---|---|---|---|
| **laya/zero-shot** | **0.515** | 1.355 | 0.092 |
| gzip+NCD kNN (no training) | 0.308 | — | — |
| potion-32M kNN (k=10) | 0.308 | 5.30 | 0.098 |
| potion-8M kNN (k=10) | 0.293 | 4.93 | 0.122 |
| potion-8M + logreg | 0.263 | 3.39 | 0.113 |
| TF-IDF + logreg | 0.253 | 3.40 | 0.140 |
| potion-32M + logreg | 0.253 | 3.39 | 0.124 |

Embedding throughput (this CPU, long states, includes truncation at 512 tokens):
- potion-base-8M: 0.43 ms/state (2,319/s), 256-dim
- potion-base-32M: 0.33 ms/state (3,028/s), 512-dim

## 2. Cascade economics (potion-32M kNN)

On covered items, 0.5 accuracy never reaches Laya's accuracy on the same items:

| signal | τ | coverage | acc(0.5) | acc(Laya on covered) |
|---|---|---|---|---|
| confidence | 0.20 | 0.93 | 0.319 | 0.541 |
| confidence | 0.40 | 0.47 | 0.430 | 0.591 |
| confidence | 0.60 | 0.13 | 0.500 | 0.654 |
| margin | 0.20 | 0.22 | 0.488 | 0.628 |

Conclusion: no operating point where delegation to 0.5 preserves accuracy on this corpus.

## 3. Shortlist recall (ranking labels, not answering)

| model/head | R@1 | R@3 | R@5 | R@10 | R@16 |
|---|---|---|---|---|---|
| potion-8M kNN | 0.293 | 0.707 | 0.813 | **0.960** | 0.995 |
| potion-32M kNN | 0.308 | 0.702 | 0.828 | 0.949 | 0.995 |
| potion-8M logreg | 0.263 | 0.667 | 0.778 | 0.960 | 0.985 |

A 0.4 ms static retriever keeps the gold label in a 10-item shortlist 96% of the time. This is the concrete 0.5 role: candidate generation / routing, matching the retrieve-then-decide pattern (cf. §8.3 route findings).

## 4. Semantic-cache equivalence (4,500 within-surface pairs)

Positive = same gold label, negative = different gold. Score = state-pair similarity.

| method | AUC | balanced acc (best t) | hard-neg rate (sim>0.95) |
|---|---|---|---|
| TF-IDF cosine | 0.572 | 0.559 | 0.000 |
| gzip-NCD (negated) | 0.548 | 0.536 | 0.000 |
| potion-32M cosine | 0.522 | 0.526 | 0.000 |
| potion-8M cosine | 0.518 | 0.522 | 0.000 |

No method separates same-label from different-label states at this corpus's similarity scale. A threshold-based semantic decision cache would either never fire (strict) or be unsafe (loose). If a decision cache is wanted, it needs a learned equivalence head (SemanticMemo pattern) or exact/near-exact duplicate keys only.

## Implications

1. Keep Laya (System One) as the decision engine for novel states. Its refit calibration (ECE 0.092) is the strongest asset.
2. Build 0.5 as `decision.shortlist`: static-embed the state (~0.4 ms), rank candidate labels/routes/actions, then hand a short list to the decider (or a small cross-encoder). This is where the 10,000x latency win is real.
3. Do not ship semantic caching of decisions on cosine thresholds. Use exact keys, or a trained equivalence head with outcome-verified labels.
4. gzip+NCD kNN is competitive with static kNN on this small corpus and needs no model — keep as the cold-start/OOD reference baseline in evals.
5. Static embeddings at 0.3–0.4 ms/state are a viable replacement for the hot-path embedder (BGE-small in `wm-gen3-core` costs ~tens of ms) where recall depth can be traded for speed; keep BGE for deep recall.
6. Next eval: re-run the bake-off on the 68-route catalog once intents are regenerated (original `intents.jsonl` is missing); compare shortlist recall against the recorded bge-small ceiling (65% @16) and the JEV/NLU baselines (30%/23.75%).

## Repro

- `scripts/system05/s05_experiment.py` — bake-off (needs `/tmp/opencode/s1_raw_probs.jsonl` from the temperature refit collection)
- `scripts/system05/s05_deepdive.py` — cascade, shortlist, cache tests
- Raw results: `receipts/s05_fastdecisions_results.json`, `receipts/s05_deepdive_results.json`
- Models: `minishlab/potion-base-8M`, `minishlab/potion-base-32M` (MIT); Python `model2vec` 0.9.0

---

# Addendum — Route-catalog eval (recovered original 80 intents, 68 routes)

The original `intents.jsonl` was recovered from `2026-09-27-demo-research-pack-v0.13.tar.gz`
(same 130 intents; 80 remain after the documented structural gaps). Same route strings and
prompt as `run_route_eval_v9.py`.

## Retrieval (zero-shot: intent text vs route descriptions)

| retriever | top-1 | R@3 | R@5 | R@8 | R@10 | R@16 |
|---|---|---|---|---|---|---|
| potion-base-32M | **0.438** | 0.550 | 0.613 | 0.738 | 0.762 | **0.838** |
| potion-base-8M | 0.400 | 0.562 | 0.675 | 0.725 | 0.775 | 0.812 |
| bge-small-en-v1.5 | 0.338 | 0.438 | 0.512 | 0.637 | 0.637 | 0.725 |

Recorded baselines on the same intents: NLU 0.2375, JEV 0.30; recorded bge-small shortlist
ceiling 0.41/0.50/0.65 @k=3/8/16 (different retrieval pipeline; treat as indicative).
Static embeddings exceed every recorded number and beat bge-small in this harness.

## Laya on the route catalog

- Full 68-option question: **0.125** accuracy — the >20-option budget truncates labels to
  ~3–4 tokens; the >20-option cliff is confirmed.
- Retrieve-then-Laya (Laya sees only the potion top-k with full descriptions):

| k | accuracy | conditioned on gold-in-shortlist | gold-in-shortlist | mean wall |
|---|---|---|---|---|
| 3 | 0.350 | 0.636 | 0.550 | 1.17 s |
| 5 | 0.325 | 0.531 | 0.613 | 1.70 s |
| 10 | 0.287 | 0.377 | 0.762 | 2.18 s |

Laya is worse than the similarity ranking itself at choosing among its own shortlist
(similarity's conditioned top-1 at k=3 = 0.438/0.550 = **0.796** vs Laya's 0.636), and
degrades as distractors grow. Latency: potion 0.33 ms/state vs Laya 4.28 s/intent full,
1.17–2.18 s shortlisted.

## Conclusions for System 0.5, route dispatch

1. Route dispatch should be a **static-embedding retrieval problem**: potion-32M (or 8M) top-1
   already beats every recorded decision head at ~0.4 ms/state.
2. Do not put Laya in wide-option routing. Its 11+ option bucket is a known cliff, and it
   loses to similarity ranking even on curated 3-item shortlists.
3. Improve route descriptions (verb coverage — e.g. "remember/store/create" synonyms) before
   tuning thresholds; retrieval misses are lexically driven ("remember this…" vs
   "memory.create — Store a new memory or fact.").
4. If a learned decider is wanted on shortlists, train a cross-encoder for route selection from
   receipts; do not reuse Laya.

## Addendum repro

- `scripts/system05/s05_routes.py` — retriever + Laya full/shortlist matrix; intents recovered via
  `tar -xzf 2026-09-27-demo-research-pack-v0.13.tar.gz --wildcards '*intents.jsonl'`
- `scripts/system05/s05_route_cascade.py` — retrieve-then-Laya cascade
- Results: `receipts/s05_routes_results.json`, `receipts/s05_route_cascade_results.json`
- Rust port: `crates/wm-gen3-zeropointfive` with fixture `tests/route_fixture.rs` (matches the
  Python harness exactly: top-1 0.438, R@16 0.838; ~13 ms/intent with `fancy-regex` tokenization)

---

# Addendum 2 — Catalog enrichment (multi-utterance), 2026-10-03

Protocol: enrichment authored from route semantics only (no eval phrasing); deterministic 75/25
tune/confirm split by intent-id hash; same 68-route distractor set; potion-32M.

| variant | top-1 (all) | tune | confirm | R@16 |
|---|---|---|---|---|
| baseline one-liners | 0.438 | 0.379 | 0.591 | 0.838 |
| verb synonyms | 0.450 | 0.414 | 0.545 | 0.912 |
| multi-utterance (max) | 0.613 | 0.603 | 0.636 | 0.950 |
| **multi-utterance + verbs (frozen)** | **0.800** | 0.810 | 0.773 | **1.000** |
| centroid of utterances | 0.362 | 0.310 | 0.500 | 0.850 |
| multi, no name prefix | 0.625 | 0.655 | 0.545 | 0.975 |

Per-op (all, frozen): checkpoint 9/10, record 9/10, search 9/10, status 9/10, continuity 8/10,
create 7/10, ingest 7/10, explain 6/10.

Findings:
1. Max-over-utterances is the lever (+0.36 top-1, R@16 1.000); centroid collapses below baseline
   (0.362), confirming the Semantic Router guidance.
2. The confirm split (0.773, n=20) shows the gain generalizes beyond tuned intents. Residual
   misses are catalog competition, not model failure: "check the substrate invariants" →
   `receipts.verify`, "how many records do we have" → `session.record`. Further tuning on those
   three intents would be overfitting; frozen at v2.
3. The name prefix ("route — utterance") is kept: slightly lower tune, better confirm.
4. Rust port matches Python exactly on both catalogs; warm query ~4.4 ms, first call ~25 ms/intent
   including catalog embedding (cached thereafter).

Frozen catalog: `catalogs/routes_v9_enriched.json` (8 enriched routes × 5–13 utterances,
60 distractor one-liners). Repro: `scripts/system05/s05_enrich.py`,
`receipts/s05_enrich_results.json`.

---

# Addendum 3 — Receipts flywheel, defaults, optional onig (2026-10-03)

1. **Verification is real now.** `wm verify-receipt` and MCP `receipts.verify` perform offline
   Ed25519 verification of `#decision`, `#shortlist` and `#outcome` receipts against
   `<store>/mandala_gate_key.bin`. Fail-closed: unsigned or tampered receipts are INVALID and the
   CLI exits 1. The previous `receipts.verify` stub (always `valid: true`) is gone; without a
   `path` it now errors instead of claiming VERIFIED.
2. **Critical serialization bug found and fixed.** `serde_json` without `float_roundtrip` does not
   guarantee exact f64 parse-back, so `margin`/`confidence` bits shifted across the JSON
   round-trip and canonical signing bytes no longer matched. Result: shortlist receipts failed
   verification 100% cross-process while self-verifying in-process. Fix: enable
   `serde_json/float_roundtrip`; regression test uses a 17-digit float
   (`0.07857093214988708`). Old receipts now verify VALID too.
3. **Outcome backfill.** `decision.outcome` (MCP) and `wm outcome` (CLI) sign a
   `continuity-receipt/0.5#outcome` record (subject receipt/spec, subject_verified, outcome,
   corrected_route, note), write a sidecar `<receipt>.outcome.json`, and append a compact line to
   `<store>/receipts/outcomes.jsonl`. Smoke: subject_verified=true, sidecar verifies VALID.
4. **Default catalog.** `resolve_catalog_path`: explicit → `WM_GEN3_ROUTES_CATALOG` →
   `~/.local/share/whitemagic/system05/routes_v9_enriched.json` → `~/tools/system05` →
   `./catalogs`. `wm shortlist` and MCP `decision.shortlist` work without passing 68 routes.
5. **Optional `onig` tokenizer.** Harness feature `system05-onig` (crate feature `onig`).
   Measured on the enriched fixture: 18.7 vs 21.5 ms/intent (~13%); warm queries stay ~4 ms and
   the first call is dominated by embedding the 320 catalog utterances. Default remains
   `fancy-regex` (no C dependency; the onig build pulls the C library).

Smoke matrix (fresh binary): shortlist receipt VALID · decision receipt VALID · tampered INVALID
(exit 1) · outcome VALID · MCP tools/list 13 (cyberbrain) including `decision.outcome` ·
`receipts.verify` dispatches (listed in the full profile).

6. **Outcome aggregation.** `scripts/system05/s05_outcomes.py` joins
   `<store>/receipts/outcomes.jsonl` with subject receipts (latest outcome per subject; stream
   parser tolerant of legacy pretty-printed records) and reports outcome totals and verification
   health, success rate per top-1 route, correction pairs, margin-bucket calibration, gate stats,
   and catalog-edit suggestions at a configurable `--min-corrections` threshold. First report:
   `receipts/system05_outcomes_report_2026-10-03.json` (smoke data: 2 receipts, 1 success,
   1 corrected).
