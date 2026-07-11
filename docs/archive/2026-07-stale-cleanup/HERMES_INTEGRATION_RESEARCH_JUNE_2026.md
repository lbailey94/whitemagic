# Hermes Integration Research — June 2026 Update

**Date:** 2026-06-04
**Research scope:** Internal repo state + external competitive landscape + Hermes architecture evolution
**Previous baseline:** `HERMES_DEEP_INTEGRATION.md` (2026-05-30)
**Status:** Research complete — plan requires material revision

---

## Executive Summary

The May 30 integration plan is **architecturally sound but operationally stale**. Hermes shipped a massive refactor (v0.15.0, "The Velocity Release") just 2 days before our analysis, collapsing `run_agent.py` from 16,083 lines to 3,821 across 14 modules. Our source code references are now outdated. More importantly, Hermes formalized two first-class plugin types — **Memory Provider** and **Context Engine** — that are the *native* integration points for what our plan proposed to do via shell hooks. A new academic system (Arbiter-K, April 2026) has published metrics on governance-first architecture that directly compete with WhiteMagic's positioning. The competitive landscape has shifted from "no one does governance substrate" to "multiple well-funded projects converging on the same idea."

**Bottom line:** The integration is more viable than ever (Hermes' plugin surface expanded massively), but WhiteMagic's differentiation must be sharper, and the implementation path should use Hermes' native plugin types rather than shell scripts.

---

## 1. Hermes Evolution (May 28 → June 4, 2026)

### What Changed

| Aspect | May 30 Analysis | June 4 Reality | Impact on Plan |
|--------|----------------|----------------|----------------|
| **Core agent file** | `run_agent.py` monolith (16K lines) | Split into 14 `agent/*` modules (3.8K lines) | Our file references in Section 6 are stale |
| **Hook system** | Inferred from `conversation_loop.py` | Documented in architecture guide; **shell hooks** are a confirmed production feature | Shell hook plan is valid |
| **Plugin types** | Generic Python plugins via entry points | **Memory Provider** and **Context Engine** are first-class, single-select plugin types | Plan should use these instead of shell hooks |
| **Plugin surface** | Hooks + commands | Expanded: `register_command`, `dispatch_tool`, `pre_tool_call` blocking, `transform_tool_result`, `transform_terminal_output`, dashboard tabs | Much richer integration possible |
| **Dashboard** | Not mentioned | Extensible web dashboard with custom tabs/widgets | WhiteMagic galaxy viz could be a dashboard plugin |
| **Skill bundles** | Not mentioned | One slash command loads a whole workflow | WhiteMagic governance could be a skill bundle |
| **MCP catalog** | Not mentioned | Nous-approved MCP catalog with interactive picker | WhiteMagic should be listed |
| **Transport layer** | Not mentioned | Pluggable `agent/transports/` ABC (Anthropic, ChatCompletions, ResponsesApi, Bedrock) | HTTP mode integration possible |
| **Version** | Inferred latest | v0.15.1 (2026.5.29) | 493 commits behind; update recommended before integration |

### Critical New Architecture

**Plugin System (from `hermes-agent.nousresearch.com/docs/developer-guide/architecture`)**

Three discovery sources:
1. `~/.hermes/plugins/` (user)
2. `.hermes/plugins/` (project)
3. pip entry points

Plugins register tools, hooks, and CLI commands through a context API.

**Two specialized plugin types (single-select — only one of each can be active):**
- **Memory Provider** (`plugins/memory/`) — Replaces Hermes' default SQLite memory backend
- **Context Engine** (`plugins/context_engine/`) — Replaces the default context compressor

**This is the native integration path.** Instead of shell hooks that intercept events, WhiteMagic should register as:
- A **Memory Provider** plugin — replaces Hermes' SQLite memory with WhiteMemory
- A **Context Engine** plugin — injects governance context into prompt assembly
- A **generic plugin** — registers `pre_tool_call` blocking hooks and slash commands

### What the Plan Got Right

- `pre_tool_call` blocking is confirmed as a production feature (v0.11.0+).
- Shell hooks are a supported, documented feature.
- The 9 hook events we cataloged are accurate (documented in the architecture guide).
- Hermes' gateway has 20+ platform adapters (our gateway integration path is valid).

### What the Plan Got Wrong

- **File references are stale.** `conversation_loop.py`, `agent_runtime_helpers.py` — these were extracted into `agent/` modules.
- **Shell hooks are the wrong default.** For memory and context injection, the native plugin types are superior. Shell hooks should be reserved for quick policy gates and users who don't want to install a full plugin.
- **No mention of Context Engine plugin type.** This is the *correct* way to inject governance context into prompts, not via `pre_llm_call` shell hooks.
- **No mention of Memory Provider plugin type.** This is the *correct* way to bridge memory, not via `post_llm_call` shell scripts.
- **No mention of dashboard plugins.** WhiteMagic's galaxy visualization (`apps/site/` galaxy viz, new in `835c7ff`) could be a Hermes dashboard tab.
- **No mention of skill bundles.** WhiteMagic's 28 Gana workflow could be packaged as a `hermes skills` bundle.

---

## 2. Competitive Landscape Update

### The Memory Layer (Not WhiteMagic's Arena)

| System | Position | Integration Pattern with Agent Runtimes | WhiteMagic Overlap |
|--------|----------|------------------------------------------|-------------------|
| **Mem0** | Managed memory layer | 3-step loop: retrieve → enrich prompt → store. 4 scoping dimensions (user/agent/app/session). v3 removed graph layer; uses entity linking instead. | **Low.** Mem0 is memory-only; WhiteMagic is governance + metacognition. But Mem0's integration pattern (retrieve/enrich/store) is the standard WhiteMagic should follow for its memory bridge. |
| **Letta** | Full agent framework | Agent edits its own memory via tool calls (`core_memory_replace`, `archival_memory_search`). Memory tiers: core (context), archival (vector), recall (history), filesystem. | **Medium.** Letta is an agent runtime + memory; WhiteMagic is a substrate. Letta's self-editing memory is more sophisticated than WhiteMagic's current `memory` tool. |
| **Cognee** | Knowledge graph engine | Entity extraction pipeline → graph. 10+ search types (GRAPH_COMPLETION, RAG_COMPLETION, TEMPORAL, CYPHER). Vector+graph+relational hybrid. | **Medium.** Cognee's graph search is comparable to WhiteMagic's Knowledge Graph + Association Miner. Cognee is more mature (production API, 70+ companies). |
| **Graphiti (Zep)** | Bi-temporal fact graph | EpisodicNodes → EntityNodes → CommunityNodes. Every fact edge is bi-temporal with validity timestamps. | **Low.** Graphiti's temporal graph is unique; WhiteMagic has causal miner but no explicit temporal validity model. |

**Key insight:** All four competitors are primarily **memory systems**. WhiteMagic's explicit positioning as "NOT a memory layer" (per `AI_PRIMARY.md`) is validated. The competitive space for "governance + metacognition substrate" is less crowded.

### The Governance Layer (WhiteMagic's Actual Arena)

| System | Position | Architecture | Metrics Published | WhiteMagic Overlap |
|--------|----------|--------------|-------------------|-------------------|
| **OpenAI Codex CLI** | Code agent with safety | Two-layer: Sandbox (workspace-write/full-access) + Approval policy (auto/on-request/never). `auto_review` with reviewer agent. Risk levels: low/medium/high/critical. | None public | **High.** Codex's approval policy is functionally equivalent to WhiteMagic's Dharm a gate. Codex has reviewer agents (WhiteMagic has bicameral reasoner). Codex's sandbox mode is comparable to WhiteMagic's `shelter`. |
| **Anthropic Claude Code** | Code agent with auto mode | Two-layer defense: Input prompt-injection probe + Output transcript classifier (Sonnet 4.6). Fast single-token filter → chain-of-thought if flagged. 93% of manual prompts accepted anyway. | None public | **Medium.** Claude Code's auto mode is a classifier-based policy gate. WhiteMagic's Dharma is rule-based + LLM guidance. Different approaches, same problem. |
| **Microsoft Agent Governance Toolkit** | Cross-platform governance | Hooks: `before_tool_call`, `after_tool_call`, `on_delegation`, `on_policy_violation`. SDK-level vs external governance. Filed proposals across: GitHub Copilot, Google ADK, OpenAI Agents SDK, PydanticAI, MCP servers. | None public | **Very High.** This is a direct competitor. Microsoft has filed governance proposals across the entire ecosystem. Their hook patterns are identical to WhiteMagic's planned Hermes hooks. |
| **Arbiter-K / ArbiterOS** (Cure Lab, April 2026) | Academic governance-first architecture | Governance-first execution: Probabilistic Processing Unit (LLM) demoted to non-privileged proposal generator. Deterministic symbolic kernel validates all environment-altering instructions. Semantic ISA with 5 logical cores. Security Context Registry. Instruction Dependency Graph. Active taint propagation. | **76-95% unsafe interception. 92.79% absolute gain over native policies.** OpenClaw and NanoBot benchmarks. | **Extremely High.** Arbiter-K is WhiteMagic's architecture described in academic language. The PPU = bicameral reasoner. Symbolic kernel = Dharma/Yama dispatch pipeline. Security Context Registry = Karma Ledger. Instruction Dependency Graph = Tool Dependency Graph. Active taint propagation = Causal Miner + Association Miner. |

### The Verdict

WhiteMagic is **not alone** in the governance substrate space. In 2026:
- **OpenAI** has a production two-layer security system with reviewer agents.
- **Anthropic** has classifier-based auto-approval with prompt injection defense.
- **Microsoft** has a cross-platform governance toolkit with ecosystem proposals.
- **Academia** (Arbiter-K) has published rigorous metrics on governance-first architecture.

**WhiteMagic's differentiation must be:**
1. **Cultural taxonomy** — The 28 Gana / Lunar Mansion system is symbolically unique. No competitor has a cultural grounding layer.
2. **5D holographic memory with galactic lifecycle** — The CORE→FAR_EDGE rotation with no-delete policy is architecturally distinct from vector DB + graph hybrids.
3. **Polyglot accelerators** — 8-language acceleration cores (Rust, Go, Haskell, Elixir, Zig, Koka, Julia, Mojo) is unmatched.
4. **Bicameral reasoner** — Dual-hemisphere debate with corpus callosum cross-critique. No competitor ships this as a callable primitive.
5. **Dream cycle** — 5-phase regeneration (CONSOLIDATION→SERENDIPITY→KAIZEN→ORACLE→DECAY) with idle-triggered processing.
6. **Karma Ledger as ethical accounting** — Not just audit logging; per-agent reputation with trust tiers and side-effect tracking.
7. **Locally runnable, vendor-neutral, MIT-licensed** — OpenAI, Anthropic, and Microsoft solutions are vendor-specific or cloud-dependent.

---

## 3. Internal State Update

| Metric | May 30, 2026 | June 4, 2026 | Change |
|--------|-------------|--------------|--------|
| **Test baseline** | 2,243 passed, 67 skipped | **2,379 passed, 0 skipped** | +136 tests, all skips resolved |
| **Test runtime** | ~40s | **~31s** | Faster, despite more tests |
| **Doc drift** | Pass | **Pass** | Stable |
| **Hermes hooks installed** | None | **None** | No progress on integration |
| **Integration code written** | 0 lines | **0 lines** | Still architecture-only |
| **New CODEX pipeline** | Did not exist | **v0.2.0 stub** (planned Q3 2026) | New but not ready |
| **Galaxy subsystem** | Existed | **Expanded** (galaxy_api, galaxy_miner, Rust archive) | More mature |
| **Repo commits since May 30** | — | 6 commits (grants, essay frameworks, core updates, site refresh, CODEX extractor) | Active development elsewhere |

### New Relevant Capability: CODEX Pipeline

`core/whitemagic/codex/__init__.py` defines a 5-stage pipeline:
1. **extract** — Parse raw corpora into normalized documents
2. **chunk** — Hierarchical chunking with speaker-turn preservation
3. **embed** — Vector embeddings
4. **index** — Graph construction, Louvain clustering, community detection
5. **export** — `sphere-nodes.json`, search indexes

**Status:** Stubs only. Subdirectories (`chunk/`, `embed/`, `index/`, `export/`) are empty. Planned Q3 2026.

**Integration relevance:** If completed, this pipeline could extract knowledge from Hermes session transcripts and feed it into WhiteMemory's Knowledge Graph. But it's not ready yet.

---

## 4. Revised Integration Plan

### What to Keep from the May 30 Plan

- **The 25-capability matrix** (Appendix A) is still valid — all 25 capabilities map to real Hermes extension points.
- **The hook event inventory** (Section 2) is confirmed by official docs.
- **The phased implementation order** is still roughly correct, but the *mechanism* for each phase changes.

### What to Change

#### Change 1: Use Native Plugin Types for Deep Integration

| Old Plan (May 30) | New Plan (June 2026) | Rationale |
|-------------------|----------------------|-----------|
| Memory bridge via `post_llm_call` shell script | **Memory Provider plugin** (`~/.hermes/plugins/memory/whitemagic/`) | Hermes supports single-select memory providers. This replaces Hermes' SQLite memory entirely. |
| Context injection via `pre_llm_call` shell script | **Context Engine plugin** (`~/.hermes/plugins/context_engine/whitemagic/`) | Hermes supports single-select context engines. This replaces the default compressor. |
| Policy gate via `pre_tool_call` shell script | **Generic plugin** with `pre_tool_call` hook + `transform_tool_result` | Still valid, but should be a proper plugin, not a shell script. |
| Galaxy viz not mentioned | **Dashboard plugin** for Hermes web UI | Hermes dashboard supports custom tabs. WhiteMagic's galaxy visualization (`apps/site/` galaxy) could be a tab. |
| Skill packaging as directory tree | **Skill bundle** (`hermes skills install whitemagic`) | Hermes v0.15.0 supports skill bundles — one slash command loads a workflow. |

#### Change 2: Update All File References

Replace stale references:
- `conversation_loop.py` → `agent/run_agent.py` (3.8K lines, still the entry point)
- `agent_runtime_helpers.py` → `agent/` modules (prompt_builder, context_engine, etc.)
- `shell_hooks.py` → Documented in architecture guide + `gateway/hooks.py`
- `plugins.py` → `hermes_cli/plugins.py` (still valid, but plugin types expanded)

#### Change 3: Prioritize Based on Competitive Landscape

| Capability | Competitive Threat | WhiteMagic Advantage | Priority |
|------------|-------------------|----------------------|----------|
| Policy gate | **High** (Codex, Claude Code, Microsoft toolkit all have this) | Dharma rules + cultural taxonomy (Ganas) | P0 |
| Memory bridge | **Medium** (Mem0, Letta, Cognee all do this better) | 5D holographic + galactic lifecycle | P1 |
| Context injection | **Medium** (Letta's memory tiers, Mem0's retrieval) | Harmony Vector + neurotransmitter telemetry + Wu Xing | P1 |
| Bicameral reasoning | **Low** (no competitor ships this) | Unique primitive | P2 |
| Dream cycle | **Low** (no competitor) | Unique primitive | P2 |
| Dashboard plugin | **None** (no competitor in this space) | Galaxy viz differentiation | P3 |

#### Change 4: Add Metrics and Benchmarks

Arbiter-K published **76-95% unsafe interception** and **92.79% gain over native policies**. WhiteMagic needs comparable metrics. Before claiming "governance substrate superiority," we must:

1. Define a test harness for policy gate accuracy (true positives, false positives, false negatives).
2. Benchmark against Hermes' native `approval.py` dangerous command detection.
3. Benchmark against a no-governance baseline.
4. Publish results in the integration doc.

#### Change 5: Update Hermes First

Hermes is **493 commits behind** (v0.15.1 from May 29). The plugin architecture may have evolved further. Before writing integration code:

```bash
hermes update  # Update to latest
```

Then re-read the architecture docs to verify plugin types and APIs.

---

## 5. New Implementation Order (Revised)

| Phase | Task | Effort | Plugin Type | Competitive Value |
|-------|------|--------|-------------|-------------------|
| 0 | `hermes update` to latest | 5 min | — | Required before any code |
| 1 | Generic plugin: `pre_tool_call` policy gate | 45 min | Generic plugin + hooks | **High** — direct response to Codex/Claude/Microsoft |
| 2 | Generic plugin: `post_tool_call` Karma audit | 30 min | Generic plugin + hooks | **High** — append-only audit trail |
| 3 | Context Engine plugin: governance context injection | 60 min | Context Engine (single-select) | **Medium** — replaces default compressor |
| 4 | Memory Provider plugin: WhiteMemory bridge | 2 hours | Memory Provider (single-select) | **Medium** — replaces SQLite backend |
| 5 | Dashboard plugin: Galaxy visualization | 2 hours | Dashboard tab | **Low** — differentiation |
| 6 | Skill bundle: `hermes skills install whitemagic` | 3 hours | Skill bundle | **Medium** — one-command install |
| 7 | Test harness + benchmark | 2 hours | — | **Critical** — metrics against Arbiter-K |
| 8 | Gateway integration (Discord/Slack) | 1 day | Gateway hooks | **Medium** — platform governance |

**Total MVP (Phases 0-3):** ~2.5 hours for policy gate + audit + context injection.
**Total V1 (Phases 0-6):** ~1.5 days for full cognitive substrate integration.
**Total with benchmarks (Phases 0-7):** ~2 days.

---

## 6. Risk Assessment (Updated)

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Arbiter-K or Microsoft toolkit becomes the de facto standard** | **High** | Double down on differentiation: cultural taxonomy (Ganas), 5D memory, polyglot accelerators, bicameral reasoner. These have no equivalent in competing systems. |
| **Hermes plugin API changes after we write code** | Medium | Pin to a specific Hermes version in the skill manifest. Use defensive imports. Monitor Hermes changelog. |
| **Context Engine and Memory Provider are single-select** | Medium | If user has another Context Engine plugin active, WhiteMagic can't be selected. Document this limitation. Offer shell hook fallback. |
| **Policy gate latency** | Medium | Cache Dharma guidance for repeated tool patterns. Use fast rule-based pre-filter before LLM-based guidance. |
| **False positives in policy gate** | Medium | Start in "warn" mode (log but don't block). Graduate to "block" after calibration. Provide override mechanism. |
| **Dashboard plugin requires Hermes web UI** | Low | Not critical path. Fallback: CLI-only integration with `hermes` commands. |

---

## 7. Recommendations

1. **Do NOT implement the May 30 plan as written.** The shell-hook approach is valid for quick demos, but the native plugin types are the correct long-term integration path.
2. **Update `HERMES_DEEP_INTEGRATION.md`** with the revised plan. Keep the capability matrix, but rewrite the implementation paths to use Memory Provider / Context Engine / generic plugin types.
3. **Add a competitive analysis section** to the integration doc. Cite Arbiter-K, Microsoft toolkit, Codex, and Claude Code explicitly. Show how WhiteMagic is differentiated.
4. **Build a benchmark harness before claiming superiority.** The May 30 plan says "immediate protection" but has no metrics. Define what "protection" means and measure it.
5. **Update Hermes before writing code.** 493 commits behind means the API surface may have drifted.
6. **Consider a two-tier integration:**
   - **Tier 1 (shell hooks):** For users who want quick setup without installing a plugin. 30 minutes.
   - **Tier 2 (native plugins):** For users who want full cognitive substrate. 1.5 days.

---

## Appendix: Sources

### Internal
- `HERMES_DEEP_INTEGRATION.md` (2026-05-30) — Previous baseline
- `SYSTEM_MAP.md` — WhiteMagic architecture
- `AI_PRIMARY.md` — WhiteMagic positioning and competitors
- `core/whitemagic/codex/__init__.py` — CODEX pipeline v0.2.0
- Git log since May 30: `52bb95d` through `f633f2c`

### External — Hermes
- `https://hermes-agent.nousresearch.com/docs/developer-guide/architecture` — Official architecture guide
- `https://github.com/NousResearch/hermes-agent/releases/tag/v2026.5.28` — v0.15.0 release notes (The Velocity Release)

### External — Competitors
- `https://github.com/mem0ai/mem0/blob/HEAD/skills/mem0/references/architecture.md` — Mem0 architecture v3
- `https://codepointer.substack.com/p/agent-memory-systems-and-knowledge` — Agent memory systems comparison (Letta, Mem0, Graphiti, Cognee)
- `https://docs.cognee.ai/` — Cognee API documentation
- `https://arxiv.org/html/2504.19413` — Mem0 academic paper

### External — Governance
- `https://developers.openai.com/codex/llms-full.txt` — Codex security and approval policies
- `https://www.anthropic.com/engineering/claude-code-auto-mode` — Claude Code auto mode
- `https://github.com/microsoft/agent-governance-toolkit` — Microsoft Agent Governance Toolkit (referenced in search)
- `https://arxiv.org/html/2604.18652` — Arbiter-K: Governance-First Execution Architecture (Cure Lab, April 2026)
