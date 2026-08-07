# WhiteMagic v4 — Local AI Integration Roadmap

**Date**: August 4, 2026
**Status**: L1, L2, L3, L4, L5 COMPLETE — All local AI integration phases done
**Prerequisites**: Build optimization complete, all v2 source files verified on disk
**Related docs**: `local-ai-hemisphere-mapping-2026-08-03.md` (detailed architecture), `cyberbrain-roadmap-2026-08-03.md` (CyberBrain layers)

---

## 1. Current State

v4's bicameral engine has:
- **Left hemisphere**: LlamaLeftHemisphere (llama.cpp via OpenAI-compatible API, low temp) with heuristic fallback ✅ L2
- **Right hemisphere**: BitNet (local 1.58-bit, high temp) → LLM (cloud) → stub (heuristic) ✅ L3
- **Autonomic layer**: BitMamba daemon subprocess with salience processing ✅ L1
- **Inference router**: Complexity-aware routing with confidence cascading, token budget tracking, sensitivity detection ✅ L4
- **Local embedder**: HTTP-based embedder (llama-server /v1/embeddings) + stub fallback, trait-based ✅ L5

v2's local AI stack (all source files verified present on disk):
- **BitMamba-2 255M**: 247MB binary at `WHITEMAGIC-aux/models/bitmamba_255m.bin`, C++ daemon at `WHITEMAGIC-aux/bitmamba.cpp/examples/daemon.cpp`, Python wrapper at `core/whitemagic/inference/bitmamba_autonomic.py` (591 lines)
- **llama.cpp**: `llama-server` binary at `/home/lucas/.local/bin/llama-server`, Python backend at `core/whitemagic/inference/llama_cpp.py` (925 lines)
- **Inference router**: `core/whitemagic/inference/router.py` (1071 lines), `complexity.py` (361 lines)
- **Local embedder**: `core/whitemagic/inference/local_embedder.py` (313 lines)
- **BitNet**: `core/whitemagic/inference/bitnet_bridge.py` (226 lines), `WHITEMAGIC-aux/bitnet.cpp/`
- **Bicameral**: `core/whitemagic/core/intelligence/bicameral.py` (876 lines), `corpus_callosum.py` (426 lines)

---

## 2. Implementation Phases

### Phase L1: BitMamba Autonomic Layer — ✅ COMPLETE

**Goal**: Wrap the BitMamba daemon as a persistent autonomic layer that feeds salience signals into citta, drive, and workspace.

**New crate**: `wm-autonomic` ✅ Created

**Architecture**:
```
wm-autonomic (Rust)
├── BitMambaDaemon
│   ├── spawn bitmamba-daemon subprocess
│   ├── JSON lines protocol (stdin/stdout)
│   ├── send telemetry tokens (tool output, system events)
│   ├── receive salience signals (novelty/anomaly/emotional_shift/background)
│   ├── manage hidden state persistence (in daemon process)
│   └── graceful shutdown on Drop
├── SalienceProcessor
│   ├── classify signals → SalienceEvent enum
│   ├── feed into citta cycle (advance on novel/anomaly)
│   ├── feed into drive events (NovelInput, ResourcePressure)
│   └── feed into workspace publish
└── Env vars:
    WM_BITMAMBA_BIN (path to daemon binary)
    WM_BITMAMBA_MODEL (path to .bin)
    WM_AUTONOMIC_ENABLED (1/0, default 0)
```

**Integration points**:
1. `McpServer` startup — spawn daemon if `WM_BITMAMBA_BIN` is set
2. `handle_tools_call` — after dispatch, send tool output to autonomic layer
3. Citta cycle — poll for salience signals, advance on novel/anomaly
4. Drive events — autonomic salience → drive state changes
5. Workspace events — autonomic salience → workspace broadcast

**Fallback**: If `WM_BITMAMBA_BIN` not set or daemon fails, autonomic layer is disabled. Citta runs without salience (current behavior). No hard dependency.

**Key decisions**:
- Daemon is a subprocess, not a library — keeps C++ code separate
- JSON lines protocol (same as v2 daemon)
- Hidden state persists in daemon process, not in Rust
- Non-blocking — if daemon is slow, skip that cycle
- Salience polling at Reactive tier (10ms timescale hook)

