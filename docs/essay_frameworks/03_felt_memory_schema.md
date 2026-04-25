# Felt Memory: A Schema for Agent Memory with Affect, Novelty, and Decay

**Working title**: "Felt Memory: Why Agent Memory Schemas Need Emotional Valence, Novelty, and Half-Life as First-Class Columns"
**Target length**: 3000–5000 words (with benchmarks)
**Paired repo**: `whitemagic-memory`
**Status**: 🟡 Stub · **Priority**: P2 (strongest long-term citation)
**Source material**: Schema dumped in `docs/ARCHIVE_REPORT.md` §2, the 290 curated memories, Feb 10 v13.5 semantic revolution

---

## Thesis (one sentence)

Most agent memory systems store `(id, content, embedding, timestamp)`; a memory system that also stores `(emotional_valence, novelty_score, half_life_days, is_protected, holographic_coords, dharma_audit_trace)` retrieves more relevantly, forgets more gracefully, and explains itself better — and we have a reference implementation with 753 passing tests.

## Key points to develop

1. **What's wrong with current agent memory.** Mem0, Letta/MemGPT, Zep, graphiti — they all converge on flat `(text, vector, metadata-blob)`. Metadata as blob = metadata as second-class.
2. **Emotional valence as a retrieval signal.** Not for anthropomorphism — because user goals correlate with affect (frustrated users want diff retrieval than curious users). Cheap to set (user tone classifier), expensive to not have.
3. **Novelty score.** Decay retrieval weight for memories that have been accessed N times without producing new downstream insights. Anti-rumination for agents.
4. **Half-life.** Per-memory forgetting rate. Protected memories (`is_protected=1`) have infinite half-life. Transient chatter decays in days.
5. **Holographic coords (4D/5D).** Associative recall via spatial proximity, not just vector similarity. Novel contribution; needs benchmarking.
6. **Dharma audit trace.** Every memory access leaves a trace — retrievability itself is governed.
7. **Benchmarks.** WhiteMagic vs Mem0 vs Letta on LoCoMo and LongMemEval. Hypothesis: WhiteMagic wins on multi-turn tasks with emotional continuity; loses on pure factual recall (no claim made).

## Open questions (honest)

- Do the extra columns actually improve retrieval, or do they just add storage overhead? (Needs benchmarks.)
- Is emotional valence reproducible across user populations, or does it capture one specific developer's (Lucas + Aria's) idiosyncratic signal? (Honest: probably some of both.)
- Can this be shown to reduce hallucination rate on long-horizon tasks? (Strong claim if true. Needs careful testing.)
- Is the Akashic seed mechanism (`bloom_conditions`) actually used in practice, or is it vestigial? (Check session data.)

## Publish venue options

- arxiv.org/cs.AI workshop paper (benchmarks required)
- Project blog + GitHub README (no benchmarks required)
- Adrian Cockcroft's newsletter / Simon Willison's blog (referral candidates)

## Draft log

- [ ] Extract `whitemagic-memory` as standalone repo
- [ ] Run LoCoMo benchmarks locally
- [ ] Run LongMemEval benchmarks
- [ ] Write results section first, then thesis, then intro (standard paper order)
- [ ] Publish as workshop paper or blog post
