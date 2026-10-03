# Phase 3 — Capability Decomposition (working ledger)

**Status:** Phase-3 ledger · 2026-09-17 · **§2.1–§2.4 verdicts effective** (entry decision
ratified: `receipts/PHASE3_ENTRY_DECISION_2026-09-17.md`; compile pass ratified:
`receipts/PHASE3_COMPILE_PASS_2026-09-17.md`). Every non-trivial verdict cites evidence (E1–E24)
or a lineage ruling; no row remains `pending`; nothing retires without a citation. The pass
method is `PHASE3_COMPILE_PASS.md`; the reading lens is `PHYLOGENETIC_FRAMING.md` (framing
only — assigns nothing).
This file folds the verified archaeology (`CODE_ARCHAEOLOGY.md`), the Gen1↔Gen2 matrix
(`~/Desktop/WHITEMAGIC_GEN1_VS_GEN2_CAPABILITY_MATRIX_2026-09-16.md`), the LINEAGE_LEDGER, and a
live route inventory (generated from the pinned 9.1.7 binary: `wm contract --json` → 302 routes,
70 declared) into the Phase-3 question: *which Gen1/Gen2 capabilities compile into the minimal
substrate, which are preserved implementations, which retire, and which were never fairly tried?*

Verdict vocabulary (CONV §3 L4174–4182): **COMPOSES CLEANLY** · **COMPOSES AWKWARDLY** ·
**IRREDUCIBLE** · **PRESERVE IMPLEMENTATION** · **RETIRE** · **EXPERIMENT**.
Entry gate: **no verdict may be assigned before Phase 2 passes** — the gate's interpretation is
the subject of `PHASE3_ENTRY_DECISION.md`: Phase 2 closed LOSS; the literal "Phase 2 passes"
gate was **not** satisfied and is superseded, by operator ratification (2026-09-17), by
completion of the full Phase-2 program and disposition of its successor claims. Verdicts below
are effective (entry decision + compile-pass ratification receipts); each EXPERIMENT row carries
its manifest status, with unset owners disclosed.

---

## 1. Method

1. **Family inventory:** group the 302 generated routes by prefix (done; counts below are
   generated, not authored).
2. **Ancestry:** attach Gen1 origin status from the LINEAGE_LEDGER/matrix (folded/partial/
   missing/obsolete).
3. **Expression hypothesis:** for each family, the *cheapest substrate hypothesis* — which
   Phase-1 primitives (records, relations, selection, lifecycle, statutes, journal) could
   express it — and whether it looks like **behavior under test** (must stay out of the A/B),
   **infrastructure** (allowed), or **cognition** (Phase 3 only).
4. **Verdict:** left `pending` until Phase 2 evidence exists. Where a family is obviously
   outside cognition (crypto, sandboxing), `preserve` is flagged as a *hypothesis*, not a
   verdict.

## 2. Decomposition table

Route counts generated 2026-09-16 from `wm 9.1.7` (`contract` manifest; declared = has an
input schema). Gen1 ancestry from the matrix/lineage (cited in those docs).

### 2.1 Memory core & retrieval

