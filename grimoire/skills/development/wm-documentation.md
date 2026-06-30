---
name: wm-documentation
description: "Documentation conventions — INDEX.md, message board, grimoire, doc drift, core vs docs"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [documentation, index, message_board, grimoire, drift, core]
---

# Documentation Conventions

## INDEX.md
- Single source of truth for document locations
- Adding a doc → update INDEX.md in same commit
- Moving a doc → `git mv`, update all references, update INDEX.md
- Archiving → move to `docs/archive/`, add superseded note

## Message Board
`docs/message_board/` is the active workspace. Keep only current-cycle docs. Archive to `docs/archive/` subfolders when cycles end.

## Grimoire
`grimoire/` (root) = canonical markdown. `core/whitemagic/grimoire/` = Python code only. Never duplicate .md files in core.

## Doc Drift Detection
```bash
python scripts/check_doc_drift.py
```
Validates: garden count (28), gana tool count (28), dispatch table matches registry, version consistency, no stale directory references.

## Core vs Docs
`core/` is a separate distributable package. Do not merge its docs with `docs/`.

## Skills
`grimoire/skills/` contains portable SKILL.md files. See `SKILL_LIBRARY.md` for the full index.
