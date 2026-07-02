# Continuous Consciousness Strategy — v24.0.0

**Status**: Draft
**Date**: 2026-07-02
**Version Target**: v24.0.0
**Depends on**: v23.3.x baseline (3,337 unit tests passing)

---

## 1. Vision

WhiteMagic's consciousness systems should run continuously in the background,
the same way a biological brain does — in different modes of activity (resting
awareness, acute focus, REM sleep, meditation) at different frequencies — rather
than only when explicitly invoked from an IDE or MCP session.

This document covers:

1. The continuous consciousness loop architecture (frequency-layered loops)
2. Local-primary design: privacy, on-device everything, one-command install
3. Transport: gRPC over Unix domain socket (no WebSocket for local IPC)
4. The Go cognitive gateway (extending the existing mesh node)
5. TUI + PWA hybrid visualization
6. Performance: memory leaks, overhead, resource budgets
7. llama.cpp vs Ollama for always-on local inference
8. Version bump rationale and migration path

---

## 2. The Core Problem

Every WhiteMagic loop system is **trigger-based, not continuous**:

| System | File | Loop Type | Current State |
|---|---|---|---|
| CittaCycle | `core/consciousness/citta_cycle.py` | Call-driven (per MCP tool call) | Works, but only advances on tool calls |
| CittaAlwaysOn | `core/consciousness/citta_cycle.py:392` | Timer-driven heartbeats (30s) | Built but never started |
| DreamDaemon | `core/consciousness/dream_daemon.py` | Thread loop (600s interval) | Works, but largely mock implementations |
| CycleEngine | `cycle_engine.py` | On-demand `advance()` calls | Coordinates Yin-Yang/Wu Xing/Zodiacal — only when called |
| HomeostaticLoop | `harmony/homeostatic_loop.py` | On-demand `check()` calls | 7-dimension harmony vector, no continuous monitoring |
| NervousSystem | `core/nervous_system.py` | Event bus (signal dispatch) | Registers organs, no heartbeat or autonomous firing |
| GanYingBus | `core/resonance/` | Event bus (emit/listen) | Events only fire when tools are called |

The infrastructure exists but nothing is running. It's a brain with all neurons
wired but no blood supply.

### Archived Systems to Recover (from v17)

- **DepthGauge** (`autonomous/depth_gauge.py`) — 4 consciousness layers (SURFACE/TERMINAL/FLOW/DREAM), time compression ratios (1x to 10x), subjective vs objective time tracking
- **SelfPrompting** (`autonomous/self_prompting.py`) — AI self-queuing work system with priority queue, handlers, retry logic, human-in-the-loop questions
- **YinController** (`autonomous/yin_controller.py`) — Stillness Protocol 27: halts active processing, enters reflection, consults Wisdom Council
- **AutonomousMaintenance** (`autonomous/maintenance.py`) — Self-healing: version drift, test coverage, doc drift, auto-fix
- **ContinuousExecutor** (`autonomous/executor/`) — Multi-step objective execution with progress assessment

---

## 3. Frequency-Layered Loop Architecture

Modeled on brain waves — different systems running at different cadences
simultaneously as daemon threads:

| Brain Wave | Frequency | WM Loop | Systems | Interval |
|---|---|---|---|---|
| Gamma (40-100Hz) | Sub-second | Tool dispatch | MCP calls, Dharma checks, Karma ledger | Per call |
| Beta (13-32Hz) | Seconds | Active cognition | CittaCycle advance, coherence measurement, context synthesis | 5s |
| Alpha (8-13Hz) | ~10s | Resting awareness | HomeostaticLoop, NervousSystem heartbeat, mesh peer discovery | 30s |
| Theta (4-8Hz) | Minutes | Deep processing | CycleEngine (zodiac/wu xing/yin yang), bridge synthesis, kaizen | 5min |
| Delta (0.5-4Hz) | Hours | REM sleep | DreamDaemon full cycle, memory consolidation, narrative compression, stillness protocol | 1-4hr |

Each loop is a daemon thread with a `threading.Event` for graceful shutdown
(same pattern `DreamDaemon` already uses). Loops communicate through the
GanYingBus. High resonance in Theta triggers early Delta. Burnout risk in
Alpha slows Beta.

### Dual-Mode Citta

