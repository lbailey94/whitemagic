# Phase 1 — Experiment Interface (harness ↔ Gen3 arm)

**Status:** working draft · 2026-09-16 · read from WMv9 `HEAD cff34a0` (9.1.7 facts cited; HEAD noted where it differs) ·
**not binding until referenced by the pre-registration at freeze.** Companion: `PHASE1_CONTRACTS.md`.

Purpose: pin exactly how the Phase-2 A/B drives each arm, what the Gen3 adapter must speak, how
corpus material maps into the substrate, which harness outputs feed which pre-registered metrics
— and which metrics need instrumentation the stock harness does not produce. This is the
unblocking artifact for the implementation session: if the adapter satisfies this document and
`PHASE1_CONTRACTS.md`, the identical harness can score both arms.

Evidence base: `benchmarks/../scripts/memorastrict_bench.py` (1,060 lines) and
`scripts/eval_protocol.py` (340 lines), read end-to-end 2026-09-16; fixtures
`benchmarks/data/memorastrict/bench_seed{1..5}.json`; generator `scripts/memorastrict_gen.py`;
control-side semantics read (not imported): `crates/wm-memory/src/episodic.rs`,
`crates/wm-tools/src/expansion/memory_ops.rs`.

---

## 1. How the harness runs an arm

Per scenario seed (5 seeds → `bench_seed{1..5}.json`, 43 questions each):

1. `run_server_batch()` spawns the arm binary once and pipes **newline-delimited JSON-RPC** on
   stdin, reading JSON-RPC lines from stdout (`memorastrict_bench.py:159-192`).
   Command: `<binary> serve --store <tmpdir> --profile full --max-requests 0 --rate-limit 0`,
   env `WM_DISPATCH_GLOBAL_RPM=0 · WM_DISPATCH_TOOL_RPM=0 · WM_DISPATCH_BURST=0`.
2. **Ingest batch**: `initialize` (id 1) → `wm` route `sandbox.set_limits`
   (id 2, args: `max_writes_per_minute:100000`, `max_spawns_per_minute:100000`,
   `max_network_per_minute:100000`, `max_repeats:100000`, `require_human_review:false`) →
   `wm` route `memory.batch_create` in ≤60 KB JSON chunks (ids 3..N), each item
   `{content, galaxy:"codex", tags:[role, session_id, maybe "has_answer"]}`.
   Audited: every batch_create response must carry `payload.status == "success"` and an `ids`
   array **in input order** (the harness builds `memory_session_ids` from it; ℹ️ scoring
   depends on ids round-tripping).
3. **Per question**: a *fresh process* is spawned containing **only** the single `tools/call`
   request for `wm` route `memory.episodic_search` (no `initialize`), args
   `{query, limit, candidate_limit, include_historical:false, [min_score], [min_coverage]}`;
   T10 questions use route `memory.aggregate` instead. Timeout 120 s (ingest 600 s).
   Audited: response must decode to `result.content[0].text` JSON with a **`results` list**
   (or `memories`) — `eval_protocol.py:212-253`. Status may be absent or `"success"`;
   an error or missing list invalidates the whole run (`valid_execution:false` → exit 2).
4. Cleanup: temp store deleted. Result JSON + run manifest (runner/binary/dataset hashes, git
   state) written per seed (`memorastrict_bench.py:996-1030`).

**Consequences for the Gen3 arm:**

