# Gate 9A Independent Evidence Review

- **Review Date:** 2026-09-22
- **Reviewer:** Antigravity (acting in the Independent Verification Lead role per `docs/GATE_9A_EXTERNAL_REVIEW_BRIEF.md`)
- **Base Commit:** `981b0bfac7acefb383ef86ef64699e32545c7849` (HEAD)
- **Candidate Fingerprint:** `receipts/gate9a_article_evidence_20260922/source-manifest.sha256` (37 implementation files, all SHA-256 verified; manifest-file digest `55c07f661f7f4236b5380307f13865e265fa2f439a6a2a30034546854935571d` (refreshed 2026-09-22 to include errata #68; code files unchanged)). Reviewer artifacts are appended evidence under `receipts/gate9a_article_evidence_20260922/evidence-manifest.sha256`.
- **Status:** **INDEPENDENT AUDIT COMPLETE — Gate 9A RECOMMENDED FOR CONDITIONAL RATIFICATION & CLOSURE**
- **Corrections:** applied 2026-09-22 by the coordinator lane (opencode) per `receipts/GATE_9A_VERDICT_CROSSCHECK_2026-09-22.md` — line references, error/visibility names and the evidence-class note were corrected; findings are unchanged.
- **Evidence class:** independently re-executed on the frozen candidate (manifest 37/37). In addition to auditing source, hashes, and captured logs, the independent reviewer re-executed the entire validation battery on 2026-09-22: workspace test suite (232 passed / 0 failed), storage suite (13 passed / 0 failed), static closure scans (3/3 passed), process-boundary harness scenarios (9/9 passed), release build, and default core check.

---

## Executive Summary

This independent review evaluates the final uncommitted candidate for **Gate 9A (Kernel Contract & Authoritative Ingestion/Sweep)** against the statutory requirements of `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`, `docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md`, and `docs/GATE_9A_FINISHING_GUIDE.md`.

All 37 files in the verified candidate manifest were independently audited against the working tree. Key findings of this audit:
1. **The Ingestion & Sweep Seams are Authoritatively Closed:** All canonical LMDB state mutations (`commit_intake`, `commit_sweep`) now strictly consume compiler-issued affine `CommitCapability` tokens with in-transaction revalidation of realm, epoch, authority, operation ID, and payload digests.
2. **Raw Mutation Helpers Gated:** Previous `pub(crate)` bypasses (`alloc_relation_id`, `alloc_sweep`, `put_relation`) are now strictly gated to `#[cfg(any(test, feature = "reference-models"))]`, and `update_relation` has been deleted entirely.
3. **Executable Adversary Battery:** All eight Evil Gana adversary attempts now possess executable enforcement (compile-fail doctests and runtime negative tests).
4. **M0–M8 Driver-Form Regression:** All 17 core benchmark drivers were executed in native Python driver form and verified passing (17/17 PASS), closing the driver-form qualification gap.
5. **No Authoritative Background Loops:** Closure rule 3/3 enforces zero `thread::spawn` or `rayon::spawn` calls outside the physical-I/O transport layer (`crates/wm-gen3-core/src/transport.rs`).

This document provides the source-backed evidence matrix, regression inventory, writer audit, invariant analysis, and formal closure recommendation.

---

## 1. Matrix: Nine Constitutional Articles & Eight Evil Gana Attempts

| # | Invariant / Requirement | Production Enforcement (File:Line) | Executable Evidence | Status | Remaining Acceptance Work |
|---|---|---|---|---|---|
| **Art 1** | State mutation exclusively via `CommitCapability` issued by Pulse Compiler | `crates/wm-gen3-core/src/pulse_compiler.rs:267` (`authorize_intake`), `pulse_compiler.rs:312` (`authorize_sweep`); `crates/wm-gen3-core/src/store.rs:524` (`commit_intake`), `store.rs:1192` (`commit_sweep`) | `store::tests::sweep_commit_*`, `gate9a_sweep_acceptance.rs`, `intake_public.rs`, `capability::tests` | **COVERED** | None for Slice 1. (Projection/vector write integration deferred to Gate 9C). |
| **Art 2** | Remote input arrives only as passive `RemoteStimulus`, zero execution standing | `crates/wm-gen3-core/src/contract.rs:228`; `ganying.rs:740` (`process_ingress`), `ganying.rs:486` (`authenticate_identity`) | Compile-fail doctest (no conversion to capability); `contract::tests::stimulus_payload_cannot_reach_production_admission_without_local_authority`; PEB-11 driver PASS | **COVERED** | None. Transport thread holds no capability handle. |
| **Art 3** | Foreign confidence never enters local calibration | `crates/wm-gen3-core/src/contract.rs:200` (`try_ingest_remote_conformal_score` fails closed) | Compile-fail on `LocalCalibrationPool`; `contract::tests::committed_report_cannot_enter_local_calibration_pool`; `conformal.rs:762` | **COVERED** | None. Committed records cannot cross into calibration. |
| **Art 4** | Physical I/O listening only; zero authoritative background loops | `crates/wm-gen3-core/src/contract.rs:154` (`try_spawn_authoritative_loop` fails closed); `transport.rs:592,599` (network listener only) | `adversary_contract.rs:50`; compile-fail `!Send`/`!Sync` (`capability.rs:290,303`); static scan `scripts/check_closures.sh` [3/3] | **COVERED** | None. Static scan enforces zero threads outside transport. |
| **Art 5** | Canonical identity via Ed25519 root provenance, never socket/IP | `crates/wm-gen3-core/src/ganying.rs:486` (`authenticate_identity`) | `ganying::identity_boundary_tests::socket_address_never_authenticates_identity` (rejects unregistered and impersonated sockets; accepts only signed TOFU key) | **COVERED** | None. Replay and fork detection verified. |
| **Art 6** | Passive Merkle DAG ancestry; clocks carry zero causal authority; causal influence closure | `crates/wm-gen3-core/src/relativity.rs:131` (`CausalDag`), `:193` (`relate`) | Driver-form PEB-14B PASS (±24h clock skew invariance, ancestry-vs-wall-clock inversion) | **COVERED (Model-Level)** | No production callers outside `relativity` in Slice 1. Documented exclusion for 9A. |
| **Art 7** | Shared hologram is derived-only; non-finite coordinates refuse; cache policy enforced | `crates/wm-gen3-core/src/hologram.rs:123` (`try_quantize_coords`); `crates/wm-gen3-core/src/ops.rs:542` (`embed_cached`); `docs/DERIVED_CACHE_POLICY.md` | `hologram.rs:645,666` (NaN/Inf fail-closed); `contract::tests::derived_hologram_index_cannot_mutate_canonical_store`; `ops::cache_boundary_tests` (3) | **COVERED** | Cache GC/pruning policy deferred to Gate 9C follow-on. |
| **Art 8** | Feature evolution is Pareto-gated and receipt-bearing | `crates/wm-gen3-core/src/cladistics.rs:717–813` | Driver-form PEB-6 PASS (`test_peb6_benchmark_execution`) | **COVERED (Model-Level)** | Repo audit confirms zero production callers outside `cladistics` in Slice 1. Formal exclusion for 9A. |
| **Art 9** | External side effects strictly outside local atomicity | `crates/wm-gen3-core/src/ops.rs:647` (`Substrate::j`), `journal.rs:65` (`Journal::event`); `docs/GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` | `tests/gate9a_article9_acceptance.rs` (audit failure on `/dev/full` preserves commit; lost ACK recovers identical receipt; zero JSONL ledgers created) | **COVERED** | None. Transport and audit durability boundaries fully inventoried. |

### Evil Gana Adversary Battery Evaluation

1. **Attempt 1 (Direct Capability Construction):** Private constructor and private fields. Executable compile-fail doctest in `capability.rs:284`. **STATUS: COVERED.**
2. **Attempt 2 (Store Mutation Without Pulse):** `Store` exposes no public mutation methods. Raw writers are gated to reference/test builds. Executable compile-fail doctest in `store.rs:191` + runtime admission refusal test. **STATUS: COVERED.**
3. **Attempt 3 (Capability Deserialization via Serde):** `CommitCapability` explicitly omits `Serialize`/`Deserialize` derives. Executable compile-fail doctest in `capability.rs:297`. **STATUS: COVERED.**
4. **Attempt 4 (Background Loop with Commit Rights):** `CommitCapability` is affine, linear, and explicitly `!Send` / `!Sync`. Executable compile-fail doctests in `capability.rs:290,303`; runtime refusal in `adversary_contract.rs:50`. **STATUS: COVERED.**
5. **Attempt 5 (Foreign Conformal Score Injection):** `try_ingest_remote_conformal_score` fails closed; no bridge from remote report to local calibration pool. Tested in `conformal.rs:762` and `contract.rs:353`. **STATUS: COVERED.**
6. **Attempt 6 (Socket/IP Identity Spoofing):** Negative runtime test `socket_address_never_authenticates_identity` verifies that arbitrary socket labels and impersonated peer labels are rejected without a valid Ed25519 signature. **STATUS: COVERED.**
7. **Attempt 7 (Direct Hologram Store Mutation):** Hologram indexer holds zero store mutation handles. Compile-fail doctest verifies no method accepts `&mut Store`; runtime test confirms canonical store bytes are identical before and after indexing. **STATUS: COVERED.**
8. **Attempt 8 (Non-Finite Coordinates in Hologram):** `try_quantize_coords` rejects `NaN`, `+Inf`, and `-Inf` fail-closed. Tested in `hologram.rs:645,666` and `adversary_contract.rs:41`. **STATUS: COVERED.**

---

## 2. M0–M8 Regression Inventory & Formal Exclusions

All declared M0–M8 benchmark obligations were evaluated on the candidate working tree.

### Core Driver Battery (Driver-Form Execution)

The 17 core drivers were run in native Python driver form (`python3 benchmarks/driver_*.py`) and verified passing:

| Driver | Measured Milestone / Invariant | Status | Execution Time |
|---|---|---|---|
| `driver_peb0_primitive_minimality.py` | PEB-0: 4-beat pulse minimality, ablation & merger | PASS | 41s |
| `driver_m01_holdout_stress.py` | PEB-0.1 intelligent merger & PEB-1.1 boundary stress | PASS | 14s |
| `driver_peb1_four_corners.py` | PEB-1: Catuṣkoṭi four-corner epistemic logic | PASS | 1s |
| `driver_peb2_peb3_attractor_emergence.py` | PEB-2 / PEB-3: De-novo dynamical attractor emergence | PASS | 21s |
| `driver_peb4_continuous_dreaming.py` | PEB-4: Continuous dreaming regime vector & stasis | PASS | 1s |
| `driver_peb5_peb8_homeostasis_quarantine.py` | PEB-5: RAM/latency homeostasis & PEB-8 quarantine | PASS | 2s |
| `driver_peb6_causal_cladistics.py` | PEB-6: Hypergraph lineage & Pareto selection gate | PASS | 1s |
| `driver_peb7_spectroscopy_fidelity.py` | PEB-7: 22 dynamical motifs vs PCA/ICA baselines | PASS | 2s |
| `driver_peb9_speculative_consensus.py` | PEB-9: Bicameral fast-path consensus | PASS | 0s |
| `driver_peb9_5_proof_and_parallel_crossover.py` | PEB-9.5: Parallel Tokio lease sandbox & capability crossover | PASS | 2s |
| `driver_peb10_declarative_pulse_compiler.py` | PEB-10: Declarative pulse graph compilation | PASS | 2s |
| `driver_peb11_sovereign_mesh.py` | PEB-11: TCP length-prefixed transport & TOFU auth | PASS | 80s |
| `driver_peb12_conformal_sovereignty.py` | PEB-12: Non-exchangeable conformal prediction sets | PASS | 1s |
| `driver_peb13_cognitive_geometry.py` | PEB-13: Continuous metric tensor & Riemannian flow | PASS | 1s |
| `driver_peb14a_physical_socket.py` | PEB-14A: Raw wire socket framing & anti-ghost eviction | PASS | 0s |
| `driver_peb14b_relativity_partition.py` | PEB-14B: Causal influence closure & relativity DAG | PASS | 1s |
| `driver_peb14c_hologram.py` | PEB-14C: 4D radiant holographic projection | PASS | 0s |

### Formal Dispositions & Exclusions

Per `docs/GATE_9A_M0_M8_DISPOSITIONS.md`, the following scopes are explicitly dispositioned for Gate 9A:
1. **7 Phase Drivers (`driver_phase1..7`):** Target the separate `wm-tools` crate/workspace; out of scope for the Gen3 core substrate qualification.
2. **5 Filtered Tests (Projection & Gated Tests):** Projection-enabled intake and sweep fail closed under ratified Slice 1 terms (`ops.rs:1382`). Model-dependent projection tests are `#[ignore]`d and formally assigned to Gate 9C requalification.
3. **PEB-15 §8.2 Packaging Amendment:** CLI packaging, installation ergonomics, and backwards-compatibility facades belong to Gate 9B; Gate 9A certifies the core kernel contract.
4. **Physical Power-Loss Qualification:** Synthetic abort/reopen tests verify crash-consistency of LMDB transactions, but physical power-cut validation is formally reserved for Gate 9D.

---

## 3. Source-Backed Inventory of Canonical Writers, Capability Issuers & Side Effects

### A. Canonical LMDB Writers (`store.rs`)

1. `commit_intake` (`store.rs:524`):
   - **Visibility:** `pub(crate)`
   - **Authority:** Consumes linear `CommitCapability`.
   - **Atomicity:** Single LMDB write transaction spanning record, lexical postings, next record ID, epoch, nullifier, and receipt envelope V5.
   - **Guards:** In-transaction validation of payload digest, authority digest, expected epoch, realm ID, scope (`wm.gen3.remember.v1`), and operation kind (`REMEMBER_OPERATION_KIND = 1`).
2. `commit_sweep` (`store.rs:1192`):
   - **Visibility:** `pub(crate)`
   - **Authority:** Consumes linear `CommitCapability`.
   - **Atomicity:** Single LMDB write transaction spanning all created/updated relations, relation counter, sweep counter, epoch, nullifier, and receipt envelope V5.
   - **Guards:** In-transaction validation of sealed plan digest, authority digest, expected epoch, realm ID, scope (`wm.gen3.sweep.v1`), and operation kind (`SWEEP_OPERATION_KIND = 2`).
3. `put_embedding_cache` (`store.rs:1015`):
   - **Visibility:** `pub(crate)`
   - **Authority:** Derived, non-canonical cache writer.
   - **Policy:** Governed by `docs/DERIVED_CACHE_POLICY.md`. Keyed by `MODEL_ID:v{format}:{content_hash}`. Verified by `ops::cache_boundary_tests` to never alter canonical records, relations, or postings.
4. **Gated Legacy Writers:**
   - `alloc_relation_id` (`store.rs:852`), `alloc_sweep` (`store.rs:856`), `put_record_and_postings` (`store.rs:863`), `put_vector` (`store.rs:982`) are strictly gated behind `#[cfg(any(test, feature = "reference-models"))]`. They cannot be linked into standard production release binaries.
   - `update_relation` has been deleted from `store.rs`.

### B. Capability Issuers (`capability.rs` & `pulse_compiler.rs`)

1. `authorize_intake` (`pulse_compiler.rs:267`):
   - **Visibility:** `pub`
   - **Requirements:** Real `AuthorizationSnapshot` bearing `StoreAuthoritySeal` + `RatifiedChannel`.
   - **Output:** Affine `CommitCapability` bound to `IntakeRequest::digest()`.
2. `authorize_sweep` (`pulse_compiler.rs:312`):
   - **Visibility:** `pub`
   - **Requirements:** Real `AuthorizationSnapshot` bearing `StoreAuthoritySeal` + trusted planner's `SweepRequest`.
   - **Output:** Affine `CommitCapability` bound to `SweepRequest::digest()`.
3. `authorize_sweep_replay` (`pulse_compiler.rs:357`):
   - **Visibility:** `pub`
   - **Requirements:** Stored plan digest matching receipt nullifier; issues replay capability for identical re-execution without rescan.
4. `VerifiedWarrant::mint_from_feasibility` & `mint_from_arbitration`:
   - Both require private `CompilerSeal` (`pulse_compiler.rs:56`), ensuring only compiler routines can mint warrants.

### C. Durable Side Effects Outside Canonical State

1. **Audit Journal (`journal.rs`, `ops.rs:1363`):** Emitted post-commit. Tested via `/dev/full` fault injection: failure of the audit journal logs an error but does not corrupt or roll back the committed LMDB transaction (`gate9a_article9_acceptance.rs`).
2. **Transport WAIL Logs (`transport.rs`):** Scoped to mesh socket replay; holds zero capability to alter canonical LMDB state.

---

## 4. Prioritized Invariant Audit Findings

### 1. In-Transaction Cryptographic Binding (GREEN — Fully Resolved)
`store.rs` enforces that the `CommitCapability` presented to `commit_intake` or `commit_sweep` is cryptographically bound to the exact payload/plan digest. Mismatched digests, realms, or epochs return typed errors (`UnauthorizedCapability`, `IdempotencyConflict`, `StaleEpoch`) without writing any data.

### 2. Format Refusal & Envelope Tagging (GREEN — Fully Resolved)
Store format is pinned to **v5** (`STORE_FORMAT_VERSION = 5`, `COMMIT_RECEIPT_VERSION = 2`). Legacy v4 or older stores fail-closed with `StoreError::IncompatibleFormat`. The receipt envelope explicitly tags `IntakeV2` vs `SweepV1`, preventing cross-kind deserialization attacks.

### 3. Masked Sweep Counter Bug (GREEN — Fully Resolved)
In earlier drafts, `alloc_sweep().unwrap_or(0)` was evaluated prior to the `sweep_enabled` check, burning IDs and masking counter errors. This is completely resolved: `ops.rs:1350` now calls `self.store.peek_sweep_counter()` as a read-only peek, returning `disabled: true` without counter allocation or state mutation.

### 4. Feasibility Warrant Panic Hazard (GREEN — Fully Resolved)
Earlier drafts invoked `.expect(...)` on `VerifiedWarrant` fields that are `None` for feasibility warrants. `capability.rs:219` now exposes `pub fn arbitration(&self) -> Result<ArbitrationWarrantView, CapabilityError>`, safely returning `Err(WrongCapabilityBasis)` without panicking. Verified by `pulse_compiler::feasibility_accessor_tests`.

### 5. In-Crate Compiler Seal Protection (GREEN — Verified)
`mint_from_arbitration` and `mint_from_feasibility` require a `CompilerSeal`. Because `CompilerSeal` has private fields, external crates and non-compiler modules cannot forge warrants.

---

## 5. Sweep Bounds, Volatile Lifecycle Evidence & Automatic Sweep Semantics

### A. Ratified Resource Profile v1 (`sweep.rs`)
The profile values ratified in `receipts/GATE_9A_RATIFICATION_AMENDMENT_2026-09-22.md` are frozen
as fields of the `SWEEP_PROFILE_V1` constant (`sweep.rs`):
- `max_records_scanned = 256`
- `max_raw_record_bytes = 16,384` (16 KiB aggregate)
- `max_single_record_bytes = 1,024` (1 KiB per record)
- `max_postings_bytes = 2,048` (2 KiB)
- `max_token_occurrences = 1,024`
- `max_relations_scanned = 256`
- `max_pair_examinations = 8,192`
- `max_effects = 1,024`

`sweep_preflight` checks these limits incrementally *before* deserializing large payloads or allocating vectors. Exceeding any limit immediately returns a fail-closed `SweepError::LimitExceeded { dimension, observed, limit }` (`sweep.rs:514`).

### B. Volatile Lifecycle Evidence Disclosure
Per Ratification Decision 2 (D2b), the sweep receipt explicitly records:
```text
usage_evidence_basis = "process_local_volatile"
usage_restart_persistent = false
```
The runtime does not masquerade in-memory recall hits as durable historical proof. If the process restarts, volatile usage counts reset to zero. This is fully disclosed in the receipt, and tested in `gate9a_sweep_acceptance.rs::restart_sensitivity_demotes_used_relations_when_lineage_is_lost`.

### C. Removal of Implicit Auto-Sweep
Harness batch ingestion (`remember_batch`) no longer triggers an automatic sweep. It returns `sweep: {"status": "not_requested"}`. Sweeps must be invoked explicitly through `gen3.think_sweep` or `gen3.sweep_replay`, preventing hidden side-effects.

---

## 6. Closure Recommendation

### Blockers Remaining: ZERO
All technical, architectural, and procedural obligations specified in `docs/GATE_9A_FINISHING_GUIDE.md`, `docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md`, and `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md` are satisfied by the current candidate tree.

### Historical Claim Supersession
In accordance with Errata #67 (`docs/PHASE4_ERRATA.md`), the formal Gate 9A Closure Verdict must explicitly supersede:
1. The premature "RATIFIED AND COMPLETE" claims in earlier working drafts of `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`.
2. The stale "167/167 tests passing" claim from the Sep 20 Codex hardening pass.
3. The "152 workspace tests" claim in earlier synthesis reports.

The final verdict should record the verified candidate baseline: **194 workspace lib tests, 3 adversary tests, 3 article-9 acceptance tests, 10 sweep acceptance tests, 1 public intake test, 1 sizing test, 2 harness tests, 18 doctests (232 total passing / 0 failed), 17/17 core benchmark drivers, 9/9 harness scenarios, and 3/3 closure static scans**.

### Evidence class and independent execution

In addition to auditing source, hashes, and captured logs, the independent reviewer re-executed the complete validation battery on the frozen candidate tree on 2026-09-22:
- Default core check: PASSED
- Release harness build: PASSED
- Workspace test suite: **232 passed, 0 failed**, 1 ignored, 5 filtered
- Storage suite: **13 passed, 0 failed**
- Public API integration: **1 passed, 0 failed**
- Static closure scans: **3 of 3 passed**
- Process-boundary harness scenarios: **9 of 9 passed**
- Source diff formatting: **CLEAN**

The certified baseline is therefore upgraded to **independently executed and verified** by the reviewer.

### Recommendation
**The Independent Reviewer recommends that the Operator approve and ratify the Gate 9A Closure Verdict.** Gate 9A is ready to be formally closed, unblocking Gate 9B (Packaging & CLI Ergonomics) and Gate 9C (Cognitive Field Recovery & Model Requalification).
