---
name: wm-memory
description: "WhiteMagic memory operations — create, search, recall, and update 5D holographic memories"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, holographic, 5d, galaxy, search, create, update]
    related_skills: [wm-research, wm-governance]
  whitemagic:
    gana: gana_neck
---

# WhiteMagic Memory Operations

Use WhiteMagic's 5D holographic memory system for persistent context across sessions.

## When to Use

- After discovering important project context future sessions need
- When the user asks to remember something
- Before starting a complex task — recall relevant context first
- When updating project state that affects future work

## Prerequisites

- WhiteMagic MCP server running (`python3 -m whitemagic.run_mcp_lean`)
- `WM_STATE_ROOT` configured

## How to Use

### Creating Memories
```
wm(thought="create memory about the new authentication system")
```

### Searching Memories
```
wm(thought="search for memories about database migrations")
```

### Updating Memories
```
wm(thought="update memory about project roadmap with new timeline")
```

## Memory Galaxies

Memories are organized into 10 galaxies: `aria`, `citta`, `codex`, `journals`, `dreams`, `research`, `sessions`, `substrate`, `tutorial`, `universal`.

## Hermes Integration

Add to `~/.hermes/config.yaml`:
```yaml
hooks:
  post_llm_call:
    - command: python /path/to/wm_memory_hook.py
```

This auto-stores significant Hermes interactions as WhiteMagic memories.
