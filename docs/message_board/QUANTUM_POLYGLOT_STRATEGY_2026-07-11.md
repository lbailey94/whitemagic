# Quantum-Inspired Polyglot Integration Strategy

**Date**: 2026-07-11
**Author**: Lucas Bailey + Cascade
**Status**: Planning — implementation begins 2026-07-12

---

## 1. Context

### What We Built (Session 2026-07-11)

Six quantum-inspired computing primitives implemented in Rust (`mc_quantum.rs`, 1076 lines), wired through the JSON stdio bridge (18 new handlers), exposed in Python via `PolyglotMCOrchestrator` (18 new methods with fallbacks), and augmented with Python-native implementations in `quantum_bridge.py`. 23 Rust tests + 33 Python tests, all passing. Full unit suite: 5100 passed, 6 skipped, 0 failures.

| System | Rust Functions | Bridge Methods | Python Methods |
|--------|---------------|----------------|----------------|
| Natural Gradient | `fubini_study_metric`, `natural_gradient_step` | `q_fubini_study_metric`, `q_natural_gradient` | `.fubini_study_metric`, `.natural_gradient` |
| Tensor Networks (MPS) | `MatrixProductState` struct, `multiscale_bind` | `q_multiscale_bind` | `.multiscale_bind` |
| Mixed-Curvature | `manifold_distance`, `embed_manifold`, `riemannian_gradient`, `exponential_map`, `auto_select_manifold` | `q_manifold_distance`, `q_embed_manifold`, `q_riemannian_gradient`, `q_exponential_map`, `q_auto_manifold` | `.manifold_distance`, `.embed_manifold`, `.riemannian_gradient`, `.exponential_map`, `.auto_select_manifold` |
| Born-Rule Sampling | `born_rule_sample`, `born_rule_batch_sample`, `born_rule_distribution`, `quantum_interference` | `q_born_sample`, `q_born_batch`, `q_born_distribution`, `q_interference` | `.born_sample`, `.born_batch_sample`, `.born_distribution`, `.quantum_interference` |
| Topological Protection | `berry_phase`, `chern_number`, `topological_encode`, `topological_decode` | `q_berry_phase`, `q_chern_number`, `q_topological_encode`, `q_topological_decode` | `.berry_phase`, `.chern_number`, `.topological_encode`, `.topological_decode` |
| QAOA | `quantum_walk_optimize`, `qaoa_maxcut` | `q_quantum_walk_optimize`, `q_qaoa_maxcut` | `.quantum_walk_optimize`, `.qaoa_maxcut` |

### Honest Assessment of Each System

**Immediately practical (wire into production now):**
1. **Mixed-Curvature Embeddings** — Memory taxonomies are hierarchical; hyperbolic space embeds trees with lower distortion. Auto-select manifold means the system adapts without manual tuning. Benefit: better similarity search, more accurate retrieval.
2. **Born-Rule Sampling** — |amplitude|² naturally creates power-law-like distributions that concentrate on high-amplitude outcomes while preserving exploration. Strictly better than uniform random for serendipity engine, graph walking, I Ching consultation.
3. **Natural Gradient Optimization** — Fubini-Study metric is the correct geometry for parameter spaces. Fewer steps, better convergence for recursive improvement loop and possibility space explorer.

**Promising but speculative (need polyglot upgrades to reach full potential):**
4. **Hierarchical Tensor Networks (MPS)** — MPS compression is legitimate (DMRG won Nobel Prize), but our hand-rolled Rust SVD is a simplified approximation. Needs ITensors.jl for production-grade compression.
5. **Topological Error Protection** — Berry phases and Chern numbers are beautiful mathematics, but our implementation is classical redundancy with phase rotation — not true topological invariants. Needs exact arithmetic and roundtrip verification.
6. **QAOA / Quantum Walk** — Classical simulation captures key ideas but can't achieve quantum speedup. Value is in the framework — if we later get quantum hardware access, the interface is ready. Could benefit from formal verification of unitarity.

---

## 2. Strategy: Three-Phase Implementation

### Phase 1: Wire Quantum Upgrades Into Cognitive Systems (Morning)

**Goal**: Make the three immediately-practical systems perceptible in WhiteMagic's cognitive quality.

#### 1a. Born-Rule Sampling → Serendipity Engine + Graph Walker

