---
name: wm-session
description: "Session lifecycle — bootstrap, checkpoint, resume, and handoff conversations"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_horn
    tools: [session_bootstrap, create_session, resume_session, checkpoint_session, focus_session, handoff_session]
    tags: [session, lifecycle, bootstrap, checkpoint, handoff]
---

# Session Management

Manage AI session lifecycle — bootstrap new sessions, checkpoint state, resume from prior context, and hand off between sessions.

## When to Use

- Starting a new conversation or work session
- Need to save progress before ending a session
- Resuming work from a previous session
- Handing off context to another AI instance
- Need to focus a session on a specific task

## How to Invoke

```python
# Bootstrap a new session
wm(thought="start a new session")
wm(route="gana_horn.create_session", args={"title": "..."})

# Checkpoint current state
wm(thought="checkpoint my session")
wm(route="gana_horn.checkpoint_session", args={})

# Resume from checkpoint
wm(thought="resume my last session")
wm(route="gana_horn.resume_session", args={"session_id": "..."})

# Hand off to next session
wm(thought="handoff this session")
wm(route="gana_horn.handoff_session", args={})
```

## Common Workflows

### New Session Setup
1. Bootstrap session → loads quickstart guides, recent memories, galaxy status
2. Check system health via `gana_root.health_report`
3. Introspect current state via `gana_ghost.gnosis`
4. Surface serendipity via `gana_abundance.serendipity_surface`

### Session Handoff
1. Checkpoint current session state
2. Generate handoff summary
3. Next session resumes with full context

## Notes

- Sessions persist across MCP disconnects
- Checkpoints include working memory, scratchpad, and tool call history
- Handoff docs are stored in `docs/message_board/` by convention
