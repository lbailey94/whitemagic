# RECEIPT — Benchmark Phase 1: B3 Concurrency & Lease Stress (2026-09-18)

**Status: VERIFIED & DEMONSTRATED — 2026-09-18.** Executed per `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` Phase 1 against baseline `G3-CRB-1`. AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Append-only; corrections create a new receipt referencing this one.

---

## 1. Benchmark Execution Parameters

| Parameter | Value |
|---|---|
| **Benchmark Suite** | `crates/wm-tools/tests/coordination_stress.rs` |
| **Driver Script** | `benchmarks/driver_phase1_b3_stress.py` |
| **Target Baseline** | `G3-CRB-1` (Commit `60b3439`, Core hash `a5ec583b…`) |
| **Concurrency Level** | 50 concurrent tokio worker tasks (8 worker threads) |
| **Execution Mode** | Multi-threaded asynchronous execution with barrier synchronization |
| **Wall-Clock Duration** | 76.61 seconds |
| **Outcome** | 4/4 suites PASS (0 failed, 0 warnings, 0 torn reads, 0 leaks) |

---

## 2. Invariant Verification Index

| Test Case | Invariant Evaluated | Empirical Result |
|---|---|---|
| `test_50_tasks_competing_for_single_scope_zero_split_brain` | **Zero Split-Brain Ownership**: 50 concurrent tasks compete for identical scope `crates/core/hot_path.rs`. | **PASS**: Exactly 1 task acquired `status: success`; exactly 49 tasks received `status: conflict` naming `holder` + mandatory `holder_intent`. Store verified consistent. |
| `test_50_tasks_disjoint_scopes_no_lost_updates` | **Zero Lost Updates & Clean Relinquishment**: 50 concurrent tasks claim disjoint scopes `crates/module_XXX/file.rs`, then concurrently release. | **PASS**: All 50 claims succeeded (`active_count = 50`). All 50 concurrent exact-owner releases succeeded (`state: released`). Final active count = 0. |
| `test_snapshot_readonly_immunity_under_heavy_write_churn` | **Snapshot Read-Only Immunity**: 10 writer tasks continuously claim/release while 10 reader tasks continuously check/list scopes. | **PASS**: Readers executed 100% unblocked; 0 torn reads; 0 lockfile leaks; 0 temp files generated. |
| `test_stale_lockfile_recovery_steals_and_succeeds` | **Stale Lock Reclamation**: Lockfile older than `STALE_LOCK_SECS` (30s) simulated via timestamp back-dating. | **PASS**: Stale lock detected, atomically stolen, claim succeeded without operator intervention, lockfile cleaned up. |

---

## 3. Findings & Engineering Disclosures

1. **Release State Precision**:
   `code.release` returns `"state": "released"` on active lease removal and `"state": "free"` only when no active claim exists. The stress harness strictly asserts this distinction.
2. **Lock Contention Bounds**:
   Under 50 simultaneous competing writers, lock retry backoff ($150 \times 10\text{ms} = 1500\text{ms}$) proved sufficient to arbitrate 100% of claims and releases without timing out or wedging.
3. **Pure Filesystem Integrity**:
   Across hundreds of concurrent file mutations and checks, zero temporary files or orphaned lockfiles lingered on disk.

---

## 4. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `benchmarks/driver_phase1_b3_stress.py`, verified all 4 stress suites, confirmed zero split-brain and zero lost updates, and recorded this receipt.
No verdict, claim, gate, or threshold movement; WEAK stays WEAK.
