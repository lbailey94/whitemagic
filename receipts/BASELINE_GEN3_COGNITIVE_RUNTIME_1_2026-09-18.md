# RECEIPT — Gen3 Cognitive Runtime Baseline 1 (`G3-CRB-1`) Freeze (2026-09-18)

**Status: FROZEN & RATIFIED — 2026-09-18.** Operator ratified in session; the baseline freeze is in effect and gates all subsequent testing, benchmarking, and Phase-4 Wave-2 evaluations. AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) prepared, verified, and attests per operator directive. Append-only; corrections create a new receipt referencing this one.

---

## 1. Frozen Baseline Artifacts

| Field | Value |
|---|---|
| **Baseline Name** | **Gen3 Cognitive Runtime Baseline 1 (`G3-CRB-1`)** |
| **Commit Tip** | `3483382d5545267c1fdad6f8d9d8806a5042bbed` (`main`, clean tree) |
| **Compiler Toolchain** | `rustc 1.98.0 (88d9e12ae 2026-08-18)` / `cargo 1.98.0 (797e8a9bc 2026-08-05)` |
| **Gen3 Core Binary** | `target/release/wm-gen3` |
| **Gen3 Core Binary Hash** | `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44` |
| **Host Tool Binary** | `WHITEMAGIC/WMv9/target/release/wm` (v9.1.9) |
| **Host Tool Binary Hash** | `e2be764ffe1ec2e514fce5c74b6d521f8082643720b70c44a934cf1283ec6970` |
| **Benchmark Protocol** | `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` (Version 1.0.0) |
| **Live MCP Scope** | `wmv9` (`session_id: 221fbb57-905f-4e7d-a4d3-3c11810ea0b7`, checkpoint `2118bb64…`) |

---

## 2. Operator Act — RECORDED

| Field | Value |
|---|---|
| **Operator** | Lucas Bailey |
| **Act** | Ratification of Outer Envelope (B2, B3, B4) and Authorization of Baseline Freeze & Extensive Benchmark Campaign |
| **Directive** | "I ratify; sign them, and we'll move forward and discuss our next steps - it sounds like we need to test and benchmark extensively before further additions / refinements to the code." — Lucas Bailey (operator) — 2026-09-18 |
| **AI Attestation** | Session `221fbb57` compiled this baseline manifest, verified binary hashes, sealed outer envelope receipts, and recorded this baseline freeze per operator directive — attestation only |

---

## 3. Scope of the Ratified Substrate

The `G3-CRB-1` baseline establishes a complete **Minimal Cognitive Runtime** spanning 13 ratified rows:

### Wave 1 (Complete):
1. **A1 (Durable store ingestion)**: Append-only LMDB substrate, deduplication gates, provenance tagging.
2. **A2 (Evidence disclosure)**: Strict floor bounds, typed refusal without journal pollution, vocabulary discipline.
3. **A3 (Revisions & supersession)**: Non-destructive revision links, history preservation.
4. **B1 (Retrieval & ranking)**: Multi-field grounded scoring, BM25/Tantivy integration.
5. **B2 (Sessions & continuity)**: Temporal Identity, lossless replay (IDs, timestamps, tags), nodiscovery checkpoints, write-time indexing.
6. **B3 (Coordination & leases)**: Negotiated Occupancy, exact-owner release, snapshot read-only inspection, typed-effect asymmetry (`Resource::CoordinationRelease` policy admission guaranteed).
7. **B4 (Claims & calibration)**: Epistemic Accountability, 100% resolution completeness, statutory Brier calibration + Empirical-Bayes shrinkage ($k=20.0$), empty-data disclosure (`insufficient_data`), write-through durability.
8. **B5 (Galaxies & recall views)**: Provenance-based recall views, crowd-out prevention, 0 ULP bitwise determinism across reductions.

### Wave 2 (Foundational):
9. **W2_01 (Relations & associations)**: Field edge topology distinct from stored records.
10. **W2_02 (Retention & lifecycle)**: Constitutional invariant `records ≠ relations`; pure reads; 100% persistence.
11. **W2_03 (Currentness strata)**: Request-time strata view; uniform history; non-destructive direction.
12. **W2_04 (Dream & consolidation)**: Constitutional invariant `consolidation ≠ deletion`; A/B demotion controls.
13. **W2_07 (Self-model inspect)**: Read-only declared/observed state inspection.

### Gated Rows (Strictly Frozen):
- **W2_05 (Recipe layer)**: Frozen. Must earn its existence through empirical expressibility experiments (Protocol Phase 6).
- **W2_06 (RSI over journal)**: Frozen. Gated on the Counterfactual Replay Harness (Protocol Phase 7) and independent four-way separation (`proposer ≠ evaluator ≠ authority ≠ deployer`).

---

## 4. Verification Check

- `cargo test --workspace` passes cleanly (54 core tests, 5 doc tests).
- `bash scripts/check_closures.sh` passes cleanly (no Gen2 crates in Gen3 tree; plastic layer never references constitution mutation surface).
- Release binary hash `a5ec583b…` matches byte-identically with previous row-exit receipts.
- All subsequent experiments must cite this receipt and compare against `G3-CRB-1`.
