# Retrieval Development Plan

**Started:** 2026-08-17
**Status:** Phase 0 and the first Phase 1 A/B are complete; selective ranking is next
**Scope:** Improve v5 memory retrieval accuracy and practical usability without
expanding the product surface.

## Objective

Improve useful recall for coding-agent memory while preserving the v5 promise:

> Local-first memory and session continuity with explicit, inspectable behavior.

The current measured baseline is the token-coverage-aligned release path:

- 50-question turn-level R@1: `0.64`
- R@5: `0.82`
- R@10: `0.82`
- MRR: `0.7150`
- Query p50: approximately `56 ms`
- Ingest average: approximately `2.6 s` per question

These are retrieval metrics, not official LongMemEval QA accuracy.

## Decisions Already Made

- Keep `memory.search` as the public retrieval route.
- Keep BM25 as the honest no-endpoint default.
- Keep hybrid vector recall optional behind `WM_EMBEDDER_ENDPOINT`.
- Keep explicit routing as the reliable MCP contract.
- Do not add naive duplicate composite memories.
- Do not apply blanket content/tag field boosts.
- Do not port large cognitive or archive features during this slice.

## Phase 0: Continuity and Evaluation Contract

Before modifying retrieval:

1. Call `session.continuity` and `memory.search` for this plan.
2. Read this plan, `docs/ARCHIVE_FINDINGS.md`, and the current roadmap.
3. Run the baseline benchmark with a fresh store.
4. Keep ingest and query timing separate.
5. Record candidate presence separately from final rank.

The evaluator now retrieves a broad candidate set and reports candidate
presence, answer-text evidence, and expected-session evidence independently.

The evaluator should distinguish:

- The answer-bearing turn entered the candidate set.
- The answer text appeared in a retrieved result.
- The answer-bearing result reached ranks 1, 5, or 10.
- The answer came from the expected session.

## Phase 1: Contextual Search Representation

Add an auxiliary search representation without duplicating user-visible
memories:

- Preserve one canonical memory ID and original content.
- Store session ID, turn index, role, and neighboring-turn context as indexed
  search metadata or a non-returned search field.
- Add deterministic fact/date keys where extraction is reliable.
- Keep the returned result tied to the canonical turn.
- Make the feature opt-in during evaluation until the A/B result is clear.

The first A/B should compare current turn-only indexing against contextualized
indexing on the same 50-question protocol.

The first A/B completed 2026-08-17. Adjacent-turn terms in indexed tags raised
candidate presence from `0.78` to `0.80`, but reduced R@1 from `0.64` to `0.54`
and R@5 from `0.82` to `0.80`. This tag-based representation is rejected;
context should not be added without selective scoring or reranking.

## Phase 2: Candidate and Reranking Paths

**Research update (2026-08-19):** See `docs/RETRIEVAL_RESEARCH_ROADMAP.md`
for research findings that reshape this phase. Key finding: on LongMemEval-S
(a lexical regime), cosine reranking and cross-encoder reranking do not
improve R@1. The path forward is storage-time vocabulary enrichment and
session-aware RRF, not neural reranking.

Only after Phase 1 has candidate evidence:

- Keep BM25 candidate generation fast and broad enough for recall.
- Use vector fusion when a real embedder is configured.
- Add an optional reranking stage over a bounded candidate set.
- Keep reranking unavailable rather than silently required when no local model
  exists.
- Measure p50, p95, candidate count, and memory footprint alongside R@k.

The likely implementation order is deterministic scorer first, real hybrid
comparison second, optional cross-encoder or late-interaction research third.

## Phase 3: Query Classes

Analyze remaining misses by class before adding general intelligence:

- Temporal questions: date normalization and time-aware expansion.
- Counting questions: structured aggregation rather than retrieval alone.
- Preferences and paraphrases: semantic candidate expansion or reranking.
- Adjacent-turn answers: contextual search representation.
- Abstention: preserve empty-result behavior for unsupported or irrelevant
  queries.

Each class gets its own regression cases and must not be hidden by an aggregate
score.

## Acceptance Gates

A retrieval change is accepted only if it:

- Improves R@1 or R@5 on the fixed 50-question set, or closes a documented
  complete-miss class.
- Does not reduce R@5 without a clearly documented tradeoff.
- Keeps BM25-only query p50 below `100 ms` on the current benchmark machine,
  unless the feature is explicitly optional.
- Passes the relevant crate tests, Clippy, formatting, and curated smoke test.
- Preserves privacy filtering, read-only behavior, transaction semantics, and
  canonical memory IDs.
- Writes a dated result and rationale to `docs/ARCHIVE_FINDINGS.md`.

## Explicitly Deferred

- Full RAPTOR-style recursive summaries.
- ColBERT or other multi-vector production indexing.
- Broad v26 tool porting.
- Automatic LLM-generated context for every memory write.
- Naive duplicate composite documents.
- Official LongMemEval QA claims until the evaluator is aligned with the paper.

## Continuity Protocol

At the start of each development session:

1. Call `session.continuity` with `n=10`.
2. Call `memory.search` for `WMv5 retrieval development plan`.
3. Read this plan and the archive findings log.
4. Start a named session with `session.start`.

During work:

- Record decisions with `session.record` using `turn_type=decision`.
- Record breakthroughs with `turn_type=breakthrough`.
- Record failures and benchmark regressions with `turn_type=error`.
- Include paths, commands, metrics, and whether a change was accepted or
  rejected.

At the end:

1. Record a compact `summary` turn with the final metrics.
2. Record a `context` turn containing the exact next command or next phase.
3. Call `session.checkpoint` when a named session exists.
4. Update `docs/NEXT_SESSION.md` and this plan if the next slice changed.
5. End the session cleanly when practical so mutable usage state persists.
