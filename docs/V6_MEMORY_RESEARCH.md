# V6 Agent Memory Research

**Date:** 2026-08-17
**Status:** Research synthesis and proposed experiments
**Scope:** Agentic memory, cognitive architectures, biologically inspired
systems, and implications for a WhiteMagic v6 memory kernel.

## Executive Thesis

Agent memory is not one database and not one context window. The strongest
architecture suggested by the literature is a layered cognitive scaffold:

1. A lossless episodic record of what happened.
2. Typed derived memories for profiles, events, facts, skills, claims, and
   hypotheses.
3. Multiple retrieval structures selected for the current query.
4. Associative expansion that completes evidence around initial anchors.
5. Consolidation that improves access without deleting the source record.
6. A context compiler that emits bounded, cited evidence for the model.
7. Governance that controls provenance, validity, conflicts, deletion, and
   release.

This is a stronger target than "vector search over memories" and maps closely
to several systems already present in WMv5.

## Research Findings

### Cognitive Architecture

- **CoALA** (Sumers et al., 2024) organizes language agents around modular
  memory, structured actions, and decision-making. It supports treating
  working memory, episodic memory, semantic memory, and procedural memory as
  distinct modules rather than one prompt buffer.
- **MemGPT** (Packer et al., 2023) treats context management like an operating
  system: fast context is a working set, while slower storage is paged in and
  out through explicit control flow. This is the closest existing analogy to
  an effectively infinite context window.
- **Generative Agents** (Park et al., 2023) combines observation, planning,
  reflection, and retrieval. Its important lesson is that reflection is a
  derived layer over raw experiences, not a replacement for them.
- **MemoryBank** (Zhong et al., 2023) adds importance-sensitive updating and
  forgetting. The useful idea is selective reinforcement, but its generated
  memory layer needs stronger provenance and conflict handling for engineering
  memory.
- **Reflexion** (Shinn et al., 2023) stores verbal feedback from failed or
  successful attempts and reuses it in later trials. This directly supports
  storing validated failure lessons separately from ordinary conversation.
- **Voyager** (Wang et al., 2023) maintains an executable skill library and
  uses environmental feedback and self-verification to improve skills. A v6
  agent should remember reusable procedures, not only facts and transcripts.

### Retrieval and Evidence

- **LongMemEval** (Wu et al., 2025) identifies five separate abilities:
  information extraction, multi-session reasoning, temporal reasoning,
  knowledge updates, and abstention. Its indexing, retrieval, and reading
  decomposition should become WMv6's evaluation contract.
- **HippoRAG** (Gutiérrez et al., 2025) combines language-model extraction,
  knowledge graphs, and Personalized PageRank. It reports up to 20% gains on
  multi-hop retrieval, with single-step retrieval 10-30x cheaper and 6-13x
  faster than iterative retrieval in its experiments. The applicable idea is
  query-conditioned graph expansion, not a mandatory graph for every memory.
- **GraphRAG** (Edge et al., 2025) uses entity graphs and community summaries
  for global questions. It is most relevant for questions about themes,
  projects, or an entire corpus, where ordinary top-k retrieval is the wrong
  operation.
- **ReFind** (Li et al., 2026 preprint) leaves raw chat logs unchanged and
  gives an agent iterative lexical search, temporal narrowing, session-aware
  fusion, and local context expansion. Its reported LongMemEval-S/M scores
  are 93.2 +/- 3.3 and 89.3 +/- 6.0 with GPT-5-mini. This is an important
  counterweight to overbuilding structure: controllable search over raw logs
  can be highly competitive.
- **RippleMem** (Ji et al., 2026 preprint) starts with hybrid anchors and
  expands through an event-centric graph using semantic and structural cues.
  It reports up to 11.87% improvement on LongMemEval-S and about 30x lower
  graph construction cost. This closely matches WMv5's association and
  spreading-activation foundations.
