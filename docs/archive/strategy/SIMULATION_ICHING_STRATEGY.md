# Simulation & I Ching SIMD Strategy

**Created**: 2026-06-23
**Status**: Draft
**Scope**: Upgrade existing simulation/Monte Carlo systems + expand I Ching into 64-lane SIMD dispatch architecture

---

## Architecture Overview

Four layers, built bottom-up:

1. **Technical Fixes** — Upgrade existing math kernels (low effort, high impact)
2. **I Ching Expansion** — Stochastic casting, trigram decomposition, 64-hexagram dispatch matrix
3. **Physics-Oracle Layer** — Resonance-based selection, galactic zone frequencies, coupled dream cycle
4. **HRR Interaction Layer** — Hexagram interaction matrix, entropy-matched routing, synergy detection

Plus a final **SIMD Integration** phase that wires the 64-hexagram system into parallel execution.

---

## Phase 1: Technical Fixes (High Priority, Low Effort)

### 1a: Analytical Oscillator Solution
**File**: `core/whitemagic/core/resonance/julia_resonance.py` (lines 196-293)
**Change**: Replace scipy `solve_ivp` RK45 numerical integration with closed-form underdamped solution:
```python
x(t) = e^(-γt/2) * [A·cos(ωd·t) + B·sin(ωd·t)]
where ωd = √(ω₀² - γ²/4)
```
**Impact**: 1000× faster, removes scipy dependency for this path, enables batch computation of 10K+ memories
**Tests**: Verify analytical solution matches numerical solution within tolerance

### 1b: FFT Crate for HRR Composition
**File**: `polyglot/whitemagic-rs/crates/wm-evolution/src/hrr_composition.rs` (lines 140-179)
**Change**: Replace O(n²) DFT with `rustfft` crate (O(n log n))
**Cargo.toml**: Add `rustfft = "0.1"` to wm-evolution dependencies
**Impact**: 32× speedup on 256-dim bind/unbind operations
**Tests**: Verify bind/unbind roundtrip still works, compare output with old DFT

### 1c: Quasi-Monte Carlo (Sobol Sequences)
**File**: `polyglot/whitemagic-rs/crates/wm-evolution/src/mc_integration.rs`
**Change**: Add Sobol sequence sampler as alternative to LCG-based Gaussian sampling. Add `rand_qmc` crate or implement Sobol directly.
**Impact**: 5-10× variance reduction for same trial count in Monte Carlo calibration
**Tests**: Verify Sobol trials produce lower variance than random trials on same problem

### 1d: Claim-Specific Beta Precision
**File**: `core/whitemagic-rust/src/monte_carlo.rs`
**Change**: Replace fixed `precision = 10.0` with claim-specific precision based on evidence quality
**Impact**: More honest calibration — speculative claims get wider posteriors
**Tests**: Verify high-precision claims produce tighter distributions

### 1e: Stratified Lead-Time Noise
**File**: `core/whitemagic-rust/src/monte_carlo.rs`
**Change**: Replace flat `rng.gen_range(-2.0..2.0)` with sigma scaled to lead weeks: `sigma = max(1.0, lead_weeks * 0.15)`
**Impact**: More realistic lead-time distributions
**Tests**: Verify 50-week predictions get wider noise than 5-week predictions

---

## Phase 2: I Ching Expansion

### 2a: Expand iching.rs
**File**: `core/whitemagic-rust/src/iching.rs` (currently 54 lines)
**Additions**:
- **Stochastic casting**: 3-coin method and yarrow stalk method using `rand::thread_rng()`
- **Trigram decomposition**: Split hexagram into upper (lines 4-6) and lower (lines 1-3) trigrams
- **Second hexagram**: Transform moving lines (6→7, 9→8) to produce relating hexagram
- **Trigram enum**: 8 trigrams (Qian, Kun, Zhen, Xun, Kan, Li, Gen, Dui) with elemental associations
- **Hexagram metadata**: Name, binary value, trigram pair, line positions
- **Dual mode**: Stochastic (production) + deterministic hash (testing/replay)

