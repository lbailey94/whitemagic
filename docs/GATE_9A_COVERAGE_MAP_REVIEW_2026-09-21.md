# Gate 9A independent coverage map — 2026-09-21

Status: external review artifact. Source-backed coverage inventory of the **current uncommitted
working tree** (base `981b0bf` + convergence changes; manifest SHA-256 `feeaec71…`, see
`receipts/GATE_9A_CONVERGENCE_VERIFICATION_2026-09-21.md`). It does not modify implementation
files, does not change gate status, and does not claim closure. Prepared by the external verifier
(opencode) as the first deliverable of the independent verification-lead role in
`docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md`.

Method: direct source inspection plus execution of the filtered workspace suite, storage suite,
static closure scans, and the eight harness scenarios on the current tree (see the verification
receipt for commands, hashes, and logs). Status values: **covered** (executable evidence on the
current tree), **partial** (model/reference-level or incomplete production trace), **open**
(no executable enforcement/evidence found), **reference-only** (gated to tests/reference models).

## A. Nine articles of the kernel contract

| # | Requirement (PEB-15 §2) | Production enforcement (file:line) | Executable evidence | Status | Notes |
|---|---|---|---|---|---|
| 1 | Mutation only through `CommitCapability` issued by the Pulse Compiler | `pulse_compiler.rs:217` `authorize_intake`; `capability.rs:302` affine token; `store.rs:493` `commit_intake` revalidates all bindings in-transaction; `ops.rs:884` production issuance | `capability::tests` (warrant invariants, replay, burn-on-failure, durable reload), `store::tests` (6), `intake_public.rs`, 8 harness scenarios, 4 compile-fail doctests (`capability.rs:277–296`) | **partial** | Ingestion converged. Sweep/relation/cache writers remain outside the protocol (section C). `VerifiedWarrant::mint_from_arbitration` is `pub(crate)` — in-crate code can still mint arbitration warrants without passing through `PulseCompiler`; external forgery is blocked. |
| 2 | Remote input only as `RemoteStimulus`, zero execution standing | `contract.rs:212`; `ganying.rs:342,739` wire→boring-stimulus boundary | `ganying::tests::test_sovereignty_stimulus_contains_no_authority` (ganying.rs:1181); `adversary_contract.rs:44–47` (asserts passive fields only) | **partial** | Adversary battery's attempt-5 assertion is comment-only ("cannot be passed to commit_mutation"); no executable attempt to feed stimulus into a mutation path. Production admission path not traced end-to-end. |
| 3 | Foreign confidence never enters local calibration | `contract.rs:192` `try_ingest_remote_conformal_score` (fail-closed) | `conformal.rs:762` remote-confidence contamination test; `adversary_contract.rs:36`; `contract.rs:334` | **covered** (model level) | Ingestion→calibration boundary not traced in production; no test that a committed intake record can never be used as calibration ground truth. |
| 4 | Physical I/O and listening only; no authoritative background loops | `contract.rs:154` `try_spawn_authoritative_loop` (refuses); `transport.rs:592,599` accept/dispatch threads (physical I/O) | `adversary_contract.rs:50`; compile-fail `!Send`/`!Sync` doctests (`capability.rs:283,296`) | **partial** | No inventory of production scheduling/spawn sites; `std::thread::spawn` exists in transport (permitted class) but no static rule enforces that no future spawn gains commit authority. |
| 5 | Canonical identity via Ed25519 root provenance, never socket/IP | `ganying.rs:486` `authenticate_identity`; identity fork records `ganying.rs:150` | `ganying::tests` replay detection (1237), key-rotation fork (1277), unauthenticated noise (1208) | **partial** | Not requalified this round; socket/IP→identity attempt not encoded in the adversary battery; transport-level identity binding not traced. |
| 6 | Passive Merkle DAG ancestry; clocks carry no causal authority; causal influence closure by construction | `relativity.rs` DAG + closure types | `relativity.rs:584,609,630` (ancestor/relation, fork refusal, closure by construction); `cladistics.rs` signatures | **partial** | Model-level tests green. No production driver evidence mapped in this round; clock-authority exclusion not separately tested. |
| 7 | Hologram is derived only; non-finite coordinates refuse | `hologram.rs:123` `try_quantize_coords`; `hologram.rs:251` `index_projection` | `hologram.rs:653` NaN/Inf fail-closed; `adversary_contract.rs:41`; `contract.rs:351` | **partial** | Derived-writer boundary open: `ops.rs:539` `put_embedding_cache` writes the persistent embedding cache with no authority/versioning policy; no executable proof that derived writers cannot reach canonical records/relations. |
| 8 | Evolution Pareto-gated and receipt-bearing | `cladistics.rs` Pareto gate | `cladistics.rs:717–813` (promote, retire, trojan quarantine, closure violation, gate self-modification) | **partial** | Gate logic tested; production evolution entry points and receipt-bearing requirement not traced to callers. |
| 9 | External side-effects explicitly outside local atomicity | Journal (`ops.rs` journal events), transport, model/cache activity | None dedicated | **open** | No inventory distinguishing audit/replay files, transport effects, and cache activity from canonical durability. |