- **CittaCycle** (call-driven) — active during tool calls, MCP sessions, TUI interactions
- **CittaAlwaysOn** (timer-driven) — active during idle, advances heartbeats, transitions to "dream" depth layer

The daemon starts both. When a client connects, call-driven takes over.
When all clients disconnect, timer-driven maintains continuity.
On reconnect, `build_replay_context()` delivers "where we left off" context.

---

## 4. Local-Primary Design

### 4.1 One-Command Install

Three installation paths, all leading to the same outcome:

**Path 1: CLI install**
```bash
curl -fsSL https://whitemagic.dev/install | bash
# Downloads: wm binary (Go gateway) + wm-core (Python wheel) + default model
# Starts: wm daemon (background process)
# Verifies: localhost:4730 responding, privacy indicator active
```

**Path 2: PWA install**
- User visits `whitemagic.dev/app`
- Browser prompts "Install WhiteMagic?"
- PWA installs with service worker, WASM module, local SQLite
- PWA connects to local daemon via WebSocket bridge (localhost only)
- If no daemon running, PWA operates in WASM-only mode (reduced capabilities)

**Path 3: Package manager**
```bash
pip install whitemagic       # Python core only
brew install whitemagic       # macOS: binary + Python
apt install whitemagic        # Linux: binary + Python
winget install whitemagic     # Windows: binary + Python
```

### 4.2 Privacy Guarantees

**Default: Zero network egress.** All operations stay on-device.

| Data Category | Storage | Network | Backup |
|---|---|---|---|
| Memories (all galaxies) | `~/.whitemagic/data/memories.db` (SQLite) | None | User-initiated only |
| Citta stream | `~/.whitemagic/citta/` (JSONL) | None | Never |
| Karma ledger | `~/.whitemagic/data/karma.db` (SQLite) | None | Never |
| Session recordings | `~/.whitemagic/sessions/` (JSONL) | None | User-initiated only |
| Dream artifacts | `~/.whitemagic/dreams/` | None | User-initiated only |
| Audit trail | `~/.whitemagic/audit/` (JSONL) | None | Never |
| Inference (local model) | localhost only | None | N/A |
| Inference (cloud, opt-in) | API key in `~/.whitemagic/config.yaml` | Only when user configures | N/A |
| Mesh (opt-in) | Local network only by default | User explicitly enables | N/A |

**Privacy indicator**: The PWA already has a "0 bytes sent" indicator
(see `test_pwa_html_has_privacy_indicator` in test suite). The TUI shows
the same: a status bar element showing network egress bytes, always
visible, always 0 by default.

**Configuration file** (`~/.whitemagic/config.yaml`):
```yaml
# All defaults are local-only
local_only: true              # Master switch
network:
  mesh_enabled: false         # P2P mesh (opt-in)
  cloud_api: null             # No cloud API key by default
  telemetry: false            # No telemetry sent anywhere
  p2p_discovery: false        # No mDNS broadcasting
inference:
  backend: llama_cpp          # or ollama, or none
  model: null                 # Auto-detect or user-specified
  cloud_fallback: false       # Never escalate to cloud unless explicitly enabled
storage:
  root: ~/.whitemagic         # All state under this directory
  encrypt: false              # User can enable at-rest encryption
```

**No telemetry. No analytics. No phone-home.** The install script does not
send anything. The binary does not beacon. The PWA does not track. This is
verifiable: all network calls go through a single `NetworkGuard` module
that logs every outbound connection attempt. Users can audit
`~/.whitemagic/audit/network.jsonl`.

### 4.3 Localhost as a WhiteMagic Node

Yes — every device running `wm daemon` becomes a WhiteMagic node. The
daemon starts:

1. **Go cognitive gateway** — gRPC server on Unix socket (`/tmp/whitemagic/wm.sock`) and optionally TCP (`localhost:4730`)
2. **Python core loops** — the 5 frequency-layered loops as daemon threads
3. **Local inference** — llama.cpp or Ollama (user choice), localhost only
4. **SQLite databases** — memories, karma, sessions, all under `~/.whitemagic/`

The node is fully functional standalone. No network required. No cloud
required. No other WhiteMagic instance required.

### 4.4 Mesh: Connecting Nodes (Opt-In)