**Data structures**:
```rust
pub enum Trigram { Qian, Kun, Zhen, Xun, Kan, Li, Gen, Dui }
pub struct HexagramCast {
    primary: u32,           // 1-64
    relating: u32,          // second hexagram from moving lines
    lines: Vec<u32>,        // 6 lines (6,7,8,9)
    moving_lines: Vec<usize>, // indices of moving lines
    lower_trigram: Trigram, // lines 1-3
    upper_trigram: Trigram, // lines 4-6
    cast_method: CastMethod, // Coin, Yarrow, or Hash
}
```

**Tests**: Stochastic casting produces correct line distributions, trigram decomposition correct for all 64 hexagrams, moving line transformation correct

### 2b: Trigram Compute/I/O Mode Definitions
**New file**: `core/whitemagic-rust/src/iching_dispatch.rs`
**Content**: Define 8 compute kernels (lower trigram) and 8 I/O patterns (upper trigram):

**Compute modes (lower trigram)**:
| Trigram | Element | Mode | Operation |
|---------|---------|------|-----------|
| Qian | Heaven | Initiate | New memory ingestion, metadata stamping |
| Kun | Earth | Consolidate | Storage, indexing, deep integration |
| Zhen | Thunder | Shock | Anomaly detection, salience spikes |
| Xun | Wind | Diffuse | Gradual search, semantic diffusion |
| Kan | Water | Flow | Temporal processing, lead-time computation |
| Li | Fire | Recognize | Pattern recognition, constellation detection |
| Gen | Mountain | Still | Checkpointing, convergence checks |
| Dui | Lake | Resonate | Resonance amplification, garden activation |

**I/O patterns (upper trigram)**:
| Trigram | Lines open | I/O behavior |
|---------|-----------|-------------|
| Qian | All 6 | Full-duplex, all channels active |
| Kun | Line 6 only | Output-only, compute on cached data |
| Zhen | Lines 1,6 | Read + output, no intermediate channels |
| Xun | Lines 1-3 | Read-heavy, gradual input |
| Kan | Lines 2,5 | Embedding + relational, temporal flow |
| Li | Lines 3,6 | Emotional + output, clarity-seeking |
| Gen | Line 6 | Minimal I/O, pure computation |
| Dui | Lines 4,6 | Relational + output, connection-seeking |

**Line → I/O channel mapping**:
- Line 1 (bottom): Memory read (holographic coords)
- Line 2: Embedding I/O (vector fetch)
- Line 3: Emotional/garden I/O
- Line 4: Relational I/O (graph edges)
- Line 5: Temporal I/O (prediction lookup)
- Line 6 (top): Output channel (result write-back)

### 2c: Hexagram Dispatch Matrix
**File**: `core/whitemagic-rust/src/iching_dispatch.rs`
**Content**: 8×8 = 64 entry dispatch table mapping each hexagram to (compute_mode, io_pattern)
**Function**: `dispatch(cast: &HexagramCast) -> DispatchResult` routes to appropriate handler

---

## Phase 3: Physics-Oracle Layer

### 3a: Resonance-Based Hexagram Selection
**New file**: `core/whitemagic-rust/src/iching_resonance.rs`
**Concept**: Pre-compute 64 oscillator states, one per hexagram. Each hexagram's trigram composition determines its oscillator parameters:
- Lower trigram → base frequency ω₀
- Upper trigram → damping coefficient γ
- Moving lines → coupling strength to query

**Selection**: Query's holographic coordinates are matched against 64 oscillators. Hexagram with highest resonance peak is selected.

**Trigram → frequency mapping**:
| Trigram | ω₀ | γ | Character |
|---------|-----|---|-----------|
| Qian | 5.0 | 0.05 | Fast, persistent (creative) |
| Kun | 0.3 | 0.02 | Slow, barely damped (receptive) |
| Zhen | 8.0 | 0.5 | Very fast, heavily damped (shock) |
| Xun | 2.0 | 0.08 | Medium, light damping (penetrating) |
| Kan | 1.0 | 0.15 | Medium, moderate damping (flowing) |
| Li | 3.0 | 0.2 | Fast, moderate damping (clarity) |
| Gen | 0.1 | 0.01 | Very slow, minimal damping (still) |
| Dui | 4.0 | 0.3 | Fast, damped (joyful) |

