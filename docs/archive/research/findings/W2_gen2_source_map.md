# W2 — Gen2 9.1.8 capability-source map (wave-2 native-cognitive rows)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` and `PHASE4_GEN2_DELTA.md`.

Pin: `WMv9` workspace `Cargo.toml:23` = `9.1.8`; source reads only — no build/test run. Wave-1 rows are
indexed in `PHASE4_WAVE1_FINDINGS.md` and not repeated here; crate paths are relative to `crates/`.

---
## 1. Associations / relations
- Typed edges: `LinkType` 7 variants `related · extends · contradicts · supersedes · temporal · causal ·
  cascade` (`wm-memory/src/associations.rs:21-67`); `Association{weight, co_activation_count,
  last_activated_at, decay_half_life_days=90}` `:86-123`; Hebbian ops `activate :154`, `decay :167`,
  `should_prune :179`; LMDB in the Associations galaxy (`AssociationStore :203`), `find_from :292` /
  `find_to :316`, cross-galaxy hop `traverse_cross_galaxy :343`, `find_cycles :395` (retention guard).
- Tool surface: `memory.relate` (`wm-tools/src/expansion/association.rs:546`; relate re-activates existing
  edge with `activate() :294`; `derive_follows` links Sessions), `memory.associate_mine :45`,
  `memory.corroborate :150` (session set `corroborated_by`; ranking effect only with
  `WM_CORROBORATION_WEIGHT > 0`), `memory.associations` (`wm-tools/src/lib.rs:2229/:2248`),
  `graph.walk` BFS depth-3/nodes-100 (`wm-tools/src/expansion/graph.rs:20/:42`).
- KG layer: `kg.extract` capitalization-NER → typed associations (`expansion/knowledge_graph.rs:203`,
  writes Associations+reads Codex), `kg.query` `:318` (entity required by `wm-mcp/src/contract.rs:18`),
  `kg.top` `:454` hub ranking (read-only Codex).
- Serving-path integration: `expand_with_graph` (`wm-memory/src/recall.rs:1199`) injects/boosts one hop and
  calls `activated_edge.activate()` `:1238`; `graph_weight` default `0.0` `:93/:145`, env
  `WM_RECALL_GRAPH_WEIGHT :193`; `association_rerank` default false `:135/:153`; Smarana applies co-activation
  bumps + decay (`wm-cognitive/src/smarana.rs:506-564`).
- Contract: typed edges (incl. `supersedes`/`contradicts`) persist with Hebbian counters; graph→recall
  influence is explicit and default-off. Status: **live** (mechanism) / **knob-gated** (recall integration).

## 2. Retention / lifecycle
- `RetentionEngine` (`wm-cognitive/src/retention.rs:88`): 7 signals averaged in `evaluate :110`; thresholds
  retain 0.35 / decay 0.15 `:70-71`; `sweep :294` only decays importance ×0.5/×0.8 `:317-323` — never
  deletes. Sole importer is the dream Decay phase (`wm-cognitive/src/dream.rs:1475-1476`).
- Tiers: `Tier{Working,Episodic,Semantic,Archival}` (`wm-memory/src/memory.rs:77-101`); default Episodic for
  pre-S5 rows; dream cycle is the only transition path (doc `:70-76`). Cold tier = compressed archive
  (`wm-memory/src/cold_storage.rs:11-18`, `ColdRecord :284`); digest synthesizes a `Tier::Semantic` hot node
  `:757` (W1 §8 has the rotation/thaw detail).
- `Lifecycle` (`wm-memory/src/lifecycle.rs:44`): `consolidate :88` (access/recency boost + daily decay),
  `forget :156` — deletes rows via `store.delete` when `should_forget` fires; `run_full_cycle :181` (skips
  Substrate/Dharma/Karma/Embeddings/Telemetry), `phagic_digest :214`, `run_full_cycle_phagic :225`. No
  callers found outside `wm-memory` — the delete-capable organ is dormant.
