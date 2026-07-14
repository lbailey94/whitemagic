# Gana: gana_heart

**26 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [analyze_scratchpad](../tools/analyze_scratchpad.md) | system | read | Dispatch-routable WhiteMagic tool 'analyze_scratchpad'. |
| [context.pack](../tools/context.pack.md) | system | read | Pack memories into an optimized context window for LLM calls — salience scoring  |
| [context.status](../tools/context.status.md) | introspection | read | Get Context Window Optimizer configuration and status |
| [get_session_context](../tools/get_session_context.md) | system | read | Dispatch-routable WhiteMagic tool 'get_session_context'. |
| [knowledge_gap.run](../tools/knowledge_gap.run.md) | synthesis | write | Detect and attempt to fill knowledge gaps using self-directed actions — seeds me |
| [scratchpad](../tools/scratchpad.md) | session | write | Unified scratchpad management for active work. Actions: create (new scratchpad), |
| [scratchpad_create](../tools/scratchpad_create.md) | system | read | Dispatch-routable WhiteMagic tool 'scratchpad_create'. |
| [scratchpad_finalize](../tools/scratchpad_finalize.md) | system | read | Dispatch-routable WhiteMagic tool 'scratchpad_finalize'. |
| [scratchpad_update](../tools/scratchpad_update.md) | system | read | Dispatch-routable WhiteMagic tool 'scratchpad_update'. |
| [session.backfill](../tools/session.backfill.md) | session | write | Backfill sequence numbers for existing session memories that lack them. Sorts by |
| [session.consolidate](../tools/session.consolidate.md) | session | write | Sleep consolidation — promote important session turns (decisions, breakthroughs, |
| [session.continuity](../tools/session.continuity.md) | session | read | Get cross-session continuity — recent turns from the previous session for contex |
| [session.handoff](../tools/session.handoff.md) | session | write | Unified cross-device session handoff. Actions: transfer (send session to another |
| [session.memory_stats](../tools/session.memory_stats.md) | session | read | Get session memory statistics (turn count, role distribution, turn types, elapse |
| [session.recall](../tools/session.recall.md) | session | read | Recall recent session turns in chronological order (oldest to newest). |
| [session.record](../tools/session.record.md) | session | write | Record a conversation turn (user message or AI response) as a persistent session |
| [session.replay](../tools/session.replay.md) | session | read | Replay session turns — full chronological, selective (important turns only), or  |
| [session.search](../tools/session.search.md) | session | read | Semantic search within session memories using FTS5. |
| [session_handoff](../tools/session_handoff.md) | system | read | Dispatch-routable WhiteMagic tool 'session_handoff'. |
| [session_handoff_summary](../tools/session_handoff_summary.md) | system | read | Dispatch-routable WhiteMagic tool 'session_handoff_summary'. |
| [state.context](../tools/state.context.md) | session | write | Get or set context values in the current work state. Without arguments, returns  |
| [state.current](../tools/state.current.md) | session | read | Get the current work state snapshot — current task, active tasks, next steps, re |
| [state.update](../tools/state.update.md) | session | write | Update the current work state. Set current task, add/complete tasks, add next st |
| [working_memory.attend](../tools/working_memory.attend.md) | memory | write | Bring a memory into working memory focus. LRU eviction when at capacity (7±2 chu |
| [working_memory.context](../tools/working_memory.context.md) | memory | read | Get current working memory contents sorted by activation, for prompt injection. |
| [working_memory.status](../tools/working_memory.status.md) | memory | read | Get working memory status: capacity, used slots, chunks, eviction stats. |