| Family | Gen2 surface (routes; declared) | Gen1 ancestry | Substrate expression hypothesis | A/B stance | Verdict (draft) |
|---|---|---|---|---|---|
| Durable store | `memory.*` write/read core (34; 34) | SQLite galaxies + FTS5 → folded | Infrastructure: LMDB stays infrastructure; not under test | allowed infra | **CLEANLY** → compile · E1 |
| Retrieval & ranking | `memory.search`/`episodic_search`/`hybrid_recall` | FTS/HNSW/modes → folded | `recall` op; ranking policy is **behavior under test** — no Gen2 planners imported | **excluded** | **CLEANLY** → compile · E2, E3 |
| Evidence disclosure | evidence bundles, abstention | none (Gen2 added) — **errata 2026-09-17:** v26 `abstention_gate.py` existed (threshold-based) → transformed; see E4 | record provenance + selection explanations + journal; natural fit | outside A/B | **CLEANLY** → compile · E4 |
| Revisions/supersession | `memory.revisions`, validity states | revisions existed | `supersedes` relation + provenance chain + current-preferred ranking | **in A/B (A1/A4)** | **CLEANLY** → compile · E2, E3 † |
| Retention/lifecycle | `retention`, cold rotation | 5-signal retention → folded | lifecycle + statutory selection; import fixed `persistent` in Phase 1 | partially | **PRESERVE IMPL.** → link · E5 |
| Associations | `memory.associate`, `association`, `graph` (3+1) | typed links + Hebbian → folded | `e=(w,s,c,t)` relations; Hebbian dynamics → promotion policy candidate | Phase 3 | **CLEANLY** → compile (edges) · E6 ‡ |
| Constellations/emergence | `constellation` (2), `emergence` (2) | v26 **zombie** → folded-with-replacement | Phase 3: topology over relations; H8 candidate (never re-adopt v26 simulation) | Phase 3 | **EXPERIMENT** (manifest required) · E7 § |
| Galaxies/registry | `galaxy.*` (14) | 14-galaxy taxonomy → distilled | scope labels / views, not storage machinery (canon §3.6) | excluded | **CLEANLY** → compile · E8 |
| Ingestion gates | `memory.*` write path, ingest | v26 ingestion → folded | `remember` contract; typology/dedup gates are **behavior under test** — excluded | **excluded** | **CLEANLY** → compile · E9 |
| Compartments | mandala, `galaxy` access | v26 compartments → folded | statutes + scopes | infra | **PRESERVE IMPL.** → link · E10 |

**Verdict evidence keys (draft).**

- **E1 — Phase-1 substrate receipts:** `receipts/PHASE1_SUBSTRATE_FIRST_SLICE_2026-09-16.md`,
  `receipts/PHASE1_CLOSURES_GREEN_2026-09-16.md` — records + provenance + JSONL journal are the
  shipped first slice; both closures machine-tested green before adaptive cognition. (Routes in
  the 34-route family beyond the write/read core are covered by rows 3–9.)
- **E2 — Earned tier:** `ARCHITECTURE_CONSOLIDATION.md` §1 (R positive on all five corpora),
  §5 (layered architecture), §2 (state resolution vs recall: TBII c11 54/60 adjudicated vs
  control 34/60).
- **E3 — Successor + Testbed II record:** `receipts/PHASE2B_RESULTS_2026-09-16.md` (projection
  rejected), `PHASE2C…` (interaction falsified), `PHASE2D…` (ordering WEAK), `PHASE2E…`
  (dispersion falsified); `experiments/testbed_ii/a/REPORT_A.md`,
  `experiments/testbed_ii/gated/REPORT_GATED.md`, `gated2/REPORT_GATED2.md`,
  `gated3/REPORT_GATED3.md` (count gate confirmed gate-scoped; O₁ 10/10; ≥2 boundary missed and
  parked).
- **E4 — Disclosure machinery:** `PHASE2_RUN_JOURNAL.md` §2 (`selection.decision` with
  `abstained`, `provenance.chain` completeness, `remember.refusal`, `boundary.refusal`) +
  consolidation §1 H4/H6 standing (100 % provenance, zero violations on every run) + audit
  protocol 20/20 + 40/40 across corpora. **Errata (2026-09-17):** the ancestry cell read
  "none (Gen2 added)"; `docs/PHASE4_WAVE1_FINDINGS.md` documents v26
  `core/memory/abstention_gate.py` ("Gap D"; default threshold 0.50, sweep-derived) — Gen2
  **transformed** threshold abstention into declared floors + explicit `insufficient_evidence`.
  Verdict unchanged; the "no swept thresholds" adversarial case is recorded in the findings.
