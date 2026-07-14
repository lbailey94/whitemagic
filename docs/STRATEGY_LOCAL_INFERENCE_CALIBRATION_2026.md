# Strategy: Local Model Wiring, Speculative Decoding, and Depth Gauge Calibration

**Date**: 2026-07-12
**Version**: v25.0.0
**Scope**: Integration strategy for three interrelated inference infrastructure systems

---

## Executive Summary

Three systems form the local inference backbone of WhiteMagic:

1. **Local Model Wiring** — LlamaCppBackend + 4-tier router + ModelDiscovery (12 GGUF models available)
2. **Speculative Decoding** — Python-level draft/verify pipeline + llama-server native `--spec-type` support
3. **DepthGauge Calibration** — Time prediction recording + Brier/CRPS scoring + machine-time estimation

All three are **functionally implemented but not fully integrated**. The code paths exist, tests pass, but there are wiring gaps, duplicate systems, and missing feedback loops. This document identifies the gaps and prescribes a phased integration plan.

---

## 1. Local Model Wiring

### 1.1 Current State

**LlamaCppBackend** (`core/whitemagic/inference/llama_cpp.py`, 770 lines):
- Full HTTP client for llama-server: `complete()`, `complete_with_tokens()`, `chat()`, `embed()`, `tokenize()`
- Server lifecycle: `start_server()` (subprocess, 120s timeout), `stop_server()`, auto-discovery
- `LlamaCppConfig` with 25+ CLI flags: KV cache quantization (q8_0), speculative decoding params, parallel slots, JSON schema constraints, Jinja templating
- `DualModelManager` — background (small, continuous) + foreground (large, on-demand) model management
- `BinaryManager` — discovers llama-server binary across 5 search paths
- Singleton via `get_llama_cpp_backend()` with env-var model auto-discovery

**ModelDiscovery** (`core/whitemagic/interfaces/chat.py`):
- 13 model env vars (`WM_MODEL_QWEN3_4B`, `WM_MODEL_PHI4_MINI`, etc.)
- Preferred order: qwen3-4b > phi4-mini > qwen3-1.7b > qwen2.5-1.5b > ...
- GGUF search across 6 paths, skips vocab test files
- `best_model()` — env vars → preferred name → size-range → any

**InferenceRouter** (`core/whitemagic/inference/router.py`, 1019 lines):
- 4-tier routing: edge (rules) → local_small (llama.cpp) → local_large (llama.cpp/BitNet) → cloud
- `_get_small_backend()` — env: `WM_MODEL_SMALL` → `WM_MODEL_QWEN3_1_7B` → ModelDiscovery
- `_get_large_backend()` — env: `WM_MODEL_LARGE` → `WM_MODEL_QWEN3_4B` → ModelDiscovery
- Complexity classifier with confidence cascading
- Token budget tracker with EMA-based prediction
- Speculative route method with fallback

**MCP Handlers** (`tools/handlers/llama_tools.py`):
- `handle_llama_chat` — multi-turn chat with WhiteMagic memory context injection
- `handle_llama_generate` — single-turn completion
- `handle_llama_agent` — autonomous loop initiation
- `handle_llama_models` — list available GGUF models

**System Inventory** (verified 2026-07-12):
- `llama-server` binary: `~/.local/bin/llama-server` (version 1, build a646006)
- 12 GGUF models in `~/models/`: qwen3-4b, qwen3-1.7b, qwen3-8b, phi4-mini, smollm2-360m, llama-3.2-1b, qwen2.5-1.5b, falcon3-1b, bitnet, glm4-9b, deepseek-r1-7b, qwen2.5vl-7b
- `~/llama.cpp/build/bin/llama-server` also present

### 1.2 Identified Gaps

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| L1 | No auto-start on MCP boot — backends lazily created on first inference call | First inference has 30-120s cold-start delay | Medium |
| L2 | `DualModelManager` exists but isn't wired into the router | Router uses separate singletons, misses background/foreground optimization | Low |
| L3 | `speculative_wiring.py` has hardcoded model paths | Not portable, doesn't use ModelDiscovery | Medium |
| L4 | No health monitoring / restart on llama-server crash | Silent failures, degraded to cloud tier | Medium |
| L5 | No model warm-up (first inference is slow due to prompt processing) | Latency spike on first use | Low |
| L6 | `LlamaCppConfig.spec_type` defaults to `ngram-mod` but this is server-side spec decoding, separate from the Python `SpeculativeDecoder` | Two speculative systems running simultaneously could conflict | High |

