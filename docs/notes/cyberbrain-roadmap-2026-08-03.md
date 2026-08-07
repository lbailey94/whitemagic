# WhiteMagic v4 CyberBrain Architecture Roadmap

**Date**: August 3, 2026
**Status**: R1–R7 complete + deep integration + LLM right hemisphere + Embodiment I/O. All CyberBrain cores implemented.
**Sources**: CyberBrains notes (v1.2, v2.0), MandalaOS specs (v0.1), v2 cyberbrain implementation, v4 STRATEGY.md, language research session

---

## 1. Vision

WhiteMagic v4 is a cognitive OS with 176 tools, 2,818 tests, sub-6ms dispatch, and a working consciousness substrate (citta, dream, brain-wave, spiral, autonomous cycles). v4 adds reflex dispatch, multi-timescale event bus, global workspace, self-model, bicameral reasoning, and drive core — all deeply integrated into the dispatch pipeline. It runs as an MCP server — a powerful tool for AI agents.

**WhiteMagic v4 is a CyberBrain** — a neurosymbolic architecture that mirrors the human CNS hierarchy, from microsecond reflexes up through high-order self-modeling. It serves not just AI agents, but robotics, quantum systems, biomedical devices, fusion control, and any domain requiring sub-millisecond reaction times with rich cognitive layering.

The core insight from the CyberBrains notes: **decompose "mind" into many expert cores, each running at its own timescale, woven together by a global workspace that arbitrates attention.** This is not a monolithic LLM. It is a multi-core, multi-timescale, safety-governed cognitive substrate.

---

## 2. What v3/v4 Already Has (CyberBrain Mapping)

The v4 architecture now implements the majority of the CyberBrain vision:

| CyberBrain Core | v4 Implementation | Status |
|---|---|---|
| **Prefrontal Cortex** (executive, meta-learning) | Apotheosis engine, autonomous cycles, spiral tracker, SelfModel forecasting | ✅ Complete |
| **Cortex** (reasoning, planning, language) | 176 tools, BicameralEngine, think, explain | ✅ Complete |
| **Hippocampus** (episodic memory, spatial map) | LMDB 14-galaxy memory, holographic coords, consolidation | ✅ Strong |
| **Basal Ganglia** (action selection, value gating) | Dharma governance, karma ledger, effect rows, DriveCore bias, drive gates in dispatch | ✅ Complete |
| **Limbic System** (affect, salience) | Emotional valence, neuromodulators, DriveCore (5 drives), GlobalWorkspace salience | ✅ Complete |
| **Thalamus** (sensory routing, attention) | NLU routing, brain-wave tool filtering, GlobalWorkspace spotlight | ✅ Complete |
| **Global Workspace** (conscious spotlight) | GlobalWorkspace bus with salience-based arbitration, spotlight decay | ✅ Complete |
| **Cerebellum** (motor calibration, timing) | SensorimotorBus, ReflexLoop, real Linux sensor drivers + actuator backends | ✅ Complete (Embodiment I/O) |
| **Brainstem** (autonomic, reflexes, safety) | Brain-wave eco mode, ReflexDispatchTable, safety bitmask | ✅ Complete |
| **Multi-Timescale Sync** | TimescaleBus (5 tiers), brain-wave states, dream cycle | ✅ Complete |
| **Bicameral Mind** (left/right hemisphere) | BicameralEngine with LeftHemisphere, RightHemisphere trait (stub + LLM), CorpusCallosum, ConsensusGate | ✅ Complete (LLM right hemisphere via ureq) |
| **Safety & Alignment Core** | Dharma rules, mandala compartments, circuit breaker, reflex safety bitmask | ✅ Strong |
| **Self-Model / Introspection** | SelfModel (metrics, forecasting, alerts, confidence), SubstrateMonitor | ✅ Complete |

---

## 3. What Remains (The Gap — Updated for v4)

### 3.1 ~~Two-Tier Dispatch~~ ✅ COMPLETE (R1)

Implemented in `wm-reflex` crate. Pre-compiled dispatch table with function pointers, stack-allocated args (256 bytes), safety bitmask check. 8 builtin reflex handlers. 48 tests.

