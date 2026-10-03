# W1 — Sessions & continuity (Gen1 v26 observable behavior)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Repo root for citations: `og_whitemagic/` @ v26.0.3 (`4d5be091`).
Row targets: *Session records/lifecycle* (PRESERVE→link) and *Continuity/digest* (CLEANLY→compile);
the split is deliberate (`PHASE3_DECOMPOSITION.md:120-121,150-154`).

## Observed behavior (cites)

- **Turn taxonomy:** 9 turn types, a frozenset: `message · decision · breakthrough · question ·
  answer · code_change · error · summary · context` (`core/whitemagic/core/memory/session_recorder.py:39-49`).
  Command: `sed -n '39,49p' session_recorder.py | rg -o '"[a-z_]+"' | wc -l` → **9**.
- **Record shape:** each turn = one `Memory(MemoryType.CITTA)` in the `sessions` galaxy; tags
  `role`, `session:<id>`, `turn_type:<t>`; metadata `session_id, sequence, role, turn_type,
  citta_stream_pos`; title `[role] #seq type`; written via the private handle
  `self._um._galaxy_backend.store(mem)` (`session_recorder.py:101-119`) — bypasses the public
  ingestion path (no dedup/gate).
- **Sequence is canonical, timestamps are metadata** (docstring `:17-23`): `_record` increments an
  in-process counter; `_restore_sequence` reseeds it from max existing sequence at construction
  (`:522-534`); `backfill_sequences` assigns sequences by `created_at` only where missing
  (`:263-284`).
- **Recall modes** (`:134-203`): `recall_recent` over-fetches `n*2` then sorts by sequence and
  slices; `recall_progressive` budget of 200-char previews at ~4 chars/token; `recall_selective`
  default `min_importance=0.7` + turn-type tags; `recall_by_query` goes to the backend search
  (SQLite FTS5 BM25 — `core/whitemagic/core/memory/backends/search_commands.py:59,112`; the route
  declares FTS5 at `core/whitemagic/tools/registry_defs/session.py:182`); `format_context` renders
  `[seq] role/type (ts): content`.
- **Cross-session continuity ("Total Recall" turn path):** `get_continuity_turns(n=10)` loads
  **10,000** sessions-galaxy memories, groups by `metadata.session_id`, picks the previous session
  by **lexicographic max ISO `created_at` string**, re-fetches its last N turns, returns
  `first_awakening=True` when none (`session_recorder.py:288-345`); exposed as
  `session.continuity` (`core/whitemagic/tools/handlers/session.py:695-713`; dispatch-table
  `core/whitemagic/tools/dispatch_table.py:463`).
- **Sleep consolidation:** turns with `importance ≥ 0.7` and type ∉ {message, context} are copied
  into the `codex` galaxy with `consolidated_from` + `sleep_consolidation` tags
  (`session_recorder.py:426-518`); invoked automatically by `end_session`
  (`core/whitemagic/gardens/sangha/session_handoff.py:212-221`), which also pushes summary/next
  steps into the state tracker (`:198-210`) and writes `sessions/HANDOFF.md` (`:194-196`).
- **Emotional auto-tagging:** every turn is stamped with valence derived from the *global* citta
  cycle's dominant tone (map `:350-367`; reader `:369-386`) — ambient, not per-turn or per-session.
- **Auto-recording middleware is the main turn producer:** skips `session.*`/`state.*` and
  `citta.*` tools and honors `WM_SESSION_RECORD=0` (`core/whitemagic/tools/middleware.py:1697-1703,1721`);
  `wm` `thought`→user/`message`; `wm` result→`answer`; error→`error` (0.7); tool names containing
  create/store/save/write/update/record→`code_change` (0.6); search/recall/read/list/status→
  `context` (0.3); else `message` (0.4) (`:1731-1778`). Note the **dual default:** settings declare
  `session_record` default **False** (`core/whitemagic/config/settings.py:104`) while the
  middleware gate is **on unless the env var is exactly "0"**.
- **Live short-term state (`current_state.py`):** dataclass snapshot persisted twice per mutation —
  JSON at `WM_ROOT/state/current_state.json` and a *new* `SHORT_TERM` memory tagged `current_state`
  in the `sessions` galaxy (`core/whitemagic/core/memory/current_state.py:24-28,231-246`); caps
  20 files / 50 events / 10 next-steps / 5 tasks (`:47-50`), but generic `update()` `setattr`s and
  bypasses the caps (`:397-404`). Injected into MCP **server instructions on startup**
  (`core/whitemagic/runtime/subsystem_init.py:144-159`), preceded by a separate citta-continuity
  block from `citta_stream` (`:115-142`); queryable via `state.current`
  (`registry_defs/session.py:247`).
- **Bootstrap ("Total Recall architecture"):** loads 10 recent memories, first 20 dispatch names,
  seen-count, `in_progress.json`, grimoire chapters → writes `state/session_context.json`
  (`core/whitemagic/session/bootstrap.py:40-55`); it does **not** call `get_continuity_turns` — the
  name covers three distinct paths (session turns, citta stream, current state).
- **Sibling modules named "continuity" are different organs** (homology rule): `continuity/grounding.py`
  = environment grounding (time/host/resources → `lighthouse.json` + daily jsonl; `:41-121`);
  `core/continuity.py` = file-locked cross-interface sync (`current_session.json`,
  `events.jsonl`, `seen_registry.json`; `:68-72,188-265`). Neither is imported anywhere else in the
  tree (grep for `GroundingSystem`/`get_continuity_suite` → no importers) — **dormant code,
  UNVERIFIED as ever-run**.
