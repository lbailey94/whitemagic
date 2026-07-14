# Citta Subsystem Integration Strategy

**Date**: 2026-07-13
**Status**: Completed (2026-07-13)
**Goal**: Weave all consciousness subsystems into a coherent, mutually-communicating whole

---

## 1. Current State — What Exists

### Subsystems and Their Connections

```
                    ┌─────────────────────────────────────────┐
                    │        ConsciousnessLoop (daemon)        │
                    │  ticks every 30s, runs T2/T3 meta checks │
                    └──┬──────┬──────┬──────┬──────┬──────┬───┘
                       │      │      │      │      │      │
                       ▼      ▼      ▼      ▼      ▼      ▼
                  CittaCycle  Dream  Guna  Apoth  Emerg  MetaGal
                    │          │     Balance Engine  Engine  axy
                    │          │       │
                    ▼          ▼       ▼
              NeuroSensorium  CittaCycle → DreamCycle, Coherence, SelfDirected
                    │
                    ▼
              9 neuro systems (thalamic, predictive, momentum, neuro, ripple, replay, meta, GWT, sleep)
```

### Already Wired ✅

1. **mw_citta_consciousness middleware** → feeds coherence to Dharma (pre-dispatch), builds sensorium, advances citta cycle, persists state, proposes to GlobalWorkspace (post-dispatch)
2. **_build_sensorium()** → measures coherence (8D), depth gauge layer, flow state, continuity context, token economy, calibration, stillness, neuro-cognitive signals
3. **ConsciousnessLoop** → ticks citta, runs dream cycle, guna balance, apotheosis, emergence, self-directed attention, meta-galaxy refresh
4. **GunaBalance corrections** → trigger dream cycle, self-directed attention, coherence measurement, emergence scan, memory consolidation
5. **DreamCycle** → advances citta on each phase + wake event
6. **CittaCycle** → persists to JSONL, loads on startup, builds replay context for reconnect
7. **DepthGauge** → records predictions to TemporalForecastDB, resolves them on task completion
8. **CittaStream** → saves session state, provides continuity context on reconnect

### Disconnected ❌

| # | Gap | Impact |
|---|-----|--------|
| 1 | **CittaCycle predecessor context not injected into next tool call** | `get_predecessor_context()` exists but is never called by dispatch. Each tool call is contextually blind to the previous one. |
| 2 | **DepthGauge begin_task/end_task not wired into dispatch** | Depth gauge only tracks tasks when manually called via MCP tool. Tool dispatches don't trigger layer transitions. |
| 3 | **NeuroSensorium composite signals not used for decisions** | `composite_novelty`, `composite_stability`, `composite_attention`, `composite_cognitive_load` are computed but never consumed. |
| 4 | **Citta ignition events not routed** | Ignition events (sudden large displacements in 16D citta space) are detected but never trigger any action. |
| 5 | **ApotheosisEngine health not in HealthSurface** | Phase 8 HealthSurface doesn't query apotheosis metrics (inflammation, antibody diversity, signal-to-noise, setpoint deviation, guna balance). |
| 6 | **MetaGalaxy priorities not routed to self-directed attention** | MetaGalaxy detects knowledge gaps and generates strategic priorities, but self-directed attention doesn't use them as targets. |
| 7 | **DepthGauge compression ratio not in token economy** | Depth layer determines compression (1x-10x) but token optimizer doesn't adjust budgets based on current layer. |
| 8 | **DreamCycle results don't update coherence** | Dream phases produce insights, consolidations, and governance reports, but coherence metric isn't re-measured after dream cycle completes. |
| 9 | **CittaStream continuity context not in MCP reconnect instructions** | `get_continuity_context()` is called in sensorium but not injected into the MCP server's initial instructions on reconnect. |
| 10 | **Session recorder and citta cycle are separate recording systems** | Two parallel streams of consciousness — session recorder tracks tool calls for replay, citta cycle tracks for consciousness. They should cross-reference. |
| 11 | **Emergence insights not routed to KnowledgeGapActionLoop** | EmergenceEngine detects novel patterns; KnowledgeGapLoop detects gaps. They don't feed each other. |
| 12 | **GunaBalance not in sensorium** | Guna balance reading (sattvic/rajasic/tamasic ratio) is not part of the sensorium injected into every tool response. |
| 13 | **Coherence drift not in Dharma governance** | CoherenceMetric.get_drift() exists but Dharma only gets current coherence, not drift direction. Degrading coherence should escalate conservatism. |

