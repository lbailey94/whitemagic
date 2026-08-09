# ACS Alignment — WhiteMagic v5 ↔ Microsoft Agent Control Specification

**Date**: 2026-08-09
**Status**: Mapping document — positioning + compliance asset (from WMV5_ANALYSIS P0/P1, handoff proposal #46)
**Baseline**: v5.6.0 (15 crates, ~131K LOC, forbid(unsafe_code), 0 clippy warnings)
**Related**: `crates/wm-governance/src/dharma_gate.rs`, `crates/wm-governance/src/policy.rs`, `crates/wm-governance/src/karma_ledger.rs`, `crates/wm-memory` (LMDB), `crates/wm-dispatch` (pipeline)

---

## 1. What ACS is

Microsoft's Agent Control Specification (announced at Build 2026, June 2) is an open industry specification for deterministic safety/security controls at checkpoints throughout agentic workflows — explicitly framed as "the MCP or A2A of agent safety." It defines **five validation checkpoints**:

1. **Input** — before the agent consumes external data
2. **LLM** — around model inference
3. **State** — memory and context integrity
4. **Tool execution** — before/after tool calls
5. **Output** — before results leave the agent

Policy is expressed as **standard policy YAML** — portable, versionable, auditable.

WhiteMagic's governance model (Dharma gate, Karma ledger, compartment access) was independently designed and covers all five checkpoints. This document maps each checkpoint to concrete v5 mechanisms, shows the policy-language correspondence, and identifies gaps.

---

## 2. Checkpoint mapping

### Checkpoint 1 — Input

| ACS intent | v5 mechanism | Evidence |
|---|---|---|
| Validate external input before consumption | MCP input validation (SSRF, path traversal, injection detection) — D1 security hardening | `crates/wm-mcp` server validation (2026-08-05 hardening) |
| Injection resistance | `OwaspAgentic::PromptInjection` policy rule (LLM01) | `crates/wm-governance/src/policy.rs` |
| Trust boundaries on data | Galaxy compartments (sandbox/production/secure) gate which galaxies a context may touch (`can_access_galaxy`, `can_write_galaxy`) | `crates/wm-mcp` context compartment fields |
| Rate/budget control | Dispatch `RateLimiter` + circuit breakers | `crates/wm-dispatch` |

### Checkpoint 2 — LLM

| ACS intent | v5 mechanism | Evidence |
|---|---|---|
| Govern model inference | Bicameral reasoning (left deterministic / right creative) with `InferenceRouter` (5 tiers, confidence cascading, token budgets, sensitivity detection) | `crates/wm-bicameral` |
| Prompt integrity | System prompt leakage policy rule (LLM07); prompt-injection probes in router | `crates/wm-governance/src/policy.rs` |
| Hallucination resistance | Bicameral consensus + `reasoning.bicameral` tools; misinformation rule (LLM09) | `crates/wm-bicameral` |
| Local model fallback | LlamaLeftHemisphere / BitNetRightHemisphere / OrtEmbedder — no external dependency required | GAP_ANALYSIS L1-L5 |

### Checkpoint 3 — State

| ACS intent | v5 mechanism | Evidence |
|---|---|---|
| Memory integrity | LMDB transactional writes; transaction snapshot/rollback tools; begin/commit/rollback semantics with destructive confirmation | `crates/wm-memory`, transaction tools (Aug 2026) |
| Context isolation | Compartment-based access control (sandbox/production/secure); per-user galaxy access | `crates/wm-mcp` Context compartment |
| Corruption recovery | LMDB integrity check, auto-repair, quarantine, map-size growth (18 tests) | 2026-08-05 hardening |
| Persistence durability | Karma chain + Gan Ying bus JSONL persistence; graceful shutdown flush | `crates/wm-governance`, server shutdown path |

### Checkpoint 4 — Tool execution

| ACS intent | v5 mechanism | Evidence |
|---|---|---|
| Pre-execution policy | `DharmaGate::evaluate(effects, ctx) -> ActionVerdict` — Observe / Advise / Correct / Intervene / Panic; homeostasis-adaptive strictness | `crates/wm-governance/src/dharma_gate.rs` |
| Effect declaration | Effect-typed dispatch (`EffectRow`, compile-time effect declarations); resource rules | `crates/wm-core` |
| Declared-vs-actual audit | **Karma ledger** — records declared effects per tool, tracks actuals, accumulates debt, batched flush, chain integrity | `crates/wm-governance/src/karma_ledger.rs` (E2E: `pipeline_karma_batched_e2e`) |
| Destructive action gates | Destructive-tool confirmation (rollback requires confirm); tool capability attestation (HMAC-signed manifests, trust scopes) | Aug 2026 safety features |
| Policy surface | `DharmaPolicy` — default/strict/permissive profiles, JSON-serializable, runtime-updatable via `PolicyEngine` | `crates/wm-governance/src/policy.rs` |

### Checkpoint 5 — Output

| ACS intent | v5 mechanism | Evidence |
|---|---|---|
| Output validation before leaving agent | Karma recording of every dispatched effect (post-execution verify); tool effectiveness reporting | `crates/wm-tools` (ToolsEffectivenessReportTool) |
| Data egress control | Tier-based egress policy (L2 `tier2_deny_unknown_egress` in v26 lineage); resource rules | `crates/wm-governance` |
| Audit trail for review | Karma ledger as append-only chain + RSI friction logging + Gnosis portals | `crates/wm-governance`, RSI phase 1-3 |

---

## 3. Policy-language correspondence

ACS expresses policy as standard YAML at each checkpoint. v5's Dharma rules are JSON-defined `PolicyRule`s today. The correspondence:

| ACS policy YAML element | v5 equivalent | Translation |
|---|---|---|
| `checkpoint: input/llm/state/tool/output` | Dharma tier (L0-L3) + effect class | Rule carries a tier; checkpoints map to effect categories (reads/writes/network/concurrency) |
| `action: allow/log/warn/throttle/block` | `ActionVerdict`: Observe / Advise / Correct / Intervene / Panic | Direct 1:1 severity ladder (v26 lineage: LOG→TAG→WARN→THROTTLE→BLOCK) |
| `condition: <policy expression>` | `PolicyRule` conditions over `EffectRow` + `Context` | Compile `condition` → effect predicates |
| `scope: agent/tool/galaxy` | Compartment access control + resource rules | Scope = galaxy compartment × tool |

A v5 adapter (`dharma_acs_bridge`) could:
- **Import**: parse ACS policy YAML → `DharmaPolicy` rules (so ACS-compliant policies run on v5 unchanged)
- **Export**: render `DharmaPolicy` → ACS YAML (so v5-deployed governance is inspectable by ACS tooling)
- **Report**: per-checkpoint coverage table, like the existing `OwaspComplianceReport`

---

## 4. Existing compliance surface (already shipped)

- **OWASP Agentic Top 10 mapping**: `OwaspAgentic` enum (LLM01-LLM10), `DharmaPolicy::owasp_coverage()`, `owasp_report()` with coverage percent — the pattern ACS mapping should mirror
- **Verdict ladder**: Observe→Panic with `blocks()` / `is_warning()` semantics — matches ACS action ladder
- **Attestation**: HMAC-signed tool manifests, trust scopes — ACS-adjacent provenance

---

## 5. Gaps & recommendations

**Status (2026-08-09)**: `wm-governance::acs` shipped — import/export/report implemented (`dharma.acs` tool, `acs-yaml` feature-gate) and this positioning doc published.

| Gap | Impact | Recommendation | Effort | Status |
|---|---|---|---|---|
| No ACS YAML import/export | Cannot participate in ACS ecosystem; policy portability absent | Build `dharma_acs_bridge` (import/export/report) | M | ✅ Done — `wm-governance::acs` + `dharma.acs` (5.6.0) |
| No published checkpoint-coverage table | Positioning asset missing — the June 5 competitive doc called this "defensively necessary" | Publish `docs/ACS_ALIGNMENT.md` (this doc) to the site; per-checkpoint coverage in the tool surface | S | ✅ Doc published; `dharma.acs report` covers the tool surface |
| Policy rules are JSON, not YAML | ACS standard is YAML; divergence complicates sharing | Support `serde_yaml` in `PolicyRule` ser/de (feature-gated) | S | ✅ Done — `acs-yaml` feature |
| Egress policy at L2 only | Output checkpoint thin | Complete `tier2_deny_unknown_egress` + add L3 output validation rules | M | ⬜ Open |

---

## 6. Positioning statement

> WhiteMagic v5 implements all five ACS checkpoints as a **local-first, self-contained runtime**: input validation and injection defense (Input), bicameral inference governance with local-model fallback (LLM), transactional LMDB memory with compartment isolation (State), Dharma policy gate + Karma declared-vs-actual ledger (Tool execution), and effect-recorded output with audit chains (Output). Where ACS is a specification, v5 is a running system — MIT-licensed, `forbid(unsafe_code)`, 0-warning, deployable air-gapped with no vendor dependency.

---

*Derived from the chronological read of WMdocs (Groups K/L: Microsoft Build 2026, ACS announcement Jun 2, 2026; competitive positioning Jun 5, 2026 — "The window is not closing on WhiteMagic's ideas. The window is closing on WhiteMagic's narrative.")*
