# WhiteMagic Archive Findings

**Started:** 2026-08-16
**Status:** Living research log
**Scope:** Historical WhiteMagic source, WMdocs, WMdata, benchmarks, and
conversation exports. This document records evidence and recoverable
inspiration, not commitments to expand the v5 product surface.

## Working Rules

1. Prefer evidence over feature nostalgia. Mark claims as verified,
   plausible, or speculative.
2. Diff historical implementations before proposing a port.
3. Preserve the v5 product cut: local-first memory and session continuity.
4. Recover tests, measurements, schemas, and wiring lessons before recovering
   large feature surfaces.
5. Never re-ingest or modify archived stores without a snapshot and an
   explicit migration plan.

## Source Map

| Source | Role | Initial assessment |
|---|---|---|
| `WMdocs/` | Consolidated documentation vault | Canonical index, chronology, architecture, handoffs |
| `WMdata/` | Runtime and archive data vault | v5 live store plus v26/v4 cold generations |
| `WHITEMAGIC/` | Retired v26 Python reference | Source, tests, benchmarks, polyglot bridges |
| `WMdocs/whitemagic-v4/` | Superseded Rust v4 | Direct architectural predecessor to v5 |
| `CODEX_VAULT/` | Conversation and internal archive | Design receipts, sessions, memory databases |

## High-Confidence Findings

### 1. The archive has a coherent lineage

**Status:** High-confidence interpretation. The chronology also contains
reconstructions and aspirational summaries, so not every historical statement
is independently verified.

The project can be read as three useful eras:

- Live substrate era: real event logs, memories, embeddings, dream cycles,
  resonance, and self-monitoring.
- Polyglot platform era: v17/v26, large tool catalog, 28 Ganas, governance,
  cognitive systems, and benchmark harnesses.
- Rust consolidation era: v4 and v5, smaller native runtime, explicit MCP
  boundary, stronger release gates, and a narrower product cut.

Evidence: `WMdocs/docs/WHITEMAGIC_CHRONOLOGY_2026-06-20.md`,
`WMdata/README.md`, `WHITEMAGIC/README.md`.

### 2. WMdata is the migration authority

**Status:** Verified for the v26 and v4 runtime generations. This does not
mean that all CODEX_VAULT documents or conversation exports have already been
ingested into v5.

`WMdata/live` contains the current v5 store. The v26 SQLite and v4 LMDB
generations remain intact as cold archives. Existing migration notes say the
WM-native runtime data was already migrated, so old databases should be used
first for verification and gap analysis, not blindly re-ingested.

Evidence: `WMdata/README.md`, `WMv5_ORGANIZATION_INGESTION_PLAN.md`,
`WMdocs/docs/message_board/WMV5_ANALYSIS.md`.

### 3. Wiring is the recurring historical failure mode

**Status:** Verified case study. Calling it a recurring project-wide failure
mode is an engineering generalization, not a quantified claim.

The v22.2 recovery showed that many subsystems and tests existed but were not
reachable through the dispatch path. A single missing Gana bridge caused a
large apparent failure. The archive's strongest engineering lesson is:

> A feature is not complete until it is reachable through the real dispatch
> path and covered by an integration test.

Evidence: `WMdocs/docs/message_board/CHRONOLOGICAL_READING_LOG.md`,
`WMdocs/docs/message_board/WMV5_HANDOFF.md`.

## Documented Historical Designs

The following are documented designs or porting candidates, not verified v5
capabilities.

### 4. Retrieval ideas worth comparing with v5

- Distance-gradient accessibility, or memory physics.
- Five-signal retention with protection overrides and archive-not-delete
  semantics.
- HRR/vector/graph/RRF retrieval chains.
- Reconsolidation windows after recall.
- Epistemic labels on memories and claims.

These are candidates for measured comparison, not automatic ports.

Evidence: `WMdocs/docs/message_board/WMV5_HANDOFF.md`,
`WMdocs/docs/message_board/CHRONOLOGICAL_READING_LOG.md`,
`WMdocs/whitemagic-v4/docs/GAP_ANALYSIS.md`.

