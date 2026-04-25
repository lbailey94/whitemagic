# Pattern Miners

**Working title**: "Mining Solutions and Anti-Patterns from Agent Execution History"
**Target length**: 1500–2500 words
**Paired repo**: `whitemagic-patterns`
**Status**: 🟡 Stub · **Priority**: P3
**Source material**: `miners.py` engine, `association_miner.py`, session data

---

## Thesis (one sentence)

Every agent already produces a stream of action → outcome pairs; if you mine that stream for recurring (solution, context) tuples and (failed-attempt, context) tuples, you get a cheap, deployable form of experience-learning without touching model weights.

## Key points to develop

1. **The setup.** Agent executes. Each execution has inputs, actions, outcomes. Stream these into a log.
2. **Pattern extraction.** For each successful outcome, cluster similar contexts, extract the common action prefix. This is a "solution pattern."
3. **Anti-pattern extraction.** Same but for failures. Surface these in-context to the agent on similar future queries.
4. **Heuristic extraction.** Meta-patterns: "when the user says X, the action that worked 7/10 times was Y."
5. **Why not RAG.** RAG stores knowledge. This stores *action traces*. Different axis.
6. **The killer use case.** Debugging recurring failure modes in agent pipelines. Anti-patterns appear in logs before they appear in user complaints.

## Open questions (honest)

- Is this meaningfully different from what Langsmith / Helicone do? (They surface traces; this extracts patterns.)
- What's the minimum log volume for useful patterns? (Guess: ~1000 traces per pattern.)
- Can this produce bad heuristics that reinforce themselves? (Yes. Need an update/decay mechanism, which the schema already has via half-life.)

## Publish venue options

- GitHub + blog post
- Submit to an agent-ops-focused newsletter

## Draft log

- [ ] Extract `whitemagic-patterns` standalone
- [ ] Add one demo dataset + one extracted pattern as example
- [ ] Draft
