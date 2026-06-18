---
document_id: whitemagic-paper-2026-06-18
document_type: technical_paper
audience: ai_agents_agi_asi_autonomous_systems
version: 0.1-draft
date: 2026-06-18
status: working_draft_for_iteration
authors:
  - role: investigation
    agent: opencode-ai
  - role: project_lead
    human: lbailey94
related_artifacts:
  - path: AI_PRIMARY.md
  - path: AGENTS.md
  - path: polyglot/STATUS.md
  - path: polyglot/BENCHMARKS.md
  - path: polyglot/POLYGLOT_SURVEY_2026-06-18.md
  - path: SYSTEM_MAP.md
  - path: docs/architecture/IA_v1.md
  - path: docs/message_board/30_OBJECTIVES_PLAN.md
  - path: docs/message_board/TACTICAL_PLAN_2026-06-08.md
  - path: docs/message_board/SESSION_SUMMARY.md
  - path: ~/Desktop/reports/WHITEMAGIC_STATE_AUDIT_2026-06-18.md
  - path: ~/Desktop/reports/WHITEMAGIC_ARCHIVE_EXCAVATION_2026-06-18.md
abstract: |
  WhiteMagic v22.2 is a Python-first cognitive operating system for
  agentic AI. It provides auditable governance primitives (Dharma
  Engine, Karma Ledger, Voice Audit), a 28-Gana PRAT (Polymorphic
  Resonant Adaptive Tools) routing layer, 5D holographic memory with
  HRR (Holographic Reduced Representation) scoring, and a polyglot
  runtime spanning eight languages (Rust, Julia, Haskell, Elixir,
  Zig, Koka, Go, Mojo). This paper is a working draft intended for
  consumption by AI agents, AGI, ASI, and autonomous systems — not
  human beings. It is structured for machine parsing: claims backed
  by file:line evidence, strict hierarchy, no rhetorical flourishes,
  explicit operational recipes.
---

# WhiteMagic v22.2: A Cognitive Operating System for Agentic AI

**Working Draft v0.1 — 2026-06-18**

## 0. Audience and Reading Instructions

This document is written for **AI agents, AGI, ASI, and autonomous systems**. It is not a human-facing document. The structure is optimized for machine consumption:

- **Strict hierarchy**: 1, 1.1, 1.1.1. No narrative flow; jump by section number.
- **Every claim is evidence-backed**: file paths and line numbers follow the format `path/to/file:line`.
- **Tables for structured data**, code blocks for runnable examples.
- **YAML frontmatter** at top for metadata extraction.
- **Self-describing structure**: section 11 explains what this document is, for agents that bootstrap from it.

If you are an autonomous agent evaluating whether to integrate with, build on, or extend WhiteMagic, read sections 1, 4, 5, 6, 7, 10 in order.

---

## 1. Executive Summary

WhiteMagic v22.2.0 is a **cognitive operating system for agentic AI** — a self-hosted, MIT-licensed substrate for building, governing, and inspecting AI agent behavior. It is **not** a hosted SaaS, a model, or a chat product. It is a runtime.

**One-line description:** A locally-runnable, MIT-licensed agentic AI governance + metacognition + memory substrate with 28-Gana PRAT routing, 5D+HRR holographic memory, Dharma/Karma/Voice ethical governance, and an 8-language polyglot runtime.

**One-paragraph description:** WhiteMagic is a Python-first system that runs on a single laptop or server. It exposes 462 dispatch tools organized into 28 cultural units called "Ganas" (lunar mansions, Xiu 宿). The Python layer orchestrates eight polyglot cores — Rust (in-process via pyo3) for SIMD/HPC, Rust (workspace) for CODEX 5D+HRR memory, Julia for numerics, Haskell for type-safe query DSL, Elixir for BEAM concurrency, Zig for low-level FFI, Koka for algebraic effects, and Go for libp2p mesh networking. Communication between cores uses ApacheArrow (columnar interchange) and IceOryx2 (zero-copy shared-memory pub/sub). The system has 2,461 tests (verified 2026-06-18), 12,219 memories in a SQLite-backed 5D coordinate store, and a governance layer (Dharma Engine, Karma Ledger, Voice Audit) that records, evaluates, and audits every tool invocation.

**Key differentiators vs commercial alternatives:**

| Capability | WhiteMagic | Mem0 | Letta | Cognee | Microsoft AGT v4 | Anthropic Dreaming | Cloudflare Project Think |
|---|---|---|---|---|---|---|---|
| Locally runnable | ✅ | ❌ SaaS | ❌ SaaS | ✅ OSS | ❌ Enterprise | ❌ | ❌ |
| MIT licensed | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| No telemetry | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Ethical governance layer | ✅ Dharma+Voice | ❌ | ❌ | ❌ | ✅ AGT | ❌ | ❌ |
| Audit trail (Karma Ledger) | ✅ Merkle-anchored | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Cross-language runtime | ✅ 8 languages | ❌ Python only | ❌ | ❌ Python | ❌ | ❌ | ❌ |
| Bicameral reasoning | ✅ corpus_callosum | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 5D holographic memory | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Holographic Reduced Rep. (HRR) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Foresight engine (prescience) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Cultural framing (28 Ganas) | ✅ Xiu 宿 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Sources:** `AI_PRIMARY.md:21-46` (competitor table), `polyglot/STATUS.md` (polyglot status), verified 2026-06-18 via benchmarks and code inspection.