- **Also dormant:** `core/memory/auto_capture.py` (file-based short-term markdown, every 5 actions,
  cap 60, archive-not-delete; `:100-118,283-293`; no importers) and
  `core/memory/cognitive_episode.py` (63-line dataclass only, no store; no importers — a distinct
  `CognitiveEpisode` lives in `core/evolution/thought_galaxy.py:4`).
- **Route surface:** 13 `session.*` + 3 `state.*` definitions in one registry file
  (`rg -c 'name="' registry_defs/session.py` → 16). Anchors: 21,351 turns, CITTA 18,204, wmv9 store
  119 sessions (`PHASE4_GEN1_TREE.md:19`, `PHASE3_DECOMPOSITION.md:128-132`). Sum of the nine
  turn-type counts via `python3 -c "print(7939+2593+2379+1827+1676+326+108+8+3)"` → **16,859**,
  a Δ of **1,345** vs CITTA 18,204 — the figures do not close; whether some turns are untagged is
  **UNVERIFIED**.

## Selection history

Gen1 stored turns as plain `Memory` rows (no session table) and folded into Gen2 `session.*`
lifecycle, "FOLDED & hardened", `session_ops.rs` 3,047 LOC; continuity also folded
(`PHASE3_DECOMPOSITION.md:128-132`). The ratified split is deliberate: storage/lifecycle is
**PRESERVE IMPL. → link** (replacement unearned; Phase 1 excluded a session module) while
continuity/digest is **CLEANLY → compile** as `recall` over the record layer + `think` synthesis —
no new primitive; Gen2's `session.continuity` stays the live path until the substrate earns
replacement (`:150-154`).

## Candidate Gen3 expression / manifest notes

- Storage (link): records + relations for turns/state; continuity (compile): `recall` + `think`
  over those records. Manifest fields for any hardening: wire = session-record relation/scope
  labels; acceptance = adversarial battery below; owner unset.
- **Adoption note (WMgen3 session rhythm):** integrate via the Gen2 9.1.8
  **`session.checkpoint_nodiscovery`** route, which stores exactly the supplied handoff fields
  (commit, branch, tests_green, next_queue, open_flags, lease_id) with **no repository discovery,
  filesystem reads, or subprocesses** — the correct integration point (fixes the observed
  WMv9-HEAD capture quirk; the git-capturing `session.checkpoint` now declares its reads/spawns)
  (`PHASE4_GEN2_DELTA.md:41,86-87`). No repo discovery/subprocess in the Gen3 rhythm.

## Adversarial cases

1. **Two-writer sequence race:** sequence counters are per-instance, reseeded from max at
   construction, with no lock across processes (`session_recorder.py:65-70,522-534`); two
   concurrent recorders on one `session_id` produce duplicate/gapped sequence numbers, and
   "chronological" replay silently degrades. Freeze spec must state the single-writer or
   merge rule.
2. **Ambient valence leak:** one global citta tone is stamped into every turn regardless of
   session or origin (`:369-386`) — replay of session A inherits session B's affective coloring.
3. **Previous-session selection:** lexical max of ISO strings + 10k fetch (`:303-327`) lets one
   future/naïve-timestamped turn or a one-turn session become "where we left off"; also O(all
   turns) per call. Test with tz-naive vs tz-aware and with a chatty vs empty previous session.
4. **Boundedness is per-method, not invariant:** `state.update()` bypasses the caps
   (`current_state.py:397-404`) and every mutation writes a fresh uncapped memory into `sessions`
   (`:231-246`) — state churn inflates the same galaxy continuity searches. (Expected share of the
   21,351 turns is UNVERIFIED.)
5. **Capture without redaction + dual default:** the middleware stores the first matching arg
   (content/query/description/…) truncated at 200 chars, no redaction (`middleware.py:1756-1760`),
   and is default-on while settings declare recording off
   (`settings.py:104` vs `middleware.py:1721`). Test secrets-in-args and counting under each default.

## Ablation ideas

- **`WM_SESSION_RECORD=0`** on a replay copy: remaining producers are only explicit
  `session.record`/`state.update`; measure `session.continuity` and `session.recall` coverage
  collapse (expect `first_awakening`-heavy behavior).
- **Remove the startup injection block** (`subsystem_init.py:144-159`): measure cold-start
  orientation (does the agent still find `state.current`?).
- **Skip end-of-session consolidation** (`session_handoff.py:212-221`): codex promotions should
  drop to zero; measure whether long-term semantic recall degrades past one session.
- **Backfill vs `created_at` comparison** (`backfill_sequences`): quantify clock-skew damage by
  re-sorting with assigned vs recorded sequences.

## Open questions

- Provenance of the fossil turn-type tags: auto-middleware vs explicit `session.record` — no
  source tag exists on the record to separate them.
- Does any Gen1 client call `session.continuity` at connect? The bootstrap path
  (`session/bootstrap.py:46-55`) uses recent memories + current state only.
- Is the wmv9 "119 sessions / 1,054 turns" count the same concept as Gen1 conversation sessions,
  or checkpoint-shaped lifecycle records (`PHASE3_DECOMPOSITION.md:130`)? Affects any migration
  count comparison.
- Where did the missing 1,345 CITTA turns' turn types go — untagged backfill, direct `Memory`
  writes, or a different query scope? (Numbers as quoted do not reconcile; needs DB access.)