### 3b: Galactic Zone → Oscillator Frequency
**File**: `core/whitemagic/core/resonance/julia_resonance.py`
**Change**: Map galactic zones to frequency ranges:
- Core: ω₀ = 5.0 (fast resonance, short half-life)
- Inner Rim: ω₀ = 2.0
- Mid Band: ω₀ = 1.0 (current default)
- Outer Rim: ω₀ = 0.3
- Far Edge: ω₀ = 0.05 (near-static, archival)

**Beat frequency detection**: When a Far Edge memory is accessed, compute beat frequency between its low ω and the accessing memory's high ω. This measures "temporal distance" — how much an old memory still resonates with current context.

### 3c: Coupled Dream Cycle (Kuramoto Model)
**New file**: `polyglot/whitemagic-rs/crates/wm-evolution/src/kuramoto.rs`
**Concept**: 12 dream phases as 12 coupled oscillators:
- Triage ↔ Harmonize (beginning/end sync)
- Consolidation ↔ Decay (lifecycle management)
- Prediction ↔ Oracle (forward-looking)
- Kaizen ↔ Enrichment (improvement)
- Serendipity ↔ Constellation (discovery/clustering)
- Governance ↔ Narrative (regularization/summarization)

**Metrics**:
- **Synchronization index** (Kuramoto order parameter R): R→1 = coherent dream, R→0 = creative tension
- **Phase coherence**: Which phases are in sync vs out of phase
- **Dream quality**: Synchronized dreams = restful (consolidation), desynchronized = creative (exploration)

---

## Phase 4: Calibration-Oracle Bridge

### 4a: Beta-Calibrated Line Probabilities
**File**: `core/whitemagic-rust/src/iching.rs`
**Concept**: Replace fixed yarrow stalk probabilities (1/16, 5/16, 7/16, 3/16) with dynamic probabilities driven by Monte Carlo calibration:
- Well-calibrated → tighter line distributions → fewer moving lines → stable hexagrams
- Poorly calibrated → wider distributions → more moving lines → transitional hexagrams

**Implementation**: Accept a `calibration_brier` parameter (0-1). Map it to line probability spread:
```rust
fn line_probabilities(calibration_brier: f64) -> [f64; 4] {
    // brier 0.0 (perfect) → tight: [1/32, 6/32, 6/32, 3/32] (few moving lines)
    // brier 0.25 (random) → wide: [2/16, 4/16, 6/16, 4/16] (many moving lines)
    // brier 1.0 (worst) → widest: [3/16, 3/16, 5/16, 5/16]
    let spread = calibration_brier.min(1.0);
    [
        1.0/32.0 + spread * (3.0/16.0 - 1.0/32.0),  // old yin (moving)
        6.0/32.0 + spread * (3.0/16.0 - 6.0/32.0),  // young yang
        6.0/32.0 + spread * (5.0/16.0 - 6.0/32.0),  // young yin
        3.0/32.0 + spread * (5.0/16.0 - 3.0/32.0),  // old yang (moving)
    ]
}
```

### 4b: Boltzmann Hexagram Selection
**File**: `core/whitemagic-rust/src/iching_dispatch.rs`
**Concept**: Use thermodynamic system's temperature to bias hexagram selection:
- High temperature → creative/disruptive hexagrams boosted
- Low temperature → receptive/stable hexagrams boosted

**Implementation**: Assign each hexagram an "energy" based on its trigram character:
- Creative hexagrams (Qian-dominant): high energy (selected when hot)
- Receptive hexagrams (Kun-dominant): low energy (selected when cold)
- Mixed: intermediate energy

Use existing `boltzmann_probabilities()` from `thermodynamic.rs` to select hexagram.

---

## Phase 5: HRR Interaction Layer