### 5. Historical benchmarks provide useful baselines

**Status:** The cited 500-question artifact is resolved as hybrid; an older
summary report is stale or mislabeled.

The v26 archive reports LongMemEval-S hybrid results of R@1 0.858, R@5
0.936, and MRR 0.892 over 500 questions. A separate 100k-memory direct FTS5
run over 200 queries reports R@1 0.415 and R@5 0.465. The LongMemEval result
file says `rerank_mode: hybrid`, and the adapter defines hybrid as FastEmbed
candidate filtering followed by cross-encoder reranking. An older benchmark
report labels the same 500-question result "FTS5-only" and "BM25, no
embeddings." The result artifact and adapter are the stronger provenance for
that run; the report should not be used as the method citation until corrected.
None of these runs are directly comparable to current v5 measurements until
datasets, indexing, ranking, and timing boundaries are aligned.

Evidence: `WHITEMAGIC/benchmarks/results/longmemeval_s_hybrid.json`,
`WHITEMAGIC/benchmarks/longmemeval_real_adapter.py`,
`WHITEMAGIC/benchmarks/results/scale_100k_fts5.json`,
`WMdocs/benchmarks/results/BENCHMARK_REPORT.md`.

### 6. Current v5 controlled retrieval baseline

**Status:** Verified run on 2026-08-17 with `target/release/wm`, fresh stores
per question, turn-level retrieval, separate ingest/query timing, and the
non-official R@k protocol used by `scripts/longmemeval_bench.py`.

The 10-question keyword/no-keyword A/B was identical: R@1 `0.40`, R@5
`0.70`, and MRR `0.5083`. Keyword extraction is not a useful improvement on
this sample.

The current 50-question keyword run produced R@1 `0.58`, R@5 `0.72`, R@10
`0.72`, and MRR `0.6383`. The prior v5 50-question baseline was R@1 `0.62`,
R@5 `0.72`, and MRR `0.6667`. Thus recall-at-5 is stable, while first-result
ranking remains the main gap.

The current run is substantially faster: ingest averaged `2.14 s` per
question and query p50 was `54.8 ms`, compared with approximately `53.2 s` and
`2.5 s` in the older run. The current 50-question misses split into 14
complete misses at R@5 and 7 ranking misses where the answer entered the top
five but not the first result. Persistent examples include degree, yoga,
February 14th, aggregation/counting, and preference questions.

Evidence: `scripts/longmemeval_bench.py`,
`benchmarks/results/longmemeval_s_v5_50q_stem.json`, and the dated 2026-08-17
run output recorded during this session.

### 7. Token-coverage alignment improves recall

**Status:** Verified intervention on 2026-08-17.

The coverage filter previously tokenized query terms by whitespace while
tokenizing content by punctuation. Possessives and hyphenated terms could
therefore fail the coverage floor even when the document contained the
corresponding words. Both sides now use the same punctuation-delimited,
stemmed tokenizer and discard standalone one-character fragments.

On the same 50-question keyword run, the fix improved R@1 from `0.58` to
`0.64`, R@5 from `0.72` to `0.82`, and MRR from `0.6383` to `0.7150`. Query p50
remained effectively flat at `55.9 ms`. The remaining errors are 9 complete
misses and 9 rank-2-to-4 misses, making composite/session-window indexing the
next measured candidate rather than an immediate necessity to validate this
fix.

Evidence: `crates/wm-memory/src/search.rs`,
`scripts/longmemeval_bench.py`, and the dated 2026-08-17 token-fix run output.

### 8. Naive composite windows are not a production win

**Status:** Measured and rejected as-is on 2026-08-17.

The benchmark harness added an experimental `--composites` flag that indexes
adjacent two-turn windows beside the original turn documents. On the same
50-question run, composites changed R@1/R@5/R@10 from `0.64/0.82/0.82` to
`0.62/0.80/0.84` and MRR from `0.7150` to `0.6867`. Query p50 increased from
about `56 ms` to `82 ms`. Deeper recall improved, but practical first-result
and top-five quality declined. Do not add naive composite documents to the
production index without a reranking or source-selection strategy.