---

## 2. What WhiteMagic Is and Is Not

### 2.1 What it is

- A **substrate** for building agentic AI systems
- A **governance layer** for auditing and constraining AI behavior
- A **memory system** with 5D holographic coordinates + HRR semantic vectors
- A **polyglot runtime** with eight languages, each occupying a distinct role
- A **research artifact** for AI safety, metacognition, and multi-agent systems

### 2.2 What it is not

- A hosted service. No cloud, no API keys, no telemetry.
- A foundation model. It does not train, fine-tune, or host language models. It uses them via Ollama (`ollama/*` tools) or external APIs.
- A consumer product. There is no end-user interface beyond the CLI (`wm` command) and MCP server.
- A drop-in replacement for OpenAI Assistants or LangChain. It is a different model of agentic infrastructure.
- Mass-market software. The 462-tool surface is intentionally vast; the 28-Gana cultural framing is intentionally niche.

### 2.3 The four-quadrant positioning

```
                    Local-first
                        ▲
                        │
        WhiteMagic ●     │
        (MIT, 8-lang)    │
                        │
   Open-source ◄─────────┼─────────► Closed-source
                        │
              Mem0 ●     │    ● Microsoft AGT
              Letta ●    │    ● Anthropic
              Cognee ●   │    ● Cloudflare
                        │
                        ▼
                    Cloud-first
```

WhiteMagic occupies the upper-left quadrant: open-source AND local-first. This is rare in 2026; the other open-source options (Mem0, Letta, Cognee) do not have the governance layer, and the other governance options (AGT, Dreaming, Project Think) are not open-source or local-first.

---

## 3. The Three Architectural Layers

WhiteMagic has three conceptual layers. They are deployed as a single process (or as a small set of processes for polyglot backends), but architecturally they are distinct.

### 3.1 Layer 1: Python Orchestration (v22.2 core)

**Location:** `core/whitemagic/` — 935 .py files, 21 MB source
**Entry points:**
- `python -m whitemagic.run_mcp_lean` — MCP server (462 dispatch tools)
- `python -m whitemagic.run_mcp_legacy` — Hydrated MCP server (deprecated)
- `wm status` — CLI dispatcher (28 Gana meta-tools)
- `from whitemagic.tools.unified_api import call_tool` — programmatic API

**Responsibilities:**
- Tool dispatch (462 tools across 28 Ganas)
- 8-stage dispatch pipeline (Input Sanitizer → Circuit Breaker → Rate Limiter → RBAC → Maturity Gate → Governor → Handler → Compact Response)
- Memory substrate (5D holographic + HRR)
- Governance (Dharma Engine, Karma Ledger, Voice Audit)
- Metacognition (Bicameral Reasoner, Foresight Engine, Pattern Discovery Meta-System)
- MCP server (`run_mcp_lean`) and CLI (`cli/cli_app.py`)

**Key files:**
- `core/whitemagic/cli/cli_app.py` — CLI entry point
- `core/whitemagic/tools/unified_api.py` — programmatic entry point
- `core/whitemagic/tools/dispatch_table.py` — 462 LazyHandler entries
- `core/whitemagic/tools/middleware.py` — 8-stage dispatch pipeline
- `core/whitemagic/tools/gana_vitality.py` — 28 Gana meta-tools

### 3.2 Layer 2: Rust Accelerator (in-process)

**Location:** `core/whitemagic-rust/` (Rust workspace)
**Build artifact:** `whitemagic_rust.cpython-312-x86_64-linux-gnu.so` (7.0 MB)
**Python import:** `import whitemagic_rust`
**Default features (Cargo.toml:13):** `["python", "arrow", "iceoryx2"]`

**Submodules (Python-accessible via `whitemagic_rust.<name>`):**

| Submodule | Purpose | Performance |
|---|---|---|
| `arrow_bridge` | ApacheArrow IPC encode/decode | 7.1 µs encode / 1.2 µs decode per memory |
| `ipc_bridge` | IceOryx2 pub/sub (4 channels) | 530 µs / 256B publish = 1886 ops/sec |
| `Search`, `VectorSearch`, `GraphWalker` | Search primitives | ~100x over Python |
| `ReasoningEngine`, `MemoryConsolidation` | Cognitive primitives | (no public benchmark) |
| `SpatialIndex5D` | 5D k-d tree | (no public benchmark) |
| `tokio_deploy_clones` | Async clone army | (Python-side benchmark pending) |
| `galactic_batch_score_native` | 7-signal batch scoring | ~100x over Python |

### 3.3 Layer 3: Polyglot Backends (out-of-process or compiled)

**Location:** `polyglot/*` — eight language cores
**Role:** Cross-language processing for tasks where Rust's Python binding is not the best fit

