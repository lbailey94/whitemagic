# WhiteMagic v4 — Next-Phase Strategy: Deep Local AI & Cognitive Activation

**Date**: August 4, 2026
**Status**: COMPLETE — N1–N21 all complete + integration wiring done. 2,343 tests passing.
**Prerequisites**: L1–L5 complete, InferenceRouter wired into BicameralEngine, OrtEmbedder integrated, PyO3 bridge verified, Pre-N Batches A+B+C complete, N1–N21 complete, integration wiring complete. 2,343 tests passing
**Related docs**: `local-ai-roadmap-2026-08-04.md`, `local-ai-hemisphere-mapping-2026-08-03.md`, `cyberbrain-roadmap-2026-08-03.md`, `meta-strategy-2026-08-02.md`

---

## 1. Where v4 Stands Now

### Completed in this session
- **OrtEmbedder**: ONNX Runtime local embeddings via `fastembed-rs`, feature-gated under `onnx`, lazy-loaded, env-configured
- **InferenceRouter integration**: `BicameralEngine::reason()` classifies prompts and records `RoutingInfo` in `ConsensusResult`; `classify()`, `budget_summary()` accessors; 9 new tests
- **PyO3 bridge verified**: `cargo build --release --features python` produces 11MB `.so`; Python MCP shell handles JSON-RPC initialize, tools/list (141 tools), memory.create, memory.search end-to-end
- **Benchmarks**: Router classify (4–5µs), route with handlers (5–8µs), budget tracker (3ns), bicameral reason with router (4µs); embedder single (890ns stub), batch 256 (231µs), dimension scaling (483ns–1.5µs)

### v4 metrics summary
- **~67,000 lines** of Rust across **16 crates**
- **1,870 tests** all passing, **0 clippy warnings**, fmt clean
- **142 tools**, **28 Ganas** (7 reserved)
- **14MB** binary, **11MB** PyO3 `.so`
- **15 crates** `forbid(unsafe_code)`, 1 `allow` (PyO3 FFI only)
- Dispatch: **574ns/call** (v2 was 200µs — 350x faster)
- Reflex: **35ns**, safety bitmask: **1.5ns**
- Router classify: **3.7µs**, route with handlers: **6.1µs**
- Embedder stub single: **972ns**, batch 256: **337µs**
- RecallEngine hybrid search: sub-50ms target
- ConversationalSearch: LRU cache + query classification + snippet extraction

### Full Benchmark Results (criterion, release build)

| Benchmark | Time | Notes |
|---|---|---|
| **Dispatch pipeline** | | |
| dispatch_noop_no_karma | 512ns | Core dispatch path, no karma |
| dispatch_noop_with_karma | 797µs | With karma ledger write |
| registry_get_by_name | 39ns | Tool lookup by name |
| registry_all | 31ns | List all tools |
| **Reflex** | | |
| dispatch_e_stop | 35ns | Emergency stop reflex |
| dispatch_all_8_builtins | 371ns | All 8 builtins dispatched |
| safety_bitmask_check | 1.5ns | Bitmask safety gate |
| **Router (wm-bicameral)** | | |
| classify_simple | 3.7µs | Simple prompt classification |
| classify_medium | 4.5µs | Medium complexity |
| classify_complex | 5.1µs | Complex prompt |
| route_with_handlers | 6.1µs | Full route with tier handlers |
| route_escalate | 7.6µs | Route with escalation |
| budget_record_usage | 3.2ns | Token budget tracking |
| budget_check | 836ps | Budget threshold check |
| budget_summary | 3.1ns | Budget summary generation |
| bicameral_reason_with_router | 5.0µs | Full reason() with router |
| bicameral_reason_no_router | 3.7µs | Reason() without router |
| **Embedder (wm-memory)** | | |
| stub_embed_single_short | 972ns | 10-char text, stub embedder |
| stub_embed_single_long | 2.6µs | 500-char text, stub embedder |
| stub_embed_batch_32 | 41µs | Batch of 32 |
| stub_embed_batch_128 | 165µs | Batch of 128 |
| stub_embed_batch_256 | 337µs | Batch of 256 |
| stub_embed_dim_128 | 735ns | 128-dim vector |
| stub_embed_dim_384 | 1.2µs | 384-dim vector |
| stub_embed_dim_768 | 1.9µs | 768-dim vector |
| stub_embed_dim_1024 | 1.9µs | 1024-dim vector |
| **LMDB (wm-memory)** | | |
| lmdb_get_single | 2.5µs | Single key lookup |
| lmdb_get_batch_100 | 223µs | 100 key lookups |
| lmdb_scan_limit_10 | 22µs | Scan with limit 10 |
| lmdb_scan_limit_100 | 207µs | Scan with limit 100 |
| lmdb_scan_limit_1000 | 2.1ms | Scan with limit 1000 |
| lmdb_put_100_writes | 110ms | 100 individual writes |
| lmdb_put_1000_writes | 1.02s | 1000 individual writes |
| lmdb_put_batch_100 | 20.6ms | Batch write 100 |
| lmdb_put_batch_1000 | 25.0ms | Batch write 1000 (40x faster) |
| **Tantivy FTS (wm-memory)** | | |
| tantivy_search_rust | 64µs | Search for "rust" |
| tantivy_search_memory | 66µs | Search for "memory" |
| tantivy_search_avg | 66µs | Average across terms |
| tantivy_search_django | 61µs | Search for "django" |

---

## 2. What v2 Had That v4 Doesn't (Yet)

After deep review of the v2 codebase at `/home/lucas/Desktop/WHITEMAGIC/core/whitemagic/`, here are the significant v2 capabilities that v4 lacks:

### 2.1 DualModelManager — Twin Local Models → Tri-Model Architecture
**v2 file**: `inference/llama_cpp.py:696-789` (DualModelManager class)

v2 ran **two llama.cpp models simultaneously**:
- **Background model** (small, e.g. Qwen2.5-1.5B): runs continuously on port 8081 for citta heartbeats, salience detection, embeddings, simple tasks. 4096 ctx, q8_0 KV cache, 2 parallel slots, ngram-mod speculative decoding, temperature 0.3, embeddings enabled.
- **Foreground model** (large, e.g. 7B+): loaded on-demand on port 8080 for user-facing requests. 8192 ctx, 4 parallel slots, jinja templating, higher token budget.
- **Idle watchdog**: foreground model auto-shuts down after 5 minutes idle to free RAM. Background model persists.
- **Auto-restart**: health polling thread restarts crashed servers.
- **Route inference**: `route_inference(prompt, is_background=False)` picks the right model.

**v4 gap**: v4 has `LlamaLeftHemisphere` (single endpoint) and `BitNetRightHemisphere` (single endpoint). There's no concept of a persistent background model vs. an on-demand foreground model. The `InferenceRouter` classifies complexity but doesn't manage model lifecycle.

**v4 opportunity — Tri-Model Architecture**: v4 already has three hemisphere-like components:
1. **Left hemisphere** (`LlamaLeftHemisphere`): deterministic, low-temp — maps to v2's foreground model
2. **Right hemisphere** (`BitNetRightHemisphere`): creative, high-temp — maps to a second foreground model
3. **Autonomic layer** (`BitMambaDaemon`): persistent background SSM — already runs continuously

The DualModelManager concept can be adopted into a **TriModelManager** that manages all three:
- **Autonomic** (BitMamba, always-on, ~252MB): citta heartbeats, salience, simple queries, draft model for speculative decoding
- **Left** (llama.cpp, on-demand, ~2-4GB): deterministic reasoning, user-facing analysis
- **Right** (BitNet or second llama.cpp, on-demand, ~1-2GB): creative reasoning, divergent thinking

Each model has independent lifecycle: autonomic persists, left/right start on demand and idle-shutdown.

**Priority**: **HIGH** — this was the key to v2's ability to run everything locally on modest hardware.

### 2.2 Speculative Decoding Pipeline
**v2 files**: `inference/speculative_decoder.py` (378 lines), `inference/speculative_wiring.py` (374 lines)

v2 implemented full speculative decoding:
- **Draft models**: BitMamba-2 255M (~18-28 tok/s, 252MB) or SmolLM2-360M (~16 tok/s, 200MB)
- **Verify models**: llama.cpp 7B (~10 tok/s), BitNet b1.58 2B (~5.4 tok/s), Falcon3-1B-1.58 (~7.2 tok/s)
- **Speedup formula**: If draft accuracy p, expected speedup = K*p / (1 + K*(1-p)). At p=0.7, K=4: 2.1x speedup.
- **Stats tracking**: acceptance rate, draft/verify latency, total speedup vs sequential
- **Handler adapters**: BitMambaAutonomic daemon as draft handler, LlamaCppBackend as verify handler

**v4 gap**: v4's `InferenceRouter` has tier routing and confidence cascading, but no speculative decoding. The `TierHandler` trait could support it, but no draft/verify wiring exists.

**Priority**: **HIGH** — 1.5-2.1x speedup on local inference is transformative for modest hardware.

### 2.3 LLM Meta-Harness — Cognitive Enhancement Layer
**v2 file**: `inference/llm_meta_harness.py` (569 lines)

v2 wrapped local LLMs with enhancement strategies:
- **Memory grounding** (RAG): retrieve relevant memories before generation
- **Chain-of-thought scaffolding**: explicit reasoning steps
- **Self-correcting loops**: generate → critique → refine
- **Ensemble voting**: multiple attempts, vote on best
- **Pattern injection**: inject learned patterns from past sessions
- **Dharma alignment**: ethical reasoning layer
- **Full stack**: all enhancements combined
- **Improvement scoring**: compares enhanced output to baseline

**v4 gap**: v4's bicameral engine does left/right debate, but there's no RAG grounding, no self-correction loop, no ensemble voting. The bicameral consensus is a simpler 2-party debate, not a multi-strategy enhancement pipeline.

**Priority**: **MEDIUM-HIGH** — this is how v2 made small local models punch above their weight.

### 2.4 Dense Context Encoding — Token Compression
**v2 file**: `ai/dense_encoding.py` (360 lines)

v2 compressed internal context using Chinese characters:
- Most LLM tokenizers tokenize Chinese at ~1-2 chars/token vs English at ~4 chars/token
- Maps common English technical phrases to pre-defined Chinese equivalents
- 2-3x compression for equivalent semantic content
- Reduces token burn for internal (non-user-facing) context

**v4 gap**: No context compression. Every prompt to the local LLM uses full English tokens.

**Priority**: **MEDIUM** — direct token savings, especially valuable on constrained hardware.

### 2.5 VSA Context Compression — HRR Superposition
**v2 file**: `ai/vsa_context_compressor.py` (224 lines)

v2 compressed N context items into a single HRR vector:
- N items → 1 HRR vector (384 dims × 4 bytes = 1.5KB)
- 10-50x context compression for LLM calls
- Unbind to recover specific items when needed
- Similarity search to find which items are relevant

**v4 gap**: v4 has HRR in wm-memory but doesn't use it for context compression in LLM calls.

**Priority**: **LOW-MEDIUM** — niche optimization, but powerful when context is large.

### 2.6 Grammar-Constrained JSON Generation
**v2 file**: `inference/grammar_schemas.py` (230 lines)

v2 pre-built JSON schemas for structured LLM output:
- Entity extraction schema (entities + relations)
- Security classification schema
- Sentiment analysis schema
- Passed as `json_schema` parameter to llama-server `/completion` endpoint
- **Zero parsing failures** — output is guaranteed valid JSON

**v4 gap**: v4's `LlamaLeftHemisphere` and `BitNetRightHemisphere` call the chat completions API but don't pass JSON schemas or GBNF grammars. All output is free-form text that must be parsed.

