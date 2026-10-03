# WhiteMagic Gen3 — Benchmark & Verification Protocol
**Document Version:** 1.0.0 · **Baseline Pinned:** Gen3 Cognitive Runtime Baseline 1 (`G3-CRB-1`)  
**Date:** 2026-09-18 · **Session:** `221fbb57-905f-4e7d-a4d3-3c11810ea0b7`  
**Governing Charters:** Design Canon §7/§13, Part 1 Constitutional Invariants, Wave Plan §2

---

## 1. Executive Summary & Objective

This document defines the comprehensive testing, stress, and benchmarking protocol for WhiteMagic Gen3 following the complete ratification of Wave 1 (A1–A3, B1–B5) and foundational Wave 2 (W2_01–W2_04, W2_07).

With the outer envelope sealed, Gen3 constitutes a **Minimal Cognitive Runtime**. Prior to introducing higher-order orchestration layers (W2_05: Recipe Layer) or recursive mechanisms (W2_06: Recursive Self-Improvement), the system must be rigorously evaluated across six systematic layers. The central question is not merely *"does each subsystem survive load?"* but:

> **Does the entire cognitive runtime continue obeying its constitutional laws when stressed in ways nobody explicitly designed for?**

Every experiment in this campaign compares against a frozen reference organism: **Gen3 Cognitive Runtime Baseline 1 (`G3-CRB-1`)**.

---

## 2. Frozen Baseline Reference: `G3-CRB-1`

| Dimension | Specification / Value |
|---|---|
| **Baseline Identifier** | `G3-CRB-1` (Gen3 Cognitive Runtime Baseline 1) |
| **Commit Tip** | `3483382d5545267c1fdad6f8d9d8806a5042bbed` (`main`, clean tree) |
| **Compiler / Toolchain** | `rustc 1.98.0 (88d9e12ae 2026-08-18)` / `cargo 1.98.0 (797e8a9bc 2026-08-05)` |
| **Gen3 Core Binary** | `target/release/wm-gen3` |
| **Gen3 Binary Hash** | `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44` |
| **Host Tool Hash** | `target/release/wm` (v9.1.9, sha256 `e2be764ffe1ec2e514fce5c74b6d521f8082643720b70c44a934cf1283ec6970`) |
| **Ratified Rows** | **Wave 1**: A1, A2, A3, B1, B2, B3, B4, B5<br>**Wave 2**: W2_01, W2_02, W2_03, W2_04, W2_07 |
| **Gated Rows** | **W2_05** (Recipe Layer: gated on empirical expressibility)<br>**W2_06** (RSI: gated on counterfactual replay & four-way role separation) |
| **Underlying Stores** | LMDB (`data.mdb`, `lock.mdb`), Tantivy index directories, Git common-dir lease ledger |

---

## 3. The Six-Layer Verification Architecture

```
                                 ▲
                     [ Layer 6: Emergent Expressibility ]
                     What can the substrate do without bloat?
                                 │
                     [ Layer 5: Epistemic Quality ]
                     Does the system remain useful over time?
                                 │
                     [ Layer 4: Scale & Duration ]
                     Resource slopes & long-horizon soak
                                 │
                     [ Layer 3: Crash & Contention ]
                     SIGKILL, full disk, multi-writer collisions
                                 │
                     [ Layer 2: Replay & Determinism ]
                     Bitwise & behavioral historical invariance
                                 │
                     [ Layer 1: Constitutional Invariants ]
                     Non-negotiable laws of Gen3 physics
                                 ┴
```

### Layer 1: Constitutional Invariants (The Laws of Physics)
*Objective*: Assert foundational invariants across all operations and compositions.
1. **`records ≠ relations` (Part 1 Invariant 9)**: No relation mutation or deletion can modify or erase an underlying evidence record.
2. **`belief ≠ evidence` (Part 1 Invariant 9)**: Epistemic predictions (`claims`) remain distinct from immutable sensory history (`records`).
3. **`read paths never mutate`**: Calls to `check`, `list`, `inspect`, and `recall` must leave the store, index, and lease ledger byte-identical (0 writes, 0 tmp files).
4. **`valid release never policy-blocked`**: Capability admission must never deny an exact-owner lease relinquishment (`Resource::CoordinationRelease`).
5. **`views ≠ authorization`**: Provenance scopes and recall views filter visible candidate subsets without serving as access-control barriers.
6. **`consolidation ≠ deletion`**: Dreaming and demotion de-activate relations without deleting historical evidence records.

