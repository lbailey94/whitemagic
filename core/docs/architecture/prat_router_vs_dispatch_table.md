# PRAT Router vs Dispatch Table: Dual-Path Architecture

## Overview

WhiteMagic employs a dual-path architecture for tool dispatch, combining the **PRAT Router** (meta-tool grouping) with the **Dispatch Table** (direct handler mapping). This design provides both high-level tool organization and low-level performance optimization.

## Architecture Diagram

```
Tool Call (e.g., "memory.recall")
         │
         ▼
┌───────────────────────────────────┐
│  Unified API (call_tool)          │
│  - Timeout management             │
│  - Nervous system checks          │
│  - Middleware pipeline            │
└───────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│  PRAT Router (Gana Prefix Check) │
│  - Checks for PRAT prefixes       │
│  - Routes to meta-tool handlers   │
│  - 28 Lunar Mansion Ganas         │
└───────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
PRAT Path  Direct Path
    │         │
    ▼         ▼
┌─────────┐ ┌─────────────────────┐
│ PRAT    │ │ Dispatch Table      │
│ Handler │ │ - Handler mapping   │
│         │ │ - Category lookup   │
└─────────┘ │ - Lazy loading      │
            └─────────────────────┘
                  │
                  ▼
            ┌─────────────┐
            │ Handler Fn  │
            └─────────────┘
```

## Path 1: PRAT Router (Meta-Tool Grouping)

### Purpose
The PRAT (Prajna-Rupa-Artha-Tattva) Router provides semantic grouping of tools into 28 Lunar Mansion Ganas. Each Gana represents a philosophical category (e.g., Knowledge, Action, Harmony).

### How It Works

1. **Prefix Detection**: When a tool is called, the PRAT router checks if it starts with a Gana prefix (e.g., `dharma.*`, `gana.*`, `wisdom.*`)

2. **Meta-Tool Routing**: PRAT tools are meta-tools that wrap multiple related handlers:
   ```python
   # Example: PRAT tool registration
   @prat_tool("dharma_rules")
   def dharma_rules_handler():
       # Returns multiple rule definitions
   ```

3. **Gana Context**: The router injects Gana-specific context (lunar phase, harmony state) into tool calls.

### When PRAT Path is Used
- Tools with PRAT prefixes (`dharma.*`, `gana.*`, `wisdom.*`, `iching.*`, `wuxing.*`)
- Meta-tool operations that aggregate multiple handlers
- Tools requiring philosophical/astrological context

### Files
- `whitemagic/tools/prat_router.py` - PRAT router implementation
- `whitemagic/tools/prat_resonance.py` - Resonance state tracking
- `whitemagic/cli/cli_prat.py` - CLI PRAT commands

## Path 2: Dispatch Table (Direct Handler Mapping)

### Purpose
The Dispatch Table provides a high-performance, category-based lookup mechanism for direct tool-to-handler mapping. It's optimized for common operations and avoids the overhead of PRAT routing.

### How It Works

1. **Category Lookup**: Tools are organized by category (memory, knowledge, vector, balance, etc.)
   ```python
   _DISPATCH_TABLE = {
       "memory": {
           "create_memory": LazyHandler("memory", "create_memory"),
           "search_memories": LazyHandler("memory", "search_memories"),
       },
       "knowledge": {
           "knowledge_search": LazyHandler("knowledge", "search"),
       },
   }
   ```

2. **Lazy Loading**: Handlers are loaded on-demand using `LazyHandler` wrapper to reduce startup time.

3. **Bridge Fallback**: If a handler isn't found in the table, it falls back to the Go/Zig dispatch bridge for polyglot acceleration.

### When Direct Path is Used
- Core memory operations (create, search, recall)
- Knowledge graph operations
- Vector operations
- Balance/harmony operations
- Most common tool calls

### Files
- `whitemagic/tools/dispatch_table.py` - Dispatch table implementation
- `whitemagic/tools/dispatch.py` - Main dispatch function
- `whitemagic/tools/handlers/` - Handler implementations by category

## Integration Points

### Unified API Entry Point
Both paths converge at `whitemagic/tools/unified_api.py::call_tool()`:
```python
def call_tool(tool_name: str, **kwargs):
    # 1. Nervous system checks
    _nervous_system_check(tool_name)
    
    # 2. PRAT router check (meta-tool path)
    if _is_prat_tool(tool_name):
        return _dispatch_via_prat(tool_name, **kwargs)
    
    # 3. Direct dispatch table lookup
    return dispatch(tool_name, **kwargs)
```

### Middleware Pipeline
Both paths share the same middleware pipeline:
- Input sanitization
- Circuit breaking
- Rate limiting
- Permission checks
- Governor risk assessment

## Performance Characteristics

| Path | Latency | Use Case | Optimization |
|------|---------|----------|--------------|
| PRAT Router | Higher (~5-10ms) | Meta-tools, context-heavy operations | Semantic grouping, context injection |
| Dispatch Table | Lower (~1-2ms) | Core operations, high-frequency calls | Category lookup, lazy loading, bridge fallback |

## Migration Strategy

### New Tools
- Use **Dispatch Table** for core operations (memory, knowledge, vector)
- Use **PRAT Router** for meta-tools requiring philosophical context

### Legacy Tools
- Existing tools in `dispatch_table.py` remain on direct path
- PRAT-prefixed tools automatically route through PRAT router
- No breaking changes required

## Testing

### Unit Tests
- `tests/unit/tools/test_dispatch_table.py` - Direct path tests
- `tests/unit/tools/test_prat_resonance.py` - PRAT path tests
- `tests/unit/tools/test_dispatcher.py` - Integration tests

### Integration Tests
- `tests/integration/test_tool_contract_full.py` - Contract validation for both paths
- `tests/integration/test_rust_acceleration.py` - Bridge fallback tests

## Future Enhancements

1. **Hot Path Optimization**: Cache frequently-used dispatch table lookups
2. **PRAT Context Caching**: Cache Gana context to reduce resonance queries
3. **Dynamic Routing**: Machine learning-based path selection based on tool usage patterns
4. **Unified Registry**: Consolidate PRAT and dispatch table into a single registry with routing hints

## References

- [PRAT System Documentation](../systems/prat_system.md)
- [Dispatch Table Implementation](../../whitemagic/tools/dispatch_table.py)
- [Unified API](../../whitemagic/tools/unified_api.py)