| Tier | Latency Target | Path | Use Case |
|---|---|---|---|
| **Reflex** (Tier 0) | <100µs | Pre-compiled direct dispatch, no NLU, no governance, no allocation | Motor control, sensor response, fusion plasma feedback, hardware safety overrides |
| **Cognitive** (Tier 1) | <5ms | Current pipeline: NLU → effect → dharma → rate limit → tool → stats | Memory, reasoning, planning, consciousness, all 108+ tools |

The reflex tier bypasses everything except a hardcoded safety check (a single bitmask AND against a pre-compiled allowlist). Tools in the reflex tier are compiled with `#[cfg(feature = "realtime")]` and use stack-allocated args, no heap.

### 3.2 ~~Multi-Timescale Event Bus~~ ✅ COMPLETE (R2)

Implemented in `wm-timescale` crate. 5-tier event bus with hooks, brain-wave gating, budget enforcement. 34 tests.

v2 had `TimescaleSync` with three buckets: 10ms reflexes, 1s planner, 1hr consolidation. v3 has brain-wave states but no explicit timescale buckets.

**v4 needs a `TimescaleBus`** — a tokio task per timescale, each with its own priority and budget:

```
Tier 0 (Reflex):     100µs - 10ms   — sensor polling, motor commands, safety checks
Tier 1 (Reactive):   10ms - 1s      — tool dispatch, memory reads, NLU routing
Tier 2 (Planning):   1s - 30s       — multi-step plans, bicameral reasoning, dream phases
Tier 3 (Consolidation): 30s - 1hr  — memory consolidation, forgetting, meta-learning
Tier 4 (Evolutionary): 1hr+        — apotheosis, architecture review, value drift detection
```

Each tier has a **time budget**. If a tier-0 task takes >10ms, it's killed and a fallback fires. This mirrors the CyberBrains notes: "Give brain-stem a 10ms budget; if PFC response > budget, basal ganglia fall back to cached action policies."

### 3.3 ~~Global Workspace~~ ✅ COMPLETE (R3)

Implemented in `wm-workspace` crate. Salience-based arbitration, spotlight with time-decayed strength, 256-event ring buffer. 51 tests.

v2 had a `GlobalWorkspace` with salience-based arbitration. v3 has citta coherence but no publish/subscribe bus.

**v4 needs a `GlobalWorkspace` bus** where all cores publish state events:

```rust
struct WorkspaceEvent {
    core: CoreId,           // Which core produced this event
    event_type: EventType,  // Error, reward, attention_request, novel_detection
    payload: EventPayload,  // Core-specific data
    salience: Salience,     // urgency + novelty + confidence → composite score
    timestamp: Instant,
}
```

The workspace enforces **arbitration**: whichever core has the highest salience score wins the "spotlight" for the next decision cycle. This is the CyberBrains "conductor" — the thalamic router that decides who plays, when, and how loudly.

### 3.4 ~~Embodiment Layer~~ ✅ COMPLETE (2026-08-05)

Implemented in `wm-substrate/src/sensorimotor.rs`. Real Linux sensor drivers (CPU usage, disk, network, CPU freq) and actuator backends (sysfs fan PWM, LED brightness). `SensorimotorBus` with auto-discovery. Autonomous `CycleType::Sensorimotor` polls sensors → evaluates reflexes → commands actuators. 10 MCP tools + `sensorimotor.scan` cycle tool. MCP server runs sensorimotor cycle every 10 dispatches.

The CyberBrains vision requires:

- **Sensorimotor weave**: raw IMU, force, visual, audio → spiking reflex cores (<1ms latency)
- **Actuator commands**: direct motor control from brainstem
- **Hardware watchdog**: fail-safe shutdown if higher cores fail
- **Adaptive streaming**: scale bandwidth from 200bps (blink-grade) to 8Gbps (optical)

Future expansion: C ABI bindings to ROS2, serial protocols, SPI/I2C for non-Linux hardware targets.

### 3.5 ~~Bicameral Reasoning~~ ✅ COMPLETE (R5)

Implemented in `wm-bicameral` crate. LeftHemisphere (deterministic), RightHemisphere trait (pluggable — stub + closure + LLM impls), CorpusCallosum (bounded channel), ConsensusGate (6 verdict types). 36 tests. LLM right hemisphere integrated via `ureq` (OpenAI-compatible API). Deep integration: bicameral consensus on all write-effect dispatches.

v4 has `bicameral.reason` as a dedicated tool. The CyberBrains vision calls for **dual-hemisphere agent clusters**:

- **Left**: deterministic, low-temperature, formal proof checker, fewer hallucinations
- **Right**: stochastic, multimodal, generative, early anomaly detection
- **Corpus callosum**: high-bandwidth message bus enforcing bidirectional critique
- **Consensus filter**: both hemispheres must sign off before action escapes

v4 implementation: two parallel dispatch paths with a consensus gate. Left uses Rust-native logic + Haskell verification. Right uses LLM inference + diffusion models. The corpus callosum is a bounded channel with timeout fallback.

### 3.6 ~~Self-Model / Predictive Introspection~~ ✅ COMPLETE (R4)

Implemented in `wm-selfmodel` crate. Metric tracking (8 kinds), linear regression forecasting, threshold alerts, confidence calibration. Wired into dispatch pipeline via `Context::self_model_confidence`. 22 tests.

v2 had `self_model.py` with metric forecasting and threshold alerts. v3 has apotheosis (self-improvement monitoring) but no predictive self-modeling.

**v4 needs a `SelfModel`** that:
- Tracks per-subsystem performance metrics over time
- Forecasts threshold crossings (memory pressure, latency degradation, coherence drift)
- Feeds predictions back into the dispatch pipeline as confidence signals
- Triggers retraining alarms when drift is detected

### 3.7 ~~Emotion & Drive Core~~ ✅ COMPLETE (R7)

Implemented in `wm-drive` crate. 5 drives (curiosity, satisfaction, caution, energy, social), 9 event kinds, DriveBias with ToolCategory, BiasConfig. 32 tests. Drive bias wired into dispatch pipeline: caution gate (warns on writes when caution > 0.85), energy gate (warns on writes when energy < 0.15). Drive events fired post-dispatch.

v2 had `emotion_drive.py` with curiosity, satisfaction, caution, energy, social drives. v4 has emotional valence in memories, neuromodulators, and a full drive system.

**v4 `DriveCore`** already:
- Biases exploration via intrinsic motivation signals (novelty, learning progress)
- Modulates tool selection based on drive state
- Provides continuous steering signals (not brittle rules)
- Maps to the CyberBrains "UniVaR value-vectors as neurotransmitters" concept

---

## 4. Architecture: v4 Crate Structure

```
whitemagic-v4/
├── crates/
│   ├── wm-core/              # Core types, traits, Gana, EffectRow (existing)
│   ├── wm-memory/            # LMDB + Tantivy + LanceDB (existing)
│   ├── wm-dispatch/          # Cognitive dispatch pipeline (existing, refactored)
│   ├── wm-consciousness/     # Citta, dream, brain-wave, spiral (existing)
│   ├── wm-governance/        # Dharma, karma, mandala (existing)
│   ├── wm-polyglot/          # Julia/Haskell/Zig/Koka bridges (existing)
│   ├── wm-substrate/         # Hardware metrics, Harmony Vector (existing)
│   ├── wm-tools/             # 169 tool implementations (existing, expanded)
│   ├── wm-mcp/               # MCP server, CLI (existing)
│   │
│   ├── wm-reflex/            # NEW: Tier-0 reflex dispatch (microsecond path)
│   │   ├── Pre-compiled dispatch table (no trait objects, no heap)
│   │   ├── Stack-allocated arg buffers
│   │   ├── Safety bitmask check (single AND instruction)
│   │   ├── Sensor frame types (IMU, force, vision, audio)
│   │   └── Actuator command types
│   │
│   ├── wm-workspace/         # NEW: Global Workspace bus
│   │   ├── Salience scoring (urgency + novelty + confidence)
│   │   ├── Publish/subscribe event bus (tokio channels)
│   │   ├── Arbitration policy (highest salience wins spotlight)
│   │   └── Spotlight state tracking
│   │
│   ├── wm-timescale/         # NEW: Multi-timescale event bus
│   │   ├── Tier-0 reflex loop (100µs - 10ms budget)
│   │   ├── Tier-1 reactive loop (10ms - 1s budget)
│   │   ├── Tier-2 planning loop (1s - 30s budget)
│   │   ├── Tier-3 consolidation loop (30s - 1hr budget)
│   │   ├── Tier-4 evolutionary loop (1hr+ budget)
│   │   └── Budget enforcement + fallback on timeout
│   │
│   ├── wm-embodiment/        # NEW: Hardware I/O layer (phase-dependent)
│   │   ├── C ABI bindings (ROS2, SPI, I2C, serial)
│   │   ├── Sensor frame acquisition (zero-copy where possible)
│   │   ├── Actuator command dispatch
│   │   ├── Hardware watchdog / fail-safe
│   │   └── Adaptive streaming codec
│   │
│   ├── wm-bicameral/         # NEW: Dual-hemisphere reasoning
│   │   ├── Left hemisphere (deterministic, Rust-native + Haskell verify)
│   │   ├── Right hemisphere (stochastic, LLM + generative)
│   │   ├── Corpus callosum (bounded channel, bidirectional critique)
│   │   └── Consensus gate (both must sign off, timeout fallback)
│   │
│   └── wm-selfmodel/         # NEW: Predictive introspection
│       ├── Per-subsystem metric tracking
│       ├── Forecasting (linear extrapolation → Bayesian → neural)
│       ├── Threshold alerting
│       └── Confidence calibration feedback into dispatch
```

