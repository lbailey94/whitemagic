# W0 — codex galaxy inventory + samples

**Status:** findings · 2026-09-17 · read-only; codex galaxy inventory + samples
**Store:** `/home/lucas/Desktop/WHITEMAGIC_GEN1_v26.0.3/…/galaxies/codex/whitemagic.db` —
2.68 GB file, 21,821 `memories` rows, opened `mode=ro`. Sibling `main`/`meta` stores out of scope.
**Method:** python3 + sqlite3 aggregates over the full table (`COUNT`/`GROUP BY`/`SUM(octet_length)`);
no dumps. Quotes are `substr()` reads with row ids. Class labels are inferred from title + metadata
JSON unless noted; **UNVERIFIED** marks inference that could not be confirmed from this store alone.

## Scale & date structure

Row counts were run per column, because this galaxy's dates are not one timeline:

| Year (`created_at`) | rows | content bytes | what the material is |
|---|---|---|---|
| 2023 | 1 | 8,082,157 | one ELF binary, title `rg` (ripgrep) |
| 2024 | 1 | 10,232,999 | one ELF binary, title `rg` |
| 2025 | 5,243 | ~356 MB | file-archive captures (VS Code / npm trees), backdated mtimes |
| 2026 | 16,576 | ~830 MB | chunks (10,390), archive top-ups, v26 state captures |

- **The 2023/2024 material is not conversations, code, or notes.** Both rows are 8–10 MB binaries
  whose first bytes are `7F454C46020101` (ELF header): row `0f99d729-3106-…` (2023-06-26) and
  `6dd45301-e20f-…` (2024-09-08), both `title='rg'`, `source=codex_archive`. `LENGTH(content)`
  reports 7 on both — SQLite stops at the first NUL; `octet_length()` exposes the true size.
- **Ingestion-time tells a different story than `created_at`.** All 21,821 rows were written
  May–Aug 2026: 2026-05 = 10,361 · 2026-06 = 299 · 2026-07 = 11,125 · 2026-08 = 36. The store is an
  import target, not a 2023→2026 live journal; `created_at` on archive rows carries a source date
  (file mtime **UNVERIFIED** — archive rows have no `mtime` metadata key) while state-capture rows
  carry the ingest date.
- Type split: `LONG_TERM` 13,740 rows / 58.0 MB · `REFERENCE` 7,642 / **1,114.5 MB** ·
  `SHORT_TERM` 392 / 3.6 MB · `DOCUMENT` 47 / 48 KB. The `REFERENCE` tail is where the bytes live.
- Adjacent tables: 450,201 associations, 36,749 tag links over 1,744 distinct tags,
  13,240 holographic coords, 2,785 constellation memberships.
- **The 2.68 GB file is half FTS copy.** `dbstat`: `memories` 1.209 GB, `memories_fts_content`
  1.202 GB, `memories_fts_data` 0.201 GB, `associations` 45 MB. Content itself = 1,176,157,699 B
  (~1.18 GB); the FTS5 index keeps a verbatim second copy.

## Content classes

Full-population split by `metadata.source` (all rows accounted; shares by bytes):

| class (`source`) | rows | bytes | mechanism | authorship |
|---|---|---|---|---|
| `codex_archive` | 7,603 | 1,043.8 MB | wholesale filesystem archive | machine capture |
| `codex_chunks` | 10,390 | 22.6 MB | 523 documents chunked (library 6,335 · conversations 4,011 · research 44) | human-authored text, machine-chunked |
| `(none)` | 2,993 | 8.8 MB | SHORT_TERM breakthroughs, emergence/kaizen events, stubs | v26 loops (machine) |
| `codex_vault_library` | 285 | 22.5 MB | texts pulled from a vault-library corpus | human-authored / sacred texts |
| `codex_consolidated` | 266 | 7.8 MB | consolidated summaries | machine |
| `research_dag`/`emergence`/`documents`/`alltexts`/`kaizen`/`hrr`/`oracle` etc. | 567 | ~70.8 MB | DAG outputs, `alltexts` docs (39 rows / 70.7 MB) | mixed, mostly machine |

