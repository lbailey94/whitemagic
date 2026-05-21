# Tracked Markdown Audit — 2026-05-21

**Status**: Initial tracked-files-first Markdown pass  
**Scope**: Tracked `.md` / `.mdx` files only; auxiliary/private corpora deferred  
**Started**: 10:43:54 EDT 2026-05-21

---

## Inventory

After commit `bbc9530`, the tracked Markdown/MDX corpus contains **250 files**.

| Bucket | Count | Initial Reading |
|--------|-------|-----------------|
| `core/docs` | 46 | Package docs; must remain under `core/` but need README/link cleanup |
| `docs/message_board` | 41 | Active workspace plus historical/grant/internal material; highest stale-risk bucket |
| `grimoire` | 38 | Canonical Gana/grimoire source; correct location, but index/count language needs refresh |
| `docs/public` | 19 | Public-facing docs; several README links point to old folder layout |
| `root` | 12 | Canonical project identity and AI handoff docs; recently refreshed under Option C |
| `core/whitemagic` | 10 | Package/runtime embedded docs and MCP instructions |
| `docs/essay_frameworks` | 9 | Publication/Aria-canon candidates; mostly stubs or research seeds |
| `core/eval_aux` | 7 | Evaluation/benchmark auxiliary docs; should remain core-adjacent |
| `docs/reports` | 6 | Historical reports; likely archive/report folder is correct |
| `docs/adr` | 5 | Accepted architectural decisions; correct location |
| `docs/strategy_manifestos` | 5 | Mixed public thesis and private strategy; needs visibility review |
| `polyglot/codex` | 5 | CODEX pipeline docs; keep under polyglot unless promoted to public narrative |
| `apps/site` | 4 | Site-specific docs; some aliases point to older doc paths |
| `docs/architecture` | 4 | Durable architecture docs; generally correct |
| `docs/plans` | 4 | Planning docs; some alias paths stale |
| `polyglot/mojo` | 4 | Mojo implementation docs; keep under polyglot |
| `polyglot/whitemagic-koka` | 4 | Koka implementation docs; keep under polyglot |
| `docs/spec` | 3 | Specs; likely correct but contains MandalaOS-adjacent material requiring audience review |
| `core/sdk_aux` | 2 | SDK docs; keep with SDK sources |
| `core/whitemagic-rust` | 2 | Rust package docs; keep with Rust sources |
| `docs/operations` | 2 | Operational docs; likely correct |
| Single-file buckets | 10 | `.github`, `apps`, `core`, `docs`, `polyglot`, and root singletons |

---

## High-Signal Findings

### 1. Canonical root docs are now the cleanest source of truth

Root docs were refreshed in the committed Truth Spine patch. They now encode Option C test-count language and should remain the first source for public identity and AI onboarding.

**Disposition**: keep root docs stable; only edit with doc-drift verification.

### 2. `docs/message_board` remains the highest-priority cleanup bucket

The active message board contains 41 tracked Markdown files after the new audit docs were added. The new manifest `docs/content_triage_2026-05-21.json` classifies the previous 39 files; the two new May 21 docs are active workspace records.

Stale-sensitive signals are concentrated here:

- Old counts: `2,154`, `2,180`, `2,185`
- Grant deadlines: `May 17`, `May 31`
- Active grant language: `submitted`, `Status: Active`
- Internal strategy and funding probability estimates

**Disposition**: next move pass should reduce `docs/message_board` to active handoff and active working docs only.

### 3. `docs/README.md` describes an older documentation layout

Observed issues:

- Says documentation structure is `v21.1`
- Points AI agents to `public/AI_PRIMARY.md`, while current canonical AI onboarding lives at root `AI_PRIMARY.md`
- Describes `docs/internal/`, but that folder does not currently exist
- Mentions `docs/private/` correctly in spirit, but it now needs alignment with the May 21 private-docs policy

**Disposition**: update soon as part of a tracked-doc link/layout cleanup.

### 4. `core/docs/README.md` contains stale links

Observed issues:

- Points to `../whitemagic/grimoire/00_PROLOGUE.md`, which does not exist from `core/docs`
- Points to `../../docs/misc/SYSTEM_MAP.md` and `../../docs/misc/AI_PRIMARY.md`, which are stale paths
- Still useful as a package-doc index, so it should stay in `core/docs`

**Disposition**: update links only; do not move core docs into project-level `docs/`.

### 5. `docs/public/README.md` appears pre-reorg and link-heavy stale

Observed issues:

- Points to many missing `guides/`, `design/`, `plans/`, `strategy_manifestos/`, and `community/` paths under `docs/public`
- Has references like `misc/AI_PRIMARY.md` that are no longer current
- May be superseded by root `README.md`, root `INDEX.md`, and current site content

