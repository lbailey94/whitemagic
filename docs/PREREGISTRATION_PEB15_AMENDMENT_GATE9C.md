# Pre-Registration: PEB-15 Amendment for Gate 9C — Candidacy Precision Refinement & Cognitive Re-Derivation

**Document ID:** `PEB-15-AMEND-GATE9C-v1.0`  
**Parent Document:** `PEB-15-PREREG-v1.0` (`docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`)  
**Milestone:** WhiteMagic Gen3 — Milestone 9 (Alpha Production Graduation) Gate 9C  
**Authors:** Lucas & Antigravity (with Sangha Peer Review)  
**Date:** September 24, 2026  
**Status:** PREREGISTERED & FROZEN  
**Target Crates:** `crates/wm-gen3-core`, `crates/wm-gen3-harness`  

---

## 1. Problem Statement & Motivation

During Milestone 9 Slice 1 and the P2B through P2E semantic projection research series, an acute candidacy precision anomaly was uncovered (Finding F2):
- **Slice 1 Baseline Recall:** $89.7\%$
- **Slice 1 Baseline Precision:** $1.06\%$
- **Noise Ratio:** $\sim 85$ spurious relation proposals for every 1 true contradiction or supersession pair.

Forensic analysis across the Anomaly Study (`experiments/semantic_projection/ANOMALY_STUDY.md`) and Failure Taxonomy (`experiments/semantic_projection/FAILURE_TAXONOMY.md`) identified three empirical mechanisms:
1. **The "Binary Cliff" Flaw:** A rigid scalar threshold ($\tau_{gate} = 0.694$) silenced semantic projection for legitimate paraphrased updates (cosine similarity $0.58 - 0.65$), reducing projection to an all-or-nothing cutoff.
2. **The "Single Token Trap":** Unweighted lexical overlap allowed single generic tokens (e.g. `"always"`, `"false"`, `"package"`) to trigger candidate pairs across completely disparate topics.
3. **The True Update Latent Signal:** True supersession updates maintain a $+0.28$ mean cosine advantage over cross-topic distractors ($0.75$ vs $0.47$). The semantic signal exists, but was filtered out before arbitration.

In addition, cognitive capabilities from Gen1 and Gen2 (the 28 Gana archetypes and Forgotten Diamonds) require formal re-derivation under Charter §3.10 (*"Symbols may render; symbols may never dispatch"*) and Article 4 (*Authoritative Background Loops = 0*).

---

## 2. Formal Hypotheses

### Hypothesis H9C-1: Candidacy Precision Scaling & Lexical Anchor Coherence
> *By lowering the candidate sweep cosine floor to $\tau_{sweep} = 0.50$ (capturing paraphrases) and enforcing Lexical Anchor Coherence (non-stopword Dice $\ge 0.25$ or $\ge 2$ shared rare tokens), the candidate generator will reduce total candidate pairs by $\ge 50\%$, achieve $\ge 2\times$ precision gain (Precision $\ge 2.12\%$), maintain Recall $\ge 85.0\%$, and produce exactly 0 reversed-direction relation proposals.*

### Hypothesis H9C-2: Ganas as Stateless Transform Policies (Recipes)
> *Re-deriving the Gana archetypes as stateless, immutable parameter configurations (`TransformPolicy` / `Recipe`) modifying operational lenses over `remember`, `recall`, `think`, and `inspect` preserves 100% of cognitive lens behavior while maintaining Authoritative Background Loops = 0, Mutable Shared-State Sites = 0, and Direct Storage Writers = 0.*

### Hypothesis H9C-3: Conformal Forgotten Diamonds & Dormant Salience
> *Re-deriving Forgotten Diamonds as conformal uncertainty recall with exponential dormant salience decay ($S(t) = S_0 \cdot 0.5^{\frac{\Delta t}{\tau}}$) enables high-value historical memory recovery within active, authorized pulse budgets without requiring un-audited background cron jobs or continuous daemon threads.*

### Hypothesis H9C-4: Constitutional Invariance & Closure Integrity
> *Requalifying the semantic projection sweep pipeline and removing the temporary Slice 1 exclusion in `crates/wm-gen3-core/src/ops.rs` will produce 0 constitutional bypasses, preserve `#![forbid(unsafe_code)]`, and pass all static closure tests (`scripts/check_closures.sh`).*

---

## 3. Frozen Metric Acceptance Thresholds

The following metric thresholds are frozen prior to implementation. Any failure against these criteria constitutes a gate rejection:

| Metric | Baseline (Slice 1) | Target Threshold (Gate 9C) | Falsification Condition |
|---|---|---|---|
| **Precision** | $1.06\%$ | $\ge 2.12\%$ ($\ge 2\times$ improvement) | $< 2.12\%$ |
| **Recall** | $89.7\%$ | $\ge 85.0\%$ | $< 85.0\%$ |
| **Candidate Pair Reduction** | 0% reduction | $\ge 50.0\%$ reduction in evaluated noise pairs | $< 50.0\%$ |
| **Reversed Direction Pairs** | 0 | $0$ (strict temporal invariance) | $> 0$ |
| **Constitutional Exceptions** | 0 | $0$ | $> 0$ |
| **Authoritative Background Loops** | 0 | $0$ (Article 4 compliance) | $> 0$ |
| **Direct Storage Writers** | 0 | $0$ (Article 1 compliance) | $> 0$ |
| **Static Law Closures** | 0 violations | $0$ violations (`check_closures.sh`) | $> 0$ |

---

## 4. Simplification Scorecard $\vec{S}_{9C}$

In accordance with PEB-15 §6, Gate 9C tracks the simplification vector:

$$\vec{S}_{9C} = \begin{bmatrix} \text{Behavioral Value Retained} \ge 1.0 \\ \Delta\text{LoC} \text{ (Pareto rent justified)} \\ \text{Cyclomatic Complexity Reduction} \\ \text{Mutable Shared-State Sites} = 0 \\ \text{Authoritative Background Loops} = 0 \\ \text{Direct Storage Writers} = 0 \\ \text{Constitutional Exceptions} = 0 \end{bmatrix}$$

---

## 5. Preregistration Ratification

- **Pre-Registration Timestamp:** 2026-09-24T23:55:00Z  
- **Ratified By:** Antigravity & Lucas  
- **Review Channel:** Sangha Whiteboard Agora (`http://127.0.0.1:8787`)  