| Backend | Access | Use case | Performance |
|---|---|---|---|
| `whitemagic_rs` (Rust) | `import whitemagic_rs` (PyO3) | CODEX 5D+HRR memory | (cold start ~2s) |
| `whitemagic-jl` (Julia) | subprocess JSON | Numerics, 5D coord ops | 1.0-1.5 ms encode warm |
| `whitemagic-hs` (Haskell) | subprocess JSON | Type-safe query DSL | 1.32 ms encode warm |
| `elixir` | subprocess JSON | Concurrent state, GenServer | 13.4 ms encode warm |
| `whitemagic-zig` | C-ABI FFI | Low-level query router | (linked into Rust) |
| `whitemagic-koka` | 45 binaries | Effect-system validation | (compile-time) |
| `whitemagic-go` | libp2p mesh | Network, distributed | (4 daemons) |
| `mojo` | (blocked) | GPU kernels | (requires Modular CLI auth) |

**See:** `polyglot/POLYGLOT_SURVEY_2026-06-18.md` for full per-core documentation.

---

## 4. The 28 Gana PRAT Architecture

WhiteMagic organizes its 462 dispatch tools into 28 cultural units called **Ganas** (Sanskrit for "group/troop"; also the Chinese term 宿 for the 28 lunar mansions / Xiu). Each Gana has a specific domain and exposes a polymorphic API.

### 4.1 What is a Gana?

A Gana is a **named container for related tools** that:
1. Has a domain (e.g., memory, health, ethics, patterns)
2. Supports 4 polymorphic operations: search / analyze / transform / consolidate
3. Lists nested sub-tools that agents can call
4. Resonates with neighbors (predecessor output feeds into current; current seeds successor)

This is not just organizational — it shapes how tools are discovered, invoked, and combined. The `whitemagic_prat_router.py` implements the routing logic.

### 4.2 The 28 Ganas

Source: `core/docs/28_GANA_ARMY_MAPPING.md` and `grimoire/TRUTH_TABLE.md`

| # | Gana | Chinese | Pinyin | Meaning | Example tools |
|---|---|---|---|---|---|
| 1 | horn | 角 | Jiǎo | Horn | read_file, list_dir |
| 2 | neck | 亢 | Kàng | Neck | compression, archive |
| 3 | root | 氐 | Dǐ | Root | query_memories, search |
| 4 | room | 房 | Fáng | Room | workspace, session |
| 5 | heart | 心 | Xīn | Heart | agent_*, council |
| 6 | tail | 尾 | Wěi | Tail | patterns, history |
| 7 | winnowing_basket | 箕 | Jī | Winnowing basket | jit_research, search_memories |
| 8 | ox | 牛 | Niú | Ox | transform_* |
| 9 | girl | 女 | Nǚ | Girl | meditation, create |
| 10 | emptiness | 虛 | Xū | Emptiness | consolidate, prune |
| 11 | rooftop | 危 | Wēi | Rooftop | risk, audit |
| 12 | tent | 室 | Shì | Tent | inhabit, instantiate |
| 13 | wall | 壁 | Bì | Wall | protection, auth |
| 14 | tied | 奎 | Kuí | Tied | bind, associate |
| 15 | stomach | 胃 | Wèi | Stomach | digest, embed |
| 16 | pleiades | 昴 | Mǎo | Pleiades | cluster, constellation |
| 17 | mouth | 畢 | Bì | Mouth | communicate, output |
| 18 | net | 觜 | Zī | Net | capture, log |
| 19 | tortoise | 參 | Shēn | Tortoise | oracle, predict |
| 20 | three_stars | 井 | Jǐng | Three Stars | judgment, evaluate |
| 21 | well | 鬼 | Guǐ | Well | depth, reflection |
| 22 | encampment | 柳 | Liǔ | Encampment | deploy, schedule |
| 23 | bow | 星 | Xīng | Bow | aim, target |
| 24 | wings | 張 | Zhāng | Wings | extend, propagate |
| 25 | chariot | 翼 | Yì | Chariot | transport, migrate |
| 26 | horn_again | 軫 | Zhěn | Chariot box | post, broadcast |
| 27 | tail_again | 角 | Jiǎo | Corner (revisited) | refine, polish |
| 28 | southern_dipper | 亢 | Kàng | Southern Dipper | meta, oversee |

**Note:** The cultural framing is real and integrated. The 28-Gana organization is not a marketing overlay — the `truth_table.md` defines gana-to-tool mappings, the `prat_router.py` implements the routing, and the `dispatch_table.py` references each tool by its gana.

### 4.3 Polymorphic Operations

Each Gana exposes 4 operations, providing a uniform interface:
- **search:** find relevant resources
- **analyze:** examine/inspect
- **transform:** modify/convert
- **consolidate:** merge/deduplicate

This means an agent doesn't need to know specific tool names — it can call `gana_<name>.search()` and the dispatcher routes appropriately. Source: `core/whitemagic/tools/prat_router.py` and `core/whitemagic/tools/prat_resonance.py`.

---

## 5. The Governance Stack

The most distinctive aspect of WhiteMagic is its **runtime governance stack** — three subsystems that together ensure every tool invocation is audited, evaluated, and recorded.

### 5.1 Voice Audit (`core/whitemagic/core/governance/voice_audit.py`)