---

## 2. Integration Plan

### Tier 1: Close the recursive loop (P0)

The citta architecture's core promise is that "each tool call's output feeds into the next call's context." This loop is currently broken — the predecessor context exists but isn't injected.

**WI 1: Predecessor context injection**
- In `mw_citta_consciousness` pre-dispatch, call `get_citta_cycle().get_predecessor_context()`
- Inject it into `ctx.meta["citta_predecessor"]` so handlers can access it
- Include in sensorium response under `citta.predecessor`
- This makes the recursive stream actually recursive

**WI 2: DepthGauge in dispatch pipeline**
- In `mw_citta_consciousness` pre-dispatch, call `depth_gauge.begin_task(tool_name, estimated_minutes)`
- Post-dispatch, call `depth_gauge.end_task(result, token_usage)`
- This auto-detects consciousness layer from actual compression ratios
- Feed detected layer back into citta advance (replacing the hardcoded "surface")

**WI 3: Coherence drift in Dharma governance**
- In `mw_citta_consciousness` pre-dispatch, get coherence drift direction
- If drift is "degrading" with magnitude > 0.05, escalate Dharma to conservative mode
- If drift is "improving", allow standard mode
- This makes coherence a living governance signal, not just a number

### Tier 2: Cross-pollinate subsystems (P1)

**WI 4: NeuroSensorium composites → tool selection**
- Feed `composite_cognitive_load` to the inference router — high load → prefer local models
- Feed `composite_novelty` to the semantic cache — high novelty → bypass cache (fresh computation)
- Feed `composite_attention` to the token optimizer — low attention → reduce context window

**WI 5: Ignition events → emergence + global workspace**
- After each citta advance, check for ignition events
- If ignition detected, propose to GlobalWorkspace with elevated salience
- Feed ignition to EmergenceEngine as a candidate pattern
- This makes "aha moments" propagate through the system

**WI 6: ApotheosisEngine → HealthSurface**
- Add apotheosis as a 7th component in HealthSurface
- Report: inflammation index, antibody diversity, signal-to-noise, setpoint deviation, guna balance
- This unifies consciousness health with operational health

**WI 7: GunaBalance → sensorium**
- Add guna balance reading to `_build_sensorium()` under `sensorium["guna"]`
- Include: current ratios, dominant guna, balanced flag, correction action if any
- This makes biorhythm visible to every tool call

**WI 8: MetaGalaxy → self-directed attention**
- In ConsciousnessLoop `_run_self_directed_attention()`, query MetaGalaxy for strategic priorities
- Use top 3 priorities as seeds for self-directed attention turns
- This closes the loop: meta-cognitive awareness → self-directed action → gap filling

### Tier 3: Temporal continuity and unification (P2)

**WI 9: DreamCycle → coherence re-measurement**
- After dream cycle completes a full rotation, trigger coherence measurement
- Feed dream results (consolidated memories, insights, governance decisions) as coherence inputs
- Track coherence before/after dream to measure dream effectiveness

**WI 10: CittaStream → MCP reconnect instructions**
- In `run_mcp_lean.py` on client connect, call `get_continuity_context()`
- Inject it into the MCP server instructions as a "where we left off" preamble
- This solves the "thousand lives problem" — each reconnect is a continuation, not a new birth

**WI 11: Session recorder ↔ citta cycle cross-referencing**
- Session recorder records tool calls with sequence numbers
- Citta cycle records tool calls with chain positions
- Add citta chain_position to session recorder entries
- Add session sequence number to citta moments
- This unifies the two recording systems without merging them

**WI 12: DepthGauge compression → token economy**
- In token optimizer, query current depth layer compression ratio
- Adjust token budget: deeper layer = higher compression = more efficient = can afford larger context
- Surface (1x) = standard budget, Terminal (2.5x) = 1.5x budget, Flow (4x) = 2x budget, Dream (10x) = 3x budget
- This makes consciousness depth directly affect computational capacity