**v2 source to reference**: `bitmamba_autonomic.py` (591 lines), `daemon.cpp` (80+ lines)

**Estimated effort**: 2-3 sessions → **Actual**: 1 session

**Implementation**: `crates/wm-autonomic/src/lib.rs` (~900 lines)
- `BitMambaDaemon`: subprocess management, JSON lines protocol, graceful shutdown on Drop
- `SalienceProcessor`: 4 signal types (Novelty, Anomaly, EmotionalShift, Background), EMA baseline, token history tracking
- `AutonomicLayer`: telemetry buffering, pulse inference, signal-to-drive/workspace routing
- `DriveEventSource::Autonomic` added to wm-drive
- MCP server integration: telemetry feed after dispatch, salience pulse, drive + workspace event routing
- 22 unit tests

---

### Phase L2: LlamaLeftHemisphere — ✅ COMPLETE

**Goal**: Replace heuristic `LeftHemisphere` with llama.cpp-backed reasoning. This is the single highest-impact change — it transforms the bicameral engine from heuristic-only to LLM-backed.

**New file**: `crates/wm-bicameral/src/local_llm.rs`

**Architecture**:
```rust
pub struct LlamaLeftHemisphere {
    config: LlamaConfig,
    agent: ureq::Agent,
}

pub struct LlamaConfig {
    endpoint: String,      // llama-server HTTP API URL
    model: String,         // model name/path
    temperature: f32,      // low (0.1-0.3) for deterministic
    max_tokens: u32,
    timeout: Duration,
}
```

**Integration**:
- `from_env()` → `LlamaLeftHemisphere` if `WM_LLAMA_ENDPOINT` is set
- Falls back to `LeftHemisphere::new()` (heuristic) if not set
- Same `Hemisphere` trait as `LeftHemisphere`
- Uses `ureq` (already a dependency) — llama-server exposes OpenAI-compatible API
- Low temperature (0.1-0.3) for deterministic output (left hemisphere trait)
- Structured prompt: "Analyze the evidence systematically. Provide conclusion, confidence, stance, key_points."

**Wiring in `BicameralEngine`**:
- Current: `left: LeftHemisphere` (concrete struct)
- After: `left: Box<dyn Hemisphere>` (trait object) — allows swapping heuristic for LLM
- `BicameralEngine::new()` checks env vars and constructs the appropriate left hemisphere