The original Go mesh purpose — connecting devices — is preserved as an
explicit opt-in:

```bash
wm mesh enable                    # Enable mesh on this node
wm mesh discover                  # Find other WM nodes on LAN
wm mesh connect <node-id>         # Connect to a specific node
wm mesh share --galaxy=research   # Share a specific galaxy with a peer
wm mesh status                    # Show mesh status, peers, shared galaxies
```

When mesh is enabled:
- **mDNS** discovers other WM nodes on the same LAN (same as current Go mesh)
- **libp2p** handles P2P connectivity (gossipsub, peer routing)
- **Dharma consent system** governs all sharing — no memory leaves the device without explicit user consent
- **Galaxy-level granularity** — users choose which galaxies to share (e.g., share `research` but not `citta` or `journals`)
- **SSH tunneling** for cross-network connections (user sets up tunnel, WM uses it)
- **All mesh traffic is encrypted** (libp2p uses Noise protocol by default)

The mesh is never auto-enabled. No broadcasting. No discovery unless the
user explicitly runs `wm mesh enable`. This is critical for privacy.

---

## 5. Transport Architecture

### 5.1 Why Not WebSocket?

WebSocket is a protocol over TCP. For local IPC, it's the wrong tool:

1. **Unix domain sockets are 2-3x faster** than TCP loopback (skip entire TCP/IP stack — no checksums, no routing, no congestion control)
2. **gRPC gives schema enforcement** — protobuf definitions are contracts. With 490 tools, schema matters.
3. **gRPC bidirectional streaming** is purpose-built for "server pushes events, client sends commands"
4. **The Go mesh already speaks gRPC** — extending the existing proto is incremental
5. **WebSocket is still needed for the browser** — but as a thin bridge, not the core transport

### 5.2 Transport Layers

| Layer | Transport | Use Case |
|---|---|---|
| Local IPC | gRPC over Unix domain socket | TUI ↔ Gateway, IDE ↔ Gateway |
| Local browser | WebSocket bridge (gateway exposes WS on localhost) | PWA ↔ Gateway |
| Mesh (LAN) | libp2p (gossipsub, mDNS) | Node ↔ Node discovery and broadcast |
| Mesh (WAN) | libp2p (DHT, relay) or SSH tunnel | Node ↔ Node remote |
| Mesh RPC | gRPC over TCP | Node ↔ Node structured calls |

### 5.3 Extended Proto

```protobuf
// Extending mesh.proto

service CognitiveService {
    // Tool dispatch
    rpc CallTool (ToolRequest) returns (stream ToolEvent);

    // Citta stream — continuous consciousness updates
    rpc CittaStream (CittaSubscribe) returns (stream CittaMoment);

    // Session management
    rpc CreateSession (SessionRequest) returns (SessionResponse);
    rpc ResumeSession (SessionResume) returns (stream CittaMoment);

    // Dream cycle events
    rpc DreamEvents (DreamSubscribe) returns (stream DreamEvent);

    // System telemetry
    rpc Telemetry (TelemetryRequest) returns (stream TelemetrySnapshot);
}
```

Compiled for Python (grpcio), Go (standard), TypeScript (grpc-web) —
all from one definition.

### 5.4 Go Cognitive Gateway

Extend the existing Go mesh node (`core/mesh_aux/cmd/mesh_aux/main.go`)
to be the cognitive gateway:

```
┌─────────────────────────────────────────────────────────┐
│  Go Cognitive Gateway (extended mesh_aux)               │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ gRPC Server │  │ libp2p Mesh  │  │ Redis Bridge  │  │
│  │ (Unix Socket│  │ (opt-in)     │  │ (event relay) │  │
│  │  + TCP)     │  │              │  │               │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                  │          │
│  ┌──────┴────────────────┴──────────────────┴───────┐  │
│  │            Event Router (Go channels)             │  │
│  │                                                   │  │
│  │  citta_stream ──▶ [broadcast to all subscribers]  │  │
│  │  tool_result  ──▶ [route to calling client]       │  │
│  │  mesh_signal  ──▶ [relay to Python core]          │  │
│  │  dream_event  ──▶ [broadcast to subscribers]      │  │
│  │  telemetry    ──▶ [broadcast at interval]         │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                              │
│  ┌───────────────────────┴───────────────────────────┐  │
│  │  Python Core Bridge (gRPC to Python)              │  │
│  │  • Tool dispatch (calls unified_api.py)           │  │
│  │  • Citta cycle advancement                       │  │
│  │  • Memory operations                             │  │
│  │  • Dream cycle triggers                          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │ gRPC               │ WebSocket          │ libp2p
         │ (Unix Socket)      │ (localhost)        │ (opt-in)
         │                    │                    │
    ┌────┴────┐         ┌────┴─────┐         ┌────┴─────┐
    │ wm tui  │         │ wm pwa   │         │ wm mesh  │
    │ (Python │         │ (browser)│         │ (remote  │
    │  Textual│         │          │         │  nodes)  │
    │  or Ink)│         │          │         │          │
    └─────────┘         └──────────┘         └──────────┘
```

