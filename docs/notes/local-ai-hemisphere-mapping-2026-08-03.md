# WhiteMagic v4 — Local AI Hemisphere & Brain Region Mapping

**Date**: August 3, 2026
**Status**: Planning document for local AI integration
**Sources**: v2 inference stack (bitmamba_autonomic.py, llama_cpp.py, bitnet_bridge.py, router.py, complexity.py), MandalaOS specs (v0.1), CyberBrains notes (v1.2, v2.0), v4 cyberbrain roadmap, v2 corpus_callosum.py + bicameral.py

---

## 1. Overview

v4 has a bicameral architecture with pluggable hemispheres and an LLM right hemisphere already integrated via `ureq` (OpenAI-compatible API). The next step is wiring v2's local AI models — BitMamba, llama.cpp, BitNet — into the v4 brain region hierarchy. This document maps each local AI model to its corresponding CyberBrain region, cross-references with MandalaOS module boundaries, and defines the integration architecture.

---

## 2. v2 Local AI Inventory

### 2.1 BitMamba-2 255M (Autonomic Layer)

**Location**: `WHITEMAGIC-aux/bitmamba.cpp/` (C++ engine), `WHITEMAGIC/core/whitemagic/inference/bitmamba_autonomic.py` (Python wrapper)
**Model**: `WHITEMAGIC-aux/models/bitmamba_255m.bin` (247MB binary), `bitmamba_255m.msgpack` (975MB)
**Architecture**: 1.58-bit ternary Mamba-2 State Space Model (not a transformer)
**Specs**: ~10 tok/s on single CPU core, 252MB RAM, persistent hidden state across sessions
**Daemon**: `bitmamba-daemon` — JSON lines over stdin/stdout, eliminates ~200ms model reload
**Features**:
- LoRA adapters per layer for fine-tuning
- RYS (Recurrent Yet Skip) virtual layer repetition via `execution_path`
- Independent `MambaState` per slot (multi-slot execution)
- Batched prefill (`prefill_block`, `prefill_sequence`)
- Salience detection: novelty (token history), repetition penalty, diversity scoring
- Signal classification: novelty / anomaly / emotional_shift / background

**v2 Integration**: Feeds salience signals into citta consciousness cycle. Runs continuously as a subprocess. Tool output → autonomic layer → salience signal → citta advancement.

### 2.2 llama.cpp (Local LLM Backend)

**Location**: `WHITEMAGIC/core/whitemagic/inference/llama_cpp.py` (925 lines), `WHITEMAGIC/core/whitemagic/inference/local_llm.py` (141 lines)
**Architecture**: llama-server HTTP API (OpenAI-compatible endpoints)
**Features**:
- `DualModelManager`: Background model (always-on, small) + foreground model (on-demand, large)
- Speculative decoding: ngram-mod (no draft model), draft-simple, EAGLE-3
- KV cache quantization: q8_0 (50% reduction), q4_0 (75% reduction)
- Config: n_ctx 8192, flash_attn, configurable threads, GPU layers
- `BinaryManager`: auto-discovers llama-server binary
- Idle timeout: 5min default, auto-shutdown

**v2 Integration**: Primary local LLM for all inference tasks. Serves as backend for bicameral reasoning, code analysis, summarization, etc.

### 2.3 BitNet (1-bit LLM)

**Location**: `WHITEMAGIC/core/whitemagic/inference/bitnet_bridge.py` (226 lines)
**Model**: BitNet b1.58-3B, GGUF format
**Transport**: Redis pub/sub (Gan Ying channel) or direct subprocess
**Features**:
- Opt-in via `WHITEMAGIC_ENABLE_BITNET=1`
- Two modes: `redis` (via Gan Ying bus) or `direct` (subprocess)
- 3B parameter model, CPU-friendly

**v2 Integration**: Lightweight local inference alternative. Used when llama.cpp is too heavy.

### 2.4 Inference Router (Complexity-Aware)

**Location**: `WHITEMAGIC/core/whitemagic/inference/router.py` (1071 lines), `WHITEMAGIC/core/whitemagic/inference/complexity.py` (361 lines)
**Architecture**: 4-tier routing with confidence cascading

