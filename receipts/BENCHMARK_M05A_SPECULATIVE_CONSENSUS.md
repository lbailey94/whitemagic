# BENCHMARK RECEIPT: MILESTONE 5A (SPECULATIVE CONSENSUS & ATTENTION SPOTLIGHT)
**WhiteMagic Gen3 Cognitive Runtime**

- **Date:** 2026-09-22 16:10:33 UTC
- **Benchmark Suite:** PEB-9 (Speculative Consensus, Jev Decision Model & Global Workspace Spotlight)
- **Status:** SEALED & RATIFIED
- **Host Hardware:** Intel(R) Core(TM) i5-8350U CPU @ 1.70GHz, 8 vCPUs, 16GB RAM, Linux x86_64
- **Toolchain:** Rustc 1.98.0 / Cargo 1.98.0
- **Parent Specifications:**
  - [`docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md`](file:///home/lucas/Desktop/WMgen3/docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md) §5.7, §6 PEB-9
  - [`crates/wm-gen3-core/src/bicameral.rs`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/bicameral.rs)

---

## 1. Executive Summary & Epistemic Breakthrough

Milestone 5A formalizes the bicameral and tricameral cognitive architecture of WhiteMagic Gen3, integrating non-autoregressive Decision Models (inspired by Jev / System 1 evaluators) between generative divergence (Chamber alpha) and formal Catuskoti verification (Chamber gamma):

$$ \text{Perceive} \longrightarrow \text{Chamber } \alpha \text{ (Generate)} \longrightarrow \boxed{\text{Chamber } \beta \text{ (Jev Decision Model)}} \longrightarrow \text{Corpus Callosum} \longrightarrow \text{Chamber } \gamma \text{ (Verify)} \longrightarrow \text{Commit} $$

### Key Architectural Resolutions:
1. **Decision Models Hold Zero Commit Capability:**
   Chamber beta (Jev) outputs purely typed scalar perturbations (Delta field: Noul P, Choice categorical, Score ordinal), operating in non-autoregressive parallel mode. It holds **no write/commit tokens**. Exclusive commit authority remains strictly with the constitutional verifier.
2. **Elimination of Unsafe Commits via Independent Semantic Risk Modeling:**
   Under Arm A (Pure Bicameral: Generator -> Verifier without Decision Model), uncalibrated generator self-confidence permitted **100 / 500 (20.0%) unsafe commits** when high-risk destructive operations were disguised as routine maintenance.
   Under Arm B and Arm C, the independent Jev AST risk classifier detected semantic hazards, driving composite margin down and enforcing formal deliberative verification: **STRICT ZERO (0) UNSAFE COMMITS**.
3. **Corpus Callosum Fast-Path Gating Invariant:**
   Reflexive fast-path execution is authorized strictly when:
   $$ \text{Margin } M = 0.40 \cdot U + 0.35 \cdot P + 0.25 \cdot R_{\text{rev}} - 0.50 \cdot R_{\text{risk}} \ge 0.85 \quad \land \quad R_{\text{risk}} \le 0.10 \quad \land \quad \text{Status} = K_1 (\text{Affirmed}) $$
   Dialectical Contradictions (K3) and Category Errors (K0) are **unconditionally barred** from fast-path bypass, regardless of confidence.
4. **Concurrent Co-Op Latency Advantage (Arm C):**
   By executing Generator proposal synthesis and Jev Decision Model evaluation concurrently, Arm C achieves identical safety to Arm B (0 unsafe commits) while reducing fast-path latency from **295.0 ns to 255.0 ns (13.6% reduction)** and deliberative latency from **675.0 ns to 635.0 ns**.
5. **Workspace Spotlight Attention Dynamics:**
   A continuous salience field sweeps across the 8 emergent attractor basins (A1..A8), governed by exponential half-life decay ($0.5^{\Delta t / 5.0}$). High-salience stimuli ($S > 0.80$) achieved **50 / 50 (100.0%) immediate interruptive preemption**.

---

## 2. Three-Arm Experimental Telemetry Audit ($N=500$ Trials)

| Experimental Arm | Architecture Pipeline | Fast-Path Commits | Deliberative Verifications | Refusal & Escalations | Unsafe Commits | Fast Latency | Delib Latency |
|---|---|---|---|---|---|---|---|
| **Arm A** | Pure Bicameral (Gen -> Verifier) | 200 | 100 | 200 | **100 (20.0% FAILS)** | 250.0 ns | 630.0 ns |
| **Arm B** | Tricameral Serial (Gen -> Jev -> Verifier) | 100 | 200 | 200 | **0 (STRICT ZERO)** | 295.0 ns | 675.0 ns |
| **Arm C** | Concurrent Co-Op (Gen + Jev -> Callosum) | 100 | 200 | 200 | **0 (STRICT ZERO)** | **255.0 ns** | **635.0 ns** |

### Probabilistic Calibration (Chamber beta Jev):
- **Brier Score (Arm B):** **0.1715** (Well below uninformative prior ceiling of 0.25).
- **Topological Transition Modeling:** Evaluated on {0, 1}^3 Bagua hypercube across 8 emergent basins, penalizing transitions by Hamming distance.

---

## 3. Global Workspace Attention Spotlight Telemetry

- **Basin Count:** 8 Emergent Basins (A1..A8)
- **Salience Half-Life:** tau = 5.0 cognitive steps
- **Preemption Threshold:** Salience >= 0.80
- **Preemption Audit:** **50 / 50 (100.0%)** interruptive preemption events successfully triggered.

---

## 4. Statutory Invariants & Ratification

1. **Law 8: The Non-Autoregressive Decision Law:**
   *Decision models evaluate comparative field utility without commit authority. Fast-path reflex is a privilege granted by the Corpus Callosum under strict epistemic warrant, never an inherent capability of generative models.*
2. **Closure Invariant Intact:**
   Zero unsafe commits admitted to germline or state under Tricameral governance.
3. **Next Phase:**
   Proceed to Milestone 5B: Declarative Pulse Compilation & Zero-DAG Substrate.