- **E5 — Retention/lifecycle:** `DESIGN_CANON.md` §14 (cold rotation / retention /
  backup-restore = IMPL-G2), `LINEAGE_LEDGER.md` (5-signal retention folded; Gen2
  implementation real), `PHASE3_COMPILE_PASS.md` §4 (link/preserve illustration) — Phase 1 keeps
  the fixed `persistent` tier, so the substrate has not earned a replacement.
- **E6 — Associations:** precondition §3.1 (relations first-class) + `THEORY_MECHANISM_MAP.md`
  §3.2 (Hebbian associations PARTIAL; promotion-policy candidate, no evidence yet).
- **E7 — Emergence lineage:** `LINEAGE_LEDGER.md` emergence ruling (v26 hardcoded patterns +
  `random.uniform` novelty; 284 runs / 0 output; folded-with-replacement) + the six-condition
  test (`experiments/contradiction/PRE_REGISTRATION.md` §6) + the §4 manifest rule below.
- **E8 — Galaxies:** `DESIGN_CANON.md` §3.6 (emergent manifolds, membership weights; Gen2 fixed
  enum + physical DBIs = PARTIAL-G2) + the compile expression itself (scope labels / views).
- **E9 — Ingestion gates:** Phase-1 `remember` contract receipts + journal `remember.refusal`
  events + the A/B exclusion of Gen2 typology/dedup behavior (stance column).
- **E10 — Compartments:** `LINEAGE_LEDGER.md` economy ruling (access pricing → mandala
  compartments as the shipped non-monetary descendant) + `PHASE3_COMPILE_PASS.md` §4
  ("governance is statute + journal, not cognition") — enforcement machinery stays Gen2-side
  for alpha; the substrate's expression target is scopes + statutes.

**Row notes (draft).**

- **† Revisions/supersession** — deliberate deviation from the `PHASE3_COMPILE_PASS.md` §4
  illustration ("likely link/preserve" for revision-verify): the capability *compiled natively*
  in Phase 1 and won the A/B (R is the one cross-ecology survivor), so **no Gen2 implementation
  is required to preserve the demonstrated capability**. The verdict attaches to
  supersession/currentness semantics only — capability compiled ≠ historical API surface
  reproduced — not to every Gen2 revision feature. Approved in review, 2026-09-17.
- **‡ Associations** — the verdict covers **typed association edges only**; the
  Hebbian-dynamics half is `pending` and can only re-enter through the §4 manifest rule
  (ancestor: Gen1 NeuralMemory; wire: promotion policy; acceptance/owner unset).
- **§ Constellations/emergence** — verdict `EXPERIMENT`, execution gated by the manifest rule
  (ancestor: v26 emergence; wire: topology over relations; acceptance: H8 six-condition test vs
  ablation; owner unset). Never re-adopt the v26 simulation (canon §13).

### 2.2 Sessions, coordination, identity

| Family | Gen2 surface (routes; declared) | Gen1 ancestry | Substrate expression hypothesis | A/B stance | Verdict (draft) |
|---|---|---|---|---|---|
| Session records/lifecycle | `session.*` (13; 13) | 21,351 turns recorder → folded | records + relations; session module explicitly out of Phase 1 | excluded | **PRESERVE IMPL.** → link · E11 |
| Continuity/digest | `session.continuity`, digest | cross-session recall → folded | `recall` over session records; digest = `think` synthesis | Phase 3 | **CLEANLY** → compile · E11, E1 ¶ |
| Coordination | `code.*` (7; 4), `workspace` (4) | informal tracks → added | statutes + journal; not cognition | infra | **PRESERVE IMPL.** → link · E12 |
| Identity/lineage | `smarana` (2), `hermit` (4) | practice not ported; hermit gap | identity is provenance duty (docs), not a module | deferred | **RETIRE** (practice forms) → docs+lineage · E13 †† |
| Memetic lineage / Geneseed | `geneseed` routes exist (2; 0 declared) | concept only → missing | Phase 4 (scaffold §8): typed parent edges, selection events | deferred | **EXPERIMENT** (Phase-4 gated; manifest required) · E14 §§ |