### 1.3 Recommendations

**Phase 1 — Consolidation (Low effort, High value)**:
- Wire `DualModelManager` into the router as the primary backend manager. Replace `_get_small_backend()` and `_get_large_backend()` with `DualModelManager.background` and `.foreground`.
- Add `WM_MODEL_BACKGROUND` and `WM_MODEL_FOREGROUND` env vars that map to `DualModelManager` constructor.
- Remove `speculative_wiring.py` hardcoded paths — use `ModelDiscovery` instead.

**Phase 2 — Resilience (Medium effort, High value)**:
- Add health check to `LlamaCppBackend._check_availability()` with periodic polling (every 30s).
- Auto-restart on crash: if `is_available` returns False and `_process` is not None, call `start_server()`.
- Add `WM_LLAMA_AUTO_START=1` env var to auto-start backends on MCP server boot via `run_mcp_lean.py`.

**Phase 3 — Performance (Low effort, Medium value)**:
- Add `warmup()` method to `LlamaCppBackend` — sends a minimal prompt to pre-load model weights.
- Call `warmup()` on background model after `start_server()` succeeds.
- Expose `warmup` as an MCP tool (`llama.warmup`).

---

## 2. Speculative Decoding

### 2.1 Current State

**Python-Level SpeculativeDecoder** (`core/whitemagic/inference/speculative_decoder.py`, 351 lines):
- `SpeculativeDecoder` class with draft + verify handler registration
- `generate()` — multi-round loop: draft K tokens → verify K tokens → accept/reject → repeat
- `_accept_reject()` — token-level comparison:
  - Accept tokens where `draft[i] == verify[i]`
  - At first mismatch: accept verify's token as correction, reject remaining draft tokens
  - If verify shorter: reject extra draft tokens
- Adaptive K — decreases when acceptance rate < `min_accept_rate`, increases when > 0.8 (capped at 8)
- `SpeculativeStats` — total calls, accepted/rejected, draft/verify latency, speedup estimation
- Singleton via `get_speculative_decoder()`

**Router Wiring** (`router.py`):
- `_draft_handler` — uses `_get_draft_backend()` (SmolLM2-360M or small model) via `complete_with_tokens()`
- `_verify_handler` — uses `_get_large_backend()` (Qwen3-4B or Phi4-mini) via `complete_with_tokens()`
- `get_speculative_router()` — registers handlers with decoder singleton
- `speculative_route()` — routes through speculative decoding with fallback to normal routing

**Alternative Wiring** (`speculative_wiring.py`):
- `_bitmamba_draft_handler` — BitMamba-2 255M via autonomic daemon
- `_llamacpp_verify_handler` — llama.cpp backend (text-only, no tokens)
- `_bitnetcpp_verify_handler` — bitnet.cpp CLI (text-only, no tokens)

**Llama-Server Native Speculative Decoding** (in `LlamaCppConfig`):
- `spec_type = "ngram-mod"` (default) — server-side ngram hash pool, ~16MB, no draft model needed
- Supports: `ngram-simple`, `ngram-map-k`, `ngram-mod`, `draft-simple`, `draft-eagle3`, `draft-dflash`, `draft-mtp`
- EAGLE-3: 2-3x speedup with trained draft model (e.g., `AngelSlim/Qwen3-4B_eagle3`)
- Config: `spec_ngram_mod_n_match=24`, `spec_ngram_mod_n_min=48`, `spec_ngram_mod_n_max=64`

**Tests** (`tests/unit/test_speculative_decoder.py`, 516 lines):
- 20+ mock-based tests: accept/reject logic, adaptive K, stats tracking, multi-round, router wiring
- No E2E tests with actual models