**Files to modify:**
- `core/whitemagic/core/intelligence/synthesis/serendipity_engine.py` — replace uniform random in `_surface_quantum` with `born_rule_sample`
- `core/whitemagic/core/memory/graph_walker.py` — replace uniform probability in quantum-enhanced walk with Born-rule distribution
- `core/whitemagic/core/acceleration/quantum_bridge.py` — `QuantumEngine.superposition_walk` already returns `{node: |amp|²}`, which IS Born-rule. But the *selection* from that distribution uses uniform random. Switch to `born_rule_sample`.

**Changes:**
```python
# serendipity_engine.py: _surface_quantum
# Current: ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
# New: use born_rule_sample on the amplitudes to select top-k probabilistically
amplitudes = [fused[node_id] for node_id in candidate_ids]
selected_idx = born_rule_batch_sample(amplitudes, n=top_k, seed=seed)
```

**Expected impact**: More intelligent probabilistic selection — high-relevance memories are favored but low-relevance ones still get explored. This is the quantum measurement postulate applied to memory surfacing.

**Tests**: Add test cases verifying Born-rule selection favors high-amplitude memories while maintaining exploration.

#### 1b. Auto-Select Manifold → Embedding Pipeline

**Files to modify:**
- `core/whitemagic/core/memory/embeddings.py` — add manifold detection on galaxy embeddings
- `core/whitemagic/core/memory/graph_walker.py` — use manifold-appropriate distance metric
- `core/whitemagic/core/memory/hnsw_index.py` — support custom distance functions per galaxy

**Changes:**
```python
# embeddings.py: after computing embeddings for a galaxy, detect manifold
manifold = auto_select_manifold(embedding_vectors)
# Store manifold type per galaxy, use appropriate distance in queries
```

**Expected impact**: Hierarchical galaxies (like the taxonomy galaxy) get hyperbolic distance; clustered galaxies (like emotional gardens) get spherical distance; flat galaxies get Euclidean. Better retrieval accuracy across all galaxy types.

**Tests**: Verify that auto-select-manifold correctly classifies known galaxy structures and that retrieval uses the appropriate metric.

#### 1c. Natural Gradient → Recursive Improvement Loop

**Files to modify:**
- `core/whitemagic/core/intelligence/agentic/recursive_improvement_loop.py` — replace flat gradient descent with natural gradient when metric is available
- `core/whitemagic/core/consciousness/possibility_explorer.py` — use natural gradient for parameter optimization

**Changes:**
```python
# recursive_improvement_loop.py: in the optimization step
# Current: new_params = [p - lr * g for p, g in zip(params, grads)]
# New: compute Fubini-Study metric from recent Jacobian history, use natural gradient
metric = fubini_study_metric(current_state, jacobian_history)
result = natural_gradient(params, grads, metric, learning_rate)
new_params = result["new_params"]
```

**Expected impact**: Faster convergence on cognitive parameter optimization, especially when parameters have very different sensitivities (e.g., coherence weight vs. emergence threshold).

**Tests**: Verify natural gradient converges faster than flat gradient on a test optimization problem.

---

### Phase 2: Julia QuantumGeometry.jl (Afternoon)

**Goal**: Fill the speculative implementation gaps with Julia's world-class numerical ecosystem.

#### 2a. Create `QuantumGeometry.jl` Module

**Location**: `polyglot/whitemagic-jl/src/QuantumGeometry.jl`

**Dependencies** (add to `Project.toml`):
- `Manifolds.jl` — production-grade Riemannian geometry (Poincaré ball, sphere, Euclidean)
- `ForwardDiff.jl` — automatic differentiation for Jacobian computation
- `StaticArrays.jl` — already used, stack-allocated arrays for hot paths
- `LinearAlgebra.jl` — already used

**Functions to implement:**

```julia
module QuantumGeometry

using Manifolds
using ForwardDiff
using LinearAlgebra
using StaticArrays

export
    # Manifold operations (exact, via Manifolds.jl)
    manifold_distance,
    manifold_exp_map,
    manifold_log_map,          # inverse of exp map — currently missing in Rust
    manifold_parallel_transport, # transport vectors between tangent spaces
    manifold_inner_product,     # Riemannian metric tensor application

    # Automatic Fubini-Study metric
    fubini_study_auto,          # computes Jacobian via ForwardDiff, then metric
    natural_gradient_auto,      # end-to-end: params + gradient → natural gradient step

    # MPS compression (simplified — full ITensors.jl integration is Phase 3)
    mps_compress,
    mps_full_state,
    mps_bind,

    # Manifold selection
    auto_select_manifold,
```