**Verdict evidence keys — §2.2 (draft).**

- **E11 — Sessions:** matrix §2.4 (`SessionRecorder` chronological turns + FTS; Gen1 sessions
  galaxy 21,351 turns → Gen2 `session.*` lifecycle **FOLDED & hardened**, `session_ops.rs`
  3,047 LOC; wmv9 store 119 sessions / 1,054 turns; continuity **FOLDED**) +
  `PHASE1_CONTRACTS.md` ("no session module" — Phase-1 exclusion) + `PHASE2_RUN_JOURNAL.md`
  (`run.start`/`run.end` session-shaped events already in the journal schema).
- **E12 — Coordination:** matrix §2.4 multi-session coordination (`code.claim` leases with
  intent+TTL, conflict naming; two-writer live-fire passed; **ADDED**) + `LINEAGE_LEDGER.md`
  watch item 3 (`code.claim` v0 `89603db`; F-1 mesh scope bridge `0ae8d4a`; lease ledger at the
  git common dir) + economy ruling (task delegation → `code.claim`/sangha coordination).
- **E13 — Identity:** matrix §2.9 (identity **DISTILLED as documentation duty**:
  `HOMECOMING_PROTOCOL.md`, `docs/lineage/`, session identity + `self_model.json`; no persona
  layer) + §2.8 smarana (**PARTIAL — name collision**: v5 `Smarana` struct is a retention
  tracker; the practice was deliberately never ported) + `LINEAGE_LEDGER.md` smarana row
  (homecoming-gated) + batch-3 hermit note ("deliberate gap, not owed for alpha"; RO stores +
  WIP containment are the product-side analogues).
- **E14 — Geneseed:** `SCAFFOLD_STRATEGY.md` §8 (deferred by decree; Phase 4 candidates only
  after selection is demonstrated; inheritance is downstream of selection) + `LINEAGE_LEDGER.md`
  digital-genetics row (**missing**; V9.1 typed parent edges, n-parent forks, selection events)
  + matrix §2.9 (**MISSING, planned**).

**Row notes — §2.2 (draft).**

- **¶ Sessions split (deliberate):** the *storage/lifecycle* layer is preserved (the live,
  hardened implementation; replacement unearned because Phase 1 excluded it), while
  *continuity/digest* compiles as `recall` + `think` over that record layer — no new primitive;
  Gen2's `session.continuity` remains the live path until the substrate earns replacement. Data
  layer = `link`; operations = `compile` target.
- **†† Identity:** `RETIRE` applies to the **runtime practice forms** only (smarana practice —
  private lineage, homecoming-gated; hermit mode — deliberate gap). Identity-as-provenance duty
  is **already carried** by the §2.1 provenance/journal rows and Gen2's documentation-duty
  layer; no separate identity module is owed. Revisit gates: `HOMECOMING_PROTOCOL` (smarana),
  product-side analogues for hermit.
- **§§ Geneseed:** `EXPERIMENT` with the Phase-4 gate explicit — the manifest rule
  (ancestor · wire · acceptance · owner) cannot be completed before a selection loop is
  demonstrated (scaffold §8); ancestor: v2-era memetic-lineage design; wire: typed parent edges
  + selection events on relations; acceptance/owner unset. Execution only after that gate.

### 2.3 Cognition & epistemics

