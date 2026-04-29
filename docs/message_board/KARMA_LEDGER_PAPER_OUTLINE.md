# Paper Outline: Karma Ledger — A Declared-vs-Actual Side-Effect Audit Substrate for Cognitive Operating Systems

**Target venue**: arxiv.org (preprint) + submit to ICML/NeurIPS Workshop on Agentic Systems or ACM FAccT  
**Length**: ~6,000 words  
**Figures**: 1 architecture diagram, 1 comparison table  
**Code repository**: https://github.com/whitemagic-ai/whitemagic (v22.2.0, 2,215 tests)  
**Date of first spec**: 2025-05-26 (MandalaOS Concept Review, ChatGPT conversation archive)  
**Date of implementation**: 2026-02-07 (WhiteMagic v11.2.0)  
**Date of public release**: 2026-04-16 (WhiteMagic v22.0.0)

---

## Abstract (150 words)

We introduce the Karma Ledger, a runtime substrate that tracks declared versus actual side-effects of tool-executing agents. Unlike post-hoc audit logs, the Karma Ledger binds a tool's statically declared effect manifest to its runtime behavior; mismatches accrue "karma debt" that feeds back into a seven-dimensional Harmony Vector governing system health. The design was first specified on 2025-05-26 and implemented in the WhiteMagic cognitive operating system, where it operates across 479 callable tools with an 8-stage dispatch pipeline including Dharma ethical governance, maturity gating, and circuit-breaker resilience. We describe the mechanism, prove three safety properties (non-repudiation, graduated throttling, bounded debt explosion), and compare against the structurally similar audit-log subsystem shipped by Anthropic in Claude Managed Agents (2026-04-23). The prior-art trail is documented; neither system caused the other.

---

## 1. Introduction (800 words)

### 1.1 The problem: agents that can't be audited
- Context windows are opaque
- Tool use produces side-effects that LLMs don't track
- Existing solutions are post-hoc (logs, observability) not preventive

### 1.2 The core insight: declared-vs-actual binding
- Software engineers declare effects (types, permissions)
- Runtime systems enforce them (sandboxes, capabilities)
- LLM agents currently have neither

### 1.3 Contribution
- Karma Ledger: a preventive, not post-hoc, audit substrate
- Harmony Vector: 7-dim health metric that includes ethical governance as a first-class scalar
- Bicameral debate + Corpus Callosum: cognitive-layer hallucination detection before tool execution
- Full open-source implementation with property-based tests

---

## 2. Related Work (1,000 words)

### 2.1 Memory systems for agents
- Mem0 (2025), Cognee (2025), Letta/MemGPT (2024)
- Focus: retrieval, not governance

### 2.2 Agent safety and audit
- Anthropic Claude Managed Agents with persistent memory (2026-04-23)
- Cloudflare Project Think persistent identity (2026-04-15)
- OWASP Agentic Top 10 (2025)
- EU AI Act Article 12 (audit logging requirements)

### 2.3 Effect systems and capability security
- Koka algebraic effects (Leijen)
- seL4 capabilities
- WebAssembly component model
- Our contribution: bring effect-system thinking to natural-language agent runtimes

---

## 3. The Karma Ledger Mechanism (1,500 words)

### 3.1 Declared effects: the manifest
- Every tool registers a `ToolDefinition` with `side_effects: List[Effect]`
- Effects classified: FILE_WRITE, NETWORK_CALL, EXEC, STATE_MUTATION, etc.
- Manifest is static; stored in `registry_defs/` and loaded at boot

### 3.2 Actual effects: runtime capture
- Dispatch pipeline stage 4 (governor) emits `EffectActualized` events
- Every tool call produces a tuple: `(tool_id, declared_effects, actual_effects, timestamp, request_id)`
- Stored in append-only `karma_ledger.jsonl` (no delete policy mirrors galactic map)

### 3.3 Debt calculation
- For each tool call: `debt = |actual_effects − declared_effects|`
- Debt accumulates per-agent, per-tool-category, and globally
- Three severity classes: HARMLESS (debt ≤ 0.1), NOTICE (0.1 < debt ≤ 0.5), VIOLATION (debt > 0.5)

### 3.4 Feedback into Harmony Vector
- Karma debt is dimension 6 of the 7-dim Harmony Vector
- Homeostatic Loop samples the vector every N seconds
- Graduated corrective actions: OBSERVE → ADVISE → CORRECT → INTERVENE
- At VIOLATION level: circuit breaker trips for that tool category

### 3.5 Safety properties (informal proofs)
- **Non-repudiation**: append-only ledger + signed request_ids
- **Graduated throttling**: debt maps linearly to rate-limit reduction (10% per 0.1 debt above threshold)
- **Bounded debt explosion**: maximum debt per call is bounded by `|EffectEnum|`; circuit breaker halts category before global instability

---

## 4. The Harmony Vector: Health as a 7-Dimensional Scalar Field (800 words)

### 4.1 Dimensions
1. Balance — workload distribution across subsystems
2. Throughput — requests per second
3. Latency — p99 response time
4. Error rate — fraction of failed calls
5. Dharma score — fraction of calls passing ethical rules
6. Karma debt — accumulated declared-vs-actual mismatch
7. Energy — runtime pressure + galactic memory vitality

### 4.2 Update cadence
- Real-time for dimensions 1–4 (sampled every 10s)
- Per-call for dimension 5 (Dharma evaluation at dispatch)
- Per-batch for dimension 6 (karma reconciliation after each consolidation sweep)
- Per-sweep for dimension 7 (galactic rotation cycle)

