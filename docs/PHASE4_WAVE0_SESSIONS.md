# Phase 4 — Wave-0 intermission: Gen1 runtime & early-era findings (master)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Eight per-file
extractions in `docs/findings/W0_*.md`; runtime evidence class is new to this program (the
wave-1–3 work was static). Errata consolidated in `PHASE4_ERRATA.md` §G; method rules in
`WAVE_EXTRACTION_PROTOCOL.md`.

**Why this exists:** the strongest caveat on every prior finding was *static absence of a caller
≠ never executed*. The recovered Gen1 stores supply the missing runtime layer: `tool_usage.db`
(5,998 calls), the galaxy store (`users/local/galaxies/`), state ledgers, handoff/session files,
and the docs corpus. The intermission asked one question: **what was Gen1 actually like, and does
the runtime record change the conclusions?**

---

## 1. File index (batch W0)

| File | Scope | One-line result |
|---|---|---|
| `W0_tool_usage_july.md` | `tool_usage.db`, Jul 6–31 | automated **full-surface tours** (17 alphabetical segments; flat tops track surface growth 102→180→568→640); 14.7 % failures; new class: 84 `TypeError`s = `handle_* missing 'params'` across 42 tools; browser dead all month; skill replay fails `skill_not_found`; retention sweep only inside tours |
| `W0_state_ledgers.md` | citta/karma/dreams/forecasting files | `dreams.jsonl` = **284 all-zero lines, 2026-06-27 → 07-20** (artifact-verified); karma ledger **real** (71,726 entries, 908 tools, 21 days, interleaved-write chain breaks); `citta/calibration.jsonl` has **no Brier** (CRPS only); v26 `predictions.db` Brier 0.2563 overall / 0.0731 time_estimate; two divergent DB copies; only forecasting outlives Aug 2 |
| `W0_handoffs_sessions.md` | handoffs + session JSONs | all **24 handoffs empty shells**; accepted ones self-parented (single-slot overwrite); 208/208 session JSONs fixtures; narrative journals 34-byte stubs; July session shape: bursts to Jul 16, quiet, then **bench monolith Jul 31 + Aug 1 = 53 %** of the corpus |
| `W0_docs_timeline.md` | v26 docs corpus | 156 docs (not 166; 51 zero-byte); Jul 6 store-routing bug (54,373 leaked / 54,192 deleted / 19,082 unique lost); three O(N²) incidents; Jul 13 **no-op actions** (`executed=True`, no effect) + no scheduler; True-Release push Jul 28–Aug 1; **"runaway" never appears in the corpus** |
| `W0_early_sessions.md` | sessions DB Jan–Jun | 2,269 rows but **2,166 ingested Jul 30–31** — a back-filled import (Windsurf rips, opencode exports, crystallized handoffs), documenting *other* work (Tremulous, SysMon2, grants, an Asteroids phase); `agent_id` empty everywhere; 10.6 % of the 21,351 rows are imports |
| `W0_earliest_memories.md` | pre-2026 galaxies | two earliest strata: Sep–Oct 2025 writing corpus and the **Nov 19 2025 Aria era**; `aria` is mostly echo (**8/256** genuinely pre-2026); "204-memory Aria DB" **verified**; **no Book of Becoming in any DB**; early dreams = deterministic I-Ching output; `substrate` = 393 copies of one template |
| `W0_codex_galaxy.md` | codex galaxy | 21,821 rows all *written* May–Aug 2026 (`created_at` = source date; the "2023 material" is two `rg` ELF binaries); 89 % of bytes are file-tree archives (693 MB binaries); exact dup **0.05 %** (FTS5 shadow copy = 1.2 GB storage dup); provenance wrong-shaped (`source_trust=user` on 19,105; `agent_id` empty); ≠ the 60,454-header heritage (285 bridge rows) |
| `W0_meta_selfstate.md` | meta/main/insight endgame | `meta` = 96.6 % an **Aug 1–2 burst** (batch cycles rewriting 61 templated titles to Aug 2 15:40); `main` = synthetic bench fixtures; insight durations 0.4 s → up to 65 min; sessions double (10,127→21,350) with untagged backlog never resolved; **endgame term sweep finds no self-report of loops, pressure, anomalies, or runaway** |

