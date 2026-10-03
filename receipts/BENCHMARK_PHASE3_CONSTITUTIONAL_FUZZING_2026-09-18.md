# RECEIPT — Benchmark Phase 3: Constitutional Fuzzing & Metamorphic Testing (2026-09-18)

**Status: VERIFIED & DEMONSTRATED — 2026-09-18.** Executed per `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` Phase 3 against baseline `G3-CRB-1`. AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Append-only; corrections create a new receipt referencing this one.

---

## 1. Benchmark Execution Parameters

| Parameter | Value |
|---|---|
| **Benchmark Driver** | `benchmarks/driver_phase3_constitutional_fuzzing.py` |
| **Target Binary** | `target/release/wm-gen3` (Exact baseline hash: `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| **Execution Protocol** | Stdio JSON-RPC over minimal substrate |
| **Metamorphic Battery** | 3 independent metamorphic invariance test suites |
| **Constitutional Fuzzing** | 100 pseudo-random composite operation cycles with unbroken journal validation |
| **Wall-Clock Duration** | 4.14 seconds |
| **Outcome** | 4/4 suites PASS (0 failed, 0 invariant violations) |

---

## 2. Invariant Verification Index

| Test Case | Invariant Evaluated | Empirical Result |
|---|---|---|
| `test_metamorphic_scope_independence` | **Scope View Independence (B5)**: Inserting 50 unrelated items under `scope_b` must not alter top recall results or scores under `scope_a`. | **PASS**: Top-5 results, item IDs, content, and scores under `scope_a` were bit-identical before and after bulk insertion into disjoint scope. |
| `test_metamorphic_insertion_order_invariance` | **Order-Fixed Determinism**: Ingesting records in forward order vs randomly permuted order. | **PASS**: Recall rankings, items, and scores matched to $10^{-5}$ across both stores. |
| `test_metamorphic_restart_transparency` | **Process Restart Invariance**: Ingesting 8 records continuously vs restarting process after every single addition. | **PASS**: Identical final cognitive state and recall results across both continuous and restarted processes. |
| `test_constitutional_fuzzing_suite` | **Multi-Op Composition Law Preservation**: 100 randomly interleaved cycles of `remember`, `recall`, `think`, `inspect`, `readonly_verify`, and `restart`. | **PASS**: Read-only operations caused 0 mutations; read-only mode refused writes fail-closed; journal hash chain remained continuous across all operations. |

---

## 3. Findings & Engineering Disclosures

1. **Strict Provenance Scoping**:
   Scope views filter candidates by exact `<label>` within `corpus:<label>:<tags>`, confirming that provenance tags act strictly as request-time recall filters without polluting global indices.
2. **Read-Only Fail-Closed Discipline**:
   Substrates opened with `--readonly` executed reads cleanly while rejecting write routes (`memory.batch_create`) with explicit typed refusals (`status: error, route: <route>, error: read-only mode: write route refused`).
3. **Continuous Cryptographic Journaling**:
   Across 100 randomized operations including process restarts, every mutation generated an append-only journal record preserving strict hash linkage.

---

## 4. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `benchmarks/driver_phase3_constitutional_fuzzing.py`, verified all 3 metamorphic invariants and 100-cycle constitutional fuzzing, and recorded this receipt.
No verdict, claim, gate, or threshold movement; WEAK stays WEAK.
