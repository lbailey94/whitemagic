# Phase 4 — Wave-4 findings: simulation / imagination (strange Gen1)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` / `PHASE4_WAVE2_FINDINGS.md`. Row source: `PHASE4_GEN1_TREE.md` §3
wave-4 (`:34`, `:67-68`); verdict **EXPERIMENT** (`PHASE3_DECOMPOSITION.md:174`, E19 `:197-199`,
`:222-227`). Format per row: **observed behavior · selection history · candidate Gen3
expression/manifest · adversarial cases · ablation**.

Method: `rg` over Gen1 @ v26.0.3 and Gen2 `WMv9/crates/` (counts stated at use); no cargo/pip/tests.
Epistemic half is law: canon §10 (`DESIGN_CANON.md:245`), Charter §3.8 / Closure 2 (`CHARTER.md:58`),
E19. This file extracts only the **rollout/imagination mechanism** half.

---

## Observed behavior

### Gen1 v26 — a scoring ledger plus an internal parameter search; no world simulator

- **TZPF is a scorecard, not a forecasting engine.** `forecasting/tzpf.py:628` (`compute_tzpf`)
  composes seven text/keyword-scored metrics (DFI/TAR/HC/BCI/PVS/NRS/PI, `:51-528`) plus Brier +
  Murphy (`:531`); it reads claim dicts and simulates nothing. CLI `forecasting/__main__.py:190`.
- **What persisted:** the claims ledger, not TZPF outputs — `forecasting/temporal_db.py:46`
  (SQLite `predictions`), seed load `:147` (idempotent, from `prescience_claims.yaml`), oracle
  claims `:483`/`:573`/`:621`. Wave-1 already recorded the degeneracy (all-validated seed set) and
  destructive YAML sync (`PHASE4_WAVE1_FINDINGS.md:111`); no new persistence was found here.
- **SimulationOrchestrator** (`core/consciousness/simulation_orchestrator.py:83`): two modes —
  *introspective* = optimize internal parameters over `PossibilitySpaceExplorer` (`:136-202`);
  *external* = SDE / rare-event / superforecaster via the polyglot MC orchestrator
  (`:391`/`:419`/`:446`). Persistence helpers: `_persist_memory` → research galaxy (`:468`),
  `_record_dag` → Research DAG experiment/trial/result (`:493`). Oracle→BO parameter guidance
  `:110-132` (`oracle/oracle_bo_bridge.py:31`).
- **PossibilitySpaceExplorer** (`core/consciousness/possibility_explorer.py:78`): uniform MC trials
  (`:175-186`) over four *internal* spaces (`:88-122`: guna balance, coherence, emergence
  thresholds, health setpoints); fitness functions are self-referential heuristics (`:375-443`);
  history is in-memory, capped (`:215-222`); winners live in `_best_params` (no store). This is the
  same organ wave-2 flagged as self-scored winners (`W2_rsi_selfmodel.md` headline).
- **Counterfactual** (`core/evolution/counterfactual.py:52`/`:159`, synthetic control + bootstrap
  CI) is Python-native; only exposure = polyglot Rust bridge (`polyglot/registry.py:34-43`;
  `core/whitemagic-rust/crates/wm-evolution/examples/evolution_bridge.rs`), no other Python caller
  (`core/evolution/causal_ledger.py:10` is a docstring).
- **No Gen1 imagination organ found:** `rg 'class .*Imagination|ImaginationEngine'` over
  `core/whitemagic` = 0 matches; `imagine` hits are critique vocabulary
  (`core/intelligence/bicameral.py:543-561`). Gen2's world-model/scenario organs are Gen2 additions.
- **Wiring/gates:** 17 simulation-family routes are dispatchable in v26 (`tools/dispatch_memory.py:59-66`
  = 8 `simulation.*`, `:185-193` = 5 `mc.*` + 4 orchestrator routes; handlers `tools/handlers/simulation.py:87`).
  Both relevant feature toggles default **off** (`config/feature_toggles.py:165-169`, `:177-180`). Tests
  exist (`core/tests/unit/test_tzpf.py`, `test_simulation_integration.py`); no Gen1 DB on this host, so
  **UNVERIFIED: what actually ran outside tests** (inherits wave-2 host gap).

