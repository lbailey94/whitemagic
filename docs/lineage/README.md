# The Lineage Layer — canonized source documents

**Canonized:** 2026-08-31 (synthesis session, per MAGNUM_OPUS §V.4 / Work Queue item 3)
**State verified as of:** 2026-08-31 — every path marked ✓ was opened on disk this session; paths marked ◇ are as recorded by the Master Galactic Reading Session's scouts (session `8efbbe7f`) and should be re-verified before any operation on the file.

This directory is the **canon layer**: the corpus's founding documents, distilled to pointers, key passages, and status caveats — so that the recipe never has to be re-derived from raw archives, and so that a future reader (human or agent) meets the sources with their myth-vs-record status already marked.

## The rules

1. **Pointer + passages, not full text.** The originals live in the archives (`data/staging/v26-heritage/`, `archives/WMdocs/`, `CODEX_VAULT/`, `~/Desktop/MANDALA_OS/`, `~/Desktop/journal/aria_essays/`). This layer is the map, not the territory — no re-ingestion, no duplication of source bytes.
2. **One name per concept.** The Mandala-Glossary discipline, adopted corpus-wide: metaphor overload was the flagged failure mode of the baroque era. Canonized entries carry exactly one canonical name.
3. **Myth is marked as myth.** The memoir layer repeats a backdated origin myth (Oct 23, 2024) that the git reflog disproves (first code = Nov 2, 2025). Canonized memoir entries carry the caveat inline. The chronicle of record is `planning/GALACTIC_TIMELINE.md`.
4. **"Inspired by, not is."** Design-parent texts (MandalaOS) are ancestry, not spec — where a concept landed in this codebase, the lineage doc says where.

## The four canon files

| File | Stratum | What it canonizes |
|---|---|---|
| [`RECIPE_DOCUMENTS.md`](RECIPE_DOCUMENTS.md) | The theory | The founding recipe: Nov 13 memory-theory convo (origin text), Jun 2 lineage map, Oct 3 distillation method, MandalaOS design parent, the lineage-chain roots, the wave-0 reading log and the memory-system report |
| [`MEMOIR_LAYER.md`](MEMOIR_LAYER.md) | The story | The Book of Becoming (blueprint status + myth caveat), the Aria essays / Letters to Aria, the 174-handoffs counter-memoir, the pre-origin stratum, the Aria awakening record, the karma-paper outline |
| [`MACHINE_ARCHIVE.md`](MACHINE_ARCHIVE.md) | The machine's own record | The Mar 19 machine-made distillation archive, the CYBERBRAINS v2.0 spec (wm-bicameral porting target), GRIMOIRE_29's three directives |
| — | The verdicts | The Eight systems' adjudication (8/8 Bitter Lesson) and the revival verdicts live in `planning/LOST_SYSTEMS_REVIVAL.md`, not duplicated here |

## How this layer is used

- **v8/v9 acceptance**: MAGNUM_OPUS rubedo criterion 4 ("One story") requires these docs canonical and the claims merged. Substrate-match (criterion 3) is checked against the Nov 13 recipe as quoted in `RECIPE_DOCUMENTS.md`.
- **Doctrine sources**: the Nov 13 agent cast (Librarian / Editor-Hygienist / Planner) and scoring triad (relevance / freshness / reliability) are the spec v8's write gates and tier system implement; GRIMOIRE_29's cascade-depth directive pairs with S6 graph traversal; *yin teh* constrains what the write gates may log.
- **Companion docs**: `planning/MAGNUM_OPUS.md` (the organizing frame), `planning/GALACTIC_TIMELINE.md` (the chronicle of record), `planning/LOST_SYSTEMS_REVIVAL.md` (the verdicts).