- **MESA** (Zhao et al., 2026 preprint) selects a query-specific combination
  of several memory structures instead of always using one structure or all
  structures. It reports 8.5% improvement with 41% fewer evidence tokens than
  the all-structure alternative.
- **LeanMem** (Liao et al., 2026 preprint) routes different information into
  profile, event, or source-grounded record memory, then allocates retrieval
  budgets per query. It reports improvements up to 15.1 points with low
  construction and inference cost.
- **ERSkill** (Chen et al., 2026 preprint) treats retrieval policies as
  executable skills, routes queries to skills, and evolves those skills behind
  a stable deployment frontier. It reports 28.1-31.3% aggregate improvement
  across its reported metrics and models. The safe promotion mechanism is more
  applicable to WMv6 than unconstrained self-modification.

### Consolidation and Memory Evolution

- **MemoryOS** (Kang et al., 2025) uses short-term, mid-term, and long-term
  storage with explicit migration and segmentation. It reports large LoCoMo
  gains, but the key architectural lesson is tiered lifecycle management.
- **LycheeMemory V2** (Li et al., 2026 preprint) consolidates semantic
  segments rather than every turn and stores typed, context-independent
  records. It reports 92.20% on LongMemEval-S and 75.9% fewer construction
  tokens than A-MEM in its setup. This is directly relevant to WMv5's costly
  ingest path.
- **A-MEM** (Xu et al., 2025) dynamically creates linked Zettelkasten-like
  notes and evolves existing representations as new memories arrive. The
  useful part is dynamic linking; eager LLM rewriting of old memories should
  not be the v6 default.
- **MemSIF** (Luo et al., 2026 preprint) separates topical segments and event
  trajectories from two fact tracks: stable CoreFact and demand/source-backed
  ActiveFact. It reports 2.87-6.15% LongMemEval-S gains over its strongest
  baseline. This is a strong model for avoiding premature fact promotion.
- **TEPA** (Zhou et al., 2026 preprint) makes validity explicit and revokes
  stale precedents while retaining them for audit. In its controlled reversal
  task it reports 0.950 versus 0.210 for append-only and last-write-wins
  memory. v6 must support supersession and retraction as first-class state.
- **Controlled Memory Interference** (Ding et al., 2026 preprint) shows that
  memory evolution fails through authority and interference conflicts, not only
  through scale. It specifically finds different interference paths for
  lexical and dense retrieval.
- **Governed Persistent Memory** (Xu, 2026 preprint) formalizes bitemporal
  state, source binding, conflict isolation, non-revival after deletion, and
  fail-closed release. Its contract tests are reported as 3,600/3,600 and its
  governed service arm as 2,400/2,400, but these are bounded contract claims,
  not open-world truth claims.

### Biological and Continual-Learning Foundations

- **Complementary Learning Systems** (McClelland, McNaughton, and O'Reilly,
  1995) distinguishes rapid hippocampal learning from slower neocortical
  integration. For v6 this means fast episodic admission plus delayed,
  replay-based semantic consolidation.
- **Hippocampal Memory Indexing Theory** (Teyler and DiScenna, 1986; updated
  by Teyler and Rudy, 2007) treats the hippocampus as an index that can use a
  partial cue to reactivate distributed cortical representations. This maps to
  anchor retrieval followed by associative completion, not to storing one
  monolithic summary.
- **Carousel Memory** (Lee et al., 2022) preserves overflowed episodic data in
  slower storage instead of discarding it. This supports a hot/cold memory
  hierarchy where slow archival storage remains recoverable.
- **Memory-augmented neural networks** (Santoro et al., 2016) demonstrate
  rapid one-shot writes to an external memory. The practical v6 lesson is to
  keep new evidence writable without forcing immediate parameter updates.
- **Titans** (Behrouz et al., 2024/2025 preprint) explores learned neural
  memory alongside short-context attention and reports experiments beyond 2M
  context positions. It is a research adapter candidate, not a replacement for
  an inspectable source-grounded memory substrate.

