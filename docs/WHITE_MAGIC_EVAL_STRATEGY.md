# WhiteMagic Evaluation Strategy: Building the Definitive Memory Benchmark

**Version**: 1.0.0
**Created**: 2026-07-16
**Status**: Draft

---

## 1. Problem Statement

Every existing memory benchmark has critical blind spots. The field acknowledges this
but no single benchmark addresses all of them. We propose building **HologramEval** —
a benchmark that combines the strengths of LoCoMo, LongMemEval, BEAM, and the
biological-memory-inspired systems (FadeMem, ZenBrain, SCM) while testing what none of
them do.

### 1.1 What Existing Benchmarks Test

| Benchmark | Scale | Abilities Tested | Key Limitation |
|-----------|-------|-------------------|----------------|
| LoCoMo | 50 conv, 7,512 Q | Single-hop, multi-hop, temporal, open-domain | Saturating; long-context can compete; no write/forget eval |
| LongMemEval-V1 | 500 sessions, 500 Q | Info extraction, multi-session, temporal, knowledge updates, abstention | Chat-only; no agentic trajectories; no isolation test |
| LongMemEval-V2 | 100-498 trajectories, 451 Q | Static state, dynamic state, workflow, gotchas, premise awareness | Web-agent only; no conversational memory; no forgetting |
| BEAM | 100 conv, 2,000 Q | 10 abilities including abstention, contradiction resolution, event ordering | No write quality, no isolation, no token economy |
| PersonaMem | 5-60 sessions, 5,990 Q | Preference tracking, personalization | Narrow ability coverage |

### 1.2 What None of Them Test (The Five Gaps)

Identified independently by Mem0, Mnemoverse, BEAM authors, and the "Memory in the Age
of AI Agents" survey (arXiv:2512.13564):

1. **Memory Write Quality** — Deciding what's worth keeping from mostly-noise input.
   A system that stores everything looks identical to one that stores only what matters
   — until token budgets and latency get involved. No benchmark scores this.

2. **Forgetting, Eviction, and Consolidation** — Real memory systems must forget. They
   must drop stale facts, merge duplicates, and reconcile contradictions. No widely
   adopted benchmark scores these dynamics directly.

3. **Per-User Isolation** — None of the public benchmarks test isolation under concurrent
   multi-user load. Every production system must handle it.

4. **Token Economy Under Realistic Budgets** — A system scoring 92% with 7K tokens is not
   the same product as one scoring 92% with 70K tokens. Most leaderboards ignore this.

5. **Cross-Session Continuity at Production Scale** — LoCoMo tops out at ~35 sessions.
   No benchmark covers a year-long personal assistant running daily.

### 1.3 What Biological Memory Research Tells Us

Recent neuroscience-inspired memory architectures (FadeMem, ZenBrain, SCM, Human-Inspired
Memory Architecture) identify cognitive mechanisms that no benchmark tests:

- **Sleep-phase consolidation** — offline deduplication and merging of redundant traces
- **Interference-based forgetting** — memories that compete should degrade
- **Engram maturation** — memories form immediately but become reliably retrievable over time
- **Reconsolidation** — retrieved memories should be updatable with new information
- **Outcome-weighted retrieval** — surfacing memories that led to good results (unexplored in production)

---

## 2. HologramEval: Design Specification

### 2.1 Design Principles

1. **Comprehensive** — Tests all 15 memory abilities in one suite (see 2.2)
2. **Multi-Modal Input** — Conversations, agent trajectories, document chains, tool calls
3. **Dynamic** — Tests memory over time, not just static retrieval
4. **Budgeted** — Every score is paired with token cost and latency
5. **Isolated** — Multi-user concurrency is a first-class test
6. **Open** — Dataset, harness, and judge prompts are open-source with pinned hashes
7. **Biological** — Tests consolidation, forgetting, and maturation — not just retrieval

### 2.2 The 15 Memory Abilities

Grouped into 5 tiers:

#### Tier 1: Retrieval (tested by existing benchmarks)
1. **Fact Recall** — Single-hop retrieval of stored facts
2. **Multi-Hop Reasoning** — Aggregating evidence across multiple memories
3. **Temporal Reasoning** — Understanding when events occurred and their ordering
4. **Open-Domain Retrieval** — Broad semantic recall without specific keywords

#### Tier 2: Dynamics (partially tested by BEAM, LongMemEval)
5. **Knowledge Update** — Revising stored facts when new information arrives
6. **Contradiction Resolution** — Detecting and reconciling inconsistent statements
7. **Event Ordering** — Reconstructing sequences from scattered memories
8. **Abstention** — Withholding answers when evidence is insufficient

#### Tier 3: Agency (tested by LongMemEval-V2, AMB)
9. **Workflow Memory** — Remembering task procedures and interface affordances
10. **Failure Mode Memory** — Recognizing recurring local failure modes (gotchas)
11. **Instruction Following** — Sustained adherence to constraints over long contexts