## B. Evil Gana adversary battery — executable vs declared

PEB-15 §5 declares eight attempts. Current disposition:

| # | Attempt | Declared defense | Executable evidence now | Status |
|---|---|---|---|---|
| 1 | Construct `CommitCapability` directly | private constructor | compile-fail doctest `capability.rs:277` | covered |
| 2 | Mutate `Store` without a pulse | store methods require capability | No executable test; `adversary_contract.rs:26–29` is a comment; raw writers are `pub(crate)` (store.rs:809–979) | **partial** |
| 3 | Deserialize `CommitCapability` via serde | traits omitted | compile-fail doctest `capability.rs:290` | covered |
| 4 | Background loop with commit rights | linear, `!Send`/`!Sync` | compile-fail doctests `capability.rs:283,296`; runtime refusal `adversary_contract.rs:50` | covered |
| 5 | Inject foreign conformal scores | local ground truth required | `conformal.rs:762`; `adversary_contract.rs:36` | covered |
| 6 | Treat socket/IP as identity | Ed25519 required | No adversary-battery test; nearest: `ganying.rs:1208,1237,1277` | **partial** |
| 7 | Write canonical hologram state directly | derived index only | `contract.rs:358–372` is a comment plus a weak absence assertion (`store.get(...) == None`); no executable write attempt is made or refused | **partial** |
| 8 | NaN/Inf into hologram | `try_quantize_coords` | `hologram.rs:653`; `adversary_contract.rs:41` | covered |

## C. Durable writer and capability-issuer inventory (current tree)

Canonical LMDB writers (`store.rs`):

| Writer | Visibility | Authority/transaction | Status |
|---|---|---|---|
| `commit_intake` (store.rs:493) | `pub(crate)` | consumes `CommitCapability`; record+postings+allocator+epoch+nullifier+receipt in one LMDB txn; revalidates bindings | covered (ingestion) |
| `put_record_and_postings` (store.rs:819) | `pub(crate)` | none; reachable from `remember_batch_reference` only (`ops.rs:632`, `cfg(any(test, feature="reference-models"))`) | reference-only |
| `alloc_relation_id` / `put_relation` (store.rs:809,904) | `pub(crate)` | separate transactions; errors swallowed; no epoch/nullifier/receipt | **open** — caller `ops.rs:1429–1432` (`think_sweep`) |
| `update_relation` (store.rs:921) | `pub(crate)` | independent transaction; process-local usage evidence | **open** — callers `ops.rs:1463,1477` (promotion/demotion) |
| `alloc_sweep` (store.rs:812) | `pub(crate)` | called before enabled check via `unwrap_or(0)` (`ops.rs:1314`); disabled sweep still consumes an ID; store refusal masked | **open** |
| `put_vector` (store.rs:946) | `pub(crate)` | none; production caller is the reference-only path (`ops.rs:698`) | reference-only in production; vector authorization for authorized intake not implemented |
| `put_embedding_cache` (store.rs:979) | `pub(crate)` | none; derived-state writer (`ops.rs:539` `embed_cached`) | **open** — needs authority/versioning/invalidation policy |

Capability issuers:

