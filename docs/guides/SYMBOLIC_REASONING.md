# Symbolic Reasoning & Concept Mapping (v2.2.5)

WhiteMagic v2.2.5 introduces a symbolic reasoning stack that encodes high-value concepts in both English and Chinese to deliver 30–50% token savings while enriching semantic search.

## Why Symbolic Reasoning?

- **Token compression**: Chinese logograms encapsulate multi-word English concepts (e.g., 道 for “The Way”), reducing prompt cost.
- **Semantic graphs**: Concept graphs expose relationships, dependencies, and cross-discipline bridges.
- **Memory navigation**: Concepts link directly to WhiteMagic memories so agents can traverse knowledge bases semantically.

## Key Modules

| Module | Path | Purpose |
| --- | --- | --- |
| `SymbolicReasoning` | `whitemagic/symbolic.py` | Core engine for concepts + relationships |
| `ConceptMap` | `whitemagic/concept_map.py` | NetworkX graph utilities (paths, communities, exports) |
| `SymbolicMemoryIntegration` | `whitemagic/symbolic_memory.py` | Bidirectional linkage between concepts and Markdown memories |
| `load_core_concepts` | `whitemagic/chinese_dict.py` | Bootstrapper for curated Daoist + technical vocab |

## Quick Start

```python
from whitemagic import (
    create_symbolic_engine,
    ConceptType,
    create_concept_map,
    MemoryManager,
    create_symbolic_memory_integration,
    load_core_concepts,
)

engine = create_symbolic_engine(use_chinese=True)
for concept in load_core_concepts():
    engine.add_concept(**concept)

define = engine.add_concept(
    concept_id="meta_optimization",
    english="Meta-Optimization",
    chinese="優化",
    concept_type=ConceptType.PATTERN,
    definition="Token-aware workflow that minimizes redundant context loads",
)

# Relationships
engine.add_relationship("meta_optimization", "wu_xing", RelationshipType.RELATED_TO)
concept_map = create_concept_map(engine)

# Link to memories
manager = MemoryManager()
integration = create_symbolic_memory_integration(manager, engine)
integration.link_memory_to_concept("20251116_symbolic_session.md", "meta_optimization")
```

## Memory Workflow

1. **Extract concepts**: `integration.extract_concepts_from_memory("<file>.md")` scans Markdown content (English + Chinese + aliases).
2. **Auto-tag**: `integration.tag_memory_with_concepts(..., tag_prefix="concept:")` keeps tags aligned with the concept graph.
3. **Search by concept**: `integration.search_by_concept("wu_xing", include_related=True)` uses graph distance to suggest contextually related memories.
4. **Analyze overlap**: `integration.suggest_related_memories("current.md")` surfaces supporting materials ranked by Jaccard similarity.

## Token Savings Diagnostics

```python
stats = engine.calculate_token_savings()
print(stats)
# {
#   'total_concepts': 48,
#   'chinese_coverage_pct': 72.9,
#   'token_savings': 188,
#   'savings_pct': 37.4,
#   ...
# }
```

These metrics also surface via MCP `track_metric` events (category `token_efficiency`).

## Exporting & Visualization

```python
graph = concept_map.export_graph()
with open("concepts.graphml", "w", encoding="utf-8") as handle:
    handle.write(graph_to_graphml(graph))
```

Use GraphML/DOT exports in Gephi, Observable, or D3 dashboards to visualize relationships, cluster boundaries, and bottlenecks.

## Best Practices

- **Hybrid approach**: Keep internal reasoning compressed (Chinese) while exposing English-friendly APIs/UI copy.
- **Curate aliases**: Provide `aliases=["daoism", "the_way"]` to improve extraction.
- **Guard rails**: For regulated environments, disable automatic linking by setting `auto_link=False` in extraction.
- **Version control**: Persist `engine.save(Path("symbolic_state.json"))` at the end of sessions, then load before subsequent runs.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ImportError: networkx not found` | `pip install networkx` to enable `ConceptMap`. |
| Concept extraction misses Chinese terms | Ensure Markdown files use UTF-8 and not sanitized ASCII exports. |
| Duplicate concept IDs | Use `engine.find_concept("alias")` before calling `add_concept`. |
