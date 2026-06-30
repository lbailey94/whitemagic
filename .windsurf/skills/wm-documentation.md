---
description: WhiteMagic documentation conventions — INDEX.md, message board, grimoire, doc drift
---

# WM Documentation

## INDEX.md
- Single source of truth for document locations
- Adding a doc → update INDEX.md in same commit
- Moving a doc → `git mv`, update all references, update INDEX.md
- Archiving → move to `docs/archive/`, add `> **Superseded by**: [new path]`

## Message Board
`docs/message_board/` is the active workspace. Move to topical folders or archive when cycles end.

## Grimoire
`grimoire/` (root) = canonical markdown. `core/whitemagic/grimoire/` = Python code only. Never duplicate .md files.

## Doc Drift Detection
```bash
python core/scripts/check_doc_drift.py
```
Validates: garden count (28), gana tool count (28), dispatch table matches registry, version consistency, no stale directory references.

## Core vs Docs
`core/` is a separate distributable package. Do not merge its docs with `docs/`.
