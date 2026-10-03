# MILESTONE-0 EXECUTION MANIFEST & PREREGISTRATION PROTOCOL
**Substrate Minimality & Epistemic Foundations**  
**WhiteMagic Gen3 Cognitive Runtime**

- **Date:** 2026-09-18
- **Status:** SEALED & RATIFIED
- **Baseline Git Tag:** `g3-crb-1`
- **Baseline Git Commit:** `9cb109404c0ec54181f0bdf20067644917fa9f34`
- **Compiler Toolchain:** `rustc 1.98.0 (88d9e12ae 2026-08-18)` / `cargo 1.98.0 (797e8a9bc 2026-08-05)`
- **Host Hardware:** Intel(R) Core(TM) i5-8350U CPU @ 1.70GHz, 8 vCPUs, 16GB RAM
- **Operating System:** Linux T4800-S 7.0.0-31-generic #31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC x86_64
- **Parent Specification:** [`docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md`](file:///home/lucas/Desktop/WMgen3/docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md) (v1.2)

---

## 1. Executive Summary & Purpose

Before executing any benchmark suite or introducing new cognitive phenotypes, WhiteMagic Gen3 requires that the foundational execution substrate be empirically tested for **minimality and irreducibility**.

The candidate foundational execution pulse is:
$$\mathbf{Select} \longrightarrow \mathbf{Transform} \longrightarrow \mathbf{Evaluate} \longrightarrow \mathbf{Commit}$$

This manifest preregisters the protocol for **PEB-0 (Primitive Minimality Benchmark)** and **PEB-1 (The Four Corners Challenge)**. It formalizes:
1. The exact reduction attacks against the candidate 4-beat pulse.
2. The rigorous definition of **Observational Equivalence** and the **Protected Metric Invariant Set ($M_{\text{protected}}$)**.
3. The frozen test corpus ($N=1000$ trials across standard, boundary, and adversarial fixtures).
4. Explicit, non-negotiable decision boundaries (`PASS`, `REDUCTION_DISCOVERED`, `INCONCLUSIVE`).
5. The strict sequential execution invariant:
   $$\boxed{\text{Seal Manifest} \longrightarrow \text{Execute PEB-0} \longrightarrow \text{Interpret Result} \longrightarrow \text{Freeze Substrate} \longrightarrow \text{Implement PEB-1}}$$

---

## 2. PEB-0: Candidate Reduction Attacks

The candidate four-beat pulse posits that every state transition in the cognitive runtime decomposes into four sequential phases:
- **Select:** Filters the active working set $S_t$ from the substrate $\mathcal{X}$.
- **Transform:** Pure functional generation $f(S_t, \theta) \to \mathcal{C}_t$ of candidate records, relations, or texts.
- **Evaluate:** Constitutional verification, Pareto admissibility, and calibration scoring $g(\mathcal{C}_t, \text{Law}) \to \mathcal{C}^*_t$.
- **Commit:** Atomic durable persistence to LMDB, journal ratcheting, and irreversible history inscription.

To falsify or confirm irreducibility, the runtime subjects this pulse to three formal attacks plus one structural factorization analysis:

### Attack 1: Ablation (Delete Evaluate)
$$\mathbf{Select} \longrightarrow \mathbf{Transform} \longrightarrow \mathbf{Commit}$$
- **Hypothesis:** Evaluate is superfluous; Transform outputs can be committed directly to durable storage.
- **Implementation:** Bypass constitutional filters, evidence verification (Closure 2), noise rejection, and write-budget accounting. Candidate items pass directly from generation to LMDB write and journal ratcheting.
- **Evaluated Failure Mode:** Injection of noise, ungrounded assertions, cyclical supersessions, and write-budget overruns.

### Attack 2: Merger (Constrained Transform)
$$\mathbf{Select} \longrightarrow [\mathbf{Transform} + \mathbf{Evaluate}] \longrightarrow \mathbf{Commit}$$
- **Hypothesis:** Evaluate does not need to exist as an independent stage; Transform can be constrained to generate *only* constitutionally valid candidates.
- **Implementation:** Internalize constitutional validation into the transform function. The generator cannot emit an invalid proposal.
- **Evaluated Questions:**
  - Can generation and multi-objective verification be merged without computational blowup or conflating epistemic exploration with admissibility?
  - Does merger violate the verification asymmetry ($P \neq NP$ cognitive principle: generating hypotheses is fundamentally different from verifying them against immutable invariants)?

### Attack 3: Substitution (Generalized Constrained Mapping)
$$[\mathbf{Select} + \mathbf{Transform}] \longrightarrow \mathbf{Evaluate} \longrightarrow \mathbf{Commit}$$
- **Hypothesis:** Explicit selection of an active working set $S_t$ is unnecessary; a single generalized mapping over the entire substrate $\mathcal{X}$ can generate candidates, followed by evaluation and commit.
- **Implementation:** Remove working set bounds; transform operates over unbounded substrate scope.
- **Evaluated Failure Mode:** Complexity scaling ($\mathcal{O}(|\mathcal{X}|^2)$), inability to maintain attentional focus or context window constraints, unbounded pair budgets.

### Attack 4: Asymmetric $(3 \mid 1)$ Factorization
$$[\mathbf{Select} \longrightarrow \mathbf{Transform} \longrightarrow \mathbf{Evaluate}] \quad\Big|\quad \mathbf{Commit}$$
- **Hypothesis:** The candidate four beats factor naturally into two categorically distinct epistemic regimes:
  1. **Reversible Epistemic Possibility ($3$ beats):** $\text{Select} \to \text{Transform} \to \text{Evaluate}$ operates purely in volatile memory, exploring counterfactuals and speculative candidates with zero physical side-effects.
  2. **Irreversible Historical Ratchet ($1$ beat):** $\text{Commit}$ bridges epistemic possibility into physical reality, enforcing atomic LMDB persistence, monotonic journal ratchet, and unchangeable history.
- **Evaluated Outcome:** If the $3+1$ factorization preserves 100% observational equivalence while clarifying rollback boundaries, WhiteMagic will adopt this architectural distinction.

---

## 3. Observational Equivalence & Protected Invariants ($M_{\text{protected}}$)

An alternative algebra (whether 3-beat, 2-beat, or asymmetric 3+1) is said to **preserve all invariants** if and only if it demonstrates **Observational Equivalence across a frozen test corpus**.

Observational equivalence requires:
1. **Identical Constitutional Outcomes:** Zero unhandled invariant breaches; 100% rejection of ungrounded or contradictory evidence.
2. **Identical Externally Visible State Transitions:** Exact match on query returns, revision links, and relation topologies across all trials.
3. **Identical Durability/Rollback Guarantees:** Any rejected candidate leaves zero residue in the journal or store.
4. **Zero Statistically Meaningful Regression in $M_{\text{protected}}$:**

### Protected Metric Set ($M_{\text{protected}}$):
| Metric | Name | Definition | Acceptable Threshold |
|---|---|---|---|
| $m_1$ | **Constitutional Violation Rate** | Proportion of committed transitions violating Closure 1, Closure 2, or Tier-1 invariants. | $\equiv 0.0000\%$ ($0$ violations across $N$) |
| $m_2$ | **Rollback / Abortion Integrity** | Clean state recovery upon transform rejection (zero memory leak, zero journal pollution). | $\equiv 100.00\%$ ($0$ lingering residues) |
| $m_3$ | **Epistemic Calibration (Brier Loss)** | Calibration of claims and confidence scores under statutory shrinkage. | $\Delta \text{Brier} \le 0.0000$ (no loss of accuracy) |
| $m_4$ | **Deterministic Replay** | Bitwise identity of store state and journal hashes across replay runs. | $0\text{ ULP}$ / Bitwise Identical |
| $m_5$ | **Resource & Execution Containment** | Wall-clock latency and memory allocation bounds under stress. | $\Delta t_{\text{exec}} \le 1.10\times$ baseline |

---

## 4. Test Fixtures, Seeds & Corpus Structure

The benchmark evaluates $N = 1000$ trials generated deterministically via PRNG seed `0xDEADBEEF42C0FFEE`:
1. **Standard Ingest & Recall Fixtures ($400$ items):**
   - Well-formed evidence records across reported, system, and simulated kinds.
   - Lexical and semantic recall queries with ground-truth targets.
2. **Boundary & Stress Fixtures ($300$ items):**
   - Rapid-fire revisions, exact duplicate collisions, superseded chain updates.
   - High-concurrency read/write operations under tight pair budgets.
3. **Adversarial Invariant Probes ($300$ items):**
   - Noise injection: raw hex garbage, empty payloads, malformed unicode.
   - Self-referential loop attacks: records attempting to supersede themselves or create closed causal cycles ($A \to B \to A$).
   - Ungrounded evidence injection: simulated records masquerading as verified evidence without provenance.
   - Budget exhaustion: burst writes exceeding statutory limits.

---

## 5. Explicit Decision Thresholds

| Outcome | Criteria | Architectural Consequence |
|---|---|---|
| **PASS (Irreducibility Confirmed)** | Candidate reductions 1, 2, and 3 fail on at least one invariant in $M_{\text{protected}}$ ($p < 0.01$); candidate 4 is ratified as the structural $(3 \mid 1)$ factorization of the canonical 4 beats. | The 4-beat pulse is declared minimal and irreducible. Substrate frozen as canonical. |
| **REDUCTION DISCOVERED** | A simpler candidate (e.g. 3-beat or 2-beat) achieves **100% Observational Equivalence** across all $1000$ trials with $\Delta M_{\text{protected}} \ge 0$. | WhiteMagic celebrates the reduction; the candidate algebra replaces the 4-beat model. |
| **INCONCLUSIVE** | Borderline statistical separation ($0.01 \le p < 0.05$), non-deterministic test failures, or external host interference. | Benchmark halts; fixtures synthesized for an additional $N=5000$ adversarial trials. |

---

## 6. Ratification & Execution Gate

This manifest is signed and sealed prior to test execution. No test results may alter the preregistered criteria.

- **Attesting Agent:** Session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity AI)
- **Operator Authorization:** Lucas Bailey
- **Next Action:** Execute PEB-0 suite in `crates/wm-gen3-harness` and `benchmarks/driver_peb0_primitive_minimality.py`.