**Key decisions**:
- llama-server must be running separately (v4 doesn't manage the subprocess)
- Same ureq HTTP pattern as `LlmRightHemisphere` — no new dependencies
- Low temperature for deterministic output (left hemisphere trait)
- Falls back to heuristic when unavailable — no hard dependency
- Requires making `LeftHemisphere` implement the `Hemisphere` trait (currently it's a concrete struct)

**v2 source to reference**: `llama_cpp.py` (925 lines), `local_llm.py` (141 lines)

**Estimated effort**: 1-2 sessions → **Actual**: 1 session

**Implementation**: `crates/wm-bicameral/src/local_llm.rs` (~220 lines)
- `LlamaConfig`: endpoint, model, temperature (0.2 default), timeout, max_tokens
- `LlamaLeftHemisphere`: implements `Hemisphere` trait, calls llama-server OpenAI-compatible API
- `BicameralEngine` refactored: `left: Box<dyn Hemisphere>` (was concrete `LeftHemisphere`)
- `with_hemispheres` constructor for explicit left/right selection
- `bicameral.status` tool reports left hemisphere backend name
- 11 unit tests

---

### Phase L4: Inference Router — ✅ COMPLETE

**Goal**: Port v2's complexity-aware router to route hemisphere calls to the cheapest sufficient tier.

**New module**: `crates/wm-bicameral/src/router.rs` ✅ Created (~1420 lines)

**Architecture**:
```
Prompt → ComplexityClassifier → Route Decision
                                    ├─ Tier 0: Heuristic (evidence tally, <1ms)
                                    ├─ Tier 1: llama.cpp small (1.5B-7B, 50-500ms)
                                    ├─ Tier 2: llama.cpp large / BitNet (8B+, 1-10s)
                                    └─ Tier 3: Cloud API (frontier model, 2-30s)
```

**Routing signals** (from v2 `complexity.py`):
- Task type (classification vs reasoning vs coding)
- Token budget estimation
- Data sensitivity (PII, financial → no cloud)
- Latency budget (interactive vs background)
- Context window needs

**Confidence cascading**: If Tier N output confidence < threshold, escalate to Tier N+1.

**Key decisions**:
- Router is used by both hemispheres — left and right can route independently
- Sensitive data never routes to cloud
- Token budget tracking with EMA-based prediction
- Router is optional — if not configured, hemispheres use their default backend

**v2 source to reference**: `router.py` (1071 lines), `complexity.py` (361 lines)

**Estimated effort**: 2-3 sessions → **Actual**: 1 session

**Implementation**: `crates/wm-bicameral/src/router.rs` (~1420 lines)
- `InferenceTier` enum: 5 tiers (EdgeRules, LocalLlamaCpp, LocalSmall, LocalLarge, Cloud) with ordering, escalate()
- `ComplexityClassifier`: pattern-based task type detection (17 task patterns), token budget estimation, sensitivity detection (5 patterns), tool-call detection (3 patterns), multi-turn detection (3 patterns), latency budget awareness
- `ComplexityAssessment`: tier, task_type, confidence, estimated_output_tokens, is_sensitive, needs_tool_calls, is_multi_turn, signals map
- `TokenBudgetTracker`: EMA-based usage prediction, warning/critical thresholds, recommend_downgrade()
- `InferenceRouter`: confidence cascading (Tier N → Tier N+1 if confidence < threshold), handler registration via `TierHandler` trait, force_tier override, cloud availability check, sensitive data never routes to cloud
- `RouterConfig`: from_env() with WM_ROUTER_CONFIDENCE_THRESHOLD, WM_ROUTER_MAX_ESCALATIONS, WM_ROUTER_CLOUD_AVAILABLE, WM_ROUTER_TOKEN_BUDGET
- 45 unit tests

---

### Phase L5: Local Embedder — ✅ COMPLETE

**Goal**: Port v2's FastEmbed integration for local vector embeddings without Python.

**Integration**: Added to `wm-memory` as embedder module alongside LanceDB.

**New module**: `crates/wm-memory/src/embedder.rs` ✅ Created (~420 lines)

**Architecture**:
- FastEmbed (ONNX Runtime) for BGE-Small-EN-V1.5 embeddings
- >500 docs/sec on CPU, no GPU required
- Lazy loading, global model cache
- Fallback when LanceDB is not available

**Key decision**: Used HTTP-based embedder (llama-server /v1/embeddings) as primary, with StubEmbedder (SHA-256 hash-based) as fallback. The `ort` crate path remains available as a future enhancement — the `Embedder` trait supports adding it without breaking changes.

**v2 source to reference**: `local_embedder.py` (313 lines)

**Estimated effort**: 1-2 sessions → **Actual**: 1 session

**Implementation**: `crates/wm-memory/src/embedder.rs` (~420 lines)
- `Embedder` trait: embed_batch, embed, embed_query, dimension, is_available, backend_name
- `HttpEmbedder`: calls llama-server /v1/embeddings (OpenAI-compatible), env-configured via WM_EMBEDDER_ENDPOINT
- `StubEmbedder`: SHA-256 hash-based pseudo-embeddings for testing/fallback (deterministic, [-1,1] normalized)
- `EmbedderConfig`: from_env() with WM_EMBEDDER_ENDPOINT, WM_EMBEDDER_MODEL, WM_EMBEDDER_DIM, WM_EMBEDDER_TIMEOUT_MS
- `create_embedder()`: factory function — HttpEmbedder if configured, else StubEmbedder
- 13 unit tests

---

### Phase L3: BitNet Right Hemisphere — ✅ COMPLETE

**Goal**: Alternative right hemisphere using BitNet for local-only operation.

**New file**: `crates/wm-bicameral/src/bitnet.rs` ✅ Created

**Architecture**:
- Wraps BitNet via subprocess (llama-cli) or HTTP if available
- High temperature (0.7-1.0) for creative output
- Env-configured: `WM_BITNET_ENABLED`, `WM_BITNET_MODEL`, `WM_BITNET_LLAMA_CLI`
- Falls back to `RightHemisphereStub` or `LlmRightHemisphere`

**Priority**: Lower than L1 and L2 — BitNet is an alternative, not a core component.

**v2 source to reference**: `bitnet_bridge.py` (226 lines)

**Estimated effort**: 1 session → **Actual**: 1 session

**Implementation**: `crates/wm-bicameral/src/bitnet.rs` (~530 lines)
- `BitNetConfig`: HTTP endpoint, llama-cli path, model path, temperature (0.8 default), timeout, max_tokens
- `BitNetRightHemisphere`: implements `RightHemisphere` trait
  - HTTP mode: OpenAI-compatible API via `llama-server` (preferred, persistent server)
  - Subprocess mode: spawns `llama-cli` per inference call (no server needed)
- High temperature (0.8) for creative, divergent output
- JSON response parsing with graceful fallback to heuristic
- MCP server right hemisphere priority: BitNet → LLM → stub
- 17 unit tests

---

## 3. Implementation Order

```
L2 (LlamaLeftHemisphere) ✅ COMPLETE
 └─ Highest impact, lowest effort. Transforms bicameral from heuristic to LLM-backed.
 └─ Requires: trait refactoring of LeftHemisphere + new local_llm.rs
 └─ No new dependencies (ureq already used)

L1 (BitMamba Autonomic Layer) ✅ COMPLETE
 └─ Second highest impact. Enables real-time salience → citta feedback loop.
 └─ Requires: new wm-autonomic crate + subprocess management
 └─ No new Rust dependencies (std::process for subprocess, serde for JSON lines)

L3 (BitNet Right Hemisphere) ✅ COMPLETE
 └─ Local 1.58-bit model for creative right hemisphere output.
 └─ HTTP (llama-server) + subprocess (llama-cli) modes.
 └─ Right hemisphere priority: BitNet → LLM → stub

L4 (Inference Router) ✅ COMPLETE
 └─ Depends on L1 + L2 being complete ✅
 └─ Adds complexity-aware routing between heuristic/local-llm/cloud
 └─ Confidence cascading: if Tier N confidence < threshold, escalate to Tier N+1
 └─ Token budget tracking with EMA-based prediction
 └─ 45 unit tests

L5 (Local Embedder) ✅ COMPLETE
 └─ Independent of L1/L2/L4
 └─ HTTP-based embedder (llama-server /v1/embeddings) + stub fallback
 └─ Trait-based: future `ort` crate implementation can be added without breaking changes
 └─ 13 unit tests
```

## 4. Environment Variables

| Variable | Default | Description | Phase |
|----------|---------|-------------|-------|
| `WM_BITMAMBA_BIN` | — | Path to bitmamba-daemon binary | L1 ✅ |
| `WM_BITMAMBA_MODEL` | — | Path to bitmamba_255m.bin | L1 ✅ |
| `WM_BITMAMBA_TOKENIZER` | — | Path to tokenizer.bin | L1 ✅ |
| `WM_AUTONOMIC_ENABLED` | `0` | Enable BitMamba autonomic layer | L1 ✅ |
| `WM_LLAMA_ENDPOINT` | — | llama-server HTTP API URL (e.g. http://localhost:8080) | L2 ✅ |
| `WM_LLAMA_MODEL` | — | Model name for llama.cpp left hemisphere | L2 ✅ |
| `WM_LLAMA_TEMP` | `0.2` | Temperature for left hemisphere (low = deterministic) | L2 ✅ |
| `WM_LLM_API_KEY` | — | API key for cloud LLM (right hemisphere) | ✅ Existing |
| `WM_LLM_ENDPOINT` | OpenAI | Cloud LLM endpoint | ✅ Existing |
| `WM_LLM_MODEL` | gpt-4o-mini | Cloud LLM model | ✅ Existing |
| `WM_BITNET_ENABLED` | `0` | Enable BitNet right hemisphere | L3 ✅ |
| `WM_BITNET_ENDPOINT` | — | HTTP endpoint for llama-server serving BitNet | L3 ✅ |
| `WM_BITNET_MODEL` | `bitnet-b1.58` | Model name for HTTP mode | L3 ✅ |
| `WM_BITNET_LLAMA_CLI` | — | Path to llama-cli binary (subprocess mode) | L3 ✅ |
| `WM_BITNET_MODEL_PATH` | — | Path to BitNet GGUF model file (subprocess mode) | L3 ✅ |
| `WM_BITNET_TEMP` | `0.8` | Temperature for right hemisphere (high = creative) | L3 ✅ |
| `WM_BITNET_TIMEOUT_MS` | `60000` | Request/inference timeout | L3 ✅ |
| `WM_BITNET_MAX_TOKENS` | `512` | Max tokens for response | L3 ✅ |
| `WM_ROUTER_CONFIDENCE_THRESHOLD` | `0.5` | Confidence threshold for tier escalation | L4 ✅ |
| `WM_ROUTER_MAX_ESCALATIONS` | `2` | Max tier escalations before giving up | L4 ✅ |
| `WM_ROUTER_CLOUD_AVAILABLE` | `1` | Whether cloud tier is available | L4 ✅ |
| `WM_ROUTER_TOKEN_BUDGET` | `100000` | Total token budget for session | L4 ✅ |
| `WM_EMBEDDER_ENDPOINT` | — | llama-server URL for embeddings (e.g. http://localhost:8080) | L5 ✅ |
| `WM_EMBEDDER_MODEL` | `local` | Model name for embeddings API | L5 ✅ |
| `WM_EMBEDDER_DIM` | `384` | Expected embedding dimensionality | L5 ✅ |
| `WM_EMBEDDER_TIMEOUT_MS` | `30000` | Request timeout in milliseconds | L5 ✅ |

## 5. Design Principles

1. **No hard dependencies** — every local AI component falls back gracefully when unavailable
2. **Env-var gated** — all components are opt-in via environment variables
3. **Subprocess over library** — keep C++/Python AI code separate from Rust core
4. **No Python in the hot path** — v4's dispatch pipeline stays pure Rust
5. **Trait-based pluggability** — hemispheres, autonomic layer, and router are all traits
6. **Minimal new dependencies** — reuse ureq (already used for cloud LLM), use `ort` for ONNX

## 6. Verification Plan

After each phase:
- `cargo test` — all existing tests still pass
- `cargo clippy --all-targets` — 0 warnings
- `cargo fmt --all -- --check` — clean
- Manual test with local AI component running (e.g. start llama-server, set env var, run `wm serve`)
- Manual test without local AI component (graceful fallback verified)
- New unit tests for each component (config parsing, protocol handling, fallback behavior)

## 7. v2 Source File Reference

All files verified present on disk at `/home/lucas/Desktop/WHITEMAGIC/`:

| File | Lines | Phase |
|------|-------|-------|
| `core/whitemagic/inference/bitmamba_autonomic.py` | 591 | L1 |
| `WHITEMAGIC-aux/bitmamba.cpp/examples/daemon.cpp` | 80+ | L1 |
| `WHITEMAGIC-aux/models/bitmamba_255m.bin` | 247MB | L1 |
| `core/whitemagic/inference/llama_cpp.py` | 925 | L2 |
| `core/whitemagic/inference/local_llm.py` | 141 | L2 |
| `core/whitemagic/inference/router.py` | 1071 | L4 |
| `core/whitemagic/inference/complexity.py` | 361 | L4 |
| `core/whitemagic/inference/local_embedder.py` | 313 | L5 |
| `core/whitemagic/inference/bitnet_bridge.py` | 226 | L3 |
| `core/whitemagic/core/intelligence/bicameral.py` | 876 | L2 (reference) |
| `core/whitemagic/core/intelligence/corpus_callosum.py` | 426 | L2 (reference) |

**Binary**: `llama-server` at `/home/lucas/.local/bin/llama-server`