Biological analogies should constrain architecture and inspire tests, not be
treated as proof that an implementation is cognitively equivalent to a brain.

## Mapping to WMv5

| WMv5 capability | Research alignment | V6 change |
|---|---|---|
| LMDB memories and galaxies | Episodic store, MemoryOS tiers | Preserve a lossless canonical event lane and add typed derived lanes |
| Tantivy BM25 and optional vectors | LongMemEval indexing/retrieval | Add query planning and multi-index evidence union |
| Typed associations and Hebbian weights | HippoRAG, RippleMem, hippocampal indexing | Add bounded query-conditioned associative expansion |
| Spreading activation | Associative completion | Replace fixed expansion with learned or calibrated query budgets |
| DreamCycle with 12 phases | Reflection and consolidation | Make semantic segments, replay, and lifecycle transitions explicit |
| RetentionEngine and decay | MemoryBank and continual learning | Never delete source evidence by default; separate decay, archive, revoke, and erase |
| ContextOptimizer | MemGPT working-set management | Add evidence coverage, contradiction handling, citations, and query-specific budgets |
| LearnedRouter and mutable structures | ERSkill and MESA | Evolve retrieval policies in shadow mode with safe promotion |
| Self-play and improvement tools | Reflexion and Voyager | Store verified failure lessons and executable skills as separate memory types |
| Claims ledger, Dharma, transactions | Governed Persistent Memory | Add bitemporal validity, source-bound claims, retraction, and fail-closed release |
| Imagination and scenario engine | Planning and reflection | Ground scenarios in cited evidence and record counterfactual provenance |

The v26 systems already contain many good primitives: working memory,
associations, gardens or namespaces, dream consolidation, resonance, semantic
coordinates, retention, and autonomous cycles. The problem is not a lack of
ideas. The problem is that their state semantics and retrieval contracts are
not yet unified into one evidence pipeline.

## Proposed V6 Memory Kernel

### 1. Canonical Episodic Lane

Every observation, tool result, decision, error, and user statement is stored
immutably with a canonical ID, session, timestamp, source, authority, and
provenance. Derived memories reference these records instead of replacing
them.

### 2. Typed Derived Lanes

Use separate records for profile, event, fact, skill, claim, hypothesis,
procedure, and summary. Maintain stable facts separately from active,
query-demanded facts. This combines MemSIF, LeanMem, Reflexion, and Voyager
without forcing every turn through the same summarizer.

### 3. Index Mesh

Maintain lexical, dense, temporal, entity, graph, session, and skill indexes.
Use reciprocal-rank fusion or calibrated score fusion only after measuring
each source. Keep a raw-log search lane permanently available as a fallback.

### 4. Recall Planner

Classify the query into retrieval modes such as exact fact, temporal, update,
multi-hop, global summary, procedural, or failure-recovery. Select the minimum
useful index set, retrieve broad candidates, expand associations only when
needed, and stop when evidence coverage is sufficient.

### 5. Evidence Compiler

Build a context pack containing source snippets, derived facts, links,
timestamps, confidence, contradictions, and citations. The answer model must
be able to distinguish observed source text, derived interpretation, stale
memory, and speculation.

### 6. Consolidation Scheduler

Use semantic segment boundaries rather than per-turn LLM consolidation. Run
fast admission synchronously, then consolidate in background or dream cycles.
Replay high-surprise, high-error, high-utility, and conflicting episodes first.

### 7. Lifecycle Governance

Represent memory state transitions explicitly: active, superseded, revoked,
archived, private, excluded-from-model, and erased. A revoked memory remains
auditable but cannot support a current answer. Conflicts should fail closed
when authority or temporal validity cannot resolve them.

## Prioritized Experiments

1. **Raw-log agentic retrieval:** Add iterative lexical search, temporal
   narrowing, local context expansion, and session-aware fusion. Compare it to
   the current single-shot BM25 path before adding more structure.
