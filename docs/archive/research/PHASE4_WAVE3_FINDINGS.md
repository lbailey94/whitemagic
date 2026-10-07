# Phase 4 — Wave-3–5 findings (lenses · strange Gen1 · hard remainder) + batch index

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to the
wave-1/2 masters and `PHASE4_ERRATA.md`. Detail in `docs/findings/W3_*.md` (six files,
~845 lines). Same per-row format.

---

## Subagent batch 3 (2026-09-17) — file index

| File | Scope | Headline findings |
|---|---|---|
| `W3_lens_projection.md` | lenses | v26's coordinate "lens" was a **silent always-on stage** (5D KNN as an RRF channel, weight 0.5, fail-soft with no caller disclosure); Gen1's embedding projection was **item-side only** (query coords heuristic → the spatial channel could not reflect query similarity); Gen2's own `Coordinate5D` is **hash-derived and self-documented "semantically meaningless"**, its semantic path (`put_semantic`) has **zero production callers**, yet `find_similar` is live in the Connect cycle comparing anchor-TF query coords against hash stored coords; **no HRR operators exist in Gen2 crates**; Gen2 serving has no lens at all (weighted BM25/vector/importance blend behind an embedder gate); the anatomy of a *declared optional lens* is already on record from the gated series |
| `W3_geneseed.md` | Geneseed | today's Geneseed is a **real but different-function miner** — `git log --numstat` + commit-message substring classification, writes `geneseed:pattern` **tags only, no parent edges**; routes registered but **undeclared**, no daemon caller; the Gen2 port is an **exact copy** of Gen1's Rust miner (recovered from archive); v26 **shipped a second organ** — `GeneseedVault` (template forks with `parent_id`, Ed25519, usage-stat deprecation) — which Gen2 dropped; the V9.1 typed-parent-edge design has **zero code in either generation**; Gen2's own Q04 disposition says "Retire (code); canonized docs" while WMgen3 keeps EXPERIMENT manifest-gated |
| `W3_simulation_imagination.md` | simulation | TZPF is a **scorecard, not an engine** (seven keyword-scored metrics + Brier/Murphy over claim dicts); "TZPF/superforecaster" names **two different organs**; Gen1 rollout machinery existed but **toggle-off and self-scored** (SimulationOrchestrator persisted research-galaxy memory + a Research DAG; PossibilitySpaceExplorer self-referential fitness); no `ImaginationEngine` class in Gen1; Gen2 "**speculative**" verified as **speculative *decoding*** (draft+verify inference) — must not be read into this row; Gen2 has **four disjoint organs** (curated claims ledger; full-profile `sim.*`; `[Experimental]` imagine with **stub world-model default**; dream Oracle counterfactual replay writing Hypothesis memories) |
| `W3_field_activation.md` | field/activation | **v26 read-side propagation was live, not tool-only** — the default planner includes a spreading-activation channel feeding `graph_score` into the six-channel RRF (corrects a wave-2 claim; only the priming write-back was tool-only); **Gen2's "300 s decay" is declared but never applied** (`tick_decay` has zero callers; the daemon stimulates and clamps at 1.0 → saturations never decay); **no measured case anywhere** (WMv9's own note: "expansion currently has zero benchmark evidence for value or harm"); Gen2's live propagation is offline only (dream Oracle hub-reach, Gan Ying sweep, `graph.propagate` tool); decay constants are ad-hoc (not benchmark-derived) and v26 priming had a rich-get-richer asymmetry |
| `W3_mesh_transport.md` | mesh/transport | Gen1 mesh was **three unwired organ systems** (Go `mesh_aux` with no committed binary; Python `mesh/` test-only importers; iceoryx2 published `wm/events` with no in-tree receiver); the clone-swarm story retired at the **measured ~97 clones/s** (local FFI search, not transport); Gen2 mesh is **live but strictly opt-in** — discovery gate (signed beacons, TOFU, replay cache, HKDF subkeys) is real code, the semantic gate is authority enforcement only; **RPC frames are unsigned and post-connect messages unauthenticated** (discovery is); **no egress/consent hook** exists in mesh tools (Charter §3.5 unmet beyond opt-in) |
| `W3_reflex_boundary.md` | reflex/sensor/actuator | the hardware path is **real and wired in production** (`linux_hardware_bus()` registers sysfs fans/LEDs as writable actuators; the daemon runs the unreviewed Sensorimotor cycle); two reflex organs — `reflex.dispatch` builtins return descriptions while `actuator.command`/`reflex.evaluate` **actually write sysfs** and never consult `SafetyMask`; **production ships `permissive()` = SAFETY_ALLOW_ALL** (the safety mask is inert); timescale tiers are declaration, not real-time (bus spawns no tasks); Gen1 ancestry "none" overstates (v26 had dormant *sensing*, no actuator/e-stop code); CONV L2627 boundary verified |