| Tier | Handler | Latency | Use Case |
|------|---------|---------|----------|
| 0 (Edge) | Cache + Rust PatternEngine | <1ms | Greetings, status, boolean |
| 1 (Local small) | llama.cpp 1.5B-7B quantized | 50-500ms | Classification, extraction, summarization |
| 2 (Local large) | BitNet/llama.cpp 8B+ | 1-10s | Reasoning, coding, analysis |
| 3 (Cloud) | Frontier model via API | 2-30s | Complex reasoning, long context |

**Routing signals**: Task type, token budget, data sensitivity, latency budget, tool-call requirement, context window needs.
**Confidence cascading**: If Tier N output confidence < threshold, escalate to Tier N+1.
**Token budget tracking**: EMA-based usage prediction, warning/critical thresholds.

### 2.5 Local Embedder

**Location**: `WHITEMAGIC/core/whitemagic/inference/local_embedder.py` (313 lines)
**Model**: FastEmbed (BAAI/bge-small-en-v1.5), ONNX Runtime
**Specs**: >500 docs/sec on CPU, no GPU required
**Features**: Global model cache, lazy loading, deferred model load

### 2.6 v2 Bicameral Reasoner

**Location**: `WHITEMAGIC/core/whitemagic/core/intelligence/bicameral.py` (876 lines), `WHITEMAGIC/core/whitemagic/core/intelligence/corpus_callosum.py` (426 lines)
**Architecture**: Dual-hemisphere with ThoughtClone armies
- Left: 50 clones, analytical/systematic/factual/cautious strategies
- Right: 50 clones, creative/intuitive/optimistic/holistic strategies
- Cross-critique: bidirectional, multi-round
- Synthesis: tension-based, semantic similarity adjustment
- Corpus Callosum Bus: 3-round debate with escalation

---

## 3. CyberBrain Region → Local AI Model Mapping

### 3.1 The Mapping Table

| Brain Region | CyberBrain Function | v4 Crate | Local AI Model | Role |
|--------------|---------------------|----------|----------------|------|
| **Brainstem** | Autonomic, reflexes, safety | wm-reflex | **BitMamba-2 255M** | Continuous autonomic layer: salience detection, anomaly monitoring, telemetry processing. Feeds signals into citta cycle. Always-on, 252MB RAM. |
| **Left Hemisphere** | Deterministic, sequential, causal | wm-bicameral | **llama.cpp (small model)** | Structured reasoning, formal logic, evidence analysis. Low temperature, precise output. Uses llama-server HTTP API. |
| **Right Hemisphere** | Holistic, pattern-matching, stochastic | wm-bicameral | **LLM API (current)** or **BitNet 3B** | Creative synthesis, novel connections, anomaly detection. High temperature. Current: OpenAI-compatible via ureq. Alternative: BitNet for local-only. |
| **Cerebellum** | Motor calibration, timing | (pending wm-embodiment) | — | Not yet implemented. Would use BitMamba for timing calibration. |
| **Thalamus** | Sensory routing, attention | wm-workspace + NLU | — | Routing is NLU-based (TF-IDF cosine). No AI model needed. |
| **Prefrontal Cortex** | Executive, meta-learning | wm-selfmodel + apotheosis | — | Forecasting is statistical (linear regression). Could use BitMamba for pattern detection. |
| **Hippocampus** | Episodic memory, spatial map | wm-memory | **Local Embedder** | Vector embeddings for memory search. FastEmbed (BGE-Small-EN-V1.5). |
| **Limbic System** | Affect, salience | wm-drive + wm-workspace | **BitMamba (shared)** | Drive state + salience scoring. BitMamba's emotional_shift classification feeds drive events. |
| **Basal Ganglia** | Action selection, value gating | wm-governance + wm-dispatch | — | Rule-based (dharma gates, karma ledger). No AI model needed. |

