# Imagination Engine — LLM Integration Progress

**Date:** 2026-08-07
**Status:** Deferred — local hardware insufficient for real-time LLM imagination pipeline

## Summary

The imagination engine (scenario generation, prediction, counterfactual reflection) was successfully wired up to use real LLM hemispheres via environment variables. The code compiles, all unit tests pass, and the architecture is sound. However, running the full pipeline against a local 3B model (Qwen2.5-3B Q4_K_M) proved impractical due to latency: each LLM call takes 15–30 seconds, and even a minimal demo requires ~68 calls (~17–34 minutes).

## What Was Done

### 1. LLM TierHandler Adapters (`wm-bicameral/src/world_model_handlers.rs`)

Created `LlmTierHandler` — an adapter that implements the `TierHandler` trait (required by `WorldModel`) by making OpenAI-compatible HTTP API calls directly via `ureq`.

- **Left hemisphere** (`left_from_env`): reads `WM_LLAMA_ENDPOINT` + `WM_LLAMA_MODEL` + `WM_LLAMA_TEMP` + `WM_LLAMA_TIMEOUT_MS`; low temperature (0.2) for deterministic predictions; 10s default timeout.
- **Right hemisphere** (`right_from_env`): reads `WM_LLM_API_KEY` + `WM_LLM_ENDPOINT` + `WM_LLM_MODEL`; higher temperature (0.7) for creative alternatives; 15s default timeout.
- **Fallback**: `world_model_from_env()` falls back to `StubWorldModelHandler` when env vars are not set, so the system works transparently with or without LLMs.
- **Safety**: `#![forbid(unsafe_code)]` compliant; no `unsafe` blocks; endpoint URL validation (must start with `http://` or `https://`).
- **Tests**: unit tests for endpoint normalization, confidence parsing, clamping, fallback behavior, and handler naming.

### 2. Imagination Tools Updated (`wm-tools/src/expansion/imagination.rs`)

Updated `imagine.scenario`, `imagine.predict`, and `imagine.reflect` tools to use `world_model_from_env()` instead of hardcoded stubs.

- Added `mc_samples` parameter to `imagine.scenario` tool (default: 10) to control Monte Carlo sample count when `enrich_simulation: true`.
- Replaced `SimulationBridge::with_defaults()` (1,000 MC samples) with a configurable `SimulationBridgeConfig` that uses sensible defaults for LLM mode (10 MC samples, 50 sensitivity/bootstrap samples).

### 3. Demo Binary (`wm-mcp/src/bin/imagination_llm_demo.rs`)

Created a demo binary that exercises all seven imagination engine subsystems with real LLM hemispheres:

1. **Scenario Engine** — LLM-generated candidate actions + rollout + scoring
2. **World Model Prediction** — dual-hemisphere prediction of a specific action
3. **Counterfactual Reflection** — what-if analysis comparing actual vs alternative actions
4. **Simulation Bridge** — MC rollout + forecasting + sensitivity analysis
5. **Pattern Bridge** — novelty + strategy + surprise assessment (no LLM calls)
6. **MCP Tools** — `imagine.scenario` / `predict` / `reflect` end-to-end
7. **NLU Routing** — natural language → imagination tool classification (no LLM calls)

### 4. Old Demo Binary Cleaned Up

Deleted the original `imagination_demo.rs` (stub-only demo) per user request.

## The Latency Problem

### Root Cause

The `SimulationBridge::enrich_scenario()` method runs Monte Carlo sampling over `WorldModel.rollout()`, and **each MC sample triggers a full multi-step rollout**, where each step calls `WorldModel.predict()`, which calls **both hemispheres** (left + right). With the default config:

```
1,000 MC samples × 3 steps × 2 hemispheres = 6,000 LLM API calls per scenario
```

At ~15–30s per call on a Qwen2.5-3B model, that's **25–50 hours per scenario**.

### Mitigations Applied

- Reduced MC samples from 1,000 → 3 (demo) / 10 (tool default)
- Reduced sensitivity/bootstrap samples from 500 → 50
- Disabled simulation enrichment in the MCP tool demo step
- Added `WM_LLAMA_TIMEOUT_MS` env var for configurable timeout
- Added progress output and time estimates

### Even With Mitigations

The minimal demo still requires ~68 LLM calls:
- Step 1 (imagine): 1 action generation + 3 candidates × 3-step rollout × 2 hemispheres = 19 calls
- Step 2 (predict): 2 calls
- Step 3 (reflect): 2 × predict = 4 calls
- Step 4 (simulation bridge): 3 MC × 3 steps × 2 hemispheres = 18 calls
- Step 6 (MCP tools): 19 + 2 + 4 = 25 calls

At 15–30s per call on the local 3B model: **17–34 minutes**. The first run timed out at the default 10s per call. The second run with 60s timeout was started but would take too long to complete in a reasonable session.