- **By rows:** chunks 48 %, archive 35 %, v26-event/stub rows 14 %, vault-library 1 %.
- **By bytes:** archive **89 %**, alltexts 6 %, chunks+vault-library ~4 %, everything else ~1 %.
- Archive categories (metadata): `ai-systems` 2,625 / 529.6 MB · `ide-configs` 2,923 / 272.1 MB ·
  `code-projects` 8 rows / 234.6 MB · `trash-review` 2,030 / 7.4 MB. It is a captured
  editor/AI-tool install tree (VS Code extension files, `.vsixmanifest`, `package.nls.*`,
  `argv.json`, `.codeiumignore`, node_modules, .NET `win-x64` runtime blobs).
- **Binary load:** 2,429 rows contain NULs in-content = 693 MB; 87 rows exceed 1 MB; the largest is
  222.1 MB (`a1ddea97-cd48-…`, title = a SHA-256 string, content-addressed blob).
- Small but real file-capture strata: `title='entries'` 1,036 rows (VS Code workspace-edit JSON),
  `METADATA` 171, `package` 160, `README` 119, `LICENSE` 113; plus 1,735 `FILE:`/`DIR:` v26 state
  snapshots (skills, sessions, `smarana/practice_log.json`, votes) totalling 1.7 MB.
- **Machine vs human:** ≥97 % of rows are machine-written captures (archive + state + event rows);
  the human-authored layer is the ~10.3k chunk rows and ~285 vault-library rows (32.6 MB, ~3 % of
  bytes). The text corpus is machine-chunked, not machine-written.

## Duplication test (the 37.2 % claim)

- `content_hash` exists on 21,773/21,821 rows (48 NULL/empty) and comes in **two generations**:
  16-hex 7,974 rows (7,970 distinct) and 64-hex SHA-256 13,799 rows (13,793 distinct).
- Exact-content duplication in this galaxy = **10 excess rows in 9 groups = 0.05 %**, not 37.2 %.
  Duplicate examples are structural re-ingests, not noise: `SOCIAL_HEART_EXTRACTS`
  (`a1afa640-…`, LONG_TERM, 2026-07-16) = `SOCIAL HEART EXTRACTS` (`151a9adb-…`, REFERENCE,
  2026-03-19); `FILE: check_import_boundaries.sh` / `CHUNK: check_import_boundaries.sh#0` captured
  three times across the 2026-07-21 and 2026-07-31 state sweeps; `DIR:c044f8ac:memory/wisdom`
  re-captured a week apart.
- Chunk-level re-ingest is absent: all 10,390 `chunk_id`s unique; 523 `document_id`s.
- Caveats: cross-scheme duplicates can never match (16-hex vs SHA-256 of the same bytes would hash
  differently), so 0.05 % is a floor for scheme-internal exact dupes only; fuzzy/near-dup was not
  tested; content-level `GROUP BY` on 1.18 GB was not run.
- **Implication for the matrix:** "59,831 migratable / 35,930 distinct / 37.2 % dup" does not
  transfer to this galaxy. If the 37.2 % figure is real, it lives in `main`+`meta` or in a
  chunk-aware definition; do not cite it for codex. Independently, the store carries ~50 %
  storage-level duplication from the FTS shadow copy.

## Heritage relationship

- Heritage ingest per the LINEAGE_LEDGER = **60,454 headers** in the vault heritage corpus (160k
  store). Codex = 21,821 rows: codex is **not** the heritage ingest, it is the v26 runtime galaxy.
- The shared layer is textual, not structural: 10,390 chunk rows (library + conversations + research,
  523 docs) plus 285 explicit `codex_vault_library` rows — the latter are vault-sourced texts
  (Tibetan Buddhist passages, conversation exports), so the codex galaxy *pulls from* the vault
  corpus; it does not contain the 60k-header ingest.
- Scale/coverage mismatch: 60,454 headers vs 10,346 codex chunk rows (5.8×). Date coverage differs
  too — chunk rows are stamped 2026-05, archive rows 2023-06→2026-04 (backdated); the heritage
  header window was not verified here (vault store out of scope).
- Caveat: `codex_vault_library` (285 rows / 22.5 MB) is the only direct provenance bridge found;
  whether its 285 rows are a sample of the 60,454 headers is **UNVERIFIED**.

## Deep reads (quotes, sparingly)

- 2023 row `0f99d729-3106-…`: `title='rg'`, `hex(substr(content,1,8))='7F454C46020101'`, 8.1 MB.
  2024 twin `6dd45301-e20f-…`: same header, 10.2 MB. (Binary, not text.)