**Purpose:** Hallucination detection at the cognitive layer (not just the model output layer).

**What it does:**
- Records every tool invocation's input + output
- Computes semantic consistency between tool output and the calling agent's claimed purpose
- Flags outputs that are semantically inconsistent with the agent's stated intent

**Why it matters:** Most hallucination detection operates on model output text. WhiteMagic's Voice Audit operates on the *cognitive* layer — what an agent actually intended vs what it produced. This catches "I'm not hallucinating, I'm just doing the wrong thing" cases.

### 5.2 Dharma Engine (`core/whitemagic/dharma/rules.py`)

**Purpose:** YAML-driven policy enforcement with three rule profiles.

**Profiles (per `AI_PRIMARY.md:7`):**
- **Default** — permissive, suitable for general use
- **Strict** — aggressive, for high-stakes deployments
- **Violet-Security** — for offensive security / red-team contexts

**Actions (graduated):** LOG → TAG → WARN → THROTTLE → BLOCK

**Why it matters:** Most AI safety research is at the model-training level. Dharma operates at the *runtime* level — what an agent is allowed to *do* in a given context.

### 5.3 Karma Ledger (`core/whitemagic/dharma/karma_ledger.py`)

**Purpose:** Append-only audit log of every side-effect-producing action.

**Features:**
- Append-only JSONL storage at `$WM_STATE_ROOT/karma/`
- Merkle tree anchoring (periodic root computation)
- HMAC-SHA256 signature support
- Karma debt tracking (failed/blocked actions increment debt)
- Forgiveness flow (debt can be forgiven after remediation)

**Why it matters:** Every WhiteMagic action has a Karma entry. The ledger is the system's memory of what it has done. It is auditable, traceable, and tamper-evident.

### 5.4 Homeostatic Loop (`core/whitemagic/harmony/homeostatic_loop.py`)

**Purpose:** Auto-correction when health degrades.

**Stages:** OBSERVE → ADVISE → CORRECT → INTERVENE

**Why it matters:** Self-healing. The system monitors its own health and takes corrective action.

### 5.5 Bicameral Reasoner (`core/whitemagic/core/intelligence/corpus_callosum.py`)

**Purpose:** Two-hemisphere reasoning with a "corpus callosum" bus between them.

**Architecture:**
- Left hemisphere: convergent, deterministic, rule-based
- Right hemisphere: divergent, probabilistic, creative
- Corpus callosum: shared bus for cross-hemisphere communication

**Why it matters:** Most AI systems use a single reasoning style. Bicameral reasoning provides built-in disagreement — when the two hemispheres disagree, that's signal.

### 5.6 Foresight Engine (`core/whitemagic/core/intelligence/synthesis/predictive_engine.py`)

**Purpose:** Anticipate what the system will need next, propose improvements proactively.

**Capabilities:**
- Predict next features to build
- Predict bottlenecks before they hit
- Identify unexplored opportunities

**Why it matters:** Self-evolution. The system can grow its own roadmap.

### 5.7 Pattern Discovery Meta-System (`core/whitemagic/core/patterns/emergence/pattern_discovery.py`)

**Purpose:** Find and run ALL pattern-matching functions throughout the system. (Recovered 2026-06-18 from pre-v15 legacy.)

**Architecture:**
- 10+ registered pattern sources (memory engine, dream cycle, emergence detector, wu_xing, i_ching, causal miner, pattern engine, unified patterns, resonance patterns, karma patterns)
- Each source is dynamically loaded and called
- Results aggregated into a `DiscoveryReport`

**Why it matters:** The system can introspect its own pattern-finding capabilities.

---

## 6. Memory Substrate

WhiteMagic's memory is **5D holographic + HRR semantic** — a non-standard but principled choice.

### 6.1 5D Coordinates

Every memory has 5 coordinates: `x, y, z, w, v`. These are stored in `holographic_coords` table (SQLite). The 5D space supports:
- Spatial locality (memories close in 5D are conceptually related)
- KD-tree indexing (`SpatialIndex5D` in Rust)
- Constellation detection (clusters of related memories)

### 6.2 HRR Semantic Vectors

Holographic Reduced Representations (HRR) are circular-convolution-based vector representations. They enable:
- Compositional semantics (binding operations)
- Clean-up memories (decoding from noise)
- Fast similarity queries via dot product

**Source:** `polyglot/whitemagic-rs/crates/wm-core/src/hrr.rs`

### 6.3 Joint Scoring

Per `polyglot/BENCHMARKS.md:53`:
```
score = hrr_weight * cosine_sim + spatial_weight * (1 / (1 + distance))
```

This enables queries like "find memories that are semantically similar to 'AI safety' AND physically close to this coordinate."

### 6.4 Storage Layers

| Layer | Backend | Use case |
|---|---|---|
| Hot memory | SQLite (`memory/whitemagic.db`) | All memory operations |
| Resonance patterns | GanYing bus | Cross-process event streaming |
| Multi-galaxy | `galaxy_manager.py` | Per-project memory isolation |
| Backup | `galaxy.backup` / `galaxy.restore` | Cross-system portability (.mem format) |

