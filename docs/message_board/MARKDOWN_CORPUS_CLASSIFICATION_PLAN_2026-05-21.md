# Markdown Corpus Classification Plan — 2026-05-21

**Status**: Phase C initial inventory and taxonomy  
**Scope**: Tracked WhiteMagic Markdown/MDX first; auxiliary/private corpora only by explicit pass  
**Start time**: 10:36:28 EDT 2026-05-21

---

## Inventory Snapshot

| Corpus | Count | Notes |
|--------|-------|-------|
| Tracked WhiteMagic `.md` / `.mdx` | 248 | Public/repo-relevant classification target |
| All visible `.md` / `.mdx` excluding common build/cache dirs | 3,652 | Includes ignored/private/auxiliary material |
| `docs/message_board` tracked Markdown | 39 | Classified in `docs/content_triage_2026-05-21.json` |
| Untracked public Markdown | 1 | `DOCS_HYGIENE_PATCH_SUMMARY_2026-05-21.md`, intentionally created and indexed |

## Largest Visible Buckets

| Bucket | Count | Disposition |
|--------|-------|-------------|
| `whitemagic-aux` | 2,271 | Auxiliary/archive material; do not upload publicly without explicit review |
| `auxiliary projects` | 1,082 | Separate projects; keep independent and ignored |
| `docs` | 117 | Main project documentation corpus |
| `core` | 74 | Package-specific documentation; keep separate from root/project docs |
| `grimoire` | 38 | Canonical Gana/grimoire source |
| `WhiteMagic-Grants` | 28 | Grant corpus; likely internal/stale strategy |
| `polyglot` | 15 | Polyglot implementation docs |
| `apps` | 7 | Site/app docs |

## Classification Taxonomy

| Class | Meaning | Default Destination |
|-------|---------|---------------------|
| Canonical root | Public project identity, install, governance, AI handoff | Repository root |
| Active workspace | Current cycle planning, handoff, and triage | `docs/message_board/` |
| Public docs | Contributor/user-facing public docs | `docs/public/` or topical public folder |
| Core package docs | Distributable package docs | `core/docs/` |
| Grimoire canonical | 28 Gana / garden source material | `grimoire/` |
| Architecture / ADR | Durable design decisions | `docs/architecture/` or `docs/adr/` |
| Internal strategy | Business, grants, positioning, tactical plans | Internal/private strategy folder after visibility decision |
| Private Garden / Aria | Persona, Vaya Vida, ontology, local handoff | Ignored `docs/private/` |
| Historical archive | Superseded plans, old audits, completed reports | `docs/archive/` with topical subfolders |
| Publication candidate | Paper, whitepaper, essay, or site-seed material | Hold until claim hygiene, then `docs/research/`, `docs/public/`, or site content |
| Auxiliary project | Fragment, STRATA, Edge Chat, or other independent projects | Keep separate; do not merge into WhiteMagic |

## Recommended Fragment-Assisted Pass

1. Build or refresh a Fragment index over the tracked WhiteMagic corpus first.
2. Query for stale counts, stale deadlines, grant/funder language, private/persona language, and publication candidates.
3. Repeat over ignored auxiliary/private corpora only with an explicit output boundary: classify references, but do not move auxiliary project files into WhiteMagic.
4. Produce a move manifest before any large file move.
5. Update `INDEX.md` in the same commit as any move.
6. Run doc drift, version check, and full core tests after each move batch.

## Initial Move Batches

| Batch | Scope | Risk | Notes |
|-------|-------|------|-------|
| 1 | `docs/message_board` historical archive docs | Low | Classification complete; move after confirming archive subfolder names |
| 2 | Grant/internal strategy docs | Medium | Needs visibility decision: tracked internal vs ignored private |
| 3 | Publication candidates | Medium | Requires claim hygiene and public/private review |
| 4 | Core docs | Medium | Must preserve `core/` package boundary |
| 5 | Auxiliary/private corpora | High | Read/classify only unless explicitly asked to move |

## Guardrails

- Do not merge Fragment, STRATA, Edge Chat, or other auxiliary projects into WhiteMagic.
- Do not expose Aria, Vaya Vida, Garden, or private ontology material in public docs by default.
- Do not collapse `core/docs/` into project-level `docs/`; `core/` is a separate distributable package.
- Do not move Grimoire markdown out of root `grimoire/`; it is canonical.
- Use Option C metrics language for all test counts.
- Keep runtime/generated state out of the repo.