- Library chunk `codex-chunk-doc-68ce4862-chunk-198`: *"Sensible heating from ambient (≈25 °C) to
  100 °C: ~0.1 MJ. … With a 50× concentration (i.e., 50 kW delivered to the focal receiver)…"* —
  an engineering-note corpus, not code.
- Conversations chunk `codex-chunk-doc-72426b8a-chunk-97`: *"Build **two income streams**:
  **Cash-flow** (courses, consults) … **Asset-flow** (equity, IP, real estate) … Timing & growth
  curve (Vimshottari overlay)"* — dated planning dialogue.
- Library README `095657c8-f472-…`: *"# 1_CONSCIOUSNESS — Explores the nature, origins, and
  mechanics of awareness … Neuroscience & Brainwave Technology … Meditation & Contemplative
  Practice"* — the library is topical knowledge notes.
- Archive file `4d5c9337-db20-…` (`.codeiumignore`): *"# exclude noise from Windsurf/Codeium's
  semantic index … Files are NEVER deleted or moved — this only affects what the AI sees."*
- Vault text `062e84db-f664-…`: *"(གདོད་མའི་གཞི་ gdod ma'i gzhi) … The basis is the original state
  'before realization produced buddhas and nonrealization produced sentient beings'"* — Dzogchen
  material, machine-mirrored into the galaxy.
- Workspace-edit noise `bf46f118-0408-…`: `{"version":1,"resource":"file:///home/lucas/Desktop/
  Tools/01-System-Optimization/maintenance.sh","entries":[{"id":"L03B.sh","source":"Workspace
  Edit",…}]}` — editor telemetry ingested as memory.

## Limits & unverified

- Counts come from the stated SQL; the 2.68 GB was never dumped. Full-content `GROUP BY` was not run.
- `created_at` semantics differ per class (state rows = ingest time; archive rows = backdated
  source date, inferred from 2023/2024 ELF rows existing despite 2026-07 ingest) — **UNVERIFIED**
  as "mtime" because archive rows carry no `mtime` key.
- `content_hash` scheme split limits exact-dup detection; near-duplicate content untested.
- "Human-authored" vs "machine-generated" is style inference, not provenance metadata — and the
  metadata is wrong-shaped anyway: `source_trust` = `user` on 19,105 rows, `tool_output` on 2,716,
  `agent_id` empty on all 21,821. Binaries, npm files, AI-written breakthroughs and sacred texts
  are all stamped `user` (consistent with the Phase-4.5 trigger finding).
- The vault-side 60,454-header figure was not re-verified (vault store out of scope).

## Implications

1. **The codex galaxy is three stores in one table:** an 89 %-by-bytes binary file archive
   (`codex_archive`), a ~33 MB text corpus (chunks + vault library + alltexts), and v26 state/event
   rows. Any migration that selects by row count/type will drown in binary archive content; select
   by `source` + `octet_length` instead.
2. **Do-not-migrate (preserve-as-documentation):** `codex_archive` (1.04 GB; IDE/AI-tool install
   trees, rg binaries, 222 MB content-addressed blob, `trash-review` category), the `entries`
   workspace-edit JSON (1,036 rows), and duplicate state re-captures. These are the heritage
   archive's "what the toolchain looked like", not substrate.
3. **Candidate substrate:** `codex_chunks` (library/conversation/research), `codex_consolidated`,
   `codex_vault_library`, `alltexts`, research-DAG outputs, and selected SHORT_TERM breakthroughs —
   ~33 MB of text with unique content hashes and only 0.05 % structural duplication.
4. **The 37.2 % dup claim needs re-homing:** measured against this galaxy it is 0.05 % exact-hash
   dup; the only replication of that magnitude here is the FTS5 shadow copy (1.20 GB), which is
   storage overhead, not row duplication. Matrix §2.1 should attribute the 37.2 % to its actual
   scope or drop the codex galaxy from its denominator.
5. **Timeline discipline:** `created_at` is a source-date column on archive rows and an ingest-date
   column on state rows; mixing them produced the "2023–2026" illusion. For Phase 5/v7 provenance,
   `ingestion_time` is the only write-time truth, and this galaxy has no rows older than 2026-05.