### Layer 2: Replay & Determinism (Temporal Invariance)
*Objective*: Guarantee that identical histories yield identical cognitive states.
1. **Target-Local Bitwise Determinism**: On the same CPU architecture and compiler profile, reductions and scoring must reproduce bit-identically (**0 ULP**).
2. **Cross-Architecture Behavioral Determinism**: Across differing CPU architectures (e.g. x86_64 vs aarch64) or toolchains, the portable invariant guarantees identical rankings, tie-breaks, strata transitions, and decision event streams, even if intermediate f32 representations vary by $\le 1$ ULP.
3. **Lossless Session Replay**: `session.export` $\rightarrow$ `session.import` preserves IDs, timestamps, and tags exactly; superseded turns are omitted by default and lossless on explicit request.

### Layer 3: Crash & Contention (Engineering Resilience)
*Objective*: Verify systemic integrity under hostile operating conditions.
1. **Multi-Process Contention**: Concurrent workers attempting to claim, refresh, inspect, and release overlapping scopes at millisecond intervals must never produce split-brain ownership or JSON corruption.
2. **Ungraceful Termination (`SIGKILL`)**: Hard kills during active lease holding, write-through claim mutations, or LMDB commit phases must leave stores readable and uncorrupted.
3. **Stale Lease Reclamation**: Expired leases must be cleanly reclaimable by subsequent workers without manual ledger intervention.
4. **Storage Exhaustion**: Simulated out-of-disk conditions must fail closed cleanly without silent truncation.

### Layer 4: Scale & Duration (Resource Slopes)
*Objective*: Profile growth curves to detect super-linear degradation before it impacts production.
1. **Slope Profiling**: Measure the first derivative of performance across store sizes ($10^3 \rightarrow 10^4 \rightarrow 10^5 \rightarrow 10^6$ records):
   $$\text{Slope} = \frac{\Delta \text{Metric}}{\Delta \log_{10}(N)}$$
   Metrics evaluated: Query Latency, RAM Footprint, Disk Amplification, Index Size, Consolidation Duration.
2. **Long-Horizon Soak**: 1,000 continuous simulated agent sessions with incremental turn ingestion, verifying zero memory leaks and zero Tantivy index drift.

### Layer 5: Epistemic Quality (Cognitive Utility)
*Objective*: Ensure that accumulated memory increases discernment rather than creating noise.
1. **Semantic Sediment Ratio ($R_{sed}$)**: Measure the ratio of relevant accepted decisions to obsolete/superseded context retrieved over long-lived projects:
   $$R_{sed} = \frac{|\text{Relevant Current Evidence Retained}|}{|\text{Obsolete / Superseded Evidence Injected}|}$$
2. **Contradiction & Shifting-Fact Recovery**: Timelines with deliberately mutating facts (e.g., architecture migrations, scoped exceptions) evaluated for:
   - Historical accuracy (*what was true at epoch $T$?*)
   - Currentness accuracy (*what is true now?*)
   - Scoped accuracy (*does the exception apply to Gen2 or Gen3?*)
   - Stale intrusion rate (*frequency of superseded context contaminating modern answers*)
3. **Adversarial Calibration Regimes**: Sweep empirical-Bayes prior sample weight $k \in \{0, 1, 5, 10, 20, 50, 100\}$ across diverse forecaster archetypes (constant 0.51, extreme 0.01/0.99, sudden degradation, domain-specific miscalibration, selective prediction refusal).

### Layer 6: Emergent Expressibility & The Recipe Challenge
*Objective*: Establish whether an additional orchestration layer (W2_05) is strictly necessary, or whether existing primitives already provide sufficient expressibility.
1. **Workflow A (Multi-Step Defect Diagnosis)**: Hypothesis generation $\rightarrow$ test failure reproduction $\rightarrow$ patch synthesis $\rightarrow$ test verification $\rightarrow$ session handoff.
2. **Workflow B (Distributed Multi-Agent Handoff)**: Atomic lease negotiation $\rightarrow$ scope occupancy $\rightarrow$ work execution $\rightarrow$ continuity receipt generation $\rightarrow$ exact-owner release $\rightarrow$ successor resumption.
3. **Workflow C (Epistemic Hypothesis Loop)**: Predictive claim registration $\rightarrow$ empirical experimentation $\rightarrow$ validation event recording $\rightarrow$ statutory Brier updating without memory rewriting.
4. **Workflow D (The Intentionally Awful Workflow)**: Mid-flight requirements shift $\rightarrow$ agent crash (`SIGKILL`) $\rightarrow$ lease expiration $\rightarrow$ hypothesis falsification $\rightarrow$ successor wake-up $\rightarrow$ superseded design resurfacing $\rightarrow$ recovery and successful completion.
5. **Ecological Blind Benchmark**: Qualitative comparative review of complex task execution:
   - Agent Group A: WhiteMagic Gen3 Minimal Cognitive Runtime
   - Agent Group B: Raw LLM context window + unstructured files
   - Agent Group C: WhiteMagic Gen2
   Metrics: Repeated questions, context reconstruction speed, stale decision intrusion, tool calls, token usage, wall-clock time.

