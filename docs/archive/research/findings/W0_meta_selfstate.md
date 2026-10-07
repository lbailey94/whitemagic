# W0 — Gen1 self-state galaxies: `meta`, `main`, `insight`, `creative_solutions`, `universal`, `research`

**Status: findings · 2026-09-17 · read-only; self-state rows + quotes**

Scope: six `whitemagic.db` files under `…/v26/state/users/local/galaxies/<name>/`, opened
`file:…?mode=ro`. Method: python3 + `sqlite3`; all counts row-derived from stated queries
(§Appendix); quotes shortened, cited `galaxy:id`. `RUNTIME-OBSERVED` = row exists with that
content; `INFERRED`/`UNVERIFIED` labeled. Per W0 convention, no "meaningfulness" grade is assigned.
Context read first: `W0_tool_usage_july.md`, `W0_state_ledgers.md`, `PHASE4_WAVE2_FINDINGS.md`,
`PHASE4_ERRATA.md`.

## 1. `meta` profile (7,823 rows, 21 MB, 2026-07-10T15:15 → 2026-08-02T15:40)

- Types: `LONG_TERM` 7,741 / `SKILL` 82 — **no** METRIC, REFLECTION, CYCLE or SESSION type exists.
  Only three tags exist in the whole galaxy, each on the 82 SKILL rows: `grimoire`/`skill`/
  `source:grimoire`. RUNTIME-OBSERVED.
- Classes by title (query Q1): Galaxy Summary 5,611 · Cross-galaxy Ref 1,593 · Strategic Priority
  531 · Cross-galaxy Link 6 (all Jul 10) · grimoire import 82 (all `2026-07-16T11:12:04`,
  one second) · 1 each of 00 COVER…30 DEEP YIN, README, TRUTH TABLE, MOLTBOOK SEED, etc.
- The 82 SKILL rows are a **static documentation import**, not runtime state: versioned docs
  (`v22.0.0`, `24.1.0`, internal dates Jan–Jun 2026), e.g. README — "28-fold cyclical instruction
  system"; TRUTH TABLE — "single source of truth". No self-model rows.
- Date curve (Q2): Jul 10 59 · Jul 11 3 · Jul 12 5 · Jul 13 28 · Jul 14 5 · Jul 15 17 · Jul 16 90 ·
  Jul 19 6 · Jul 21 1 · Jul 22 1 · Jul 25 3 · Jul 26 4 · Jul 29 1 · Jul 30 3 · Jul 31 43 ·
  **Aug 1 5,114 · Aug 2 2,440**. 96.6 % of the galaxy is the Aug 1–2 burst.
- Duplication: 7,823 rows carry **658 distinct contents**; Aug 1's 5,114 rows = 90 batch timestamps
  × 50–61 rows over only 61 distinct titles ("Galaxy Summary: universal" appears 133× lifetime).
- Post-Jul-20 content is galaxy **bookkeeping**, machine-templated per cycle: e.g.
  `meta_priority_0_1785542220` (Jul 31): "Refresh stale galaxies: quarantine, openai_archives,
  archive, self_discovery, journals, substrate"; knowledge gaps like `meta_priority_2_1785542220`:
  "Galaxy 'quarantine' is stale — no new memories in >7 days".
- The endgame `meta` loop: 90 Aug-1 bursts (median gap 308 s; min 27 s; 12.4 h overnight pause) and
  40 Aug-2 bursts, writing 50–61 summaries per cycle; last row `2026-08-02T15:40:08`. INFERRED: an
  unattended recurring summarizer; no process identity is recorded (tool_usage.db has no `meta.*`
  tool and its log ends Jul 31 19:57). It never summarizes `meta` itself (72 distinct
  "Galaxy Summary: X" titles; no self-entry) — meta has no recorded self-portrait.

## 2. `main` profile (4,226 rows, 41 MB, 2026-07-10T14:51 → 2026-08-01T13:35)

- 100 % `SHORT_TERM`; 200 distinct titles, **all** `bench_src/file_N.md`; 4,226/200 = ~21 copies.
  Repetition histogram: 150 titles ×22, 25 ×20, 16 ×17, 5 ×18, 3 ×21, 1 ×1 — i.e. re-import rounds
  (Jul 10 199 · Jul 26 378 · Jul 30 1,157 · Jul 31 1,895 · Aug 1 597).