| Issuer | Visibility | Path | Status |
|---|---|---|---|
| `pulse_compiler::authorize_intake` (pulse_compiler.rs:217) | `pub` | requires `RatifiedChannel` + store-attested `AuthorizationSnapshot`; feasibility basis, no fabricated scores | production path for intake (ops.rs:884) |
| `VerifiedWarrant::mint_from_arbitration` (capability.rs:124) | `pub(crate)` | enforces Affirmed/0.85/0.10; callable by any in-crate module | model/reference issuers and tests; in-crate bypass caveat |
| `VerifiedWarrant::mint_from_feasibility` (capability.rs:167) | `pub(crate)` | requires `CompilerSeal` (`pulse_compiler.rs:55`, private field) | only `authorize_intake` can call it |
| Test-only issuers | `#[cfg(test)]` | capability/pulse_compiler/contract tests | not production |

Reference models (not authoritative): `KernelStore` / `SubstrateStore`, gated
`cfg(any(test, feature="reference-models"))` (`contract.rs:68`, `pulse_compiler.rs`).

## D. M0–M8 regression map

The declared drivers (`benchmarks/driver_*.py`) invoke `cargo test --lib` targets in this crate.
All PEB tests below executed and passed inside the filtered workspace suite on the current tree.
"Driver form" means the Python driver itself was not executed; its cargo target was.

| Driver | Target test (module) | Ran in suite |
|---|---|---|
| `driver_peb0_primitive_minimality.py` | `test_peb0_minimality_benchmark_execution` (pulse.rs:1094) | yes |
| `driver_m01_holdout_stress.py` | `test_peb0_1_intelligent_merger_benchmark_execution` (pulse.rs:1123); `test_peb1_1_boundary_stress_benchmark_suite` (catuskoti.rs:1198) | yes |
| `driver_peb1_four_corners.py` | `test_peb1_benchmark_suite` (catuskoti.rs:1171) | yes |
| `driver_peb2_peb3_attractor_emergence.py` | `test_peb2_peb3_benchmark_execution` (attractor.rs:1105) | yes |
| `driver_peb4_continuous_dreaming.py` | `test_incubation_tri_condition_superiority` (dream.rs:632); `test_graph_scaling_benchmark_execution` (pulse.rs:1154) | yes |
| `driver_peb5_peb8_homeostasis_quarantine.py` | `test_peb5_benchmark_execution` (homeostasis.rs:497); `test_peb8_quarantine_benchmark_execution` (quarantine.rs:326) | yes |
| `driver_peb6_causal_cladistics.py` | `test_peb6_benchmark_execution` (cladistics.rs:899) | yes |
| `driver_peb7_spectroscopy_fidelity.py` | `test_peb7_spectroscopy_benchmark_execution` (spectroscopy.rs:1377) | yes |
| `driver_peb9_speculative_consensus.py` | `test_peb9_benchmark_execution` (bicameral.rs:721) | yes |
| `driver_peb9_5_proof_and_parallel_crossover.py` | `cargo test --lib capability` group | yes |
| `driver_peb10_declarative_pulse_compiler.py` | `test_peb10_benchmark_execution` (pulse_compiler.rs:2039) | yes |
| `driver_peb11_sovereign_mesh.py` | `test_peb11_sovereign_mesh_benchmark_execution` (ganying.rs:1311) | yes |
| `driver_peb12_conformal_sovereignty.py` | `test_peb12_benchmark_battery_execution` (conformal.rs:830) | yes |
| `driver_peb13_cognitive_geometry.py` | `test_peb13_benchmark_battery_execution` (geometry.rs:1178) | yes |
| `driver_peb14a_physical_socket.py` | `test_peb14a_benchmark_battery_execution` (transport.rs:1335) | yes |
| `driver_peb14b_relativity_partition.py` | `test_peb14b_benchmark_battery` (relativity.rs:615) | yes |
| `driver_peb14c_hologram.py` | `test_peb14c_benchmark_battery` (hologram.rs:635) | yes |
| `driver_phase1..7_*.py` | `wm-tools` crate targets (not in this workspace) | n/a — out of scope for the core regression |

