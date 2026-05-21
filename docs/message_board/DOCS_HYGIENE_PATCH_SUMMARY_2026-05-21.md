# Docs Hygiene Patch Summary — 2026-05-21

**Status**: Commit-ready patch narrative  
**Scope**: Truth Spine, private-docs policy, active handoff refresh, and message-board triage  
**Last verified**: 2026-05-21

---

## Suggested Commit Message

```text
docs: refresh truth spine and classify active workspace
```

## Summary

This patch refreshes WhiteMagic's documentation truth spine and prepares the active documentation workspace for deeper corpus classification.

## Main Changes

- **Option C metrics policy**: Canonical docs now distinguish the frozen `v22.2.0 release baseline` from the `current local audit baseline`.
- **Doc drift enforcement**: `core/scripts/check_doc_drift.py` now validates labeled release/current audit test-count references instead of requiring a single shared count.
- **Private docs policy**: `docs/private/` is documented as ignored, local-only space for Aria, Vaya Vida, Garden, ontology, and private handoff material.
- **Root Markdown hygiene**: Previously untracked root Markdown docs were classified and moved into ignored private documentation folders.
- **Active handoff refresh**: `docs/message_board/SESSION_SUMMARY.md` now starts with a May 21 addendum that marks older April content as historical.
- **Message-board triage**: `docs/content_triage_2026-05-21.json` classifies all 39 current `docs/message_board` Markdown files by audience, freshness, and disposition.
- **Index correction**: `INDEX.md` now points archived grant application drafts to `docs/archive/grant_applications/` instead of listing them as active message-board docs.

## Touched Files

- `.gitignore`
- `AGENTS.md`
- `AI_PRIMARY.md`
- `INDEX.md`
- `README.md`
- `SYSTEM_MAP.md`
- `core/scripts/check_doc_drift.py`
- `docs/content_triage_2026-05-21.json`
- `docs/message_board/DOCS_HYGIENE_PATCH_SUMMARY_2026-05-21.md`
- `docs/message_board/SESSION_SUMMARY.md`
- `docs/public/SYSTEM_MAP.md`
- `skill.md`

## Current Baselines

| Baseline | Result |
|----------|--------|
| v22.2.0 release baseline | 2,216 passed, 67 skipped, 0 failed |
| Current local audit baseline | 2,243 passed, 67 skipped, 0 failed as of 2026-05-20/21 |
| Tool surface | 479 callable tools, 451 dispatch entries, 28 Gana meta-tools |

## Verification Commands

```bash
cd /home/lucas/Desktop/WHITEMAGIC/core
WM_STATE_ROOT=/tmp/whitemagic_handoff_refresh_state ../.venv/bin/python scripts/check_doc_drift.py
../.venv/bin/python scripts/check_versions.py
WM_STATE_ROOT=/tmp/whitemagic_handoff_refresh_state ../.venv/bin/python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q
```

## Last Known Verification

- **Doc drift**: passed
- **Version check**: passed
- **Full core suite**: 2,243 passed, 67 skipped, 1 warning
- **Untracked public Markdown**: none via `git ls-files -o --exclude-standard '*.md'`

## Follow-Up

- **Next docs move pass**: Use `docs/content_triage_2026-05-21.json` to move historical archive, grant-internal, and publication-candidate documents into appropriate folders.
- **Broader corpus pass**: Scale the same classification taxonomy to the full Markdown corpus, ideally with Fragment-assisted retrieval.
- **Later code work**: Resume code hygiene and runtime improvements after docs classification phases are complete.