### 5a: Hexagram HRR Encoding + Interaction Matrix
**New file**: `polyglot/whitemagic-rs/crates/wm-evolution/src/hexagram_hrr.rs`
**Concept**: Encode each hexagram as an HRR vector using existing `hrr_composition::encode_hypothesis`. Bind hexagram pairs to compute interactions:
- 64×64 = 4,096 bind operations (one-time precomputation)
- Compute synergy scores for each pair
- Result: interaction matrix revealing which archetypal combinations are superlinear vs sublinear

**Encoding**: 6 lines → 6-dimensional binding. Each line position maps to a dimension:
- Line 1 → "temporal" role
- Line 2 → "semantic" role
- Line 3 → "emotional" role
- Line 4 → "relational" role
- Line 5 → "importance" role
- Line 6 → "output" role

Yang line = bind with "active" token. Yin line = bind with "receptive" token. Moving line = bind with "transition" token.

### 5b: Entropy-Matched Routing
**File**: `core/whitemagic-rust/src/iching_dispatch.rs`
**Concept**: Each hexagram has intrinsic entropy based on line distribution:
- Hexagram 1 (111111) or 2 (000000): entropy = 0 (maximum certainty)
- 3 yang / 3 yin hexagrams: entropy = ln(20) ≈ 3.0 (maximum uncertainty)

Route queries to hexagram processes whose entropy matches the query's uncertainty:
- Well-defined query (clear intent) → low-entropy hexagram
- Ambiguous query (fuzzy intent) → high-entropy hexagram

### 5c: Hexagram Synergy Detection
**File**: `polyglot/whitemagic-rs/crates/wm-evolution/src/hexagram_hrr.rs`
**Concept**: Use `hrr_composition::compute_synergy` to detect which hexagram pairs produce superlinear effects:
- Synergy > 1: the combination is more effective than either alone
- Synergy < 1: the combination interferes (sublinear)
- Synergy ≈ 1: additive (no interaction)

This produces a 64×64 synergy heatmap — a taxonomy of archetypal interactions.

---

## Phase 6: SIMD Integration

### 6a: 64-Lane Hexagram SIMD Execution
**New file**: `core/whitemagic-rust/src/hexagram_simd.rs`
**Concept**: All 64 hexagram processes execute the same instruction on different data:
```
SIMD instruction: "compute_resonance(coords)"
→ Lane 0 (Hex 1): compute on newly-ingested memory coords
→ Lane 1 (Hex 2): compute on consolidation-queue coords
...
→ Lane 63 (Hex 64): compute on exploration-frontier coords
```

**AVX-512**: 64 × 8-bit hexagram states fit in one 512-bit register
**Fallback**: Scalar loop when AVX-512 unavailable (use existing `simd.status` capability detection)

### 6b: Wire into gana_tail
**File**: `core/whitemagic/core/handlers/acceleration.py` or equivalent
**Change**: Register hexagram SIMD operations as Tail Gana tools:
- `hexagram_simd.dispatch`: Route query to hexagram process via SIMD
- `hexagram_simd.batch`: Run 64 parallel computations
- `hexagram_simd.interaction`: Compute hexagram pair interactions

### 6c: I/O Channel Gating
**File**: `core/whitemagic-rust/src/iching_dispatch.rs`
**Concept**: Each hexagram's 6 lines gate I/O channels:
- Yin line (0) = channel closed
- Yang line (1) = channel open
- Moving line = channel in transition (flush + reopen)

I/O-light hexagrams run at full SIMD speed. I/O-heavy ones use separate threads with rendezvous at dream phase boundaries.

---

## Execution Order

