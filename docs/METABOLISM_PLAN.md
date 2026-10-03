# Phase 1–2 — Metabolism Lane (one-pager)

**Status:** planning note · 2026-09-16 · companion to `DESIGN_CANON.md` §10 ·
**not binding.** This lane runs *parallel* to Phases 1–2 and blocks nothing; it exists so the
stranger-usage question is designed before it is needed, not after Phase 2 passes.

Purpose: an adaptive substrate that only consumes its own outputs becomes self-referential
("synthetic inbreeding", CONV §3 L3899–3905). Metabolism is the discipline of staying coupled to
external reality. It is the *research* half of the stranger lane whose *product* half already
exists (installs, releases).

---

## 1. The distinction to preserve

- **Gan Ying** = general internal/external coupling (resonance, events). Already a design concern.
- **communicate** (verb candidate) = **governed** coupling across a maintained boundary
  (CONV §3 L4226–4228). Metabolism enters only through this verb — never as a side door.
- **Two gates** for anything crossing: `transport validation → semantic/authority validation`
  (CONV §3 L4230–4234). Safe bytes can still carry an unsafe interpreted instruction; this is the
  prompt-injection boundary and it applies to telemetry, mesh messages, and corpus imports alike.

## 2. What counts as externally grounded intake (Phase 2–3)

| Signal | Class | Domain | Notes |
|---|---|---|---|
| Stranger install + first-session continuity success | system | `system` | from release/distribution side, not the substrate |
| Autonomous agent usage events (opt-in) | system | `system` | e.g. recall miss/abstention rates, session resume counts |
| Explicit user value report ("this helped / this failed") | **reported** | `reported` | testimony; never `world` |
| Task outcomes from real work (success/failure of an action) | system/`world` only via consequence channel | `system`→`world` intake rules | consequences of action are the only self-generated path toward world-evidence — still via ratified channel |
| Mesh peers' messages | reported | `reported` | signed ≠ true; domain stays `reported` |
| Synthetic/developmental runs | simulated | `simulated` | never promotable (Charter §3.8) |

Non-negotiable: **no intake is recorded as `world` unless it arrived through a ratified
world-intake channel** (sensor, authenticated source, recorded action consequence). Repetition
never promotes. This table is a statute, not an invariant — amendable with a receipt.

## 3. The M health metric (monitor, never a target)

```
M = externally grounded informational intake / total cognitive processing
```
- **Numerator:** records entering via the channels in §2, weighted by provenance strength.
- **Denominator:** all substrate operations in the window (selection events, proposals,
  recalls — measured from the journal, which already exists for Phase 1).
- **Use:** a health indicator inspected periodically (`inspect` scope, Phase 3+). Low M with high
  processing = recursive self-consumption; it is a **warning to investigate**, not a KPI to
  maximize. Do not add machinery to move M; add coupling only when a failure is demonstrated.

## 4. Consent & governance (Charter §3.5)

- Local-first default; opt-in for any transmission; `transport: none` until an explicit opt-in
  phase exists (inherits Gen2's telemetry precedent, `WMv9/docs/TELEMETRY.md`).
- Any collected signal is inspectable, deletable (authorized erasure, Charter §3.2), and its
  presence disclosed in user-facing surfaces.
- Never collect memory content, prompts, or session text without explicit, scoped consent.

## 5. What this lane does *not* do

- No telemetry implementation in Phase 1 (interface work only; the A/B must not depend on it).
- No automatic promotion of usage statistics into the epistemic substrate.
- No mesh/communicate verb implementation before Phase 3+; only the two-gate boundary design
  is fixed now so later implementations cannot bypass it.

## 6. Next concrete artifacts (when the lane is picked up)

1. Consent/collection spec (one page, operator-approved) before any field collection.
2. A manual intake channel for stranger reports (reported-domain records), with provenance, to
   bootstrap metabolism without infrastructure.
3. M computed from journal + intake counts once Phase 2 runs exist — first honest reading of
   whether the substrate encountered reality or itself.
