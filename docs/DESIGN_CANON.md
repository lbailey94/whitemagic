# WMgen3 — Gen3 Design Canon (working record)

**Status:** design record · 2026-09-16 (annotated 2026-09-19) · **not binding** — `docs/CHARTER.md` binds; this file remembers.
Status tags below are design-time snapshots; the implemented/earned state lives in `docs/NUCLEUS.md`
and `docs/archive/research/PHASE3_DECOMPOSITION.md`, and PEB-era evidence in `receipts/BENCHMARK_*.md`.
Written after a three-pass read of `~/Desktop/dev journal/WHITEMAGIC CHATGPT CONVERSATIONS.txt`
(§2 L1741–3420 design sessions; §3 L3422–4271 expedition + strategy) cross-checked against the
verified code survey in `docs/archive/research/CODE_ARCHAEOLOGY.md`. Status labels and per-frame dispositions now
have a home in `docs/THEORY_MECHANISM_MAP.md` (2026-09-17).

Purpose: keep the converged Gen2→Gen3 design vocabulary, mark what is **actually implemented**
versus **intended** versus **deferred**, and prevent re-litigation. This is explicitly *not* a
fourth thesis (§3 L3969: "We now have enough philosophy. The next artifact should therefore not
be another broad thesis document"). Nothing here changes the Phase-0 freeze or the experimental
era's standing rule: **let Gen3 lose if it loses** (§3 L4162–4164).

Status legend:

| Tag | Meaning |
|---|---|
| **IMPL-G2** | exists in frozen Gen2 v9.1.7 today (evidence in `archive/research/CODE_ARCHAEOLOGY.md`) |
| **PARTIAL-G2** | Gen2 has a related mechanism, but not the concept as described |
| **DESIGN** | converged intent; not built; enters only through Phases 1–3 gates |
| **DEFERRED** | deliberately out of scope until Phase 2 passes (`archive/legacy/SCAFFOLD_STRATEGY.md` §8) |
| **CAND-LAW** | candidate Charter amendment; requires the CHARTER §4 procedure |

---

## 1. Generational arc (the frame everything else hangs on)

> Gen1: differentiation without sufficient selection or constraint.
> Gen2: strong constraint and human-curated selection over mostly predetermined structures.
> Gen3: plastic structure under mechanized selection inside constitutional constraint.
> — §3 L4016–4018

Corrections the archaeology forced onto the narrative (see `archive/research/CODE_ARCHAEOLOGY.md` §17):
Gen1's counts drift (e.g. "875 dispatch entries" vs 851/879 measured); Gen1's "emergence"
was partly simulated (5 hardcoded detectors + `random.uniform` novelty); the
number-drift problem itself is the historical lesson, not a footnote.

## 2. Four plastic layers inside one constitutional shell

| Layer | Purpose | Phase-1 form | Status |
|---|---|---|---|
| Epistemic substrate | evidence / belief / speculation kept distinct | one store, `x=(content, class, source, provenance, confidence, horizon)` | **DESIGN** (Charter §3.9) |
| Dynamic field | activation, relations, propagation, decay | `e=(w,s,c,t)` — weight, sign, cost, trust. Nothing more until an experiment demands it | **DESIGN** (§3 L4098–4102) |
| Selection + lifecycle | what earns resources, persists, cools, dissolves | per-operation selection contracts; exploration budget; delayed credit | **DESIGN** (Charter §6) |
| Compiler surface | stable intent → changing internal organization | verbs **remember · recall · think · inspect** | **DESIGN** (subset of §3 L4083–4087) |

The constitution is **not layer five** — it surrounds all four and is unreachable by plastic
runtime updates (§3 L4024–4032; Charter §2). Two closures anchor it: **Closure 1 — Law** (no
plastic write path reaches constitutional state) and **Closure 2 — Evidence** (inference alone
cannot create world-evidence) — both machine-tested *before* adaptive cognition exists.

## 3. Epistemic substrate

### 3.1 Triple separation — evidence / belief / speculation
- Memory asks "what have I encountered?"; epistemics asks "what do I currently believe, and why?"
  (coolant-example, §2 L2262–2321).
- No three separate databases initially: `MemoryStore` / `EpistemicGraph` / `ThoughtField` are
  conceptual *views of one substrate* (§3 L4112). Status: **PARTIAL-G2** — Gen2 has evidence
  bundles, revision/supersession chains, and a claims ledger, but not a first-class class field.
- Durability ≠ truth: "graduates into persistence, not truth" (Charter §3.9).

### 3.2 Record shape (`x`)
`x = (content, class, source, provenance, confidence, horizon)`; `class ∈ {evidence, belief,
speculation}` (§3 L4104–4110). Evidence objects additionally carry
`domain ∈ {world, system, simulated, reported}` (Charter §3.8, v0.1.1): domains are **immutable**
— no existing record may ever be re-labeled — and world-evidence enters only as **new records**
through a ratified intake channel.

### 3.3 Memory stars and projections
A memory does not have *one* position; it has *many projections* — the computational meaning of
"holographic multidimensional memory" (§2 L1910–1963):

```
MemoryStar { identity; semantic_vector; lexical_signature; episodic_coordinates;
             temporal_coordinates; causal_signature; structural_signature;
             importance; trust; confidence; novelty; emotional_salience;
             current_state; provenance }
```

A query chooses the projection ("a debugging memory may be close semantically but distant
temporally"; §2 L1933–1965). Status: **DESIGN**. Gen2 today has *two* coordinate systems
(5D garden coords, 6D holographic coords) and no generalized projection abstraction — treat the
existing coord systems as projections #1 and #2, not the final geometry (§2 L3279–3320).

### 3.4 Thought stars vs memory stars; stellar lifecycle
- **Thought stars** are ephemeral cognitive artifacts (hypotheses, analogies, counterfactuals,
  questions, predictions); most die; some are promoted: thought → verification → insight →
  provenance → durable memory (§2 L2116–2152). "Thinking is not the same thing as knowing."
- Lifecycle: sensory/event fragments → **thought dust** (µs–s) → **thought stars** (s–min/h) →
  {burn out → nebula/dust} or {stabilize → **memory star** → constellation member → conceptual
  structure → higher-order galaxy} (§2 L2629–2649). Burn-out is compression, not deletion
  (`rotation, not deletion`; §2 L2651).
- Star dynamics map onto real scoring dimensions (§2 L2655–2665): mass = accumulated
  evidential/support weight; brightness = current activation; lifetime = retention expectation;
  velocity = movement through coordinates; gravity = associative attraction; trust = epistemic
  reliability; heat = exploratory instability.
- Status: **DESIGN** (Gen2 has candidate/cold tiers and cold rotation — PARTIAL-G2 as substrate
  mechanics, absent as a unified star model).

### 3.5 Constellations and hyperedges
- A constellation is not merely a cluster; it is a **reusable pattern** ("stale concurrent state
  failure": high concurrency → stale state → inconsistent reads → restart → recovery), promoted
  into a first-class star (§2 L2019–2064, L2677–2687). Status: **PARTIAL-G2** —
  `constellation.detect/list` tools exist (5D clustering); topology comparison exists only as a
  non-shipped example.
- **Hyperedges** for multi-source relations: `(A+B+C) → causes → D`; relations carry strength,
  confidence, source, last_verified, activation_history; relation vocabulary includes supports /
  contradicts / causes / supersedes / analogous_to / derived_from / co_occurs (§2 L2066–2114).
  Status: **DESIGN** (absent in Gen2).
- Higher layers must retain pointers down to evidence: compression without losing provenance
  (§2 L2062–2064).

### 3.6 Galaxies as emergent manifolds, not containers
One memory can belong to many galaxies with weighted membership
(retrieval 0.93 / engineering 0.84 / WhiteMagic 0.99 / …); galaxies acquire centroids, topology,
relations, overlap; Dreaming may propose new conceptual regions (§2 L1969–2017). Status:
**PARTIAL-G2** — galaxies are per-name physical containers (dynamic; taxonomy advisory-only
— `archive/research/findings/W1_galaxies_compartments.md`); membership weights absent.

## 4. Dynamic field & Cognitive Physics

- Minimal Phase-1 edge/field parameter: `e=(w,s,c,t)` = weight, sign/direction, resource cost,
  trust/confidence. "Latency can initially be measured rather than ontologized"; valence,
  reversibility, plasticity coefficients must *earn* entry through failed experiments. Warning on
  record: a giant vector schema can become "Gardens in mathematical clothing" (§3 L4098–4102).
- **Cognitive Physics** as an explicit kernel governing activation, decay, inhibition,
  temperature, resonance, attention, propagation, plasticity, competition, energy/resource budget
  (§2 L2154–2174). Status: **PARTIAL-G2** — activation, Hebbian association decay, graph
  propagation with per-hop decay, and neuro-score decay exist as primitives; the regime concept
  does not. Corrections of record: the declared 300 s half-life **never ticks** (`tick_decay` has
  zero callers — Errata #14), and parts of this machinery are dormant/inert
  (`archive/research/findings/W3_field_activation.md`).
- Temperature as regime selector (§2 L2197–2219): low → precise recall; medium → problem
  solving/analogy; high → creative association/dreaming; constrained + high verification →
  auditing. "Same machinery. Different regime."
- Gardens modify the metric (e.g. Mystery: causal distance ×0.7, novelty reward ×1.8; Truth:
  contradiction cost ×2.0, currentness ×1.7) — same stars, different geometry of attention
  (§2 L3300–3319).
- Homeostasis keeps propagation bounded (Gen2's homeostasis veto + Harmony Vector are PARTIAL-G2
  ancestors).
- Governing design principle: *don't build a subsystem per capability; build few adaptive
  processes whose interactions generate the capabilities* (§2 L2603–2621).

## 5. Selection & lifecycle

- Selection is **cross-cutting metabolism, not a tenth homunculus-tool**; each operation declares
  what it selects over (§3 L4089–4096): `recall` selects retrievable structures; `think` selects
  transformations/relations; `remember` selects what earns persistence and its epistemic status;
  `inspect` explains requested stance, applied policy, resulting choice (Charter §6).
- **Credit assignment** must be stronger than co-occurrence (§3 L3869–3885): contribution record
  `path → structures touched → transformation → outcome → later feedback`; ladder
  `coupling → correlation → traceable participation → causal attribution → selection`; delayed
  credit inside a statutory horizon; uncredited exploration rotates cold. "Not every resonance
  deserves reinforcement." Status: **DESIGN** / **CAND-LAW** if promoted to statute.
- Emergence qualifies only through the pre-declared six-condition test
  (`experiments/contradiction/PRE_REGISTRATION.md` §6): not enumerated, ≥3 seeds, improves a
  measured outcome vs ablation, survives restart, inspectable/causally traceable, within bounds.
- **No new Garden or Engine implementation unless its behavior cannot be expressed as a profile,
  operator, or composition of existing operators** (§2 L3356–3360). Status: **CAND-LAW/STATUTE**.

## 6. Compiler surface (verbs, planner, cognitive ISA)

- Verb count is a Phase-3 question, not a Phase-0 doctrine. Two candidate bases converged:
  7 (`perceive · remember · recall · think · simulate · act · inspect`, §2 L2396–2403) and
  9 (adds `imagine` and `communicate`, §2 L2798–2808). "If seven suffice, use seven… If the
  correct basis is eleven, use eleven. … architecture follows evidence" (§3 L4184–4191).
- Phase 1 implements only **remember · recall · think · inspect** (§3 L4083–4087).
- Underneath, keep the **hundreds of primitives** as an internal cognitive ISA (~100–300),
  invocable by developers/diagnostics, not by normal AI clients (§2 L2515–2550).
- **Recall Compiler / Yoga Planner**: the model expresses intent + stance; WhiteMagic compiles it
  into a retrieval/execution program (lexical/semantic/entity/episodic arms, fallback relaxation,
  early stop on high-confidence agreement) (§2 L2323–2366, L2471–2513).
  "The model doesn't select algorithms. It expresses intent. WhiteMagic selects algorithms."
- Compilation pipeline: intent → semantic IR → cognitive execution plan → parallelize/fuse/
  cancel/reuse/select hardware → execution (§2 L2831–2849). Status: **DESIGN**.

## 7. Gardens and Engines — dissolution without loss

The archaeology study (§2 L2977–3419) concluded:
- Gen1 Gardens were already trying to become fields ("emotional gardens are memory namespaces,
  not processing layers" — `gardens/garden_config.py:3-5`); Gen1's GardenRouter (courage/wisdom/
  play/grief/mystery with priors + Brier calibration) was an early Meta-Garden.
- Gen1 Engines were already absorbing each other (28 canonical slots absorbing 44 + 5 = 77
  named concepts — verified exactly).
- Gen2 turned Gardens into structured data (29 profiles + one resonance engine) but its engine
  layer sits halfway: 28 catalog entries are *metadata*; only 5 engines execute in the Citta loop.

Gen3 direction:
- **Garden = conditions** — basis states in the field: `semantic_anchor, coordinate_priors,
  resonance_kernel, temperature_bias, attention_bias, novelty_bias, verification_bias,
  timescale_bias, operator_priors`; a Meta-Garden is a generated mixture/pose
  (DEBUGGING = truth .28 heals .22 …), with only repeatedly useful mixtures gaining durable
  names; learned resonance can be blended `λ·canonical + (1−λ)·learned`, with Julia doing
  spectral/community analysis offline (§2 L3002–3104). Status: **PARTIAL-G2** → **DESIGN**.
- **Engine = transformation** — a compiled DAG/recipe over general operators
  (PROJECT/SEARCH/PROPAGATE/CLUSTER/COMPARE/ASSOCIATE/SIMULATE/VERIFY/SYNTHESIZE); historical
  engines become recipes (Serendipity ≈ sample dormant stars → project → cross-galaxy search →
  novelty filter → topology compare → evidence score → surface); successful primitive traces
  can be mined into Meta-Engine recipes (§2 L3106–3211). Status: **PARTIAL-G2** → **DESIGN**.
  (Gen2's `SkillForge` catalog entry describes this — but is metadata only; see archaeology.)
- Clean relation: **Gardens say how to think. Engines say what transformation to perform.**
  Intent → Garden Compiler (field priors) → Engine Compiler (DAG) → Citta field → Gan Ying (§2
  L3213–3265).
- No Garden needs its own router/event bus/database/homeostasis; one field, one memory fabric,
  one nervous system, one scheduler (§2 L3267–3277).

## 8. Gan Ying, transport, and the membrane

- **Gan Ying is the semantic nervous system** (what happened, what it means, what resonates, who
  responds, how strongly activation propagates). Transport is an abstraction underneath:
  Tokio (in-process) · iceoryx2 (local zero-copy IPC) · network (Sangha/mesh). A tiny
  single-process WhiteMagic needs none of the IPC layer (§2 L1877–1898, L2585).
  Status: **PARTIAL-G2** — Gen2 has resonance/event types; no iceoryx2. Archaeology note: *Gen1*
  compiled iceoryx2 (Rust bridge default features `["python","arrow","iceoryx2"]`), Gen2 dropped
  it — so this is a re-adoption decision, not a new idea.
- Semiosis ladder: `resonance → signal → communication → semiosis → memetic transfer →
  inheritance`; semiosis is where a signal acquires meaning inside the recipient — hence
  prompt injection is an interpretive problem, not only a transport problem (§3 L3937–3959).
- Membrane stance: integration ≠ loss of boundary. "The membrane must remain logically
  enforceable, not necessarily physically distant" (§3 L3929–3935); make it increasingly
  permeable, fast, intelligent while preserving the distinction (§3 L3763–3793).
- Two gates: `transport validation → semantic/authority validation` (§3 L4230–4234). Status:
  **DESIGN** (Gen2's Landlock/compartments/consent cover the transport half only).

## 9. Representation & mathematics stack (all Phase 3+; Phase 1 forbids)

- Durable: LMDB / Tantivy / vector index. Working set: **Arrow RecordBatch** per activation
  wave (id, activation, semantic_similarity, edge_strength, trust, recency, novelty,
  temperature_weight, galaxy_membership, conflict) processed by Rayon/SIMD (§2 L2221–2260).
- **Rust owns the living system; Julia explores the mathematics of the living system; Arrow is
  the shared representation.** Julia is not in the recall path: it answers geometry/topology
  questions offline; proven kernels get ported to Rust (§2 L2689–2741).
- Full stack: LMDB + Tantivy + vectors + Arrow + graph math + Tokio + Rayon + SIMD + optional
  iceoryx2 + tiny models + experimental Julia (§2 L2963–2967, L3394–3402).
- Status: **DEFERRED** by `DEPENDENCY_MANIFEST.md`; included here so Phase 3 knows the shape.
  Gen1 precedent: its Rust bridge had arrow + iceoryx2; Gen2 keeps arrow only as an optional
  LanceDB feature and has no iceoryx2.

## 10. Developmental ecology, inheritance, and metabolism (DEFERRED)

- Models of adaptation speed: context ≪ adaptive substrate ≪ Geneseed/adapters ≪ foundation
  weights (§3 L3593–3597). External evidence: Moving Castles / Zero trained character into
  weights from a simulated associative field — "an ecology turned into a genome" vs WhiteMagic
  keeping the ecology alive (§3 L3563–3617).
- Soma/germline: sessions, memories, dreams, transient adaptations are somatic; only repeatedly
  validated adaptations graduate toward **Geneseed** (§3 L3887–3905, L4246–4250). Inheritance is
  downstream of selection — it becomes a **Phase 4 candidate**, never a Phase-1 dependency.
- `simulation ≠ evidence`: a simulated childhood can form priors; only external outcomes ground
  them (§3 L3725–3731; Charter §3.8).
- **Developmental power is governance power** (§3 L3737–3753) — a synthetic world needs
  provenance, generated evidence stays tagged simulated, developmental interventions are
  inspectable. See §12.
- Metabolism vs recurrence (§3 L3891–3905): monitor `M = externally grounded informational
  intake / total cognitive processing` as a health metric against "synthetic inbreeding". The
  stranger lane (real installs, usage, value evidence) is **architectural metabolism**, run in
  parallel with Phases 0–3 (§3 L4212–4234).

## 11. Symbolic lenses (render only)

Tree of Life (Kether → Malkuth with both descending and ascending paths), Suares, Yijing,
Yogācāra, Mahāmudrā, alchemy, astronomy, biology — all are **lenses for communication and
design**, never runtime branches (§2 L2851–2931; Charter §3.10 "Symbols may render; symbols may
never dispatch"). The 9-sphere ↔ 9-verb convergence is intellectually interesting; architecture
follows evidence (§3 L4192).

## 12. Review notes on the frozen constitution (no new invariants)

Charter **v0.1.1** froze the invariant set at **ten** with the explicit instruction that the
next change should come from an experiment breaking them, not from further design prose. The
conversation produced four candidate rules; they are recorded here as **review notes only**,
not proposals, and none should be raised until Phase-2 evidence exists:

1. **Developmental environments carry provenance**; generated evidence remains tagged simulated;
   developmental interventions are inspectable (§3 L3745–3753). Currently covered in spirit by
   Charter §3.2/§3.5/§3.8.
2. **Two-gate boundary rule:** transport validation → semantic/authority validation
   (§3 L4230–4234). Not yet reflected in any invariant; first candidate for a real amendment if
   Phase-2+ boundary work demands it.
3. **Membrane principle:** physical integration is acceptable only while logical enforcement
   persists (§3 L3929–3935). Architectural stance; no invariant needed yet.
4. **Credit gate:** reinforcement requires traceable participation in an outcome — **already
   ratified** as the causal attribution gate (Charter §6), so no amendment is required.

If any note becomes a proposal, it follows the CHARTER §4 procedure (proposal → canary
demonstration → ratification → receipt).

## 13. Explicit non-goals / anti-patterns

- No "300 → 900 better tools" path; the move is 300 tools → a small verb basis (§2 L2607–2613).
- No subsystem-per-capability; no bespoke Garden/Engine classes (§2 L3356–3360).
- No simulated emergence — "don't simulate the appearance of emergence; construct conditions and
  measure whether it occurred" (§2 L3501–3505).
- No constitutional self-amendment by adaptive processes; constitutions never recombine
  implicitly (§3 L3909–3925; Charter §4).
- No architecture-by-symmetry (28×28×28 as scaffolding was Gen1's bloat mechanism — archaeology).
- No silent promotion of simulated → world evidence; no inference-only world-evidence.

## 14. Verification snapshot (what Gen2 already proves vs. what Gen3 must earn)

| Canon element | Gen2 status today | Phase where it must earn entry |
|---|---|---|
| Evidence bundles + abstention + revision chains | **IMPL-G2** | inherited as prior art, not imported into the A/B |
| Claims ledger + Brier calibration | **IMPL-G2** | inherited (Gen3's thesis is recorded there) |
| Cold rotation / retention / backup-restore | **IMPL-G2** | Phase 1 lifecycle analogue |
| Activation/decay/propagation primitives | **PARTIAL-G2** | Phase 1 field (`e=(w,s,c,t)`) |
| Garden profiles + resonance engine | **PARTIAL-G2** | Phase 3 (Gardens → conditions) |
| Engines as executable recipes | **PARTIAL-G2** (5 exec / 28 metadata) | Phase 3 (Engines → transformations) |
| Memory star projections / stellar lifecycle | **DESIGN** | Phase 1 field shape; Phase 3 refinement |
| Hyperedges / constellation topology | **DESIGN** | Phase 3 (evidence-gated) |
| Recall compiler / verb planner | **DESIGN** | Phase 1 (4 verbs) → Phase 3 (full basis) |
| Arrow / Julia / iceoryx2 stack | **DEFERRED** | Phase 3+, only if metrics demand |
| Geneseed / developmental worlds | **DEFERRED** | Phase 4, after selection demonstrated |

**Reading rule:** a row tagged DESIGN is a hypothesis about Gen3, not a claim about Gen2. Any
sentence in future documents that promotes a DESIGN row to "WhiteMagic does X" violates the
claim-discipline that both generations died to learn.