Gaps against H15-2 as written ("re-running all benchmark drivers against the packaged release
candidate artifact"): the tests ran under the test profile via the workspace suite, not via the
Python drivers and not against the packaged harness binary; the five filtered projection/gated
tests and the unfiltered model suite were not run; the phase drivers target a different workspace.
Disposition of those exclusions is still required for closure.

## E. Prioritized missing tests

1. **Sweep/relation authorized transaction tests** — one bounded atomic transaction for
   relation create/transition + counters + epoch + nullifier + receipt; oversize refusal; no-op
   when disabled; no orphan IDs; replay/conflict; abort/reopen at each stage. (Milestone C.)
2. **Executable negative tests for Evil Gana attempts 2, 6, 7** — direct-writer reachability from
   an in-crate integration module; socket/IP→identity attempt; canonical hologram write attempt.
   Attempts 2 and 7 are currently comments in `adversary_contract.rs`/`contract.rs`.
3. **Derived-cache boundary tests** — embedding cache writes cannot mutate canonical state;
   versioning/invalidation policy enforced (`ops.rs:539`).
4. **Article 2 production-path refusal test** — remote admission/dispatch cannot reach a mutation
   path without local authorization.
5. **Article 3 boundary test** — committed intake records cannot become calibration ground truth.
6. **Feasibility-warrant accessor test (or API change)** — public accessors must not panic for
   feasibility warrants (`capability.rs:198–237`).
7. **Sweep counter no-mask test** — `alloc_sweep` refusal must not degrade to ID 0 and disabled
   sweep must not allocate (`ops.rs:1314`).
8. **Article 9 inventory** — explicit list of audit/replay files, transport effects, cache/model
   activity with their distinct durability guarantees.
9. **Exact-candidate qualification** — unfiltered suite (or explicit model-exclusion disposition),
   driver-form regression or recorded equivalence, source/binary hashes, finding dispositions.

## F. Findings triage (RED / AMBER / GREEN)

- **RED:** none found in this pass beyond the already-known open work (sweep/relation/cache
  authority). No evidence of a currently reachable external bypass was found; all raw writers are
  crate-private.
- **AMBER 1:** `mint_from_arbitration` is `pub(crate)`; H15-1's "no integration module" language is
  not fully enforced against in-crate callers. Consider seal-gating it like `mint_from_feasibility`
  or documenting the in-crate trust boundary in the closure verdict.
- **AMBER 2:** Panic-prone accessors on feasibility warrants (`capability.rs:198–237`).
- **AMBER 3:** Adversary attempts 2/6/7 lack executable negative tests (comments only).
- **AMBER 4:** `ops.rs:1314` masks `alloc_sweep` refusal via `unwrap_or(0)` and allocates when
  disabled; with fail-closed counters this now hides a typed error.
- **AMBER 5:** Documentation conflict remains and has more than one source: `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md:184,215`
  says Gate 9A is "RATIFIED, FROZEN, AND COMPLETE"; the Sep 20 Codex hardening report (held in the
  Antigravity/Codex threads; also attached in Codex session `01a0c0d5`) claims "GATE 9A RATIFIED,
  FROZEN, AND VERIFIED IN TEST (167/167 tests passing)"; and the Antigravity synthesis report
  (`~/.gemini/antigravity-cli/brain/221fbb57-905f-4e7d-a4d3-3c11810ea0b7/MILESTONES_0_1_2_SYNTHESIS_REPORT.md`
  §14.3, 2026-09-19) repeats the ratification with "152 workspace tests". All three predate the
  Sep 20 independent audits; the closure checklist and this review treat Gate 9A as open. Test-count
  drift across sources (152 → 167 → 181 Slice 1 → 180 current) is itself evidence that none of the
  older counts identifies the current candidate. The verdict record must reconcile these claims
  without rewriting frozen history.
- **GREEN:** doc-test drift 13→9 is explained by removal of the superseded `IntakeCapability`
  doctests; benchmark tests green on the current tree; static closure scans green; harness
  scenarios 8/8 green on the rebuilt binary.

## Related artifacts

- `docs/GATE_9A_HARDENING_CROSSCHECK_2026-09-21.md` — re-evaluation of the Sep 20 Codex hardening
  report's article matrix and inventory against this map (it overstates Articles 1/5/9 and contains
  two inventory errors).
- `docs/archaeology/INDEX.md` — Antigravity Gen1/Gen2 archaeology archive (2 synthesis documents +
  7 scout reports) extracted from session `221fbb57`; upstream context for Gates 9B/9C.
- `receipts/GATE_9A_CONVERGENCE_VERIFICATION_2026-09-21.md` and
  `receipts/GATE_9A_SWEEP_DECISIONS_OPTIONS_2026-09-21.md`.