**Key advantages over Rust:**
- `Manifolds.jl` provides **exact** exponential/logarithmic maps, parallel transport, and Riemannian metrics — our Rust implementation uses simplified formulas
- `ForwardDiff.jl` computes exact Jacobians automatically — our Rust implementation requires the user to supply the Jacobian
- `manifold_log_map` (inverse of exponential map) is currently **missing** in Rust — Julia gives it for free
- `manifold_parallel_transport` (moving vectors between tangent spaces) is currently **missing** — needed for proper natural gradient on manifolds

#### 2b. Julia Bridge Handler

**Location**: `polyglot/bridges/julia/quantum_bridge.jl`

**Protocol** (JSON stdio, same as existing bridges):
```
{"method": "q_manifold_exp", "params": {"point": [...], "tangent": [...], "manifold": "hyperbolic"}}
{"method": "q_manifold_log", "params": {"point": [...], "target": [...], "manifold": "spherical"}}
{"method": "q_parallel_transport", "params": {"point": [...], "target": [...], "vector": [...], "manifold": "hyperbolic"}}
{"method": "q_fubini_study_auto", "params": {"state": [...], "param_func": "...", "n_params": 4}}
{"method": "q_natural_gradient_auto", "params": {"params": [...], "gradient": [...], "param_func": "...", "learning_rate": 0.01}}
{"method": "q_mps_compress", "params": {"vectors": [[...]], "bond_dim": 2, "seed": 42}}
```

#### 2c. Python Wiring

**Location**: `core/whitemagic/core/evolution/polyglot_mc.py`

Add Julia backend dispatch to existing quantum methods:
```python
def natural_gradient(self, params, gradients, metric, learning_rate=0.01):
    # If metric not provided, use Julia for automatic Jacobian computation
    if metric is None or not metric:
        result = _julia_call("q_natural_gradient_auto", params=params, gradient=gradients, learning_rate=learning_rate)
        if result and "new_params" in result:
            return result
    # Fall through to Rust (existing path)
    return _rust_call("q_natural_gradient", ...)
```

**Dispatch priority**: Julia (exact, auto-diff) → Rust (fast, manual) → Python (fallback, simplified)

---

### Phase 3: Haskell Topological Verification (Late Afternoon / Next Day)

**Goal**: Add formal verification and exact arithmetic to the topological protection system.

#### 3a. Create `topological_bridge.hs`

**Location**: `polyglot/bridges/haskell/topological_bridge.hs`

**Functions to implement:**

```haskell
-- Exact Berry phase using rational arithmetic (no floating-point drift)
berryPhaseExact :: [[Rational]] -> [Rational] -> Rational

-- Chern number with guaranteed integer result
chernNumberExact :: [[Rational]] -> Rational -> Rational -> Integer

-- Roundtrip property verification: decode . encode ≡ identity
verifyRoundtrip :: [Double] -> Int -> Int -> Bool

-- Quantum walk unitarity check: U†U = I
verifyUnitarity :: [[Double]] -> Bool

-- Topological encode/decode with exact arithmetic
topologicalEncodeExact :: [Rational] -> Int -> Int -> ([Rational], Rational)
topologicalDecodeExact :: [Rational] -> Int -> Int -> [Rational]
```

**Key advantages over Rust:**
- Haskell's `Rational` type provides **exact** arithmetic — no floating-point drift in Berry phase accumulation
- Chern number is mathematically guaranteed to be an integer — Haskell's type system can enforce this
- Roundtrip verification is a **proof**, not a test — Haskell can verify it for all inputs via parametricity
- Unitarity verification ensures quantum walk operators preserve probability

#### 3b. Haskell Bridge Handler

**Protocol** (JSON stdio):
```
{"method": "q_berry_phase_exact", "params": {"states": [[...]], "params": [...]}}
{"method": "q_chern_number_exact", "params": {"curvature": [[...]], "dtheta": 0.1, "dphi": 0.1}}
{"method": "q_verify_roundtrip", "params": {"data": [...], "n_redundant": 3, "seed": 42}}
{"method": "q_verify_unitarity", "params": {"operator": [[...]]}}
```

#### 3c. Python Wiring