### 2.2 Identified Gaps

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| S1 | **Two parallel speculative systems** — Python `SpeculativeDecoder` (token comparison) vs. llama-server native `--spec-type ngram-mod` | Conflict: if both run, the server does its own spec decoding AND the Python layer tries to compare tokens from two separate server instances | **Critical** |
| S2 | **Tokenizer mismatch** — SmolLM2-360M (draft) and Qwen3-4B (verify) use different tokenizers. Token IDs won't match even for identical text | `_accept_reject()` compares token IDs — will reject almost everything, making the Python decoder useless | **Critical** |
| S3 | `complete_with_tokens()` falls back to `tokenize()` when server doesn't return token IDs | Double-tokenization overhead + potential inconsistency between generation and post-hoc tokenization | High |
| S4 | `speculative_wiring.py` verify handlers return empty tokens (text-only) | Breaks `_accept_reject()` which expects token IDs | High |
| S5 | No E2E test with actual models | Can't verify real-world acceptance rates or speedup | Medium |
| S6 | No EAGLE-3 draft model integration despite config support | Missing 2-3x speedup opportunity | Low |

### 2.3 Recommendations

**Phase 1 — Resolve Architecture Conflict (Critical)**:

The fundamental decision: **use llama-server native speculative decoding OR the Python-level SpeculativeDecoder, not both.**

**Recommended: Use llama-server native spec decoding as primary; keep Python decoder as fallback for non-llama.cpp backends.**

Rationale:
- llama-server's ngram-mod is zero-config, ~16MB overhead, shared across slots
- EAGLE-3 support is native and achieves 2-3x speedup
- The Python decoder's token-level comparison requires same-tokenizer models, which constrains model selection
- The Python decoder adds latency (two HTTP round-trips per round vs. server-internal single forward pass)

Actions:
1. **Disable Python speculative decoding when using llama-server backends** — in `LlamaCppConfig`, `spec_type="ngram-mod"` is already the default. The server handles spec decoding internally.
2. **Keep Python `SpeculativeDecoder` for cross-backend scenarios** — e.g., BitMamba draft + llama.cpp verify. But add a **text-based comparison fallback** when token IDs are unavailable or tokenizers differ.
3. **Add tokenizer compatibility check** — in `_draft_handler` and `_verify_handler`, compare tokenizer vocab sizes or sample token IDs for the same text. If incompatible, fall back to text comparison or disable Python speculative decoding.
4. **Remove `speculative_wiring.py` hardcoded paths** — use `ModelDiscovery`.

**Phase 2 — Text-Based Comparison Fallback (High value)**:

