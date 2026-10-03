# W0 — Handoffs & sessions (Gen1 v26 state layer)

**Status:** findings · 2026-09-17 · read-only; authored-doc + runtime-artifact evidence, labeled
per source. Scope: `v26/state/sessions/` (208 JSON + `handoffs/` 24 JSON) + siblings
`users/local/`, `conductor/`, `scratchpads/` (+ adjacent `narrative/`, read because it is the
narrative sibling of sessions). Every claim below is from files read in place; no file modified.
Companion: `W1_sessions_continuity.md` (code-path view). Cross-file check pending:
`W0_tool_usage_july.md` did **not** exist at write time (2026-09-17 16:47 EDT).

---

## 1. Handoff inventory & quotes

**24 `handoff-*.json`, dates 2026-07-08 → 2026-07-26; every one is an empty payload shell.**
Verified by script over all 24: non-empty `message`: **0**; `context_summary`: **0**;
`modified_files`: **0**; `session.goals`: **0**; `session.checkpoints`: **0**. Names: 22×
`Bench Session`, 2× `exercise_test`. Status: 16 `pending` / 8 `accepted`; `source_device`
`T4800-S`, target `any`. mtimes match `created_at` (no later edits). FUNCTION: a session
single-slot lifecycle state machine (create→hand off→accept→resume→hand off again), **not a
context-transfer document**. This is the v26 ancestor of our HANDOFF docs — structurally
present, payload absent.

Quotes (verbatim, short; all from `state/sessions/handoffs/`):

1. `handoff-4fe5aa7c.json` (accepted, 2026-07-13T17:25) — a handoff that names itself as its
   own parent:
   `"status": "accepted",` … `"resumed_from_handoff": "handoff-4fe5aa7c", "resumed_on": "T4800-S"`
2. Same file, the payload: `"message": "", "status": "pending", "context_summary": "",
   "modified_files": []` — 796 bytes total, of which 0 are work context.
3. `handoff-0274b26b.json` (pending, 2026-07-13T17:31) points at the previous file:
   `"resumed_from_handoff": "handoff-4fe5aa7c"` (chain is real; content is not).
4. `handoff-0bbc0ba5.json` — the last one (2026-07-26T19:05), still empty:
   `"message": "", "context_summary": "", "modified_files": []`.
5. All 8 `accepted` handoffs are self-parented (`resumed_from_handoff == own id`), consistent
   with resume **rewriting the same slot in place** — the archive's form of the W1-coordination
   "single-slot silently drops" mechanism. Label: **runtime-artifact inference**.
6. `handoff-2781a5e3.json` / `handoff-5557d7b0.json` are the only non-"Bench" names:
   `"name": "exercise_test"` — a test-harness handoff, not an operator session.

No handoff anywhere contains prose, decisions, blockers, or next steps. There is nothing in
this layer to quote as a narrative record.

## 2. Session-file census

208 JSON files in `sessions/` root (assignment says 209 — see Limits). Two shapes:

| Class | Count | Telling fields |
|---|---|---|
| `session-*.json` lifecycle shells | 192 | name ∈ {Default 105, Bench 51, Lean Bootstrap 27, exercise_test 9}; status ∈ {active 159, checkpointed 22, handed_off 10, resumed 1}; `goals` non-empty **0**, `tags` non-empty **0**; 22 have exactly 1 checkpoint, names only `"test"`/`"checkpoint"` |
| `sess_*.json` agent fixtures | 16 | `agent_type: "test"` (all); `agent_id` ∈ {test, test1, test2, persist_test}; `cycle_count: 0` (all); `metadata: {}` (all); summaries only `""`/`"test summary"`/`"persisted"`/`"done"` (4/16 populated, boilerplate); `created_at` as **epoch seconds** (8 = 1783115962 ≈ 2026-07-03, 8 = 1784483928 ≈ 2026-07-19) |