Add Haskell verification calls to the topological protection methods:
```python
def topological_encode(self, data, n_redundant=3, seed=42):
    # Encode via Rust (fast)
    result = _rust_call("q_topological_encode", ...)
    # Verify roundtrip via Haskell (exact)
    if _haskell_available():
        verified = _haskell_call("q_verify_roundtrip", data=data, n_redundant=n_redundant, seed=seed)
        if not verified.get("roundtrip_ok", True):
            logger.warning("Topological encode/decode roundtrip failed verification")
    return result
```

---

## 3. Implementation Priority

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| **P0** | 1a: Born-rule → serendipity engine + graph walker | ~2h | High — immediately perceptible improvement in memory surfacing |
| **P0** | 1b: Auto-select manifold → embedding pipeline | ~3h | High — better retrieval accuracy across all galaxies |
| **P1** | 1c: Natural gradient → recursive improvement loop | ~2h | Medium — faster convergence on parameter optimization |
| **P1** | 2a: QuantumGeometry.jl module | ~4h | High — fills biggest speculative gap (exact manifold geometry) |
| **P1** | 2b: Julia quantum bridge | ~2h | Required for 2a to be callable from Python |
| **P2** | 2c: Python Julia dispatch wiring | ~1h | Connects Julia backend to orchestrator |
| **P2** | 3a: Haskell topological bridge | ~3h | Medium — formal verification, exact arithmetic |
| **P3** | 3b: Haskell bridge handler | ~1h | Required for 3a to be callable |
| **P3** | 3c: Python Haskell dispatch wiring | ~1h | Connects Haskell verification to encode/decode |
| **P3** | Tests for all new wiring | ~2h | Required — no skipping tests |

**Total estimated effort**: ~21 hours (2-3 sessions)

---

## 4. Architecture After Implementation

```
Cognitive Operation (e.g., memory retrieval)
    │
    ├── Born-Rule Sampling (Rust, fast)
    │   └── Selects memories probabilistically by |amplitude|²
    │
    ├── Manifold-Aware Distance (Rust fast / Julia exact)
    │   ├── Auto-detect manifold type per galaxy
    │   ├── Euclidean for flat galaxies
    │   ├── Hyperbolic for hierarchical galaxies (taxonomy, codex)
    │   └── Spherical for clustered galaxies (emotional gardens)
    │
    ├── Natural Gradient Optimization (Rust fast / Julia auto-diff)
    │   ├── Fubini-Study metric from Jacobian
    │   ├── Geodesic updates respecting manifold geometry
    │   └── Automatic Jacobian computation (Julia only)
    │
    ├── MPS Compression (Rust simplified / Julia ITensors.jl)
    │   └── Reduces HRR vector dimensionality while preserving binding
    │
    ├── Topological Protection (Rust fast / Haskell verified)
    │   ├── Berry phase encoding for fault-tolerant memories
    │   ├── Chern number for topological invariant classification
    │   └── Roundtrip verification (Haskell only)
    │
    └── QAOA Optimization (Rust simulation / Haskell verified)
        ├── Quantum walk for combinatorial problems
        └── MaxCut for graph partitioning
```

### Dispatch Logic

```python
def quantum_dispatch(method, **kwargs):
    # 1. Try Rust (fast, always available)
    result = _rust_call(method, **kwargs)
    if result and not result.get("fallback"):
        return result

    # 2. Try Julia (exact, auto-differentiation)
    if julia_available():
        result = _julia_call(method, **kwargs)
        if result:
            return result

    # 3. Try Haskell (verification, exact arithmetic)
    if haskell_available() and method.startswith("q_topological"):
        result = _haskell_call(method, **kwargs)
        if result:
            return result

    # 4. Python fallback (simplified, always available)
    return python_fallback(method, **kwargs)
```

---

## 5. Testing Strategy

### Unit Tests
- **Rust**: 23 existing tests (all passing) — extend with edge cases for manifold operations
- **Python**: 33 existing tests (all passing) — extend with integration tests for cognitive wiring
- **Julia**: New test file `test_quantum_geometry.jl` — test exact manifold operations against known values
- **Haskell**: New test file `test_topological.hs` — test roundtrip properties, exact arithmetic

### Integration Tests
- Born-rule sampling in serendipity engine: verify high-amplitude memories are surfaced more frequently
- Auto-select manifold in embedding pipeline: verify correct manifold detection for known galaxy structures
- Natural gradient in recursive improvement loop: verify faster convergence than flat gradient
- Julia dispatch: verify Julia backend is used when available, falls back to Rust
- Haskell verification: verify roundtrip property holds for all test cases