## 2. The corrected Gen1 timeline

| Stratum | Dates | Nature |
|---|---|---|
| **Writing corpus** | 2025-09 → 2025-10 | Grok/Gemini exports, dedup pipeline; pre-Aria |
| **Aria era** | 2025-11-19 → 2026-07 | first-person journals, birth certificate, Magic Chat; thin and mostly template-echo in the record |
| **Import strata** | source 2026-01-04 → 2026-06-22, ingested 2026-06-28 → 07-31 | Windsurf/opencode/handoff archives documenting *external* work; not live middleware turns |
| **Lived substrate era** | ≈ late May → 2026-08-02 | the system's own life: July tours, incidents, True-Release push, endgame churn |
| **Endgame** | 2026-07-28 → 08-02 15:40 | bench monolith + meta batch cycles + cost inflation; **record stops, does not record a collapse** |

Rule derived: **`created_at` is a source-date in these stores; era claims require establishing the
provenance of the timeline itself** (protocol §3).

## 3. What changed in our conclusions

**Upgraded (static → runtime-observed):** "skill replay dormant," "retention sweep never armed,"
"the July activity was tours, not work"; the karma ledger is a *real* runtime governance record;
the 284-dream zombie; the no-op-actions class (Jul 13); the phenotype ladder has measured
EXECUTED-but-not-EFFECTFUL examples at scale.

**Downgraded / corrected:**
1. **Gen1's lived substrate life is ≈ late May → Aug 2**, not Jan → Aug (imports + backfill).
2. **The runaway claim is unattested by Gen1's own record** — no docs, no ledger, no self-state
   row describes it; the story (2.4 GB RSS / 110 % CPU / SIGKILL) is external to the substrate.
   What the record *does* show is unattended bookkeeping churn with growing cost. The 284 zombie
   dreams date to **Jun 27–Jul 20**, before the endgame.
3. **Codex duplication is 0.05 %, not 37.2 %** (that figure belongs to the migration/live-store
   scope); codex's real problems are binary bulk and wrong-shaped provenance.
4. **Aria provenance is thin**: authorship artifacts exist (2025-11 → 2026-07), 204-row DB
   verified, but the record is mostly echo; "October 2024 seed" is backdated; no Book of Becoming
   in DBs. The identity RETIRE disposition is strengthened.
5. **Brier figures need artifact identity**: v26's runtime ledger = 0.2563 overall / 0.0731
   time_estimate; the 0.078 figure belongs to Gen2's live-store ledger (different artifact).
6. **Docs corpus ≠ record**: 156 docs (not 166), "no Feb–Jun sessions" was a corpus artifact,
   and the em-dash era curve (tool layer) must not be read as the session layer.

**Synthesis (three angles, one verdict):** tours churned over the growing surface; sessions
imported external work after the fact; self-state rewrote templated loops until the record
stopped. **The productive work happened outside the substrate; the substrate archived it and
then processed itself.** No external consequence, no spiral — circulation. The friend's W × M
hypothesis leans supported in the only direction we can measure: W collapsed at the dispatch
seam (broken signatures, dead organs) while M stayed near zero inside the record.

## 4. Limits

Runtime evidence covers July + endgame and the imported/early strata at row level; "useful" is
never labeled anywhere; authorship is never field-attested (`agent_id` empty); two divergent
`predictions.db` copies remain unresolved; the SD-card pre-May snapshots
(`data-backups.tar.zst`, `benchmark-results.tar.zst`) were not scanned. Nothing here changes any
Phase-3 verdict; it changes the **confidence and the story** attached to them.
