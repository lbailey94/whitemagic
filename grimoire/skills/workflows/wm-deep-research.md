---
name: wm-deep-research
description: "Multi-source web research with synthesis, memory storage, and knowledge graph extraction"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [research, web, synthesis, knowledge_graph, memory, rabbit_hole]
---

# Deep Research

Multi-step research workflow combining memory search, web search, enhanced fetching, knowledge graph extraction, and synthesis storage.

## When to Use

- Researching a topic across multiple sources
- Literature reviews and competitive analysis
- Technology evaluation and comparison
- Any task requiring synthesized knowledge from multiple web sources

## Workflow

1. **Search memories** — Find relevant prior knowledge
   ```python
   wm(thought="search for memories about <topic>")
   ```

2. **Web search** — Find current information
   ```python
   wm(route="gana_chariot.web_search", args={"query": "<topic>"})
   ```

3. **Enhanced fetch** — Get structured content from key sources
   ```python
   wm(route="gana_chariot.web_fetch_enhanced", args={"url": "..."})
   ```

4. **Rabbit hole** — Multi-hop exploration for depth
   ```python
   wm(route="gana_chariot.rabbit_hole_research", args={"topic": "...", "depth": 3})
   ```

5. **Extract knowledge graph** — Build structured knowledge from findings
   ```python
   wm(route="gana_chariot.kg_extract", args={"text": "<combined findings>"})
   ```

6. **Store synthesis** — Persist as a research memory
   ```python
   wm(route="gana_neck.create_memory", args={
       "title": "Research: <topic>",
       "content": "<synthesis>",
       "tags": ["research"],
       "galaxy": "research"
   })
   ```

7. **Cross-reference** — Find connections to existing knowledge
   ```python
   wm(route="gana_extended_net.association_mine_semantic", args={"query": "<topic>"})
   ```

## Tips

- Start with memory search — prior research may already exist
- Use enhanced fetch for long articles (gets outline + chunks)
- Rabbit hole depth 3 is usually sufficient; 5 for deep dives
- Store in the `research` galaxy for organized retrieval
- Cross-reference after storing to build the knowledge graph
