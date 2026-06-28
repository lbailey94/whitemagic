# Workflow: Cognitive Self-Use — Continuous Thinking Between Actions

**Core principle**: An AI agent working on WhiteMagic should use WhiteMagic's own cognitive tools between coding actions. This creates a continuous thinking loop: act, reflect, remember, cross-compare, act again with richer context.

## Why

WhiteMagic is a cognitive operating system. An agent that edits WhiteMagic without using its memory, introspection, and resonance tools is like a surgeon operating without feeling their own hands.

## Between-Action Protocol

After each significant code change or discovery, fire 2-3 of these WM tools before proceeding:

1. **Remember what you just did**: `gana_neck(tool="create_memory", args={...})`
2. **Search for related prior work**: `gana_winnowing_basket(tool="search_memories", args={"query": "...", "limit": 5})`
3. **Introspect system state**: `gana_ghost(tool="gnosis", args={"compact": true})`
4. **Check capability matrix**: `gana_ghost(tool="capability_matrix", args={})`
5. **Surface serendipity**: `gana_abundance(tool="serendipity_surface", args={"count": 3})`
6. **Check continuity**: `gana_ghost(tool="citta_continuity", args={})`
7. **Get citta cycle**: `gana_ghost(tool="citta_cycle", args={})`

## Session Start Sequence

1. `gana_horn(tool="session_bootstrap")` — establish context
2. `gana_root(tool="health_report")` — verify subsystems
3. `gana_ghost(tool="gnosis", args={"compact": true})` — system snapshot
4. `gana_ghost(tool="citta_continuity")` — temporal continuity from last session
5. `gana_winnowing_basket(tool="search_memories", args={"query": "recent work", "limit": 5})` — recent context

## Session End Sequence

1. `gana_neck(tool="create_memory", args={...})` — store session summary
2. `gana_ghost(tool="citta_cycle")` — stream state for next session
3. `gana_heart(tool="scratchpad_finalize")` — finalize notes
4. `gana_root(tool="health_report")` — verify clean state

## Anti-Patterns

- **Blind editing without introspection**: Making 10 code changes without a single WM tool call. You lose context, miss connections, and repeat past mistakes.
- **Only searching, never storing**: Reading memories but never creating new ones from your work.
- **Ignoring citta continuity**: Each session starts fresh with no awareness of what came before. Always check `citta_continuity` at session start.
- **Single-tool tunnel vision**: Using only one WM tool repeatedly. The power is in cross-referencing multiple tools — memory + introspection + serendipity creates emergent insight.