#### Tier 4: Biological (untested by any benchmark)
12. **Consolidation Quality** — Can the system merge redundant memories without losing detail?
    - Metric: precision/recall of consolidated facts vs. raw facts
    - Test: ingest 100 redundant memories, trigger consolidation, verify no information loss
13. **Forgetting Accuracy** — Does the system forget stale/irrelevant memories?
    - Metric: FAMA score (Forgetting Accuracy with Memory Assessment)
    - Test: inject time-sensitive facts, advance clock, verify stale facts are deprioritized
14. **Reconsolidation** — Can retrieved memories be updated with new information?
    - Metric: update precision (did the update preserve correct old info + add new info?)
    - Test: store fact A, retrieve it, present contradicting fact B, verify A is updated not duplicated

#### Tier 5: Production (untested by any benchmark)
15. **Write Quality** — Does the system store only what matters from noisy input?
    - Metric: signal-to-noise ratio of stored memories (relevant vs. irrelevant stored)
    - Test: ingest a 100-turn conversation that is 80% small talk, 20% factual.
      Verify the system stores the 20% and discards the 80%.

### 2.3 Dataset Architecture

**Scale tiers:**
- **HologramEval-S**: 100 memories, 50 queries — smoke test (< 1 min)
- **HologramEval-M**: 1,000 memories, 200 queries — standard (5 min)
- **HologramEval-L**: 10,000 memories, 500 queries — scale (30 min)
- **HologramEval-XL**: 100,000 memories, 1,000 queries — production scale (2 hr)

**Data sources:**
- Synthetic conversations (deterministic, seed=42, like current benchmarks)
- Agent trajectory logs (tool calls, state changes, outcomes)
- Document chains (research papers, code repositories, meeting transcripts)
- Time-evolving facts (facts that change over simulated time)
- Multi-user scenarios (concurrent users with overlapping and isolated data)

**Question types per ability:**

| Ability | Question Format | Scoring |
|---------|----------------|---------|
| Fact Recall | "What is X?" | Recall@K, MRR |
| Multi-Hop | "How does X relate to Y?" | Recall@K, MRR, answer accuracy |
| Temporal | "What changed between T1 and T2?" | Temporal accuracy, staleness rate |
| Open-Domain | "Tell me about X" | Semantic similarity to ground truth |
| Knowledge Update | "What is the current value of X?" | Update precision, stale fact rate |
| Contradiction | "Which statement about X is correct?" | Contradiction detection F1 |
| Event Ordering | "What happened after X?" | Sequence accuracy |
| Abstention | (irrelevant query) | TPR, FPR, F1, abstention accuracy |
| Workflow | "How do you do X in environment Y?" | Step accuracy |
| Failure Modes | "What went wrong last time you did X?" | Gotcha recall rate |
| Instructions | "Follow constraint C while doing X" | Constraint adherence rate |
| Consolidation | "Summarize what you know about X" | Consolidation precision, info retention |
| Forgetting | "Is fact X still relevant?" | FAMA score, staleness detection |
| Reconsolidation | "Update fact X with new info Y" | Update precision, no-duplication rate |
| Write Quality | (ingest noisy conversation) | Signal-to-noise ratio, storage efficiency |

### 2.4 Scoring System

Every score is reported as a **triple**: `(accuracy, token_cost, latency_p50)`.

**Composite score:**
```
HologramScore = w_acc * accuracy - w_token * token_cost / 1000 - w_lat * latency_p50 / 100
```
Where `w_acc = 0.7`, `w_token = 0.2`, `w_lat = 0.1` (tunable).

This makes it impossible to game with unlimited tokens. A system scoring 95% with 10K
tokens scores lower than one scoring 90% with 100 tokens.

**Per-ability subscores:** Each of the 15 abilities gets its own score triple, so
strengths and weaknesses are visible.

**Bootstrap CIs:** All scores include 95% bootstrap confidence intervals computed from
per-query data.

### 2.5 Anti-Bias Measures

To prevent accusations of self-serving evaluation:

1. **Open-source everything** — dataset generator, harness, judge prompts, scoring code
2. **Pinned configs** — dataset hash, judge-prompt hash, embedding model, reader model
   are all recorded and published
3. **Deterministic data** — seed=42, reproducible by anyone
4. **Invite verification** — publish a "run it yourself" guide
5. **Report honestly** — publish weaknesses alongside strengths
6. **No custom tuning** — the benchmark is designed before results are known
7. **External judge** — use a fixed LLM (e.g., GPT-4o-mini) for answer scoring, not our own model
8. **Cross-system comparison** — invite Mem0, Letta, Cognee, etc. to run and submit scores

### 2.6 Relationship to Existing Benchmarks

HologramEval is **not a replacement** for LoCoMo, LongMemEval, or BEAM. It is a
**superset** that tests what they test plus what they don't. We will continue to run
external benchmarks (BEAM, LongMemEval-V2) and report those scores alongside
HologramEval scores.