### 3.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        v4 CyberBrain                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Bicameral Engine                            │   │
│  │                                                               │   │
│  │  ┌─────────────────────┐    ┌──────────────────────────────┐ │   │
│  │  │  Left Hemisphere    │    │  Right Hemisphere            │ │   │
│  │  │  (deterministic)    │    │  (intuitive/creative)        │ │   │
│  │  │                     │    │                              │ │   │
│  │  │  Tier 1: Heuristic  │    │  Tier 1: LLM API (ureq)      │ │   │
│  │  │  Tier 2: llama.cpp  │    │  Tier 2: BitNet 3B (local)   │ │   │
│  │  │  Tier 3: LLM API    │    │  Tier 3: LLM API (fallback)  │ │   │
│  │  └──────────┬──────────┘    └───────────┬──────────────────┘ │   │
│  │             │                           │                     │   │
│  │             └───────────┬───────────────┘                     │   │
│  │                         │                                     │   │
│  │              ┌──────────▼──────────┐                          │   │
│  │              │  Corpus Callosum    │                          │   │
│  │              │  (bounded channel)  │                          │   │
│  │              └──────────┬──────────┘                          │   │
│  │                         │                                     │   │
│  │              ┌──────────▼──────────┐                          │   │
│  │              │  Consensus Gate     │                          │   │
│  │              │  (verdict)          │                          │   │
│  │              └─────────────────────┘                          │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                Autonomic Layer (parallel)                     │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  BitMamba-2 255M (persistent daemon)                    │  │   │
│  │  │  • Salience detection (novelty/anomaly/shift)           │  │   │
│  │  │  • Feeds signals into citta cycle                       │  │   │
│  │  │  • ~10 tok/s, 252MB RAM, always-on                     │  │   │
│  │  │  • Hidden state persists across sessions                │  │   │
│  │  │  • LoRA adapters for domain fine-tuning                 │  │   │
│  │  │  • RYS virtual layer repetition                         │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  Inference Router (complexity-aware)                    │  │   │
│  │  │  Tier 0: Edge rules (heuristic, <1ms)                   │  │   │
│  │  │  Tier 1: llama.cpp small (50-500ms)                     │  │   │
│  │  │  Tier 2: llama.cpp large / BitNet (1-10s)               │  │   │
│  │  │  Tier 3: Cloud API (2-30s)                              │  │   │
│  │  │  Confidence cascading: escalate on low confidence       │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                Memory Layer                                   │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  Local Embedder (FastEmbed / BGE-Small-EN-V1.5)         │  │   │
│  │  │  • >500 docs/sec on CPU, ONNX Runtime                   │  │   │
│  │  │  • Vector embeddings for memory.search                  │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. MandalaOS Cross-Reference

### 4.1 MandalaOS Module → v4 + Local AI

| MandalaOS Module | v4 Implementation | Local AI Component | MandalaOS Gap |
|------------------|-------------------|--------------------|----|
| `ethics/` (Dharma, Karma) | wm-governance + wm-bicameral consensus | LLM right hemisphere for ethical reasoning | Multi-agent consensus (MandalaOS Q1) |
| `action/` (PRAT dispatch) | wm-dispatch + wm-reflex | — | Cross-system auth |
| `deliberation/` (Gana council) | wm-bicameral + wm-workspace | llama.cpp left + LLM/BitNet right | Voting/veto protocol |
| `health/` (Harmony, Homeostasis) | wm-substrate + wm-selfmodel | BitMamba salience for anomaly detection | Cross-system homeostasis |
| `memory/` (Experience buffer) | wm-memory (LMDB + Tantivy) | Local Embedder (FastEmbed) | Federation protocol |
| `coordination/` (Resource ledger) | Future: multi-agent via wm-workspace | Inference router (token budget tracking) | Merge evaluator, convergence tracker |

### 4.2 MandalaOS Vision → v4 Reality

The MandalaOS spec describes a NixOS-based declarative OS with compartmentalized agent workloads. v4 implements the **cognitive substrate** that would run inside MandalaOS compartments. The key insight:

- **MandalaOS compartments** = v4 Mandala compartments (4 security tiers: Research/Sandbox/Production/Secure)
- **mandala-dharmad** = v4 Dharma gate in dispatch pipeline
- **mandala-karmad** = v4 Karma ledger (Merkle-chained)
- **mandala-harmonyd** = v4 Harmony Vector + SelfModel
- **mandala-cbd** = v4 circuit breaker in dispatch pipeline
- **SutraCode** (effect-typed language) = v4 EffectRow + Koka polyglot (partial)

What MandalaOS would add that v4 doesn't have:
1. NixOS declarative configuration (OS-level)
2. eBPF kernel-level enforcement (v4 is software-level)
3. TPM attestation (v4 has no hardware trust root)
4. Default-deny network egress (v4 has dharma rules but not network-level)
5. Reproducible builds (v4 has CI but not SLSA level 3+)