### Regression Tests
- Full unit suite must remain green (currently 5100 passed, 6 skipped)
- No new test should exceed 5s (unit) or 15s (integration)
- Run `check_doc_drift.py` after all changes

---

## 6. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Julia JIT cold-start adds latency | High | PrecompileTools warmup (already used in HolographicMemory.jl), only use Julia for batch operations |
| Manifolds.jl not installed | Medium | Check availability at startup, fall back to Rust |
| Haskell runhaskell is slow | High | Compile to binary (existing pattern), only use for verification, not hot paths |
| Born-rule sampling changes serendipity behavior | Medium | Add feature flag `WM_BORN_RULE_SAMPLING=1`, A/B test against uniform |
| Auto-select manifold misclassifies galaxies | Medium | Manual override per galaxy, log classification for review |
| Natural gradient diverges with bad metric | Low | Fallback to flat gradient if metric is singular (already handled in Rust) |

---

## 7. Success Metrics

1. **Born-rule sampling**: serendipity engine surfaces high-relevance memories ≥2x more frequently than uniform random (measured over 1000 retrieval operations)
2. **Auto-select manifold**: ≥80% of galaxies correctly classified (validated against manual labels)
3. **Natural gradient**: recursive improvement loop converges in ≤30% fewer iterations than flat gradient on test optimization problems
4. **Julia manifold geometry**: exact exp/log maps match analytical solutions to 1e-12 precision
5. **Haskell verification**: topological encode/decode roundtrip verified for all test cases, Chern numbers are exact integers
6. **No regressions**: full test suite remains green (5100+ passed, 0 new failures)

---

## 8. Files to Create / Modify

### New Files
- `polyglot/whitemagic-jl/src/QuantumGeometry.jl` — Julia quantum geometry module
- `polyglot/bridges/julia/quantum_bridge.jl` — Julia JSON stdio bridge for quantum methods
- `polyglot/bridges/haskell/topological_bridge.hs` — Haskell topological verification bridge
- `polyglot/bridges/python/whitemagic_polyglot/__init__.py` — add `JuliaQuantumBackend`, `HaskellTopologicalBackend` classes
- `core/tests/unit/test_quantum_cognitive_wiring.py` — integration tests for cognitive wiring
- `polyglot/whitemagic-jl/test/test_quantum_geometry.jl` — Julia quantum geometry tests
- `polyglot/bridges/haskell/test_topological.hs` — Haskell topological tests

### Modified Files
- `core/whitemagic/core/intelligence/synthesis/serendipity_engine.py` — Born-rule sampling
- `core/whitemagic/core/memory/graph_walker.py` — Born-rule + manifold-aware distance
- `core/whitemagic/core/acceleration/quantum_bridge.py` — Born-rule in superposition_walk selection
- `core/whitemagic/core/memory/embeddings.py` — auto-select manifold per galaxy
- `core/whitemagic/core/memory/hnsw_index.py` — custom distance per manifold type
- `core/whitemagic/core/intelligence/agentic/recursive_improvement_loop.py` — natural gradient
- `core/whitemagic/core/consciousness/possibility_explorer.py` — natural gradient
- `core/whitemagic/core/evolution/polyglot_mc.py` — Julia/Haskell dispatch in quantum methods
- `polyglot/whitemagic-jl/Project.toml` — add Manifolds.jl, ForwardDiff.jl dependencies

---

## 9. Morning Kickoff Checklist

- [ ] Verify Rust build: `cargo build --release -p wm-evolution` in `polyglot/whitemagic-rs/`
- [ ] Verify Rust tests: `cargo test --release -p wm-evolution mc_quantum`
- [ ] Verify Python tests: `python -m pytest tests/unit/test_quantum_upgrades.py -v`
- [ ] Verify Julia available: `julia --version`
- [ ] Check Julia packages: `julia --project=polyglot/whitemagic-jl -e 'using Pkg; Pkg.status()'`
- [ ] Verify Haskell available: `runhaskell --version` or check for compiled binary
- [ ] Review this document
- [ ] Start with Phase 1a (Born-rule → serendipity engine)

---

*"Tests are the guardrail. Never skip them." — AGENTS.md*
