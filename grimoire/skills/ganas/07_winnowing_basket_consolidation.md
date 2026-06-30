---
name: wm-search
description: "Search memories, vector search, hybrid recall, graph walk, and batch read"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_winnowing_basket
    tools: [search_memories, vector_search, hybrid_recall, graph_walk, batch_read_memories, fast_read_memory, fragment_index, fragment_query, jit_research]
    tags: [search, vector, hybrid, graph, recall, fragment, research]
---

# Search & Wisdom Retrieval

Search memories using semantic similarity, full-text search, hybrid recall, or knowledge graph traversal. The winnowing basket filters signal from noise.

## When to Use

- Finding relevant memories before starting a task
- Researching a topic across the memory store
- Exploring connections via the knowledge graph
- Hybrid search (semantic + keyword combined)
- Batch reading multiple memories efficiently
- JIT research — just-in-time knowledge gathering

## How to Invoke

```python
# Semantic search
wm(thought="search for memories about database migrations")
wm(route="gana_winnowing_basket.search_memories", args={"query": "...", "limit": 10})

# Vector similarity search
wm(route="gana_winnowing_basket.vector_search", args={"query": "...", "limit": 5})

# Hybrid recall (semantic + FTS5)
wm(route="gana_winnowing_basket.hybrid_recall", args={"query": "...", "limit": 10})

# Knowledge graph walk
wm(route="gana_winnowing_basket.graph_walk", args={"start_node": "...", "max_depth": 3})

# Batch read
wm(route="gana_winnowing_basket.batch_read_memories", args={"ids": ["...", "..."]})

# JIT research
wm(route="gana_winnowing_basket.jit_research", args={"topic": "..."})
```

## Search Modes

- **FTS5** — Full-text search with phrase-first matching
- **Semantic** — Embedding-based similarity (HNSW index, 0.26ms search)
- **Hybrid** — Combines FTS5 + semantic with reciprocal rank fusion
- **Graph** — Traverses cross-galaxy associations
- **Galaxy-aware** — Search within specific galaxies or across all