**Real vs fixture: 208/208 are fixtures / harness shells by content** (zero goals, zero tags,
no summary, no narrative). The *real* record is not these files — it is the `sessions` galaxy DB
(§4): 21,351 middleware-written turns, 134 distinct `session:<uuid>` tags, real tool names and
errors (e.g. `"[ai] #1 error | Error in search_memories: Tool 'search_memories' exceeded 120.0s
timeout"`, 2026-08-02). Those DB rows match the W1 finding's machine-generated turn taxonomy
(and its 9-type tag counts: message 7,239, error 1,585, context 2,085, code_change 526…).

**Date coverage (ISO `created_at`, sessions root):** 2026-05-24 (1) · 07-03 (8, epochs) ·
07-06 (7) · 07-08 (6) · 07-09 (3) · 07-10 (15) · 07-11 (1) · 07-12 (13) · **07-13 (58)** ·
07-14 (2) · 07-15 (13) · 07-19 (8, epochs) · 07-21 (4) · 07-24 (1) · 07-26 (5) · 07-27 (7) ·
07-30 (21) · 07-31 (29) · 08-01 (6). File mtimes match. The Jul-13 burst is not human work:
27 Lean Bootstrap + 26 Default + 5 Bench shells, all `goals: []`.

## 3. Sibling dirs

- **`users/local/`** — 203 files, entirely galaxy stores: 46 galaxy dirs × (`whitemagic.db` +
  `-wal` + `-shm`), 9 `.galaxy_class`, 21 zero-width-named `.1` backups (all mass-written
  2026-07-31 18:36), one `whitemagic.db.prerestore-20260729` (+wal/shm) and a
  `.empty-20260728` — traces of a pre-restore backup and an emptied DB around Jul 28–29
  (**runtime-artifact; operational inference**). 13 numbered `bench-galaxy-<epoch>` dirs were
  created 2026-07-30 19:03 → 2026-08-01 13:22. Content by DB (read-only SQLite queries):
  `sessions` 21,351 turns (Jul 31 = 8,707 = 41 % of all turns; Aug 1 = 2,526); `main` 4,226
  memories whose newest titles are `bench_src/file_N.md` "This is test content…"; `knowledge`
  431 memories, 329 `emergence_insights` whose text is self-diagnostic tag co-occurrence
  (`"Tags 'current_state' and 'state' co-occurred 58 times in the last 7 days…"`); `citta` 501
  and `aria` 256 rows of `emotional_shift:neutral->sattvic @ pos=…` keyed to tool names;
  `longmemeval_bench` 74 eval rows ("In the security audit session, Alice said…", Jul 28).
  Only the turn log reads as real runtime work; everything else is eval corpus or self-churn.
- **`conductor/`** — one file, `live_status.json` (Jul 8 20:56): `"active": false`,
  `"phase": "iteration-2-complete"`, `"status": "in_progress"`, `"tokens_used": 0`,
  `"avg_confidence": 0.9499996000001334`, `"current_preview": "[Clone 1 / chain_of_thought]
  Explored: Generate a FastAPI endpoint for health checks"`. A single test-scale run frozen in
  progress; no durable orchestration record.
- **`scratchpads/`** — 7 files: `bench_pad.json` (empty entries), `scratchpad.json` (one entry,
  2026-08-01: `"[reasoning.bicameral] {'reasoning': {'left_hemisphere': 'Analytical reasoning
  module ready'…"`, tag `dispatch_sync`), and 5 `.lock` files (two from Jul 6 tooling runs:
  `.meta_tool_analysis.json.lock`, `.meta_tool_refinement.json.lock`). Real scratchpad I/O, but
  fixture-scale.
- **Adjacent `narrative/`** (read for completeness) — 21 daily journals, Jun 27 → Jul 20, each
  **34 bytes**: `# Daily Narrative — 2026-07-XX` and nothing else. A narrative organ existed
  and recorded nothing; a name-≠-function exemplar for the framing doc's §4 rule.

## 4. What the layer shows about July

