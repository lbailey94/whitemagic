---
name: wm-memory
description: "Create, update, search, and manage persistent 5D holographic memories"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_neck
    tools: [create_memory, update_memory, delete_memory, import_memories, clone_memory]
    tags: [memory, create, update, holographic, 5d, galaxy]
---

# Memory Operations

Store, update, and manage persistent memories with 5D holographic coordinates (temporal, semantic, emotional, relational, importance).

## When to Use

- After discovering important project context future sessions need
- When the user explicitly asks to remember something
- After completing a major milestone or architectural decision
- Before starting a complex task — recall relevant context first
- When project state changes and memories need updating

## When NOT to Use

- For trivial facts that won't be needed later
- For information already in files (code, docs, AGENTS.md)
- For ephemeral conversation context

## How to Invoke

```python
# Create a memory
wm(thought="create memory about the new authentication system")
wm(route="gana_neck.create_memory", args={
    "title": "Auth System Design",
    "content": "...",
    "tags": ["auth", "security"]
})

# Update an existing memory
wm(thought="update memory about database migrations")
wm(route="gana_neck.update_memory", args={"id": "...", "content": "..."})

# Search memories (uses gana_winnowing_basket)
wm(thought="search for memories about database migrations")
```

## Memory Types

- **ARIA** — Agent persona memories
- **CITTA** — Consciousness-stream memories (auto-persisted)
- **CODEX** — Codebase knowledge
- **JOURNALS** — Development journals
- **DREAMS** — Dream cycle outputs, oracle readings
- **RESEARCH** — Research findings
- **SESSIONS** — Session state and handoffs
- **SUBSTRATE** — System state
- **TUTORIAL** — Tutorial and onboarding
- **UNIVERSAL** — General purpose (default)

## 5D Coordinates

Every memory has coordinates: `(x:temporal, y:semantic, z:emotional, w:relational, v:importance)`. These enable holographic recall — finding memories by similarity across any dimension.