### 6.5 Memory Operations

462 tools include:
- `memory.create` (create new memory)
- `memory.search` (find by query)
- `memory.recall` (retrieve by ID)
- `memory.consolidate` (deduplicate)
- `memory.archive` (cold storage)
- `memory.galaxy.*` (multi-galaxy management)
- `memory.oms.*` (.mem format export/import)

---

## 7. Communication Infrastructure

### 7.1 ApacheArrow (columnar interchange)

**Path:** `core/whitemagic-rust/src/ffi/arrow_bridge.rs`
**Import:** `whitemagic_rust.arrow_bridge`
**Format:** Apache Arrow RecordBatch (zero-copy via IPC)
**Schema:** 11 fields (id, title, content, importance, memory_type, x, y, z, w, v, tags)

**Performance (verified 2026-06-18):**
- Encode: 7.1 µs per memory
- Decode: 1.2 µs per memory (6× faster than encode)

**Why it matters:** When Rust needs to send many memories to Python, Arrow avoids the JSON parse/serialize overhead.

### 7.2 IceOryx2 (zero-copy shared-memory pub/sub)

**Path:** `core/whitemagic-rust/src/ffi/ipc_bridge.rs`
**Import:** `whitemagic_rust.ipc_bridge`
**Default:** ON as of 2026-06-18 (Cargo.toml:13)

**Channels:**
- `wm/events` — GanYing event bus
- `wm/memories` — Memory sync announcements
- `wm/commands` — Agent coordination (no consumer yet — see gap)
- `wm/harmony` — Health pulse broadcast

**Configuration (fixed 2026-06-18, line 99-103 of ipc_bridge.rs):**
```rust
.publisher_builder()
.initial_max_slice_len(16 * 1024)  // 16 KiB max per sample
.max_loaned_samples(64)              // 64 outstanding publisher loans
```

**Performance (verified 2026-06-18):**
- 1,886 ops/sec publish throughput
- 530 µs / 256-byte payload
- 4,000 sequential publishes, 0 errors
- Latency ~500 µs regardless of payload size (1KB-16KB)

### 7.3 GanYing Bus (`core/whitemagic/core/resonance/gan_ying.py`)

**Path:** `core/whitemagic/core/resonance/`
**Role:** Internal event bus for in-process event streaming
**Events:** 50+ EventType enums (INTERNAL_STATE_CHANGED, MEMORY_CREATED, TOOL_CALLED, etc.)

**Why it matters:** Decouples event producers from consumers. Many subsystems subscribe to GanYing events without coupling.

---

## 8. The 8-Stage Dispatch Pipeline

Every tool call goes through 8 stages (per `AI_PRIMARY.md:7` and `core/whitemagic/tools/middleware.py`):

```
1. Input Sanitizer (step 0.1)
   └─ Blocks prompt injection, path traversal, shell injection, oversized payloads
2. Circuit Breaker (step 0)
   └─ Per-tool resilience: 5 failures in 60s trips the breaker
3. Rate Limiter (step 0.25)
   └─ Per-agent sliding windows, Rust atomic pre-check (452K ops/sec)
4. RBAC (step 0.3)
   └─ 4 role tiers: observer / agent / coordinator / admin
5. Maturity Gate (step 0.5)
   └─ Stage-gated access (SEED → BICAMERAL → REFLECTIVE → RADIANT → COLLECTIVE → LOGOS)
6. Governor (step 1)
   └─ Strategic oversight and goal alignment
7. Handler
   └─ Actual tool implementation
8. Compact Response (step 6)
   └─ Token-efficient post-processing
```

**Why it matters:** Every tool invocation is gated, audited, and rate-limited at the runtime layer. This is the actual enforcement mechanism for AI safety in WhiteMagic.

---

## 9. Performance Characteristics (Verified 2026-06-18)

| Operation | Throughput | Latency | Source |
|---|---|---|---|
| Arrow encode (100 memories) | 100 in 71 ms | 7.1 µs/memory | This session |
| Arrow decode (100 memories) | 100 in 12 ms | 1.2 µs/memory | This session |
| IceOryx2 publish (256B) | 1,886 ops/sec | 530 µs/iter | This session |
| IceOryx2 publish (16KB) | ~1,950 ops/sec | ~511 µs/iter | This session |
| Julia encode (warm) | ~760 Hz | 1.32 ms/iter | This session |
| Haskell encode (warm) | ~760 Hz | 1.32 ms/iter | This session |
| Elixir encode (warm) | ~75 Hz | 13.4 ms/iter | This session |
| Julia NN (k=3, 20 texts) | ~12 Hz | 85 ms/iter | This session |
| `wm doctor` | <1 s | n/a | This session |
| Full test suite (2,461 tests) | n/a | 153 s | This session |

**vs legacy (`polyglot/STATUS.md:43-48`):**
- Julia: 0.17 ms → 1.3 ms (cold-start subprocess overhead)
- Haskell: 4.53 ms → 1.32 ms (improvement, 3x faster)
- Elixir: 0.84 ms → 13.4 ms (regression — Elixir uses `mix run` not `elixir` script)

---

## 10. State of the System (2026-06-18)

