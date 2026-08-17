# Model Guide — Using WhiteMagic from an Agent

**Version**: 5.8.0

This is the one-page primer for LLMs using WhiteMagic through MCP. You are the
agent; the server exposes a single `wm` tool. Use explicit `route=` calls.

## Session rhythm

1. **Start of session** — check continuity before doing anything else:
   `wm(route="session.continuity", args={"n": 5})`. If there is a specific
   prior session, replay it budgeted:
   `wm(route="session.replay", args={"mode": "progressive", "session_id": "<id>", "token_budget": 600})`.
2. **Start a new session** when beginning real work:
   `wm(route="session.start", args={"title": "<project>"})`.
3. **During work** — record decisions, breakthroughs, and errors:
   `wm(route="session.record", args={"content": "<what happened>", "role": "ai", "turn_type": "decision", "importance": 0.8})`.
   Default importance is 0.5; raise it for durable facts.
4. **End of session** — record a summary turn so the next continuity call
   lands on something useful.

## Memory rhythm

- Store durable facts, decisions, and project context:
  `wm(route="memory.create", args={"content": "...", "galaxy": "codex", "tags": ["project", "topic"]})`.
- Find things: `memory.search` (BM25; BM25+vector when an embedder is
  configured). `memory.hybrid_recall` is the same implementation under an
  old name. `memory.chat` is cached conversational search. `memory.query`
  is tag/importance filters, not full-text. `memory.nearby` is 5D spatial,
  not general search.
- Prefer explicit routes over `thought=` for anything important. Natural
  language routing is a convenience layer and can never reach destructive
  tools.
- Private content: memories flagged `is_private` never appear in responses;
  `model_exclude` memories never enter reasoning. Use them for credentials and
  internal notes.

## Safety rules you must respect

- Destructive tools (`memory.delete`, `transaction.rollback`, `galaxy.purge`,
  ...) require an explicit route AND `"confirm": true` in args. Never add
  confirm automatically.
- `transaction.begin` snapshots the whole store; `transaction.commit` keeps
  changes; `transaction.rollback` restores exact pre-transaction records. Use
  transactions for multi-step changes you might need to undo.
- Read-only mode: if the server was started with `--readonly`, all writes are
  refused — that is intentional (another process owns the store).

## Discovery

- `wm(route="tools.list")` — the full curated surface with argument schemas
  and safety annotations (readOnlyHint/destructiveHint).
- `wm(route="claims.calibration")` — the claims ledger's self-graded track
  record (Brier, calibration gap, recalibrated confidences).
- `wm(route="gnosis.status")` — system state and galaxy counts.

## Things not to do

- Do not invent routes: use `tools.list` to see what exists.
- Do not delete memories to "clean up": use tags, importance, and
  `memory.export` instead.
- Do not store the same fact repeatedly: the store deduplicates by content
  hash, but re-stating facts wastes tokens and clutters recall.