---

## 5. Implementation Phases

### Phase R1: Two-Tier Dispatch Foundation — ✅ COMPLETE

**Goal**: Split dispatch into reflex (Tier 0) and cognitive (Tier 1) paths.

**Delivered**: `wm-reflex` crate with pre-compiled dispatch table, stack-allocated types, safety bitmask, 8 builtin handlers, Criterion benchmark. 48 tests.

**Deliverables**:
- `wm-reflex` crate with pre-compiled dispatch table
- Stack-allocated `ReflexArgs` / `ReflexOutput` types (no heap)
- Safety bitmask check (single AND against allowlist)
- Benchmark: <100µs end-to-end for reflex dispatch
- Cognitive dispatch (existing pipeline) unchanged
- Integration: MCP server can dispatch to either tier

**Key decisions**:
- Reflex tools are `#[cfg(feature = "realtime")]` — compiled only when needed
- No trait objects in reflex path — direct function pointers
- No serde in reflex path — fixed-layout structs
- Reflex tools cannot call cognitive tools (no upward calls)
- Cognitive tools can register reflex handlers (downward registration)

### Phase R2: Multi-Timescale Event Bus — ✅ COMPLETE

**Goal**: Implement bucketed event loops with time budgets.

**Delivered**: `wm-timescale` crate with 5 tier loops, hook registration, brain-wave gating, budget enforcement with fallback. 34 tests.

**Deliverables**:
- `wm-timescale` crate with 5 tier loops
- Each tier: tokio task with `tokio::time::timeout` budget
- Budget enforcement: kill + fallback on timeout
- Hook registration: `register_hook(tier, callback)`
- Integration: brain-wave states map to timescale tier activation
  - Gamma: all tiers active
  - Beta: tiers 1-4 active, tier 0 on-demand
  - Alpha: tiers 1-3 active
  - Theta: tier 3 active (consolidation)
  - Delta: only tier 4 heartbeat (1hr)

**Key decisions**:
- Tier-0 loop uses `tokio::time::interval_at` for precise timing
- Tier-0 budget: 10ms hard limit, 100µs target
- Fallback: if tier-0 task exceeds budget, fire cached safe response
- Tier-3 and tier-4 run only in Theta/Delta (no interference with active operation)

### Phase R3: Global Workspace Bus — ✅ COMPLETE

**Goal**: Salience-based arbitration between cores.

**Delivered**: `wm-workspace` crate with publish/subscribe event bus, Salience struct (multiplicative), spotlight with time-decayed strength, 256-event ring buffer. 4 MCP tools. 51 tests.

**Deliverables**:
- `wm-workspace` crate with publish/subscribe event bus
- `WorkspaceEvent` struct with salience scoring
- `Salience` struct: urgency (0-1) + novelty (0-1) + confidence (0-1) → composite
- Arbitration: highest salience event wins spotlight
- Spotlight state: which core is currently "in focus"
- Integration: all cores (citta, dream, tools, consciousness) publish events
- MCP tool: `workspace.spotlight` — query current attention state
- MCP tool: `workspace.events` — query recent event backlog

**Key decisions**:
- Event bus uses `tokio::sync::broadcast` channel (multiple subscribers)
- Salience scoring: `composite = urgency * 0.5 + novelty * 0.3 + confidence * 0.2`
- Spotlight arbitration runs at tier-1 timescale (1s updates)
- High-salience events (>0.8) can preempt spotlight immediately

