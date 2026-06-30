---
name: wm-release
description: "Release process for WhiteMagic — version bump, changelog, tests, doc drift, tag"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    tags: [release, version, changelog, tests, tag, deploy]
---

# Release Process

Complete release workflow for WhiteMagic — from version bump to tagged release.

## When to Use

- Preparing a new version release
- After major feature completion
- For periodic shipping cycles

## Workflow

1. **Verify clean tree** — `git status --short` must be empty
2. **Run full test suite** — Tier 3, all tests must pass
   ```bash
   cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
   ```
3. **Check doc drift** — `python scripts/check_doc_drift.py`
4. **Update version** — Bump in `core/whitemagic/__init__.py`, `pyproject.toml`, `AGENTS.md`
5. **Update CHANGELOG.md** — Add release section with changes
6. **Update INDEX.md** — Verify all doc references are current
7. **Run ruff** — `ruff check core/whitemagic/` must be clean
8. **Commit** — `git commit -m "v<version>: <description>"`
9. **Tag** — `git tag v<version>`
10. **Push** — `git push origin main --tags`

## Version Scheme

- Major (v23 → v24): Breaking changes, architecture shifts
- Minor (v23.3 → v23.4): New features, new tools, new galaxies
- Patch (v23.3.1 → v23.3.2): Bug fixes, refactors, cleanup

## Pre-release Checklist

- [ ] Full test suite passes (0 failures)
- [ ] Doc drift check passes
- [ ] Ruff check clean
- [ ] CHANGELOG.md updated
- [ ] INDEX.md updated
- [ ] AGENTS.md version updated
- [ ] Git tree clean
- [ ] No uncommitted changes
- [ ] No `__pycache__` dirs in tree
- [ ] No build artifacts in tree