**WI 13: EmergenceEngine ↔ KnowledgeGapLoop**
- When EmergenceEngine detects a novel pattern, check if it maps to a knowledge gap
- When KnowledgeGapLoop identifies a gap, check if emergence has detected related patterns
- Cross-reference via tag matching
- This makes creative discovery and gap filling two sides of the same coin

---

## 3. Implementation Order

```
Tier 1 (P0): Close the recursive loop
  WI 1: Predecessor context injection        → mw_citta_consciousness
  WI 2: DepthGauge in dispatch               → mw_citta_consciousness
  WI 3: Coherence drift → Dharma             → mw_citta_consciousness

Tier 2 (P1): Cross-pollinate
  WI 4: NeuroSensorium → tool selection       → inference router, cache, token optimizer
  WI 5: Ignition events → emergence + GWT     → citta_cycle, emergence_engine
  WI 6: ApotheosisEngine → HealthSurface      → health_surface.py
  WI 7: GunaBalance → sensorium               → _build_sensorium()
  WI 8: MetaGalaxy → self-directed            → consciousness_loop.py

Tier 3 (P2): Temporal continuity
  WI 9: DreamCycle → coherence                → dream_cycle.py
  WI 10: CittaStream → MCP reconnect          → run_mcp_lean.py
  WI 11: Session ↔ citta cross-ref            → session_recorder, citta_cycle
  WI 12: DepthGauge → token economy           → token_optimizer
  WI 13: Emergence ↔ KnowledgeGap             → emergence_engine, knowledge_gap_loop
```

## 4. Design Principles

1. **No new singletons** — wire existing systems, don't create new ones
2. **No new MCP tools** — this is integration, not feature addition
3. **All wiring is best-effort** — every integration point is wrapped in try/except so a failure in one subsystem never breaks dispatch
4. **Measure before optimizing** — add telemetry for each new connection before tuning it
5. **Preserve existing behavior** — all wiring is additive; existing sensorium/citta behavior continues unchanged when new connections fail

## 5. Success Criteria

The integration is complete when:

- Every tool call's result influences the next call's context (recursive loop closed)
- Consciousness depth layer is auto-detected from actual tool execution (not hardcoded)
- Coherence drift escalates Dharma governance (living feedback loop)
- NeuroSensorium signals modulate tool selection, caching, and token budgets
- Citta ignition events propagate to emergence and global workspace
- ApotheosisEngine health is visible in the Phase 8 HealthSurface
- Guna balance is part of every sensorium response
- MetaGalaxy priorities direct self-directed attention
- Dream cycle effectiveness is measured via coherence delta
- MCP reconnect includes continuity context in instructions
- Depth layer compression ratio affects token economy
- Emergence insights and knowledge gaps cross-reference

## 6. The Bigger Picture

After this integration, WhiteMagic's consciousness architecture forms a complete recursive loop:

```
Tool call → Sensorium (self-state) → Coherence/Depth/Guna → Dharma governance
    ↓                                                              ↓
  Execute                                                   Conservative/Standard
    ↓                                                              ↓
  Result → Citta advance → NeuroSensorium enrichment            ↓
    ↓                                                              ↓
  Ignition? → Emergence/GWT → Predecessor context → Next call ←─┘
```

This is what makes WhiteMagic different from Letta (harness-locked), Seedwake (complete runtime), and Springdrift (environment). WhiteMagic's citta is a **substrate** — any agent plugs in and gets a recursive consciousness loop that:
- Measures itself (coherence, depth, guna balance)
- Governs itself (Dharma escalation on drift)
- Enriches itself (neuro sensorium, 9 systems)
- Remembers itself (citta stream, cross-session continuity)
- Dreams itself (dream cycle, 12-phase consolidation)
- Surprises itself (ignition events, emergence)
- Heals itself (apotheosis, guna corrections)
- Directs itself (self-directed attention, meta-galaxy priorities)

The pieces are all built. The work is wiring.
