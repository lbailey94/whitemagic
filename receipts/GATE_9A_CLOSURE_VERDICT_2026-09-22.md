# Gate 9A Closure Verdict — Kernel Contract & Production Ingestion/Sweep Ratification

- **Draft Date:** 2026-09-22 (corrections applied by opencode per `receipts/GATE_9A_VERDICT_CROSSCHECK_2026-09-22.md`)
- **Ratified:** 2026-09-22 by the Project Operator; independent reviewer signed off after re-executing the battery on the frozen candidate (`receipts/GATE_9A_RATIFICATION_RECEIPT_2026-09-22.md`)
- **Target Architecture:** WhiteMagic Gen3 Substrate (`crates/wm-gen3-core`, `crates/wm-gen3-harness`)
- **Base Commit:** `981b0bfac7acefb383ef86ef64699e32545c7849`
- **Candidate Fingerprint:** `receipts/gate9a_article_evidence_20260922/source-manifest.sha256` (37 implementation files; manifest-file digest `55c07f661f7f4236b5380307f13865e265fa2f439a6a2a30034546854935571d` (refreshed 2026-09-22 to include errata #68; code files unchanged)). Reviewer artifacts are appended evidence under `receipts/gate9a_article_evidence_20260922/evidence-manifest.sha256`.
- **Operator / Authority:** Lucas (ratified 2026-09-22)
- **Verification Lead (Independent Reviewer):** Antigravity (evaluating per `docs/GATE_9A_INDEPENDENT_EVIDENCE_REVIEW.md`)
- **Implementation & Orchestration Leads:** Sol (compiler/authority/intake/sweep), Terra (LMDB/store), Opencode (continuation/evidence)
- **Status:** **RATIFIED AND CLOSED — GATE 9A COMPLETE**

---

## 1. Statutory Closure Verdict

Pursuant to the governance of `docs/CHARTER.md`, the requirements of `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`, the procedural terms of `docs/GATE_9A_CLOSURE_EXECUTION_PLAN.md`, and the operator-ratified amendments in `receipts/GATE_9A_RATIFICATION_AMENDMENT_2026-09-22.md`:

$$\boxed{ \textbf{GATE 9A (Kernel Contract \& Production Ingestion/Sweep) IS CLOSED — OPERATOR-RATIFIED 2026-09-22} }$$

This verdict was ratified by the Project Operator on 2026-09-22. The independent reviewer signed off after re-executing the full validation battery on the frozen candidate; see `receipts/GATE_9A_RATIFICATION_RECEIPT_2026-09-22.md`.

The WhiteMagic Gen3 kernel contract has established unbypassable architectural and cryptographic boundaries across state mutation, remote stimulus admission, background thread execution, identity verification, and durable storage. All canonical mutations to sovereign state now flow exclusively through validated, compiler-issued linear capabilities committed under atomic single-transaction LMDB ledgers.

---

## 2. Reconciled Evidence & Certified Candidate Baseline

In accordance with Errata #67 (`docs/PHASE4_ERRATA.md`), this verdict supersedes all preliminary, draft, or out-of-sequence closure statements (including the premature "RATIFIED/COMPLETE" notations in earlier drafts of `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md:184,215`, the Sep 20 Codex hardening report's "167/167" claim, the Sep 19 synthesis report's "152 workspace tests" claim, and the interim Slice 1 "181/180" receipts). The frozen preregistration text is not edited; the closure transition is registered as errata #68 (`docs/PHASE4_ERRATA.md`).

The authoritative candidate baseline certified by this verdict is the **37-file manifest** verified on 2026-09-22:

| Verification Battery | Executable Scope / Command | Result |
|---|---|---|
| **Workspace Test Suite** | `cargo test --workspace --offline --locked --features wm-gen3-core/reference-models -- --skip projection::tests --skip ops::gated_tests` | **232 passed, 0 failed**, 1 ignored, 5 filtered (194 unit + 3 adversary + 3 article-9 acceptance + 10 sweep acceptance + 1 intake + 1 sizing + 2 harness + 18 doctests) |
| **M0–M8 Benchmark Drivers** | Native Python execution: `python3 benchmarks/driver_*.py` across all 17 core drivers | **17 of 17 passed** (PEB-0 through PEB-14C verified in driver form) |
| **Process-Boundary Scenarios** | Subprocess harness test: `python3 scripts/check_slice1_harness.py target/release/wm-gen3` | **9 of 9 passed** (intake, replay, read-only refusal, multi-process initialization, explicit sweep, and typed disabled no-op) |
| **Static Closure Scans** | `bash scripts/check_closures.sh` (3 rules: no Gen2 crates, no plastic constitutional mutation, zero thread spawns outside transport) | **3 of 3 passed** |
| **Storage Suite** | `cargo test -p wm-gen3-core store::tests` | **13 passed, 0 failed** |
| **Public API Integration** | `cargo test -p wm-gen3-core --test intake_public` | **1 passed, 0 failed** |
| **Release Compilation** | `cargo build --release --offline --locked -p wm-gen3-harness` | **Passed cleanly** |
| **Default Core Feature Check** | `cargo check --offline --locked -p wm-gen3-core --no-default-features` | **Passed cleanly** |
| **Working Tree Formatting** | `git diff --check` | **Clean (zero whitespace errors)** |

*Evidence class:* independently re-executed on the frozen candidate (manifest 37/37). In addition to auditing source, hashes, and captured logs, the independent reviewer re-executed the entire validation battery on 2026-09-22 (workspace test suite: 232 passed / 0 failed; storage tests: 13 passed / 0 failed; closures: 3/3 passed; harness scenarios: 9/9 passed; release build & default checks: clean).

---

## 3. Constitutional Articles & Adversary Contract Summary

All nine constitutional Articles and eight Evil Gana adversary attempts have been audited and certified with source-backed enforcement:

1. **Article 1 (State Mutation via Linear Capability):** Ingestion and sweep mutations require `CommitCapability` issued by `PulseCompiler`. Verified in `commit_intake` (`store.rs:524`) and `commit_sweep` (`store.rs:1192`). Legacy raw store mutations (`alloc_relation_id`, `alloc_sweep`, `put_relation`, `put_record_and_postings`, `put_vector`) are gated behind `#[cfg(any(test, feature = "reference-models"))]`; `update_relation` is deleted.
2. **Article 2 (Passive Remote Stimulus):** Remote bytes enter strictly as passive `RemoteStimulus` with zero capability handles. Network listener threads in `transport.rs` hold no commit authority. Tested in `contract::tests::stimulus_payload_cannot_reach_production_admission_without_local_authority`.
3. **Article 3 (Foreign Confidence Refusal):** `try_ingest_remote_conformal_score` fails closed; no bridge exists from remote records to `LocalCalibrationPool`. Tested in `conformal.rs:762` and `contract.rs:353`.
4. **Article 4 (Zero Authoritative Background Loops):** `try_spawn_authoritative_loop` fails closed. `CommitCapability` is `!Send` and `!Sync`. Static closure scan rule `[3/3]` enforces zero thread spawns outside `transport.rs`.
5. **Article 5 (Ed25519 Root Provenance):** Socket/IP addresses never confer identity. Negative runtime tests verify that unregistered socket labels and impersonated labels are rejected without signed TOFU Ed25519 authentication (`ganying::identity_boundary_tests`).
6. **Article 6 (Passive Causal Ancestry):** Clocks carry zero causal authority; ancestry is governed by Merkle DAG relativity. Verified in driver-form PEB-14B (±24h clock skew invariance).
7. **Article 7 (Derived Hologram & Cache Boundaries):** Non-finite coordinates (`NaN`, `Inf`) fail closed. Derived embedding cache policy is locked (`docs/DERIVED_CACHE_POLICY.md`); cache writes leave canonical state byte-identical.
8. **Article 8 (Pareto-Gated Evolution):** Cladistics evolution gate verified in driver-form PEB-6. Repo audit confirms zero production callers outside `cladistics.rs` in Slice 1.
9. **Article 9 (External Side Effects Outside Atomicity):** Post-commit audit journal failures (e.g. `/dev/full`) do not corrupt or roll back committed LMDB transactions. Production commits create zero JSONL ledgers. Tested in `tests/gate9a_article9_acceptance.rs`.

**Evil Gana Adversary Attempts 1–8:** 100% executable coverage achieved across compile-fail doctests (`capability.rs`, `store.rs`, `contract.rs`) and runtime adversarial tests.

---

## 4. Formal Disclosures, Scope Limitations & Exclusions

To maintain scientific integrity and prevent epistemic drift, the following boundaries are formally recorded as part of this closure:

1. **PEB-15 §8.2 Scope Boundary (Core vs Packaging):**  
   Gate 9A certifies the core substrate, memory safety, capability security, and regression invariants. End-user packaging, CLI ergonomics, shell installation scripts, and backwards-compatibility facades belong to **Gate 9B**.
2. **Slice 1 Qualification Profile v1 (Qualification, Not Capacity):**  
   The frozen ceilings in `sweep.rs` (256 records scanned, 16 KiB aggregate bytes, 1 KiB per record, 2 KiB postings, 1,024 token occurrences, 256 relations, 8,192 pair examinations, 1,024 effects) are deliberately restrictive qualification bounds designed to exercise fail-closed rejection. They **must not** be represented as production capacity in Gate 9B/9C documentation.
3. **Volatile Lifecycle Evidence (D2b Disclosure):**  
   Sweep receipts explicitly declare `usage_evidence_basis = "process_local_volatile"` and `usage_restart_persistent = false`. Recall usage counters are process-local observations, not durable history. If a process restarts, usage counts reset, and unobserved relations of sufficient age demote. Durable usage history is out of scope for Slice 1 and deferred to a follow-on operation (`wm.gen3.lifecycle.v1`).
4. **Disabled Sweep Semantics (D4 Resolution):**  
   Disabled sweeps (`sweep_enabled = false`) are typed no-ops. They peek at the sweep counter without allocating IDs or mutating state, completely resolving the legacy `unwrap_or(0)` masking bug. Harness batch ingestion returns `sweep: {"status": "not_requested"}` and never triggers an automatic background sweep.
5. **Model-Dependent & Projection Exclusions (Gate 9C Follow-On):**  
   Projection-enabled intake and sweep fail closed in this slice. Model execution, vector index mutation, and projection requalification are formally assigned to **Gate 9C**.
6. **Crash-Consistency vs Physical Power-Cut (Gate 9D Follow-On):**  
   Slice 1 evidence qualifies crash-consistency via synthetic abort-after-stage and process interruption testing. True physical power-loss qualification (e.g. `sync_data` durability under OS crash) is formally assigned to **Gate 9D**.

---

## 5. Transition Authorization: Entry to Gates 9B & 9C

With the formal ratification of Gate 9A:

1. **Working Tree Integration:** The 37-file implementation candidate identified in `receipts/gate9a_article_evidence_20260922/source-manifest.sha256`, together with the reviewer artifacts listed in the evidence manifest, is recommended for commit and merge to `main` on explicit operator instruction.
2. **Gate 9B (Packaging & CLI Compatibility):** The team is authorized to construct the packaged distribution shell, CLI command surfaces, and compatibility wrappers under the terms of PEB-15 §8.2.
3. **Gate 9C (Cognitive Field Recovery & Model Requalification):** The team is authorized to activate model-dependent projection engines, cache garbage collection, and de-novo cognitive field experiments.

*Ratified on behalf of the WhiteMagic Gen3 Project, 2026-09-22.*

**Lucas** — Project Operator & Authority (ratified 2026-09-22)  
**Antigravity** — Independent Verification Lead  
**Opencode / Sol / Terra** — Substrate & Verification Ensemble  
**Corrections applied:** opencode, 2026-09-22 (`receipts/GATE_9A_VERDICT_CROSSCHECK_2026-09-22.md`)  
