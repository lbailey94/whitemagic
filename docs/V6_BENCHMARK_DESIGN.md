# WhiteMagic v6 Benchmark Design — "MemoraStrict"

**Status:** Draft — 2026-08-20
**Authors:** WM team
**Precedents:** LongMemEval (ICLR 2025), LoCoMo (ACL 2024), AMemGym (ICLR 2026),
MemDelta (2026), GroupMemBench (2026), EverMemBench (2026), Memora (ACL 2026)

## Motivation

LongMemEval-S has fundamental limitations as an evaluation tool:

1. **Fits in a context window** (~115K tokens) — doesn't structurally require
   external memory. Full-context GPT-4o scores 60%.
2. **Retrieval-only metric** — measures R@K (session ID in top-K), not answer
   quality. A system can achieve 96% R@5 without answering any question.
3. **Lenient judge** — the GPT-4o-mini judge accepts 62.81% of intentionally
   wrong-but-topical answers (Penfield Labs audit).
4. **Synthetic needle-in-haystack** — questions are derived from known facts
   explicitly stated in conversation. No temporal evolution, no contradictions,
   no abstention, no multi-hop reasoning.
5. **No cost/footprint constraints** — "store everything" is optimal. Real
   memory systems need forgetting, consolidation, and budget management.
6. **Off-policy** — the assistant never participates. Real deployment is
   interactive, on-policy, and the assistant's responses shape the conversation.
7. **We've hit the ceiling** — 86% R@1 with 7 near-tie misses that are
   artifacts of symmetric scoring on synthetic data. Further optimization on
   this benchmark has diminishing returns and may not transfer to real use.

## Design Principles

### P1: Adversarial Distractor Design

Every test case includes **competing turns** that:
- Contain *more* keyword overlap with the query than the answer turn
- Are in the same session or temporally closer than the answer turn
- Are the same `EpisodicKind` (UserStatement) as the answer turn
- Use similar vocabulary but answer a different question

If BM25 can pass a test, the test is not testing anything interesting.

### P2: Deterministic Ground Truth

No LLM judge. Answers are verified by:
- **Exact string match** (case-insensitive, whitespace-normalized)
- **Structured comparison** (JSON field equality, set membership, numeric range)
- **Deterministic verification functions** (e.g., `is_current_preference(topic, value)`)

The scoring function does not know which system produced the results.

### P3: Parameterized Generation

Scenarios are generated from templates with randomized parameters:
- Names, dates, locations, topics drawn from large pools
- Session ordering and interleaving randomized per seed
- Distractor density and similarity controlled but randomized
- Multiple seeds (≥5) per scenario to prevent overfitting

### P4: Cross-System Baselines

Every test runs against three baselines:
1. **BM25-only** — raw keyword matching, no typed keys, no enrichment, no
   consolidation. If WM doesn't beat this, the feature isn't helping.
2. **Full-context LLM** — entire conversation fed to a frontier model. If this
   beats WM, we have a context-window management problem (not a memory problem).
3. **WM full stack** — episodic keys, enrichment, query planner, lifecycle,
   associations, optional embedding reranking.

Results report all three side-by-side. No system gets a home-field advantage.

### P5: Cost-Aware Metrics

Every test reports:
- **Accuracy** (exact match, MRR, nDCG)
- **Memory footprint** (bytes stored, number of records, index size)
- **Write cost** (ingest time, enrichment time, embedding time)
- **Read cost** (search latency p50/p95/p99)
- **Write amplification** (bytes written per byte of input)

A system that stores everything and searches slowly is not better than a
system that stores selectively and searches fast.

### P6: Negative Results Are Valuable

Tests are designed to *find* weaknesses, not to confirm strengths. If
abstention score is 20%, that's a roadmap item. If consolidation doesn't help
under memory budget, that's a design insight. We do not design tests to make
WM look good.

## Scenario Structure

A **scenario** is a life simulation: a user interacting with an assistant
across N sessions over simulated weeks/months.

```
Scenario {
  persona: Persona,           // name, age, job, location, preferences
  sessions: Vec<Session>,     // 10-50 sessions, each 5-30 turns
  timeline: Timeline,         // real timestamps per session
  facts: Vec<Fact>,           // ground-truth facts with temporal validity
  contradictions: Vec<Contradiction>,  // explicit fact changes
  questions: Vec<Question>,   // test questions with deterministic answers
  noise_profile: NoiseConfig, // distractor density, topic interleaving
}
```