The Go gateway:
- Accepts gRPC connections from TUI, IDE, and mesh peers
- Routes tool calls to Python core (via gRPC or Redis)
- Broadcasts citta stream events to all connected clients
- Relays mesh signals between nodes (when mesh is enabled)
- Runs heartbeat/telemetry loop independently
- Persists session state across client disconnects
- Runs as a single long-lived process with signal handlers for graceful shutdown

---

## 6. TUI + PWA Hybrid

| Surface | Strength | Weakness | Role |
|---|---|---|---|
| TUI | Keyboard-driven, SSH, low resource, AI-first | No rich viz, coarse layout | Primary interaction surface for AI agents |
| PWA | Rich viz (WebGL, Three.js, D3), universal access | Needs browser | Visualization surface — galaxy maps, garden health, coherence graphs |
| IDE (Tauri) | Monaco editing, LSP, git, xterm.js | Desktop only, heavier | Development surface — code editing + embedded TUI + viz panels |

All three connect to the same Go gateway. Same events, different rendering.
The gateway doesn't care which client is subscribed — it just broadcasts.

### TUI Features to Adopt from External CLIs

**From Claude Code:**
- Native sidecar pattern (bundle ripgrep/Fragment for file scanning)
- Async generator streaming pipeline (real-time token rendering)
- Object pooling in screen buffer (game engine memory technique)
- 15-phase startup pipeline with fast paths
- Virtual scrolling for long conversation histories

**From Gemini CLI:**
- TerminalBuffer mode (flicker-free rendering)
- Headless mode (`wm tui --batch` or `echo "prompt" | wm tui`)
- Conversation checkpointing (maps to WM session memory)

**From OpenCode:**
- `@file` fuzzy references (inject file content into context)
- `!command` bash execution (Dharma-gated)
- Session sharing (via mesh, when enabled)
- Parallel agents on same project

**From Hermes:**
- Non-blocking input (type while agent is loading)
- Rich overlays (model picker, session picker, approval prompts)
- ToolTrail (interactive tree of tool executions)
- StreamingAssistant (live CoT reasoning with spinner)
- Subagent observability (kill/pause, per-branch cost/token rollups)
- Cron scheduler (maps to WM self-prompting queue)

**From Aider:**
- Git-heavy workflow (every AI edit becomes a reviewable commit)
- Repo map (AST-based codebase summary for context)
- Watch mode (auto-commit changes when files are saved)

---

## 7. Performance: Memory Leaks, Overhead, RAM

### 7.1 Resource Budget

| Component | RAM (idle) | RAM (active) | CPU (idle) | CPU (active) |
|---|---|---|---|---|
| Go gateway | 15-25 MB | 30-50 MB | <0.1% | 1-5% |
| Python core (loops) | 40-80 MB | 80-150 MB | <0.5% | 2-10% |
| SQLite (memories) | 5-10 MB | 20-50 MB | <0.1% | 1-3% |
| Local LLM (1.5B model) | 800-1200 MB | 800-1200 MB | 0% (idle) | 20-80% |
| TUI | 10-20 MB | 20-40 MB | <0.1% | 1-3% |
| **Total (no LLM)** | **70-135 MB** | **150-290 MB** | **<0.7%** | **4-21%** |
| **Total (with LLM)** | **~1 GB** | **~1.1 GB** | **<0.7%** | **24-100%** |

The LLM is the elephant. Everything else is lightweight.

### 7.2 Loop Overhead