### Phase R4: Self-Model & Predictive Introspection — ✅ COMPLETE

**Goal**: System predicts its own state and feeds confidence into dispatch.

**Delivered**: `wm-selfmodel` crate with MetricTracker (8 kinds), ForecastEngine (linear regression + R²), AlertEngine, ConfidenceCalibrator. Wired into dispatch via `Context::self_model_confidence`. 3 MCP tools. 22 tests.

**Deliverables**:
- `wm-selfmodel` crate
- Per-subsystem metric tracking (CPU, memory, latency, coherence, error rate)
- Forecasting: simple linear extrapolation → EWMA → (future) Bayesian
- Threshold alerts: predict when metrics will cross danger thresholds
- Confidence calibration: dispatch pipeline reads self-model confidence
- MCP tools: `selfmodel.forecast`, `selfmodel.alerts`, `selfmodel.snapshot`

**Key decisions**:
- Metrics stored in LMDB (substrate galaxy) with temporal keys
- Forecasting is always running but only fires alerts in Beta/Gamma
- Confidence <0.5 triggers conservative dispatch (prefer cached results)
- Self-model is read-only from the dispatch pipeline (no feedback loops)

### Phase R5: Bicameral Reasoning Upgrade — ✅ COMPLETE

**Goal**: Upgrade `reasoning.bicameral` from stub to dual-hemisphere system.

**Delivered**: `wm-bicameral` crate with LeftHemisphere (deterministic), RightHemisphere trait (pluggable — stub + closure + LLM impls), CorpusCallosum (bounded channel), ConsensusGate (6 verdict types), BicameralEngine. 2 MCP tools. 36 tests. LLM right hemisphere integrated via `ureq` (OpenAI-compatible API, env-configured, graceful fallback). Deep integration: bicameral consensus runs on all write-effect dispatches.

**Deliverables**:
- `wm-bicameral` crate
- Left hemisphere: deterministic Rust logic + Haskell verification (via polyglot)
- Right hemisphere: LLM inference (via MCP client or embedded model)
- Corpus callosum: bounded channel with bidirectional critique
- Consensus gate: both hemispheres must agree, timeout → left-only fallback
- Integration: `reasoning.bicameral` tool dispatches to both hemispheres
- Novel: right hemisphere can flag anomalies in sensor feeds (if embodiment active)

**Key decisions**:
- Left hemisphere always available (Rust-native)
- Right hemisphere optional (requires LLM connection or embedded model)
- Corpus callosum bandwidth: configurable, default 1KB per exchange
- Timeout: 5s default, configurable. On timeout, left hemisphere result used.
- Consensus: both must return `agree` or `disagree`. If disagree, debate up to 3 rounds.

### Phase R6: Embodiment Layer (Hardware-Dependent) — PENDING

**Goal**: Connect WhiteMagic to physical sensors and actuators.

**Status**: Not yet started. Hardware-dependent, requires target platform selection (ROS2, SPI/I2C, lab instruments, etc.).

**Deliverables**:
- `wm-embodiment` crate
- C ABI bindings for common hardware interfaces:
  - SPI/I2C (Linux spidev, i2c-dev)
  - Serial (UART, USB serial)
  - ROS2 bridge (via rcl-rs or C ABI to rcl)
  - Camera frames (V4L2, zero-copy DMA buffers)
  - IMU/force sensors (stack-allocated frame types)
- Sensor frame types: `ImuFrame`, `ForceFrame`, `VisionFrame`, `AudioFrame`
- Actuator command types: `MotorCommand`, `ServoCommand`, `RelayCommand`
- Hardware watchdog: if no cognitive response in 100ms, enter safe state
- Reflex arcs: sensor → reflex tool → actuator (all in tier-0 path)

**Key decisions**:
- Hardware support is feature-gated: `#[cfg(feature = "ros2")]`, `#[cfg(feature = "spi")]`
- Sensor frames are stack-allocated with fixed-size buffers (no heap in reflex path)
- Vision frames use pre-allocated DMA buffers (zero-copy from kernel)
- Watchdog is a hardware timer (timerfd), not a software check
- Safe state: all actuators to neutral, log event, await cognitive recovery

### Phase R7: Emotion & Drive Core — ✅ COMPLETE

