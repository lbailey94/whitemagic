# W0 — v26 state ledgers as runtime artifacts (Gen1 evidence intermission)

Status: findings · 2026-09-17 · read-only; RUNTIME-ARTIFACT (mtime-agnostic content) + inferred, labeled

Scope: `/home/lucas/Desktop/WHITEMAGIC_GEN1_v26.0.3/WHITEMAGIC_GEN1_v26_MEMORY_CORE/v26/state/` only.
Method: `python3` (json/jsonl, `sqlite3` via `mode=ro` URIs), `find/ls/wc/rg`; mtimes never used as
evidence (parsed content timestamps only). Every count below was printed by `/tmp/opencode/analyze.py`
+ `analyze2.py`; file:line citations are 1-indexed. **"Recorded" ≠ "meaningful"** throughout: a row
existing is recorded evidence; a row carrying consumed, consequential state is meaningful evidence.

---

## 1. Inventory (organ · file · rows · first/last content date · nature)

| Organ | File (under `state/`) | Rows | First | Last | Nature |
|---|---|---|---|---|---|
| citta | `citta/coherence_drift.jsonl` | 65,642 | 2026-06-28 | 2026-08-02 | self-report coherence sample, machine-generated |
| citta | `citta/machine_time.jsonl` | 83,733 | 2026-06-28 | 2026-08-01 | tool-latency prediction-error ledger |
| citta | `citta/calibration.jsonl` | 83,266 | 2026-06-28 | 2026-08-01 | duration-estimate scoring (CRPS) — **no Brier field (0 hits)** |
| citta | `citta/depth_gauge.jsonl` | 29,168 | 2026-07-13 | 2026-07-30 | dream-layer work packets w/ embedded calibration summaries |
| citta | `citta/stream.jsonl` | 100 | 2026-08-01 | 2026-08-02 | lossy in-memory ring (deque cap = 100) |
| citta | `citta/stream_state.json`, `workspace_state.json` | 1+1 | — | — | session counters (`session_count`, `ignition_count`) |
| dharma | `dharma/karma_ledger{.3,.2,.1,}.jsonl` | 18,347 / 18,830 / 21,033 / 13,516 | 2026-07-12 | 2026-08-02 | hash-linked action ledger, 71,726 rows total |
| forecasting | `forecasting/predictions.db` | 528 | created 2026-05-29 | created 2026-09-04 | scored claims ledger (100 validated / 27 falsified / 400 pending) |
| forecasting | `state/state/forecasting/predictions.db` (mirror) | 647 | 2026-05-29 | 2026-08-29 | **divergent second copy** (70 validated / 0 falsified) — see §5 |
| emergence | `emergence/dreams.jsonl` | 284 | 2026-06-27 | 2026-07-20 | emergence dream cycles — **every row all-zero output** |
| dreams | `dreams/*.yaml` | 52 | 2026-07-13 | 2026-08-01 | bicameral dream records; all names end `_benchmark-test` |
| harmony | `harmony/activity_log.jsonl` | 56 | 2026-07-06 | 2026-08-01 | homeostasis actions — **56/56 READ, 0 CORRECT/INTERVENE** |
| economy | `token_economy.jsonl` | 154,015 | 2026-06-28 | 2026-08-01 | per-tool-call instrumentation; api_tokens=0 in 153,203 rows |
| economy | `state/token_economy.jsonl` (nested) + `economy/*.jsonl` (4 files) | 4 + 584 | 2026-07-07 | 2026-08-01 | path artifact; test-content marketplace (`"test"`, `tx_hash:"test"`) |
| matrix | `matrix/timeline.json`, `current_session.json` | 1 event | 2026-06-19 | 2026-06-19 | single `session_start`; session interactions = 0 |
| conductor | `conductor/live_status.json` | 1 | 2026-07-08 | 2026-07-08 | one 0.18 s / 0-token / `active:false` run, status stuck `in_progress` |
| users | `users/local/galaxies/` | 46 galaxies | 2026-01-28 | 2026-08-02 | 22 bench-like + 24 named; sessions 21,351 memories; main 4,226; research 520; citta 501 |
| logs | `logs/{telemetry.jsonl,whitemagic.log,whitemagic_dream.log}` | 80,609 / 273 / 744 | 2026-04-22 / 05-24 / 06-28 | 2026-08-01 / 07-19 / 07-13 | telemetry, runtime, dream logs |
| events | `events.jsonl` | 1,182 | 2026-06-23 | 2026-08-01 | narrator/system events (`type` field, not `event_type`) |
| skills | `skills/` | 33 JSON + `exported/` | 2026-07-08 | 2026-08-01 | SkillForge persistence (W2's 33 confirmed as live artifact) |

Cross-cutting month coverage (content dates, **Jan–Aug 2026**; `●` = rows present; sessions-galaxy
figures are monthly memory counts from SQL):

| Organ | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug |
|---|---|---|---|---|---|---|---|---|
| sessions-galaxy memories | 150 | 341 | 49 | 224 | 430 | 1,075 | 16,549 | 2,533 |
| research galaxy | – | – | – | – | ● | ● | ● | – |
| telemetry.jsonl | – | – | – | ● | ● | ● | ● | ● |
| whitemagic.log | – | – | – | – | ● | ● | ● | – |
| predictions.db created rows | – | – | – | – | 3 | 20 | 125 | 325 (+27 in Sep) |
| events / citta drift / calibration / machine_time / token_economy | – | – | – | – | – | ● | ● | ● (to Aug 1–2) |
| karma ledger (all rotations) | – | – | – | – | – | – | ● | ● (to Aug 2) |
| emergence/dreams.jsonl | – | – | – | – | – | ● | ● | – |
| dreams/*.yaml · harmony · economy/ | – | – | – | – | – | – | ● | ● |
| depth_gauge | – | – | – | – | – | – | ● | – |
| matrix (Jun 19) | – | – | – | – | – | ● | – | – |
| conductor (Jul 8) · stream.jsonl | – | – | – | – | – | – | ● | ● |

Jan–Mar 2026 content exists only in the sessions-galaxy store (540 rows) plus one 2025-11-21 seed row
in the `citta` galaxy. Runtime switch-on is 2026-06-18→06-28; peak density is July; the archive
terminates abruptly 2026-08-02 (forecasting excepted).

---

## 2. Per-organ observations

**citta.** Three different things are recorded. (i) `coherence_drift.jsonl:1` is all-1.0 and `:2`
dips to 0.875; 51.6 % of 65,642 rows equal 1.0 exactly, and `memory_accessibility` is the only
sub-score <1.0 in 31,521 rows (only 7 rows for `emotional_attunement`). Daily means (computed per
day) fall 0.924→0.875 (Jun 28–Jul 6), spike to 0.998 on Jul 16 (19,944 rows that day), then
plateau 0.96–0.99 → **oscillation early, saturation late, never monotonic drift**. (ii)
`calibration.jsonl` contains zero `brier` strings: schema is `estimated_minutes/actual_minutes/
compression_ratio/crps` (`:1` pre-schema, lacks `crps`; `:2`+ have it), median CRPS 0.14 vs mean
1.24, 82,265/83,266 rows `depth_layer:"surface"`, top description `create_memory` (55,312).
`machine_time.jsonl`: 82,299/83,733 "trivial" tier, max `abs_error_pct` 2,374,586 %, 7,622 rows
>1,000 % — recorded, but dominated by fixed priors/overhead noise. (iii) `depth_gauge.jsonl` is
29,048/29,168 `layer:"dream"`; 103 lines embed forecasting summaries with runtime `brier_score`
0.0–1.0 (mode 0.2757; `depth_gauge.jsonl:14` = 0.2028, count 6696, accuracy_rate 0.2676).
`stream.jsonl` = exactly 100 rows (the deque cap) over Aug 1–2: 24 `consciousness_loop_tick`,
52 `dream_phase:*` labels from the 13-phase vocabulary.

**dharma.** Strongest runtime artifact here: 71,726 entries over 21 days, 908 distinct tool names,
real traffic dominant (`search_memories` 20,074; `create_memory` 17,954) interleaved with probes
(`totally_nonexistent_tool_xyz_12345` 178; `nonexistent.tool.xyz` 98; `unit_test_tool_dispatch`;
`foundry.test*`). Hash-linked but **not linear**: chain passes 18,118/18,347 (.3), 17,691/18,830
(.2), 19,870/21,033 (.1), 13,305/13,516 (current); at every break checked the expected hash still
exists elsewhere in the file (228/228, 1,138/1,138, 1,162/1,162; 207/210 current) → interleaved
concurrent writes (INFERRED), 3 orphan links. **Rotation boundaries are perfectly linked** (last
`.3` hash = first `.2` prev_hash; same `.2`→`.1`, `.1`→current). Failure states recorded: success
71.9 % / 91.9 % / 93.6 % / 58.6 % by rotation, 9,076 `mismatch:true` rows, ~917 total `debt_delta`.

**forecasting.** `predictions.db` is genuinely scored, not fixtures: 528 rows, **127 resolved (100
validated / 27 falsified)**, overall Brier 0.2563 (confidence vs binary outcome, SQL-computed).
By category: `time_estimate` 0.0731 (n=18), `agent_architecture` 0.0898 (n=21),
`ai_governance` 0.1038 (n=16), **`simulation_test` 0.6544 (n=34)** — real forecasts mixed with
self-scored test rows. Created 2026-05-29 → 2026-09-04 (Sep rows exist); `source_date` reaches
2025-03-07. This is the only ledger whose writing outlives the Aug 2 cliff. The mirror copy at
`state/state/` disagrees: 647 rows, 70 validated / **0 falsified**, Brier 0.1215.

**dreams / emergence / harmony.** `emergence/dreams.jsonl` = **284 lines, every one all-zero**
(0 memories_processed, 0 connections, 0 patterns, 0 insights — field-by-field; mean duration
0.57 s). This independently reproduces LINEAGE_LEDGER's "284 runs, 0 with any output" *for this
file*; it does not place these at the 2026-08-01 incident (window Jun 27–Jul 20 — see §5). The 52
`dreams/*.yaml` are all `_benchmark-test`, `source: bicameral_reasoner`, with live-looking fields
(`status: promoted`, `revisit_count`) over template content ("balanced test dream"). Harmony: 56×
READ, zero CORRECT/INTERVENE — but `logs/whitemagic_dream.log` holds **361 `[Homeostasis/CORRECT]`
lines, 0 INTERVENE** (Jun 28–Jul 13), so "no CORRECT ever" holds only for the `harmony/` recorder.

**economy / matrix / users / conductor.** `token_economy.jsonl` is mostly real instrumentation
(152,615 `mcp_tools`) yet only 812 rows have `api_tokens>0` (sum 2.41 M) and none have
`local_ram_mb>0`; `:1` is `"description":"test_op"`. The separate `economy/` ledgers are pure
fixtures (`"test"` descriptions, `tx_hash:"test"`, `agent_id:"default"`) — so the "economy = test
fixtures" ruling is confirmed for `economy/` and **partly contradicted** for `token_economy.jsonl`
(real call record, thin meaningfulness). `matrix/timeline.json` holds exactly one event (Jun 19,
`session_start`, interactions 0); `conductor/live_status.json` is one Jul 8 record, `active:false`,
0 tokens. `users/local`: 46 galaxies (24 named, 22 bench-like); sessions 21,351 memories
(CITTA 18,204 — W2's label-artifact count reproduced from the DB), main 4,226 (all SHORT_TERM,
Jul 10–Aug 1), research 520 (May 16–Jul 31), citta galaxy 501 with a 2025-11-21 seed row.
`events.jsonl` (1,182) uses its own `type` taxonomy.

---

## 3. Accumulation vs recurrence-without-output

**Accumulation (write-side volume, internally indexed):** karma ledger (71,726 chained entries,
21 days, rotation-linked); token_economy (154,015 calls); sessions store (+18,760 memories
Jan–Aug, 16,549 in July); SkillForge (33 persisted skill JSONs, write-only per W2); forecasting —
the only **closed loop** (prediction → validation_date → status → Brier, 127 resolved).

**Recurrence without output (cycles that increment and emit nothing consequential):** emergence
284 runs / 0 outputs in 24 days; harmony 56 reads / 0 actions; `consciousness_loop_tick` and
`dream_phase:*` dominate the 100-row stream ring; 52 benchmark-template dream YAMLs nothing
downstream reads; `coherence_drift` converging to its own ceiling (97 %+ days pinned at 1.0).
The saturation and "write-only" readings are INFERENCE; the counts are command-derived.

## 4. Organs / artifacts with no runtime trace here

- `dharma/anchors/` empty; retention/lifecycle has no trace (`dharma_audit` and `akashic_seeds`
  0 rows in every galaxy checked; no archive/delete log).
- Homeostat *actions*: 0 CORRECT/INTERVENE in `harmony/` (dream log has CORRECT emissions —
  recorder-level absence, not organ-level).
- Conductor and matrix: 1 record each, no multi-run history.
- `emotional_memories/`, `memory_matrix/`, `codegenome/`: directories exist, 0 content files.
- Hebbian/typed dynamics: no ledger; `associations` rows exist (112,240 in sessions galaxy)
  without a dynamics trace (consistent with W2: typing never persisted).
- `CycleEngine`/citta cycles: no cycle ledger, only per-tick stream rows + the 284-zero file.
- No non-empty emergence insight under `emergence/` (W2's 329 detector insights live elsewhere).
- All organs stop by 2026-08-02 except forecasting (Sep content).

## 5. Limits & unverified

1. **284 coincidence:** count and zero-output property match LINEAGE_LEDGER exactly, but the
   window (Jun 27–Jul 20) predates the Aug-1 incident. Same event or equal count: **UNVERIFIED**;
   W2's "no run log reproducing 284" is partially lifted for the count only.
2. **Brier 0.078 not reproduced:** neither `predictions.db` copy yields it (0.2563 / 0.1215
   overall; nearest category 0.0731, n=18). Runtime depth_gauge Brier is 0.20–0.31. The 0.078
   figure refers to some other snapshot/category or the Gen2 claims ledger — UNVERIFIED.
3. **Divergent `predictions.db` copies** (528 vs 647 rows, different resolved sets): canonicality
   UNVERIFIED; any quoted count must name the path.
4. **Karma chain breaks** are out-of-order links, not corrupt hashes; interleaved-concurrency is
   INFERRED; 3 orphan links unexplained (likely rotation pruning, UNVERIFIED).
5. **`state/state/` recursive mirror** (94 files, 6.8 MB; citta truncated to 330/4/100 rows) is a
   state-path collision artifact whose forecasting copy is newer than the top-level one — never
   count both trees.
6. Content dates only; mtimes (e.g. `forecasting/` shm Sep 17) excluded by design.
7. "Meaningful" gradings (saturation, write-only, noise) are labeled inferences; counts above are
   reproducible from the stated commands.

## 6. Implications for the wiring/coupling hypotheses

- **Write side coupled, read side absent:** karma, token_economy, sessions, SkillForge all
  accumulate; nothing in state consumes them except forecasting. Strengthens W2's "edges compile,
  dynamics parked" and W3's field/actuation split — the archive records, it does not control.
- **The spiral has exactly one weak instance here:** forecasting's closed score loop (127
  resolved), mixed with self-scored `simulation_test` rows (Brier 0.65). PHYLOGENETIC_FRAMING §2's
  "productive spiral" is otherwise unattested in these ledgers.
- **Rumination is artifact-attested:** 284 output-less runs, 56 action-less reads, a 100-row
  lossy ring, coherence saturating at its ceiling — the inward-movement failure mode is measured.
- **Coupling-ratio operationalization:** denominator evidence exists (karma/token/session
  volumes); the numerator (externally grounded intake) has no ledger here — that absence is the
  finding.
- **No upgrades to the citta headline** (18,204 CITTA is a `memory_type` in the sessions galaxy)
  and **no reproduction of 0.078**; both stay flagged in matrix/ledger errata.