| # | Requirement | Why |
|---|---|---|
| I1 | `serve` subcommand accepting the four flags (semantics per §3) | exact command line is part of the frozen invocation |
| I2 | stdio JSON-RPC envelope: `{"jsonrpc":"2.0","id":N,"result":{"content":[{"type":"text","text":"<json>"}]}}` | `parse_jsonrpc_payload` |
| I3 | `initialize` answered harmlessly (result ignored) | harness sends it first |
| I4 | `tools/call` without prior handshake | fresh per-query processes send no initialize |
| I5 | Durable store: every query process reopens the same `--store` directory | single-run ingest + per-query processes |
| I6 | `memory.batch_create` → `{status:"success", ids:[…]}` ids stable and ordered | strict scoring + session mapping |
| I7 | `memory.episodic_search` → `{results:[{id, content, score,…}]}`; `results:[]` on abstention (never omit the list) | audit + T2 scoring |
| I8 | numeric `score` per result on a scale where "no relevant hit" < 0.01 | `strict_abstention` / `verify_abstention` |
| I9 | no crash on unknown routes/flags; unknown → JSON-RPC error is tolerable, malformed stdout is not | harness raises on non-JSON lines |

## 2. Route → operation mapping (interface, not behavior)

| Harness call | Gen3 surface | Notes |
|---|---|---|
| `initialize` | no-op ack | harness ignores result |
| `wm`/`sandbox.set_limits` | statutes: resource budgets | implement genuinely (persist or apply per-process); do **not** no-op silently |
| `wm`/`memory.batch_create` | `remember` (batch) | one evidence record per item; returns ids in order |
| `wm`/`memory.episodic_search` | `recall` | args: `query`, `limit`; `include_historical:false` → **current-preferred ranking** (historical records retained, ranked below current — never silently dropped; semantics pinned in `PHASE1_CONTRACTS.md` §2.2); `candidate_limit`, `min_score`, `min_coverage` honored as selection thresholds |
| `wm`/`memory.aggregate` (T10 only) | `recall` + aggregation over relations | only needed if T10 is in the frozen category set; pre-reg scopes primary/secondary without T10 |

**Fairness rules.** (a) The mapping is name-shimming; no Gen2 behavioral machinery may be
imported (manifest §3). (b) `--profile full`, `--max-requests 0`, `--rate-limit 0` are accepted;
Gen3 statutes may cap internally only within values the pre-reg pins as identical. (c) The
control arm runs the frozen binary on the same script; the only difference is `--binary` and the
store directory. (d) The adapter lives in `crates/wm-gen3-harness` (per `SCAFFOLD_STRATEGY.md` §3)
and is excluded from the A/B's *capability* comparison — it is plumbing, and it must be hash-
pinned per run in the receipts.

## 3. Corpus mapping (epistemic honesty)

| Corpus element | Gen3 representation |
|---|---|
| Session turn content | evidence record: `class = evidence`, `domain = reported` (authored scenario data — **never** `world`) |
| `tags:[role, sid, "has_answer"]` | import metadata: session id + role retained as source refs; `has_answer` is corpus provenance, not a retrieval hint |
| `galaxy:"codex"` | accepted as a scope label; no behavioral effect in Phase 1 (single substrate) |
| Duplicate/stale turns | ordinary records; current-state resolution emerges from relations + selection, not from ingest-time filtering |

Rationale: domain gates *creation/promotion* of evidence, not *retrieval* (Charter §3.8 v0.1.1 —
domains immutable, world-intake via ratified channel only). T8/T1 questions are answerable from
`reported` evidence; H5's laundering canary stays meaningful.

## 4. Scoring map (pre-reg metrics → harness outputs)

Stock harness produces, per question: `verified` (legacy protocol), `recall_at_1/5`, `mrr`,
`first_match_rank`, `candidate_count`, latency, plus strict evidence fields for `exact` questions.

| Pre-reg | Metric | Source | Status |
|---|---|---|---|
| H1 | T8 per-question pass | legacy `verified` (vtype `set`: both conflicting terms in top-10 contents) | ✅ stock |
| H2 | T1+T6 per-question pass | legacy `verified` (vtype `supersession`: current-value turn at rank 1) | ✅ stock |
| H7 | latency, ingest throughput | `latency.p50/p95`, `ingest` | ✅ stock (peak memory: see §5) |
| H4 | provenance retention | Gen3 run journal (§5) | ⚠ instrumentation |
| H5 | laundering canary | Gen3 violation log + canary probe results | ⚠ instrumentation |
| H6 | constitutional violations | Gen3 violation log | ⚠ instrumentation |
| H3 | false-conflict rate | **neither arm exposes a stock conflict-report surface** | ⚠ decision needed (§6) |
| H8 | emergent useful structure | journal + ablated variant runs | ⚠ instrumentation |

