# Pre-Registration: PEB-13 Continuous Cognitive Geometry & The Metric Ladder

**Document ID:** `PEB-13-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 7 (Continuous Cognitive Geometry)  
**Authors:** Lucas & Antigravity  
**Status:** PREREGISTERED & FROZEN  
**Target Crate:** `crates/wm-gen3-core/src/geometry.rs`  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Primary Thesis: "Curvature Has to Pay Rent"
In modern cognitive modeling and theoretical machine learning, it is common to invoke metaphors of "curved thought manifolds," "information geometry," and "non-Euclidean cognitive spaces." However, a more complex geometry possesses more free parameters. If a Riemannian or Finsler model merely fits data better because of higher expressive capacity, no scientific discovery has been made.

**The Operational Principle:**
Higher geometric complexity must buy measurable, held-out predictive accuracy over simpler geometries on an identical, preregistered prediction target. If it does not, Gen3 halts its ascent on the ladder:
$$ L_2 \longrightarrow d_G \longrightarrow g_{\mu\nu}(x) \longrightarrow F(x, v) $$

### 1.2 Unified Prediction Target
The ladder models are evaluated on a single, shared prediction target:
$$\text{Given state } x \text{ and candidate next state } y, \text{ predict the held-out observed transition cost / distance } D(x, y).$$
Every rung on the ladder receives:
- The exact same train / holdout data split ($80\% / 20\%$).
- The exact same loss function: Root Mean Squared Error ($\text{RMSE}$) and Mean Absolute Percentage Error ($\text{MAPE}$).
- A complexity penalty (Bayesian Information Criterion / penalty per parameter) to prevent overfitting noise.

**Criteria for Ascending to Higher Rungs:**
A higher rung $M_{k+1}$ is accepted over $M_k$ if and only if:
1. $\Delta \text{RMSE} = \text{RMSE}(M_k) - \text{RMSE}(M_{k+1}) > \delta_{\min}$ (where $\delta_{\min} = 0.05$).
2. The $95\%$ bootstrap confidence interval of $\Delta \text{RMSE}$ strictly excludes zero.
3. The improvement survives the parameter complexity penalty ($\Delta \text{BIC} > 10.0$).
4. The result reproduces across multiple random seeds and operational regimes.

---

## 2. Milestone 7A: Calibration Stage (Ground-Truth Recovery)

Before any empirical cognitive traces from WhiteMagic are evaluated, the geometry identification engine must prove that it can distinguish the four candidate geometries on **synthetic ground-truth worlds**:

1. **World E (Truly Euclidean $L_2$):**
   - Coordinates generated in flat $\mathbb{R}^d$.
   - Ground truth cost: $D_E(x, y) = \|x - y\|_2$.
   - Identification Contract: $L_2$ must achieve minimum error; higher rungs must fail the complexity/rent test.
2. **World G (Discrete Graph Geodesic $d_G$):**
   - States embedded as nodes in a sparse geometric graph (e.g. Watts-Strogatz or grid network).
   - Ground truth cost: Shortest path distance over edges $d_G(x, y)$.
   - Identification Contract: Graph geodesic must significantly outperform $L_2$ ($\Delta > \delta_{\min}$); continuous Riemannian manifold must not overfit.
3. **World R (Curved Riemannian Manifold $g_{\mu\nu}(x)$):**
   - States generated on a 2D/3D sphere or Poincaré disk with metric tensor $g_{\mu\nu}(x)$.
   - Ground truth cost: Geodesic arc length $\int \sqrt{g_{\mu\nu}(x) \dot{x}^\mu \dot{x}^\nu} \, dt$.
   - Identification Contract: Riemannian metric tensor must outperform both $L_2$ and $d_G$.
4. **World F (Directional / Asymmetric Finsler Cost $F(x, v)$):**
   - States moving in a vector field with a drift or potential gradient $w$: moving with the drift costs less than moving against it ($F(x, v) \ne F(x, -v)$).
   - Ground truth cost: Zermelo navigation distance.
   - Identification Contract: Asymmetric Finsler model must outperform all symmetric metrics ($L_2, d_G, g_{\mu\nu}$).

**Negative Control Gate:**
If the identification pipeline cannot recover these four synthetic worlds blind with $100\%$ accuracy, it is formally barred from drawing inferences on WhiteMagic runtime traces.

---

## 3. Experiment Structure (PEB-13)

### 3.1 PEB-13A: Metric Identification on Cognitive Traces
- **Frozen State Representation:** To avoid confounding feature representation with geometry, the state representation is frozen prior to fitting:
  $$ \text{Cognitive Tuple: } \mathcal{T}_t = (X_t, B_t, S_t, O_t, C_t) $$
  where $X_t$ is the microstate vector, $B_t$ is the macrostate/basin index, $S_t$ is the incoming stimulus, $O_t$ is the selected operation $[Select, Transform, Evaluate, Commit]$, and $C_t$ is the commit outcome.
- **Trace Intake:** Traces from $[Select \to Transform \to Evaluate \to Commit]$ cycles are split into train ($80\%$) and holdout ($20\%$).
- **Ladder Evaluation:** Evaluate $L_2$, $d_G$, $g_{\mu\nu}$, and $F(x, v)$ against held-out transition costs.

### 3.2 PEB-13B: Arrow of Time & Stochastic Entropy Production
- **Transition Probability Matrix:** Compute $P_{ij}$ across discrete macrostate basins $i, j \in \{1, \dots, K\}$.
- **Ergodicity & Recurrent Class Diagnostics:** Verify irreducibility of the transition matrix. Identify recurrent vs transient classes.
- **Stationary Distribution Solver:** Compute unique stationary distribution $\pi$ satisfying $\pi P = \pi, \sum \pi_i = 1$.
- **Stationary Probability Current:**
  $$ J_{ij} = \pi_i P_{ij} - \pi_j P_{ji} $$
- **Stochastic Entropy Production Rate:**
  $$ \sigma = \sum_{i < j} J_{ij} \ln \left( \frac{\pi_i P_{ij}}{\pi_j P_{ji}} \right) $$
- **Strict Framing:** $\sigma$ measures *stochastic time-reversal asymmetry*, not literal thermodynamic heat in Joules.
- **Regularization for Divergence:** For pairs where $P_{ij} > 0$ and $P_{ji} = 0$, apply pre-registered Bayesian Dirichlet smoothing (Laplace pseudocount $\alpha_0 = 1.0 / K$) and perform sensitivity analysis across $\alpha_0 \in [10^{-3}, 1.0]$.
- **Null Controls:**
  1. *Shuffled-Time Null:* Permuting transition timestamps must yield $J_{ij} \approx 0, \sigma \approx 0$.
  2. *Reversed-Trajectory Null:* Evaluating trajectories in reverse order must invert currents $J_{ij} \to -J_{ij}$.

### 3.3 PEB-13C: Geometric Holonomy vs State Hysteresis
A critical distinction is drawn between two fundamentally different phenomena:
- **Hypothesis $H13\text{-}C1$ (Path Dependence / Hysteresis):**
  Different final microstates $x_{\gamma_1}(A) \ne x_{\gamma_2}(A)$ occur simply because the agent writes to memory, increments counters, updates caches, or logs events.
- **Hypothesis $H13\text{-}C2$ (Geometric Holonomy):**
  Parallel transport of a tangent probe vector $v \in T_A \mathcal{M}$ (e.g. a predictive basis or sensitivity vector) around closed loops $\gamma_1, \gamma_2$ back to coordinate $A$ produces an intrinsic rotation or displacement:
  $$ \Delta v = v_{\gamma_1}' - v_{\gamma_2}' \ne 0 $$
  independent of explicit memory storage.

#### Layered Ablation Protocol (Via Deterministic Replay)
Starting from an identical frozen snapshot $S_0$ at node $A$, traverse loop $\gamma_1: A \to B \to C \to A$ and loop $\gamma_2: A \to D \to E \to A$, and evaluate microstates and transported tangent vectors across 5 ablation tiers:
1. **Tier 1 (Full Cognition):** Normal execution with full episodic memory, journal writes, and adaptation.
2. **Tier 2 (No Episodic Writes):** Memory store writes disabled; cache and working memory only.
3. **Tier 3 (No Adaptation):** Parameter and weight updates frozen; homeostatic tuning disabled.
4. **Tier 4 (No Timestamps / Monotonic Counters):** Time and sequence counters strictly held constant.
5. **Tier 5 (Pure Reversible Operations):** Only bijective $[Select \to Transform]$ operations; no commits or evictions.

**Target Question:** *At which exact layer does path dependence vanish?*
- Does $[Select \to Transform]$ remain geometrically flat and reversible?
- Does $[Evaluate]$ introduce directional asymmetry?
- Does $[Commit]$ create the arrow of time?
- Does episodic memory consolidation create hysteresis?

---

## 4. Pre-Registered Invariants & Verification Checklist

- [ ] **INV-7.1 (Negative Control Gate):** 100% ground-truth recovery across synthetic Worlds E, G, R, and F before evaluating runtime traces.
- [ ] **INV-7.2 (Pareto Complexity Gate):** Higher rungs must achieve $\Delta \text{RMSE} > 0.05$ with 95% CI excluding zero and $\Delta \text{BIC} > 10.0$ to be adopted.
- [ ] **INV-7.3 (Ergodicity & Smoothing Contract):** Transition matrix tested for irreducibility; Dirichlet smoothing parameter $\alpha_0$ preregistered for zero-reverse transitions.
- [ ] **INV-7.4 (Null Control Asymmetry):** Shuffled-time null must produce $\sigma \approx 0$; genuine cognitive trajectories must demonstrate statistically significant asymmetry ($\sigma > 0, p < 0.01$).
- [ ] **INV-7.5 (Hysteresis vs Holonomy Separation):** Tangent probe vector parallel transport tested independently of microstate variable drift.
- [ ] **INV-7.6 (Deterministic Ablation Ladder):** Exact layer of path-dependence emergence identified across Tiers 1–5.
