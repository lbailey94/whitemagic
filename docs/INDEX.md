# Documentation index

Map of `docs/` for the Gen3 `wm` 10.2.0-alpha line. Version numbers live in the
release surfaces, not here. The product contract is in
[`../README.md`](../README.md); agent onboarding is in [`../skill.md`](../skill.md).

## Operate

| Document | What it covers |
|---|---|
| [`SELFTEST_AND_HOST_HEALTH.md`](SELFTEST_AND_HOST_HEALTH.md) | `wm selftest`: persistence invariants, host-health checks + thresholds, `--strict`/`--json` contracts, guard/CI use |
| [`INSTALL.md`](../INSTALL.md) | source build, store location, optional model layer, verification |
| [`STORE_AND_DATA_HYGIENE.md`](STORE_AND_DATA_HYGIENE.md) | store/data layout and disposable-store policy (historical banner + current v10 layout) |
| [`DEPENDENCY_MANIFEST.md`](DEPENDENCY_MANIFEST.md) | declared dependencies and exceptions |
| [`DERIVED_CACHE_POLICY.md`](DERIVED_CACHE_POLICY.md) | derived embedding cache: classification, invalidation, non-claims |
| [`BENCHMARK_AND_VERIFICATION_PROTOCOL.md`](BENCHMARK_AND_VERIFICATION_PROTOCOL.md) | how benchmark/verification evidence is produced |
| [`CLOSURE_TESTS.md`](CLOSURE_TESTS.md) | Closure 1 / Closure 2 test contract |

## Constitution & design canon

| Document | What it covers |
|---|---|
| [`CHARTER.md`](CHARTER.md) | binding constitutional core (tiers, closures, budgets) |
| [`NUCLEUS.md`](NUCLEUS.md) | four-part nucleus snapshot: pinned contents, statutes, verdict dispositions |
| [`NUCLEUS_FREEZE_CRITERIA.md`](NUCLEUS_FREEZE_CRITERIA.md) | what may enter the nucleus and how the freeze is performed/verified |
| [`DESIGN_CANON.md`](DESIGN_CANON.md) | converged Gen2→Gen3 design vocabulary (annotated, not binding) |
| [`THEORY_MECHANISM_MAP.md`](THEORY_MECHANISM_MAP.md) | every theoretical frame → status label → where it lives |
| [`PHYLOGENETIC_FRAMING.md`](PHYLOGENETIC_FRAMING.md) | reading lens for the compile pass |
| [`GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md`](GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md) | physics/phenotype framing of the organism |
| [`MILESTONE_0_EXECUTION_MANIFEST.md`](MILESTONE_0_EXECUTION_MANIFEST.md) | M0 execution manifest |
| [`WAVE_EXTRACTION_PROTOCOL.md`](WAVE_EXTRACTION_PROTOCOL.md) | extraction/transform record discipline for regressions |

## Preregistrations (PEB-13 … PEB-16)

Frozen experiment registrations; they bind their own runs only.

- [`PREREGISTRATION_PEB13_CONTINUOUS_COGNITIVE_GEOMETRY.md`](PREREGISTRATION_PEB13_CONTINUOUS_COGNITIVE_GEOMETRY.md)
- [`PREREGISTRATION_PEB14A_PHYSICAL_SOCKET_SOVEREIGNTY.md`](PREREGISTRATION_PEB14A_PHYSICAL_SOCKET_SOVEREIGNTY.md)
- [`PREREGISTRATION_PEB14B_RELATIVITY_AND_PARTITIONS.md`](PREREGISTRATION_PEB14B_RELATIVITY_AND_PARTITIONS.md)
- [`PREREGISTRATION_PEB14C_HETEROGENEOUS_SANGHA_HOLOGRAM.md`](PREREGISTRATION_PEB14C_HETEROGENEOUS_SANGHA_HOLOGRAM.md)
- [`PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`](PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md)
- [`PREREGISTRATION_PEB15_AMENDMENT_GATE9C.md`](PREREGISTRATION_PEB15_AMENDMENT_GATE9C.md)
- [`PREREGISTRATION_PEB15_AMENDMENT_GATE9D.md`](PREREGISTRATION_PEB15_AMENDMENT_GATE9D.md)
- [`PREREGISTRATION_PEB16_MANDALA_P2P_MESH_AND_SOVEREIGN_SYNC.md`](PREREGISTRATION_PEB16_MANDALA_P2P_MESH_AND_SOVEREIGN_SYNC.md)

## Specs (`docs/specs/`)

Frozen Wave-1/Wave-2 behavioral specs and their registrations (all draft-era,
kept as the frozen text they were ratified against):

- Wave 1: `W1_A1_durable_store_ingestion`, `W1_A2_evidence_disclosure`,
  `W1_A3_revisions_supersession`, `W1_B1_retrieval_ranking`,
  `W1_B2_sessions_continuity`, `W1_B3_coordination`,
  `W1_B4_claims_belief_class`, `W1_B5_galaxies_compartments`
- Wave 2: `W2_01_relations_edges`, `W2_02_retention_lifecycle`,
  `W2_03_currentness_strata`, `W2_04_dream_consolidation`,
  `W2_05_recipe_layer`, `W2_06_rsi_over_journal`, `W2_07_selfmodel_inspect`
- Registrations/prep: `W1_B5_RECALL_VIEW_REGISTRATION`,
  `W1_SCORER_DETERMINISM_REGISTRATION`, `W2_02_04_ACCEPTANCE_PREP`

## Archive

Closed/superseded material; each directory has a README explaining its scope.
Paths written inside archived files refer to their pre-archive locations.

| Directory | Contents |
|---|---|
| [`archive/gate9a/`](archive/gate9a/README.md) | Gate 9A working set (convergence, coverage maps, external-effect boundaries, reviews) |
| [`archive/research/`](archive/research/README.md) | Phase 1–4 papers, wave findings, archaeology, row-exit packets |
| [`archive/legacy/`](archive/legacy/README.md) | milestone-era handoffs, scaffold/metabolism/testbed plans, one-off audits |

Elsewhere: [`../reference/INDEX.md`](../reference/INDEX.md) is the legacy
reference ledger (Gen1/Gen2 pointers) and [`../HANDOFF.md`](../HANDOFF.md)
carries the current-state block plus the retained historical openers.