**Goal**: Intrinsic motivation signals biasing exploration and tool selection.

**Delivered**: `wm-drive` crate with 5 drives (curiosity, satisfaction, caution, energy, social), 9 event kinds, DriveCore with decay toward baseline, DriveBias with ToolCategory, BiasConfig. 2 MCP tools. 32 tests. Drive bias wired into dispatch pipeline: caution gate (warns on writes when caution > 0.85), energy gate (warns on writes when energy < 0.15). Drive events fired post-dispatch. Self-model confidence feeds drive system.

**Deliverables**:
- Drive state: curiosity, satisfaction, caution, energy, social
- Event-driven drive updates (tool success → satisfaction, novel input → curiosity)
- Drive bias on tool selection (high curiosity → prefer exploration tools)
- MCP tools: `drive.snapshot`, `drive.event`
- Integration with global workspace (drive changes publish events)

---

## 6. Performance Targets

| Metric | v3 (current) | v4 reflex tier | v4 cognitive tier |
|---|---|---|---|
| Dispatch latency | 4.9ms | <100µs | <5ms (same) |
| Memory read | 2.9ms | <10µs (mmap direct) | <3ms (same) |
| Sensor → actuator | N/A | <1ms (target <100µs) | N/A |
| Startup | 34.9ms | <5ms (reflex-only mode) | <50ms (full) |
| Memory footprint | ~12MB | <2MB (reflex-only) | <20MB (full) |
| CPU idle | 0% (Delta) | 0% (no polling) | 0% (same) |
| Safety check | ~2µs (dharma) | 1 instruction (bitmask) | ~2µs (same) |

---

## 7. Language Decision (Settled)

**Rust is the primary language for v4.** The language research session evaluated Koka, Go, C, Java, and PHP against WhiteMagic's requirements:

- **Microsecond latency** eliminates Go (GC pauses), Java (GC + JVM overhead), PHP (interpreted)
- **Memory safety** eliminates C (no safety guarantees)
- **Production readiness** eliminates Koka (not ready, no ecosystem)
- **Polyglot FFI** — Rust's C ABI is the cleanest bridge to every domain's tools

Rust satisfies all five requirements: zero-runtime, safe-by-default, polyglot-capable, production-proven, microsecond-capable. No other language does.

**Polyglot languages remain for specialized cores** (not as primary):
- Koka: effect verification for Dharma rules (compiled to C, linked as .so)
- Julia: Monte Carlo, quantum geometry (embedded via jlrs)
- Haskell: topological verification, DAG cycle checks (GHC → .so)
- Zig: ultra-low-latency TRN gate (C ABI, link directly)

---

## 8. Relationship to MandalaOS

MandalaOS is the **north star** — the long-horizon vision of a governed AI operating system. WhiteMagic v4 is the **cognitive substrate** that would run inside MandalaOS compartments.

| MandalaOS Module | WhiteMagic v4 Implementation |
|---|---|
| `ethics/` (Dharma, Karma, Voice Audit) | wm-governance + wm-bicameral consensus |
| `action/` (PRAT dispatch, tool registry) | wm-dispatch (cognitive) + wm-reflex (real-time) |
| `deliberation/` (Gana council, voting) | wm-bicameral + wm-workspace arbitration |
| `health/` (Harmony, Homeostasis) | wm-substrate + wm-selfmodel + wm-timescale budgets |
| `memory/` (Experience buffer, Galactic map) | wm-memory (LMDB + Tantivy + LanceDB) |
| `coordination/` (Resource ledger, merge) | Future: multi-agent federation via wm-workspace |

v4 does not require MandalaOS. But v4's architecture is designed to **slot into MandalaOS compartments** when that OS layer is built. The `wm-reflex` crate's safety bitmask is the in-process equivalent of MandalaOS's `mandala-dharmad` policy engine — and could be compiled to eBPF for kernel-level enforcement in a future MandalaOS integration.

---

## 9. CyberBrains 7-Layer Model → v4 Mapping

The CyberBrains v2.0 notes describe a 7-layer nested model (Jaynes × Bailey developmental stages). Here's how v4 maps:

| Layer | CyberBrains Name | v4 Implementation | Priority |
|---|---|---|---|
| 1 | Atomic Kernel (seed-consciousness) | wm-core + wm-reflex safety bitmask | Phase R1 |
| 2 | Sensorimotor Weave | wm-embodiment + sensor frames | Phase R6 |
| 3 | Command Hall (bicameral oracle) | wm-governance + wm-bicameral left hemisphere | Phase R5 |
| 4 | Narrative Layer (self-conscious metaphor) | wm-consciousness (citta, dream) + wm-bicameral right | Existing + R5 |
| 5 | Radiant Layer (surplus routing) | Future: resource sharing, API publication | Post-v4 |
| 6 | Constellation Layer (swarm negotiation) | Future: multi-agent via wm-workspace federation | Post-v4 |
| 7 | Logos Layer (planetary governance) | Future: MandalaOS integration | Post-v4 |

**v4 focuses on layers 1-4.** Layers 5-7 are future work that depends on multi-agent infrastructure and MandalaOS.

---

## 10. Next Steps

### Immediate — ALL DONE:
1. ~~**Finish Phase 9 Tier 6-7**~~ — ✅ 126 tools, Phase 9 substantively complete
2. ~~**Update STRATEGY.md**~~ — ✅ v4 section added
3. ~~**Discuss**~~ — ✅ Reviewed, prioritized, built R1-R7
4. ~~**Deep integration**~~ — ✅ Drive bias → dispatch, bicameral → writes, timescale → citta/dream, workspace → drive
5. ~~**LLM right hemisphere**~~ — ✅ OpenAI-compatible via ureq, env-configured, graceful fallback
6. ~~**Live performance test**~~ — ✅ 45/45 NLU routes correct, 1302 tests

### v4 Phases R1–R7 — ALL COMPLETE:
1. ~~R1: wm-reflex~~ — ✅ 48 tests
2. ~~R2: wm-timescale~~ — ✅ 34 tests
3. ~~R3: wm-workspace~~ — ✅ 51 tests
4. ~~R4: wm-selfmodel~~ — ✅ 22 tests
5. ~~R5: wm-bicameral~~ — ✅ 25 tests
6. ~~R6: wm-substrate~~ — ✅ 19 tests (already existed)
7. ~~R7: wm-drive~~ — ✅ 32 tests

**v4 totals**: 17 crates, 139 tools, 1302 tests, 0 clippy warnings.

### Remaining Work:
1. **Local AI integration** — BitMamba autonomic layer (salience → citta), LlamaLeftHemisphere (llama.cpp), BitNet right hemisphere, inference router
2. **R6 Embodiment Layer** — hardware I/O (ROS2, SPI/I2C, sensors, actuators). Requires target platform selection.
3. ~~**Migration tool**~~ — ✅ 28 tests (galaxy mapping, type mapping, dry run, tags, galaxy filter, multi-galaxy). Benchmark regressions: 0 regressions, 10 improvements.

---

## 11. Source Material References

- `WHITEMAGIC-aux/aux/codex/whitemagic-codex/00_source/LIBRARY/cyberbrains.txt` — Main CyberBrains essay (535 lines)
- `WHITEMAGIC-aux/aux/codex/whitemagic-codex/00_source/LIBRARY/cyberbrains2` — CyberBrains v2.0 with 7-layer model (347 lines)
- `WHITEMAGIC-aux/aux/codex/whitemagic-codex/00_source/LIBRARY/- CYBERBRAINS -.txt` — CyberBrain v1.2 → v2.0 enhancements (136 lines)
- `WHITEMAGIC-aux/aux/codex/whitemagic-codex/00_source/LIBRARY/CyberBrain Core Mapping.txt` — Core mapping + RTC integration (242 lines)
- `WHITEMAGIC/core/whitemagic/core/cyberbrain/` — v2 Python implementation (nervous_system.py, global_workspace.py, multi_timescale_sync.py)
- `WHITEMAGIC/core/whitemagic/tools/handlers/cyberbrain.py` — v2 tool handlers (salience, bicameral, retention, drives, self-model)
- `WHITEMAGIC/docs-2/spec/MANDALA_OS.md` — MandalaOS vision spec (191 lines)
- `WHITEMAGIC/docs-2/SFW2/MandalaOS_v0.1_SPEC.md` — MandalaOS v0.1 spec (80 lines)
- `whitemagic-v4/docs/STRATEGY.md` — v4 architecture & strategy (1559 lines)
- `whitemagic-v3/docs/notes/strategic-gap-analysis-2026-08-03.md` — Phase 9 gap analysis