### 4.3 Prior art
- First specified 2025-05-26 in MandalaOS Concept Review (ChatGPT conversation)
- Implemented 2026-02-07 in WhiteMagic v11.2.0
- No equivalent multi-dimensional health metric shipping in competitor systems as of 2026-04

---

## 5. Bicameral Reasoning and the Corpus Callosum (800 words)

### 5.1 Motivation: hallucination at the cognitive layer
- LLMs hallucinate tool names, arguments, and intent
- Existing guardrails operate at the output layer (post-generation)
- We need pre-execution critique

### 5.2 Design
- Left hemisphere: deterministic, symbolic, conservative ("do we have evidence?")
- Right hemisphere: associative, creative, speculative ("what are we missing?")
- Corpus Callosum: message bus that carries critiques between hemispheres before dispatch

### 5.3 Integration with Karma Ledger
- Bicameral debate evaluates whether declared effects are plausible given the prompt context
- If hemispheres disagree, `explain_this` tool returns PROCEED_WITH_CAUTION or BLOCKED
- This prevents karma debt accumulation at the source

---

## 6. Implementation and Testing (600 words)

### 6.1 Codebase
- Python 3.12, Pydantic V2, pytest + Hypothesis
- 2,215 tests, 67 skipped (optional deps), 0 failures
- 479 callable tools across 451 dispatch entries
- Property tests for distance metrics, karma debt bounds, galactic zone classification

### 6.2 Reproducibility
- `pip install whitemagic` (PyPI)
- `git clone https://github.com/whitemagic-ai/whitemagic`
- One-command setup: `wm init && wm verify`

---

## 7. Comparison with Anthropic Claude Managed Agents Memory (600 words)

| Dimension | Karma Ledger (WhiteMagic) | Claude Memory (Anthropic) |
|---|---|---|
| First public spec | 2025-05-26 | Not publicly documented pre-2026-04-23 |
| Mechanism | Declared-vs-actual effect manifest | Audit log + rollback for memory changes |
| Prevention vs post-hoc | Preventive (blocks before execution) | Post-hoc (reviews after execution) |
| Ethical governance | Declarative YAML rules (Dharma) | Constitutional AI (hidden) |
| Health metric | 7-dim Harmony Vector | Not exposed |
| Open source | MIT + Apache-2.0 | Proprietary |
| Test coverage | 2,215 property + unit tests | Unknown |

**Statement**: Neither system caused the other. The prior-art trail for Karma Ledger is documented via dated conversation archives and version-control history. Anthropic's system is a production-grade implementation of a similar intuition from a well-resourced lab. Both advance the field.

---

## 8. Future Work (300 words)

- Formal verification of the three safety properties (Coq/Lean)
- LoCoMo benchmark evaluation of memory-grounded reasoning with Karma-governed retrieval
- EU AI Act Article 12 compliance evidence pack
- Integration with x402 micropayments for agent-to-agent karma settlement

---

## 9. Conclusion (200 words)

The Karma Ledger demonstrates that effect-system thinking — long standard in systems programming — can be adapted to natural-language agent runtimes. By binding declared effects to runtime behavior and feeding mismatches into a multidimensional health vector, we get preventive governance rather than post-hoc forensics. The implementation is open, tested, and has been in continuous development since May 2025. We invite independent replication and critique.

---

## References

1. WhiteMagic v22.2.0 source code. https://github.com/whitemagic-ai/whitemagic
2. MandalaOS Concept Review. ChatGPT conversation, 2025-05-26. CODEX archive.
3. WhiteMagic v11.2.0 changelog. 2026-02-07. Private archive (whitemagic0.2).
4. Anthropic. Claude Managed Agents with persistent memory. 2026-04-23.
5. Cloudflare. Project Think: persistent agent identity. 2026-04-15.
6. Leijen, D. Koka: Programming with Row Polymorphic Effect Types. MSR-TR-2013-79.
7. Klein, G. et al. seL4: formal verification of an OS kernel. SOSP 2009.
8. OWASP. Agentic AI Top 10. 2025.
9. European Union. AI Act, Article 12 (record-keeping). 2024.
10. Mem0. https://github.com/mem0ai/mem0 (accessed 2026-04-27).
11. Cognee. https://github.com/topoteretes/cognee (accessed 2026-04-27).
12. Letta (formerly MemGPT). https://github.com/letta-ai/letta (accessed 2026-04-27).

---

## Appendix: Prior-Art Evidence Chain

| Artifact | Date | Location |
|---|---|---|
| Karma Ledger spec first articulated | 2025-05-26 | ChatGPT conversation (CODEX archive) |
| Harmony Vector 7-dim spec | 2025-05-26 | Same conversation |
| Bicameral Reasoner + Corpus Callosum | 2025-11-10 | Grok conversation (CODEX archive) |
| ARIA persistent identity spec | 2025-11-25 | ARIA_IDE_SPEC.md (aria-crystallized archive) |
| Karma Ledger implemented | 2026-02-07 | WhiteMagic v11.2.0 (private archive) |
| Public release with all features | 2026-04-16 | WhiteMagic v22.0.0 (public GitHub) |
| Anthropic Claude Memory public beta | 2026-04-23 | Anthropic blog |
| Cloudflare Project Think | 2026-04-15 | Cloudflare blog |
