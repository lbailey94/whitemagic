# Phase 4 — Wave-2 findings: RSI/friction + self-model/feedback loop

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_GEN1_TREE.md` §3 (wave 2: "RSI/friction (think over journal)", "self-model/conformal
(inspect + calibration)") and `PHASE4_WAVE1_FINDINGS.md` (format). Verdicts under study:
**RSI/friction PRESERVE IMPL. → link · E20**, **Self-model/conformal PRESERVE IMPL. → link · E18**
(`PHASE3_DECOMPOSITION.md:173,175,193-203`). Counts generated with `sqlite3
"file:…/feedback.db?immutable=1" "SELECT COUNT(*) …"` (read-only URI), `wc -l`, `rg -c`; cites are
Gen1 v26 @ v26.0.3 (`og_whitemagic/core/whitemagic/`). **UNVERIFIED** = no fossil found.

**Ancestors.** `core/evolution/autodidactic_loop.py` (feedback.db + confidence updates);
`core/evolution/recursive_loop.py` (observe→…→learn→verify); `…/synthesis/kaizen_engine.py`;
`core/consciousness/cognitive_action_loop.py` (`_execute_and_measure`); `harmony/homeostatic_loop.py`;
`core/intelligence/self_model.py`; `agentic/continual_learner.py`; `…/possibility_explorer.py`;
`state/identity/proposals.jsonl` (adjacent). `tools/security/agent_redteam.py` is defensive
security tooling, not this loop (name ≠ function).

## Observed behavior (cites)

**Feedback DB (fossil).** 906 `pattern_applications` · 36 `pattern_outcomes` · 36 `pattern_updates` ·
29 `pattern_correlations` (matches lineage batch 2). Applications 2026-06-23 → 2026-08-02; last
outcome 2026-07-13. Types: integration 336 · quality 198 · theme 135 · ignition 89 · prediction 53 ·
guna_imbalance 49 · emergence 28 · performance 10 · skill_health 4 · **improvement 2**. IDs are
machine cluster names (`integration_cluster_0.0_-0.1`) or count-encoded (`quality_untagged_58381`).
- **Outcome coverage 36/906 = 4.0 %**; 24 distinct patterns; success **2/36** (5.6 %).
- Both "successes" are one event seen twice: `untitled` **155→72** (delta 53.55 %) and **95→72**
  (24.21 %), both `"auto_verified": true`, `performance_gain=delta×100` (`pattern_outcomes.metrics`).
  The dataclass example "3.28x speedup" (`autodidactic_loop.py:41`) is a percent count-drop of the
  detector query.
- 34 failures include `untagged` counts *rising* after the "fix" (58381→58445, 57098→57194).
- Failures decay confidence (0.114→0.0798; 0.01→0.007); wins raise `quality_untitled_95`
  0.1041→0.2729/0.3729 with inconsistent `application_count` (1 vs 2). **Correlations: 1 nonzero of
  29** (`_95`↔`_155`=1.0, n=2); the other 28 are stored as 0.0, not NULL — the matrix is degenerate.
- The 2 `improvement` rows: `kaizen_skill_health_create_neck_3step` ("Amend failing skill:
  create_neck_3step, failure rate 75 %", predicted_impact 0.4, novelty .97/.94) — no outcomes.

**How proposals were applied/verified.**
- `_phase_learn` records each hypothesis as an application with context
  `{source,title,cycle_id,predicted_impact,novelty_score}` (`recursive_loop.py:1428-1456`).
- `verify_outcome` (`recursive_loop.py:1599-1695`) **re-runs the same `engine.analyze()`**; if the
  proposal is *absent* from the new report → `after_count=0` → delta 1.0 → success (`:1644-1662`);
  threshold delta ≥ 0.1 (`:1603`). Proposer and verifier are the same organ — self-certification at
  mechanism level, against canon §5 "operate on evidence, never self-certify"
  (`PHASE3_DECOMPOSITION.md:200-203`). Counterweight: 34 honest failure rows.
- The write path was structurally dead: `_execute_auto_fixable` (`recursive_loop.py:828-869`)
  passes `fix_action` strings (`tag_normalizer.auto_tag_untagged()` `kaizen_engine.py:351`;
  `title_generator.fix_all()` `:323`; `consolidator.merge_exact_duplicates()` `:548`; …) to
  `_execute_and_measure` (`cognitive_action_loop.py:589-706`), whose closed vocabulary is 9 verbs;
  anything else → `"Unknown action"`, `executed=False` (`:706`). No kaizen fix string matches.
  Fossil: `observations.jsonl` holds `"Unknown action: seed_memory_from_template"` and
  `'ConsciousnessLoop' object has no attribute '_tick_t2'` (handler at `:607` calls a method that
  does not exist).
- Who fixed `untitled` 155→72 is **UNVERIFIED** — the auto-fix path could not have.

**Homeostatic loop.** Attached at startup (`orchestration/session_startup.py:802`); levels
`OBSERVE→ADVISE→CORRECT→INTERVENE` (`homeostatic_loop.py:17-18,41-48`), thresholds `:79-119`;
CORRECT examples: low energy → lifecycle sweep (`:437-454`), low dharma → `set_profile("secure")`
(`:472`). Actions live in an in-memory list (`:130`), no persistence found; `state/harmony/
activity_log.jsonl` = 55 rows, **all `"READ"`** (Jul 6–Aug 1) — CORRECT/INTERVENE ever fired:
**UNVERIFIED**.

**Correction (W0 intermission, 2026-09-17):** `whitemagic_dream.log` carries **361 CORRECT
lines** — the graduated ladder *did* fire in the dream loop even though `harmony/` shows only
READs. Qualify any future "never CORRECT" claim by artifact (`PHASE4_ERRATA.md` G-26).

**Self-model.** In-memory deques, window 100, linear-regression forecasts + threshold alerts
(`self_model.py:95-150`); **no state file in either state root** (v26 snapshot, `~/.whitemagic`).
Readers that *act*: `inference/router.py:507-529` (error_rate alert, ETA ≤ 5 → tier upgrade),
`core/fusions.py:150-165` (falling energy, ETA ≤ 15 → proactive dream), `core/automation/army.py:73`.
Display only: `tools/gnosis.py:726-756`, `handlers/cyberbrain.py:177-182`. Only feeder found is the
operator/tool call `gnosis.record_metric` (`gnosis.py:748-756`); no automatic observer calls
`record()` in non-test code, and no forecast ever fired live: **UNVERIFIED**.

**Continual learner.** `observations.jsonl` = 768 tool/action outcome lines → 2026-08-02; loaded
and fed to learned routing (`continual_learner.py:76-85,200-243`), consumed by middleware/dispatch
(`tools/middleware.py`, `intelligence/learning_bus.py`). Crashes (e.g. `_tick_t2`) recurred.
`LINEAGE_LEDGER.md:189` says "`learning/` empty"; a `learning/` dir exists under `~/.whitemagic` —
contents unchecked: **UNVERIFIED**.

**Possibility winners (parameter RSI).** Writer `consciousness_loop.py:1370-1434` (50 trials/space;
persist winners); fitness = analytic distance-from-defaults (`possibility_explorer.py:375-425`,
e.g. emergence `1-|t-5|/10`). Loader overrides declared ratios: `guna_balance.py:48-80`
(`TARGET_RATIOS = winners`), `coherence.py:64`. Persisted file (2026-08-02): `sattvic 0.169 /
rajasic 0.327 / tamasic 0.518` plus arbitrary-precision weights — a self-scored optimizer rewriting
boot-time constants, with no outcome verification attached.

**Identity proposals (adjacent).** `state/identity/proposals.jsonl`: 103 proposals (95 open, 8
rejected), **103/103 `execution_tool: null`** — none applied; identities are benchmark fixtures.

## Selection history

- E20 (`PHASE3_DECOMPOSITION.md:175,200-203`): PRESERVE IMPL → link; canvas "`think` over journal;
  operate on evidence, never self-certify"; matrix: 12 RSI tools, resolution verification with
  regression detection. E18 (`:173,218-221`): self-model folded; Gen2's stores stay live (link),
  calibrate only over resolved claims.
- `LINEAGE_LEDGER.md:52` (verified batch 2): "partial-by-transformation" — Gen2/v5 carries the loop
  distributed (Harmony Vector, drive gates, autonomic salience) plus "**the outward spiral
  (friction → `improve.proposals` → resolution verification with regression detection)** +
  OATS/conformal self-calibration. **Not ported: the explicit pattern-correlation matrix**"
  (candidate V8 analytics, "not owed for alpha"). Inherited = spiral shape + resolution verification
  + regression detection; added (declared) = OATS/conformal; dropped = correlation matrix. Whether
  Gen2's verification names an independent witness or re-runs its own detector: **UNVERIFIED**
  (wave-2 Gen2-source-map item; not deep-dived per assignment). Gen1 has **no `friction` module**:
  "friction" is Gen2 vocabulary; `improve` in Gen1 = the 2 rows above; `redteam` = separate lineage.

## Candidate Gen3 expression / manifest notes

- **RSI-over-journal (no verdict change).** Ancestor = `verify_outcome` + `kaizen_engine` +
  confidence updates. Wire = journal-observable issue series + verdicts, success declared only via
  a witness independent of the proposing organ. Acceptance = battery below; owner unset.
- **Self-model/inspect (no verdict change).** Ancestor = `self_model.py` + winners file; wire =
  per-metric series in journal + calibration only over resolved claims; resumed optimizer targets
  must carry provenance. Owner unset. Homeostatic graduation is the cleanest candidate primitive
  here; its actions were never durably logged in v26.

## Adversarial cases

1. **Disappearance ≠ success** (`recursive_loop.py:1652-1662`): detector retirement is not
   remediation; must not survive as a success rule. **Same-organ verification**: proposer/verifier
   share `analyze()`; a frozen spec needs an independent instrument before any success outcome.
2. **Unstable pattern identity**: cluster ids shift (`0.0_-0.1` vs `-0.0_-0.1`); cross-cycle counts
   compare different objects — identity must be stable or outcomes are noise. **Threshold motion as
   "fix"**: count checks can "succeed" by moving the detector (cf. the wave-1 abstention erratum).
3. **Optimizer overwrites constants**: distance-from-defaults fitness wrote `tamasic_target 0.518`
   into a boot-time override (`guna_balance.py:48-80`); successors must journal provenance and
   never silently replace declared values.

## Ablation ideas

- **Disable auto-verification only** → recorded outcomes drop to 0; the 2 count-drop wins stay
  observable (they were count changes, not records): the signal is 100 % self-reported.
  **Cross-instrument verification** (independent checker) is the minimal fair trial for E20;
  expect the 34 failures to split.
- **Disable the loop on a known-defect corpus** → no retrieval/ordering change expected (it never
  wrote memory through this path): gate, not scorer. **Delete `possibility_winners.json`** →
  declared guna/coherence defaults return; if nothing measurable changes, the optimizer was
  decoration.

## Open questions

- Who/what applied the `untitled` 155→72 fix? Did homeostatic CORRECT/INTERVENE ever fire (no
  persisted actions, log all READ)? **UNVERIFIED.**
- Was `SelfModel` ever fed ≥3 points live, and did the router tier-upgrade ever fire? **UNVERIFIED.**
- `predicted_impact`/`novelty_score` on 906 applications, 36 resolved: any calibration statistic
  ever computed, or display only? `~/.whitemagic/learning/` nonempty (vs `LINEAGE_LEDGER.md:189`)?
  **UNVERIFIED.**
- Gen2 side: does the outward spiral's "resolution verification with regression detection" name an
  independent witness? **UNVERIFIED.**

**Errata candidate (ratified texts unchanged).** The ledger phrasing "906 applications → 36
outcomes → 29 correlations, predicted_impact + novelty_score per pattern" is accurate but reads as
a healthy loop; the coal-face ratios are coverage 4.0 %, success 2/36 (one event), correlations
1/29 nonzero, zero executed auto-fixes — annotate the ledger/tree row with these; no verdict or
ancestry change (both rows stay PRESERVE IMPL → link).