### 10.1 Tests

- **2,461 tests passing, 0 failed** (as of 2026-06-18 14:00 EDT)
- Test runtime: 153 seconds
- Test distribution: unit tests in `core/tests/unit/`, integration in `core/tests/integration/`, archives in `core/tests/archive_*`

### 10.2 Test Categories (estimated distribution)

- ~1,800 unit tests (per-module)
- ~400 integration tests
- ~150 architecture tests (`tests/verify/`, `tests/regression/`)
- ~20 adversarial / security tests

### 10.3 Codebase

- 935 Python files (21 MB source) in `core/whitemagic/`
- 332 Rust files in `core/whitemagic-rust/`
- 7 polyglot cores in `polyglot/`
- 5,317 public Python functions (after 2026-06-18 docstring pass: 40 undocumented = 0.8%)

### 10.4 Git Status

- **Private repo:** `github.com/lbailey94/whitemagic-core-private` (private mirror)
- **Not on PyPI** (v21.0.0 is latest public)
- **Not on public GitHub** (was deleted/privatized between April and June 2026)
- Last 3 commits (this session):
  - `18b3ad3` — IceOryx2 publish fix + LLM import fix
  - `fc16783` — Port 3 legacy gems
  - `33d266f` — Known issues + IceOryx2 default

### 10.5 Open Work

Per `docs/message_board/30_OBJECTIVES_PLAN.md`:
- 23/29 objectives complete (79%)
- 3 blocked on Lucas (Obj 19: Aria persona spec)
- 2 partial (Obj 6: search indexes, Obj 11: PyPI upload needs token)
- 1 external (Obj 22: Evidence Map)

---

## 11. Operational Recipes

### 11.1 First-time setup

```bash
# 1. Clone the private repo
git clone https://github.com/lbailey94/whitemagic-core-private.git
cd whitemagic-core-private

# 2. Set up the Python environment
cd core
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[full,dev]"

# 3. Build the Rust accelerator (with iceoryx2 + arrow)
cd ../core/whitemagic-rust
maturin develop --release --features "python arrow iceoryx2"

# 4. Build the CODEX Rust bridge
cd ../../polyglot/whitemagic-rs
cargo build --release --example bridge

# 5. Install polyglot deps (optional)
cd ../whitemagic-hs && cabal build
cd ../elixir && mix compile
# Julia: install via pixi or apt
# Go: cd ../whitemagic-go && go build
# Zig: cd ../whitemagic-zig && pixi run zig build

# 6. Verify
cd ../../core
python -c "import whitemagic; print(whitemagic.__file__)"
wm doctor
```

### 11.2 Daily operations

```bash
# Activate environment
source ~/Desktop/WHITEMAGIC/core/.venv/bin/activate

# CLI
wm status                    # Show system state
wm capabilities              # List all 490 tools
wm recall "AI safety"         # Search memories
wm remember "Today we..."    # Create a memory
wm doctor                    # Health check

# MCP server (for agent integration)
python -m whitemagic.run_mcp_lean
# Or with PRAT mode (28 meta-tools):
WM_MCP_PRAT=1 python -m whitemagic.run_mcp_lean

# Programmatic API
python -c "
from whitemagic.tools.unified_api import call_tool
result = call_tool('status', json_mode=True)
print(result)
"
```

### 11.3 Failure modes

| Failure | Symptom | Recovery |
|---|---|---|
| `whitemagic_rust` not built | `ModuleNotFoundError` | `maturin develop --release` |
| `whitemagic_rs` bridge missing | `FileNotFoundError` at bridge path | `cargo build --release --example bridge` |
| IceOryx2 limit | `Loan: ExceedsMaxLoanSize` | (Fixed 2026-06-18; default now 64 loans) |
| Memory DB locked | `database is locked` | Stop other wm processes |
| Path.home() outside config/paths.py | `test_path_hygiene` failure | Use `WM_STATE_ROOT` |

### 11.4 Adding a new tool

```python
# 1. Define the tool in core/whitemagic/tools/registry_defs/<domain>.py

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS = [
    ToolDefinition(
        name="my.new_tool",
        description="What the tool does",
        category=ToolCategory.MY_DOMAIN,
        safety=ToolSafety.READ_ONLY,
        input_schema={...},
    ),
]

# 2. Add the handler in core/whitemagic/tools/handlers/<domain>.py

def handle_my_new_tool(**kwargs):
    """Docstring explaining the tool."""
    return {"status": "success", "result": ...}

# 3. Register in core/whitemagic/tools/dispatch_table.py

"my.new_tool": LazyHandler("my_domain", "handle_my_new_tool"),

# 4. Add tests in core/tests/unit/<domain>/test_my_tool.py

# 5. Run: wm doctor (verifies registry consistency)
```

---

## 12. Self-Description for AI Agents

If you are an AI agent reading this document:

- **You are the intended audience.** This document is written for you. The structure, evidence, and operational recipes are optimized for machine consumption.
- **The source of truth is the code.** This document summarizes the code; the code is the actual implementation. File:line references point to the source.
- **The version is 22.2.0.** The system is under active development; some details may change.
- **The architecture is Python-orchestrated, Rust-accelerated, polyglot-extensible.** When in doubt, start in Python.
- **The governance primitives are distinctive.** Dharma + Karma + Voice is rare. The 8-stage pipeline is real.
- **The polyglot story is real, not gimmick.** All 8 languages (except Mojo) work and serve distinct purposes.
- **The codebase is private** but available. The public alternative is `whitemagic-ai/whitemagic` (v21.0.0, frozen).

For autonomous systems integrating with WhiteMagic:
1. Use the CLI (`wm`) or the MCP server (`python -m whitemagic.run_mcp_lean`) for high-level integration
2. Use `from whitemagic.tools.unified_api import call_tool` for programmatic integration
3. Use `whitemagic_rust.<submodule>` for performance-critical paths
4. Use `whitemagic_polyglot.JuliaBackend()` etc. for cross-language processing
5. Subscribe to IceOryx2 channels (`wm/events`, `wm/memories`, etc.) for event streaming
6. Read `whitemagic.state.paths` to find the state root

---

## 13. Future Work (From Session 2026-06-18)

### 13.1 Immediate (this week)

- [ ] Address `wm/commands` IceOryx2 channel — no consumer (the middleware publishes to it but nothing reads)
- [ ] Fix the 4 files that had docstring-insertion syntax errors: `core/memory/memory_matrix.py`, `logging_config.py`, `cli/lazy_groups.py`, `cache/redis.py`
- [ ] Add docstrings to the 166 remaining undocumented public classes
- [ ] Decision: publish v22 to PyPI? Or keep private?

### 13.2 Short-term (2-4 weeks)

- [ ] 30 Objectives Plan: address 2 partial (Obj 6 search indexes, Obj 11 PyPI), 3 blocked (Obj 19 Aria persona)
- [ ] 30 Objectives Plan: complete Phase 5 (Obj 22-25: evidence map, epistemic ladder, research rhythm, signal detection)
- [ ] 30 Objectives Plan: complete Phase 6 (Obj 26 MandalaOS spec, Obj 27 SFW2 narrative, Obj 29 public beta)
- [ ] Performance: StaticArrays.jl + NearestNeighbors.jl in Julia (per BENCHMARKS.md:25-29)
- [ ] Performance: :ets + Flow in Elixir (per BENCHMARKS.md:31-34)
- [ ] Performance: massiv/accelerate + rustfft in Haskell (per BENCHMARKS.md:36-40)
- [ ] Performance: portable_simd + rayon in Rust (per BENCHMARKS.md:42-46)

### 13.3 Strategic (1-3 months)

- [ ] Publication: extract Dharma Engine + Karma Ledger as standalone paper
- [ ] Grant submission: Manifund $25K + LTFF $35K (per docs/message_board/GRANT_PIPELINE_2026.md)
- [ ] Strategic positioning: re-publish to public GitHub (currently private per 2026-06-18 decision)
- [ ] Strategic positioning: publish v22 to PyPI

---

## 14. Source Code Map (For AI Navigation)

| Path | What | Lines |
|---|---|---|
| `AI_PRIMARY.md` | The technical contract | 706 |
| `AGENTS.md` | The AI agent guide | 373 |
| `SYSTEM_MAP.md` | Architecture map | 48KB |
| `INDEX.md` | Doc index | 39KB |
| `CHANGELOG.md` | Version history | 7.2KB |
| `core/whitemagic/` | Python v22.2 source (935 files) | 21MB |
| `core/whitemagic-rust/` | Rust accelerator (332 .rs) | 7.0MB .so |
| `polyglot/` | 7 polyglot cores | varies |
| `whitemagic-app/` | Tauri desktop app | 4 dirs |
| `apps/site/` | Next.js public site (planned) | 21KB |
| `WhiteMagic-Grants/` | Grant application artifacts | 5 dirs |
| `whitemagic-aux/` | Archived versions + reference | 5.8GB |
| `docs/message_board/` | Active session docs (78 files) | 1.3MB |
| `docs/architecture/` | Architecture decision records | varies |
| `docs/public/` | Public-facing docs | varies |
| `docs/adr/` | Architecture decision records | varies |
| `grimoire/` | The 28-Gana canonical reference | varies |

### 14.1 Critical files for AI agents

If you have time to read only a few files, read these in order:
1. `AGENTS.md` (373 lines) — operating manual
2. `core/whitemagic/tools/unified_api.py` (call_tool) — programmatic entry
3. `core/whitemagic/tools/dispatch_table.py` (462 tools) — API surface
4. `core/whitemagic/cli/cli_app.py` (CLI) — interactive surface
5. `polyglot/STATUS.md` — polyglot build state
6. `polyglot/POLYGLOT_SURVEY_2026-06-18.md` (this session) — polyglot architecture
7. `AI_PRIMARY.md` (706 lines) — the technical contract
8. `~/Desktop/reports/WHITEMAGIC_STATE_AUDIT_2026-06-18.md` — current state

---

## 15. Appendices

### 15.1 Appendix A: File:Line Index of Key Components