**Runtime-artifact (turn log) day counts** — `sessions` galaxy, created_at: Jul 5=340, Jul 6=17,
**Jul 7=1,102**, Jul 8=43, **Jul 9=1,604**, Jul 10=80, Jul 11–12=14/24, **Jul 13=1,146**,
Jul 14=35, Jul 15=569, **Jul 16=2,259**, Jul 17–28=≤9/day, Jul 29=88, Jul 30=58,
**Jul 31=8,707**, Aug 1=2,526.

- The Jul 6–16 burst is real in this layer (peaks 7/9/13/15/16); shell-file dates agree.
- **After Jul 10 there is no silence in raw turns** (Jul 13/15/16 are among the busiest days),
  but the *interactive* layer thins: last handoff Jul 26; last session shell Aug 1. Near-silence
  proper is **Jul 17–29** (≤9 turns/day).
- The archive's last phase is an **automated bench monolith**: Jul 31 + Aug 1 = 11,233 turns
  (53 % of everything), 13 numbered bench galaxies created inside 18 h, individual sessions of
  ~860–870 turns in 15–30 min (e.g. 869 turns 13:22–13:51 on Aug 1), eval corpora
  (longmemeval/beam/abstention/hologram) written Jul 27–31.
- **Vs "touristing surface":** corroborated from this side. Every artifact class that would
  carry deliberate operator/agent task work — handoff `message`, session `goals`/`tags`,
  checkpoint names, daily journals — is empty or boilerplate (`test`, `checkpoint`, `Bench
  Session`). What the layer does contain is machinery exercising itself: tool-call logs, timeouts
  (`search_memories` 120 s), emergence stats about its own churn. **Label: runtime-artifact
  synthesis; cross-check with `W0_tool_usage_july.md` not yet possible.** The do-not-edit
  parallel file did not exist at write time, so no contradiction is claimed either direction.

## 5. Limits & unverified

- **Count mismatch:** 208 root JSON + 24 handoff JSON counted; assignment says 209 sessions.
  One file may differ (a `HANDOFF.md` is *not* present). UNVERIFIED which count is canonical.
- All `created_at`s are store-written; replay/import can backdate or re-time rows (the
  `sessions` DB holds turn dates from 2026-01 on). Wall-clock intent of early rows: UNVERIFIED.
- Which rows are middleware-recorded real use vs bench-harness replay is not distinguishable
  from the data (no origin tag) — W1 open question stands.
- `.db-shm` files show Sep-2026 mtimes; WAL-shm touches happen on connection open, so they are
  **not** evidence of Gen1 activity. Flagged so no one reads them as such.
- The self-parent handoff pattern is inferred from field values (8/8 accepted), not from logs of
  the resume code path.
- No provenance signal separates auto-written from human-written *anything* in this layer.

## 6. Implications

1. **Continuity ancestry is thinner than it looks.** W1's split (session storage → PRESERVE;
   continuity → CLEANLY compile) is **upgraded** by stronger evidence: v26's handoff carried no
   fields at all, so Gen2's explicit checkpoint payload (`commit/branch/tests_green/
   next_queue/open_flags/lease_id` per the `session.checkpoint_nodiscovery` adoption note) is a
   genuine functional addition, not a rename. Migration must not cite v26 handoffs as a
   payload-bearing ancestor.
2. **"Single-slot drops" is worse than reported:** the surviving slot is also empty and, in this
   archive, self-parented — the slot is overwritten on resume. Acceptance test candidate: a
   handoff resumed twice must retain both parents (or refuse), and a payload-less handoff should
   be a declared refusal, not a `pending` artifact.
3. **Name ≠ function, again:** `narrative/journal_*.md`, `handoff` files, and `Lean Bootstrap
   Session` are all functional stubs. Any Gen3 manifest naming continuity/narrative must name
   its wire + acceptance — the ancestor here supplies only the shell.
4. **The July record supports the rumination/touristing failure mode** in
   `PHYLOGENETIC_FRAMING.md` §2: the archive's final phase is self-measurement (bench galaxies,
   emergence insights about tag co-occurrence, timer errors), not externally grounded work.
5. For Gen3: build the narrative record where the evidence actually is — the turn log — and make
   handoff payload a first-class, non-empty artifact; empty schema is not inheritance.