- Content is synthetic fixture, e.g. `e0c8e57c391dc1ce` (Jul 10): "# File 118 / This is test
  content for file number 118." repeated to ~2.6 KB. Metadata: `"source_path":
  "…/imports/bench_src/file_118.md"`, `"surprise_boosted": true`, `"surprise_score": 10.0`,
  `"reinforcement_count": 10`.
- Verdict: `main` is the tracker's "test content" **confirmed** — a benchmark/ingestion target
  (`ingested`, `galaxy:main`, `source:md`), no self-state, no free text about the system.

## 3. `insight` / `creative_solutions` / `universal` / `research`

- **insight** (67 rows, all `LONG_TERM`, Jul 10→Aug 2; 11/12/23 on Jul 10–12, then 1 each Jul
  13/15/19, 1 Jul 28, 7 Jul 31, 9 Aug 1, 1 Aug 2). Every row = `Intelligence Briefing #1 (date)`
  from `InsightPipeline`: totals + `by_engine` + top items. All 67 record `'max_drift_7d': 0.0`
  (Q3). `Duration:` jumps from 51–378 ms (Jul 10) to 105,762–6,820,752 ms (Jul 11–12 — 1.9 h once),
  34,558 ms (Jul 28), then **491,199–3,924,530 ms (Jul 31–Aug 2)**. Recurring kaizen items:
  "Fix 125 untitled memories", "Tag 39850 untagged memories" → "Tag 40498 untagged memories"
  (Jul 31, 14:50→20:49), "Large cluster at (0.0, 0.0): 207" — store-hygiene self-diagnostics,
  emitted, never consumed (same text each briefing). Genuine synthesis? Mostly template; the
  emergence items cite real co-occurrence counts ("co-occurred 3 times in the last 7 days").
- **creative_solutions** (43 rows, 38 distinct contents; Jul 8→Aug 1). All are compression
  narratives over other galaxies' rows: "Narrative: consolidated, strategy (23 memories)";
  Jul 31 narratives re-state bench text ("# File 132 This is test content…"); the Jul 31 20:08 row
  compresses emergence insights ("Tag cluster: carol + session_0000" — LongMemEval tags); the
  Aug 1 row compresses "Current Work State … **Current task**: test". No system-condition claims.
- **universal** (774 rows; 357 LTE / 417 STE; May 24→Jul 31). Scratch/test galaxy: imported web
  articles "The Ultimate Guide to Test Results Analysis" (Llama-4-Maverick byline), arXiv metadata,
  codex scan manifests (`"errors": 0`, `duration_s` 0.06 vs 18.1), auto-seed messages ("Auto-seeded
  memory for gap: Galaxy 'test-galaxy-script' is empty"), fixtures ("Bench Fixture Memory"),
  dev notes ("Session: MCP Optimization Complete — T480s Production-Ready", Jul 13), and two
  self-scored loop outputs at Jul 31 20:02:09 — "Cycle 1: Low confidence (0.47) — needs
  refinement" (producer UNVERIFIED).
- **research** (520 rows; 402 LTE / 118 STE; May 16→Jul 31). Documents (GRANT_PIPELINE_2026.md,
  DHARMA_SPEC, LLC operating agreement, digests) plus the closest thing to genuine synthesis here:
  "Introspective simulation: guna_balance fitness=" rows with optimized sattvic/rajasic/tamasic
  targets and sensitivity (Jul 26: 5 rows, 0.8018–0.9413; Jul 31 20:04–21:06: 7 rows,
  0.8234–**0.9667** — the best value in the series). Whether any consumer read them: UNVERIFIED
  in scope (W2: possibility-winners overwrite boot constants with no outcome verification).

## 4. Endgame evidence, Jul 31 → Aug 2 (all six DBs, term sweep Q4)

**What exists (RUNTIME-OBSERVED):**
1. The `meta` bookkeeping loop above: 7,554 rows in 39 h of repeated summaries/refs/priorities,
   running to the archive's last timestamp (`meta_priority_3_1785685208`, Aug 2 15:40:08).
2. Quantified growth of an incoming corpus, inside `meta` summaries of the `sessions` galaxy:
   `memory_count` 10,127 (Aug 1 00:01) → 21,350 (Aug 2 15:02); `turn_type:message` 2,816→7,239;
   `turn_type:context` 740→2,084; `turn_type:error` **679→1,585**. These are counts of records
   arriving, not statements about the system's own condition.
3. 18 `insight` briefings (Jul 31–Aug 2): durations 0.5–65 min, `max_drift_7d` 0.0 in every row,
   kaizen hygiene items unchanged across consecutive runs.
4. 7 `research` optimizer rows Jul 31 evening (fitness 0.8234–0.9667); `universal` codex scan
   manifests with `"errors": 0` and web imports; two "Cycle 1: Low confidence (0.47)" rows.
   `main` ends Aug 1 13:35 with another fixture round.

**What does NOT exist (term sweep, rows dated 2026-07-31…08-02, all six DBs):**
- **No endgame row describes loops, resource pressure, anomalies, errors or runaway.** "runaway"
  58 hits total = 57 in May research documents + 1 grimoire chapter (sandboxing guidance), 0
  endgame; "out of control" 6/0; "memory leak" 6/0; "latency", "timeout", "slow", "backlog",
  "queue", "degraded", "coherence", "karma", "sweep", "memory pressure", "unbounded", "overload",
  "stuck", "crash", "emergency", "shutdown", "restart": **0 endgame rows**. Single endgame hits
  for "loop"/"failure"/"fail"/"ram"/"resource"/"exhaust" are imported-article or DOI text
  (`universal:d4e98f0052ad19fd`, Jul 31 20:02 — a test-results web article).
- Endgame "spiral" (260) and "calibration" (261) hits are **tag names inside** `meta` summary
  templates; "stale" (918) is the stale-galaxy gap string; "untagged/untitled" (25) is the kaizen
  item; "health_score" (5,511) is summary JSON.
- No memory_type anywhere in scope is a reflection/metric/cycle log; no `meta` row about the
  `meta` writer itself; no row referencing the tool tours, the 284 empty dreams, the karma chain,
  calibration ledgers, or any "incident".

## 5. Limits & unverified

1. **Scope hole:** the story-bearing ledgers (sessions, citta, dharma, emergence, tool_usage) are
   not in these six DBs; this file can speak only to galaxy-side self-recording. W0_state_ledgers
   shows organ ledgers also stop by 2026-08-02.
2. Summary counts are **writer-reported** and can be internally inconsistent: "Galaxy Summary:
   main" `memory_count` takes 25 different values across Aug 1 batches (0…4226, ending at main's
   final 4,226) — reads of concurrently written stores (INFERRED); cause UNVERIFIED.
