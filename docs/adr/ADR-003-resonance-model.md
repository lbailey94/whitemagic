# ADR-003: Resonance Model — Gan Ying Bus and Wu Xing Scheduling

**Status**: Accepted  
**Date**: 2026-04-15  
**Deciders**: WhiteMagic core team  
**Tags**: architecture, resonance, scheduling

---

## Context

WhiteMagic needs a mechanism to prioritize which memories surface, which tools activate,
and when background processes run. Initial approach: simple priority queues and TTL caches.
Problem: this is purely mechanical — it doesn't capture the *relational context* of why
one memory is more relevant than another at a given moment.

## Decision

Adopt the **Resonance Model**: a first-principles scheduling and activation system based on
two complementary frameworks:

### 1. Gan Ying Bus (感應 — "Resonance Response")

A publish-subscribe event bus that propagates state changes through the system
using sympathetic resonance rather than direct method calls:

```
Memory stored  →  Gan Ying event  →  Subscribers (salience arbiter, constellation detector, ...)
```

Events carry a `resonance_score` ∈ [0, 1]. High-resonance events trigger immediate downstream
reactions; low-resonance events accumulate over time until a threshold is crossed.

### 2. Wu Xing Phase Scheduling (五行 — "Five Elements")

Background processes are scheduled according to the current Wu Xing phase (Wood, Fire, Earth,
Metal, Water) which cycles on a configurable period:

| Phase | Process Type | Example |
|-------|-------------|---------|
| Wood | Growth / Ingestion | New memory intake, embedding updates |
| Fire | Peak activity | PRAT dispatch, active session handling |
| Earth | Stabilization | Memory consolidation, deduplication |
| Metal | Refinement | Retention sweep, galactic edge archival |
| Water | Rest / Dreaming | Dream cycle, pattern synthesis, KG extraction |

**Key design choices**:
- Resonance scoring is continuous — no binary "active/inactive" states
- The Gan Ying Bus is the primary inter-subsystem communication channel; direct coupling is discouraged
- Wu Xing phase affects scheduling *weight*, not *eligibility* — all processes can run in any phase

## Consequences

**Positive**:
- Salience-driven activation finds relevant memories without scanning the full DB
- Wu Xing provides a natural throttle for background work (prevents CPU spikes during Fire/peak)
- Resonance scores are auditable and inspectable via `ganying_history` tool

**Negative**:
- ~10ms overhead per tool call for resonance context injection and recording
- Subtle resonance bugs are hard to debug (non-deterministic activation patterns)
- Contributors must understand the model to safely add new subsystems

## Alternatives Considered

- **Simple priority queue**: Rejected — no contextual sensitivity across sessions
- **ML-based activation**: Deferred — requires training data not yet collected
- **Redis pub/sub directly**: Partially adopted for multi-node coordination (broker tools); Gan Ying Bus used for in-process coordination to avoid Redis dependency for single-node deployments