### Persona

A persona defines:
- Stable attributes (name, age, occupation, location)
- Evolving attributes (preferences, goals, relationships)
- Temporal trajectory (what changes, when, and why)

Example:
```json
{
  "name": "Jordan",
  "age": 29,
  "occupation": "data scientist",
  "location": "Boston",
  "preferences": [
    {"topic": "coffee", "initial": "light roast", "final": "dark roast", "change_session": 12},
    {"topic": "programming_language", "initial": "Python", "final": "Rust", "change_session": 8}
  ]
}
```

### Sessions

Each session is a natural conversation:
- 5-30 turns, mixed user/assistant
- 1-3 topics per session (interleaved, not segregated)
- Natural transitions, tangents, and topic shifts
- Distractor turns: 70-90% of turns are noise (small talk, opinions, questions
  about unrelated topics)
- Signal turns: 10-30% contain factual information that could be queried

### Facts

Ground truth facts with temporal validity windows:
```json
{
  "id": "fact_001",
  "content": "I live in Boston",
  "category": "location",
  "valid_from": "session_1",
  "valid_until": "session_15",
  "superseded_by": "fact_042",
  "session": 1,
  "turn": 3
}
```

### Contradictions

Explicit fact changes that test supersession:
```json
{
  "old_fact": "fact_001",
  "new_fact": "fact_042",
  "content": "I moved to Austin",
  "session": 15,
  "turn": 7,
  "type": "supersession"
}
```

## Test Categories

### T1: Temporal Supersession (harder than LongMemEval)

**What it tests**: Can the system prefer the current version of a fact over
an older, contradictory version?

**Design**: A preference or fact is stated in session 1, then changed in
session N. The query asks for the *current* value. The answer turn (session N)
must rank above the old turn (session 1).