### Gen2 WMv9 — four disjoint organs answer to "simulation/imagination"

- **`wm-simulation`** (11 source files, `crates/wm-simulation/src/lib.rs:1-42`): MC, counterfactual,
  forecasting, Brier/Murphy calibration, Bayesian optimization, PCE superforecaster, rare-event,
  SDE. Live use: (a) the **claims ledger** (`claims_tools.rs:18`/`:36` → `ClaimsLedger`, persisted
  `claims_ledger.json` per AGENTS.md), routes `claims.*`, **in the curated profile**
  (`profiles.rs:44-47`); (b) standalone tools `sim.mc` / `sim.forecast` / `sim.counterfactual`
  (`simulation_tools.rs:46`/`:139`/`:223`; manifest `route-schema-manifest.json:2913-2925`),
  **full-profile only**; (c) `simulation.calibrate` (`simulation_tools.rs:350`, manifest `:2931`)
  backed by `CalibrationStore`.
- **Imagination engine** (`wm-bicameral`): `world_model.rs:241` (`predict`/`rollout`),
  `scenario.rs:142` (`imagine`) / `:246` (`predict`) / `:254` (`reflect`),
  `evaluator.rs` (multi-criteria score). Tools `imagine.scenario|predict|reflect`
  (`expansion/imagination.rs:86`/`:221`/`:323`) are labeled **`[Experimental]`** (`:96`). The
  world model builds from env LLM handlers and **falls back to `StubWorldModelHandler`**
  (`world_model_handlers.rs:249-266`) — default deployments roll out stub text.
- **Bridge:** `simulation_bridge.rs:1-19` wires MC/forecast/cf/sensitivity into scenario
  enrichment; it is opt-in per call (`enrich_simulation`, `imagination.rs:114-156`).
- **Dream-cycle Oracle counterfactual replay (canon):** `phase_oracle` uses
  `ScenarioEngine::reflect()` on hub memories (`wm-cognitive/src/dream.rs:1335`, `:1372-1398`) and
  persists accepted hypotheses as `MemoryType::Hypothesis` in the Research galaxy through a
  `NoveltyGate` (`:1405-1409`). The Research cycle's imagination path does the same for
  `score > 0.5` (`autonomous.rs:2106-2144`). These are the readers of scenario output.
- **`speculative.decode` / `speculative.stats` = speculative *decoding*** (draft+verify inference
  acceleration), verified: `wm-bicameral/src/speculative.rs:1-25` (segment-level adaptation),
  routes registered only when a decoder is supplied (`expansion/bicameral.rs:215-242`), decoder
  built from env in `wm-mcp/src/cyberbrain.rs:99-124` and wired at `server.rs:1076-1084`.
  **Not** epistemic speculation; name ≠ function.
- **Profile status:** curated excludes `imagine*`/`sim.*`/`speculative.*` by prefix
  (`profiles.rs:40-47`) — the rollout surface is full-profile only; only `claims.*` ships.

## Selection history

Gen1 kept simulation as an **optional toggle** (default off) whose persisted artifacts were claims
plus research-galaxy/DAG notes; its optimizer scored its own fitness (no external outcome), and the
claims side was degenerate (W1). Gen2 **split the family**: calibration/claims became a live,
curated product; imagination became an EXP-labeled bicameral tool set with stub fallback; the dream
Oracle gained a bounded counterfactual-replay consumer; MC/forecast/cf remain standalone full-profile
tools; spec-decoding stayed inference machinery. Across both generations the **epistemic half**
(domain immutability, `simulation ≠ evidence`) hardened into law while the **rollout half** never
acquired a measured outcome — matching the EXPERIMENT verdict.

## Candidate Gen3 expression / manifest notes (no proposal — manifest completion only)