- Currentness strata: `ValidityState` in metadata `memory.rs:195-199`; dream `validity_sweep`
  (`dream.rs:954`) derives `superseded` from edges, gated `WM_VALIDITY_SWEEP=1` exact-match `:40`; request-time
  enforcement off unless `WM_VALIDITY_ENFORCE=1` (`recall.rs:1003`).
- Daemon: non-destructive phagic sweep (`wm-mcp/src/daemon.rs:862`); `retention.prune` propose-only cycle
  (W1 §8; `wm-tools/src/expansion/autonomous.rs:306`). Contract: forgetting decays, never purges; the only
  delete-capable path (Lifecycle::forget) is unwired. Status: **live** (retention+cold) / **unwired** (Lifecycle).

## 3. Citta / dream / cycles
- Dream: 12 `DreamPhase`s (`wm-cognitive/src/dream.rs:46`, count test `:1785`); `DreamCycle :438`,
  `run :565`, brain-wave gate `should_run :556`; daemon drives it on `dream_interval` (600 s default) in
  Theta/Delta (`wm-mcp/src/daemon.rs:75-76/:494-518`).
- Learned cycle: `LearnedDreamCycle` (`wm-core/src/mutable.rs:468`) — effectiveness map, `phases_to_run :548`
  (skip when score < 0.2 after 5 runs, `:486-488`), `record_phase :515`, `with_learned` (`dream.rs:514`),
  persistence via `save_learned_cycles` (`daemon.rs:36`).
- Citta heartbeat: 4 phases (`citta_engine.rs:24`); `CittaCoordinator :580`, 5 OG engines registered
  `:603-610` (Kaizen `:238`, Prescience `:307`, Serendipity `:379`, Foresight `:437`, Apotheosis `:502`),
  `run_cycle :625`; `CittaHeartbeat` (`citta.rs:539`, `beat :592`); daemon runs both on `citta_interval`
  (`daemon.rs:623`).
- Alchemical: `AlchemicalRoundCoordinator` (`alchemical_round.rs:336`) with 28 declarative `EngineProfile`s
  (SkillForge `:248`, Apotheosis `:265`); `execute_alchemical_round :370` returns heuristic counters
  (clusters = 7/3 by health, synapses = 12+coherence×10) — not engine execution.
- Routes: `citta.status` (`consciousness.rs:38`), `citta.reflect :84` (scan summary), `citta.history :519`,
  `dream.status :139`, `dream.trigger :190` (writes a Dreams marker only — the daemon is the runner),
  `dream.analyze :597`. Contract: cycles run under daemon scheduling; tool triggers observe or write markers.
  Status: **live** (daemon dream/citta) / **experimental** (learned phase selection) / **unwired**
  (28-engine catalog).

## 4. Gan Ying / resonance
- Vocabulary: 10 `EventCategory`s (`wm-cognitive/src/resonance/event_type.rs:22-75`); `EventType` enum `:93`
  (module doc claims 234 types — count UNVERIFIED); category→event mapping `:650-659`.
- Bus: `GanYingBus` (`resonance/bus.rs:291`), subscribe `:382`, `emit :410` / `emit_with :451` with cascade
  rules `default_cascade_rules :162`, recent ring `:535`, optional file persistence `enable_persistence :353`.
- Autonomous layer: `AutonomousGanYing` (`resonance/gan_ying.rs:1005`), `daemon_pulse :1043`/`run_sweep :1063`;
  `PreConsciousBuffer :813` with L1 fringe `:656` / L2 reservoir `:748`, token probe `:852`;
  `CircadianPhase :65` weights.
- Wiring: bus constructed `wm-mcp/src/server.rs:660`, held by the server `:92`; daemon attaches at `:307` and
  sweeps at `:1036` (pre-warm counters in stats); bus tools `bus.stats`/`bus.emit`/`bus.recent`
  (`expansion/resonance.rs:37/:96/:160`, register `:225`); other emitters = coordination `:447`, research,
  sensorimotor tools. Contract receipts: `wm-cognitive/tests/gan_ying_recall_path.rs` +
  `wm-tools/tests/gan_ying_normal_tools.rs` (cue → synchronicity → Research → normal `memory.search`/
  `memory.read`, byte-exact).