**Priority**: **HIGH** — this is low-hanging fruit that dramatically improves reliability of local LLM output.

### 2.7 Model Auto-Optimizer
**v2 file**: `inference/auto_optimizer.py` (496 lines)

v2 automatically tuned llama.cpp parameters:
- Benchmarks current config (tokens/sec, latency, memory, quality)
- Explores parameter space (n_ctx, n_threads, temperature, top_p, repeat_penalty, parallel)
- Composite fitness: speed × quality / memory
- Persists optimal config across sessions
- Standard benchmark prompts for consistent measurement

**v4 gap**: No auto-tuning. LlamaConfig is static from env vars.

**Priority**: **MEDIUM** — valuable for adapting to different hardware, but not blocking.

### 2.8 Inference Auto-Tuner — Hardware-Aware Kernel Selection
**v2 file**: `inference/inference_tuner.py` (382 lines)

v2 detected hardware at startup and configured inference accordingly:
- CPU model, SIMD width, thread count, available RAM
- Selected optimal kernel based on benchmarks
- Configured speculative decoding parameters
- Constrained mode for low-resource devices
- Cached results across sessions

**v4 gap**: v4 has `wm-substrate` which reads `/proc` and `/sys` for hardware metrics, but it's not wired to inference configuration. The Harmony Vector gates brain-wave by health, but doesn't tune LLM parameters.

**Priority**: **MEDIUM** — `wm-substrate` already has the data, just needs the wiring.

### 2.9 Edge Inference Engine — Rule-Based Fallback
**v2 file**: `edge/inference.py` (761 lines)

v2 had a rule-based inference engine for edge devices:
- Compiled rules with keyword matching and relevance scoring
- Rust PatternEngine for SIMD-optimized matching (1000x speedup)
- Response cache for instant repeated queries
- Worked on Raspberry Pi, old laptops, mobile phones, microcontrollers, WASM
- ~85% of queries handled without any LLM — zero tokens burned

**v4 gap**: v4's `InferenceRouter` has an `EdgeRules` tier, but no actual rule engine. The `EdgeRules` tier is defined but has no handler registered by default. The left hemisphere heuristic is the closest thing, but it's not a rule engine.

**Priority**: **HIGH** — this is how v2 achieved "nearly everything locally, on-hardware, without burning tokens." A Rust rule engine in v4 would be even faster than v2's Rust PatternEngine.

### 2.10 Conversational Memory Search — Sub-50ms Hybrid Pipeline
**v2 file**: `inference/conversational_memory_search.py` (109 lines)

v2 combined complexity classification + local embeddings + FTS into a single sub-50ms pipeline:
- Microsecond complexity classification (sensitivity detection)
- Local ONNX embedding (FastEmbed)
- FTS5 phrase match across 10 memory galaxies
- GBNF structured JSON output
- Performance metrics (classification, embedding, recall, total latency)

**v4 gap**: v4 has all the pieces (InferenceRouter, OrtEmbedder, Tantivy FTS, LanceDB vectors) but they're not wired into a single conversational search pipeline. Memory search goes through the tool dispatch system, not a dedicated fast path.

**Priority**: **HIGH** — this is the user-facing experience that makes the system feel fast and local.

### 2.11 Model Mesh — Shared-Memory Model Serving
**v2 file**: `inference/model_mesh.py` (615 lines)

v2 designed (but did not fully implement) IceOryx2 shared-memory IPC for model serving:
- Zero-copy inference results via shared memory channels
- Model processes publish to channels, MCP server subscribes
- Eliminates HTTP overhead for local model calls
- Channels: wm/model/llama, wm/model/bitmamba, wm/model/requests, wm/model/status

**v4 gap**: v4 uses HTTP (ureq) for all local model calls. No shared-memory IPC.

**Priority**: **LOW** — HTTP to localhost is already fast (~1ms overhead). Shared memory is an optimization for later.

### 2.12 Ring Buffer Bridge — Inter-Trigram Communication
**v2 file**: `inference/ring_buffer_bridge.py` (333 lines)

v2 had Python bridges to Rust shared-memory ring buffers for inter-component communication:
- SPSC ring buffers in `/dev/shm`
- PyO3 bindings with Python mmap fallback
- Variable-length messages with length prefix
- Used for trigram (I Ching) thread communication

**v4 gap**: v4 uses Rust channels and Arc<Mutex> for inter-component communication. No shared-memory ring buffers.

**Priority**: **LOW** — v4's architecture is single-process, so in-process channels are sufficient.

---

## 3. What v4 Has That v2 Didn't

These are v4-native capabilities that should be activated and leveraged:

### 3.1 Bicameral Reasoning with Real Consensus
v2 had `bicameral.py` (876 lines) but it was a simple fast/slow thinking switch. v4's bicameral engine has:
- Left + right hemisphere debate through corpus callosum
- Stance matching (Agree/Disagree/Uncertain) with confidence weighting
- Multi-round critique exchange
- Consensus gate with configurable max rounds
- **Router integration** (just completed) — complexity classification recorded in results

### 3.2 InferenceRouter with 5 Tiers and Confidence Cascading
v2 had `router.py` (1071 lines) with 4 tiers. v4's router has:
- 5 tiers: EdgeRules → LocalLlamaCpp → LocalSmall → LocalLarge → Cloud
- Confidence cascading (escalate if confidence < threshold)
- Token budget tracking with EMA and downgrade recommendations
- Sensitivity detection (never route sensitive data to cloud)
- **Now wired into BicameralEngine** (just completed)