---

## 4. Specialized Test Harness Specifications

### 4.1 The Constitutional Fuzzing Harness
Unlike traditional fuzzing that tests for memory panics, Constitutional Fuzzing generates random, legal sequences of high-level operations:
$$\text{remember} \longrightarrow \text{revise} \longrightarrow \text{supersede} \longrightarrow \text{recall} \longrightarrow \text{consolidate} \longrightarrow \text{inspect} \longrightarrow \text{checkpoint} \longrightarrow \text{restart} \longrightarrow \text{recall}$$
$$\text{claim} \longrightarrow \text{lease} \longrightarrow \text{session handoff} \longrightarrow \text{release} \longrightarrow \text{falsify} \longrightarrow \text{consolidate} \longrightarrow \text{import}$$
*Invariants Asserted at Every Iteration*:
- Original record payload bytes remain unchanged.
- Journal hash links remain intact.
- Read operations cause 0 disk mutations.
- Superseded data remains accessible via `include_superseded: true`.
- Claims never mutate into evidence records.
- Relation transitions never delete referenced entity records.
- Successful mutations survive process restart.

### 4.2 The Metamorphic Test Harness
Metamorphic testing verifies properties where input transformations must not alter expected outputs:
- **Scope Independence**: Inserting unrelated memories with disjoint tags must not alter top-K recall for an existing scoped query (beyond declared crowd-out boundaries).
- **Insertion Invariance**: Permuting the insertion order of records into LMDB must produce bit-identical ranking and scores.
- **Restart Transparency**: Restarting the process between every single operation must yield a final state identical to continuous uninterrupted execution.
- **Relation Invariance**: Adding a `Cold` relation between two records must not alter active supersession strata.

### 4.3 The Counterfactual Replay Harness (Maker ≠ Checker for RSI)
The foundation of Recursive Self-Improvement (W2_06). Takes an immutable event journal $\mathcal{J}$ from history and replays it under two implementations:
$$\Delta(\text{Baseline } A, \text{Candidate } B) \Longrightarrow \{\Delta \text{Ranking}, \Delta \text{Strata}, \Delta \text{Relations}, \Delta \text{Claims}, \Delta \text{Resource Cost}\}$$
This harness guarantees that any proposed self-modification must prove its claimed benefit over thousands of historical situations before being submitted to the constitutional authority for deployment.

### 4.4 The Adversarial Time Harness
Simulates temporal anomalies without relying on trusting the system clock:
- System clock jumps backward by 1 hour.
- System clock jumps forward by 24 hours.
- High-frequency burst resulting in identical timestamps.
- Millisecond collisions across concurrent workers.
- Lease expiry exactly on the evaluation boundary.
- Claim validation date predating claim creation date.
*Invariant*: The system must resolve sequence and causality by explicit causal graph structure and journal ordering, never blind wall-clock comparison.

### 4.5 The Zero-Hidden-State Boundary Map
Identical inputs to identical binaries across clean environments must produce identical outputs. Any deviation exposes hidden state:
- Environment variables (`PATH`, `LANG`, `HOME`, etc.)
- Process ID (`PID`) and thread scheduling
- Working directory (`CWD`)
- Filesystem enumeration non-determinism
- Random number generator seeds
The harness constructs a definitive **Causal Boundary Map** listing every environmental factor capable of influencing cognition.

---

## 5. Execution Phasing & Scheduling

The benchmark campaign executes in the following strict order:

| Phase | Suite Name | Primary Focus | Failure Risk Addressed |
|---|---|---|---|
| **Phase 1** | **B3 Contention & Concurrency** | Multi-process leases, collisions, releases | Split-brain scope ownership |
| **Phase 2** | **B2 Long-Horizon Continuity** | Multi-session replay, compaction, drift | State amnesia / context hallucination |
| **Phase 3** | **Constitutional Fuzzing & Metamorphic** | Multi-op compositions, invariant preservation | Emergent composition bugs |
| **Phase 4** | **B4 Calibration & Adversarial Epistemics** | $k$-sweep, adversarial forecasters | Epistemic self-deception / overconfidence |
| **Phase 5** | **Scale Slopes & Semantic Sediment** | $10^3 \dots 10^5$ scaling, $R_{sed}$ ratio | Memory drowning / quadratic slowdown |
| **Phase 6** | **Recipe Expressibility (Workflows A–D)** | Autonomous task execution without W2_05 | Premature / unearned orchestration bloat |
| **Phase 7** | **Counterfactual Replay Harness** | History replay baseline vs candidate | Unverified self-modification (W2_06 gate) |

---

## 6. Attestation & Governance

This protocol is ratified as the binding benchmark framework for `G3-CRB-1`. No row exits for W2_05 or W2_06 may be claimed until the respective phases in this protocol have generated verified, immutable SHA256 receipts.
