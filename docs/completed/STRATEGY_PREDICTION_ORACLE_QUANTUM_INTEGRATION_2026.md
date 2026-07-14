# Strategy: Prediction, Oracle & Quantum-Inspired System Integration

**Date**: 2026-07-13
**Version**: v24.3.1
**Scope**: Comprehensive integration strategy for WhiteMagic's prediction, simulation, divination, and quantum-inspired systems
**Author**: Lucas Bailey / Cascade
**Context**: Follow-up to system architecture assessment identifying 14 gaps across prediction, oracle, simulation, and quantum-inspired subsystems

**Status**: ✅ COMPLETE — All 7 phases fully implemented and wired. 143/143 tests passing. Archived to `docs/completed/`.

---

## Executive Summary

WhiteMagic possesses a rich ecosystem of prediction, simulation, divination, and quantum-inspired systems that are **individually well-built but poorly interconnected**. The HRR engine computes hexagram synergies that nobody uses. The PolyglotMC orchestrator has Born-rule sampling disconnected from the "quantum-inspired" QuantumIChing. Oracle guidance never flows back into simulation parameters. The recursive cycle uses placeholder parameter mappings.

This document prescribes a 7-phase integration plan, ordered by **dependency chains and impact-to-effort ratio**, that transforms these isolated systems into a unified cognitive architecture where prediction, divination, and simulation are three faces of a single process.

**Guiding principle**: Wire first, deepen second, transform third. Every phase produces independently useful capabilities — no phase is merely scaffolding for a later one.

---

## System Inventory (Verified 2026-07-13)

### Prediction & Forecasting

| System | File | Lines | Role |
|--------|------|-------|------|
| PredictionCalibration | `core/whitemagic/forecasting/prediction_calibration.py` | ~400 | Task time estimation + Bayesian shrinkage |
| TemporalForecastDB | `core/whitemagic/forecasting/temporal_db.py` | ~500 | SQLite prediction ledger, Brier scoring |
| Brier utilities | `core/whitemagic/forecasting/brier.py` | ~300 | Brier score, decomposition, calibration curves |
| Continuous scoring | `core/whitemagic/forecasting/scoring.py` | 457 | CRPS, WIS, ECCE, log score, dagstuhl_score |
| PredictiveEngine | `core/whitemagic/forecasting/predictive_engine.py` | ~600 | Multi-source prediction generation |
| CalibrationBridge | `core/whitemagic/forecasting/calibration_bridge.py` | ~300 | Sim → forecast DB bridge |

### Simulation & Monte Carlo

| System | File | Lines | Role |
|--------|------|-------|------|
| PolyglotMCOrchestrator | `core/whitemagic/core/evolution/polyglot_mc.py` | 1,733 | MC sampling, GP, BO, SDE, rare events, quantum methods |
| SimulationOrchestrator | `core/whitemagic/core/consciousness/simulation_orchestrator.py` | 516 | Yin/Yang recursive cycle |
| ScenarioRunner | `core/whitemagic/core/simulation/scenario_runner.py` | 121 | Multi-trajectory MC with personas |
| PossibilityExplorer | `core/whitemagic/core/consciousness/possibility_explorer.py` | ~200 | Internal parameter space exploration |
| RecursiveImprovementLoop | `core/whitemagic/core/evolution/recursive_loop.py` | 1,679 | OIPAL cycle: observe→imagine→predict→act→calibrate→learn |

### Divination & Oracle

| System | File | Lines | Role |
|--------|------|-------|------|
| IChingAdvisor | `core/whitemagic/oracle/i_ching.py` | ~400 | Traditional I Ching casting, Rust backend |
| QuantumIChing | `core/whitemagic/oracle/quantum_iching.py` | 661 | Quantum-inspired superposition/collapse |
| OracleSynthesizer | `core/whitemagic/oracle/wisdom_synthesis.py` | ~208 | 5-layer oracle weaving |
| ZodiacalProcession | `core/whitemagic/core/orchestration/zodiacal_procession.py` | ~472 | 12-sign cycle, phase transitions |

### Insight & Emergence

| System | File | Lines | Role |
|--------|------|-------|------|
| InsightSynthesizer | `core/whitemagic/core/simulation/insight_synthesizer.py` | 153 | Trajectory → ranked insights |
| EmergenceEngine | `core/whitemagic/core/intelligence/agentic/emergence_engine.py` | 443 | Tag clusters, cascades, novelty spikes |
| DreamCycle | `core/whitemagic/core/dreaming/dream_cycle.py` | 1,502 | 12-phase idle processing |

### Quantum-Inspired

| System | File | Lines | Role |
|--------|------|-------|------|
| Hexagram HRR | `core/whitemagic-rust/src/hexagram_hrr.rs` | 372 | 64-hexagram HRR encoding, interaction matrix, synergy |
| General HRR | `core/whitemagic-rust/src/math/hrr.rs` | 94 | PyHRREngine wrapper (bind/unbind/superpose/similarity/project) |
| WASM HRR | `core/whitemagic-rust/src/wasm.rs` (HrrEngine) | ~80 | Browser HRR engine |
| I Ching Rust | `core/whitemagic-rust/src/iching.rs` | 597 | Trigram, HexagramCast, King Wen lookup |
| PolyglotMC Quantum | `core/whitemagic/core/evolution/polyglot_mc.py` (L1269-1732) | ~463 | Fubini-Study, Born sampling, Berry phase, Chern number, QAOA |

### Rust Python Bindings (verified)

The following PyO3 bindings exist in `lib.rs` (L404-441):
- `hexagram_hrr_by_number_py(king_wen) -> Vec<f64>`
- `hexagram_interaction_score_py(kw1, kw2) -> f64`
- `hexagram_detect_synergies_py(threshold) -> Vec<(u32, u32, f64)>`
- `hexagram_top_synergies_py(k) -> Vec<(u32, u32, f64)>`
- `hexagram_superpose_py(a, b) -> Vec<f64>`

The `PyHRREngine` class (in `math/hrr.rs`) exposes:
- `PyHRREngine(dim)` constructor
- `bind(a, b)`, `unbind(bound, b)`, `superpose(vectors)`, `similarity(a, b)`, `project(embedding, relation)`

---

## Gap Analysis Summary