| Step | Phase | Effort | Depends On |
|------|-------|--------|------------|
| 1 | 1a: Analytical oscillator | Low | — |
| 2 | 1b: FFT crate for HRR | Low | — |
| 3 | 1c: Sobol QMC | Low | — |
| 4 | 1d: Claim-specific Beta precision | Low | — |
| 5 | 1e: Stratified lead-time noise | Low | — |
| 6 | 2a: Expand iching.rs | Medium | — |
| 7 | 2b: Trigram compute/I/O modes | Medium | 2a |
| 8 | 2c: Hexagram dispatch matrix | Medium | 2a, 2b |
| 9 | 3a: Resonance-based selection | Medium | 1a, 2a |
| 10 | 3b: Galactic zone frequencies | Low | 1a |
| 11 | 3c: Kuramoto dream cycle | Medium | — |
| 12 | 4a: Beta-calibrated lines | Low | 2a |
| 13 | 4b: Boltzmann hexagram selection | Low | 2a, thermodynamic.rs |
| 14 | 5a: Hexagram HRR encoding | Medium | 1b, 2a |
| 15 | 5b: Entropy-matched routing | Low | 2a, 5a |
| 16 | 5c: Hexagram synergy detection | Low | 5a |
| 17 | 6a: 64-lane SIMD execution | High | 2b, 2c |
| 18 | 6b: Wire into gana_tail | Medium | 6a |
| 19 | 6c: I/O channel gating | Medium | 2b, 6a |

**Phased execution**:
- **Phase 1 (steps 1-5)**: All independent, can be done in parallel
- **Phase 2 (steps 6-8)**: Sequential within phase
- **Phase 3 (steps 9-11)**: 9 depends on 1a+2a, 10 depends on 1a, 11 independent
- **Phase 4 (steps 12-13)**: Both depend on 2a
- **Phase 5 (steps 14-16)**: Sequential within phase, depends on 1b+2a
- **Phase 6 (steps 17-19)**: Sequential, depends on Phase 2

---

## Testing Strategy

- Every new function gets unit tests in its Rust module
- Analytical oscillator: compare against scipy RK45 solution (keep scipy as test fixture)
- FFT replacement: compare bind/unbind output with old DFT implementation
- Sobol QMC: verify variance reduction vs random sampling
- I Ching expansion: verify all 64 hexagram trigram decompositions, moving line transformations
- Resonance selection: verify each hexagram produces distinct oscillator parameters
- Kuramoto: verify synchronization index converges for coupled identical oscillators
- HRR hexagram: verify 64×64 interaction matrix is symmetric
- SIMD: verify scalar fallback produces same results as SIMD path

## Dependency Changes

| Crate | Dependency | Version | Purpose |
|-------|-----------|---------|---------|
| wm-evolution | rustfft | 0.1 | O(n log n) FFT for HRR |
| wm-evolution | rand | 0.8 | Better RNG (already in whitemagic-rust, add to wm-evolution) |
| whitemagic-rust | (none new) | — | iching.rs already in this crate |

## Files Modified/Created

**Modified**:
- `core/whitemagic/core/resonance/julia_resonance.py` — analytical oscillator, galactic zone frequencies
- `core/whitemagic-rust/src/iching.rs` — stochastic casting, trigram decomposition, second hexagram
- `core/whitemagic-rust/src/monte_carlo.rs` — claim-specific precision, stratified noise
- `polyglot/whitemagic-rs/crates/wm-evolution/src/hrr_composition.rs` — replace DFT with rustfft
- `polyglot/whitemagic-rs/crates/wm-evolution/src/mc_integration.rs` — Sobol sequences
- `polyglot/whitemagic-rs/crates/wm-evolution/Cargo.toml` — add rustfft, rand dependencies
- `polyglot/whitemagic-rs/crates/wm-evolution/src/lib.rs` — export new modules
- `polyglot/whitemagic-rs/crates/wm-evolution/examples/evolution_bridge.rs` — new bridge methods

**Created**:
- `core/whitemagic-rust/src/iching_dispatch.rs` — trigram modes, dispatch matrix, Boltzmann selection
- `core/whitemagic-rust/src/iching_resonance.rs` — resonance-based hexagram selection
- `core/whitemagic-rust/src/hexagram_simd.rs` — 64-lane SIMD execution
- `polyglot/whitemagic-rs/crates/wm-evolution/src/kuramoto.rs` — coupled dream cycle oscillators
- `polyglot/whitemagic-rs/crates/wm-evolution/src/hexagram_hrr.rs` — HRR hexagram encoding + interactions