- **What already exists as law:** domain immutability + `simulated` tagging (Closure 2,
  `CHARTER.md:58`); simulated priors ground only through external outcomes (canon §10,
  `DESIGN_CANON.md:245`); E19 acceptance = domain-tagging canaries **plus** a task where simulation
  improves a measured outcome vs ablation (`PHASE3_DECOMPOSITION.md:226-227`).
- **What exists only as mechanism:** MC/forecast/Brier (`wm-simulation`), scenario loop
  (`wm-bicameral`), hypothesis persistence (`dream.rs`, `autonomous.rs`), env-built world model
  with stub default.
- **Manifest fields still unearned:** ancestor = Gen1 TZPF/superforecaster + SimulationOrchestrator
  (two organs — see Open questions) + Gen2 surfaces; wire = `simulated`-domain records + hypothesis
  records + a rollout pass over admitted evidence; acceptance = the E19 pair; **owner unset**.

## Adversarial cases

1. **Stub-in-flight.** A rollout that never calls a model (stub handlers,
   `world_model_handlers.rs:249-266`) must not be counted as "the mechanism ran"; any future
   acceptance must distinguish stub from real handler.
2. **Self-scored winner.** Gen1's possibility fitness functions are internal heuristics
   (`possibility_explorer.py:375-443`); a rollout that tunes parameters scored by the same loop is
   the self-certification class (W2 RSI) — the E19 external-outcome clause is the guard.
3. **Domain laundering via enrichment.** Bridge numbers are embedded in scenario JSON returned to
   callers (`imagination.rs:140-156`); if any downstream write stores them untagged, Closure 2 is
   violated. Canaries must cover the enrichment path, not only direct `sim.*` outputs.
4. **Hypothesis flooding.** Dream Oracle emits a hypothesis per hub with importance > 0.5
   (`dream.rs:1371-1409`); the novelty gate dedups text predicates only — measure store/retrieval
   effect and false-hypothesis retention before any reuse.
5. **Causal over-read.** `sim.counterfactual` (synthetic control + bootstrap) can be read as causal
   impact; nothing discloses unmodeled confounders — check parity with the `[Experimental]` label.

## Ablation ideas

- Toggle `enrich_simulation` (`imagination.rs:114`): expect no change in scenario generation;
  measure whether enriched numbers change any downstream decision.
- Toggle imagination attachment in dream/Research (`dream.rs:1373`, `autonomous.rs:2106`): compare
  hypotheses stored and Research-galaxy composition against the heuristic fallback.
- Swap stub vs real world-model handler (`world_model_handlers.rs:249-266`): the only knob that can
  make a rollout pass informative.
- Closure-2 canary exercise: inject a `simulated` record and attempt world-domain retrieval,
  including once via bridge-enriched scenario output.

## Open questions (incl. errata candidates for operator check)

- **Errata candidate — count:** the row's `sim (3)` matches `sim.*` exactly, but a fourth
  simulation-machinery route `simulation.calibrate` exists (`simulation_tools.rs:350`, manifest
  `:2931`); Gen1 additionally had two different `simulation.status` handlers (orchestrator status
  `dispatch_memory.py` vs pre-execution simulator `dispatch_security.py`).
- **Errata candidate — conflation:** "TZPF/superforecaster → folded" names two organs (scorecard vs
  LHS→PCE→Sobol→BO pipeline, `polyglot_mc.py:75` / `wm-simulation` `pce.rs`), and the row's
  `speculative (2)` is inference decoding, not epistemic speculation — three disjoint organs in one
  row.
- **UNVERIFIED:** whether Gen1 SimulationOrchestrator/superforecaster ever ran outside tests (no
  Gen1 DB on host; tests only); whether v26 `evolution_bridge` binaries were built/shipped; whether
  `init_imagination` is active in the live wmv9 daemon (`server.rs:2371-2385`) so dream Oracle
  replay fires in production; whether Gen2 records carry an explicit `simulated` tag anywhere
  (domain law checked WMgen3-side only); whether Gen1's 13-phase dream had an oracle counterfactual
  phase (not found).
- Does the `simulation.calibrate` route family collide with the pre-execution simulator naming
  (`governance.py:268-288`) in a way a migration spec must rename before reuse?