Evidence: `scripts/longmemeval_bench.py` and the dated 2026-08-17 composite
experiment output.

### 9. Blanket field weighting is not practical

**Status:** Measured and rejected on 2026-08-17.

A content boost of `2.0` with a tag boost of `0.5` produced the same R@1/R@5
and MRR as the tokenizer-fix baseline (`0.64/0.82/0.7150`) while increasing
query p50 from about `56 ms` to `73 ms`. The change was removed. Future
ranking work should score candidate content selectively rather than applying a
blanket field boost.

### 10. Adjacent-term contextual tags improve candidate presence but hurt rank

**Status:** Measured and rejected as-is on 2026-08-17.

The evaluator was hardened to retrieve up to 100 candidates while scoring the
requested top 10, and now reports answer-bearing candidate presence, answer text
evidence, and expected-session evidence separately. On the fixed 50-question
single-session turn-level protocol, the no-context baseline reproduced
R@1/R@5/R@10 `0.64/0.82/0.82`, MRR `0.7150`, candidate presence `0.78`, and
expected-session presence `0.84`. Query p50 was `85.5 ms` under the broader
candidate limit and ingest averaged `2.98 s`.

The first contextualized-indexing prototype added deterministic terms from the
previous and next turn to each canonical memory's indexed tags. It preserved
the canonical memory ID and original returned content, and did not add
duplicate memories. Candidate presence rose to `0.80`, but R@1/R@5/MRR fell to
`0.54/0.80/0.6523`; R@10 stayed `0.82`. Query p50 rose to `95.6 ms` and ingest
averaged `4.37 s`. Expected-session presence was unchanged at `0.84`.

The result confirms that candidate evidence is useful for diagnosing misses,
but broad neighboring terms contaminate lexical ranking. Do not promote this
tag-based representation into the production indexing path. The next ranking
experiment should operate on the broad candidate set with selective scoring or
optional reranking rather than adding more unweighted context terms.

Evidence: `scripts/longmemeval_bench.py`,
`benchmarks/results/longmemeval_s_v5_50q_eval_hardened.json`, and
`benchmarks/results/longmemeval_s_v5_50q_contextual.json`.

## External Retrieval Research

### LongMemEval

The LongMemEval paper defines five long-term memory abilities: information
extraction, multi-session reasoning, temporal reasoning, knowledge updates, and
abstention. It separates memory systems into indexing, retrieval, and reading
stages, and identifies session decomposition, fact-augmented key expansion,
and time-aware query expansion as useful optimizations.

Implications for v5:

- Keep the current turn-level R@k harness explicitly separate from official QA
  accuracy.
- Fix the evaluator so candidate presence, answer substring, and answer-session
  provenance are reported separately.
- Prefer deterministic fact/date keys or query transforms before adding a large
  generative memory layer.

Source: <https://arxiv.org/abs/2410.10813>.

### Contextual Retrieval

Anthropic's contextual retrieval approach prepends concise chunk-specific
context before both BM25 indexing and embedding, then optionally reranks a
larger candidate set. Their report claims a 49% reduction in top-20 retrieval
failures from contextual BM25 plus contextual embeddings, and 67% with
reranking. These are vendor results on different data and are not v5 evidence,
but the design directly addresses our session-context misses without requiring
duplicate result documents.

Source: <https://www.anthropic.com/news/contextual-retrieval>.

### Retrieve then rerank

Sentence Transformers documents the standard two-stage architecture: a fast
bi-encoder or lexical retriever produces candidates, then a cross-encoder scores
the query-document pairs. This is the most practical route for improving the
current rank-2-to-4 errors, provided the candidate set is large enough and the
reranker remains optional for local-only installations.

Source: <https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html>.

### Heavier future directions

ColBERT-style late interaction preserves token-level query-document matching,
which is attractive for the remaining lexical-gap cases, but its multi-vector
storage and indexing cost are inappropriate as the next v5 change. RAPTOR's
recursive summaries are aimed at holistic multi-step reasoning and are likewise
interesting for a research profile, not the immediate memory boundary.

