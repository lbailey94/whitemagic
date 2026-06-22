# ADR-001: PRAT Gana System — 28 Meta-Tools over Flat Tool Namespace

**Status**: Accepted  
**Date**: 2026-04-15  
**Deciders**: WhiteMagic core team  
**Tags**: architecture, tools, mcp

---

## Context

WhiteMagic grew to 374 individual MCP tools. Claude Desktop and similar MCP clients present tools
in a flat list, creating an overwhelming cognitive load for AI models. Models were spending
significant tokens selecting tools rather than performing work.

The flat namespace also created maintenance problems: similar tools had inconsistent naming
(`search_memory` vs `memory_search` vs `search_query`), and adding a tool required knowing the
entire 374-tool namespace to avoid collisions.

## Decision

Adopt the **PRAT (Polymorphic Resonance-Allocated Tool) Gana system**: 28 meta-tools
named after the 28 Ganas of Vedic astrology. Each Gana routes to a contextually appropriate
sub-tool based on resonance scoring and the `dispatch_table.DISPATCH_TABLE`.

```
AI Model  →  28 Gana tools  →  Gana routing logic  →  374 handlers
```

Key design choices:

1. **Semantic grouping**: Tools grouped by function (memory, dharma, intelligence, resonance, etc.) not by implementation module.
2. **Polymorphic dispatch**: The Gana args (`action`, `intent`, `context`) select the sub-tool dynamically, reducing the model's selection burden.
3. **Backward compatibility**: The flat 374-tool namespace remains available via `WM_MCP_PRAT=0` for clients that need it.
4. **Resonance tracking**: Every Gana invocation records Wu Xing phase and resonance metrics for telemetry.

## Consequences

**Positive**:
- Reduces MCP tool count from 374 → 28 (92% reduction in model decision space)
- Single `dispatch_table.py` (now domain-sliced) is the source of truth for all routing
- New tools added to domain slices without changing the Gana API surface

**Negative**:
- Adds routing complexity — model must understand Gana semantics vs individual tool names
- Debug path is longer (model → Gana → dispatch → handler)
- Requires `mcp-registry.json` maintenance (addressed by F-24 auto-generation script)

## Alternatives Considered

- **Flat namespace with autocomplete hints**: Rejected — still requires model to scan 374 tools
- **Category-prefix naming** (`memory.search`, `dharma.evaluate`): Partially adopted as aliases; not sufficient alone for cognitive load reduction
- **Single unified tool** (`whitemagic(action, ...)`: Too opaque, breaks tool-specific prompting