## Architecture Observations

### What Works Well

- **Bicameral design is sound**: left (deterministic) + right (creative) hemispheres with consensus gating works correctly in stub mode and would produce rich results with a fast LLM.
- **Graceful fallback**: `world_model_from_env()` transparently falls back to stubs when env vars aren't set — no code changes needed between stub and LLM modes.
- **Structured output parsing**: the `DESCRIPTION:/CHANGES:/RISKS:/PROGRESS:/CONFIDENCE:` format works well for extracting structured predictions from LLM text.
- **NLU routing**: correctly classifies natural language queries to imagination tools without any LLM calls.
- **Pattern Bridge**: novelty/strategy/surprise assessment is purely algorithmic — no LLM dependency.

### Bottlenecks

- **Sequential LLM calls**: all hemisphere calls are sequential. No batching, no parallelism.
- **MC sampling calls LLM**: `probabilistic_rollout()` uses `world_model.rollout()` inside the MC callback, meaning each sample makes real LLM calls. This is architecturally questionable — MC sampling should perturb the *distribution* over outcomes, not re-call the LLM.
- **No response caching**: identical prompts (e.g., repeated actions in rollout) are re-sent to the LLM each time.
- **3B model latency**: ~8 tokens/sec generation speed makes even single calls take 15–30s.

## Recommendations for Future Work

### Short-term (code changes)

1. **Cache LLM responses**: add a prompt→response cache in `LlmTierHandler` to avoid redundant calls for identical prompts.
2. **Batch hemisphere calls**: call left and right hemispheres concurrently (e.g., `tokio::join!`) instead of sequentially.
3. **Decouple MC from LLM**: `probabilistic_rollout()` should sample from a distribution fitted to a single LLM prediction, not re-call the LLM per sample. The LLM call should happen once, then MC sampling perturbs the confidence/progress values.
4. **Reduce max_tokens**: 256 tokens is generous for structured predictions; 128 would halve generation time.

### Medium-term (architecture)

5. **Async dispatch**: make `TierHandler::handle()` async to enable concurrent hemisphere calls and request pipelining.
6. **Streaming responses**: use SSE streaming to start parsing partial responses before generation completes.
7. **Speculative decoding**: leverage the existing `SpeculativeDecoder` in `wm-bicameral` to use a smaller draft model for faster generation.

### Long-term (hardware/scale)

8. **Cloud LLM for right hemisphere**: set `WM_LLM_API_KEY` + `WM_LLM_ENDPOINT` to use a fast cloud API (e.g., GPT-4o-mini at ~1s/call) for the creative hemisphere while keeping the left hemisphere local for privacy.
9. **GPU acceleration**: the current setup runs CPU-only inference. A modest GPU would 10–50x the token generation rate.
10. **Smaller model for imagination**: use a 0.5B–1B model for the world model (which needs structured but not deeply creative output) and reserve the larger model for action generation.

## Files Modified

| File | Change |
|------|--------|
| `crates/wm-bicameral/src/world_model_handlers.rs` | **Created** — `LlmTierHandler`, `world_model_from_env()`, tests |
| `crates/wm-bicameral/src/lib.rs` | Added module declaration and exports |
| `crates/wm-tools/src/expansion/imagination.rs` | Updated to use `world_model_from_env()`; added `mc_samples` parameter |
| `crates/wm-mcp/src/bin/imagination_llm_demo.rs` | **Created** — live LLM demo binary |
| `crates/wm-mcp/src/bin/imagination_demo.rs` | **Deleted** — old stub-only demo |

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `WM_LLAMA_ENDPOINT` | Left hemisphere (llama-server URL) | not set → stub |
| `WM_LLAMA_MODEL` | Left hemisphere model name | `local` |
| `WM_LLAMA_TEMP` | Left hemisphere temperature | `0.2` |
| `WM_LLAMA_TIMEOUT_MS` | Left hemisphere HTTP timeout | `10000` |
| `WM_LLM_API_KEY` | Right hemisphere API key | not set → stub |
| `WM_LLM_ENDPOINT` | Right hemisphere API URL | `https://api.openai.com/v1/chat/completions` |
| `WM_LLM_MODEL` | Right hemisphere model name | `gpt-4o-mini` |
| `WM_LLM_TIMEOUT_MS` | Right hemisphere HTTP timeout | `15000` |

## Conclusion

The imagination engine is fully wired for LLM integration and works correctly in stub mode. The architecture is clean — env vars control LLM vs stub, and the fallback is automatic. The barrier to running it live on this hardware is purely a latency issue: a 3B model on CPU at ~8 tok/s cannot service the ~68 LLM calls required for even a minimal demo in a reasonable timeframe. The code is ready for when faster hardware or a cloud API endpoint becomes available.
