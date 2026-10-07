# Phase 4 — Wave-2 findings: Citta / cycles / dream

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Assignment: `PHASE4_GEN1_TREE.md` §3 (wave 2, "citta/dream
consolidation half") and `PHASE3_DECOMPOSITION.md` §2.3 row "Citta/cycles" — verdict
**AWKWARDLY → compile** (E15; dream/consolidation half compiles, field half is a
missing-primitive candidate — activation/decay, gated on "a task where propagation beats
retrieval"). Ancestors read at tag v26.0.3: `core/whitemagic/cycle_engine.py`,
`core/whitemagic/autonomous/`, `core/whitemagic/core/dreaming/dream_cycle.py` (canonical phase
source), `core/whitemagic/core/intelligence/dream/dream_phases.py` (re-export),
`core/whitemagic/core/consciousness/citta_{cycle,bridge,stream,vector}.py`. Counts are
command-generated (`wc -l`, `rg`); turn totals are cited from the matrix, not re-queried
(UNVERIFIED against the DB).

---

## Observed behavior

**CycleEngine — an orchestrator that writes nothing.** 489 LOC; `advance()`
(`cycle_engine.py:283-340`) gathers state from lazily-imported subsystems (yin-yang summary,
zodiac phase, wu-xing element, context synthesizer), advances one zodiac phase, records a
yin/yang activity category, increments `element_counts`, emits three `cascade=True` Gan Ying
events (`:342-409`). Outputs are the `CycleState`/`CycleMetrics` dataclasses in memory
(`:127-156`); `rg 'write|store|persist|open\('` over the module finds no persistence; the
element/zodiac→action tables are fixed (`:102-124`). Only callers are `SessionStartupOrchestrator`
wrappers (`core/orchestration/session_startup.py:1152-1174`, `:1215`); whether any live route
drove `advance()`/`run_rounds()` (`:411-438`, n × 12 advances) is UNVERIFIED — no journal, row,
or file found.

**Citta — a real per-dispatch pipeline, with a lossy sink.** The stream advances post-dispatch
in `mw_citta_consciousness` (`tools/middleware.py:1819`; registered `dispatch_table.py:637`,
`:686`): inputs tool name, wall time, sensorium coherence (fallback 1.0 success / 0.4 failure),
DepthGauge/sensorium depth, tone `neutral|frustrated`; middleware passes `neuro_signals={}`
(not None), so the auto-enrichment branch is skipped (`citta_cycle.py:148-149`). Transformation:
`CittaVector.from_moment` (16D) plus tuned per-dimension modulation of the 8 coherence dims
(`:150-197`), trajectory append, coherence history, depth transitions. Parallel path:
`prat_resonance.record_resonance` (`tools/prat_resonance.py:555,656,671`) and the chat/TUI
interfaces (`interfaces/chat.py:787`, `interfaces/unified_tui.py:930`).
- Outputs: `$WM_STATE_ROOT/citta/stream.jsonl`, rewritten every 5 moments from a
  `deque(maxlen=100)` (`citta_cycle.py:116-118`, `:407-415`) — a rolling window, not an
  append-only stream; `save_citta_state` writes `stream_state.json` (history capped 100,
  `citta_stream.py:37`; callers `prat_resonance.py:631`, `meta_tool.py:3164`,
  `consciousness/lifecycle.py:288`); `citta_bridge.check_and_store` significance-gates CITTA
  memories into `GALAXY_CITTA` with a 60 s floor (`citta_bridge.py:37`, `:58-141`, `:199`,
  `:328`; caller `prat_resonance.py:673`), gates = depth change, tone distance ≥0.7, coherence
  milestones (0.5-0.95), vector displacement ≥1.5, velocity >2× running average.
- Introspection: `citta.vector/trajectory/coherence` (`registry_defs/cognitive_extensions.py:
  685-707`) and `citta.continuity/cycle/ignitions/sensorium/stream_summary`
  (`registry_defs/unauthored_consciousness.py:112-140`). `citta_stream.py` (198 LOC) is a
  separate JSON continuity layer, not the moment stream; `CittaAlwaysOn` (30 s heartbeat,
  `citta_cycle.py:546-617`) has **no production starter** (no non-test callers of
  `get_always_on`) — dormant.

**The "CITTA 18,204 (85%)" figure is a storage-label artifact.** `SessionRecorder._record`
stores *every* recorded turn as `memory_type=MemoryType.CITTA` in galaxy `sessions`
(`core/memory/session_recorder.py:104`; taxonomy travels in `turn_type:` tags, `:99`, `:114`).
Turns are machine-written by a post-call hook (`dispatch_table.py:699`,
`middleware.py:1706-1760`, opt-out `WM_SESSION_RECORD=0` `:1721`). `citta_bridge` also writes
`memory_type="CITTA"` in another galaxy, so a type-count over the store conflates the session
recorder with the bridge; matrix L163 reads the recorder's constant as a pipeline measurement.

**Dream cycle — 13 phases, fixed order, per-phase DB writes.** v26.0.3 `DreamPhase` has **13**
members: the 12 in `PHASE_DESCRIPTIONS` (`core/intelligence/dream/dream_phases.py:13-24`) plus
`CODE_GRAPH` (v24.3, `dream_cycle.py:61`); `PHASE_ORDER=list(DreamPhase)` (`dream_phases.py:10`),
so the descriptions dict is already one short. Rotation is positional over
`self._phases = list(DreamPhase)` (`dream_cycle.py:133`, `:268`), each phase a cancellable
`DreamJob` (30-60 s timeouts, `:141-155`), report kept in `deque(maxlen=100)` (`:135`,
`:297-299`), `DREAM_PHASE_*` on Gan Ying, and a citta advance at depth "dream"/tone "tamasic"
(`:309-320`). `trigger_cycle()` runs all phases synchronously (`:1758-1784`), reached from
`cognitive_action_loop.py:601-604` (chains `trigger_dream_cycle`→`trigger_emergence_scan`→
`trigger_self_directed_attention`, `:258`) and guna tamasic correction (`guna_balance.py:266,296`).
The background thread starts only via `dream.start` (`tools/handlers/dreaming.py:29`) unless
`WHITEMAGIC_ELIXIR_MASTER=1` (`dream_cycle.py:166-171`); `scripts/dream_overnight.py` runs it in
a terminal (8-phase docstring, stale, `:1-18`).
- Persisted structures by phase: TRIAGE tags + `galactic_distance` rewrites + **DELETE** of orphan `holographic_coords`/`associations` when <500 (`:511-526`) + entity merge at 0.92 (`:492-509`); CONSOLIDATION promotions/clusters, cross-galaxy associations, constellation detect (`:548-631`); SERENDIPITY graph rebuild + association proposals created (`:633-729`); GOVERNANCE centrality snapshot, edge inhibition `strength*0.5`, karma-ledger record (`:731-808`); NARRATIVE LONG_TERM narrative anchors (`narrative_compressor.py:475`); KAIZEN persists emergence insights as memories (`_persist_dream_insights`, `:1635-1681`; docstring names the "self-reinforcing intelligence loop") + recursive-improvement loop (`:950-972`); ORACLE suggest-only (`:974-1045`); DECAY lifecycle sweep (`:1047-1059`); PREDICTION auto-resolves oracle claims in `TemporalForecastDB` by keyword search (`:1095-1190`); ENRICHMENT tags + seed fitness to `wired.json` (`:1228-1445`); HARMONIZE counts imbalance but applies nothing (`:1466-1540`); CODE_GRAPH stores ≤3 hypotheses as `memory_type="dream"` (`:1610-1625`).

**Failure evidence (runaway/284-zombie), code-anchored.** Guards sit outside the cycle: `BoundedExecutor` defaults 4 GB / 80 % CPU / 1 h / plateau (`core/consciousness/autonomy.py:30-47`), anti-loop circuit breaker (`intelligence/agentic/anti_loop.py:1-18`), rate limiter (`tools/rate_limiter.py:3`). Amplifiers inside: `_persist_dream_insights` re-stores what later scans re-read; `_check_ignition_trigger` fires `run_cycle` every 20 advances whenever the **cumulative** ignition count ≥5 (`citta_cycle.py:373-405`; `ignition_events` computed over the whole trajectory, `citta_vector.py:320-330`); `unified_nervous_system` maps `coherence.critical` → dream trigger (`autonomous/unified_nervous_system.py:461`). The matrix attests the 2026-08-01 incident (2.4 GB RSS / 110 % CPU / 284 zombie dream loops / SIGKILL, matrix L36) and `CODE_ARCHAEOLOGY.md:273` records "284 runs / zero output" as lineage history, not code — no Gen1 run log, counter, or artifact reproducing 284 was found (UNVERIFIED).

---

## Selection history

Gen2 folded a 12-phase `DreamPhase` with per-phase handlers
(`WMv9/crates/wm-cognitive/src/dream.rs:46-95`) and added `LearnedDreamCycle` /
phase-effectiveness reordering (`wm-core/src/lib.rs:40`, `wm-cognitive/src/dream.rs:448,
514-531`); **no Gen1 ancestor for learned cycle selection was found** — Gen1 order is the enum
and every threshold is a constant. The field half was never integrated into retrieval:
`spreading_activation.py` (460 LOC; `spread()` `:150-268`, `apply_priming` `:385-424` boosting
`neuro_score`/`recall_count`) is reachable only via explicit `activation.spread/stats` tools
(`tools/handlers/neuro_cognitive.py:50,77`; no recall-path importer), alongside decay
primitives (`decay_associations`, `galactic_map.decay_drift:304`, `neuro_hotpath.decay:186`,
`metaplasticity.decay_all:154`, `memory/neural/decay_daemon.py`).

## Candidate Gen3 expression / manifest notes

- Compile target (pass row): a scheduled **consolidation pass** over already-compiled
  operators — triage/tag, exact-dup refusal, supersession, retention rotation, association
  proposals, narrative anchors — each journaled (`pass.phase`) with persisted report rows,
  replacing the in-memory 100-entry history and silent per-phase `except` fallbacks.
- Not carried without a new manifest: tuned constants (0.92 merge, 0.5 inhibition, 2σ echo,
  50 % overlap), DELETE paths, keyword-evidence claim resolver, kaizen re-persistence loop.
- Field half: candidate primitive remains **activation/decay field** (ancestor above); entry
  gate unchanged; owner unset, no manifest opened here. Gen1 observable to beat:
  `spread()` returns `(primed, total_activated, cross_galaxy_links, duration_ms)` and priming
  is an explicit opt-in write (`apply_priming`), never a recall-side effect.
- **Correction (batch 3, 2026-09-17):** the *read-side* spreading-activation channel **was
  live** in the default planner (six-channel RRF; `search_planner.py:351-400`); only the
  priming *write-back* was tool-only. See `PHASE4_WAVE3_FINDINGS.md` and
  `W3_field_activation.md`; `PHASE4_ERRATA.md` F-13.

## Adversarial cases

1. **Rolling-window amnesia:** >100 dispatches, persist, restart — `stream.jsonl` holds only
   the last 100 moments; `chain_position` continues from the file (`citta_cycle.py:417-458`).
   Any continuity claim must state the window v26 calls cross-session.
2. **Type-label collision:** counting `memory_type=CITTA` across galaxies mixes SessionRecorder
   turns with bridge moments; specs must key on writer + galaxy, not type.
3. **Trigger storm:** synthetic near-threshold steps yield `ignition_events ≥5` early, then
   every 20 advances fires `run_cycle` → `trigger_dream_cycle` → 13 synchronous phases → ≥13
   more citta moments (ignitions cumulative, not delta-based); `trigger_cycle` takes no
   cycle-level lock versus the background `_run_phase`. Assert a bound.
4. **Self-feeding corpus:** repeated KAIZEN on a static set stores emergence output that later
   scans re-find (dup growth; cf. the 37.2 % dup finding). Rotation must dominate.
5. **Docstring vs code:** header promises "gentle — never destructive… no-delete policy"
   (`dream_cycle.py:17-19`) while TRIAGE deletes (`:511-526`) and GOVERNANCE halves edge
   strengths — a frozen spec must fix which sentence is behavior.

## Ablation ideas

- Disable the dream thread and `trigger_cycle`; measure dup counts, promotions, retrieval
  ordering (expect cleanup deltas only, no ordering change; mirrors `W1_retrieval.md`).
- `mw_citta_consciousness` on vs `WM_FAST_CITTA=1` (skips sensorium only) vs removal: latency,
  `_sensorium` payloads, GlobalWorkspace proposals, Dharma coherence escalation
  (`middleware.py:1819-2010`) — isolates what the stream feeds downstream.
- `activation.spread` with/without `apply_priming` on a fixed corpus; verify whether priming
  changes later recall before any "propagation beats retrieval" test.

## Open questions

- Did `dream.start`/`dream_overnight.py`/`dream_daemon.py` ever run against live state? The
  284 figure has no code/log counterpart (UNVERIFIED).
- Errata candidates (wording): 13 vs 12 phases (matrix L115); learned selection is Gen2-side;
  CITTA type-share is a label (matrix L163). `PHASE_DESCRIPTIONS` missing `CODE_GRAPH`; stale
  docstrings ("5 phases", "8 phases").
- Where does the `docs/LINEAGE_LEDGER.md` cited by `PHYLOGENETIC_FRAMING.md:51` live? Not
  found under `WMgen3/docs/` (UNVERIFIED). CittaVector's tuned multipliers and 16D basis have
  no selection history — ever validated against an outcome? (UNVERIFIED.)
