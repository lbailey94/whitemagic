# Gate 9A M0–M8 regression dispositions — 2026-09-22

Status: regression-execution evidence and formal exclusion dispositions for the declared M0–M8
drivers on the current candidate. Prepared by the continuation lane (opencode); does not change
gate status.

## Driver-form execution (new this round)

All 17 core drivers executed **in driver form** (the Python scripts themselves) against the current
working tree on 2026-09-22; 17/17 PASS. Logs:
`receipts/gate9a_article_evidence_20260922/logs/drivers/` (one log per driver + `summary.txt`).

| Driver | Result | Target (cargo) |
|---|---|---|
| driver_peb0_primitive_minimality | PASS | `wm-gen3-core --lib test_peb0_minimality_benchmark_execution` |
| driver_m01_holdout_stress | PASS | `test_peb0_1_intelligent_merger…`; `test_peb1_1_boundary_stress…` |
| driver_peb1_four_corners | PASS | `test_peb1_benchmark_suite` |
| driver_peb2_peb3_attractor_emergence | PASS | `test_peb2_peb3_benchmark_execution` |
| driver_peb4_continuous_dreaming | PASS | `test_incubation_tri_condition_superiority`; `test_graph_scaling…` |
| driver_peb5_peb8_homeostasis_quarantine | PASS | `test_peb5…`; `test_peb8…` |
| driver_peb6_causal_cladistics | PASS | `test_peb6_benchmark_execution` |
| driver_peb7_spectroscopy_fidelity | PASS | `test_peb7_spectroscopy_benchmark_execution` |
| driver_peb9_speculative_consensus | PASS | `test_peb9_benchmark_execution` |
| driver_peb9_5_proof_and_parallel_crossover | PASS (after fix) | `--lib capability` group + adversarial-proof experiment |
| driver_peb10_declarative_pulse_compiler | PASS | `test_peb10_benchmark_execution` |
| driver_peb11_sovereign_mesh | PASS | `test_peb11_sovereign_mesh_benchmark_execution` |
| driver_peb12_conformal_sovereignty | PASS | `test_peb12_benchmark_battery_execution` |
| driver_peb13_cognitive_geometry | PASS | `test_peb13_benchmark_battery_execution` |
| driver_peb14a_physical_socket | PASS | `test_peb14a_benchmark_battery_execution` |
| driver_peb14b_relativity_partition | PASS | `test_peb14b_benchmark_battery` |
| driver_peb14c_hologram | PASS | `test_peb14c_benchmark_battery` |

Driver fix in this round: `driver_peb9_5` asserted a hard-coded "ok. 4 passed" for the capability
filter; the matched set legitimately grew to 10 (new capability/store tests). The assertion is now
count-robust ("ok." and "0 failed"), preserving intent without freezing coverage.

## Formal exclusion dispositions

| Exclusion | Disposition |
|---|---|
| 7 `driver_phase*` drivers | Target the separate `wm-tools` workspace, not this crate (per `GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` §D). Out of scope for the core M0–M8 regression; they remain phase-driver evidence for later gates. |
| 5 filtered projection/gated tests | Projection-enabled intake fails closed under ratified Slice 1 scope; the two projection-path tests are additionally `#[ignore]`d with an explicit 9C requalification reason. Filter remains declared in the ratified battery command. |
| Unfiltered model suite | Not run; model behavior is not qualified by this slice (verdict must state this). Projection execution is inventoried under Article 9 with its boundary. |
| H15-2 "packaged release candidate" wording | Core regression is qualified via driver-form cargo targets and the 9-scenario process-boundary harness check on the release binary; packaged CLI verification is 9B per PEB-15 §8.2. |
| Physical power-loss proof | Out of scope (9D); current evidence is synthetic reopen/abort testing, explicitly not power-loss proof. |

Driver scripts wrote their own artifacts under `receipts/` (`benchmark_*.json`, `BENCHMARK_*.md`);
those are generated evidence, not source.