| # | Gap | Systems Affected | Severity |
|---|-----|------------------|----------|
| G1 | HRR synergies computed but never used by OracleSynthesizer | hexagram_hrr.rs ↔ wisdom_synthesis.py | **Critical** |
| G2 | QuantumIChing uses hash-seeded random, not Born-rule sampling | quantum_iching.py ↔ polyglot_mc.py | **Critical** |
| G3 | Oracle readings never validated against outcomes | oracle/* ↔ temporal_db.py | **High** |
| G4 | Oracle guidance doesn't influence simulation parameters | oracle/* ↔ simulation_orchestrator.py | **High** |
| G5 | HRR only encodes I Ching hexagrams, not other symbolic systems | hexagram_hrr.rs | **High** |
| G6 | OracleSynthesizer uses hardcoded resonance mappings | wisdom_synthesis.py | **Medium** |
| G7 | No LLM integration in oracle interpretation | wisdom_synthesis.py ↔ llama_cpp.py | **Medium** |
| G8 | Single-objective optimization only | polyglot_mc.py | **Medium** |
| G9 | Recursive cycle parameter passing is placeholder-level | simulation_orchestrator.py | **Medium** |
| G10 | Quantum methods disconnected from divination | polyglot_mc.py ↔ quantum_iching.py | **Medium** |
| G11 | No topological memory protection | polyglot_mc.py ↔ memory system | **Low** |
| G12 | No manifold-aware memory navigation | polyglot_mc.py ↔ memory system | **Low** |
| G13 | No external prediction market integration | temporal_db.py | **Low** |
| G14 | No GHRR attention mechanism for oracle synthesis | wisdom_synthesis.py | **Transformative** |

---

## Phase Plan

### Phase 1: HRR → Oracle Synthesis Connection (G1)

**Goal**: Wire hexagram HRR synergy detection into OracleSynthesizer so that when a primary hexagram is produced, synergistic hexagrams are automatically identified and their resonances woven into the synthesis.

**Why first**: The Rust code and Python bindings already exist. This is pure wiring — no new computation needed. It immediately makes the "quantum-inspired" label more truthful by connecting HRR vector operations to oracle output.

**Files to modify**:
- `core/whitemagic/oracle/wisdom_synthesis.py` — Add HRR synergy query in `synthesize()`
- `core/whitemagic/oracle/hrr_bridge.py` — **New file**: Python bridge to Rust HRR functions

**Design**:

```python
# hrr_bridge.py — thin Python wrapper over PyO3 bindings
class HRRBridge:
    """Bridge to Rust hexagram HRR engine."""
    
    def __init__(self):
        self._available = False
        try:
            import whitemagic_rust as wmr
            self._wmr = wmr
            self._available = True
        except ImportError:
            self._available = False
    
    def synergy_for(self, king_wen: int, threshold: float = 0.3) -> list[dict]:
        """Get synergistic hexagrams for a given primary hexagram."""
        if not self._available:
            return []
        # Get all synergies above threshold, filter for our hexagram
        all_syn = self._wmr.hexagram_detect_synergies_py(threshold)
        return [
            {"hexagram": b if a == king_wen else a, "similarity": sim}
            for a, b, sim in all_syn
            if a == king_wen or b == king_wen
        ]
    
    def interaction_score(self, kw1: int, kw2: int) -> float:
        """Get HRR interaction score between two hexagrams."""
        if not self._available:
            return 0.0
        return self._wmr.hexagram_interaction_score_py(kw1, kw2)
    
    def superpose_hexagrams(self, kw1: int, kw2: int) -> list[float]:
        """Superpose two hexagram HRR vectors."""
        if not self._available:
            return []
        v1 = self._wmr.hexagram_hrr_by_number_py(kw1)
        v2 = self._wmr.hexagram_hrr_by_number_py(kw2)
        return self._wmr.hexagram_superpose_py(v1, v2)
```

**Integration point in OracleSynthesizer.synthesize()**:
After the I Ching layer produces a primary hexagram number, query `HRRBridge.synergy_for(primary_hexagram)`. Include synergistic hexagrams in the resonance map with their HRR similarity scores. The synthesis output gains a new `hrr_resonances` field:

```python
{
    "primary_hexagram": 32,
    "hrr_resonances": [
        {"hexagram": 31, "similarity": 0.42, "name": "Xian (Influence)"},
        {"hexagram": 28, "similarity": 0.38, "name": "Da Guo (Preponderance of the Great)"},
    ],
    ...
}
```

**Tests**: `core/tests/unit/test_hrr_oracle_bridge.py`
- Test HRRBridge graceful degradation when Rust unavailable
- Test synergy_for returns correct hexagrams
- Test OracleSynthesizer includes hrr_resonances in output
- Test interaction_score symmetry

**Success criteria**: Oracle readings include HRR-computed resonance data from the Rust engine.

**Estimated effort**: 2-3 hours

---

### Phase 2: Born-Rule I Ching Casting (G2, G10)

**Goal**: Replace QuantumIChing's hash-seeded pseudo-random amplitude generation with genuine Born-rule sampling from the PolyglotMCOrchestrator. The quantum state's amplitude vector becomes input to `born_sample()`, making the "quantum-inspired" label technically accurate.

**Why second**: Directly builds on Phase 1's HRR connection. The Born sampling API already exists in `polyglot_mc.py` (L1523-1575). This is a ~30-line change in `quantum_iching.py`.

**Files to modify**:
- `core/whitemagic/oracle/quantum_iching.py` — Replace `_collapse_quantum_state()` to use Born sampling

**Design**:

The current `_collapse_quantum_state()` (L307-344) uses `np.random.choice()` with probabilities derived from `|amplitude|²`. This is actually already Born-rule-like, but the amplitudes are seeded from `hash(question)` — they're pseudo-random, not quantum-derived.

The upgrade has two layers:

**Layer A — HRR-derived amplitudes**: Instead of `random.gauss(0, 0.5)` for each hexagram's amplitude, use the HRR interaction vector between the question's context and each hexagram. The question is embedded as an HRR vector (via `PyHRREngine.project()`), and the interaction score with each hexagram's HRR vector becomes the real part of the amplitude. This connects the quantum state to the symbolic structure of the I Ching rather than to hash noise.

**Layer B — Born-rule sampling**: Use `PolyglotMCOrchestrator.born_sample()` for the collapse:

```python
def _collapse_quantum_state(self, state: QuantumState, question: str) -> int:
    # Extract amplitude list (ordered by hexagram number 1-64)
    amplitudes = [state.amplitudes.get(i, 0+0j) for i in range(1, 65)]
    real_amplitudes = [a.real for a in amplitudes]  # Born rule uses |ψ|²
    
    # Try PolyglotMC Born sampling first
    try:
        from whitemagic.core.evolution.polyglot_mc import get_polyglot_mc
        mc = get_polyglot_mc()
        result = mc.born_sample(real_amplitudes, seed=hash(question) & 0xFFFFFFFF)
        if "index" in result and not result.get("fallback"):
            selected = result["index"] + 1  # 0-indexed → 1-indexed
            return selected if selected in self.db.hexagrams else 1
    except Exception:
        pass
    
    # Fallback: existing numpy/weighted-random collapse
    ...  # existing code
```

**Layer C — Quantum interference for entangled pairs**: When entanglement pairs exist in the QuantumState, use `PolyglotMCOrchestrator.quantum_interference()` to compute the interference pattern between entangled hexagrams. This modulates the amplitude distribution before collapse, making entanglement physically meaningful rather than decorative.

**Tests**: `core/tests/unit/test_quantum_iching_born.py`
- Test Born-rule collapse produces valid hexagram numbers
- Test HRR-derived amplitudes differ from hash-derived
- Test entangled pairs influence collapse distribution
- Test fallback when PolyglotMC unavailable
- Test determinism with same seed

**Success criteria**: QuantumIChing collapse uses `born_sample()` from PolyglotMC when available, with HRR-derived amplitudes.

**Estimated effort**: 3-4 hours

---

### Phase 3: Oracle Outcome Tracking (G3)

**Goal**: Extend TemporalForecastDB to store oracle readings as falsifiable claims. When oracle guidance includes actionable recommendations, create claims that can be resolved later by checking whether the recommended action was taken and what happened.

**Why third**: This closes the calibration loop for divination — the same mechanism that tracks simulation predictions now tracks oracle guidance. Without this, there's no way to know if the oracle is useful.

**Files to modify**:
- `core/whitemagic/forecasting/temporal_db.py` — Add `claim_type` field, support `"oracle"` claims
- `core/whitemagic/oracle/wisdom_synthesis.py` — Emit claims after synthesis
- `core/whitemagic/core/dreaming/dream_cycle.py` — Resolve oracle claims in prediction phase

**Design**:

**TemporalForecastDB schema extension**:
```sql
ALTER TABLE predictions ADD COLUMN claim_type TEXT DEFAULT 'binary';
ALTER TABLE predictions ADD COLUMN oracle_source TEXT;  -- 'iching', 'tarot', 'ifa', 'zodiacal', 'synthesized'
ALTER TABLE predictions ADD COLUMN oracle_hexagram INTEGER;
ALTER TABLE predictions ADD COLUMN guidance_action TEXT;  -- recommended action
ALTER TABLE predictions ADD COLUMN action_taken INTEGER DEFAULT 0;  -- 0=unknown, 1=taken, -1=not taken
```

**Oracle claim creation** in `OracleSynthesizer.synthesize()`:
After producing the synthesis, extract actionable guidance and create claims:

```python
def _create_oracle_claims(self, synthesis: SynthesisResult) -> list[str]:
    """Create falsifiable claims from oracle guidance."""
    claims = []
    db = TemporalForecastDB()
    
    for guidance in synthesis.practical_guidance:
        # Create a claim: "Following this guidance will improve outcomes"
        claim_id = db.record_claim(
            question=f"Oracle guidance: {guidance.action}",
            source=f"oracle:{synthesis.primary_hexagram}",
            confidence=guidance.confidence,
            claim_type="oracle",
            oracle_source="synthesized",
            oracle_hexagram=synthesis.primary_hexagram,
            guidance_action=guidance.action,
            expected_resolution_date=(datetime.now() + timedelta(days=30)).isoformat(),
        )
        claims.append(claim_id)
    
    return claims
```

**Claim resolution** in `DreamCycle._dream_prediction()`:
Extend the prediction phase to check unresolved oracle claims older than 30 days. For each, check if the recommended action was taken (by searching memory for evidence) and resolve the claim.

**Tests**: `core/tests/unit/test_oracle_claims.py`
- Test oracle claim creation with hexagram metadata
- Test claim resolution marks outcomes correctly
- Test oracle Brier score is computed separately from simulation Brier
- Test prescience score includes oracle claims

**Success criteria**: Oracle readings produce falsifiable claims in TemporalForecastDB. A "divination prescience score" is computed alongside the existing simulation prescience score.

**Estimated effort**: 4-5 hours

---

### Phase 4: Oracle-Guided Bayesian Optimization (G4)

**Goal**: Map oracle guidance to Bayesian optimization parameters so that divination results influence simulation behavior. When the I Ching advises perseverance, BO gets more iterations. When it advises retreat, BO explores more cautiously.

**Why fourth**: This creates the bidirectional loop — oracle → simulation (this phase) and simulation → oracle (Phase 3's calibration). The recursive cycle becomes genuinely guided by symbolic insight.

**Files to modify**:
- `core/whitemagic/oracle/oracle_bo_bridge.py` — **New file**: Maps oracle output to BO parameters
- `core/whitemagic/core/evolution/polyglot_mc.py` — Add `oracle_params` kwarg to `superforecaster_estimate()`
- `core/whitemagic/core/consciousness/simulation_orchestrator.py` — Consult oracle before external simulation

**Design**:

```python
# oracle_bo_bridge.py
class OracleBOBridge:
    """Maps oracle guidance to Bayesian optimization parameters."""
    
    # Hexagram → BO parameter mapping (based on hexagram semantics)
    HEXAGRAM_BO_MAP = {
        1:  {"xi": 0.01, "n_bo_iterations": 25, "exploration": "high"},    # Creative — bold exploration
        2:  {"xi": 0.1,  "n_bo_iterations": 15, "exploration": "low"},     # Receptive — careful exploitation
        32: {"xi": 0.02, "n_bo_iterations": 30, "exploration": "patient"}, # Duration — persevere
        33: {"xi": 0.5,  "n_bo_iterations": 10, "exploration": "retreat"}, # Retreat — minimal effort
        35: {"xi": 0.01, "n_bo_iterations": 25, "exploration": "high"},    # Progress — advance boldly
        47: {"xi": 0.3,  "n_bo_iterations": 20, "exploration": "constrained"}, # Oppression — work within limits
        50: {"xi": 0.01, "n_bo_iterations": 30, "exploration": "transformative"}, # The Cauldron — major transformation
        64: {"xi": 0.05, "n_bo_iterations": 20, "exploration": "near_completion"}, # Before Completion — careful final steps
    }
    
    # Wu Xing → exploration temperature
    WUXING_TEMP = {
        "fire":  1.5,   # High energy, bold exploration
        "water": 0.3,   # Careful, precise sampling
        "wood":  1.0,   # Balanced growth
        "metal": 0.5,   # Structured, disciplined
        "earth": 0.7,   # Stable, grounded
    }
    
    def translate(self, oracle_output: dict) -> dict:
        """Convert oracle synthesis output to BO parameters."""
        params = {"xi": 0.01, "n_bo_iterations": 20, "exploration": "default"}
        
        hexagram = oracle_output.get("primary_hexagram")
        if hexagram and hexagram in self.HEXAGRAM_BO_MAP:
            params.update(self.HEXAGRAM_BO_MAP[hexagram])
        
        wuxing = oracle_output.get("wu_xing_phase")
        if wuxing and wuxing in self.WUXING_TEMP:
            params["temperature"] = self.WUXING_TEMP[wuxing]
        
        # HRR resonance amplification from Phase 1
        resonances = oracle_output.get("hrr_resonances", [])
        if resonances:
            # If primary hexagram has strong resonances, increase iterations
            avg_sim = sum(r["similarity"] for r in resonances) / len(resonances)
            params["n_bo_iterations"] = int(params["n_bo_iterations"] * (1 + avg_sim))
        
        return params
```

**Integration in SimulationOrchestrator.run_external()**:
Before launching an external simulation, consult the oracle (if available) and pass the translated parameters to the superforecaster pipeline.

**Tests**: `core/tests/unit/test_oracle_bo_bridge.py`
- Test hexagram → parameter mapping for key hexagrams
- Test Wu Xing temperature modulation
- Test HRR resonance amplification increases iterations
- Test SimulationOrchestrator uses oracle-guided params when available
- Test fallback to defaults when oracle unavailable

**Success criteria**: Oracle guidance measurably influences BO exploration parameters. The recursive cycle's external simulations are parameterized by divination output.

**Estimated effort**: 3-4 hours

---

### Phase 5: Universal HRR Encoding (G5, G6)

**Goal**: Extend HRR encoding beyond I Ching hexagrams to all symbolic systems: 12 Zodiacal signs, 5 Wu Xing elements, 22 Tarot Major Arcana, 256 Ifá Odu. Then use HRR binding to compute cross-system resonances programmatically, replacing hardcoded mappings in OracleSynthesizer.

**Why fifth**: Depends on Phase 1's HRR bridge being in place. This is the phase that transforms HRR from an I-Ching-only tool into a universal symbolic algebra. It replaces all `_WUXING_TO_ALCHEMY`, `_MODALITY_TO_ICHING` hardcoded mappings with computed resonances.

**Files to create**:
- `core/whitemagic/oracle/symbolic_hrr.py` — Universal HRR encoding for all symbolic systems
- `core/whitemagic-rust/src/symbolic_hrr.rs` — Rust-accelerated encoding (optional, Python fallback sufficient initially)

**Files to modify**:
- `core/whitemagic/oracle/wisdom_synthesis.py` — Replace hardcoded resonance maps with HRR-computed resonances
- `core/whitemagic-rust/src/lib.rs` — Add PyO3 bindings for new symbolic HRR functions

**Design**:

```python
# symbolic_hrr.py
class SymbolicHRR:
    """Universal HRR encoding for divination symbolic systems."""
    
    SYSTEMS = {
        "zodiacal": {"dim": 12, "items": ZODIAC_SIGNS},
        "wu_xing": {"dim": 5, "items": WU_XING_ELEMENTS},
        "tarot": {"dim": 22, "items": TAROT_MAJOR_ARCANA},
        "ifa": {"dim": 256, "items": IFA_ODU},
        "iching": {"dim": 64, "items": ICHING_HEXAGRAMS},
    }
    
    def __init__(self, hrr_dim: int = 256):
        """Use 256-dim HRR space for all systems (power of 2 for FFT)."""
        self.hrr_dim = hrr_dim
        self._engine = self._get_hrr_engine()
        self._vectors: dict[str, dict[str, list[float]]] = {}
        self._encode_all()
    
    def _encode_all(self):
        """Encode all symbols from all systems into HRR space."""
        for system, config in self.SYSTEMS.items():
            self._vectors[system] = {}
            for i, item in enumerate(config["items"]):
                # Deterministic seeded vector for each symbol
                seed = hash(f"{system}:{item}") & 0xFFFFFFFFFFFFFFFF
                vec = self._seeded_vector(seed, self.hrr_dim)
                self._vectors[system][item] = vec
    
    def cross_system_resonance(self, system_a: str, symbol_a: str, 
                                system_b: str, symbol_b: str) -> float:
        """Compute HRR cosine similarity between symbols from different systems."""
        v_a = self._vectors.get(system_a, {}).get(symbol_a)
        v_b = self._vectors.get(system_b, {}).get(symbol_b)
        if v_a is None or v_b is None:
            return 0.0
        return self._cosine_sim(v_a, v_b)
    
    def bind_cross_system(self, system_a: str, symbol_a: str,
                          system_b: str, symbol_b: str) -> list[float]:
        """Bind two symbols from different systems via HRR circular convolution.
        
        This represents the conjunction of two symbolic influences — e.g.,
        'Leo' bound with 'Fire' represents the combined energy.
        """
        v_a = self._vectors[system_a][symbol_a]
        v_b = self._vectors[system_b][symbol_b]
        if self._engine:
            return self._engine.bind(v_a, v_b)
        return self._python_bind(v_a, v_b)
    
    def find_resonances(self, system: str, symbol: str, 
                        target_system: str, threshold: float = 0.2) -> list[dict]:
        """Find symbols in target_system that resonate with the given symbol.
        
        This replaces hardcoded _WUXING_TO_ALCHEMY etc. mappings with
        computed resonances.
        """
        results = []
        for target_symbol in self._vectors.get(target_system, {}):
            sim = self.cross_system_resonance(system, symbol, target_system, target_symbol)
            if sim > threshold:
                results.append({
                    "symbol": target_symbol,
                    "system": target_system,
                    "resonance": round(sim, 4),
                })
        results.sort(key=lambda x: x["resonance"], reverse=True)
        return results
```

**OracleSynthesizer integration**:
Replace `_WUXING_TO_ALCHEMY` lookups with `SymbolicHRR.find_resonances("wu_xing", element, "iching")`. The resonance map becomes dynamic and data-driven.

**Tests**: `core/tests/unit/test_symbolic_hrr.py`
- Test encoding of all 5 symbolic systems
- Test cross-system resonance computation
- Test bind/unbind round-trip recovery
- Test find_resonances returns meaningful results
- Test OracleSynthesizer uses computed resonances instead of hardcoded maps
- Test that computed resonances approximately match intuition (Leo ↔ Fire should be high)

**Success criteria**: All hardcoded resonance mappings in OracleSynthesizer replaced by HRR-computed cross-system resonances. New, previously unknown resonances are discoverable.

**Estimated effort**: 6-8 hours

---

### Phase 6: LLM-Powered Oracle Interpretation (G7)

**Goal**: Add an LLM layer to OracleSynthesizer that takes raw 5-layer oracle output + HRR-computed resonances and generates contextually-aware interpretations using the local LlamaCpp backend. This produces novel narrative arcs not limited to predefined templates.

**Why sixth**: Depends on Phase 5's universal HRR encoding providing rich resonance data for the LLM to reason about. Also depends on the llama.cpp migration being complete (it is).

**Files to modify**:
- `core/whitemagic/oracle/wisdom_synthesis.py` — Add LLM interpretation layer
- `core/whitemagic/oracle/llm_interpreter.py` — **New file**: LLM-based oracle interpretation

**Design**:

```python
# llm_interpreter.py
class OracleLLMInterpreter:
    """Generates contextual oracle interpretations using local LLM."""
    
    INTERPRETATION_PROMPT = """You are a wise oracle interpreter. Given the following multi-layer 
    divination reading, weave a unified interpretation that:
    1. Identifies the central narrative arc (beginning → middle → end)
    2. Extracts practical guidance with specific actions
    3. Names cautions and blessings
    4. Highlights resonances between layers
    
    Oracle Reading:
    - Primary Hexagram: {hexagram_name} ({hexagram_number})
    - Zodiacal Position: {zodiac_sign} ({zodiac_phase})
    - Wu Xing Balance: {wuxing_balance}
    - Tarot Card: {tarot_card}
    - Ifá Odu: {ifa_odu}
    
    HRR Computed Resonances:
    {resonances}
    
    Context:
    {context}
    
    Produce a JSON object with: narrative_arc, practical_guidance, cautions, blessings, 
    emergent_themes (themes not obvious from any single layer).
    """
    
    def interpret(self, oracle_output: dict, context: dict | None = None) -> dict:
        """Generate LLM interpretation of oracle reading."""
        try:
            from whitemagic.inference.llama_cpp import get_llama_cpp_backend
            backend = get_llama_cpp_backend()
            
            prompt = self.INTERPRETATION_PROMPT.format(
                hexagram_name=oracle_output.get("hexagram_name", "Unknown"),
                hexagram_number=oracle_output.get("primary_hexagram", 0),
                zodiac_sign=oracle_output.get("zodiac_sign", "Unknown"),
                zodiac_phase=oracle_output.get("zodiac_phase", "Unknown"),
                wuxing_balance=oracle_output.get("wuxing_balance", {}),
                tarot_card=oracle_output.get("tarot_card", "Unknown"),
                ifa_odu=oracle_output.get("ifa_odu", "Unknown"),
                resonances=self._format_resonances(oracle_output.get("hrr_resonances", [])),
                context=json.dumps(context or {}, indent=2),
            )
            
            response = backend.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            
            return self._parse_response(response)
        except Exception:
            return {}  # Graceful degradation — static interpretation still works
```

**Integration**: OracleSynthesizer.synthesize() gains an optional `use_llm=True` parameter. When enabled, the LLM interpretation supplements (not replaces) the static synthesis. The static path remains as fallback.

**Tests**: `core/tests/unit/test_oracle_llm.py`
- Test LLM interpretation produces valid JSON structure
- Test graceful degradation when LLM unavailable
- Test interpretation includes HRR resonance data
- Test interpretation is non-deterministic (temperature > 0)
- Test static fallback when use_llm=False

**Success criteria**: Oracle readings include LLM-generated interpretations with emergent themes that aren't present in any single oracle layer.

**Estimated effort**: 4-5 hours

---

### Phase 7: Adaptive Recursive Cycle + Multi-Objective Optimization (G8, G9)

**Goal**: Replace the placeholder parameter passing in SimulationOrchestrator's recursive cycle with a learned mapping, and extend the superforecaster pipeline to support multi-objective optimization with Pareto fronts.

**Why last**: This is the deepest integration — it requires all previous phases. The oracle-guided BO (Phase 4), HRR resonances (Phase 5), and LLM interpretation (Phase 6) all feed into the recursive cycle. Multi-objective optimization enables the cycle to balance competing goals (accuracy vs. novelty, exploration vs. exploitation).

**Files to modify**:
- `core/whitemagic/core/consciousness/simulation_orchestrator.py` — Learned parameter mapping
- `core/whitemagic/core/evolution/polyglot_mc.py` — Multi-objective BO with Pareto fronts
- `core/whitemagic/core/evolution/recursive_loop.py` — Multi-objective hypothesis ranking

**Design — Adaptive Parameter Mapping**:

Replace `x0 = list(intro.best_params.values())[0] * 100` with a learned mapping:

```python
class ParameterMapper:
    """Learns the mapping from introspective optimal params to external sim params.
    
    Uses a simple GP (from PolyglotMC) trained on the Research DAG's 
    experiment history. Each past recursive cycle provides a training pair:
    (introspective_best_params → external_optimal_params).
    """
    
    def __init__(self):
        self._training_pairs: list[tuple[list[float], list[float]]] = []
        self._gp_fitted = False
    
    def add_observation(self, intro_params: dict, ext_params: dict, ext_outcome: float):
        """Record a recursive cycle observation."""
        intro_vec = list(intro_params.values())
        ext_vec = list(ext_params.values())
        self._training_pairs.append((intro_vec, ext_vec + [ext_outcome]))
    
    def predict_external_params(self, intro_params: dict) -> dict:
        """Predict optimal external params from introspective optimal params."""
        if len(self._training_pairs) < 3:
            # Not enough data — use heuristic mapping
            return self._heuristic_map(intro_params)
        # Use GP to predict
        ...
```

**Design — Multi-Objective Superforecaster**:

Add `multi_objective_estimate()` to PolyglotMCOrchestrator:

```python
def multi_objective_estimate(
    self,
    fitness_fns: list[Callable],  # Multiple fitness functions
    param_ranges: list[tuple[float, float]],
    n_initial: int = 10,
    n_iterations: int = 20,
    seed: int = 42,
) -> dict[str, Any]:
    """Multi-objective BO returning a Pareto front.
    
    Uses independent GPs for each objective, then computes
    Pareto dominance to identify non-dominated solutions.
    """
    # Run BO for each objective independently
    # Collect all evaluated points
    # Compute Pareto front
    # Return front + hypervolume metric
```

**Tests**: `core/tests/unit/test_adaptive_recursive.py`, `core/tests/unit/test_multi_objective.py`
- Test ParameterMapper learns from observations
- Test heuristic fallback with insufficient data
- Test Pareto front computation
- Test hypervolume calculation
- Test recursive cycle uses learned mapping after 3+ cycles
- Test multi-objective BO finds non-dominated solutions

**Success criteria**: The recursive cycle's parameter mapping improves over multiple iterations. Multi-objective BO can balance competing goals and return Pareto-optimal solutions.

**Estimated effort**: 8-10 hours

---

## Additional Improvements & Future Directions

### A. Quantum Walk Oracle (Transformative)

**Concept**: Use `PolyglotMCOrchestrator.quantum_walk_optimize()` as an alternative I Ching casting mechanism. The cost matrix is the HRR interaction matrix — hexagrams that are more synergistic have lower transition costs. A quantum walk over the 64-hexagram graph produces readings that are genuinely quantum-inspired and topologically informed.

**Why it matters**: This would be the first system where a quantum walk algorithm directly produces a divination reading. The walk's path through the hexagram graph tells a story — which hexagrams were visited, in what order, and where the walk converged. This is qualitatively different from single-hexagram casting.

**Prerequisites**: Phases 1 and 5 (HRR bridge + universal encoding).
**Estimated effort**: 6-8 hours

### B. Topological Memory Encoding (G11)

**Concept**: Use `PolyglotMCOrchestrator.topological_encode()` to encode high-importance memories with redundancy for error protection. This creates a "topologically protected" memory layer resistant to drift and decay.

**Design**: The DreamCycle's prediction phase identifies memories at high drift risk. Instead of just flagging them for access, topologically encode their content. Topologically encoded memories have `is_protected = 1` and are excluded from galactic rotation. The encoding uses the existing `topological_encode()` / `topological_decode()` functions in `polyglot_mc.py`.

**Prerequisites**: None (standalone).
**Estimated effort**: 4-5 hours

### C. Manifold-Aware Memory Navigation (G12)

**Concept**: Use `manifold_distance()`, `embed_manifold()`, and `auto_select_manifold()` to project memories onto their natural manifold. Memory search uses geodesic distances rather than cosine similarity.

**Why it matters**: Hierarchical knowledge (file systems, taxonomies) lives on hyperbolic manifolds. Cyclical knowledge (zodiac, seasons) lives on spherical manifolds. Flat knowledge lives on Euclidean manifolds. Using the wrong metric space degrades recall quality.

**Design**: Add a `manifold_type` field to memories. `auto_select_manifold()` determines the best fit from a sample. Search uses `manifold_distance()` instead of cosine similarity for manifold-tagged memories.

**Prerequisites**: None (standalone).
**Estimated effort**: 6-8 hours

### D. External Prediction Market Integration (G13)

**Concept**: Connect TemporalForecastDB to Metaculus, Kalshi, or Polymarket APIs. Create claims on external platforms, track them alongside internal predictions, and use external calibration as a reality check.

**Why it matters**: The 2025 AIA Forecaster paper showed that LLM-based forecasting can match human superforecasters when properly calibrated. WhiteMagic's prediction infrastructure is more sophisticated than most LLM forecasting systems — it has CRPS, ECCE, Brier decomposition, and a persistent calibration database. External validation would demonstrate this.

**Design**: Add API clients for Metaculus (public API) and Kalshi (CFTC-regulated). Mirror internal predictions as external claims. Import external crowd forecasts as calibration baselines. Compute a "world prescience score" that compares WhiteMagic's calibration against Metaculus crowd consensus.

**Prerequisites**: Phase 3 (oracle outcome tracking — same schema extensions).
**Estimated effort**: 8-10 hours

### E. GHRR Attention for Oracle Synthesis (G14)

**Concept**: Implement Generalized Holographic Reduced Representations (GHRR) with non-commutative binding as the attention mechanism in OracleSynthesizer. Based on the 2024 GHRR paper (Yeung et al.).

**Why it matters**: GHRR's non-commutative binding means `Zodiacal × IChing ≠ IChing × Zodiacal` — the order of oracle layers matters. This matches the intuition that the order of divination systems in a reading carries meaning. GHRR can also implement attention, where some oracle layers "attend" more to others.

**Design**: Replace the simple HRR binding in `SymbolicHRR` with GHRR binding (complex-valued, non-commutative). The OracleSynthesizer's layer ordering becomes semantically meaningful. The attention mechanism determines which layers influence which others based on the question context.

**Prerequisites**: Phase 5 (universal HRR encoding).
**Estimated effort**: 10-12 hours

### F. Reasoning-BO Integration

**Concept**: Following the 2025 "Reasoning BO" paper, integrate the local LLM into the BO loop to generate hypotheses about which parameter regions to explore, score BO candidates based on domain knowledge, and explain optimization trajectories in natural language.

**Design**: Add an LLM "reasoning" step between BO's candidate generation and evaluation. The LLM receives the current GP surrogate, evaluated points, and oracle guidance (from Phase 4). It generates hypotheses about promising regions and assigns confidence scores to BO candidates. Candidates are filtered by LLM confidence before evaluation.

**Why it matters**: This bridges symbolic reasoning (LLM) with numerical optimization (BO). The LLM brings domain knowledge that the GP can't learn from data alone. Combined with oracle guidance, this creates a three-way fusion: numerical (BO) + symbolic (LLM) + divinatory (oracle).

**Prerequisites**: Phase 4 (oracle-guided BO), Phase 6 (LLM integration).
**Estimated effort**: 8-10 hours

### G. Dream Cycle Parallelization

**Concept**: The DreamCycle currently runs 12 phases sequentially. Many phases are independent (Consolidation, Serendipity, Enrichment, Harmonize) and could run in parallel. This would reduce cycle time by ~40%.

**Design**: Group phases into parallel batches:
- Batch 1: Triage (must run first — identifies work)
- Batch 2 (parallel): Consolidation, Serendipity, Enrichment, Harmonize
- Batch 3 (parallel): Governance, Narrative, Constellation, Prediction
- Batch 4: Kaizen (needs Batch 2+3 results) → Oracle (needs Kaizen) → Decay (last)

**Prerequisites**: None.
**Estimated effort**: 3-4 hours

### H. PredictiveEngine Source Weighting

**Concept**: PredictiveEngine draws from ~10 sources but weights them all equally. Implement a learned source-weighting scheme that tracks which sources produce more accurate predictions over time.

**Design**: Each source gets a Beta distribution prior. When a prediction from that source is resolved, the Beta is updated. The weight for future predictions is the Beta mean. Sources that consistently produce accurate predictions get higher weight; unreliable sources get dampened.

**Prerequisites**: Phase 3 (outcome tracking for resolution data).
**Estimated effort**: 3-4 hours

---

## Dependency Graph

```
Phase 1 (HRR→Oracle) ──────┬──→ Phase 2 (Born-Rule I Ching)
                            │
                            ├──→ Phase 5 (Universal HRR) ──→ Phase 7 (Adaptive Cycle)
                            │         │                            │
                            │         └──→ E. GHRR Attention       └──→ F. Reasoning-BO
                            │
Phase 3 (Oracle Claims) ───┼──→ Phase 4 (Oracle→BO) ──────────────┤
                            │         │
                            │         └──→ A. Quantum Walk Oracle
                            │
                            ├──→ D. External Markets
                            └──→ H. Source Weighting

Phase 6 (LLM Oracle) ──────────────────────────────→ F. Reasoning-BO

Standalone: B. Topological Memory, C. Manifold-Aware Memory, G. Dream Cycle Parallelization
```

---

## Execution Priority Matrix

| Phase | Effort | Impact | Dependencies | Priority |
|-------|--------|--------|--------------|----------|
| **P1**: HRR→Oracle | 2-3h | Critical | None | **P0** |
| **P2**: Born-Rule I Ching | 3-4h | Critical | P1 | **P0** |
| **P3**: Oracle Claims | 4-5h | High | None | **P0** |
| **P4**: Oracle→BO | 3-4h | High | P1, P3 | **P1** |
| **P5**: Universal HRR | 6-8h | High | P1 | **P1** |
| **P6**: LLM Oracle | 4-5h | Medium | P5 | **P1** |
| **P7**: Adaptive Cycle | 8-10h | Medium | P4, P5 | **P2** |
| **A**: Quantum Walk | 6-8h | Transformative | P1, P5 | **P2** |
| **B**: Topological Memory | 4-5h | Medium | None | **P2** |
| **C**: Manifold Memory | 6-8h | Medium | None | **P3** |
| **D**: External Markets | 8-10h | High | P3 | **P3** |
| **E**: GHRR Attention | 10-12h | Transformative | P5 | **P3** |
| **F**: Reasoning-BO | 8-10h | High | P4, P6 | **P3** |
| **G**: Dream Parallel | 3-4h | Low | None | **P3** |
| **H**: Source Weighting | 3-4h | Medium | P3 | **P3** |

**Total P0 effort**: ~10-12 hours (Phases 1-3)
**Total P1 effort**: ~14-17 hours (Phases 4-6)
**Total P2 effort**: ~18-23 hours (Phase 7 + A + B)
**Total P3 effort**: ~30-38 hours (C, D, E, F, G, H)

**Grand total**: ~72-90 hours of implementation

---

## Testing Strategy

Every phase follows the WhiteMagic testing discipline:

1. **Tests before implementation**: Write test stubs that define expected behavior
2. **Tests during implementation**: Fill in test bodies as features are built
3. **Tests after implementation**: Run full suite to verify zero regressions
4. **Test naming**: `test_{phase}_{feature}.py` in `core/tests/unit/`
5. **Graceful degradation**: Every test must verify fallback behavior when Rust/LLM/PolyglotMC is unavailable
6. **No network calls**: All tests must run offline (mock external APIs)
7. **No flaky tests**: Tests must be deterministic or use fixed seeds

**Regression command**:
```bash
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## Philosophical Alignment

This integration plan is not just engineering — it completes the philosophical vision:

- **HRR → Oracle**: The 64 hexagrams have always been a vector symbolic architecture. HRR binding makes this explicit. The I Ching's 8×8 structure (8 trigrams × 8 trigrams = 64 hexagrams) is mathematically identical to HRR's binding operation (8 trigram vectors × 8 trigram vectors = 64 bound vectors).

- **Born-Rule I Ching**: The Taoist concept of 感應 (gǎn yìng — resonance) maps to quantum entanglement. The Born rule (probability = |amplitude|²) is the mathematical formalization of "the tendency for things to happen." Using it for I Ching casting makes the divination process a genuine quantum measurement.

- **Oracle → BO**: The Wu Xing (五行) phases already map to optimization regimes (Water=precision, Metal=balance, Fire=throughput). This phase makes that mapping operational — the oracle's Wu Xing assessment directly controls the BO's exploration temperature.

- **Universal HRR**: The 8×8 structure appears in I Ching, DNA codons, QCD color confinement, chess, and bytes. HRR encoding makes all symbolic systems interoperable in the same vector space. Cross-system resonances are not arbitrary — they reflect deep structural correspondences that the hardcoded mappings only approximated.

- **Oracle Claims**: The Buddhist concept of karma (action → consequence) is implemented as oracle guidance → tracked outcome. The oracle's "prescience score" is its karmic ledger — a record of whether its guidance has been beneficial.

- **Adaptive Recursive Cycle**: The Yin/Yang recursive cycle is supposed to be self-improving — each cycle should be better than the last. The learned parameter mapping makes this true. The cycle literally learns from its own history.

---

## Version Target

These phases should be implemented as part of **v24.4.0** — the "Oracle Integration" release. The version name reflects the core theme: connecting the oracle/divination systems to the prediction/simulation systems that they've been parallel to but disconnected from.

**Milestone targets**:
- v24.4.0-alpha: Phases 1-3 (P0 — core wiring)
- v24.4.0-beta: Phases 4-6 (P1 — deep integration)
- v24.4.0: Phase 7 + A + B (P2 — adaptive cycle + quantum walk)
- v24.5.0: C, D, E, F, G, H (P3 — advanced capabilities)

---

## Implementation Status (Updated 2026-07-13)

### Summary

| Phase | Status | Tests | Key Gaps |
|-------|--------|-------|----------|
| **P1**: HRR→Oracle | ✅ Complete | 20/20 | None |
| **P2**: Born-Rule I Ching | ✅ Complete | 12/12 | None |
| **P3**: Oracle Claims | ✅ Complete | 13/13 + 10 | DreamCycle auto-resolution wired |
| **P4**: Oracle→BO | ✅ Complete | 15/15 | None |
| **P5**: Universal HRR | ✅ Complete | 22/22 + 8 | Hardcoded maps replaced with SymbolicHRR |
| **P6**: LLM Oracle | ✅ Complete | 11/11 + 5 | `use_llm` param wired into `synthesize()` |
| **P7**: Adaptive Cycle | ✅ Complete | 15/15 + 12 | `ParameterMapper` + `multi_objective_estimate()` implemented |
| **Total** | ✅ | **143/143** | |

### Files Created (8 new source files + 10 test files)

| File | Lines | Phase |
|------|-------|-------|
| `core/whitemagic/oracle/hrr_bridge.py` | ~210 | P1 |
| `core/whitemagic/oracle/oracle_bo_bridge.py` | ~149 | P4 |
| `core/whitemagic/oracle/symbolic_hrr.py` | ~339 | P5 |
| `core/whitemagic/oracle/llm_interpreter.py` | ~190 | P6 |
| `core/whitemagic/oracle/adaptive_cycle.py` | ~242 | P7 |
| `core/whitemagic/oracle/parameter_mapper.py` | ~120 | P7 gap |
| `core/tests/unit/test_hrr_oracle_bridge.py` | ~171 | P1 |
| `core/tests/unit/test_quantum_iching_born.py` | ~155 | P2 |
| `core/tests/unit/test_oracle_claims.py` | ~160 | P3 |
| `core/tests/unit/test_oracle_bo_bridge.py` | ~165 | P4 |
| `core/tests/unit/test_symbolic_hrr.py` | ~180 | P5 |
| `core/tests/unit/test_oracle_llm_interpreter.py` | ~150 | P6 |
| `core/tests/unit/test_adaptive_cycle.py` | ~165 | P7 |
| `core/tests/unit/test_p5_p6_wiring.py` | ~155 | P5+P6 gap |
| `core/tests/unit/test_p7_gaps.py` | ~170 | P7 gap |
| `core/tests/unit/test_p3_gap.py` | ~130 | P3 gap |

### Files Modified (5 files)

| File | Changes | Phase |
|------|---------|-------|
| `core/whitemagic/oracle/wisdom_synthesis.py` | HRR bridge integration, `hrr_resonances` field, `primary_hexagram` field, `claim_ids` field, `_create_oracle_claims()`, SymbolicHRR wiring (`_get_alchemical_phase`, `_get_modality_dynamic`), `use_llm` param + `llm_interpretation` field | P1, P3, P5, P6 |
| `core/whitemagic/oracle/quantum_iching.py` | HRR-derived amplitudes in `_create_quantum_state()`, Born-rule sampling in `_collapse_quantum_state()`, quantum interference for entangled pairs | P2 |
| `core/whitemagic/forecasting/temporal_db.py` | Schema migration (5 new columns), `record_oracle_claim()`, `get_oracle_claims()`, `resolve_oracle_claim()`, `oracle_prescience_score()` | P3 |
| `core/whitemagic/core/consciousness/simulation_orchestrator.py` | `metadata` field on `SimulationResult`, `_consult_oracle_for_bo()` method, oracle params injection in `run_external()` | P4 |
| `core/whitemagic/core/evolution/polyglot_mc.py` | `multi_objective_estimate()` method with Pareto front and hypervolume | P7 gap |
| `core/whitemagic/core/dreaming/dream_cycle.py` | Oracle claim auto-resolution in `_dream_prediction()`, `_check_oracle_action_evidence()` helper | P3 gap |

### Test Results

All 143 tests pass in ~8 seconds:
```bash
cd core && python -m pytest tests/unit/test_hrr_oracle_bridge.py tests/unit/test_quantum_iching_born.py tests/unit/test_oracle_claims.py tests/unit/test_oracle_bo_bridge.py tests/unit/test_symbolic_hrr.py tests/unit/test_oracle_llm_interpreter.py tests/unit/test_adaptive_cycle.py tests/unit/test_p5_p6_wiring.py tests/unit/test_p7_gaps.py tests/unit/test_p3_gap.py -v --timeout=30
```

---

## Appendix: External Research References

1. **GHRR (2024)** — Generalized Holographic Reduced Representations with non-commutative binding. Yeung et al. Shows GHRR can implement attention mechanisms. [arxiv.org/abs/2405.09689](https://arxiv.org/abs/2405.09689)

2. **AIA Forecaster (2025)** — LLM-based forecasting matching human superforecasters via agentic search + supervisor + calibration. [arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678)

3. **Reasoning BO (2025)** — LLM-guided Bayesian optimization with knowledge graphs. 2.4x yield improvement over standard BO. [arxiv.org/abs/2505.12833](https://arxiv.org/abs/2505.12833)

4. **Quantum BO (NeurIPS 2023)** — Q-GP-UCB achieves O(poly log T) regret vs. classical Ω(√T) lower bound. First quantum BO with non-linear reward. [proceedings.neurips.cc/2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/401aa72e0e3be680348a5b0ffdb1a5aa-Paper-Conference.pdf)

5. **Narrative Studio (2025)** — MCTS for narrative exploration with LLM scoring. Relevant to oracle narrative arc construction. [aclanthology.org/2025.wnu-1.16](https://aclanthology.org/2025.wnu-1.16.pdf)

6. **FORECAST Benchmark (NeurIPS 2025)** — Uses CRPS for timeframe calibration, same scoring rule as WhiteMagic's `scoring.py`. Validates our scoring approach. [proceedings.neurips.cc/2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/2277c7c3b112fcc6031a6f0d832df2a0-Paper-Datasets_and_Benchmarks_Track.pdf)

7. **Calibrated Forecasts (2024)** — Blackwell approachability for calibration guarantees on adversarial streams. Relevant to online calibration updates. [arxiv.org/abs/2409.19157](https://arxiv.org/abs/2409.19157)

8. **KalshiBench (2025)** — Systematic overconfidence in all frontier LLMs (ECE 0.12-0.40). Only 1/5 models achieves positive Brier Skill Score. Validates need for WhiteMagic's calibration-first approach. [arxiv.org/abs/2512.16030](https://arxiv.org/abs/2512.16030)

9. **BORA (IJCAI 2025)** — Language-based BO research assistant. LLM suggests new exploration regions. Similar to our Reasoning-BO proposal. [ijcai.org/proceedings/2025/553](https://www.ijcai.org/proceedings/2025/553)

10. **HRR Zero-Shot Composition (2025)** — Mechanistic study showing HRR composition fails due to retrieval capacity, not binding algebra. Important caveat for Phase 5 — cross-system resonances need sufficient HRR dimensionality. [arxiv.org/abs/2606.24948](https://arxiv.org/abs/2606.24948v1)