### 4.3 The Karmic Types Gap

MandalaOS strategy doc identified `EffectSignature` as a key gap. v4's `EffectRow` is close but not as comprehensive:

| MandalaOS Effect | v4 EffectRow | Status |
|------------------|-------------|--------|
| `reads` | ✅ Tracked | Complete |
| `writes` | ✅ Tracked | Complete |
| `network` | ❌ Not tracked | Gap |
| `network_targets` | ❌ Not tracked | Gap |
| `concurrency` | ❌ Not tracked | Gap |
| `dharma` | ✅ Dharma gate in pipeline | Complete |
| `pure` | ✅ `EffectRow::pure()` | Complete |
| `shelter_id` | ✅ Mandala compartment ID | Complete |

---

## 5. Integration Plan

### Phase L1: BitMamba Autonomic Layer

**Goal**: Wrap the BitMamba daemon as a persistent autonomic layer in v4.

**New crate**: `wm-autonomic` (or module in `wm-consciousness`)

**Architecture**:
```
┌─────────────────────────────────────────────┐
│  wm-autonomic (Rust)                        │
│                                             │
│  BitMambaDaemon                             │
│  ├── spawn bitmamba-daemon subprocess      │
│  ├── JSON lines protocol (stdin/stdout)    │
│  ├── send telemetry tokens                 │
│  ├── receive salience signals              │
│  ├── manage hidden state persistence       │
│  └── graceful shutdown on drop             │
│                                             │
│  SalienceProcessor                          │
│  ├── classify signals (novelty/anomaly/)   │
│  ├── feed into citta cycle                 │
│  ├── feed into drive events                │
│  └── feed into workspace events            │
│                                             │
│  Env vars:                                  │
│  WM_BITMAMBA_BIN (path to daemon)          │
│  WM_BITMAMBA_MODEL (path to .bin)          │
│  WM_AUTONOMIC_ENABLED (1/0)                │
└─────────────────────────────────────────────┘
```

**Integration points**:
1. `McpServer::with_defaults` — spawn daemon if `WM_BITMAMBA_BIN` is set
2. `handle_tools_call` — after dispatch, send tool output telemetry to autonomic layer
3. Citta cycle — poll autonomic layer for salience signals, advance citta on novel/anomaly
4. Drive events — autonomic salience → drive events (NovelInput, ResourcePressure)
5. Workspace events — autonomic salience → workspace publish

**Fallback**: If `WM_BITMAMBA_BIN` not set or daemon fails to start, autonomic layer is disabled. Citta cycle runs without salience input (current behavior).

**Key decisions**:
- Daemon is a subprocess, not a library — keeps C++ code separate
- Communication via JSON lines (same as v2 daemon protocol)
- Hidden state persists in daemon process, not in Rust
- Salience polling happens at Reactive tier (10ms timescale hook)
- No blocking — if daemon is slow, skip that cycle

### Phase L2: LlamaLeftHemisphere

**Goal**: Replace the heuristic `LeftHemisphere` with a llama.cpp-backed reasoning engine.

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
    max_tokens: usize,
    timeout_ms: u64,
}
```

**Integration**:
- `from_env()` → `LlamaLeftHemisphere` if `WM_LLAMA_ENDPOINT` is set
- Falls back to `LeftHemisphere::new()` (heuristic) if not set
- Same `RightHemisphere` trait pattern as `LlmRightHemisphere`
- Uses `ureq` (same as LLM right hemisphere) — llama-server exposes OpenAI-compatible API
- Low temperature (0.1-0.3) for deterministic output
- Structured prompt: "Analyze the evidence systematically. Provide conclusion, confidence, stance, key_points."

**Wiring in `with_defaults`**:
```rust
let left = if let Some(llama) = LlamaLeftHemisphere::from_env() {
    left_with_llama(llama)
} else {
    LeftHemisphere::new()
};
```

**Key decisions**:
- llama-server must be running separately (v4 doesn't manage the subprocess)
- Same ureq HTTP pattern as right hemisphere — no new dependencies
- Low temperature for deterministic output (left hemisphere trait)
- Falls back to heuristic when unavailable — no hard dependency

### Phase L3: BitNet Right Hemisphere

**Goal**: Alternative right hemisphere using BitNet for local-only operation.

**New file**: `crates/wm-bicameral/src/bitnet.rs`

**Architecture**:
- Wraps BitNet via subprocess (llama-cli) or HTTP if available
- High temperature (0.7-1.0) for creative output
- Env-configured: `WM_BITNET_ENABLED`, `WM_BITNET_MODEL`, `WM_BITNET_LLAMA_CLI`
- Falls back to `RightHemisphereStub` or `LlmRightHemisphere`

**Priority**: Lower than L1 and L2 — BitNet is an alternative, not a core component.

### Phase L4: Inference Router

**Goal**: Port v2's complexity-aware router to route hemisphere calls to the cheapest sufficient tier.

**New crate**: `wm-router` (or module in `wm-bicameral`)

**Architecture**:
```
Prompt → ComplexityClassifier → Route Decision
                                    ├─ Tier 0: Heuristic (evidence tally)
                                    ├─ Tier 1: llama.cpp small (1.5B-7B)
                                    ├─ Tier 2: llama.cpp large / BitNet (8B+)
                                    └─ Tier 3: Cloud API (frontier model)