**Disposition**: either rewrite as a compact public docs landing page or archive if not used by the site/package.

### 6. `grimoire/` is correctly canonical but has stale index claims

Observed issues in `grimoire/00_INDEX.md`:

- `Version: 22.0.0` while the current baseline is v22.2.0
- `Tools: 28 PRAT Gana meta-tools + 453+ internal callable tools` while the current surface is 479 callable / 451 dispatch / 28 Gana
- `Benchmark: LoCoMo 78.3% recall accuracy` appears as a strong claim and should be verified or relabeled

**Disposition**: keep files in root `grimoire/`; patch index/count language after checking `grimoire/TRUTH_TABLE.md` and doc drift.

### 7. Strategy and grant material is valuable but mixed-audience

Tracked strategy/grant material spans:

- `docs/message_board/*GRANT*`
- `docs/archive/grant_applications/*`
- `docs/strategy_manifestos/*`
- `docs/plans/ROADMAP.md`
- publication seeds like `KARMA_LEDGER_PAPER_OUTLINE.md`

The content is directionally useful, but much of it contains stale deadlines, private strategy, and probability estimates.

**Disposition**: keep tracked for now, but separate into:

- internal grant strategy
- public publication candidates
- historical archive
- active roadmap

### 8. App/site docs are mostly scoped but contain old alias paths

Observed in `apps/site/README.md`:

- Refers to `@docs/SESSION_STATE.md`, while the tracked file is `docs/message_board/SESSION_STATE.md`
- Site docs should remain under `apps/site`, but cross-links need current repo paths

**Disposition**: patch link aliases later; do not move site docs.

---

## Link/Stale Signal Scan Summary

A simple tracked-only scan found:

| Signal | Count | Meaning |
|--------|-------|---------|
| Old test counts `2,154` / `2,180` / `2,185` | 7 files total | Mostly historical message-board docs |
| `2,216 tests` / `2,216 passed` | 22 file hits | Some are valid release baseline, many grant/public docs need Option C labeling if public-facing |
| `2,243` | 7 files | Current baseline references in refreshed canonical/handoff docs |
| May 2026 grant deadlines | 14 file hits | Grant and strategy docs are time-sensitive/stale |
| Stale path aliases | 10 files | `docs/misc`, `@docs/SESSION_STATE`, `public/AI_PRIMARY`, etc. |
| Markdown link issues | 53 rough hits | Includes real missing links plus some false positives from placeholders/example syntax |

---

## Recommended Tracked-Docs-First Order

### Pass 1 — Link and index hygiene

Patch the obvious stale path/index docs:

- `docs/README.md`
- `core/docs/README.md`
- `docs/public/README.md`
- `apps/site/README.md`
- `docs/plans/ROADMAP.md`
- selected stale alias mentions in strategy manifests

### Pass 2 — Grimoire index truth refresh

Patch only index-level stale claims:

- `grimoire/00_INDEX.md`
- possibly `grimoire/README.md`
- verify against `grimoire/TRUTH_TABLE.md` and registry counts

### Pass 3 — Message-board move batch

Use `docs/content_triage_2026-05-21.json` to move:

- historical archive docs to `docs/archive/`
- grant-internal docs to an agreed internal/private location
- publication candidates to a holding area after claim hygiene

### Pass 4 — Strategy/grants consolidation

Consolidate stale grant docs into a smaller, current internal strategy corpus. Preserve source docs, but prevent stale deadlines or probability estimates from becoming public truth.

### Pass 5 — Publication pipeline

Promote only claim-checked publication seeds:

- Karma Ledger
- PRAT/Gana compression
- Voice Audit
- Dharma/Karma governance
- 5D memory / galactic lifecycle
- Harmony Vector / telemetry

---

## Recommended Discussion Before Moving Files

Before moving tracked files, decide:

1. Should internal grant/strategy docs stay tracked under a new `docs/internal/` folder, or move to ignored `docs/private/`?
2. Should `docs/public/README.md` be rewritten or archived?
3. Should `docs/message_board` be aggressively reduced now, or only after we finish the broader tracked corpus review?
4. Should publication candidates get a new tracked folder such as `docs/research/` or `docs/publications/`?

---

## Auxiliary Corpora Boundary

This pass intentionally did not inspect or move `whitemagic-aux` or `auxiliary projects` beyond counting them. They should be discussed after tracked docs because:

- `whitemagic-aux` appears to be archive/reference material and may contain historical code/docs.
- `auxiliary projects` contains separate projects like Fragment and STRATA and should remain independent.
- Both can inform WhiteMagic, but neither should be merged into public docs without explicit review.
