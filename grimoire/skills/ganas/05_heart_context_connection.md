---
name: wm-context
description: "Scratchpad, working memory, session context, and handoff management"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_heart
    tools: [analyze_scratchpad, context_pack, context_status, get_session_context, create_scratchpad, update_scratchpad, finalize_scratchpad, handoff]
    tags: [context, scratchpad, working_memory, handoff, session]
---

# Context & Scratchpad

Manage working memory and session context — create scratchpads, pack context for handoffs, and analyze session state.

## When to Use

- When building up context across multiple tool calls
- Before handing off to another session or agent
- To analyze what's been accomplished in a session
- When working memory is getting too large
- To pack context for efficient transfer

## How to Invoke

```python
# Create a scratchpad
wm(route="gana_heart.create_scratchpad", args={"topic": "...", "content": "..."})

# Update scratchpad
wm(route="gana_heart.update_scratchpad", args={"id": "...", "content": "..."})

# Get session context
wm(thought="what's my current session context")
wm(route="gana_heart.get_session_context", args={})

# Pack context for handoff
wm(route="gana_heart.context_pack", args={})

# Analyze scratchpad
wm(route="gana_heart.analyze_scratchpad", args={"id": "..."})

# Finalize and handoff
wm(route="gana_heart.handoff", args={})
```

## Scratchpad Lifecycle

1. **Create** — Start a new scratchpad with a topic
2. **Update** — Add findings, notes, progress
3. **Analyze** — Review what's been collected
4. **Finalize** — Mark as complete
5. **Handoff** — Pack into transferable context