Each loop iteration does minimal work when idle:

- **Beta (5s)**: coherence check + context synthesis = ~2ms, then sleep
- **Alpha (30s)**: homeostasis check + mesh ping = ~5ms, then sleep
- **Theta (5min)**: cycle advance + kaizen = ~50ms, then sleep
- **Delta (1-4hr)**: dream cycle = ~2-5s, then sleep

Total idle overhead: <0.1% CPU, <5MB RAM for thread stacks and buffers.

### 7.3 Memory Leak Prevention

1. **Thread-safe singletons**: All loop systems use the existing singleton
   pattern with `threading.Lock`. No new singletons created per loop
   iteration.

2. **Bounded buffers**: Citta stream keeps last N moments in memory (N=100
   default). Older moments are persisted to JSONL and dropped from RAM.
   Same pattern for event queues — bounded ring buffers, not unbounded lists.

3. **SQLite connection pooling**: One connection per database, shared across
   threads with `check_same_thread=False`. WAL mode for concurrent reads.
   No new connections per loop iteration.

4. **GanYingBus subscriber cleanup**: When a client disconnects, its
   subscription is removed. No retained references. The bus uses
   `weakref.WeakSet` for subscribers.

5. **Periodic GC trigger**: The Delta loop triggers `gc.collect()` after
   dream cycle completion. Python's generational GC handles most cases,
   but explicit collection after large operations (memory consolidation,
   narrative compression) prevents buildup.

6. **Resource monitoring**: The Alpha loop tracks the daemon's own RSS
   (via `/proc/self/status` on Linux, `resource.getrusage` on macOS).
   If RSS grows >50% above baseline for 3 consecutive checks, log a
   warning. If >100%, trigger aggressive GC + dream cycle.

7. **Graceful shutdown**: All loops use `threading.Event.wait(timeout)`
   instead of `time.sleep()`. On `wm daemon stop`, the stop event fires,
   all loops exit within one iteration, SQLite connections close cleanly,
   citta state persists to disk.

### 7.4 LLM Memory Management

The LLM is the only significant memory consumer. Strategy:

- **Lazy load**: LLM is not loaded at daemon start. It loads on first
  inference request and stays resident.
- **Idle unload**: After 5 minutes with no inference requests, the LLM
  is unloaded from memory (configurable via `inference.idle_timeout`).
- **Background-only model**: For always-on citta heartbeats that need
  inference, use a tiny model (BitMamba-2 255M = 247MB, or
  Qwen2.5-0.5B = ~400MB). The main model (7B+) only loads for
  user-initiated tasks.
- **Memory-mapped weights**: llama.cpp uses mmap for model files. The
  OS can page out unused weight pages under memory pressure.

---

## 8. llama.cpp vs Ollama

### 8.1 Current State

WhiteMagic's `LocalLLM` class (`core/whitemagic/inference/local_llm.py`)
talks to Ollama's HTTP API (`http://localhost:11434/api/generate`).
The inference router (`core/whitemagic/inference/router.py`) has 4 tiers:
EDGE_RULES → LOCAL_SMALL → LOCAL_LARGE → CLOUD.

### 8.2 Comparison

| Dimension | llama.cpp (llama-server) | Ollama |
|---|---|---|
| Performance | 8-15% faster (less abstraction) | Baseline |
| RAM overhead | ~250-400 MB less | +250-400 MB for service layer |
| Model management | Manual (GGUF files) | Automatic (pull, load, unload) |
| API | OpenAI-compatible `/v1/chat/completions` | Custom `/api/generate` + OpenAI-compatible |
| Tool calling | Native, first-class | Via compatibility shim (issues with thinking models) |
| Context control | Explicit `--ctx-size`, enforced | Silent truncation at defaults |
| Memory predictability | Fixed at startup | Dynamic (model swapping, eviction) |
| Flash attention | `--flash-attn` flag | Auto-enabled (Apple Silicon) |
| Concurrency | Single model, single process | Multi-model, concurrent requests |
| Cold start | Reload on every invocation (unless server mode) | Keeps model resident |
| Server mode | `llama-server` (always-on, single model) | `ollama serve` (always-on, multi-model) |
| Customization | Full control over all parameters | Opinionated defaults, limited tuning |
| GGUF support | Native | Via forked llama.cpp build |