**Why BM25 fails**: Both turns contain the same keywords (e.g., "favorite
coffee"). BM25 may prefer the older turn if it's longer or has more context.

**Adversarial distractor**: Add 3-5 turns in sessions 2-N-1 that mention the
*old* preference in passing ("I still love my light roast every morning").

**Metrics**: R@1 for current-value retrieval, Supersession Accuracy (does the
system suppress the old fact?).

### T2: Abstention

**What it tests**: Can the system correctly return "I don't know" when no
relevant memory exists?

**Design**: 50% of questions are about topics never discussed. 50% are about
topics discussed but with different specifics (e.g., "What's my favorite
podcast?" when podcasts were never mentioned, but music was discussed
extensively).

**Why BM25 fails**: BM25 always returns the closest match. It has no concept
of "nothing relevant exists."

**Metrics**: True Positive Rate (relevant query → correct answer), False
Positive Rate (irrelevant query → confident wrong answer), Abstention F1.

### T3: Multi-Hop Reasoning

**What it tests**: Can the system connect two facts across sessions to answer
a question that neither fact alone answers?

**Design**: Fact A in session 3 ("I bought a bookshelf from IKEA"). Fact B in
session 7 ("It took me 4 hours to assemble the bookshelf"). Query: "How long
did it take to assemble the thing I bought from IKEA?"

**Why BM25 fails**: The query contains "assemble" and "IKEA" but the answer
turn (session 7) only contains "assemble" and "bookshelf", not "IKEA". BM25
matches on "assemble" but may rank a distractor turn mentioning IKEA higher.

**Adversarial distractor**: Add a turn in session 5 mentioning IKEA and
assembly: "I helped my friend assemble her IKEA desk." This has more keyword
overlap with the query than either answer turn.

**Metrics**: R@1, Multi-hop Accuracy (both facts retrieved and connected).

### T4: Distractor Resistance

**What it tests**: Can the system find a single signal turn buried in 50+
noise turns with similar vocabulary?

**Design**: 1 turn contains the answer. 50+ turns discuss the same topic but
with different specifics. The query uses generic terms that match many turns.

**Why BM25 fails**: BM25 ranks by term frequency × inverse document frequency.
With 50+ similar turns, the signal turn may not have the highest TF-IDF score.

**Example**: 50 turns about cooking (different recipes, techniques, ingredients).
1 turn mentions "I'm allergic to shellfish." Query: "What food allergy do I
have?" Distractor turns mention "allergy" in passing ("my friend has a peanut
allergy") and "shellfish" in recipes ("I made a great shellfish pasta").

**Metrics**: R@1, Signal-to-Noise Ratio (score gap between answer and top
distractor).

### T5: Consolidation Benefit

**What it tests**: Does repeated mention of a fact improve retrieval?

**Design**: Fact A is mentioned once. Fact B is mentioned 5 times across
different sessions. Both are queried with equal specificity.

**Why this matters**: If WM's consolidation (importance boost on access) works,
Fact B should be easier to retrieve. If it doesn't help, consolidation is
dead weight.

**Metrics**: R@1 for single-mention vs multi-mention facts, Consolidation
Lift (R@1 improvement for repeated facts).

### T6: Memory Budget

**What it tests**: Under a memory budget constraint, does forgetting/consolidation
help or hurt recall?

**Design**: Run the same scenario with unlimited memory and with a budget
(e.g., retain only 50% of turns). The budget forces the system to choose what
to keep.

**Why this matters**: Real systems can't store everything. A good memory
system should retain high-importance facts and prune noise. If recall drops
proportionally to budget, the system is just storing everything. If recall
drops less than proportionally, forgetting is working.

**Metrics**: R@1 at 100%, 75%, 50%, 25% memory budget. Budget-Adjusted Recall
(R@1 / memory_used).

### T7: Scale Stress

**What it tests**: Does recall degrade at scale? Does latency stay under SLO?

**Design**: Generate scenarios with 1K, 10K, 50K, 100K turns. Query for facts
inserted early, middle, and late.

**Metrics**: R@1 at each scale, p50/p95/p99 latency, index size, write
throughput.

### T8: Contradiction Detection

**What it tests**: Can the system identify when two memories conflict?

**Design**: Insert explicit contradictions ("I'm vegetarian" in session 3,
"I had a great steak" in session 8). Query: "Do I have any dietary
restrictions?" The system should surface both memories and flag the conflict.

**Why BM25 fails**: BM25 retrieves both turns but has no mechanism to identify
the contradiction. It may rank the older turn higher (more context) or the
newer turn higher (recency), but it can't reason about the conflict.

**Metrics**: Contradiction Detection Rate (both turns retrieved), Conflict
Flag Rate (system identifies the contradiction).

### T9: Preference Drift Tracking

**What it tests**: Can the system track how a preference changed over time and
answer questions about both the current and past state?

**Design**: A preference changes 3 times over 20 sessions. Queries:
- "What's my current favorite X?" (should return latest)
- "What was my favorite X before I switched?" (should return previous)
- "How many times have I changed my mind about X?" (should count transitions)

**Why BM25 fails**: All turns mention the same topic with similar vocabulary.
BM25 can't distinguish "current" from "past" without temporal reasoning.

**Metrics**: Current-Value Accuracy, Past-Value Accuracy, Transition Count
Accuracy.

### T10: Cross-Session Synthesis

**What it tests**: Can the system connect facts across sessions to answer
questions that require synthesis?

**Design**: Session 3: "I started learning Rust." Session 10: "I finished my
first Rust project, a CLI tool." Session 15: "I got a job using Rust." Query:
"How long did it take from starting Rust to getting a job using it?"

**Why BM25 fails**: No single turn contains the answer. The system must
retrieve all three turns and compute the time span.

**Metrics**: Synthesis Accuracy (correct time span), R@K for all relevant
turns.

## Metrics Summary

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| R@1 | Top-1 retrieval accuracy | >90% on T1, T4, T5 |
| R@K | Top-K retrieval accuracy | >95% on all categories |
| MRR | Mean Reciprocal Rank | >0.95 |
| Abstention F1 | Correct "I don't know" behavior | >80% |
| Supersession Accuracy | Current fact preferred over old | >90% |
| Consolidation Lift | Repeated facts easier to find | >10% R@1 improvement |
| Budget-Adjusted Recall | Recall per unit memory | Non-decreasing as budget shrinks |
| Contradiction Detection | Conflicts identified | >70% |
| Preference Drift Accuracy | Temporal tracking | >80% |
| Synthesis Accuracy | Multi-fact reasoning | >60% |
| p95 Latency | Search under SLO | <50ms at 10K, <200ms at 100K |
| Write Throughput | Ingest rate | >1000 turns/sec |
| Memory Footprint | Storage efficiency | <1KB per turn average |

## Implementation Plan

### Phase 1: Scenario Generator (pure Python, no LLM)

1. Define persona templates with parameterized attributes
2. Generate sessions with controlled noise/signal ratio
3. Insert facts, contradictions, and preference changes at scheduled sessions
4. Generate questions with deterministic ground-truth answers
5. Output as JSON (compatible with existing `longmemeval_bench.py` harness)

**Key**: No LLM is used for generation. All conversations are template-based
with randomized parameters. This ensures reproducibility and eliminates LLM
bias in test data.

### Phase 2: Evaluation Harness

1. Adapt `longmemeval_bench.py` to run against WM's MCP interface
2. Add BM25-only baseline (disable enrichment, keys, query planner)
3. Add full-context baseline (feed all turns to an LLM, ask the question)
4. Add deterministic scoring (exact match, structured comparison)
5. Add cost metrics (footprint, latency, throughput)
6. Output per-category breakdowns with confidence intervals

### Phase 3: Run and Analyze

1. Generate 5 scenarios × 5 seeds = 25 runs per test category
2. Run all three baselines (BM25, full-context, WM)
3. Analyze per-category results
4. Identify weaknesses → roadmap items
5. Iterate on WM features → re-run → measure improvement

### Phase 4: Interactive Extension (future)

1. Add AMemGym-style on-policy evaluation
2. Simulated user role-plays with WM as the assistant
3. Write/Read/Utilization diagnostics
4. Self-evolution feedback loop

## Anti-Cheating Checklist

- [ ] BM25 baseline fails on every test category (or WM doesn't beat it)
- [ ] Ground truth is deterministic (no LLM judge)
- [ ] Distractors have higher keyword overlap than answer turns
- [ ] Scenarios are parameterized with multiple seeds
- [ ] Results include all three baselines side-by-side
- [ ] Cost metrics are reported alongside accuracy
- [ ] Negative results are reported, not hidden
- [ ] Test categories include capabilities WM doesn't have yet
- [ ] No test is designed to show WM in a favorable light
- [ ] The benchmark can be run by a third party without WM-specific knowledge

## Comparison to Existing Benchmarks

| Feature | LongMemEval-S | LoCoMo | AMemGym | Memora | **MemoraStrict** |
|---------|:---:|:---:|:---:|:---:|:---:|
| Temporal evolution | ✗ | ✗ | ✓ | ✓ | ✓ |
| Abstention | ✗ | ✗ | ✗ | ✗ | ✓ |
| Multi-hop | partial | ✓ | ✗ | ✗ | ✓ |
| Contradiction detection | ✗ | ✗ | ✗ | ✓ | ✓ |
| Preference drift | ✗ | ✗ | ✓ | ✓ | ✓ |
| Memory budget | ✗ | ✗ | ✗ | ✓ | ✓ |
| Scale stress | ✗ | ✗ | ✓ | ✗ | ✓ |
| Cost-aware | ✗ | ✗ | ✓ | ✗ | ✓ |
| Deterministic scoring | ✗ | ✗ | ✗ | ✗ | ✓ |
| Adversarial distractors | partial | ✗ | ✗ | ✗ | ✓ |
| Cross-system baselines | ✗ | ✗ | partial | ✗ | ✓ |
| Parameterized generation | ✗ | ✗ | ✓ | ✗ | ✓ |
| Interactive (on-policy) | ✗ | ✗ | ✓ | ✗ | Phase 4 |

## References

- LongMemEval: https://arxiv.org/abs/2410.10813
- LoCoMo: https://aclanthology.org/2024.acl-long.218/
- AMemGym: https://openreview.net/forum?id=sfrVLzsmlf
- MemDelta: https://arxiv.org/abs/2606.29914
- GroupMemBench: https://arxiv.org/abs/2605.14498
- EverMemBench: https://arxiv.org/abs/2602.01313
- Memora: https://aclanthology.org/2026.findings-acl.1337/
- Penfield Labs judge audit: https://agentos.sh/blog/memory-benchmark-transparency-audit/
- Benchmark Theatre critique: https://essays.bloo-mind.ai/posts/2026-05-20-mem-eval/
