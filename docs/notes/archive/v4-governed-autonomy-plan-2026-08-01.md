# WhiteMagic v4 — Governed Autonomy Plan

**Date:** 2026-08-01  
**Authors:** Lucas + Cascade (v4)  
**Companion to:** `v2-autonomous-activity-investigation-2026-08-01.md`  
**Principle:** All improvements in v4 first. Future autonomous behavior must be **intentional, efficient, transparent, deep, actionable, and spiraling outward**.

---

## 1. Design Principles for v4 Autonomous Cognition

v2 ran uncontrolled because it lacked governance layers. v4 will implement autonomous cognition differently — guided by six principles derived from the Mandala OS specification and the v2 investigation:

### 1.1 Intentional
- **No default-on background loops.** Autonomous cognition is opt-in, not opt-out.
- **Purpose gating:** Every autonomous cycle must declare its purpose and expected outcome before running. Cycles that cannot articulate a purpose are not started.
- **Task-bound:** Autonomous cycles are triggered by specific events (tool dispatch, memory threshold, user request, scheduled task) — not by a continuous timer that fires regardless of context.
- **Feature flags default to `False`.** Each cognitive function must be explicitly enabled.

### 1.2 Efficient
- **Harmony Vector gating:** Before any autonomous cycle runs, the system checks a Harmony Vector (CPU load, memory pressure, battery state, thermal state). If resources are constrained, cycles are deferred, throttled, or skipped.
- **No eager prewarming.** Subsystems load on first use, not at startup. The v2 prewarm thread that loaded torch + MiniLM + HNSW + 10 Citta modules at startup is an anti-pattern.
- **Bounded computation:** Each cycle has a time budget and memory budget. Cycles that exceed their budget are terminated and logged.
- **Diminishing returns detection:** If a cycle produces the same output N consecutive times (v2's dream cycle produced zero insights 284 times), it is automatically suspended.

### 1.3 Transparent
- **Gnosis Portals:** Every autonomous cycle is visible via introspection APIs. Users can query `wm.gnosis.autonomy.status()` to see what's running, why, and what it's consuming.
- **Activity log:** All autonomous actions are logged with: trigger, purpose, duration, resource cost, and output summary.
- **No hidden cognition:** The UI/CLI surfaces autonomous activity. No background thinking without a visible indicator.
- **Auditable:** Every autonomous decision is traceable. Dharma rules log the Karmic Trace of each action.

### 1.4 Deep
- **Grounded in real context:** Autonomous cycles operate on actual data — the codebase, development goals, conversation history, project roadmap — not on abstract cognitive parameters.
- **No meta-circular loops:** v2 optimized its own optimization parameters and dreamed about its own dreams. v4's autonomy must connect to external reality: code analysis, documentation gaps, test coverage, architectural decisions.
- **Source-aware:** Cycles can read the project's source code, docs, and test suite to generate grounded insights.

### 1.5 Actionable
- **Every insight has a recommended action:** Not just "178 memories are disconnected" but "connect memory X to memory Y because they share concept Z."
- **Action verification:** Recommended actions can be verified (does the connection make sense? does the test pass? does the doc exist?).
- **Human-in-the-loop by default:** Insights are surfaced for review. Autonomous action requires explicit Dharma permission.

### 1.6 Spiraling Outward
- **Expanding scope, not recursive depth:** Each autonomous cycle should explore new domains, not re-examine the same data at greater depth.
- **Cross-domain discovery:** Cycles should connect disparate galaxies/domains, not optimize within a single domain.
- **Novelty requirement:** Cycles that cannot identify novel information are suspended. The system must demonstrate it is learning something new, not reprocessing what it knows.

---

## 2. Acting on v2's T3 Insights (in v4)

v2's most recent T3 insight pipeline (Aug 1, 9:40 PM) produced 29 insights. Here is how each category translates to v4 action:

### 2.1 Critical: Knowledge Gaps

**v2 said:** "No critical future-oriented memories. Create high-level vision documents." and "No memories in Detail+Future quadrant. Create specific, dated implementation plans."

**v4 action:**
- **Already addressed.** v4 has `docs/STRATEGY.md` (the roadmap) and `docs/PROGRESS.md` (the progress tracker). These are the strategic vision and implementation plans v2 was missing.
- **v4 improvement:** Add a `memory.vision` tool that can store and retrieve strategic vision documents in a dedicated `Vision` galaxy. This gives the autonomous cognition system a grounding in project goals.
- **v4 improvement:** Add a `memory.roadmap` tool that links memories to specific roadmap phases, creating the "Detail+Future quadrant" v2 identified as missing.

### 2.2 High: Disconnected High-Value Memories (178)

**v2 said:** "178 memories with gravity > 0.6 but fewer than 3 associations. These are isolated knowledge."

**v4 action:**
- **Phase 6.2 already addresses this.** The `LinkType` enum and Hebbian learning (`activate()` / `decay()`) provide the typed association framework v2 lacked.
- **v4 improvement:** Implement a `consolidation.connect` autonomous cycle (gated, opt-in) that:
  1. Scans for high-importance memories with < 3 associations
  2. Uses semantic similarity (Tantivy FTS + LanceDB embeddings from Phase 6.3) to find candidate connections
  3. Proposes typed associations (`LinkType::Related`, `LinkType::Extends`, etc.)
  4. Surfaces proposals for human review before persisting
- **Key difference from v2:** Proposals are typed, grounded in semantic similarity, and require human approval.

### 2.3 High: Activity Surge Detection (21.4x)

**v2 said:** "Last 7 days had 21,750 memories vs 1,018 the week before. A burst of new knowledge is entering the system."

**v4 action:**
- **This is expected behavior.** The surge was caused by v4 development sessions (our coding conversations). v2 detected it but couldn't contextualize it.
- **v4 improvement:** Add a `memory.telemetry` tool that tracks memory creation velocity and can attribute surges to specific sources (development sessions, document ingestion, autonomous cycles).
- **v4 improvement:** The Harmony Vector should include a "cognitive load" metric — memory creation rate as a proxy for system activity. High cognitive load should throttle autonomous cycles.

### 2.4 High: Memory Creation Accelerating (2.7x)

**v2 said:** "Creation velocity is 2.7x the 30-day average. High capacity for consolidation."

**v4 action:**
- **v4 improvement:** Implement a `consolidation.compress` autonomous cycle (gated) that:
  1. Identifies memories with high semantic overlap (using Phase 6.3 embeddings)
  2. Proposes merging or creating `LinkType::Supersedes` associations
  3. Surfaces proposals for human review
- **v4 improvement:** The `lifecycle.consolidate()` function (Phase 6.1) already skips protected memories. Extend it to propose consolidation candidates rather than auto-merging.

### 2.5 High: 147 Untitled Memories

**v2 said:** "147 memories without meaningful titles."

**v4 action:**
- **v4 already has titled memories.** The `MemoryMetadata` struct includes content-based identification.
- **v4 improvement:** Add a `memory.title` tool that generates concise titles for memories lacking them, using semantic summarization. This should be a user-triggered tool, not an autonomous background process.

### 2.6 Medium: Tag Cluster Emergence (`gana_abundance` + `sattvic`)

**v2 said:** "Tags co-occurred 9 times in 7 days, above emergence threshold. May indicate a new topic nexus."

**v4 action:**
- **v4 improvement:** Implement an `emergence.scan` autonomous cycle (gated, opt-in) that:
  1. Analyzes tag co-occurrence across galaxies
  2. Identifies clusters above a configurable threshold
  3. Proposes new `LinkType::Cascade` associations to represent emergent themes
  4. Logs findings to a dedicated `Emergence` galaxy for review
- **Key difference from v2:** v2 detected emergence but never acted on it. v4 should propose concrete associations and surface them for review.

### 2.7 Medium: Novelty Spike (`wisdom` tag, 3.2x)

**v2 said:** "Tag spiked from 5 to 16 in last 3 days. Novelty spike."

**v4 action:**
- **v4 improvement:** Add novelty detection to the `retention.rs` engine. Memories with novel tags should receive a `neuro_score` boost, making them less likely to be forgotten.
- **v4 improvement:** Log novelty spikes to the activity log for transparency.

---

## 3. v4 Implementation Roadmap: Governed Autonomy

### Phase A: Harmony Vector (Lakshmi) — New Crate: `wm-substrate`

The foundational layer. Without resource awareness, no governed autonomy is possible.

**Deliverables:**
- `HarmonyVector` struct: CPU load, memory pressure, swap usage, thermal state, battery state, disk I/O
- `SubstrateMonitor` that reads `/proc/meminfo`, `/proc/loadavg`, `/sys/class/thermal/`, `/sys/class/power_supply/` on Linux
- `GunaTag` classification: processes tagged as Sattvic (low resource, responsive), Rajasic (high CPU, greedy), Tamasic (idle, sleeping)
- `harmony.vector` MCP tool: returns current Harmony Vector as JSON
- `harmony.history` MCP tool: returns historical Harmony Vector data

**Dependencies:** None (pure Rust, reading `/proc` and `/sys`)  
**Estimated effort:** 1-2 phases

### Phase B: Resource Gating (Tiferet) — Extend `wm-consciousness`

Wire the Harmony Vector into the brain-wave state system.

**Deliverables:**
- `BrainWaveState` transitions gated by Harmony Vector:
  - High CPU/memory pressure → force `Delta` (minimal cognition)
  - Moderate load → allow `Theta` (light background processing)
  - Low load → allow `Alpha`/`Beta` (full cognition)
  - Critical load → force `Off` (no autonomous cycles)
- `TiferetEngine` that evaluates Harmony Vector and sets brain-wave state
- Configurable thresholds (when to throttle, when to sleep)
- `tiferet.status` MCP tool: shows current resource gating state

**Dependencies:** Phase A (Harmony Vector)  
**Estimated effort:** 1 phase

### Phase C: Dharma Resource Rules — Extend `wm-governance`

Add resource-aware Dharma rules that govern autonomous behavior.

**Deliverables:**
- `DharmaRule::ResourceBudget` — max CPU%, memory, duration for autonomous cycles
- `DharmaRule::PurposeRequired` — autonomous cycles must declare a purpose
- `DharmaRule::NoveltyRequired` — cycles must produce novel output or be suspended
- `DharmaRule::HumanReview` — certain cycle outputs require human approval before action
- `dharma.audit` MCP tool: shows resource rule violations and Karmic Traces

**Dependencies:** Phase A, Phase B  
**Estimated effort:** 1 phase

### Phase D: Gnosis Portals — Extend `wm-mcp`

Transparency layer for all autonomous activity.

**Deliverables:**
- `gnosis.status` MCP tool: real-time view of all autonomous cycles, their purposes, resource costs, and outputs
- `gnosis.history` MCP tool: historical log of autonomous activity
- `gnosis.explain` MCP tool: explains why a specific autonomous action was taken (traceable decision path)
- Activity log persisted to LMDB (not SQLite — v4 uses LMDB)
- CLI command `wm gnosis` — dashboard showing autonomous activity

**Dependencies:** Phase C  
**Estimated effort:** 1 phase

### Phase E: Grounded Autonomous Cycles — Extend `wm-consciousness`

The actual cognitive cycles — but now governed, grounded, and transparent.

**Deliverables:**
- `consolidation.connect` cycle: proposes typed associations for disconnected memories (gated by Harmony Vector, requires human review)
- `consolidation.compress` cycle: proposes merging semantically overlapping memories (gated, human review)
- `emergence.scan` cycle: detects tag/topic emergence patterns (gated, logged)
- `retention.prune` cycle: identifies memories ready for forgetting based on decay + neuro_score (gated, human review for high-importance memories)
- All cycles:
  - Declare purpose before running
  - Check Harmony Vector before starting
  - Have time and memory budgets
  - Produce actionable output (not just observations)
  - Log to Gnosis activity log
  - Suspend if output is not novel (diminishing returns detection)

**Dependencies:** Phase D, Phase 6.3 (embeddings for semantic similarity)  
**Estimated effort:** 2-3 phases

### Phase F: Outward Spiral Mechanism — Extend `wm-consciousness`

Prevent the circular thinking trap v2 fell into.

**Deliverables:**
- `SpiralTracker` that monitors the scope of autonomous cycle outputs:
  - **Inward spiral detection:** If cycles repeatedly examine the same memories/tags/domains, flag as circular
  - **Outward spiral encouragement:** Cycles that connect disparate galaxies or discover cross-domain patterns receive priority
- `novelty.score` function: scores cycle output against historical outputs. Low novelty = cycle suspended.
- `spiral.report` MCP tool: shows whether autonomy is expanding or circling
- Automatic suspension of cycles that produce identical output 3+ consecutive runs

**Dependencies:** Phase E  
**Estimated effort:** 1 phase

---

## 4. Priority and Sequencing

| Phase | Name | Deps | Effort | Priority |
|-------|------|------|--------|----------|
| A | Harmony Vector (Lakshmi) | None | 1-2 phases | **High** — foundation for all governed autonomy |
| B | Resource Gating (Tiferet) | A | 1 phase | **High** — without this, any autonomous cycle is another v2 |
| C | Dharma Resource Rules | A, B | 1 phase | **Medium** — can start with hardcoded rules, formalize later |
| D | Gnosis Portals | C | 1 phase | **Medium** — transparency is important but can follow initial cycles |
| E | Grounded Autonomous Cycles | D, Phase 6.3 | 2-3 phases | **Medium** — the actual cognitive value, but must be governed first |
| F | Outward Spiral Mechanism | E | 1 phase | **Low** — refinement layer once cycles are running |

**Recommended approach:** Implement Phases A-B alongside the existing Phase 6 roadmap (Memory Intelligence). The Harmony Vector and Tiferet gating are lightweight (pure Rust, no heavy deps) and provide the foundation everything else depends on. Phases C-F can follow after Phase 6 is complete.

---

## 5. What We Will NOT Do

- **No modifications to v2.** All improvements in v4.
- **No continuous background loops.** All autonomous cycles are event-triggered and gated.
- **No eager prewarming.** Subsystems load on first use.
- **No autonomous action without human review.** Cycles propose; humans dispose.
- **No meta-circular optimization.** Cycles must be grounded in real project context.
- **No divination/oracle systems.** v2's I Ching/Ifá narrative generation was philosophically interesting but operationally useless. v4's autonomy is grounded in code, docs, and development goals.
- **No feature flags defaulting to True.** Every autonomous function is opt-in.

---

## 6. Relationship to Mandala OS

This plan is the first concrete step toward the Mandala OS vision, implemented within v4's Rust architecture:

| Mandala OS Concept | v4 Implementation | Phase |
|--------------------|-------------------|-------|
| Lakshmi (Harmony Monitor) | `wm-substrate` crate — Harmony Vector | A |
| Tiferet Engine (Self-Balancing) | Brain-wave state gating in `wm-consciousness` | B |
| Yama (Dharma Engine) | Resource rules in `wm-governance` | C |
| Gnosis Portals (Transparency) | Introspection tools in `wm-mcp` | D |
| Controlled Emergence (Lila) | Grounded autonomous cycles in `wm-consciousness` | E |
| Annamaya Kosha (Hardware Layer) | `/proc` and `/sys` readers in `wm-substrate` | A |

The Mandala OS spec describes a full operating system. v4 is not an OS — it's a cognitive architecture running on Linux. But by implementing the governance layers (Lakshmi, Tiferet, Yama, Gnosis) within v4's crate structure, we prototype the core Mandala OS concepts in a real, running system. This is the "behavioral prototyping" path the feasibility roadmap recommends:

> *"Use a standard Linux base and implement eBPF-based monitoring. Great for testing the algorithms of the Harmony Vector and Dharma Engine on real-world hardware."*

v4 does this in Rust instead of eBPF, but the principle is the same: implement the governance algorithms on real hardware, in a real system, before attempting the full OS.

---

## 7. Summary

v2 demonstrated that autonomous cognition without governance is a resource parasite. It produced 59,411 memories and 29 insights per cycle, but the insights were meta-circular and the memory was operationally shallow. The process consumed 2.4GB RAM and 110% CPU because it had no awareness of its own resource footprint.

v4 will implement autonomous cognition with the governance layers v2 lacked: Lakshmi (resource awareness), Tiferet (self-balancing), Yama (ethical gating), and Gnosis (transparency). The result will be an autonomous cognition system that is **intentional, efficient, transparent, deep, actionable, and spiraling outward** — the opposite of v2's uncontrolled, opaque, shallow, circular spiral.

The v2 investigation and this plan are preserved in `docs/notes/` for future reference. All implementation will be in v4.