## Consolidated errata candidates (batch 3)

1. **Field wording (map §3.3 + wave-2 claim):** v26 read-side SA channel *was* live in the
   default planner; Gen2's 300 s decay is never applied — `THEORY_MECHANISM_MAP.md` §3.3's
   "activation with 300 s half-life" should read "declared half-life, tick never called."
   (`W2_citta_dream_cycles.md` corrected in place.)
2. **E21 / reflex ancestry:** "none (Gen2 added)" overstates — v26 had dormant sensing
   (ambient sensorium, psutil physical metrics, declared 10 ms bucket with no callers); no
   actuator/e-stop code. Wording correction only.
3. **Geneseed name ≠ function:** "Geneseed" shipped twice as *different* functions (git miner;
   v26 template forker); the decomposition's "concept only" is right for the **lineage design**,
   wrong for the name. Also: route manifest counts differ live vs tag — **303/86/217 on
   9.1.9-dev main vs 302/85/217 at the v9.1.8 tag** (Track A's release figures stand; live
   counts must say "main").
4. **Simulation row:** `sim` route count is 4 (adds `simulation.calibrate`); the row bundles
   three disjoint organs (TZPF scorecard / possibility explorer / speculative decoding); Gen1
   had two distinct `simulation.status` handlers. Wording corrections only.
5. **Mesh precision:** keyless beacons for a *bound* peer are dropped, not merely "address
   hints" (`transport.rs:1213-1232`) — precision note for `PHASE4_GEN2_DELTA.md` §2.2.
6. **Reflex safety posture:** `daemon.rs` says "all 7 cycles" vs 8 in `CycleType::all()`;
   e-stop docs vs `SAFETY_DENY_ALL`; `SAFETY_DEFAULT` documented as production posture while
   permissive ships. **Safety-mask inertness is the load-bearing item** — any Gen3 link must
   not inherit an unenforced mask.

## Divergences for migration specs (batch 3)

1. **Lens vs stage:** a Gen3 lens must be declared, activatable, cost-accounted, journaled —
   the gated series is the template; Gen2's coords are render/diagnostic (hash-derived), so no
   Gen2 lens behavior is available to inherit.
2. **Field:** no measured propagation-beats-retrieval case exists in either generation; the
   candidate primitive stays gated on exactly that task.
3. **Geneseed:** split the name/design; the EXPERIMENT row's acceptance cannot cite any
   existing lineage mechanism (there is none — the miner is unrelated), and Gen2's own
   disposition retired its code.
4. **Mesh:** the two-gate boundary currently has one real gate; specs must state which gate is
   exercised, and must add the missing consent/egress hook before any communicate surface.
5. **Reflex:** link must keep the hardware path behind an explicit, enforced boundary — the
   current mask is documented but inert in production.

## Remaining open questions (batch 3)

UNVERIFIED carried: whether v26's spatial channel was ever load-bearing; live Gen2 coordinate
provenance; whether Gen1 simulation ever ran outside tests; whether Gen2 records carry an
explicit `simulated` tag (domain law checked WMgen3-side only); v26 Rust `activation.rs`; mesh
RPC exploitability; whether the hardware bus was ever non-empty; `reflex_bench` results. The
wave-3–5 extraction is now complete; the **wave plan** is the next artifact.