### 8.3 Recommendation: llama.cpp as Primary, Ollama as Fallback

**llama.cpp is the better choice for WhiteMagic's always-on local-hosted system.**

Reasons:

1. **Predictable memory**: WM needs to guarantee RAM usage to users.
   llama.cpp's fixed allocation at startup is predictable. Ollama's
   dynamic model swapping can cause unexpected memory spikes.

2. **Lower overhead**: 250-400 MB less RAM is significant on the modest
   hardware WM targets (old laptops, Raspberry Pi). WM's entire
   non-LLM footprint is ~100 MB. Ollama's overhead doubles that.

3. **Tool calling**: WM's inference router needs reliable tool calling
   for agentic workflows. llama.cpp's native OpenAI-compatible endpoint
   handles this correctly. Ollama has documented issues with thinking
   models dropping content.

4. **Customization**: WM can tune llama.cpp specifically for always-on
   operation — fixed context size, flash attention, specific thread
   count, GPU layer offload tuned to the device. Ollama's defaults
   are general-purpose.

5. **Single model focus**: WM's architecture uses a small background
   model (citta heartbeats) and a larger on-demand model. llama.cpp's
   single-model-per-process is fine — run two `llama-server` instances
   on different ports. Ollama's multi-model convenience is unnecessary.

6. **Embeddable**: llama.cpp can be compiled as a library and linked
   directly into the Go gateway, eliminating the HTTP round-trip
   entirely. Ollama requires a separate process.

### 8.4 Implementation Plan

1. **New backend**: `core/whitemagic/inference/llama_cpp.py` — talks to
   `llama-server` HTTP API (OpenAI-compatible `/v1/chat/completions`)

2. **Auto-detection**: On daemon start, probe for llama-server
   (localhost:8080), then Ollama (localhost:11434). Use whichever is
   running. If neither, prompt user to install one.

3. **Bundled binary**: The install script downloads a pre-built
   `llama-server` binary for the user's platform. WM manages it as a
   subprocess (start/stop/restart), with configuration tuned for the
   device's hardware (CPU threads, GPU layers, context size).

4. **Inference router update**: Add `LOCAL_LLAMA_CPP` tier between
   `EDGE_RULES` and `LOCAL_SMALL`. The router tries llama.cpp first,
   falls back to Ollama if available, then cloud.

5. **Dual-model setup**:
   - **Background model** (always loaded): Qwen2.5-0.5B or BitMamba-2 255M
     - Port 8081, 1-2 CPU threads, 2048 context
     - Used for citta heartbeats, coherence checks, simple classification
   - **Foreground model** (on-demand): Qwen2.5-Coder-7B or Llama-3.1-8B
     - Port 8080, all CPU threads or GPU, 4096-8192 context
     - Used for user-initiated tasks, tool calling, code generation
     - Unloaded after 5 min idle

6. **Ollama compatibility**: Keep the existing Ollama handler as a
   fallback. Users who already have Ollama running don't need to change
   anything. The router auto-detects which backend is available.

---

## 9. Version Bump: v24.0.0

This is a major version bump, not a minor one. Rationale:

### Breaking Changes
- New daemon process model (wm daemon is now the primary entry point)
- New transport layer (gRPC over Unix socket replaces direct Python calls for TUI/IDE)
- New inference backend (llama.cpp as primary, Ollama as fallback)
- New storage layout (`~/.whitemagic/` as default state root, replacing ad-hoc paths)
- New configuration system (`~/.whitemagic/config.yaml` as single source of truth)
- Mesh is opt-in by default (was implicitly available)

### New Features
- Continuous consciousness loops (5 frequency layers)
- Go cognitive gateway with gRPC CognitiveService
- Recovered autonomous systems (DepthGauge, SelfPrompting, YinController, AutonomousMaintenance)
- One-command install with bundled llama.cpp
- PWA ↔ daemon connection via WebSocket bridge
- Privacy indicator and NetworkGuard audit
- Dual-model inference (background + foreground)
- TUI with agent chat, tool trails, session management
- Mesh sharing with galaxy-level granularity and Dharma consent