2. **Associative completion:** Use WMv5 associations and spreading activation
   to expand from top anchors. Measure whether supporting evidence enters the
   candidate set without contaminating rank.
3. **Typed semantic segments:** Build sidecar topical segments, event
   trajectories, stable facts, and active facts while preserving canonical
   turns. Measure construction cost and answer-supported accuracy.
4. **Query-adaptive structure selection:** Route among raw, lexical, dense,
   temporal, graph, and skill views using the existing learned-router shadow
   machinery.
5. **Conflict and revocation suite:** Add tests for changed preferences,
   superseded files, contradictory authorities, deletion, stale summaries,
   and memory poisoning.
6. **Evidence and cost benchmark:** Add multi-hop, global-summary, update, and
   abstention tasks; measure accuracy, candidate recall, evidence tokens,
   ingest cost, query latency, and false-recall rate together.

## Acceptance Gates

A v6 memory change should not ship unless it satisfies all applicable gates:

- Candidate presence improves or a documented complete-miss class closes.
- R@5 does not regress on the fixed v5 50-question set.
- Answer-supported accuracy and abstention are measured separately from rank.
- Source IDs and provenance survive consolidation and migration.
- Superseded or revoked memories cannot support current claims.
- Raw source evidence remains recoverable after derived-memory failure.
- Offline mode makes no network calls.
- Private and model-excluded records do not enter MCP or model evidence.
- Query p50 and p95 remain within declared local SLOs.
- Every learned retrieval policy is evaluated in shadow mode before promotion.

## Sources

- [CoALA](https://arxiv.org/abs/2309.02427)
- [Generative Agents](https://arxiv.org/abs/2304.03442)
- [MemGPT](https://arxiv.org/abs/2310.08560)
- [MemoryBank](https://arxiv.org/abs/2305.10250)
- [Reflexion](https://arxiv.org/abs/2303.11366)
- [Voyager](https://arxiv.org/abs/2305.16291)
- [LongMemEval](https://arxiv.org/abs/2410.10813)
- [HippoRAG](https://arxiv.org/abs/2405.14831)
- [GraphRAG](https://arxiv.org/abs/2404.16130)
- [A-MEM](https://arxiv.org/abs/2502.12110)
- [MemoryOS](https://arxiv.org/abs/2506.06326)
- [Titans](https://arxiv.org/abs/2501.00663)
- [Carousel Memory](https://arxiv.org/abs/2110.07276)
- [RippleMem](https://arxiv.org/abs/2608.13334)
- [LycheeMemory V2](https://arxiv.org/abs/2608.12990)
- [ReFind](https://arxiv.org/abs/2608.12888)
- [EgoCITE](https://arxiv.org/abs/2608.12627)
- [LeanMem](https://arxiv.org/abs/2608.03463)
- [ERSkill](https://arxiv.org/abs/2608.12720)
- [MESA](https://arxiv.org/abs/2608.10108)
- [TEPA](https://arxiv.org/abs/2608.07429)
- [Controlled Memory Interference](https://arxiv.org/abs/2608.07622)
- [MemSIF](https://arxiv.org/abs/2608.01742)
- [Governed Persistent Memory](https://arxiv.org/abs/2608.12476)
- [SuperLocalMemory 4.0](https://arxiv.org/abs/2608.08253)
- [Total Recall at What Cost?](https://arxiv.org/abs/2608.11879)
- [Complementary Learning Systems](https://doi.org/10.1037/0033-295X.102.3.419)
- [Hippocampal Memory Indexing Theory](https://doi.org/10.1037/0735-7044.100.2.147)
- [Hippocampal Indexing Theory update](https://doi.org/10.1002/hipo.20350)

The 2026 papers listed here are arXiv preprints unless their entry states a
published venue. Their reported gains are useful hypotheses for WMv6
experiments, not claims about WhiteMagic performance.