| Family | Gen2 surface (routes; declared) | Gen1 ancestry | Substrate expression hypothesis | A/B stance | Verdict (draft) |
|---|---|---|---|---|---|
| Citta/cycles | `citta` (4), `dream` (3) | citta/dreams → folded | field dynamics + temperature regimes (canon §4); dream = consolidated selection pass | Phase 3 | **AWKWARDLY** → compile · E15 |
| Engines/recipes | `kaizen`, `serendipity`, `apotheosis` (1 each), `skill` (2) | 28 engines → 5 executable | Phase 3: recipes over operators (canon §7); SkillForge is metadata-only today | Phase 3 | **AWKWARDLY** → compile · E16 |
| Gan Ying/resonance | `bus` (3), resonance events | Gan Ying bus → folded | internal coupling; transport deferred (iceoryx2 is not new — Gen1 had it) | Phase 3 | **PRESERVE IMPL.** → link · E17 |
| Claims/prescience | `claims.*` (6; 4) | prescience → folded | **belief class** + calibration; close cousin of the epistemic triple | Phase 3 | **CLEANLY** → compile · E18 |
| Self-model/conformal | `selfmodel` (4), `conformal` (8) | feedback.db → folded | `inspect` + confidence calibration | excluded | **PRESERVE IMPL.** → link · E18 |
| Simulation/imagination | `sim` (3), `imagine` (3), `speculative` (2) | TZPF/superforecaster → folded | Phase 3+; simulation ≠ evidence is already law | deferred | **EXPERIMENT** (manifest required; epistemic half already law) · E19 |
| RSI/friction | `friction` (4), `improve` (2), `redteam` (3) | kaizen loop → folded | `think` over journal; operate on evidence, never self-certify | Phase 3 | **PRESERVE IMPL.** → link · E20 |
| Reflex/sensor/actuator | `reflex` (5), `sensor` (4), `actuator` (3) | none (Gen2 added) | MandalaOS boundary; hard real-time stays outside (CONV §2 L2627) | deferred | **PRESERVE IMPL.** → link · E21 |

**Verdict evidence keys — §2.3 (draft).**