Add a `_text_accept_reject()` method to `SpeculativeDecoder` that compares generated text character-by-character instead of token IDs. Use this when:
- Token IDs are empty (llama-server didn't return them)
- Tokenizers are incompatible (different vocab sizes)

```python
def _text_accept_reject(
    self, draft_text: str, verify_text: str
) -> tuple[str, str]:
    """Text-level comparison fallback for incompatible tokenizers."""
    accepted = ""
    rejected = ""
    for i, (d_char, v_char) in enumerate(zip(draft_text, verify_text)):
        if d_char == v_char:
            accepted += d_char
        else:
            accepted += v_char  # correction from verify
            rejected = draft_text[i+1:]
            break
    return accepted, rejected
```

**Phase 3 — EAGLE-3 Integration (Future, High value)**:

- Download `AngelSlim/Qwen3-4B_eagle3` GGUF draft model
- Configure `LlamaCppConfig` with `spec_type="draft-eagle3"`, `draft_model_path=<eagle3.gguf>`
- This gives 2-3x speedup with no Python overhead
- Requires EAGLE-3 model conversion via `convert_hf_to_gguf.py --target-model-dir`

**Phase 4 — E2E Testing (Medium value)**:

- Test 1: ngram-mod only (server-side) — verify speedup with repeated text prompts
- Test 2: draft-simple with SmolLM2-360M draft + Qwen3-4B verify (same tokenizer family if possible)
- Test 3: Python decoder with text fallback (cross-backend scenario)
- Measure: acceptance rate, tokens/s, latency vs. baseline

---

## 3. DepthGauge Calibration / Time Tracking

### 3.1 Current State

**Three Parallel Calibration Systems**:

#### System A: DepthGauge → TemporalForecastDB (Subjective Time)
- `ConsciousnessDepthGauge` (`depth_gauge.py`) — 4 layers (SURFACE/TERMINAL/FLOW/DREAM) with compression ratios (1x/2.5x/4x/10x)
- `begin_task(description, estimated_subjective_minutes)` → records prediction to `TemporalForecastDB` with confidence from `_layer_to_confidence()` (static: 0.50/0.65/0.75/0.85)
- `end_task(work_output, token_usage)` → resolves prediction (validate if actual ≤ predicted, falsify otherwise)
- `get_calibration()` — queries `TemporalForecastDB` for `time_estimate` category, computes Brier score
- `predict_objective_time()` — divides subjective estimate by current layer's compression ratio

#### System B: MachineTimeEstimator → PredictionCalibration (Machine Time)
- `MachineTimeEstimator` (`machine_time.py`) — per-tool duration prediction from historical telemetry
- `predict(tool_name)` — returns `EffortPrediction` with p50/p90/p99, confidence, effort tier
- `record_actual(tool_name, duration, prediction)` — updates history, computes CRPS
- `_correction_factors` — per-tool multipliers to adjust biased predictions
- `PredictionCalibration` (`prediction_calibration.py`) — tracks estimates vs actuals
- `record_auto()` — auto-wiring entry point, computes CRPS using Gaussian approximation
- `get_calibration_score()` — Brier score on binary "within 2x" + CRPS + log-ratio error + per-layer/per-type breakdown
- `get_adjusted_estimate()` — Bayesian shrinkage with prior (3.0x compression, weight 5)

#### System C: TemporalForecastDB + Brier (Prescience Track Record)
- `TemporalForecastDB` (`forecasting/temporal_db.py`) — SQLite-backed prediction ledger
- `brier.py` — Brier score, Brier Skill Score, calibration curve, resolution, decomposition
- Used primarily for prescience claims (AI SBOM, Karma Ledger, etc.)
- DepthGauge writes `time_estimate` category predictions here

#### Auto-Wiring in Dispatch Pipeline
- `unified_api.py` lines 447-518:
  1. Before tool call: `MachineTimeEstimator.predict(canonical)` → `EffortPrediction`
  2. After tool call: `MachineTimeEstimator.record_actual(canonical, duration, prediction)`
  3. After tool call: `PredictionCalibration.record_auto(task_id, description, est_seconds, actual_seconds, task_type)`

### 3.2 Identified Gaps

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| D1 | **Three parallel systems don't share data** — DepthGauge writes to TemporalForecastDB, MachineTimeEstimator writes to `machine_time.jsonl`, PredictionCalibration writes to `calibration.jsonl` | No unified calibration view; each system has partial data | **Critical** |
| D2 | **No feedback loop** — `PredictionCalibration.get_adjusted_estimate()` exists but isn't called by `MachineTimeEstimator.predict()` | Predictions don't improve over time despite data accumulation | High |
| D3 | **`MachineTimeEstimator._correction_factors` is separate from `PredictionCalibration`** — two correction systems, neither authoritative | Conflicting adjustments | High |
| D4 | **DepthGauge confidence is static** (0.50/0.65/0.75/0.85) — doesn't learn from actual calibration data | Overconfident at deep layers, underconfident at surface | Medium |
| D5 | **No MCP tool exposes calibration metrics** — agent can't see its own calibration score | Agent can't self-correct estimates | Medium |
| D6 | **`DepthGauge.get_calibration()` and `PredictionCalibration.get_calibration_score()` compute separate Brier scores** — no unified metric | Conflicting calibration reports | Medium |
| D7 | **CRPS computation in `PredictionCalibration.record_auto()` uses fixed sigma (20% of prediction)** — doesn't learn from historical variance | Overconfident for high-variance tools, underconfident for low-variance ones | Low |

### 3.3 Recommendations

**Phase 1 — Unify Calibration Data (Critical)**:

Make `MachineTimeEstimator` the single source of truth for machine-time calibration. `PredictionCalibration` becomes a consumer, not a separate store.

Actions:
1. **`MachineTimeEstimator.predict()` calls `PredictionCalibration.get_adjusted_estimate()`** — apply Bayesian shrinkage correction to the median-based prediction.
2. **`MachineTimeEstimator.record_actual()` feeds `PredictionCalibration.record_auto()`** — single recording path, not two separate ones in `unified_api.py`.
3. **Remove the separate `PredictionCalibration.record_auto()` call from `unified_api.py`** — it's redundant when `MachineTimeEstimator` does it.
4. **`DepthGauge.get_calibration()` queries `PredictionCalibration` instead of `TemporalForecastDB`** — unified calibration view.

**Phase 2 — Dynamic Confidence (High value)**:

Replace static `_layer_to_confidence()` with learned confidence from historical calibration data.

Actions:
1. In `DepthGauge.begin_task()`, query `PredictionCalibration` for per-layer accuracy rate.
2. Use the rolling accuracy rate (last 20 tasks at this layer) as the confidence value.
3. Fall back to static values (0.50/0.65/0.75/0.85) when insufficient data (< 5 tasks).
4. Log the confidence source (learned vs. default) in the prediction notes.

**Phase 3 — Adaptive Sigma (Medium value)**:

Replace fixed sigma (20% of prediction) with historical variance.

Actions:
1. In `MachineTimeEstimator.predict()`, compute IQR from historical durations for this tool.
2. Use `sigma = IQR / 1.35` (IQR-to-std conversion) instead of `0.2 * predicted_seconds`.
3. Fall back to 20% when insufficient data (< 3 samples).
4. Pass sigma to `PredictionCalibration.record_auto()`.

**Phase 4 — MCP Exposure (Medium value)**:

Add MCP tools so the agent can query and use its own calibration data.

Actions:
1. `calibration.score` — returns unified calibration metrics (Brier, CRPS, by-layer, by-type)
2. `calibration.estimate` — given a tool name, returns the predicted duration + confidence interval
3. `calibration.history` — returns recent estimates vs actuals for review
4. Map to `gana_heart` (self-awareness cluster)

**Phase 5 — DepthGauge ↔ MachineTime Bridge (Low priority)**:

Connect subjective time (DepthGauge) and machine time (MachineTimeEstimator) so they inform each other.

Actions:
1. When `DepthGauge.begin_task()` is called, also call `MachineTimeEstimator.predict()` for the same task to get a machine-time estimate.
2. Record both estimates in the prediction notes.
3. After `end_task()`, compare both predictions to actual and update both systems.
4. Use the ratio between subjective and machine time as an additional calibration signal.

---

## 4. Integration Roadmap

### Phase 1: Critical Fixes (1-2 sessions)

| Task | System | Effort | Impact |
|------|--------|--------|--------|
| Disable Python spec decoding when using llama-server native spec | Speculative | Low | Eliminates S1 conflict |
| Add text-based comparison fallback to `SpeculativeDecoder` | Speculative | Low | Fixes S2, S4 |
| Unify calibration recording path (MachineTimeEstimator → PredictionCalibration) | Calibration | Medium | Resolves D1, D2, D3 |
| Wire `DualModelManager` into router as primary backend manager | Local Model | Medium | Resolves L2 |

### Phase 2: High-Value Improvements (2-3 sessions)

| Task | System | Effort | Impact |
|------|--------|--------|--------|
| Add health monitoring + auto-restart to LlamaCppBackend | Local Model | Medium | Resolves L4 |
| Dynamic confidence from calibration history in DepthGauge | Calibration | Medium | Resolves D4 |
| Adaptive sigma from historical variance in MachineTimeEstimator | Calibration | Medium | Resolves D7 |
| MCP tools for calibration metrics | Calibration | Medium | Resolves D5 |
| Remove hardcoded paths in speculative_wiring.py | Speculative | Low | Resolves L3 |

### Phase 3: Performance Optimization (Future)

| Task | System | Effort | Impact |
|------|--------|--------|--------|
| EAGLE-3 draft model integration | Speculative | High | 2-3x speedup |
| Model warmup on server start | Local Model | Low | Reduces cold-start latency |
| Auto-start backends on MCP boot | Local Model | Low | Resolves L1 |
| DepthGauge ↔ MachineTime bridge | Calibration | Medium | Cross-system calibration |
| E2E speculative decoding tests with real models | Speculative | Medium | Validates real-world performance |

---

## 5. Key Architecture Decisions

### Decision 1: llama-server native spec decoding as primary

**Rationale**: The Python `SpeculativeDecoder` adds latency (two HTTP round-trips per round) and requires same-tokenizer models. llama-server's ngram-mod is zero-config, ~16MB, shared across slots, and EAGLE-3 achieves 2-3x speedup natively.

**Trade-off**: Loses cross-backend speculative decoding (e.g., BitMamba + llama.cpp). The text-based fallback preserves this capability but with lower accuracy.

### Decision 2: MachineTimeEstimator as calibration source of truth

**Rationale**: It has the richest data (per-tool, per-type, historical, correction factors) and is already auto-wired in the dispatch pipeline. PredictionCalibration becomes a scoring layer on top, not a separate recording system.

**Trade-off**: DepthGauge's subjective-time predictions become secondary. They're still valuable for consciousness layer tracking but not for machine-time calibration.

### Decision 3: DualModelManager as router backend manager

**Rationale**: It already manages background/foreground model lifecycle. The router's separate singletons (`_small_backend`, `_large_backend`) duplicate this functionality without the background/foreground optimization.

**Trade-off**: Requires refactoring router handlers to use `DualModelManager.background` and `.foreground` properties. Minimal API change but touches the hot path.

---

## 6. File Inventory

### Local Model Wiring
- `core/whitemagic/inference/llama_cpp.py` — LlamaCppBackend, LlamaCppConfig, DualModelManager, BinaryManager (770 lines)
- `core/whitemagic/interfaces/chat.py` — ModelDiscovery, ModelInfo (1101 lines)
- `core/whitemagic/inference/router.py` — InferenceRouter, handlers, speculative wiring (1019 lines)
- `core/whitemagic/tools/handlers/llama_tools.py` — MCP handlers (453 lines)

### Speculative Decoding
- `core/whitemagic/inference/speculative_decoder.py` — SpeculativeDecoder, SpeculativeResult, SpeculativeStats (351 lines)
- `core/whitemagic/inference/speculative_wiring.py` — Alternative handlers with hardcoded paths (199 lines)
- `core/tests/unit/test_speculative_decoder.py` — Mock-based tests (516 lines)

### DepthGauge Calibration
- `core/whitemagic/core/consciousness/depth_gauge.py` — ConsciousnessDepthGauge (398 lines)
- `core/whitemagic/core/consciousness/prediction_calibration.py` — PredictionCalibration, TaskEstimate (473 lines)
- `core/whitemagic/core/consciousness/machine_time.py` — MachineTimeEstimator, EffortPrediction (591 lines)
- `core/whitemagic/core/consciousness/time_dilation.py` — TimeDilationMonitor (304 lines)
- `core/whitemagic/forecasting/temporal_db.py` — TemporalForecastDB (461 lines)
- `core/whitemagic/forecasting/brier.py` — Brier scoring utilities (217 lines)
- `core/whitemagic/tools/unified_api.py` — Auto-wiring in dispatch pipeline (1080 lines)

---

## 7. External Research Context

### llama.cpp Speculative Decoding (2026)
- **ngram-mod**: Hash pool (~16MB), shared across slots, zero-config. Best for repeated text (code editing, summarization, reasoning models repeating thinking). Default in llama-server.
- **EAGLE-3**: SOTA speculative decoding, 2-3x speedup. One-layer transformer trained for specific target model. Reads target hidden states. Available models: `AngelSlim/Qwen3-4B_eagle3`, `AngelSlim/Qwen3-8B_eagle3`.
- **draft-simple**: Standalone draft model, requires compatible tokenizer. Less efficient than EAGLE-3 but works with any model pair.
- **Comma-separated types**: Can combine `ngram-mod,draft-simple` for hybrid speculation.

### CRPS (Continuous Ranked Probability Score)
- Proper scoring rule for continuous predictions (generalization of Brier score)
- Incentivizes honest, well-calibrated probabilistic forecasts
- Used in meteorology, ensemble forecasting (AIFS-CRPS, ECMWF)
- Formula for Gaussian: `CRPS = σ * [z * (2Φ(z) - 1) + 2φ(z) - 1/√π]` where `z = (actual - prediction) / σ`
- Lower is better. 0 = perfect prediction.
- WhiteMagic already implements this correctly in `machine_time.py` and `prediction_calibration.py`

### Brier Score Decomposition
- `BS = reliability - resolution + uncertainty`
- Reliability: how well probabilities match observed frequencies (lower = better)
- Resolution: how much forecasts vary from base rate (higher = better)
- Uncertainty: inherent variability of the event (fixed)
- WhiteMagic implements full decomposition in `brier.py`