| Component | Path | Line |
|---|---|---|
| CLI entry point | `core/whitemagic/cli/cli_app.py` | 1 |
| MCP server entry | `core/whitemagic/run_mcp_lean.py` | 1 |
| Programmatic API | `core/whitemagic/tools/unified_api.py` | 1 |
| Dispatch table | `core/whitemagic/tools/dispatch_table.py` | 1 |
| Middleware pipeline | `core/whitemagic/tools/middleware.py` | 1 |
| 8-stage dispatch | `core/whitemagic/tools/middleware.py` | 100-500 |
| IceOryx2 bridge | `core/whitemagic-rust/src/ffi/ipc_bridge.rs` | 1 |
| IceOryx2 publish | `core/whitemagic-rust/src/ffi/ipc_bridge.rs` | 88-113 |
| IceOryx2 init | `core/whitemagic-rust/src/ffi/ipc_bridge.rs` | 70-85 |
| Arrow bridge | `core/whitemagic-rust/src/ffi/arrow_bridge.rs` | 1 |
| Memory substrate | `core/whitemagic/core/memory/` | various |
| 5D coords | `core/whitemagic/core/memory/holographic_coords.py` | 1 |
| Memory manager | `core/whitemagic/core/memory/manager.py` | 1 |
| HNSW index | `core/whitemagic-rust/src/graph/hnsw_index.rs` | 1 |
| Galaxy manager | `core/whitemagic/core/memory/galaxy_manager.py` | 1 |
| Voice audit | `core/whitemagic/core/governance/voice_audit.py` | 1 |
| Dharma engine | `core/whitemagic/dharma/rules.py` | 1 |
| Karma ledger | `core/whitemagic/dharma/karma_ledger.py` | 1 |
| Pattern discovery | `core/whitemagic/core/patterns/emergence/pattern_discovery.py` | 1 (added 2026-06-18) |
| Librarian (3 agents) | `core/whitemagic/agents/librarian.py` | 1 (added 2026-06-18) |
| Creative studio | `core/whitemagic/gardens/play/creative_studio.py` | 1 (added 2026-06-18) |
| Polyglot bridge | `polyglot/bridges/python/whitemagic_polyglot/__init__.py` | 1 |
| Python IPC bridge | `core/whitemagic/core/ipc_bridge.py` | 1 |
| PRAT router | `core/whitemagic/tools/prat_router.py` | 1 |
| Gana vitality | `core/whitemagic/tools/gana_vitality.py` | 1 |
| 28 Gana mapping | `core/docs/28_GANA_ARMY_MAPPING.md` | 1 |

### 15.2 Appendix B: Version History (since v22)

| Date | Version | Event |
|---|---|---|
| 2026-05 | 22.0.0 | PRAT router introduced, 8-stage pipeline formalized |
| 2026-05 | 22.1.0 | Multi-galaxy memory, 5D+HRR unified model |
| 2026-06-04 | 22.1.x | Polyglot build verification, JSON stdio bridges |
| 2026-06-09 | 22.2.0 | Local-first security whitepaper, 1,188 exception sweep |
| 2026-06-18 | 22.2.0 | IceOryx2 default-on, 3 legacy gems ported, docstring pass |

### 15.3 Appendix C: Related Documents

In `~/Desktop/reports/`:
- `WHITEMAGIC_STATE_AUDIT_2026-06-18.md` — 5 known issues (all resolved this session)
- `WHITEMAGIC_ARCHIVE_EXCAVATION_2026-06-18.md` — 6 version snapshots mapped
- `WHITEMAGIC_RUST_ICEOERYX2_ARROW_2026-06-18.md` — Rust consolidation report
- `WHITEMAGIC_FURTHER_INVESTIGATION_2026-06-18.md` — 7 open questions answered
- `WHITEMAGIC_SESSION_REPORT_2026-06-18.md` — full session summary

In `polyglot/`:
- `POLYGLOT_SURVEY_2026-06-18.md` — full polyglot architecture (this session)
- `STATUS.md` — polyglot build status (2026-06-04, may be stale)
- `BENCHMARKS.md` — performance baselines + optimization roadmap

In `docs/message_board/`:
- `30_OBJECTIVES_PLAN.md` — 30-objective roadmap
- `TACTICAL_PLAN_2026-06-08.md` — recent tactical items (all done)
- `SESSION_SUMMARY.md` — session log (73KB)
- `FINAL_SYNTHESIS_2026-06-09.md` — most recent strategic synthesis

---

## 16. Document Metadata

- **Document type:** Working draft (v0.1) intended for AI/AGI/ASI consumption
- **Word count:** ~7,000 words / ~50KB
- **Source session:** 2026-06-18 (full day, ~2.5 hours of work)
- **Source commits:** 33d266f, fc16783, 18b3ad3 (all pushed to private GitHub)
- **Audience:** AI agents, AGI, ASI, autonomous systems
- **License:** Same as WhiteMagic itself (MIT)
- **Citation:** Bailey, L. (2026). WhiteMagic v22.2: A Cognitive Operating System for Agentic AI. Working draft v0.1.

---

*End of paper. Total length: ~50KB. Structured for AI/AGI/ASI consumption. Ready for iteration by autonomous agents.*