3. No driver identity: no `meta`/summarizer tool call appears in tool_usage.db; `session_id` was
   NULL there; "unattended loop" is structural inference from cadence and repetition only.
4. Repetition measured by exact content equality; near-duplicates not measured. Quotes truncated;
   ids given so each claim can be re-run read-only.
5. "Genuine synthesis" is judged only structurally (new quantities vs template copy), not by
   meaning; no labels exist to grade it. Durations >1 h may be hangs or mis-timed logging
   (UNVERIFIED, cf. tool_usage's 2.97 h row).

## 6. Implications for the runaway narrative

1. **Partial corroboration, but not in the form the narrative assumes.** What is attested is an
   unattended, self-repeating writer that ran every few minutes to the final timestamp, emitting
   7,554 near-duplicate bookkeeping rows. "Something ran unbounded into the end" is
   RUNTIME-OBSERVED; the system describing *itself* as runaway is absent.
2. **The strong claim — self-reported dysregulation during the endgame — is contradicted by
   silence here.** The one pipeline that reports condition (insight) logs `max_drift_7d: 0.0` in
   all 67 briefings, including Aug 1–2, while flagging only hygiene backlog. No error/anomaly/
   pressure row exists in the window; the only failure-adjacent counter is `turn_type:error`
   inside a summary of an incoming transcript corpus.
3. **A cost, not a complaint:** insight briefing runtimes inflate from ≤0.4 s (Jul 10) to 0.5–65
   min (Jul 31–Aug 2). INFERRED as load/latency; not monotonic (Jul 11–12 was already long), so
   weak evidence for a sharp endgame onset.
4. **No closed loop to ground it:** the only endgame "return" signal is the research optimizer's
   self-scored fitness 0.9667, consistent with W2's possibility-winner critique (no outcome
   verification), not with external grounding.
5. **Net:** in these six galaxies Gen1's final weeks record galaxy accounting, a grimoire import,
   and bench churn; the archive ends at 2026-08-02T15:40 as a stop, with no self-report channel
   that tracks system condition. The runaway narrative is neither confirmed nor refuted at the
   level of self-description — the appropriate evidence channels are the ledgers outside scope.

## Appendix — stated queries (read-only)

- Q1: `SELECT title, COUNT(*) FROM memories GROUP BY 1` (classes by prefix; id patterns
  `meta_summary_*`, `meta_xref_*`, `meta_priority_*`, `cross_galaxy_link_*`).
- Q2: `SELECT substr(created_at,1,10), COUNT(*) FROM memories GROUP BY 1 ORDER BY 1`.
- Q3: `SELECT content FROM memories` + regex `'max_drift_7d': ([\d.]+)`, `Duration: (\d+)ms`.
- Q4 sweep: rows `created_at BETWEEN '2026-07-31' AND '2026-08-02'` × 40 lowercase terms, all six
  DBs; hits printed with ±100-char context; per-term totals and pre/post dates recorded.
- Dup/type checks: `SELECT COUNT(*), COUNT(DISTINCT content|title)`; `SELECT memory_type, COUNT(*)`.