- Contract: process-local event bus with cascades; the daemon pre-warms a pre-conscious buffer each sweep;
  coincidence→action is test-proven, not benchmarked. Status: **live**.

## 5. Engines / recipes
- Engine trait/registry: `CittaEngine` + `CittaCoordinator::with_og_engines` (5 engines, §3); outputs are
  scored findings from context (e.g. Kaizen counts frictions/health `citta_engine.rs:253-290`).
- Skill surfaces: `skill.invoke` (`expansion/pipeline.rs:252`) and `skill.list :320` — skills are Codex
  memories tagged `skill`; invocation is a lookup/echo, there is no compiler or recipe runtime.
  `SkillForge` exists only as an `EngineProfile` name (`alchemical_round.rs:248`).
- Imagination engine: `imagine.scenario`/`imagine.predict`/`imagine.reflect` (`expansion/imagination.rs:86/:221/:323`);
  `CycleType::Research` = `research.scan` (`autonomous.rs:76/:718`) with planner-tier handlers;
  `research.topic :308` / `research.repo :427` / `research.rabbit_hole :588` are the tool-side probes;
  dream `phase_oracle` consumes the imagination engine (`dream.rs:1335/:1372`).
- Other named engines: `kaizen.correlate` = Pearson (`expansion/correlation.rs:351/:484`),
  `serendipity.surface` (`expansion/patterns.rs:188`), `apotheosis.check` (`consciousness.rs:409`, proxy
  score from Citta memory importance).
- Contract: engine names are catalogs or single-purpose tools; only `skill.*` is an invocable recipe surface,
  and it is lookup-only. Status: **live** (skills lookup, research/imagination tools) / **unwired**
  (SkillForge compile, 28-engine execution, recipe runtime) — consistent with the missing-primitive reading.

## 6. RSI / friction
- Log path: `friction.log` (`wm-tools/src/expansion/rsi.rs:196`) with content hash dedup `:99-138`;
  regression detection = resolved entry + same hash → new entry with escalated severity
  (`is_resolved :144`, `escalate_severity :151`); `friction.auto_log :810` writes dispatch errors to
  Telemetry under the evidence importance ceiling `:118-124`.
- Proposals/review: `friction.review :413`, `improve.proposals :882` (runs `CycleType::Improve`),
  `redteam.proposals :966` (`CycleType::Redteam`), `improve.active_proposals :1186`,
  `redteam.from_friction :1280`, `redteam.coverage_report :1442`; Improve/Redteam carry
  `requires_human_review = true` (`autonomous.rs:105`).
- Resolution: `friction.resolve :1047` requires `friction_id` + `resolution_note` + method; tags
  `rsi:resolved`/`rsi:resolved_method:*`/`rsi:resolved_at:*` `:1093-1101`; karma
  `record_friction_resolved :1125`; workspace Reward emit `:1130`. There is **no independent verification**
  of a resolution — resolution is caller-asserted, and regression is caught only when the same hash is logged
  again. Contract: friction ledger lives in memory (Codex+Telemetry), proposals are review-gated, resolutions
  are asserted. Status: **live**, full-profile only (curated profile excludes the RSI loop,
  `wm-tools/src/profiles.rs:40-43`).

## 7. Self-model / conformal / calibration
- `SelfModel` (`wm-selfmodel/src/lib.rs:87`): `record :113`, `forecast :138`, `check_alerts :177`,
  `confidence :219`, `snapshot :280`, cognitive subset `:368`; server holds `Arc<Mutex<>>` (`server.rs:92/:853`),
  refresh `:2819`, confidence injected into dispatch context `:3689`; persisted `self_model.json`
  (`wm-mcp/src/bin/wm.rs:3775-3786` thresholds).
- Self-model tools: `selfmodel.forecast` (`expansion/selfmodel.rs:69`), `selfmodel.alerts :155`,
  `selfmodel.snapshot :234`, `selfmodel.gnosis :327` (per-metric health verdict), register `:435`.