Sources: <https://arxiv.org/abs/2112.01488>,
<https://arxiv.org/abs/2401.18059>.

## Current Recommendation

The next experiment should be **contextualized indexing without duplicate
returned memories**:

1. Keep one canonical memory ID and returned content per turn.
2. Add an auxiliary, non-returned search representation containing session ID,
   neighboring-turn context, role, and deterministic fact/date keys.
3. Retrieve a broader candidate set and record candidate presence before any
   filtering or reranking.
4. Compare lexical-only, hybrid, and optional reranked ordering on the same
   50-question protocol.

This combines the strongest internal and external evidence while avoiding the
measured failure mode of naive composite documents. It also keeps the product
usable without an LLM endpoint by making contextualization deterministic first.

## Immediate v5 Findings

### Fixed: search discovery schema

`memory.search` and `memory.hybrid_recall` worked through explicit routing but
returned an empty `input_schema` in `tools.list`. The shared retrieval tool now
advertises its required `query` field and optional search filters. Unit and
process-level smoke tests cover both public and compatibility routes. The
process-level check inspects the inner `wm(route="tools.list")` registry, not
the outer MCP `tools/list` envelope.

### Resolved: health readings use two intentional models

`gnosis.status` reports two distinct health models. Dharma homeostasis uses a
50/50 CPU and memory score for governance. The substrate Harmony Vector uses
CPU 30%, memory 30%, swap 20%, and thermal state 20%. Repeated samples from
WMv5 5.8.0 against `/home/lucas/Desktop/WMdata/live` were stable, and
`homeostasis.check` agreed with the substrate score. The earlier difference was
therefore a model-labeling issue, not a sampling race or corrupted state.

**Evidence:** repeated samples at `2026-08-17T01:36:19Z` stayed near
homeostasis `0.694` and substrate `0.746` with identical CPU and memory input;
the difference came from swap and thermal terms.

### Resolved: usage statistics survive graceful restart

`tools.usage_report` correctly measured calls made in the same server process.
A controlled writable-store test recorded a successful `memory.search`, closed
the server cleanly, reopened the same store, and recovered the call count.
The persisted file is `lmdb/mutable_tool_stats.json` below the configured store
root. A newly opened empty store correctly reports no usage.

## Session and Environment Notes

### MCP restart

The current OpenCode session's WM connection returned `Connection closed` after
the binary/configuration transition, while direct WMv5 MCP startup and the
OpenCode server listing worked. Restarting OpenCode is required after MCP
configuration changes; one writable server must own a store at a time. A
second `opencode mcp list` invocation can report the writable dev server as
failed because it attempts to start a competing process against the same
Tantivy writer lock; the already-running OpenCode child remains the owner.

## Deferred Archaeology

- Compare v26 retrieval and v5 retrieval on one controlled benchmark harness.
- Audit live-era substrate data without modifying the stores.
- Examine the v17/v26 activation sequence and dream artifacts for tests or
  measurements worth adapting.
- Review the 61-item v5 handoff against current code before considering any
  additional port.
- Inspect historical UI artifacts only after the memory boundary is stable.

## Change Log

| Date | Change |
|---|---|
| 2026-08-16 | Created after initial archive survey; recorded lineage, retrieval baselines, MCP observations, and immediate v5 schema issue. |
| 2026-08-16 | Fixed the public retrieval schema and added regression coverage. |
| 2026-08-17 | Resolved health-model interpretation and confirmed tool-stat persistence across graceful restart. |
| 2026-08-17 | Verified the live MCP bridge and recorded current v5 10q/50q retrieval baselines plus benchmark provenance. |
| 2026-08-17 | Aligned query/content coverage tokenization; 50q result improved to R@1 0.64 and R@5 0.82. |
| 2026-08-17 | Measured naive two-turn composite windows; rejected due to worse R@1/R@5 and higher latency. |
| 2026-08-17 | Measured blanket content/tag field weighting; rejected due to no accuracy gain and higher latency. |