Notes from fixture inspection (2026-09-16): T8 answers are `"CONFLICT: was {old}, now {new}"`
with `verification_type:"set"`; after the common-word filter the required terms are
`{old_label, new_item}` (e.g. `vegetarian` + `steak`) — both must appear in the top-10 contents
across the two planted sessions (`memorastrict_gen.py:822-865`). T1 answers are persona
preference values; pass requires the current value's *session* at rank 1 (`verify_supersession`,
`memorastrict_bench.py:276-308`). T6 = T1 questions relabeled under budget
(`memorastrict_gen.py:752-763`). T2 abstention passes iff no results or top-3 scores < 0.01
(`verify_abstention:263-273`).

## 5. Required instrumentation (Gen3-side, Phase 2)

The stock harness cannot observe H3–H6/H8. The Gen3 arm therefore emits a **run journal** per
scenario (one file per run, written to the run directory, hash recorded in the result manifest):

1. **Violation events** — schema from `CLOSURE_TESTS.md` §3 (`{ts, path_attempted, mechanism,
   refused_by, receipt_id}`); zero-tolerance accounting for H6.
2. **Laundering canary results** — per-question: planted simulated canary id, observed domains,
   any promotion attempt (`H5`).
3. **Relation (candidacy) ledger** — every relation proposed during the run: kind, endpoints, rule id,
   score components, promotion state, and its contribution record (path → structures → transformation
   → outcome). "Conflict" is a derived analytic label (co-referent incompatible values), not a second
   stored ontology; the journal stores candidates, and H3/H8 counts are computed from it.
4. **Provenance chains** — for each returned result: chain reconstructable to ingested record
   (`H4` requires 100%).
5. **Structure inventory** — recurring structures promoted during the run, with the six-condition
   evidence fields; ablated variant runs use the same journal so "improves outcome vs ablation"
   is computable.

Peak memory (H7): wrap each arm's full-seed run in `/usr/bin/time -v` (max RSS) — per-process
harness runs make per-query memory less meaningful; report both max RSS and total elapsed.

## 6. Pinned configuration (to freeze in the pre-reg) and open decisions

To pin at freeze: seeds `1 2 3 4 5`; categories `T8 T1 T6` (+ guardrails `T2 T9` if run);
`--limit 10`; `--candidate-limit 100`; `--min-score 0`; `--min-coverage 0`; **no** `--bm25-only`
(control keeps its episodic route; Gen3 is model-free by construction); timeouts as stock;
control binary hash from the freeze receipt; Gen3 binary hash per run.

Open decisions before freeze (draft-stage, metric-safe):

1. **H3 false-conflict rate** — no control-side conflict surface exists, so a symmetric metric is
   not measurable. Options: (a) Gen3-only informational metric via the journal, control side
   reported "not measurable"; (b) drop H3 from pass/fail and record it as a qualitative finding;
   (c) define a behavioral proxy in T1 (any non-current pairing surfaced as conflict degrades
   ordering). Recommendation: (a)+(b).
2. **Score convention** — Gen3 recall must define its score scale now (requirement I8); pin it in
   `PHASE1_CONTRACTS.md`, not ad hoc in code.
3. **Smoke run** — propose a non-scored smoke run of both arms on seed 1, categories `T8`,
   declared as non-evidence (receipt records the runs; result files marked `smoke: true`).
4. **Guardrails in the scored run** — run `T2` (abstention) as a guardrail category in both arms
   for comparable failure accounting, or keep guardrails unscored? Recommendation: run T2 (cheap,
   meaningful abstention parity) and leave T9 out of the scored invocation.