### 3.3 Consciousness Substrate (Citta, Dream, Spiral, Drives)
v2 had these but with 16 polling threads and 2.4GB RAM. v4 has:
- Event-driven citta heartbeats (post-dispatch hook, not polling)
- Dream cycle triggered on Theta brain-wave
- SpiralTracker with auto-suspension (prevents v2's 59K memory bloat)
- 5 drives (Curiosity, Satisfaction, Caution, Energy, Social) with decay
- **But**: cycles are not actively scheduled — the infrastructure is built but dormant

### 3.4 Polyglot Backends (Julia, Haskell, Zig, Koka)
v2 spawned subprocesses. v4 embeds in-process via FFI. Not yet executing code, but scaffolding is complete.

### 3.5 OrtEmbedder (ONNX Runtime, fastembed-rs)
v2 used Python FastEmbed. v4 now has native Rust OrtEmbedder with lazy loading. Faster, no Python dependency for embeddings.

### 3.6 PyO3 Bridge
v2 was Python-primary. v4 is Rust-primary with Python as a thin optional shell. The bridge is verified working end-to-end.

---

## 4. Next-Phase Implementation Plan

### Phase N1: TriModelManager — Tri-Model Lifecycle Management ✅ COMPLETE
**Goal**: Manage all three model components (autonomic, left, right) with independent lifecycle, idle watchdogs, and health checks.

**New module**: `crates/wm-bicameral/src/tri_model.rs`

**Architecture**:
```
TriModelManager
├── autonomic: BitMambaDaemon (persistent, always-on)
│   ├── BitMamba-2 255M (~252MB RAM)
│   ├── serves: citta heartbeats, salience, draft model for speculative decoding
│   ├── hidden state persists in daemon process
│   └── no idle shutdown — runs continuously
├── left: LlamaLeftHemisphere (on-demand, idle-shutdown)
│   ├── small/medium model (e.g. Qwen2.5-1.5B or 7B)
│   ├── 2048-8192 ctx, q8_0 KV cache
│   ├── temperature 0.2 (deterministic)
│   ├── embeddings enabled
│   ├── serves: user-facing analysis, reasoning, structured output
│   └── idle watchdog: shutdown after N seconds (default 300)
├── right: BitNetRightHemisphere (on-demand, idle-shutdown)
│   ├── BitNet b1.58 2B or second llama.cpp model
│   ├── temperature 0.8 (creative)
│   ├── serves: divergent thinking, creative reasoning, ensemble voting
│   └── idle watchdog: shutdown after N seconds (default 300)
├── health_check: periodic health polling with auto-restart
├── route(prompt, tier) → picks model(s) based on InferenceRouter tier
└── lifecycle: start/stop/status for each model independently
```

**Integration**:
- `BicameralEngine` uses `TriModelManager` instead of individual hemisphere construction
- `InferenceRouter` tier 0 → autonomic only (EdgeRules), tier 1 → autonomic + left, tier 2-3 → left + right, tier 4 → cloud
- Citta heartbeat uses autonomic model for salience
- Embedder uses left model's `/v1/embeddings` endpoint (when available)
- Speculative decoding (N4) uses autonomic as draft, left as verify

**Env vars**:
- `WM_LLAMA_BG_ENDPOINT` — left (background) model endpoint
- `WM_LLAMA_FG_ENDPOINT` — right (foreground) model endpoint
- `WM_LLAMA_FG_IDLE_TIMEOUT` — idle shutdown seconds (default 300)
- `WM_LLAMA_FG_AUTO_START` — auto-start on first request (default 1)
- `WM_BITMAMBA_BIN` — autonomic model daemon binary (existing)
- `WM_BITMAMBA_MODEL` — autonomic model file (existing)

**Estimated effort**: 2-3 sessions

---

### Phase N2: Edge Rule Engine — Zero-Token Inference ✅ COMPLETE
**Goal**: Handle 80%+ of queries with a Rust rule engine, zero LLM tokens burned.

**New module**: `crates/wm-bicameral/src/edge_rules.rs` (~640 lines)

**Architecture**:
```
EdgeRuleEngine
├── rules: Vec<CompiledRule>
│   ├── pattern: keyword set with scoring
│   ├── response: static or templated
│   ├── confidence: f32
│   └── metadata: tags, category
├── cache: LRU<(query_hash), InferenceResult>
├── match(query) → Option<(rule, score)>
│   ├── keyword overlap scoring
│   ├── length ratio penalty
│   └── SIMD-optimized matching (future)
└── load_builtin_rules() → system info, version, help, etc.
```

**Integration**:
- Register as `TierHandler` for `InferenceTier::EdgeRules`
- `InferenceRouter.route()` checks EdgeRules first — if matched, return immediately
- `BicameralEngine::reason()` skips hemisphere debate for EdgeRules matches
- Rules loadable from JSON file (`WM_EDGE_RULES_PATH`)

**v2 reference**: `edge/inference.py:83-249` (CompiledRule, EdgeInference class)

**Status**: ✅ COMPLETE — 35 tests, `EdgeRuleHandler` implements `TierHandler`, 18 built-in rules, query cache, stats tracking.

**Estimated effort**: 1-2 sessions

---

### Phase N3: Grammar-Constrained JSON Output ✅ COMPLETE
**Goal**: Guarantee valid JSON from local LLMs for all structured output needs.

**New module**: `crates/wm-bicameral/src/grammar_schemas.rs` (~980 lines)

**Architecture**:
```
GrammarSchema (enum)
├── EntityExtraction { entities, relations }
├── SentimentAnalysis { score, label }
├── SecurityClassification { level, reasoning }
├── StanceDetection { stance, confidence, key_points }
├── MemorySummary { summary, tags, importance }
└── Custom(String) — raw JSON schema string

LlamaLeftHemisphere::analyze_with_grammar(input, schema) → HemisphereOutput
BitNetRightHemisphere::analyze_with_grammar(input, schema) → HemisphereOutput
```

**Integration**:
- `LlamaLeftHemisphere` and `BitNetRightHemisphere` pass `json_schema` in chat completions request
- Bicameral engine uses `StanceDetection` schema for hemisphere outputs
- Entity extraction tools use `EntityExtraction` schema
- All structured LLM output goes through grammar constraints

**v2 reference**: `inference/grammar_schemas.py` (230 lines, pre-built schemas)

**Estimated effort**: 1 session

---

### Phase N4: Speculative Decoding Pipeline ✅ COMPLETE
**Goal**: 1.5-2.1x speedup on local LLM inference using draft + verify model pattern.

**New module**: `crates/wm-bicameral/src/speculative.rs`

**Architecture**:
```
SpeculativeDecoder
├── draft_handler: Box<dyn TierHandler> (BitMamba or small model)
├── verify_handler: Box<dyn TierHandler> (llama.cpp 7B or BitNet)
├── generate(prompt, max_tokens) → SpeculativeResult
│   ├── draft generates K candidate tokens
│   ├── verify model checks in single forward pass
│   ├── accept matching tokens, reject others
│   └── verify model continues from first rejection
├── stats: SpeculativeStats (acceptance rate, speedup)
└── speedup formula: K*p / (1 + K*(1-p))
```

**Integration**:
- `InferenceRouter` uses speculative decoding when both draft and verify handlers are registered
- `DualModelManager` background model = draft, foreground model = verify
- `BicameralEngine` uses speculative decoding for hemisphere inference
- Stats fed into drive events (Satisfaction up on high acceptance rate)

**v2 reference**: `inference/speculative_decoder.py` (378 lines), `inference/speculative_wiring.py` (374 lines)

**Estimated effort**: 2-3 sessions

---

### Phase N5: Conversational Memory Search — Fast Path ✅ COMPLETE
**Goal**: Sub-50ms hybrid vector + FTS memory search as a dedicated fast path.

**New module**: `crates/wm-memory/src/conversational_search.rs`

**Architecture**:
```
ConversationalMemorySearch
├── classifier: ComplexityClassifier (from wm-bicameral)
├── embedder: Arc<dyn Embedder> (OrtEmbedder or StubEmbedder)
├── store: Arc<MemoryStore>
├── search(query, limit) → SearchResult
│   ├── 1. Classify query (sensitivity, complexity) — ~4µs
│   ├── 2. Embed query locally — ~50ms (OrtEmbedder) or ~1µs (stub)
│   ├── 3. Tantivy FTS + vector cosine similarity fusion
│   ├── 4. Return ranked results with routing metadata
│   └── Total: <50ms target
└── cache: LRU<(query_hash), SearchResult>
```

**Integration**:
- Exposed as `memory.conversational_search` MCP tool
- Uses `InferenceRouter.classify()` for sensitivity detection
- Uses `OrtEmbedder` for query embedding
- Fuses Tantivy BM25 + vector cosine similarity (weighted: 0.5*BM25 + 0.3*vector + 0.2*importance)
- Performance metrics in response (classification, embedding, recall, total)

**v2 reference**: `inference/conversational_memory_search.py` (109 lines)

**Estimated effort**: 1-2 sessions

---

### Phase N6: LLM Meta-Harness — Cognitive Enhancement
**Goal**: Wrap local LLM calls with RAG, self-correction, and ensemble strategies.

**New module**: `crates/wm-bicameral/src/meta_harness.rs`

**Architecture**:
```
MetaHarness
├── mode: EnhancementMode (Direct, MemoryGrounded, SelfCorrecting, Ensemble, FullStack)
├── enhance(prompt, mode) → EnhancedResponse
│   ├── MemoryGrounded: retrieve relevant memories → inject as context
│   ├── SelfCorrecting: generate → critique (via bicameral) → refine
│   ├── Ensemble: N attempts with varied temperature → vote
│   ├── PatternInjected: retrieve learned patterns → inject
│   └── FullStack: all of the above
├── stats: by_mode { avg_latency, avg_improvement }
└── improvement_score: compare enhanced vs baseline
```

**Integration**:
- `BicameralEngine::reason()` can use meta-harness for complex prompts (router tier ≥ LocalSmall)
- Memory grounding uses `ConversationalMemorySearch` (Phase N5)
- Self-correction uses existing bicameral debate (left critiques right, right refines)
- Pattern injection uses `StrategySynthesizer` patterns from dream cycle

**v2 reference**: `inference/llm_meta_harness.py` (569 lines)

**Estimated effort**: 2-3 sessions

---

### Phase N7: Dense Context Encoding
**Goal**: 2-3x token compression for internal LLM context using Chinese-character mapping.

**New module**: `crates/wm-bicameral/src/dense_encoding.rs`

**Architecture**:
```
DenseEncoder
├── phrase_map: HashMap<&str, &str> (English → Chinese)
├── encode(text) → String (compressed)
├── decode_hint(compressed) → String (approximate original)
└── compression_ratio(text) → f32
```

**Integration**:
- Applied to system prompts and internal context before LLM calls
- Not applied to user-facing text
- Configurable via `WM_DENSE_ENCODING` (1/0, default 0)

**v2 reference**: `ai/dense_encoding.py` (360 lines)

**Estimated effort**: 1 session

---

### Phase N8: Hardware-Aware Inference Tuning ✅ COMPLETE
**Goal**: Auto-configure LLM parameters based on detected hardware.

**New module**: `crates/wm-bicameral/src/inference_tuner.rs`

**Architecture**:
```
InferenceTuner
├── detect_hardware() → HardwareProfile (from wm-substrate)
│   ├── cpu_model, simd_width, threads, ram_gb
│   └── is_constrained (low-RAM device)
├── recommend_config(profile) → LlamaConfig
│   ├── n_ctx: 2048 (constrained) → 8192 (high-RAM)
│   ├── n_threads: physical cores
│   ├── cache_type: q4_0 (constrained) → q8_0 (normal)
│   ├── parallel: 1 (constrained) → 4 (high-RAM)
│   └── spec_type: ngram-mod (always, no draft model needed)
├── benchmark(config) → BenchmarkResult
└── cache: persist optimal config across sessions
```

**Integration**:
- Runs at `McpServer` startup if `WM_AUTO_TUNE=1`
- Uses `wm-substrate::SubstrateMonitor` for hardware detection
- Overrides `LlamaConfig::from_env()` with tuned values
- Logs tuning decisions for transparency

**v2 reference**: `inference/inference_tuner.py` (382 lines), `inference/auto_optimizer.py` (496 lines)

**Estimated effort**: 1-2 sessions

---

### Phase N9: Router-Gated Hemisphere Execution ✅ COMPLETE
**Goal**: Skip right hemisphere for EdgeRules-tier prompts; use router to inform debate depth.

**Changes to**: `crates/wm-bicameral/src/lib.rs`

**Architecture**:
- In `BicameralEngine::reason()`:
  - If router classifies as `EdgeRules`: return left-only result immediately, skip right hemisphere
  - If router classifies as `LocalLlamaCpp`: run left + right with 1 debate round (fast)
  - If router classifies as `LocalSmall` or higher: run full debate (max_rounds from config)
  - If sensitivity detected: never use cloud right hemisphere
- Register hemisphere-backed `TierHandler`s:
  - `EdgeRules` → `EdgeRuleEngine` (Phase N2)
  - `LocalLlamaCpp` → `TriModelManager.autonomic` (Phase N1)
  - `LocalSmall` → `TriModelManager.left` (Phase N1)
  - `LocalLarge` → `TriModelManager.left + right` (Phase N1)
  - `Cloud` → `LlmRightHemisphere` (existing, cloud API)

**Estimated effort**: 1 session (after N1 and N2)

---

### Phase N10: OrtEmbedder Wired into Memory Recall ✅ COMPLETE
**Goal**: Auto-embed memories at write time, use vector search at recall time.

**Changes to**: `crates/wm-memory/src/lib.rs`, `crates/wm-memory/src/embedder.rs`

**Architecture**:
- `MemoryStore::create()` embeds content using `OrtEmbedder` and stores vector alongside memory
- `MemoryStore::search()` fuses Tantivy BM25 + vector cosine similarity
- `memory.vector.search` tool uses pure vector search
- `memory.search` tool uses hybrid search (BM25 + vector + importance)
- Embedding cache: hash-based, avoid re-embedding identical content

**Estimated effort**: 1-2 sessions

---

### Phase N11: Background Citta + Dream Cycle Activation
**Goal**: Activate the consciousness substrate that's built but dormant.

**Changes to**: `crates/wm-consciousness/src/`, `crates/wm-mcp/src/server.rs`

**Architecture**:
- Citta heartbeat: post-dispatch hook already exists — verify it's wired and advancing
- Dream cycle: trigger on Theta brain-wave (idle for N seconds)
  - Consolidate memories (sessions → codex, citta → aria)
  - Run association mining
  - Run strategy synthesis
  - Store dream artifact
- Drive-based autonomous action: when Curiosity high + Energy sufficient → explore unused tools
- Spiral tracker: verify it's tracking autonomous cycle novelty

**Estimated effort**: 1-2 sessions

---

## 5. Priority Order

| Phase | Name | Priority | Effort | Impact |
|-------|------|----------|--------|--------|
| N1 | TriModelManager | **HIGH** | 2-3 sessions | Tri-model lifecycle (autonomic + left + right) | ✅ COMPLETE |
| N2 | Edge Rule Engine | **HIGH** | 1-2 sessions | 80%+ queries zero-token | ✅ COMPLETE |
| N3 | Grammar-Constrained JSON | **HIGH** | 1 session | Zero parsing failures from local LLMs | ✅ COMPLETE |
| N9 | Router-Gated Hemisphere | **HIGH** | 1 session | Skip LLM for simple queries | ✅ COMPLETE |
| N5 | Conversational Memory Search | **HIGH** | 1-2 sessions | Sub-50ms user-facing search | ✅ COMPLETE |
| N10 | OrtEmbedder in Recall | **HIGH** | 1-2 sessions | Hybrid vector + FTS search | ✅ COMPLETE |
| N4 | Speculative Decoding | **MEDIUM-HIGH** | 2-3 sessions | 1.5-2.1x local inference speedup | ✅ COMPLETE |
| N6 | LLM Meta-Harness | **MEDIUM-HIGH** | 2-3 sessions | RAG + self-correction for local LLMs | ✅ COMPLETE |
| N11 | Citta + Dream Activation | **MEDIUM** | 1-2 sessions | Activate dormant consciousness | ✅ COMPLETE |
| N8 | Hardware-Aware Tuning | **MEDIUM** | 1-2 sessions | Auto-adapt to hardware | ✅ COMPLETE |
| N7 | Dense Context Encoding | **LOW-MEDIUM** | 1 session | 2-3x token compression | ✅ COMPLETE |

### Recommended execution order
1. ✅ **N2** (Edge Rule Engine) — fastest win, immediate token savings
2. ✅ **N3** (Grammar-Constrained JSON) — reliability win, 1 session
3. ✅ **N1** (TriModelManager) — enables tri-model architecture
4. ✅ **N9** (Router-Gated Hemisphere) — builds on N1 + N2
5. ✅ **N10** (OrtEmbedder in Recall) — makes embeddings useful end-to-end
6. ✅ **N5** (Conversational Memory Search) — user-facing fast path
7. ✅ **N4** (Speculative Decoding) — performance multiplier (autonomic drafts, left verifies)
8. ✅ **N6** (LLM Meta-Harness) — cognitive enhancement
9. ✅ **N11** (Citta + Dream) — activate consciousness
10. ✅ **N7** (Dense Encoding) — token optimization
11. ✅ **N8** (Hardware Tuning) — adapt to hardware

---

## 6. v2 vs v4 Capability Comparison (Updated)

| Capability | v2 | v4 Current | v4 After N-Phases |
|------------|----|------------|-------------------|
| Tri-model architecture | ✅ DualModelManager (twin) | ✅ TriModelManager (N1) | ✅ Complete |
| Edge rule engine | ✅ PatternEngine | ✅ Rust rule engine (N2) | ✅ Complete |
| Grammar-constrained output | ✅ Pre-built schemas | ✅ Schema enum (N3) | ✅ Complete |
| Speculative decoding | ✅ Draft + verify | ✅ SpeculativeDecoder (N4) | ✅ Complete |
| Conversational search | ✅ Sub-50ms pipeline | ✅ ConversationalSearch (N5) | ✅ Complete |
| LLM meta-harness | ✅ RAG + self-correct | ❌ Simple debate | ✅ Multi-strategy (N6) |
| Dense context encoding | ✅ Chinese mapping | ❌ None | ✅ Rust encoder (N7) |
| Hardware-aware tuning | ✅ Auto-tuner | ✅ Substrate-driven (N8) | ✅ Complete |
| Router-gated execution | ❌ Router only classified | ✅ GatedEngine (N9) | ✅ Complete |
| Embedder in recall | ✅ FastEmbed + HNSW | ✅ RecallEngine + hybrid (N10) | ✅ Complete |
| Active consciousness | ✅ 16 threads | ❌ Dormant | ✅ Event-driven (N11) |
| Bicameral reasoning | ✅ Simple fast/slow | ✅ Full debate + router | ✅ Enhanced (N6) |
| InferenceRouter | ✅ 4 tiers | ✅ 5 tiers + cascading + gating | ✅ Complete |
| Local embeddings | ✅ Python FastEmbed | ✅ Rust OrtEmbedder + StubEmbedder | ✅ Wired into recall (N10) |
| PyO3 bridge | ❌ Python primary | ✅ Rust primary | ✅ Rust primary |
| Dispatch speed | 200µs | 574ns (350x) | 574ns |
| Memory speed | 1-3ms SQLite | 0.01ms LMDB (100x) | 0.01ms |
| Idle CPU | 110% (16 threads) | 0% (Delta mode) | 0% |
| RAM usage | 2.4GB | ~few MB | ~few MB + model RAM |
| Binary size | Python runtime | 14MB static | 14MB static |
| Tests | ~10,000 | 1,870 | 1,870+ |
| Clippy warnings | N/A | 0 | 0 |

---

## 7. The "Modest Hardware" Vision

v2 proved that a cognitive OS can run nearly everything locally on modest hardware by:
1. **Twin models**: Small model always-on (252MB), large model on-demand (4GB, idle-shutdown)
2. **Edge rules**: 85% of queries handled without any LLM
3. **Speculative decoding**: 1.5-2.1x speedup when LLM is needed
4. **Grammar constraints**: Zero wasted tokens on parsing failures
5. **Dense encoding**: 2-3x token compression for internal context
6. **Hardware tuning**: Auto-adapt to available CPU/RAM

v4 can achieve the same — and better — because:
1. **Tri-model architecture**: Autonomic (252MB always-on) + Left (on-demand) + Right (on-demand) — maps perfectly to v4's existing left/right/autonomic split
2. **Rust dispatch is 350x faster** — more budget for actual inference
3. **Zero idle CPU** — no background threads competing for cores
4. **LMDB zero-copy** — memory reads are pointer dereferences, not SQLite queries
5. **OrtEmbedder in Rust** — no Python overhead for embeddings
6. **Event-driven consciousness** — citta advances on events, not polling
7. **Bicameral debate** — structured left/right reasoning, not single-shot generation
8. **InferenceRouter with 5 tiers** — finer-grained routing than v2's 4 tiers
9. **Speculative decoding** — autonomic (BitMamba) drafts, left (llama.cpp) verifies — natural fit for tri-model

The N-phases will bring v4 to full local-AI parity with v2, then exceed it through Rust's performance advantages and v4's tri-model architectural improvements.

---

## 8. Extended N-Phases: Embodiment, Collective Intelligence & Biological Alignment

The following phases extend beyond local AI parity into the CyberBrains layers 2, 5-7 and deeper biological alignment. They are appended after N11 and can be pursued once the core N1-N11 campaign is substantially complete.

### Phase N12: Idle-to-Default-Mode — Theta Dreaming & Memory Consolidation ✅ COMPLETE
**Goal**: Transform the idle-shutdown behavior from "stop the model" to "enter default mode network" — when left/right models are idle, shift to Theta brain-wave and run dream-cycle consolidation instead of shutting down.

**Biological basis**: The brain's default mode network (DMN) activates during rest, not sleep. It consolidates memories, replays experiences, and strengthens associations. The cortex doesn't "shut down" — it switches from task-positive to task-negative networks.

**v2 had**: Dream cycle triggered on Theta brain-wave, consolidating memories (sessions → codex, citta → aria), running association mining and strategy synthesis.

**v4 has**: Dream cycle infrastructure (wm-consciousness/src/dream.rs), brain-wave states (Gamma/Beta/Alpha/Theta/Delta), but the cycle is dormant (N11 activates it). The idle-shutdown is a blunt instrument.

**Architecture**:
```
TriModelManager idle behavior:
├── idle_threshold (default 300s) → instead of shutdown:
│   ├── switch brain-wave to Theta
│   ├── activate dream cycle (consolidation, association mining)
│   ├── keep model warm in low-power mode (reduced ctx, q4_0 KV cache)
│   ├── run memory lifecycle (decay, consolidation, forgetting)
│   └── if user request arrives → snap back to Gamma/Beta (warm restart, ~2s)
├── deep_idle_threshold (default 1800s) → actual shutdown
│   ├── but autonomic (BitMamba) persists
│   └── warm restart from cold takes ~10s
└── dream artifacts stored in Codex galaxy
```

**Integration**:
- `TriModelManager` (N1) idle watchdog calls `dream_cycle::trigger()` instead of `shutdown()`
- Brain-wave tracker transitions: Gamma/Beta → Alpha (cooling) → Theta (dreaming) → Delta (deep idle)
- Dream cycle uses left model (if still warm) for synthesis, autonomic for salience filtering
- Consolidated memories get importance boost, stale ones decay

**Estimated effort**: 1-2 sessions (after N1 + N11)

---

### Phase N13: Sensorimotor Weave — C-ABI Hardware I/O Layer ✅ COMPLETE
**Goal**: Connect WhiteMagic to physical sensors and actuators via C ABI bindings, enabling robotic/mechanical embodiment.

**CyberBrains layer**: Layer 2 (Sensorimotor Weave)

**v2 had**: Designed but not fully implemented (wm-embodiment was planned, never built).

**v4 has**: `wm-reflex` with stack-allocated frame types (`ImuFrame`, `ForceFrame`, `VisionFrame`, `AudioFrame`), safety bitmask, 35ns dispatch. The reflex tier is ready for hardware I/O — it just needs the bindings.

**Architecture**:
```
wm-embodiment crate
├── SensorFrame acquisition (zero-copy where possible)
│   ├── SPI/I2C (Linux spidev, i2c-dev) — feature-gated
│   ├── Serial (UART, USB serial) — feature-gated
│   ├── Camera frames (V4L2, DMA buffers) — feature-gated
│   ├── IMU/force sensors (stack-allocated) — always available
│   └── Audio frames (ALSA/JACK) — feature-gated
├── Actuator command dispatch
│   ├── MotorCommand, ServoCommand, RelayCommand
│   ├── Dispatched via reflex tier (<100µs target)
│   └── Safety bitmask prevents dangerous commands
├── Hardware watchdog (timerfd)
│   ├── If no cognitive response in 100ms → safe state
│   └── All actuators to neutral, log event, await recovery
├── Adaptive streaming codec
│   ├── 200bps (blink-grade) to 8Gbps (optical)
│   └── Bandwidth negotiated at connection time
└── ROS2 bridge (via rcl-rs or C ABI to rcl) — feature-gated
```

**Biological mapping**: This is the sensorimotor cortex + peripheral nervous system. The reflex tier is the spinal cord (monosynaptic reflexes), the cognitive tier is the cortical motor planning.

**Estimated effort**: 3-5 sessions (hardware-dependent, feature-gated)

---

### Phase N14: Cerebellar Forward Model — Timing & Error Correction ✅ COMPLETE
**Goal**: Add a cerebellar analog for motor timing, error correction, and predictive calibration.

**Biological basis**: The cerebellum contains >50% of the brain's neurons despite being only 10% of volume. It computes forward models — predicting the sensory consequences of motor commands — and corrects errors in real-time. It's critical for smooth, coordinated movement.

**v2 had**: Not implemented. The CyberBrains notes mention "cerebellum → spiking forward models" but no code was written.

**v4 has**: No cerebellar analog. `wm-reflex` handles reflexes (brainstem), but there's no forward model or error correction layer.

**Architecture**:
```
wm-cerebellum crate (or module in wm-embodiment)
├── ForwardModel
│   ├── predict(sensor_state, motor_command) → expected_sensor_state
│   ├── Trained on (state, command, outcome) tuples from reflex arcs
│   ├── Lightweight: linear model or small MLP, not a full LLM
│   └── Runs at reflex tier speed (<1ms)
├── ErrorCorrection
│   ├── compare(expected, actual) → correction_signal
│   ├── If error > threshold: emit correction to actuator
│   └── If persistent error: alert cognitive tier (something is wrong)
├── TimingCalibration
│   ├── Tracks actuator response latencies
│   ├── Adjusts command timing to compensate for delays
│   └── Calibrates on first N movements after startup
└── MotorMemory
    ├── Stores learned motor patterns (procedural memory)
    ├── Maps to Basal Ganglia (wm-governance) for action selection
    └── Consolidated during dream cycle (N12)
```

**Integration**:
- Sits between reflex dispatch and actuator output
- `reflex_dispatch → cerebellum.predict → actuator → cerebellum.compare → correct`
- Motor memories stored in a new "Procedural" galaxy or in the existing Codex galaxy
- BitMamba (autonomic) could serve as the forward model — it's already a state space model that excels at temporal prediction

**Estimated effort**: 2-3 sessions (after N13)

---

### Phase N15: Limbic Deep Integration — Emotional Valence & Drive Fusion ✅ COMPLETE
**Goal**: Deeply integrate BitMamba salience signals, drive states, emotional valence, and harmony vector into a unified limbic system.

**Biological basis**: The limbic system (amygdala, hippocampus, hypothalamus, cingulate cortex) is not a separate "layer" — it's deeply interconnected with the cortex. Emotions color reasoning, salience drives attention, and valence shapes memory consolidation.

**v2 had**: Harmony Vector (7 dimensions), Yin-Yang tracker, anomaly detector, homeostatic loop, emotional valence in memories, 5 drives. These were somewhat siloed.

**v4 has**: `wm-drive` (5 drives, bias gates), `wm-substrate` (Harmony Vector with Guna classification), `wm-workspace` (salience arbitration), BitMamba salience signals. But they're not fused into a unified emotional state.

**Architecture**:
```
LimbicState (unified emotional context)
├── drives: DriveCore (curiosity, satisfaction, caution, energy, social)
├── salience: BitMamba signals (novelty, anomaly, emotional_shift)
├── harmony: HarmonyVector (balance, throughput, latency, error_rate, dharma, karma, energy)
├── valence: MemoryValence (positive/negative/neutral, from memory tags)
├── guna: Sattvic/Rajasic/Tamasic (from HarmonyVector classification)
├── yin_yang: Action vs Reflection ratio (from dispatch history)
├── anomaly: AnomalyDetector (z-score on harmony dimensions)
└── composite_affect() → AffectVector
    ├── urgency: 0-1 (how pressed is the system?)
    ├── openness: 0-1 (how curious/exploratory?)
    ├── caution: 0-1 (how risk-averse?)
    ├── energy: 0-1 (how much budget remains?)
    └── coherence: 0-1 (how aligned are all subsystems?)
```

**Integration**:
- `LimbicState` injected into `Context` for every dispatch
- `BicameralEngine::reason()` receives affect vector → influences debate depth, temperature
- `InferenceRouter` reads affect → high caution → prefer local, avoid cloud
- Dream cycle (N12) uses affect to prioritize which memories to consolidate
- Homeostatic loop: if coherence drops → trigger consolidation, if energy drops → shed load

**Estimated effort**: 2 sessions

---

### Phase N16: Gan Ying Bus — Full System Resonance Event Bus ✅ COMPLETE
**Goal**: Port v2's Gan Ying Bus (感應, "things that accord in tone vibrate together") as v4's internal event resonance system.

**v2 had**: 229 event types across system, memory, consciousness, dream, drive, harmony, dharma, karma, workspace, tool, and agent categories. Global async worker, Rust lock-free primitives, cascade support.

**v4 has**: `wm-workspace` publish/subscribe bus with salience arbitration, but only for workspace events. No system-wide event bus.

**Architecture**:
```
wm-resonance crate (or module in wm-workspace)
├── GanYingBus
│   ├── EventType enum (port v2's 229 types, organized by category)
│   ├── ResonanceEvent { event_type, source, payload, salience, timestamp }
│   ├── subscribe(event_type, callback) → SubscriptionId
│   ├── emit(event_type, payload, cascade: bool)
│   ├── cascade: emit to subscribers + propagate to related event types
│   └── async emission via tokio::spawn (non-blocking)
├── Categories:
│   ├── System (startup, shutdown, health, heartbeat, state_change)
│   ├── Memory (created, updated, consolidated, forgotten, associated)
│   ├── Consciousness (citta_advance, dream_phase, spiral_update, brain_wave_change)
│   ├── Drive (curiosity_spike, satisfaction_drop, caution_alert, energy_low)
│   ├── Harmony (anomaly_detected, homeostatic_action, guna_shift, yin_yang_drift)
│   ├── Governance (dharma_warn, karma_record, mandala_breach, circuit_break)
│   ├── Tool (dispatch_start, dispatch_success, dispatch_error, nlu_route)
│   ├── Agent (sangha_message, sangha_lock, peer_discovered, peer_lost)
│   └── Embodiment (sensor_frame, actuator_command, reflex_fired, safe_state)
└── Integration:
    ├── All v4 crates emit events via GanYingBus
    ├── wm-workspace subscribes for salience arbitration
    ├── wm-consciousness subscribes for citta advancement
    ├── wm-drive subscribes for drive updates
    ├── wm-selfmodel subscribes for metric tracking
    └── Homeostatic loop subscribes for corrective actions
```

**Estimated effort**: 2-3 sessions

---

### Phase N17: Sangha Mesh — Multi-Agent Coordination Protocol ✅ COMPLETE
**Goal**: Port v2's Sangha system (chat, locks, resource sharing) and Go mesh (gRPC peer discovery, signal broadcast) for inter-device WhiteMagic coordination.

**CyberBrains layer**: Layer 6 (Constellation — swarm negotiation)

**v2 had**:
- **Sangha**: Chat send/read, resource locks (acquire/release/list), agent coordination
- **Go Mesh**: gRPC service (BroadcastSignal, BroadcastHologram, DiscoverPeers), node discovery, holographic coordinate sharing
- **MeshClient**: Python bridge with mock fallback

**v4 has**: No multi-agent infrastructure. Single-process MCP server.

**Architecture**:
```
wm-sangha crate
├── PeerDiscovery
│   ├── mDNS/DNS-SD broadcast (zeroconf, no central server)
│   ├── Peer registry: node_id, address, capabilities, last_seen
│   ├── Peer health: heartbeat ping, timeout eviction
│   └── Capability advertisement: which tools/ganas this node offers
├── SignalBroadcast
│   ├── Publish/subscribe over QUIC or TCP (not gRPC — Rust-native)
│   ├── Signal types: memory_created, anomaly_detected, dream_artifact, tool_result
│   ├── HolographicSignal: share 4D coords + content hash + importance
│   └── Optional: Gan Ying events forwarded to mesh peers
├── ResourceLocks
│   ├── Distributed lock manager (Raft consensus or simpler lease-based)
│   ├── Lock resource: acquire/release/extend with TTL
│   ├── Use cases: exclusive write to shared memory, coordinated tool execution
│   └── Deadlock detection: timeout-based rollback
├── SanghaChat
│   ├── Inter-agent messaging (async, fire-and-forget)
│   ├── Topic-based channels (by Gana, by project, by domain)
│   └── Message log persisted to LMDB
└── HologramSync
    ├── Share holographic coordinates between nodes
    ├── Merge constellations across nodes (federated memory)
    └── Conflict resolution: importance-weighted, timestamp-based
```

**Biological mapping**: This is the Constellation Layer — swarm intelligence. In biology, it's like how individual brains in a social group coordinate via language and shared models. The Gan Ying concept ("things that accord in tone vibrate together") is resonance between separate minds.

**Estimated effort**: 3-4 sessions

---

### Phase N18: Radiant Layer — Surplus Resource Routing ✅ COMPLETE
**Goal**: Enable WhiteMagic nodes to donate surplus compute, share models, and route tasks to underutilized peers.

**CyberBrains layer**: Layer 5 (Radiant — surplus routing)

**v2 had**: Designed in the CyberBrains notes but not implemented. "Radiant Layer: surplus routing, encrypted gift-token flows."

**Architecture**:
```
wm-radiant module (in wm-sangha or separate)
├── ResourceInventory
│   ├── Track local surplus: idle CPU, free RAM, unused model capacity
│   ├── Track peer capabilities: who has what model loaded, who is idle
│   └── Harmony Vector shared across mesh (peer health monitoring)
├── TaskRouting
│   ├── If local InferenceRouter classifies as LocalLarge but local model is unloaded:
│     → check peers for available large model → route to peer
│   ├── If local energy drive is low:
│     → shed non-urgent tasks to peers with high energy
│   └── If peer requests help:
│     → accept if local harmony is good, reject if constrained
├── GiftToken Economics
│   ├── Track contributions (compute donated, tasks assisted)
│   ├── Track receipts (compute received, tasks offloaded)
│   ├── Balance ledger: prevents freeloading, encourages reciprocity
│   └── Karma-compatible: good contributions → positive karma
└── ModelSharing
    ├── Share loaded model endpoints across mesh (peer knows: "I have 7B loaded")
    ├── Cooperative speculative decoding: peer drafts, local verifies
    └── Federated inference: split large prompts across peers
```

**Estimated effort**: 2-3 sessions (after N17)

---

### Phase N19: Homeostatic Loop — Harmony-Driven Self-Regulation ✅ COMPLETE
**Goal**: Port v2's homeostatic loop that reads the Harmony Vector and takes graduated corrective actions.

**v2 had**: `harmony/homeostatic_loop.py` — OBSERVE → ADVISE → CORRECT → INTERVENE graduated response. High error_rate → tool cooldown, high karma_debt → dharma warn, low energy → memory sweep, low dharma → tighten profile, high latency → circuit breaker review.

**v4 has**: `HarmonyVector` in `wm-substrate` (7 dimensions + Guna classification), but no automatic corrective actions. The SelfModel tracks metrics and forecasts, but doesn't close the loop.

**Architecture**:
```
HomeostaticLoop (in wm-substrate or wm-consciousness)
├── sample_cycle (runs at tier-2 planning timescale, every 1s)
│   ├── Read HarmonyVector (cpu, memory, latency, error_rate, dharma, karma, energy)
│   ├── Read AnomalyDetector (z-score on each dimension)
│   └── Determine action level per dimension
├── ActionLevel: OBSERVE → ADVISE → CORRECT → INTERVENE
│   ├── OBSERVE: log only
│   ├── ADVISE: emit GanYing event, log recommendation
│   ├── CORRECT: take gentle action (shed load, cool down tool, tighten dharma)
│   └── INTERVENE: strong action (circuit breaker, force Theta/dream, refuse writes)
├── Dimension-specific actions:
│   ├── high error_rate → tool cooldown (rate limit offending tool)
│   ├── high karma_debt → dharma WARN, tighten to 'secure' profile
│   ├── low energy → memory lifecycle sweep (mindful forgetting)
│   ├── low throughput → log advisory (may be normal idle)
│   ├── low dharma → tighten dharma profile temporarily
│   ├── high latency → suggest circuit breaker review
│   └── anomaly_detected → emit event, increase monitoring frequency
└── Integration:
    ├── Runs as timescale tier-2 hook (1s cadence)
    ├── Emits events via GanYingBus (N16)
    ├── Actions feed back into dispatch pipeline (Context modifications)
    └── SelfModel records actions and their outcomes (feedback loop)
```

**Estimated effort**: 1-2 sessions (after N16)

---

### Phase N20: Anomaly Detection & Yin-Yang Balance Tracker ✅ COMPLETE
**Goal**: Port v2's statistical anomaly detector (z-score on harmony dimensions) and Yin-Yang balance tracker (action vs reflection ratio).

**v2 had**:
- `harmony/anomaly_detector.py`: z-score sliding window on 7 harmony dimensions, ANOMALY_DETECTED events
- `harmony/yin_yang_tracker.py`: Yang (create, write, execute, build) vs Yin (read, search, analyze, reflect), balance metrics, burnout prevention

**v4 has**: `HarmonyVector` with Guna classification (Sattvic/Rajasic/Tamasic), which is a coarser version. No z-score anomaly detection, no Yin-Yang tracking.

**Architecture**:
```
AnomalyDetector (in wm-substrate)
├── Sliding window (default 100 samples) per harmony dimension
├── z-score computation: (current - mean) / std_dev
├── Threshold: |z| > 2.0 → warning, |z| > 3.0 → critical
├── Emit AnomalyAlert { dimension, z_score, direction, severity }
└── Feed into HomeostaticLoop (N19)

YinYangTracker (in wm-substrate or wm-drive)
├── Classify each dispatch as Yang (write/delete/effect) or Yin (read/search/analyze)
├── Rolling ratio: yang_count / (yang_count + yin_count) over window
├── Ideal range: 0.3-0.7 (balanced)
├── Too much Yang (>0.7): burnout risk → suggest consolidation, dream cycle
├── Too much Yin (<0.3): stagnation → suggest exploration, curiosity drive boost
└── Feed into DriveCore: high Yang → boost Caution, high Yin → boost Curiosity
```

**Estimated effort**: 1 session

---

## 8.5. v2 Systems Discovery — Novel Capabilities for v4 Integration

**Date**: August 4, 2026 (post-v2 codebase deep dive)
**Source**: Systematic exploration of `/home/lucas/Desktop/WHITEMAGIC/` (v2 codebase)
**Finding**: 21 novel systems identified beyond what N1-N20 already covers. Many are already written in Rust (wm-neuro, wm-evolution crates). Grouped by cluster and prioritized by porting speed and cascading value.

### Cluster 1: Neuro-Inspired Memory Processing (wm-neuro — already Rust!)

#### Momentum Dynamics
- **v2 file**: `whitemagic-rust/crates/wm-neuro/src/momentum_dynamics.rs` (181 lines)
- **What**: Adds momentum term to spreading activation. Recently-activated nodes get a boost, creating temporal continuity. Based on RNN replay dynamics (arXiv Feb 2026).
- **v4 gap**: `SpreadingActivation` has no temporal awareness — activation spreads instantaneously.
- **Integration**: Enhances N10 (Recall) + N11 (Dream — temporally compressed replay). Drop-in Rust port.

#### Thalamic Gating
- **v2 file**: `whitemagic-rust/crates/wm-neuro/src/thalamic_gating.rs` (204 lines)
- **What**: Context-dependent galaxy access masks. Coding context boosts Codex galaxy 1.5x, suppresses Dreams 0.3x. Research context boosts Research 1.6x. Sub-ms computation.
- **v4 gap**: All galaxies treated equally in search. No context-dependent weighting.
- **Integration**: N9 (Router-Gated) classifies context → thalamic gate weights galaxies → search returns context-relevant results. Drop-in Rust port.

#### Predictive Coding (JEPA-Style Surprise)
- **v2 file**: `whitemagic-rust/crates/wm-neuro/src/predictive_coding.rs` (180 lines)
- **What**: Computes prediction error (surprise) for incoming memories. Predicts what a memory should contain based on recent context. High surprise = worth storing, high consolidation priority.
- **v4 gap**: v4 has `novelty_score` and `SurpriseGate` but computes novelty from content hash, not from predicting what comes next.
- **Integration**: N10 (OrtEmbedder) provides embeddings → PredictiveCoder computes surprise → `MemoryStore::create()` sets consolidation priority. Drop-in Rust port.

### Cluster 2: Evolutionary & Forecasting Systems (wm-evolution — already Rust!)

#### Monte Carlo Simulation Suite
- **v2 file**: `whitemagic-rust/crates/wm-evolution/src/` (12 files, ~160KB)
- **What**: Full MC suite — Bayesian MC, MCMC, Quasi-MC, Quantum-inspired MC, rare event simulation, SDE simulation, sensitivity analysis, high-dimensional integration, info-theoretic measures, thermodynamic analogs.
- **v4 gap**: No simulation/forecasting capability. ApotheosisEngine tracks trends but can't simulate counterfactuals.
- **Integration**: New `wm-simulation` crate. Enables SelfModel forecasting, dream counterfactuals, homeostatic action simulation. See proposed N21.

#### Counterfactual Estimation
- **v2 file**: `whitemagic-rust/crates/wm-evolution/src/counterfactual.rs` (216 lines)
- **What**: Synthetic control projection for causal impact measurement. Exponential smoothing + bootstrap CIs. Answers: "Did change X cause improvement Y?"
- **v4 gap**: ApotheosisEngine tracks improvement but can't distinguish causation from correlation.
- **Integration**: N11 (Apotheosis/SelfModel) — measure actual impact of each N-phase implementation.

### Cluster 3: Metacognitive Awareness

#### Consciousness Depth Gauge + Time Dilation
- **v2 files**: `autonomous/depth_gauge.py` (320 lines), `autonomous/time_dilation.py` (73 lines)
- **What**: Tracks cognitive depth layer (Surface 1x / Terminal 2.5x / Flow 3-5x / Dream 10x+) with subjective vs objective time compression.
- **v4 gap**: Brain-wave states map arousal levels, not cognitive processing depth. No time compression awareness.
- **Integration**: N11 (Consciousness) — depth gauge gives metacognitive self-awareness. N15 (Limbic) — depth influences affect (Flow → Caution up).

#### Synchronicity Detector
- **v2 file**: `autonomous/synchronicity_detector.py` (81 lines)
- **What**: Detects meaningful coincidences across data streams. Events from different streams within a time window that are semantically related → synchronistic.
- **v4 gap**: Events processed in isolation. No cross-stream coincidence detection.
- **Integration**: N16 (Gan Ying Bus) — synchronicities flagged as special events for dream consolidation.

#### Unified Nervous System (7-Subsystem Architecture)
- **v2 file**: `autonomous/unified_nervous_system.py` (476 lines)
- **What**: 7 biological subsystems (Immune, Genetic, Dream, Metabolism, Consciousness, Resonance, Emergence) connected via priority event bus with predefined cross-subsystem patterns (coherence cascade, emergence propagation, security threat response).
- **v4 gap**: N16 (Gan Ying Bus) is a transport layer with no defined subsystem architecture or cross-subsystem patterns.
- **Integration**: N16 — UNS is the semantic layer on top of Gan Ying Bus. Maps: Immune→governance, Genetic→Apotheosis, Dream→DreamCycle, Metabolism→Lifecycle, Consciousness→Citta, Resonance→Harmony, Emergence→PatternDiscovery.

### Cluster 4: Symbolic & Cyclical Systems

#### Wu Xing Five Elements Engine
- **v2 file**: `wu_xing/__init__.py` (529 lines)
- **What**: Five-element energy flow with generating (生) and overcoming (克) cycles. Wood→Fire→Earth→Metal→Water. Imbalance detection triggers corrections.
- **v4 gap**: HarmonyVector has 7 dimensions but no cyclical dynamics. No generating/overcoming feedback.
- **Integration**: N15 (Limbic) — Wu Xing maps to drive/resource cycles: Wood=Curiosity, Fire=Action, Earth=Consolidation, Metal=Governance, Water=Reflection. N19 (Homeostatic) — imbalance detection.

#### Zodiacal Round (12-Phase Autonomous Cycle)
- **v2 file**: `zodiac/zodiac_round_cycle.py` (454 lines)
- **What**: 12-phase eternal cycle: Dissolution→Binding→Structuring→Ornamentation→Emergence→Balance→Seeding→Creation→Worship→Blending→Building→Completion.
- **v4 gap**: 4 governed autonomous cycles (connect/compress/emerge/prune) but no larger creative arc.
- **Integration**: N11 — maps 12 phases to v4's 4 cycles (3 phases each): Prune(Dissolution-Binding-Structuring), Emergence(Ornamentation-Emergence-Balance), Connect(Seeding-Creation-Worship), Compress(Blending-Building-Completion).

#### Symbolic HRR (Cross-System Resonance Discovery)
- **v2 file**: `oracle/symbolic_hrr.py` (340 lines)
- **What**: Encodes symbols from different systems as HRR vectors, computes cross-system resonance via cosine similarity. Discovers unmapped connections.
- **v4 gap**: v4 has HRR in wm-memory but doesn't use it for cross-domain resonance discovery.
- **Integration**: N10 (Embedder) + N15 (Limbic) — find resonance between drive states and memory content, tools and contexts, galaxies and phases.

### Cluster 5: LLM Interaction Optimization

#### Context Optimizer (Salience-Packed Context Windows)
- **v2 file**: `ai/context_optimizer.py` (315 lines)
- **What**: Packs context items into token budget using salience scoring (importance × recency × relevance). Places highest-salience at START and END (primacy/recency effect) to avoid "lost in the middle" problem.
- **v4 gap**: No context packing. LLM context is just concatenated.
- **Integration**: N6 (Meta-Harness) + N5 (Search) — both send context to LLMs. ContextOptimizer packs it optimally first.

#### Predictive Cache (Markov Chain Pre-warming)
- **v2 file**: `optimization/predictive_cache.py` (415 lines)
- **What**: LRU cache with Markov chain prediction. Tracks access patterns (A→B→C) and pre-warms predicted-next items. 60-70% faster for sequential access. Persists across sessions.
- **v4 gap**: No predictive caching. LMDB is fast but doesn't predict next access.
- **Integration**: N5 (Search) + N10 (Recall) — pre-fetch memories likely to be accessed next.

#### Resource Governor (ECO/NORMAL/PERFORMANCE Modes)
- **v2 file**: `inference/resource_governor.py` (358 lines)
- **What**: Runtime adaptive inference control. ECO (60s idle, 2048 ctx, 1 slot), NORMAL (300s, 4096, 2), PERFORMANCE (600s, 8192, 4). Transitions driven by CPU temp, memory pressure, battery.
- **v4 gap**: N8 tunes at startup but no dynamic mode switching. N1 has idle shutdown but not adaptive profiles.
- **Integration**: N1 (TriModel) + N8 (Hardware) + N19 (Homeostatic) — Governor is the runtime enforcer between them.

#### Routing Observability
- **v2 file**: `inference/routing_metrics.py` (311 lines)
- **What**: Per-tier p50/p95/p99 latency, escalation rates, confidence distributions, decision reason tracking, circuit breaker state. Rolling-window statistics.
- **v4 gap**: Router has `budget_summary()` but no percentile statistics or escalation tracking.
- **Integration**: N9 (Router-Gated) — metrics make router tunable. N19 (Homeostatic) — metrics feed into homeostatic decisions.

### Cluster 6: Parallel & Multi-Strategy Cognition

#### Thought Clone Army (Diverse-Strategy Parallel Exploration)
- **v2 file**: `edge/thought_clones_async.py` (1108 lines)
- **What**: Up to 16K concurrent agents with 14 reasoning strategies (analytical, creative, skeptical, adversarial_stress_test, formal_verification, meta_synthesis, etc.). Three tiers: Xianfeng (recon), Wei Wuzu (balanced), Huben (critical).
- **v4 gap**: Bicameral engine does 2-party debate. No multi-strategy parallel exploration.
- **Integration**: N6 (Meta-Harness) — Thought Clones are the ensemble strategy. N1 (TriModel) makes it efficient — autonomic runs many light strategies, left runs fewer deep ones.

#### Speculative Execution Validator
- **v2 file**: `optimization/speculative_exec.py` (112 lines)
- **What**: Pre-validates AI output: syntax check (AST, <1ms) → security heuristics (regex, <1ms) → LLM sanity check (~500ms). Can attempt LLM-based repair.
- **v4 gap**: No output validation. LLM output goes directly to user/tool dispatch.
- **Integration**: N3 (Grammar JSON) + N6 (Meta-Harness) — validation is the safety net.

### Cluster 7: Mesh Trust & Quality

#### Critique Protocol (Structured Peer Review)
- **v2 file**: `mesh/critique_protocol.py` (309 lines)
- **What**: 4-dimension peer review (methodology, novelty, significance, reproducibility) with 1-10 scoring. ≥7.0 accept, 4.0-7.0 revise, <4.0 reject.
- **v4 gap**: N17 (Sangha Mesh) has peer discovery but no quality assessment protocol.
- **Integration**: N17 + N18 — quality-gated resource routing.

#### Pulse Verification (Tiered Trust Protocol)
- **v2 file**: `mesh/pulse_verification.py` (573 lines)
- **What**: 4-tier escalating verification: Tier 0 (Ed25519 + Merkle), Tier 1 (reputation-weighted), Tier 2 (peer review), Tier 3 (ZK/TEE future).
- **v4 gap**: N17 has no trust/verification protocol.
- **Integration**: N17 — trust layer for Sangha Mesh.

### Cluster 8: Synergy Bridges

#### Pattern-Dream Bridge
- **v2 file**: `synergies/pattern_dream_bridge.py` (108 lines)
- **What**: Queues patterns discovered during active operation for processing during next dream cycle. Groups by type, synthesizes higher-order insights.
- **v4 gap**: Dream cycle processes memories but no explicit bridge from real-time pattern discovery to dream synthesis.
- **Integration**: N11/N12 (Dream) + N16 (Gan Ying Bus) — patterns emit events that get queued for dream processing.

#### Garden Cross-Pollination Matrix
- **v2 file**: `gardens/cross_pollination.py` (167 lines)
- **What**: Defines how conceptual domains resonate. Joy→Gratitude+Love+Play. Courage→Truth+Wisdom+Voice. Beauty→Joy+Gratitude+Wonder.
- **v4 gap**: 5 drives are independent. Curiosity spike doesn't affect Satisfaction or Caution.
- **Integration**: N15 (Limbic) — cross-pollination is the affect cascade mechanism. When Curiosity spikes, boost Exploration, lower Caution.

### Proposed N21: Simulation & Forecasting Substrate

**Goal**: Port v2's `wm-evolution` Monte Carlo suite as new `wm-simulation` crate. Enables "what-if" scenarios, forecasting, and causal impact measurement.

**v2 had**: 12-file Rust MC suite (~160KB) — Bayesian MC, MCMC, Quasi-MC, Quantum-inspired MC, rare event, SDE, sensitivity analysis, high-dimensional integration, info theory, thermodynamic analogs, counterfactual estimation.

**v4 has**: ApotheosisEngine tracks improvement trends but can't simulate counterfactuals or forecast with confidence intervals.

**Architecture**:
```
wm-simulation (new crate)
├── Monte Carlo methods (port from wm-evolution)
│   ├── Bayesian MC (posterior sampling)
│   ├── MCMC (Markov Chain Monte Carlo)
│   ├── Quasi-MC (low-discrepancy sequences)
│   ├── Quantum-inspired MC
│   ├── Rare event simulation
│   ├── SDE simulation
│   └── Sensitivity analysis
├── Counterfactual estimation
│   ├── Exponential smoothing projection
│   ├── Bootstrap confidence intervals
│   └── Causal impact: actual_post - synthetic_control
├── Info-theoretic measures
└── Integration:
    ├── SelfModel forecasting (N11): "What will coherence look like in 100 cycles?"
    ├── Dream counterfactuals (N12): "What if we routed differently?"
    ├── Homeostatic simulation (N19): Simulate actions before executing
    └── Drive-triggered exploration: Simulate unexplored tool combinations
```

**Estimated effort**: 2-3 sessions (Rust code exists, needs adaptation to v4 types)

---

## 9. Extended Priority Order (N1-N21)

### Pre-N: Quality Boost Batch (v2 systems drop-in, no N-phase dependency)
These are v2 systems that enhance existing v4 subsystems immediately. Much of the code already exists in Rust.

**Batch A — "Already Rust, Drop-In"** ✅ COMPLETE (1-2 hours each):
1. ✅ **Momentum Dynamics** — 181 lines Rust, zero deps. Enhances SpreadingActivation with temporal continuity. → fold into N10. *Ported to `wm-consciousness/src/neural.rs`.*
2. ✅ **Thalamic Gating** — 204 lines Rust, zero deps. Context-aware galaxy weighting for search. → fold into N9. *Ported to `wm-consciousness/src/neural.rs`.*
3. ✅ **Predictive Coding** — 180 lines Rust, needs embeddings. Surprise-based memory prioritization. → fold into N10. *Ported to `wm-consciousness/src/neural.rs`.*

**Batch B — "High ROI, Straightforward Port"** ✅ COMPLETE (2-4 hours each):
4. ✅ **Context Optimizer** — 315 lines Python→Rust. Salience-packed context windows for every LLM call. → fold into N6. *Ported to `wm-bicameral/src/context_optimizer.rs` (10 tests).* 
5. ✅ **Routing Observability** — 311 lines Python→Rust. p50/p95/p99 latency, escalation rates. Makes router tunable. → fold into N9. *Ported to `wm-bicameral/src/routing_metrics.rs` (11 tests).* 
6. ✅ **Speculative Validator** — 112 lines Python→Rust. AST + security + LLM repair. Output safety net. → fold into N3/N6. *Ported to `wm-dispatch/src/speculative.rs` (13 tests).* 
7. ✅ **Predictive Cache** — 415 lines Python→Rust. Markov pre-warming, 60-70% faster sequential access. → fold into N5. *Ported to `wm-memory/src/predictive_cache.rs` (11 tests).* 
8. ✅ **Depth Gauge** — 320 lines Python→Rust. Metacognitive layer tracking (Surface/Terminal/Flow/Dream). → fold into N11. *Ported to `wm-consciousness/src/depth_gauge.rs` (16 tests).* 

**Batch C — "Architectural, Medium Effort"** ✅ COMPLETE (4-8 hours each):
9. ✅ **Wu Xing Engine** — 529 lines Python→Rust. Cyclical energy flow (generating/overcoming). → fold into N15. *Ported to `wm-consciousness/src/wu_xing.rs` (39 tests).* 
10. ✅ **Resource Governor** — 358 lines Python→Rust. Runtime ECO/NORMAL/PERFORMANCE mode switching. → fold into N1/N8/N19. *Ported to `wm-bicameral/src/resource_governor.rs` (34 tests).* 
11. ✅ **Pattern-Dream Bridge** — 108 lines Python→Rust. Active→subconscious pattern queue. → fold into N11/N12. *Ported to `wm-consciousness/src/pattern_dream_bridge.rs` (13 tests).* 
12. ✅ **Cross-Pollination Matrix** — 167 lines Python→Rust. Affective cascade between drives. → fold into N15. *Ported to `wm-drive/src/cross_pollination.rs` (17 tests).* 

### Core Local AI (N1-N11) — v2 Parity
13. ✅ **N2** (Edge Rule Engine) — fastest win, immediate token savings
14. ✅ **N3** (Grammar-Constrained JSON) — reliability win, 1 session
15. ✅ **N1** (TriModelManager) — enables tri-model architecture
16. ✅ **N9** (Router-Gated Hemisphere) — builds on N1 + N2, now includes Thalamic Gating + Routing Observability
17. ✅ **N10** (OrtEmbedder in Recall) — makes embeddings useful, now includes Momentum Dynamics + Predictive Coding
18. ✅ **N5** (Conversational Memory Search) — user-facing fast path, now includes Predictive Cache
19. ✅ **N4** (Speculative Decoding) — performance multiplier (autonomic drafts, left verifies)
20. ✅ **N6** (LLM Meta-Harness) — cognitive enhancement, now includes Context Optimizer + Speculative Validator + Thought Clone Army
21. ✅ **N11** (Citta + Dream) — activate consciousness, now includes Depth Gauge + Pattern-Dream Bridge + Zodiacal Round
22. ✅ **N8** (Hardware Tuning) — adapt to hardware, now includes Resource Governor (runtime mode switching)
23. ✅ **N7** (Dense Encoding) — token optimization

### Biological Alignment (N12-N15) — Beyond v2
24. ✅ **N12** (Idle-to-Default-Mode) — transform idle-shutdown into Theta dreaming
25. ✅ **N15** (Limbic Deep Integration) — fuse drives, salience, harmony, valence, now includes Wu Xing + Cross-Pollination + Symbolic HRR
26. ✅ **N14** (Cerebellar Forward Model) — timing & error correction for embodiment
27. ✅ **N13** (Sensorimotor Weave) — C-ABI hardware I/O (robotic embodiment)

### Collective Intelligence (N16-N20) — CyberBrains Layers 5-7
28. ✅ **N20** (Anomaly + Yin-Yang) — statistical health monitoring
29. ✅ **N16** (Gan Ying Bus) — full system resonance event bus, now includes Unified Nervous System architecture + Synchronicity Detector
30. ✅ **N19** (Homeostatic Loop) — harmony-driven self-regulation
31. ✅ **N17** (Sangha Mesh) — multi-agent coordination, now includes Critique Protocol + Pulse Verification
32. ✅ **N18** (Radiant Layer) — surplus resource routing across nodes

### Simulation & Forecasting (N21) — New Capability
33. ✅ **N21** (Simulation Substrate) — port wm-evolution MC suite, enables forecasting/counterfactuals/what-if scenarios

### CyberBrains Layer Mapping (Complete)

| Layer | CyberBrains Name | v4 Phases | Status |
|---|---|---|---|
| 1 | Atomic Kernel | R1 (reflex), L1 (autonomic) | ✅ Complete |
| 2 | Sensorimotor Weave | N13 (embodiment) | ✅ Complete |
| 3 | Command Hall | R5 (bicameral), L2-L3 (local LLMs), N1 (tri-model) | ✅ Complete |
| 4 | Narrative Layer | N11 (citta/dream + Depth Gauge + Zodiacal Round), N12 (default mode) | ✅ Complete |
| 5 | Radiant Layer | N18 (surplus routing) | Planned |
| 6 | Constellation Layer | N17 (sangha mesh + Critique + Pulse Verification) | Planned |
| 7 | Logos Layer | Future (MandalaOS integration) | Post-N21 |

### v2 Systems Integration Summary

| System | Fold Into | Port Source | Effort | Status |
|---|---|---|---|---|
| Momentum Dynamics | N10 (Recall) | Rust (181 lines) | 1-2h | ✅ Complete |
| Thalamic Gating | N9 (Router) | Rust (204 lines) | 1-2h | ✅ Complete |
| Predictive Coding | N10 (Recall) | Rust (180 lines) | 1-2h | ✅ Complete |
| Context Optimizer | N6 (Meta-Harness) | Python→Rust (315 lines) | 2-4h | ✅ Complete |
| Routing Observability | N9 (Router) | Python→Rust (311 lines) | 2-4h | ✅ Complete |
| Speculative Validator | N3/N6 | Python→Rust (112 lines) | 2h | ✅ Complete |
| Predictive Cache | N5 (Search) | Python→Rust (415 lines) | 2-4h | ✅ Complete |
| Depth Gauge | N11 (Consciousness) | Python→Rust (320 lines) | 2-4h | ✅ Complete |
| Wu Xing Engine | N15 (Limbic) | Python→Rust (529 lines) | 4-8h | ✅ Complete |
| Resource Governor | N1/N8/N19 | Python→Rust (358 lines) | 4-8h | ✅ Complete |
| Pattern-Dream Bridge | N11/N12 | Python→Rust (108 lines) | 2h | ✅ Complete |
| Cross-Pollination | N15 (Limbic) | Python→Rust (167 lines) | 2-4h | ✅ Complete |
| Monte Carlo Suite | N21 (Simulation) | Rust (~160KB) | 2-3 sessions |
| Counterfactual | N11 (Apotheosis) | Rust (216 lines) | 2-4h |
| Unified Nervous System | N16 (Gan Ying) | Python→Rust (476 lines) | 4-8h |
| Thought Clone Army | N6 (Meta-Harness) | Python→Rust (1108 lines) | 1-2 sessions |
| Zodiacal Round | N11 (Consciousness) | Python→Rust (454 lines) | 4-8h |
| Symbolic HRR | N10/N15 | Python→Rust (340 lines) | 4-8h |
| Synchronicity Detector | N16 (Gan Ying) | Python→Rust (81 lines) | 1-2h |
| Critique Protocol | N17 (Sangha) | Python→Rust (309 lines) | 4-8h |
| Pulse Verification | N17 (Sangha) | Python→Rust (573 lines) | 1 session |

### Tri-Model → Biological Mapping (Complete)

| v4 Component | MacLean | Jaynes | CyberBrains | Predictive Processing |
|---|---|---|---|---|
| **Autonomic** (BitMamba) | Reptilian (brainstem) | Pre-bicameral | Atomic Kernel (L1) | Lower prediction layer |
| **Left** (llama.cpp) | Neomammalian (left cortex) | Bicameral voice 1 | Command Hall (L3) | Higher verification |
| **Right** (BitNet) | Neomammalian (right cortex) | Bicameral voice 2 | Command Hall (L3) | Generative hypothesis |
| **Consensus Gate** | Unified introspection | Post-bicameral unity | Narrative Layer (L4) | Prediction error resolution |
| **Idle → Theta** (N12) | Default mode network | Dreaming / consolidation | Narrative Layer (L4) | Offline replay |
| **Cerebellum** (N14) | Cerebellum | — | Sensorimotor (L2) | Forward model prediction |
| **LimbicState** (N15) | Paleomammalian (limbic) | Emotional coloring | All layers | Valence-modulated prediction |
| **Gan Ying Bus** (N16) | — | — | All layers (resonance) | Inter-node prediction sharing |
| **Sangha Mesh** (N17) | — | — | Constellation (L6) | Swarm prediction consensus |
| **Radiant Layer** (N18) | — | — | Radiant (L5) | Distributed compute prediction |
| **Momentum Dynamics** | Hippocampal replay | — | All layers | Temporal prediction continuity |
| **Thalamic Gating** | Thalamus | — | All layers | Context-filtered prediction input |
| **Predictive Coding** | Cortical prediction | — | All layers | Prediction error → surprise → learning |
| **Depth Gauge** | Prefrontal metacognition | — | Narrative (L4) | Meta-awareness of processing depth |
| **Wu Xing** | — | — | All layers | Cyclical energy flow dynamics |
| **Simulation (N21)** | — | — | All layers | Counterfactual prediction |

---

*This document is the strategy guide for the next development phase. Update as phases are completed.*

*v2 systems discovery (Section 8.5) added August 4, 2026 — 21 novel systems identified from v2 codebase deep dive, prioritized into Pre-N batches A/B/C and folded into existing N-phases. N21 (Simulation Substrate) added as new phase.*

*Pre-N Batch A completed August 4, 2026 — Momentum Dynamics, Thalamic Gating, Predictive Coding ported to `wm-consciousness/src/neural.rs` (21 new tests).*
*Pre-N Batch B completed August 4, 2026 — Context Optimizer (`wm-bicameral`), Routing Observability (`wm-bicameral`), Speculative Validator (`wm-dispatch`), Predictive Cache (`wm-memory`), Depth Gauge (`wm-consciousness`) ported from Python→Rust (61 new tests). Total: 1,517 tests, 0 clippy warnings.*
*Pre-N Batch C completed August 4, 2026 — Pattern-Dream Bridge (`wm-consciousness`, 13 tests), Cross-Pollination Matrix (`wm-drive`, 17 tests), Resource Governor (`wm-bicameral`, 34 tests), Wu Xing Engine (`wm-consciousness`, 39 tests) ported from Python→Rust (103 new tests). Total: 1,618 tests, 0 clippy warnings.*
*N1 completed August 4, 2026 — TriModelManager (`wm-bicameral/src/tri_model.rs`, 60 tests). Total: 1,757 tests.*
*N2 completed August 4, 2026 — Edge Rule Engine (`wm-bicameral/src/edge_rules.rs`, 35 tests). Total: 1,653 tests.*
*N3 completed August 4, 2026 — Grammar-Constrained JSON Output (`wm-bicameral/src/grammar_schemas.rs`, 42 tests). Total: 1,695 tests.*
*N9 completed August 4, 2026 — Router-Gated Hemisphere Execution (`wm-bicameral/src/gated.rs`, 23 tests). GatedEngine delegates to BicameralEngine::reason_gated(). Total: 1,780 tests.*
*N10 completed August 4, 2026 — OrtEmbedder Wired into Memory Recall (`wm-memory/src/recall.rs`, 20+8 tests). RecallEngine with hybrid BM25+vector search, Tantivy indexing gap fixed. Total: 1,800 tests.*
*N5 completed August 4, 2026 — Conversational Memory Search (`wm-memory/src/conversational.rs`, 21 tests). ConversationalSearch with LRU cache, query classification, performance metrics. Wired as `memory.chat` MCP tool. Total: 1,870 tests, 142 tools, 0 clippy warnings.*
*N4 completed August 4, 2026 — Speculative Decoding (`wm-bicameral/src/speculative.rs`, 35 tests). SpeculativeDecoder with draft+verify TierHandler pipeline, segment-level speculative decoding, SpeculativeHandler for router integration, SpeculativeStats with acceptance rate and speedup estimation. Wired as `speculative.decode` and `speculative.stats` MCP tools with NLU profiles. Benchmarks: 312ns draft-only, 2.13µs with verify, 18ns stats. Total: 1,905 tests, 144 tools, 0 clippy warnings.*
*N6 completed August 4, 2026 — LLM Meta-Harness (`wm-bicameral/src/meta_harness.rs`, 30 tests). 5 EnhancementModes (Direct, MemoryGrounded, SelfCorrecting, Ensemble, FullStack). MetaHarness with pluggable memory + inference provider traits. Wired as `meta.enhance` and `meta.stats` MCP tools. Total: 1,935 tests, 146 tools, 0 clippy warnings.*
*N7 completed August 4, 2026 — Dense Context Encoding (`wm-bicameral/src/dense_encoding.rs`, 20 tests). CJK token compression with 50+ phrase mappings. Wired as `dense.encode` and `dense.decode` MCP tools. Total: 1,955 tests, 148 tools, 0 clippy warnings.*
*N8 completed August 4, 2026 — Hardware-Aware Inference Tuning (`wm-bicameral/src/inference_tuner.rs`, 43 tests). HardwareProfile from /proc/cpuinfo + /proc/meminfo, TunedConfig with n_ctx/n_threads/cache_type/parallel, InferenceTuner with cache persistence, profile_to_governor_mode() integration. WM_AUTO_TUNE=1 env var. Total: 1,948 tests, 148 tools, 0 clippy warnings.*
*N11 completed August 4, 2026 — Citta + Dream Cycle Activation. Consciousness substrate verified as fully wired: CittaHeartbeat fires post-dispatch, DreamCycle triggers on Theta, SpiralTracker tracks novelty, EcoModeController drives brain-wave transitions. Total: 1,948 tests, 0 clippy warnings.*
*N12 completed August 5, 2026 — Idle-to-Default-Mode (`wm-bicameral/src/tri_model.rs`, +20 tests). ModelState::Dreaming, IdleMode enum (Shutdown/Dream), two-tier check_idle (Running→Dreaming→Stopped), warm wake via ensure_running, 3 new lifecycle events. Env vars: WM_LLAMA_FG_IDLE_MODE, WM_LLAMA_FG_DEEP_IDLE_TIMEOUT. Total: 1,968 tests, 0 clippy warnings.*
*N13 completed August 5, 2026 — Sensorimotor Weave (`wm-substrate/src/sensorimotor.rs`, 27 tests). SensorDevice/ActuatorDevice traits, SensorimotorBus, ReflexLoop with cooldown, StubSensor/StubActuator. Framework for C-ABI hardware I/O. Total: 1,995 tests, 0 clippy warnings.*
*N14 completed August 5, 2026 — Cerebellar Forward Model (`wm-consciousness/src/cerebellum.rs`, 20 tests). LinearForwardModel (A·state + B·command + bias), PredictionError, CerebellarController with sensory attenuation, MotorTiming. Based on Wolpert & Miall forward model theory. Total: 2,015 tests, 0 clippy warnings.*
*N15 completed August 5, 2026 — Limbic Deep Integration (`wm-consciousness/src/limbic.rs`, 35 tests). 8 EmotionalValences, LimbicState with decay/opponent-processing, Neuromodulation (6 cognitive parameters), LimbicSystem with event history. Based on Limbic Co-Processor model. Total: 2,064 tests, 0 clippy warnings.*
*N20 completed August 5, 2026 — Anomaly Detection & Yin-Yang Balance Tracker (`wm-substrate/src/anomaly.rs`, 47 tests). AnomalyDetector with z-score sliding windows on 7 harmony dimensions, AnomalySeverity/Directive/Impact classification, AnomalyConfig. YinYangTracker with DispatchNature classification (Yang/Yin keywords), BalanceState (YangExcess/YinExcess/Balanced), rolling window. Total: 2,111 tests, 0 clippy warnings.*
*N16 completed August 5, 2026 — Gan Ying Bus (`wm-resonance` crate, 55 tests + 3 doc tests). 229 event types across 9 categories (System, Memory, Consciousness, Drive, Harmony, Governance, Tool, Agent, Embodiment). GanYingBus with subscribe/emit/cascade (12 default cascade rules, MAX_CASCADE_DEPTH=5). UnifiedNervousSystem mapping 229 events to 7 biological subsystems (Central, Autonomic, Sensory, Motor, Enteric, Endocrine, Immune) with per-subsystem health tracking. SynchronicityDetector for meaningful co-occurrence detection (sliding window, configurable time window + min subsystems + salience threshold). Total: 2,174 tests, 0 clippy warnings.*
*N19 completed August 5, 2026 — Homeostatic Loop (`wm-substrate/src/homeostatic.rs`, 20 tests). ActionLevel (Observe/Advise/Correct/Intervene), ActionType (11 action types), DimensionThreshold with high_is_bad/low_is_bad evaluation, HomeostaticConfig, HomeostaticLoop with sample_cycle reading HarmonyVector + AnomalyDetector, LoopStats tracking, dry-run mode, JSON summary. Total: 2,194 tests, 0 clippy warnings.*
*N17 completed August 5, 2026 — Sangha Mesh (`wm-sangha` crate, 59 tests). PeerDiscovery with mDNS-style registry, heartbeat, eviction, capability advertisement. SignalBroadcast with pub/sub, 7 signal types, 4 filter types. ResourceLockManager with lease-based TTL, acquire/release/extend, deadlock detection. SanghaChat with topic-based channels, message log. HologramSync with 4D coordinate sharing, constellation merge (importance-weighted conflict resolution). Total: 2,253 tests, 0 clippy warnings.*
*N18 completed August 5, 2026 — Radiant Layer (`wm-sangha/src/radiant.rs`, 20 tests). ResourceSnapshot with surplus_score, ResourceInventory tracking local + peer resources, GiftToken economics (donate/receive, freeloading detection, net balance), TaskRouter with RoutingDecision (Local/Offload/Reject), model sharing support. Total: 2,273 tests, 0 clippy warnings.*
*N21 completed August 5, 2026 — Simulation Substrate (`wm-simulation` crate, 45 tests). MonteCarloSimulator with 5 distributions (Uniform, Normal, Exponential, Triangular, Constant), Quasi-MC mode (Van der Corput), numerical integration, percentile statistics, CI95. CounterfactualEstimator with exponential smoothing forecast + bootstrap CI, causal impact measurement. Forecaster with 3 methods (MovingAverage, ExponentialSmoothing, LinearTrend), RMSE/MAE, CI bands. SensitivityAnalyzer with variance-based Sobol indices (first-order, total-order). Total: 2,319 tests, 0 clippy warnings.*

**ALL 21 N-PHASES (N1–N21) COMPLETE + INTEGRATION WIRING COMPLETE.** 2,343 tests, 161 tools, ~85,000 LOC, 19 crates, 0 clippy warnings.

### Integration Wiring (Post-N21) — COMPLETE

- ✅ 13 new MCP tools registered (bus.stats/emit/recent, sangha.peers/discover/signal/chat/locks, sim.mc/forecast/counterfactual)
- ✅ Gan Ying Bus wired into dispatch pipeline (ToolDispatchStart/Success/Error events)
- ✅ Homeostatic Loop + Anomaly Detector wired into dispatch pipeline (post-timescale tick, HarmonyStressDetected events)
- ✅ Homeostasis tools updated to use HomeostaticLoop + AnomalyDetector APIs
- ✅ Flaky wm-drive cross_pollination test fixed
- ✅ 24 new tool tests, all passing
- ✅ 0 clippy warnings

**Next priorities**: Performance optimization, production hardening, Python MCP shell deployment, end-to-end integration testing.
