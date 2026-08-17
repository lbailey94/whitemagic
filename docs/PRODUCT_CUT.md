# Product cut — local memory for coding agents

**Written:** 2026-08-16
**Status:** In progress. Measurement (OR 10q/50q) is a separate evening slice.

This is the execution plan for putting v5.8 in the best *product* state
without adding organs. The release promise stays:

> Your agent can remember project context, find it after restart, and carry
> work across sessions without sending its memory store to a hosted service.

## Decisions

1. **`memory.search` is the public retrieval verb.** BM25 by default; hybrid
   BM25+vector when `WM_EMBEDDER_ENDPOINT` is set. `memory.hybrid_recall`
   remains as a compatibility alias with the same implementation.
   `memory.chat` stays conversational/cached. `memory.nearby` stays 5D
   spatial and is not a general search.
2. **Curated is the stranger-install surface.** Prefixes: `memory`,
   `session`, `claims`, `transaction`, `gnosis`, `tools.list`.
   `nlu.shadow_report` and `tools.usage_report` move to full.
3. **`wm serve` defaults to curated.** Already done. `wm daemon` and library
   constructors stay full (cycle tools live outside curated).
4. **Citta / self-model stay advisory.** Fresh writes into `galaxy=citta`
   are already refused (Satya). Do not add coherence/valence gates on
   user writes.
5. **NLU is not promoted.** Explicit `route=` is the contract. Destructive
   hard-block + abstention stay. Shadow disagreement is not a ship gate.
6. **Seal is corruption detection**, not a root of trust. `wm doctor`
   surfaces an existing `seal.json`. Help text states the threat model.
7. **Bench numbers must split ingest vs query.** The `* 0.95` split is a
   lie. Two-phase timing (ingest batch, then search) is the honest path.
8. **Contextualized session indexing and fact+chunk keys** are the next
   *quality* work after OR is scored. Naive duplicate composite documents were
   measured and rejected; preserve canonical turn IDs and returned content.
   Not in this cut.
9. **Client hook** (inject recall at session start) is a design note only
   until the one-verb path is stable.

## Out of scope this cut

B4 sandbox, official 500q QA, NLU promotion, `McpServer` split, Sangha,
self-play, imagination, more tools, fusion-weight grids.

## Client hook (design only)

Winning local MCP servers inject memory before the model thinks. Do not
implement a plugin zoo this cut.

Recommended contract for Cursor / Claude Code / any MCP client:

1. On session start, call `wm(route="session.continuity", args={"n": 5})`.
2. If the user has a live question, also call
   `wm(route="memory.search", args={"query": "<user text>", "limit": 5})`.
3. Stuff the JSON into the system / project context. Do not ask the model
   to remember to remember.
4. Writes stay explicit: `memory.create` / `session.record` after a
   decision, not on every turn.

A later afternoon can add a one-file hook example under `docs/` or
`python/`. Not this evening.

## Contextualized Session Indexing (next quality work)

Turn-only indexing is the likely cause of the three persistent 10q misses
(Glass Menagerie, Serenity Yoga, February 14th): the answer string often
sits one turn away from the question terms.

After OR is scored on 10q/50q, which is now complete:

- Add neighboring-turn context to an auxiliary search representation while
  preserving the canonical turn document and memory ID.
- Do not return duplicate composite memories by default.
- Keep session ID and turn order as structured metadata for candidate evidence.
- Fact+chunk keys (extract a user fact, index it as an additional key,
  keep the raw chunk) is the Engram-shaped follow-up. `kg.extract` exists
  and is unused on the write path.

Do not start this until the OR number exists. Otherwise you cannot tell
whether composites helped.

## Verification (targeted, not the full workspace gate)

```bash
cargo test -p wm-mcp seal -- --test-threads=1
cargo test -p wm-tools profiles -- --test-threads=1
cargo test -p wm-tools memory_search -- --test-threads=1
```