- Conformal: `SplitConformalClassifier` (`wm-conformal/src/split.rs:42`; `add_sample :70`, `fit :89`,
  `predict_set :105`), regressor + `AdaptivePredictionSets`; coverage eval `calibrate.rs:13`, 5 % slack `:82`.
  Tools: `conformal.fit_classifier` (`expansion/conformal.rs:213`), `fit_regressor :294`, `predict_set :388`,
  `predict_interval :472`, `status :542`, `monitor :610`, `export/import :769/:816`;
  `ConformalStore` `:30`; persisted `calibration_store.json` (`server.rs:1388`).
- Recall feedback: `WM_RECALL_CONFORMAL_ALPHA` (`wm-memory/src/recall.rs:30`, parse `:218-221`);
  `record_relevance_feedback :323`, `conformal_disclosure :348`, per-result `in_conformal_set :77`,
  hybrid disclosure `:957/:1089`; tool `memory.recall_feedback` (`memory_ops.rs:1806`, refuses honestly when
  the env knob is unset `:1904-1908`).
- Adjacent (not re-covered): claims calibration ledger — W1 §6 (`wm-simulation/src/claims.rs:316/:379`).
  Contract: conformal guarantees exist only after fit with labeled samples; recall-side conformal is
  env-gated and refusal-honest. Status: **live** / **experimental** (env-gated recall conformal).
## Gaps / unverified
1. `EventType` count "234" is a doc claim (`event_type.rs:93`); variant enumeration not counted in this pass.
2. Curated-profile exposure per route not verified; only prefix rules read (`profiles.rs:40-43` excludes
   RSI/friction/redteam/self-play/imagination from `curated` — route-level check pending).
3. Whether daemon-level Dream `validity_sweep` runs in a given session depends on `WM_VALIDITY_SWEEP=1`
   (exact match) — no default-on evidence found.
4. `Lifecycle` has no callers outside `wm-memory` in this grep; a bin/example path invoking `run_full_cycle`
   directly was not traced; karma debt math (`record_friction_resolved`) only skimmed.
5. `kg.extract` entity quality (capitalization heuristic) and its actual recall impact not measured.
6. `apotheosis.check` and `citta.reflect` are scan proxies over Citta memories; relation to the
   `Apotheosis` struct (`citta.rs:451`) is UNVERIFIED.
## Divergences vs ratified verdicts

1. **"Hebbian parked" (tree §3)** — Hebbian dynamics are implemented in `wm-memory` (activate/decay/
   co_activation_count; `memory.relate` re-activates; Smarana applies decay). Parked describes the
   **serving path** (graph_weight 0.0, association_rerank off), not the mechanism; specs must say which.
2. **"retention/lifecycle"** — two organs: `RetentionEngine` (decay-only, wired to dream) and `Lifecycle`
   (delete-capable `forget`, unwired). "Mindful forgetting is gentle" holds for the engine, not for
   `lifecycle.rs:156`; the link-to-compile row must name the organ.
3. **Citta/dream "consolidation half"** — dream is live end-to-end under the daemon; the citta and
   alchemical layers are heuristic report generators (counts/proxies), and the 28 engines are names in a
   catalog, not execution units. "Consolidation half" is real; "engines" are surface vocabulary.
4. **RSI "think over journal"** — the loop is memory-ledger-backed (Codex+Telemetry), not journal-backed;
   resolutions are caller-asserted with only relog-regression detection; the whole loop is outside the
   curated profile. No verification receipt exists to import.
5. **"calibration"** — four separate universes: self-model confidence/forecast, conformal tool store
   (`calibration_store.json`), env-gated recall conformal, and the claims ledger (W1 §6). Ratified wording
   should be per-universe; recall conformal explicitly refuses when unconfigured.
6. **Currentness strata "already native"** — native only as enum + dream-only sweep behind
   `WM_VALIDITY_SWEEP`/`WM_VALIDITY_ENFORCE`; not a request-time derived relation (W1 divergence 3:
   no first-class `supersedes` on the serving path).