```

**Routing signals** (from v2 complexity.py):
- Task type (classification vs reasoning vs coding)
- Token budget estimation
- Data sensitivity (PII, financial → no cloud)
- Latency budget (interactive vs background)
- Context window needs

**Confidence cascading**: If Tier N output confidence < threshold, escalate to Tier N+1.

**Key decisions**:
- Router is used by both hemispheres — left and right can route independently
- Sensitive data never routes to cloud (data sensitivity detection)
- Token budget tracking with EMA-based prediction
- Router is optional — if not configured, hemispheres use their default backend

### Phase L5: Local Embedder

**Goal**: Port v2's FastEmbed integration for local vector embeddings.

**Integration**: Add to `wm-memory` as an alternative to LanceDB.

**Architecture**:
- FastEmbed (ONNX Runtime) for BGE-Small-EN-V1.5 embeddings
- >500 docs/sec on CPU, no GPU
- Lazy loading, global model cache
- Fallback when LanceDB is not available

**Priority**: Medium — v4 already has LanceDB for vectors, but FastEmbed is lighter.

---

## 6. Implementation Priority

| Phase | Component | Effort | Priority | Dependencies |
|-------|-----------|--------|----------|--------------|
| L1 | BitMamba autonomic layer | 2-3 days | **High** | bitmamba-daemon binary |
| L2 | LlamaLeftHemisphere | 1-2 days | **High** | Running llama-server |
| L4 | Inference router | 2-3 days | **Medium** | L1 + L2 |
| L5 | Local embedder | 1 day | **Medium** | FastEmbed Python package |
| L3 | BitNet right hemisphere | 1 day | **Low** | BitNet model + binary |

---

## 7. v2 Bicameral Reasoner → v4 Migration Notes

### What v2 Has That v4 Doesn't (Bicameral)

| Feature | v2 | v4 | Migration Path |
|---------|----|----|----------------|
| ThoughtClone armies | 50 left + 50 right clones | Single left + single right | v4 is simpler — one call per hemisphere. Could add multi-sample in future. |
| Strategy lists | 7 left strategies, 7 right strategies | Single strategy per hemisphere | v4 uses temperature/config instead of strategy selection. |
| Multi-round debate | Up to 3 rounds with refinement | Up to 3 rounds (configurable) | v4 already has this via ConsensusGate. |
| Semantic similarity | SequenceMatcher for tension adjustment | Not implemented | Could add to v4 ConsensusGate. |
| Karma logging | Debate results logged to karma | Not implemented | Could add karma logging for bicameral.reason. |
| Corpus Callosum Bus | Persistent bus with debate history | Stateless per debate | v4 is simpler — could add history if needed. |
| LLM refinement | Uses LLM to refine hemispheres between rounds | Not implemented | Could add if LLM is available. |

### What v4 Has That v2 Doesn't (Bicameral)

| Feature | v4 | v2 |
|---------|----|----|
| Pluggable RightHemisphere trait | ✅ Trait + stub + closure + LLM impls | Hardcoded reasoner |
| Corpus Callosum bandwidth limits | ✅ Per-message + total | No limits |
| 6 verdict types | ✅ Agreed/AgreedAfterDebate/LeftPrevailed/RightPrevailed/LeftOnly/Inconclusive | 3 (balanced/left/right) |
| Deep integration | ✅ Bicameral consensus on all write-effect dispatches | Standalone tool only |
| LLM right hemisphere | ✅ OpenAI-compatible via ureq | Requires local LLM |
| Graceful degradation | ✅ Falls back to heuristic on API failure | Falls back to heuristic on timeout |

---

## 8. Environment Variables Summary

| Variable | Default | Description | Phase |
|----------|---------|-------------|-------|
| `WM_BITMAMBA_BIN` | — | Path to bitmamba-daemon binary | L1 |
| `WM_BITMAMBA_MODEL` | — | Path to bitmamba_255m.bin | L1 |
| `WM_AUTONOMIC_ENABLED` | `0` | Enable BitMamba autonomic layer | L1 |
| `WM_LLAMA_ENDPOINT` | — | llama-server HTTP API URL (e.g., http://localhost:8080) | L2 |
| `WM_LLAMA_MODEL` | — | Model name for llama.cpp left hemisphere | L2 |
| `WM_LLAMA_TEMP` | `0.2` | Temperature for left hemisphere (low = deterministic) | L2 |
| `WM_LLM_API_KEY` | — | API key for cloud LLM (right hemisphere) | ✅ Existing |
| `WM_LLM_ENDPOINT` | OpenAI | Cloud LLM endpoint | ✅ Existing |
| `WM_LLM_MODEL` | gpt-4o-mini | Cloud LLM model | ✅ Existing |
| `WM_BITNET_ENABLED` | `0` | Enable BitNet right hemisphere | L3 |
| `WM_BITNET_MODEL` | — | Path to BitNet GGUF model | L3 |
| `WM_BITNET_LLAMA_CLI` | — | Path to llama-cli binary | L3 |

---

## 9. Source Material References

- `WHITEMAGIC/core/whitemagic/inference/bitmamba_autonomic.py` — v2 BitMamba autonomic layer (591 lines)
- `WHITEMAGIC/WHITEMAGIC-aux/bitmamba.cpp/` — C++ BitMamba inference engine
- `WHITEMAGIC/WHITEMAGIC-aux/bitmamba.cpp/include/bitmamba/model.h` — Model class (98 lines)
- `WHITEMAGIC/WHITEMAGIC-aux/bitmamba.cpp/include/bitmamba/block.h` — Block + MambaState (67 lines)
- `WHITEMAGIC/WHITEMAGIC-aux/bitmamba.cpp/examples/daemon.cpp` — Daemon implementation (80+ lines)
- `WHITEMAGIC/WHITEMAGIC-aux/models/bitmamba_255m.bin` — 247MB model binary
- `WHITEMAGIC/core/whitemagic/inference/llama_cpp.py` — v2 llama.cpp backend (925 lines)
- `WHITEMAGIC/core/whitemagic/inference/local_llm.py` — v2 LocalLLM interface (141 lines)
- `WHITEMAGIC/core/whitemagic/inference/bitnet_bridge.py` — v2 BitNet bridge (226 lines)
- `WHITEMAGIC/core/whitemagic/inference/router.py` — v2 inference router (1071 lines)
- `WHITEMAGIC/core/whitemagic/inference/complexity.py` — v2 complexity classifier (361 lines)
- `WHITEMAGIC/core/whitemagic/inference/local_embedder.py` — v2 local embedder (313 lines)
- `WHITEMAGIC/core/whitemagic/core/intelligence/bicameral.py` — v2 bicameral reasoner (876 lines)
- `WHITEMAGIC/core/whitemagic/core/intelligence/corpus_callosum.py` — v2 corpus callosum bus (426 lines)
- `WHITEMAGIC/docs-2/spec/MANDALA_OS.md` — MandalaOS vision spec (191 lines)
- `WHITEMAGIC/docs-2/SFW2/MandalaOS_v0.1_SPEC.md` — MandalaOS v0.1 spec (80 lines)
- `WHITEMAGIC/docs-2/archive/strategy/MANDALA_OS_MAPPING.md` — MandalaOS → WhiteMagic mapping
- `WHITEMAGIC/docs-2/archive/strategy/MANDALA_STRATEGY.md` — MandalaOS implementation strategy
- `whitemagic-v4/docs/notes/cyberbrain-roadmap-2026-08-03.md` — v4 CyberBrain roadmap
