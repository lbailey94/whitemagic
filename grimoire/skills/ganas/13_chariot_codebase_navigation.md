---
name: wm-research
description: "Codebase navigation, external research, web search/fetch, browser automation, archaeology"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_chariot
    tools: [archaeology, archaeology_find_changed, archaeology_find_unread, archaeology_daily_digest, kg_extract, kg_query, strata, codegenome, web_search, web_fetch, web_fetch_enhanced, deep_fetch, rabbit_hole_research, browser_navigate, browser_extract, browser_screenshot, image_analyze, fragment]
    tags: [research, web, codebase, archaeology, strata, browser, image, kg, fragment]
---

# Research & Codebase Navigation

Multi-source web research, codebase archaeology, knowledge graph extraction, browser automation, and image analysis. The chariot drives exploration.

## When to Use

- Researching topics across the web
- Deep-diving into codebase history (archaeology)
- Running STRATA static analysis
- Extracting knowledge graphs from text
- Browser automation for web interaction
- Image OCR and structural analysis
- Rabbit hole research (multi-hop exploration)
- Enhanced web fetching with chunking and outlines

## How to Invoke

```python
# Web search
wm(thought="search the web for MCP 2.0 specifications")
wm(route="gana_chariot.web_search", args={"query": "..."})

# Enhanced web fetch (with outline + chunking)
wm(route="gana_chariot.web_fetch_enhanced", args={"url": "..."})

# Deep fetch (multi-page)
wm(route="gana_chariot.deep_fetch", args={"url": "...", "max_pages": 5})

# Rabbit hole research
wm(thought="research the history of holographic memory systems")
wm(route="gana_chariot.rabbit_hole_research", args={"topic": "...", "depth": 3})

# Codebase archaeology
wm(route="gana_chariot.archaeology", args={"repo_path": "..."})

# STRATA analysis
wm(route="gana_chariot.strata", args={"path": "..."})

# Knowledge graph extraction
wm(route="gana_chariot.kg_extract", args={"text": "..."})

# Image analysis
wm(route="gana_chariot.image_analyze", args={"image_path": "..."})

# Browser automation
wm(route="gana_chariot.browser_navigate", args={"url": "..."})
```

## Research Workflow

1. Search memories for prior knowledge
2. Web search for current information
3. Enhanced fetch key sources
4. Extract knowledge graph from findings
5. Store synthesis as a research memory