- **E15 — Citta/cycles:** matrix (12-phase dream cycle **FOLDED**, `DreamPhase`;
  `LearnedDreamCycle` reorders by effectiveness) + canon §4 (field DESIGN; temperature as
  regime selector; map §4 real-math notes) + `THEORY_MECHANISM_MAP.md` §3.3 (field dynamics
  **PARTIAL-G2 / DEFERRED** in WMgen3; the move is *"a task where propagation beats retrieval —
  none demonstrated"*) + Phase-1/2 sweep machinery (`think.sweep` journal).
- **E16 — Engines/recipes:** canon §7 (Engine = compiled DAG/recipe over general operators;
  historical engines become recipes; SkillForge is metadata-only; anti-bloat law) +
  `THEORY_MECHANISM_MAP.md` §3.3 (recall compiler / verbs-as-ISA **UNTESTED**) + matrix
  (28 slots absorbed 44 + 5 = 77 named concepts → 5 executable).
- **E17 — Gan Ying:** canon §8 (Gan Ying = semantic nervous system; transport is an
  abstraction; iceoryx2 is a re-adoption decision, not a new idea) + matrix (resonance
  FOLDED; 234 event types / 10 categories) + `receipts/PHASE0_CLOSE_ADDENDUM_2026-09-16.md` §4.4
  (any transport adoption gets its own manifest receipt).
- **E18 — Epistemics (claims, self-model):** canon §3.1–3.2 (evidence/belief/speculation
  separation; `x = (content, class, …)`) + matrix claims discipline (dated falsifiable claims,
  Brier 0.078, underconfident −0.215 recorded honestly) + Charter §5 `inspect` obligations +
  today's ledger state (8 claims; `claim-0007` the only validated one).
- **E19 — Simulation:** canon §10 (`simulation ≠ evidence`; simulated priors ground only
  through external outcomes) + Charter §3.8 / Closure 2 + matrix (imagination surfaces
  EXP-labeled; live model-update paths not production-verified).
- **E20 — RSI/friction:** `LINEAGE_LEDGER.md` feedback-controller row (outward spiral IS the
  kaizen loop's descendant; pattern-correlation matrix not ported) + matrix (12 RSI tools,
  resolution verification with regression detection) + canon §5 (operate on evidence; never
  self-certify).
- **E21 — Reflex/sensor/actuator:** CONV §2 L2627 (hard real-time stays outside the cognitive
  substrate; MandalaOS boundary) + matrix (Gen2-added; no Gen1 ancestry).

**Row notes — §2.3 (draft).**

- **Citta field (missing-primitive candidate, not a feature):** the dream/consolidation half
  compiles now (selection + lifecycle sweep, already instrumented); the field-dynamics half
  does not — candidate primitive: activation/decay field with an operationally defined regime
  parameter (map §4). Entry gate: a task where propagation beats retrieval. No temperature
  parameter in any runtime until then (symbols-never-dispatch risk boundary).
- **Recipe layer (missing-primitive candidate):** a small operator vocabulary + recipe runtime
  is what stands between AWKWARDLY and CLEANLY; the anti-bloat law attaches to every candidate
  (behavior must be a profile, operator, or composition before any class). SkillForge metadata
  is not evidence.
- **Claims/self-model split:** the belief-class half compiles (class + provenance + resolution
  records; calibration is a statutory statistic over resolved claims — this very ledger is the
  working prototype); Gen2's claims tool and self-model/conformal stores remain the live product
  surfaces (`link`) until the substrate earns them.
- **Simulation:** the epistemic half (inference cannot create world evidence; simulations stay
  `simulated`) is already law and enforced (Closure 2 canaries); only the rollout/imagination
  machinery is unearned. Manifest status: ancestor = Gen1 TZPF/superforecaster + Gen2
  imagination surfaces; wire = `simulated`-domain records + hypothesis records + a rollout pass
  over admitted evidence; acceptance = domain-tagging canaries (already law) **plus** a task
  where simulation improves a measured outcome vs ablation; owner unset.

### 2.4 Governance, security, distribution

| Family | Gen2 surface (routes; declared) | Gen1 ancestry | Substrate expression hypothesis | A/B stance | Verdict (draft) |
|---|---|---|---|---|---|
| Effects/capability gate | `pipeline` (3), `security` (7) | EffectSignature → enforced | constitutional shell / statutes (infrastructure) | infra | **CLEANLY** → compile · E22 |
| Firebreak/bulk-scope | firebreak | design-only in Gen1 | statutes; preserve the seam (`firebreak.rs`) | infra | **PRESERVE IMPL.** → link · E22 |
| Dharma/karma | `dharma` (8), `karma` (5) | dharma 1,338 LOC → folded | statutes; karma ledger ≈ **contribution/credit records** (canon credit ladder) | infra | **PRESERVE IMPL.** → link · E22 |
| Resource/homeostasis | `homeostasis` (4), `harmony` (2) | Harmony Vector → folded | statutory budgets; homeostasis bounds selection | infra/statute | **PRESERVE IMPL.** → link · E22 |
| Sandbox/confinement | `sandbox` (2), Landlock | none → added | infrastructure; not cognition | infra | **PRESERVE IMPL.** → link · E22 |
| Canaries/deception | `canary_tokens` (unwired in Gen2) | tokens existed | closure canaries (Phase 1 already live for closures) | infra | **CLEANLY** → compile · E22 |
| Mesh/agents | `sangha` (12), `agent` (8), `network` (3), `mc` (5) | mesh aux → distilled | `communicate` verb later; two-gate boundary (metabolism plan) | deferred | **EXPERIMENT** (deferred; manifest required) · E23 |
| Ops/telemetry | `telemetry` (4; 4), `tools` (4) | trackers → folded | distribution infra; metabolism reads telemetry as `system` domain | infra | **PRESERVE IMPL.** → link · E22 |
| Economy remnant | `bounty` (8; 0 declared) | v26 economy → **obsolete-by-design** | verify shipped-vs-dormant before any verdict; retire-bias | out of scope | **RETIRE** (monetary economy) → docs+lineage · E24 |
| Symbolic families | `bagua` (1), `council` (1), `god` (1), `violet` (3), `drive` (2) | v26 symbolic sprawl; i_ching never-by-design | render-only (Charter §3.10); retirement candidates unless a real function is shown | out of scope | **split** — misfiled: `violet`/`drive`/`god` = **PRESERVE IMPL.**→link; `bagua`/`council` = **RETIRE** → docs+lineage · E24 |

**Verdict evidence keys — §2.4 (draft).**

- **E22 — Governance stack:** `receipts/PHASE1_CLOSURES_GREEN_2026-09-16.md` (closures 1/2
  machine-tested, canaries live) + matrix (EffectRow typed effects FOLDED & hardened; Firebreak
  armed by default — 31 forbidden / 13 dangerous / 8 caution patterns; DharmaGate
  Observe/Advise/Correct/Intervene/Panic; Landlock v0+v1 **ADDED**, ABI v8 enforced; telemetry
  local-only, egress-frugal) + `LINEAGE_LEDGER.md` (zodiac ledger → karma ledger folded;
  Landlock v0 Phase-5 row) + `PHASE3_COMPILE_PASS.md` §4 (governance = statute + journal;
  preserve the seam).
- **E23 — Mesh/agents:** canon §8 (two-gate boundary: transport validation → semantic/authority
  validation; membrane stays logically enforceable) + `METABOLISM_PLAN.md` (external coupling;
  stranger lane) + matrix (sangha DISTILLED + evidenced; quarantine rules).
- **E24 — Shipped-vs-dormant + symbolic audit (2026-09-17, pinned 9.1.7 contract + source):**
  every family in these two rows is **shipped** in the 302-route manifest (not dormant). The
  audit corrected three misfilings and confirmed two symbolic ones:
  - `bounty.*` = **submission/outcome ledger** (`bounty_ledger.rs`: JSONL ledger of submissions
    + rejection-reason taxonomy; *not* the XRP economy) → preserved as the non-monetary descendant.
  - `violet.*` = **engagement tokens + model signing** (`violet.rs`, `capability_gate.rs`:
    Ed25519 issue/validate/revoke, scope-derived capability coverage, `_engagement` credential
    verification at dispatch) — this **closes the v5-era scope-token gap**; a real security
    capability, not symbolic sprawl.
  - `drive.*` = autonomic **DriveState** energy/caution machinery (`wm-cognitive/drive/`); real.
  - `god.nodes` = **graph hub-entity analytics** (`correlation.rs`), not symbolic.
  - `bagua.dispatch` = literal trigram→tool **symbolic router** (`bagua.rs`: "☰ Qian → Captain
    Alchemist", "Grounding in I Ching cosmology") — a runtime branch justified by symbolism
    (Charter §3.10).
  - `council.deliberate` = archetypal deliberation harness (`zodiac_council.rs`); the v5
    lineage ruling already made the zodiac council obsolete-by-design ("nothing load-bearing").

**Row notes — §2.4 (draft).**

- **Economy:** the ruling retires the **monetary** family (XRP rails; all persisted artifacts
  were test/bench data) with its revisit condition; the shipped `bounty.*` ledger is the
  non-monetary submission/outcome surface and is preserved (`link`), not retired — the
  shipped-vs-dormant check the row demanded is satisfied (E24).
- **Symbolic:** `bagua` retires as the only literal symbolic **dispatch** found in the 302-route
  audit (Charter §3.10: symbols may render, never dispatch; the i_ching/bagua family is
  never-by-design per the lineage ruling); `council` retires per the lineage ruling — if
  multi-perspective deliberation is ever wanted, it re-enters as declared conditions/poses
  (canon §7), not as an archetype module. `violet`/`drive`/`god` are **mislabeled rows, not
  symbolic families**: they stay as preserved Gen2 capability (`violet` = security, `drive` =
  autonomic, `god` = analytics).
- **Mesh manifest status:** ancestor = Gen1 mesh/Go auxiliary + Gen2 sangha; wire =
  `communicate` verb over signed identity with the two-gate boundary (transport validation →
  semantic/authority validation); acceptance = boundary refusals logged + egress proof + a
  demonstrated multi-agent task; owner unset. Execution deferred by the metabolism plan's two
  gates.

## 3. Phase-1 reimplementation notes (what the minimal substrate must be able to express later)

These are inputs to the implementation session — not new requirements; all are already in
`PHASE1_CONTRACTS.md`:

1. **Relations must be first-class** (kind, endpoints, `(w,s,c,t)`, class, provenance) before any
   Phase-3 family can compile — constellations, recipes, karma-as-credit, lineage edges all
   reduce to typed relations plus selection.
2. **Provenance chains at result granularity** are the common denominator for evidence
   disclosure, claims, retention, and H4 — no family needs its own provenance mechanism.
3. **Selection explanations** (population → rule → choice) subsume the families Gen2 spread
   across scoring knobs (`source_trust`, `WM_TRUST_WEIGHT`, conformal sets) — those become
   policy parameters, not modules.
4. **Lifecycle on inferred structure** is the precondition for retention, cold rotation,
   emergence, and Geneseed; keep it exercising on relations in Phase 1 so it is real before
   Phase 3 needs it.
5. **Statutes must be inspectable and versioned** — the governance family (dharma/karma/yama/
   firebreak) collapses into statute + journal if the tier system is honest.
6. **Journal-as-evidence**: every Phase-3 candidate that claims improvement must be ablatable and
   measurable through the same journal schema (A-ledger precedent).

## 4. Candidate re-entry list (from matrix §5; fair-trial rule applies)

- Memetic lineage / Geneseed (missing; Phase 4 by scaffold decree).
- External-validation sourcing for claims (partial).
- Per-tool EffectRow profiles (open in Gen2).
- Emotional valence in retrieval (schema exists; retrieval never reads it).
- Story/narrative layer (post-Gate-2; render-only until then).
Each would need the manifest rule: ancestor · wire · acceptance · owner, and a receipt.

## 5. What this document is not

Not a plan of record, not a schedule, not permission to build. The Phase-2 **program**
determines what, if anything, earns entry into the compile pass: Phase 2 closed **LOSS** on the
original substrate claim, and the successor evidence defines the narrow earned tier from which
verdicts may now be assigned under the ratified entry decision. Counts above are generated
(`wm contract --json`, 2026-09-16); any future revision must regenerate rather than edit numbers
by hand.

## 6. Errata register (2026-09-17)

Wave-1/2 source extraction raised corrections that touch ancestry/evidence lines **without
changing any verdict**. Consolidated and dispositioned in `docs/PHASE4_ERRATA.md`; the entries
that touch this table:

- **E4 / disclosure row:** v26 `abstention_gate.py` existed (threshold-based) — inline errata
  above.
- **E6 / associations row:** v26 typing never survived a save (kind/direction reverted);
  Hebbian was dormant in v26 and is live in Gen2's *mechanism* (not in the serving path). The
  "edges compile, Hebbian parked" verdict is **strengthened**, not changed.
- **E8 / galaxies row:** the 14-galaxy taxonomy was **advisory-only** (never called by the
  write path); the 47-galaxy sprawl is **narrative-only** (mechanism plausible, no source
  attestation). Verdict unchanged.
- **E15 / citta row:** Gen1 `DreamPhase` has **13** members vs Gen2's 12; `LearnedDreamCycle`
  reordering is Gen2-only; the "CITTA 18,204" headline is a storage-label artifact (real
  taxonomy = `turn_type`).
- **E16 / engines row:** v26's SkillForge **ran and persisted 33 skills** over a 4-verb
  vocabulary (write-only replay) — "SkillForge is metadata-only" holds for Gen2. The
  operator-level runtime is absent in both; the missing-primitive candidate stands.
- **E5 / retention row:** the v26 sweep was never auto-armed and its persist path was broken on
  the shipped backend; association edges were hard-deleted (rotation-not-deletion was not
  uniform). The PRESERVE→link verdict is strengthened.