The ideal reporting structure:
```
WhiteMagic Benchmark Report:
  External: BEAM-1M: XX%, BEAM-10M: XX%, LongMemEval-V2: XX%
  HologramEval-M: XX% (15-ability breakdown)
  Token economy: 0 tokens/query (external), 0 tokens/query (HologramEval)
```

---

## 3. Implementation Plan

### Phase 1: Improve Retrieval Quality (Week 1)

Fixes to the existing search pipeline before running external benchmarks:

1. **Cross-encoder blending** — Change from "replace" to "blend" mode:
   `final_score = 0.6 * cross_encoder + 0.4 * semantic_similarity`
   This should recover the 2-4% regression while improving ranking quality.

2. **Abstention threshold tuning** — Lower from 0.15 to 0.08, or implement per-query
   calibration. Target: TPR > 90% with FPR < 5%.

3. **Conversation-level summarization** — When ingesting multi-turn conversations,
   also store a per-conversation summary as a separate memory. This should help
   LoCoMo Recall@1 dramatically.

4. **Entity extraction and linking** — Extract entities from memories, store as
   metadata, and boost on entity matches during retrieval. This is what Mem0's
   improvement came from (71.4 → 92.5 on LoCoMo).

### Phase 2: Adopt External Benchmarks (Week 1-2)

1. **BEAM** — Download from HuggingFace, adapt to our search_memories API, run
   BEAM-1M and BEAM-10M. Compare against Mem0's published scores (64.1%, 48.6%).

2. **LongMemEval-V2** — Download from GitHub, adapt to our API, run small and
   medium tiers. Compare against AgentRunbook baselines (58.6%, 72.5%).

### Phase 3: Build HologramEval (Week 2-3)

1. **Dataset generator** — Synthetic conversation/trajectory/document generator
   with deterministic seeds. Covers all 15 abilities.

2. **Evaluation harness** — Runs each ability test, computes per-ability scores
   with bootstrap CIs, generates markdown report.

3. **Judge system** — Fixed external LLM for answer scoring. Judge prompts
   pinned and hashed.

4. **Open-source release** — Publish dataset, harness, and results with
   "run it yourself" guide.

### Phase 4: Run and Report (Week 3)

1. Run HologramEval-M and HologramEval-L
2. Run BEAM-1M and BEAM-10M
3. Run LongMemEval-V2 small and medium
4. Publish comprehensive report with all scores, token costs, and latencies
5. Open-source everything

---

## 4. Expected Outcomes

### 4.1 Where WhiteMagic Should Excel

- **Token economy** — 0 tokens/query vs. 7K for Mem0. This is our core differentiator
  and should be visible in every score triple.
- **Latency** — <100ms p50 vs. ~1s for Mem0. Critical for BEAM and LongMemEval-V2
  which use accuracy-latency frontier metrics.
- **Abstention** — Our gate is already implemented. With threshold tuning, we should
  achieve FPR < 5% with TPR > 90%.
- **Consolidation** — Our Dream Cycle already implements sleep-phase consolidation.
  HologramEval will be the first benchmark to score it.
- **Forgetting** — Our importance scoring and temporal decay already exist.
  HologramEval will be the first benchmark to score it.

### 4.2 Where We Expect Weakness

- **Multi-hop reasoning** — Our FTS5+semantic pipeline retrieves individual memories,
  not aggregated evidence. Graph traversal or multi-step retrieval may be needed.
- **Scale** — Without Rust SIMD HNSW, semantic search at 100K+ memories may be slow.
- **Write quality** — We currently store everything with auto_embed=True. A write
  quality filter may be needed.

### 4.3 What We're Not Claiming

- We're not claiming HologramEval is unbiased. We're claiming it's transparent,
  comprehensive, and open to verification.
- We're not claiming our scores on external benchmarks will be the best. We're
  claiming they'll be honest, budgeted, and reproducible.
- We're not claiming 0 tokens is always better. We're claiming the token-accuracy
  tradeoff should be visible in every score.

---

## 5. References

- LoCoMo: snap-research.github.io/locomo (Maharana et al., 2024)
- LongMemEval-V1: arXiv:2410.10813 (ICLR 2025)
- LongMemEval-V2: arXiv:2605.12493 (May 2026)
- BEAM: arXiv:2510.27246 (ICLR 2026)
- FadeMem: arXiv:2601.18642 (biologically-inspired forgetting)
- ZenBrain: arXiv:2604.23878 (15 neuroscience mechanisms)
- SCM: arXiv:2604.20943 (sleep-consolidated memory)
- Human-Inspired Memory Architecture: arXiv:2605.08538
- PragAURA: OpenReview (speech-act-guided abstention)
- CoRM-RAG: arXiv:2605.01302 (risk-aware abstention)
- Memory in the Age of AI Agents: arXiv:2512.13564 (survey, 200+ refs)
- Mem0 State of AI Agent Memory 2026: mem0.ai/blog/state-of-ai-agent-memory-2026
- Mnemoverse AI Memory Landscape 2026: mnemoverse.com/docs/research/ai-memory-landscape-2026
