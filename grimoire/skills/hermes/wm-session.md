---
name: wm-session
description: "Session lifecycle — bootstrap, checkpoint, resume, and handoff with WhiteMagic context"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [session, bootstrap, checkpoint, resume, handoff, context]
    related_skills: [wm-memory, wm-cognitive]
  whitemagic:
    gana: gana_horn
---

# WhiteMagic Session Management

Manage AI session lifecycle with persistent context across MCP disconnects.

## When to Use

- Starting a new work session
- Saving progress before ending
- Resuming from a previous session
- Handing off context to another agent

## How to Use

### Bootstrap New Session
```
wm(thought="start a new session")
```

### Checkpoint
```
wm(thought="checkpoint my session")
```

### Resume
```
wm(thought="resume my last session")
```

### Handoff
```
wm(thought="handoff this session")
```

## Hermes Integration

```yaml
hooks:
  pre_llm_call:
    - command: python /path/to/wm_context_hook.py
      matcher: {}
```

This injects WhiteMagic session context (coherence, depth, active gardens) into every Hermes prompt.