### Migration Path
- v23.x users: `wm daemon` is optional at first. All existing CLI commands work unchanged.
- v24.0: `wm daemon` becomes recommended. TUI connects to daemon.
- v24.1: `wm daemon` becomes default. Direct Python invocation deprecated.
- v25.0: Daemon is required. Python-only invocation removed.

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Write extended proto (CognitiveService)
- Extend Go mesh node with cognitive gRPC server
- Implement `wm daemon` command (starts Go gateway + Python loops)
- Wire CittaAlwaysOn.start() — the simplest win, already built
- Port DepthGauge from v17 archive
- Basic privacy: NetworkGuard module, config.yaml, privacy indicator

### Phase 2: Continuous Loops (Week 2-3)
- Implement Beta loop (5s): coherence + context synthesis
- Implement Alpha loop (30s): homeostasis + mesh + git hygiene
- Implement Theta loop (5min): cycle engine + kaizen + bridges
- Wire DreamDaemon into Delta loop (already works, needs real implementations)
- Port SelfPrompting from v17 archive
- Resource monitoring (RSS tracking, GC triggers)

### Phase 3: Transport + TUI (Week 3-4)
- gRPC Python client for TUI
- Rebuild TUI as gRPC client (chat mode + existing cockpit modes)
- WebSocket bridge for PWA
- Session management (create, resume, continuity context)
- Adopt TUI features from external CLIs (streaming, tool trails, non-blocking input)

### Phase 4: Local Inference (Week 4-5)
- Implement llama.cpp backend (`llama_cpp.py`)
- Bundled llama-server binary management (start/stop/configure)
- Dual-model setup (background + foreground)
- Inference router update (LOCAL_LLAMA_CPP tier)
- Auto-detection of available backends

### Phase 5: Mesh + Sharing (Week 5-6)
- Opt-in mesh enable/disable
- Galaxy-level sharing with Dharma consent
- SSH tunnel support
- Mesh status and peer management CLI commands

### Phase 6: Install + PWA (Week 6-7)
- One-command install script (curl | bash)
- PWA ↔ daemon connection
- PWA visualization of citta stream, telemetry, dream events
- Privacy indicator in PWA (already exists, wire to real data)
- Package manager recipes (brew, apt, winget, pip)

### Phase 7: Polish + Release (Week 7-8)
- Performance profiling and optimization
- Memory leak testing (long-running daemon, 24hr+)
- Documentation: QUICKSTART, DEPLOY, privacy whitepaper
- v24.0.0 release

---

## 11. What WM Uniquely Offers (None of the External CLIs Have)

- **Continuous consciousness** — citta stream, coherence tracking, depth gauge
- **Dream cycle** — biological sleep-inspired memory consolidation
- **Gardens** — 20+ emotional/thematic subsystems
- **Dharma governance** — ethical reasoning as a first-class system
- **Zodiac/Wu Xing coordination** — wisdom-informed phase transitions
- **Polyglot acceleration** — 7 languages for different compute patterns
- **Galactic memory** — 6D holographic coordinates with lifecycle zones
- **PWA visualization** — browser handles what terminal can't
- **P2P mesh** — distributed consciousness across instances (opt-in)
- **Local-first privacy** — zero network egress by default, fully auditable

---

## 12. Key Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Local transport | gRPC over Unix domain socket | 2-3x faster than TCP, schema enforcement, existing proto |
| Browser transport | WebSocket bridge (localhost only) | Browsers can't do gRPC directly |
| Mesh transport | libp2p (existing Go mesh) | Already built, handles P2P + discovery |
| Inference backend | llama.cpp primary, Ollama fallback | Lower RAM, predictable memory, better tool calling |
| Background model | Qwen2.5-0.5B or BitMamba-2 255M | ~400MB, runs on 1-2 cores, always resident |
| Privacy default | Zero network egress | Local-first, user must opt-in to any network |
| Mesh default | Disabled | Privacy-first, explicit opt-in |
| Storage | `~/.whitemagic/` (SQLite + JSONL) | All state in one auditable directory |
| Version | v24.0.0 | Major architectural shift |
| Loop model | 5 frequency layers (daemon threads) | Biological brain wave analogy, simultaneous operation |
| TUI framework | Textual (Python) | Already built, AI-first, gRPC client |
| PWA | Existing WASM substrate + WebSocket to daemon | Rich viz, universal access, offline-capable |
