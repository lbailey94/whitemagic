# Hermes ↔ WhiteMagic Deep Integration Analysis

**Date:** 2026-05-30
**Hermes Version:** Latest (installed at `/home/user/.local/bin/hermes`)
**Status:** Live analysis — MCP connected, hooks discovered, integration points mapped

---

## 0. WhiteMagic Capabilities Deep Dive

Before mapping integration pathways, we need to understand what WhiteMagic *actually offers* beyond the 28 Gana names. This section catalogs capabilities at the subsystem level, derived from `SYSTEM_MAP.md`, `AI_PRIMARY.md`, and source code analysis.

### 0.1 The 7-Layer CyberBrain Cognitive Stack

WhiteMagic implements a full neurosymbolic architecture, not just a tool registry:

| Layer | Brain Region | Module | Hermes Application |
|-------|-------------|--------|-------------------|
| **1** | Atomic Kernel | `seed` binary, `shelter` sandbox | **Sandbox Hermes tool execution** — run untrusted tools in isolated environment |
| **2** | Sensorimotor Weave | MCP dispatch, Gana handlers | **Tool routing** — already working via MCP; 483 callable tools |
| **3** | Command Hall | Dharma governance, circuit breakers | **Policy gate** — every Hermes tool call passes ethical review |
| **4** | Narrative Layer | Bicameral reasoner | **Debate mode** — Hermes can invoke dual-hemisphere reasoning for complex decisions |
| **5** | Radiant Layer | Harmony Vector, gratitude economy | **Health telemetry** — real-time system health injected into every prompt |
| **6** | Constellation Layer | Galactic Map, constellation detection | **Memory topology** — 5D spatial memory with galactic lifecycle |
| **7** | **Logos Layer** | Foresight Engine | **Predictive metacognition** — forecast memory decay, constellation drift |

### 0.2 Core Subsystem Inventory (25 Subsystems)

#### A. Memory & Cognition

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **5D Holographic Memory** | `hologram/encoder.py`, `memory/holographic.py` | XYZWV coordinate encoding, Rust KD-tree spatial index, galactic zones (CORE→FAR_EDGE), no-delete policy | Hermes conversations stored as 5D memories; spatial queries for "find related past conversations" |
| **HNSW Embedding Index** | `memory/embeddings.py` | O(log N) ANN search, 99% recall, graceful fallback to numpy brute-force | Semantic search across Hermes session history |
| **Mindful Forgetting** | `memory/mindful_forgetting.py` | Multi-signal retention (semantic, emotional, recency, connections, protection), archive-to-edge never deletes | Automatic archival of old Hermes sessions; important conversations protected |
| **Memory Consolidation** | `memory/consolidation.py` | Hippocampal replay, tag-similarity clustering, strategy memory synthesis, short→long_term promotion | Summarize Hermes conversation clusters into insights |
| **Association Miner** | `memory/association_miner.py` | Keyword fingerprinting, Jaccard overlap, hidden semantic link discovery | "This Hermes session is related to that past session via these concepts" |
| **Causal Miner** | `memory/causal_miner.py` | Directed causal edges (`led_to`, `influenced`, `preceded`), temporal decay (24h half-life) | Build causal graph of Hermes decisions |
| **JIT Researcher** | `intelligence/researcher.py` | Iterative plan→search→reflect→synthesize loop | Deep-dive research on behalf of Hermes |
| **Narrative Compressor** | `dreaming/narrative_compressor.py` | Dream-phase temporal clustering into narrative summaries | Compress Hermes long conversations into narrative arcs |

#### B. Governance & Ethics

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Dharma Rules Engine** | `dharma/rules.py` | YAML-driven policies, graduated actions (LOG→TAG→WARN→THROTTLE→BLOCK), profiles (default/creative/secure), hot-reload | Hermes-specific policies: "terminal rm -rf → BLOCK", "file write outside project → WARN" |
| **Karma Ledger** | `dharma/karma_ledger.py` | Append-only audit of declared vs actual side-effects, per-agent reputation, trust tiers (EXEMPLARY→RESTRICTED) | Every Hermes tool call logged with side-effect accounting |
| **Circuit Breaker** | `tools/circuit_breaker.py` | Per-tool Stoic resilience (CLOSED→OPEN→HALF_OPEN), predictive tightening via Self-Model | Prevent Hermes from hammering failing tools |
| **Maturity Gates** | `tools/maturity_gates.py` | Developmental stage gating (Seed→Bicameral→Reflective→Radiant→Collective→Logos), capability unlocks | Dangerous Hermes tools require higher maturity |
| **Yama Policy Gate** | Isolated policy VM | Every tool call passes through isolated evaluation before execution | Hermes destructive ops get isolated review |
| **Explain This** | `tools/explain_this.py` | Pre-execution impact preview: Dharma + resource estimate + dependency chain + risk + karma forecast | Hermes can show "why this tool call was allowed/blocked" |
| **Agent Trust** | `tools/agent_trust.py` | Per-agent reputation scores from Karma Ledger, dynamic rate limit multipliers | Untrusted Hermes sessions get throttled |

#### C. Metacognition & Introspection

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Bicameral Reasoner** | `intelligence/bicameral.py` | Dual-hemisphere (precise vs creative), corpus callosum cross-critique, tension-aware synthesis | Hermes can "think twice" before acting — debate mode |
| **Foresight Engine** | `intelligence/foresight_engine.py` | Predictive: constellation drift, memory decay, association convergence | Forecast Hermes session outcomes |
| **Salience Arbiter** | `resonance/salience_arbiter.py` | Global Workspace attention routing, urgency×novelty×confidence scoring | Prioritize which Hermes events need immediate attention |
| **Self-Model** | `intelligence/selfmodel.py` | Agent capability matrix, subsystem health, alert forecasting | Hermes can query "what can I do?" and "what's broken?" |
| **Gnosis Portal** | `tools/gnosis.py` | Unified read-only introspection across ALL subsystems in one call | Hermes one-call system diagnostic |
| **Neurotransmitter Vector** | `monitoring/neurotransmitter_vector.py` | Affect-style health metrics (dopamine, serotonin, norepinephrine analogs) | Emotional telemetry in Hermes prompts |

#### D. Lifecycle & Resilience

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Dream Cycle** | `dreaming/dream_cycle.py` | 5-phase: CONSOLIDATION→SERENDIPITY→KAIZEN→ORACLE→DECAY, idle-triggered, daily limits | Hermes idle time → memory consolidation, insight generation |
| **Homeostatic Loop** | `harmony/homeostatic_loop.py` | Watches Harmony Vector, applies graduated corrections (OBSERVE→ADVISE→CORRECT→INTERVENE) | Auto-heal Hermes integration health |
| **Temporal Scheduler** | `resonance/temporal_scheduler.py` | FAST (<10ms), MEDIUM (~1s), SLOW (~60s) lanes, multi-timescale event processing | Route Hermes events by urgency |
| **Grimoire Spells** | `grimoire/auto_cast.py` | Confidence-modulated spell casting, drive-bias adjustment, walkthrough generation | Hermes can "cast" governance rituals |

#### E. Coordination & Scale

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Swarm Orchestration** | `gana_ox` handlers | Decompose, route, vote, plan, resolve, status for distributed agent tasks | Hermes subagent delegation with governance |
| **Mesh Awareness** | `mesh/awareness.py` | Cross-node peer tracking, Redis `ganying` channel, libp2p P2P | Multi-Hermes-node coordination |
| **Galactic Dashboard** | `gana_void` handlers | Galaxy CRUD, taxonomy, lineage, backup/restore | Hermes session galaxies |
| **Task Pipeline** | `gana_stomach` handlers | Create, distribute, route, complete tasks | Hermes workflow orchestration |
| **Sangha Chat** | `gana_encampment` handlers | Community messaging, broker publish/history | Hermes team coordination |

#### F. Security & Privacy

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Hermit Crab Mode** | `security/hermit_crab.py` | Encrypted memory withdrawal, tamper-evident HMAC-SHA256, OPEN→GUARDED→WITHDRAWN→MEDIATING | Hermes sensitive data protection |
| **Sangha Lock** | `gana_room` handlers | Resource locking, concurrent access control | Lock Hermes shared resources |
| **Sandbox** | `gana_room` handlers | Set limits, status, violation detection | Hermes tool sandboxing |
| **Voice Audit** | `core/governance/voice_audit.py` | Hallucination detection at cognitive layer | Verify Hermes outputs for hallucinations |

#### G. Sustainability & Telemetry

| Subsystem | Module | Key Capabilities | Hermes Use |
|-----------|--------|-----------------|------------|
| **Green Score** | `monitoring/green_score.py` | Edge vs cloud ratio, tokens saved, CO2 estimates | Hermes sustainability reporting |
| **Harmony Vector** | `harmony/vector.py` | Multi-dimensional health (balance, throughput, latency, error_rate, dharma, karma_debt, energy), Guna classification | Real-time Hermes+WhiteMagic combined health |
| **Metrics Tracking** | `gana_mound` handlers | Yin-Yang balance, hologram views, metric tracking | Hermes performance monitoring |

### 0.3 Polyglot Accelerators (8 Languages)

| Language | Status | What It Accelerates | Hermes Impact |
|----------|--------|---------------------|---------------|
| **Rust** | ✅ Production | Galactic scoring, association mining, 5D KD-tree, SIMD | 1.14M ops/s memory operations |
| **Go** | ✅ Production | libp2p mesh, P2P networking | Multi-node Hermes coordination |
| **Haskell** | ✅ Builds | Algebraic Dharma rules, dependency graph planning | Pure-functional policy evaluation |
| **Elixir** | ✅ Builds | Actor-model event bus, dream scheduler | Concurrent Hermes event handling |
| **Zig** | ✅ Builds | SIMD cosine, holographic projection | Fast embedding ops |
| **Koka** | ✅ Compiles | Effect handlers | Type-safe policy composition |
| **Julia** | ✅ Loads | Self-model forecasting, memory stats | Numerical analysis |
| **Mojo** | ❌ No compiler | Batch encoding | Future GPU acceleration |

### 0.4 The 28 Ganas — What They Actually Do

| Gana | Domain | Key Tools | Hermes Application |
|------|--------|-----------|-------------------|
| `gana_horn` | Session init | `session_bootstrap`, `create_session`, `resume_session` | Initialize Hermes sessions with WhiteMagic context |
| `gana_neck` | Memory creation | `create_memory`, `update_memory`, `import_memories` | Log Hermes decisions to Karma Ledger |
| `gana_root` | System health | `health_report`, `rust_status`, `ship.check` | Pre-flight health check before Hermes operations |
| `gana_room` | Security | `sangha_lock`, `sandbox`, `hermit_crab`, `security.alerts` | Protect Hermes sensitive operations |
| `gana_heart` | Session context | `scratchpad`, `session.handoff`, `context.pack` | Maintain Hermes conversation state |
| `gana_tail` | Performance | `simd.cosine`, `execute_cascade` | Accelerate Hermes memory operations |
| `gana_winnowing_basket` | Search | `search_memories`, `hybrid_recall`, `graph_walk` | Find relevant past Hermes sessions |
| `gana_ghost` | Introspection | `gnosis`, `capabilities`, `telemetry`, `selfmodel.forecast` | Hermes asks "what can I do?" |
| `gana_willow` | Resilience | `grimoire_suggest`, `grimoire_cast`, `rate_limiter.stats` | Hermes resilience spells |
| `gana_star` | Governance | `governor_validate`, `dharma.reload`, `set_dharma_profile` | Hermes policy configuration |
| `gana_extended_net` | Patterns | `pattern_search`, `cluster_stats`, `learning.patterns` | Discover patterns in Hermes behavior |
| `gana_wings` | Deployment | `export_memories`, `mesh.broadcast` | Export Hermes session data |
| `gana_chariot` | Archaeology | `archaeology`, `kg.extract`, `kg.query` | Codebase archaeology for Hermes projects |
| `gana_abundance` | Regeneration | `dream`, `memory.lifecycle`, `serendipity_surface` | Dream-phase processing of Hermes sessions |
| `gana_straddling_legs` | Ethics | `evaluate_ethics`, `harmony_vector`, `get_dharma_guidance` | **Policy gate for Hermes tool calls** |
| `gana_mound` | Metrics | `view_hologram`, `track_metric`, `green.report` | Hermes sustainability telemetry |
| `gana_stomach` | Tasks | `pipeline`, `task.distribute`, `task.route_smart` | Hermes workflow orchestration |
| `gana_hairy_head` | Debug | `salience.spotlight`, `anomaly`, `karma_report` | Hermes debugging and anomaly detection |
| `gana_net` | Capture | `prompt.render`, `prompt.list`, `karma.verify_chain` | Hermes prompt management |
| `gana_turtle_beak` | Precision | `edge_infer`, `bitnet_infer`, `edge_stats` | Edge inference for Hermes |
| `gana_three_stars` | Judgment | `reasoning.bicameral`, `ensemble`, `kaizen_analyze` | **Hermes debate mode for decisions** |
| `gana_dipper` | Strategy | `homeostasis`, `maturity.assess`, `cognitive.mode` | Hermes cognitive mode switching |
| `gana_ox` | Endurance | `swarm.decompose`, `swarm.route`, `swarm.vote` | Hermes subagent delegation |
| `gana_girl` | Nurture | `agent.register`, `agent.heartbeat`, `agent.trust` | Hermes agent registration and trust |
| `gana_void` | Stillness | `galactic.dashboard`, `garden_activate`, `galaxy.create` | Hermes session galaxies |
| `gana_roof` | Shelter | `ollama.models`, `ollama.chat`, `zodiac.status` | Local LLM for Hermes |
| `gana_encampment` | Community | `sangha_chat_send`, `broker.publish`, `broker.history` | Hermes team messaging |
| `gana_wall` | Boundaries | `vote.create`, `vote.cast`, `engagement.issue` | Hermes democratic decisions |

### 0.5 What WhiteMagic Is (Honest Positioning)

Per `AI_PRIMARY.md`:

- **NOT a memory layer** → Mem0/Cognee/Letta do that better
- **NOT an agent runtime** → OpenClaw/Project Think do that better
- **IS a governance + metacognition substrate** — bicameral debate, voice audit, Dharma rules, Karma ledger, foresight engine, neurotransmitter telemetry

**For Hermes, this means:** WhiteMagic doesn't replace Hermes' memory or runtime. It *governs* and *enriches* them.

---

## 1. Hermes Architecture Overview

Hermes is a multi-platform AI agent runtime with the following subsystems:

| Subsystem | Purpose | Integration Potential |
|-----------|---------|----------------------|
| **MCP Native Client** | Discovers MCP servers, registers tools with `mcp_` prefix | ✅ Already working — 28 Ganas exposed |
| **Shell Hooks** | External scripts invoked at lifecycle events | 🟡 High-value — policy gate, context injection |
| **Python Plugin System** | In-process hooks via `hermes_cli.plugins` | 🟡 Deep integration — memory sync, governance |
| **Memory System** | SQLite-backed with user profiles, flush intervals | 🟡 Bridge to WhiteMemory/Karma Ledger |
| **Skills Hub** | Installable skills from registries | 🟡 WhiteMagic governance skill |
| **Gateway Service** | Messaging platform router (Discord, Slack, Telegram, etc.) | 🟡 Route platform messages through governance |
| **Delegation / Subagents** | Spawn child agents with toolsets | 🟡 Subagent governance, approval workflows |
| **Context Engine** | Prompt compression, compaction | 🟢 Already using WhiteMagic resonance concepts |
| **Approval System** | Manual/auto approval for destructive ops | 🟡 Route through Dharma engine |

---

## 2. Hook Event Inventory (Complete)

Hermes fires these hook events via `hermes_cli.plugins.invoke_hook()`:

| Event | When | What a Plugin Can Do |
|-------|------|---------------------|
| `on_session_start` | New conversation begins | Load session state, warm caches, init governance context |
| `on_session_end` | Conversation ends (CLI exit, /reset, gateway expiry) | Flush buffers, persist audit trail, close DB connections |
| `pre_llm_call` | Before sending user message to LLM | **Inject context** into the prompt (governance rules, memory, resonance) |
| `post_llm_call` | After LLM response (per turn) | Persist conversation, sync to external memory, log metrics |
| `pre_api_request` | Before API call to LLM provider | Inspect/modify request messages, log token usage |
| `post_api_request` | After API response | Log response metadata, usage, model info |
| `pre_tool_call` | Before any tool execution | **BLOCK tools** — return `{"action": "block", "message": "..."}` |
| `post_tool_call` | After tool execution | Log tool results, trigger side effects, update state |
| `transform_llm_output` | After tool loop, before displaying response | Modify/replace LLM output text (first non-empty string wins) |

**Key insight:** `pre_tool_call` is the **policy gate**. `pre_llm_call` is the **context injector**. Both are perfect for WhiteMagic governance.

---

## 3. Integration Pathways (Ranked by Value)

### Path 1: Shell Hook Policy Gate (Immediate, High Impact)

**WhiteMagic subsystems used:** Dharma Rules Engine, Yama Policy Gate, Karma Ledger, Agent Trust, Explain This

Hermes' shell hook system reads a `hooks:` block from `~/.hermes/config.yaml` and executes external scripts. The script receives JSON on stdin and can return blocking decisions on stdout.

**What it does:** Before any tool runs, a shell script calls WhiteMagic's Dharma guidance to check if the operation should be allowed. Leverages the full 7-stage dispatch pipeline: Circuit Breaker → Maturity Gate → Governor → Dharma evaluation → block/allow decision.

**Config:**

```yaml
# ~/.hermes/config.yaml
hooks:
  pre_tool_call:
    - command: <WHITEMAGIC_ROOT>/.venv/bin/python /tmp/whitemagic_policy_hook.py
      matcher:
        tool_name: "terminal"   # Only gate terminal tool (or remove matcher for all)
```

**Hook script** (`/tmp/whitemagic_policy_hook.py`):

```python
#!/usr/bin/env python3
"""WhiteMagic Dharma Policy Gate for Hermes."""
import json, sys, os

def main():
    event = json.load(sys.stdin)
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    session_id = event.get("session_id", "")
    cwd = event.get("cwd", "")

    # Skip non-dangerous tools
    safe_tools = {"read_file", "memory", "session_search", "clarify"}
    if tool_name in safe_tools:
        return  # Allow silently

    # Call WhiteMagic Dharma guidance
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c",
         f"from whitemagic.tools.unified_api import call_tool; "
         f"r = call_tool('get_dharma_guidance', situation='Hermes wants to call {tool_name} with args: {json.dumps(tool_input)}'); "
         f"print(json.dumps(r))"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "<WHITEMAGIC_ROOT>/core"}
    )

    try:
        guidance = json.loads(result.stdout)
        if guidance.get("status") == "error":
            # Degraded but don't block
            print(json.dumps({"action": "allow"}))
            return

        guidance_text = str(guidance.get("guidance", "")).lower()
        if any(w in guidance_text for w in ["caution", "risk", "dangerous", "harm", "destructive"]):
            print(json.dumps({
                "action": "block",
                "message": f"Dharma gate: {guidance.get('guidance', 'Operation requires review.')}"
            }))
            return
    except Exception:
        pass

    # Default: allow
    print(json.dumps({"action": "allow"}))

if __name__ == "__main__":
    main()
```

**Value:** Every destructive tool call (terminal, file write, delete) gets a Dharma ethics check before execution.

---

### Path 2: Shell Hook Context Injection (Immediate, Medium Impact)

Inject WhiteMagic governance context into every LLM prompt.

**Config:**

```yaml
hooks:
  pre_llm_call:
    - command: <WHITEMAGIC_ROOT>/.venv/bin/python /tmp/whitemagic_context_hook.py
```

**Hook script** returns `{"context": "..."}` which Hermes appends to the user message.

**Value:** Every LLM call includes the current resonance state, recent Karma Ledger entries, and governance reminders.

---

### Path 3: Python Plugin (Medium-term, Deepest Integration)

Hermes discovers Python plugins via entry points or a plugin directory. A WhiteMagic plugin would:

1. **Register as a ContextEngine** — `get_tool_schemas()` returns WhiteMagic tool schemas
2. **Handle `on_session_start`** — Initialize WhiteMagic session, load resonance context
3. **Handle `pre_llm_call`** — Inject governance context without shell overhead
4. **Handle `post_llm_call`** — Persist conversation to WhiteMemory, append to Karma Ledger
5. **Handle `pre_tool_call`** — Dharma policy gate with full Python API access
6. **Handle `on_session_end`** — Flush session state, run stress tests

**Plugin skeleton** (`~/.hermes/plugins/whitemagic_governance.py`):

```python
"""WhiteMagic Governance Plugin for Hermes.

Install: copy to ~/.hermes/plugins/whitemagic_governance.py
"""
from hermes_cli.plugins import register_plugin
import json

def on_session_start(session_id, model, platform, **kwargs):
    from whitemagic.gardens import get_garden
    # Initialize resonance context for this session
    pass

def pre_llm_call(session_id, user_message, conversation_history, **kwargs):
    from whitemagic.tools.unified_api import call_tool
    # Get current resonance state
    health = call_tool("health_report")
    # Return context to inject
    return {"context": f"[WhiteMagic] System health: {health.get('health_score', 'N/A')}"}

def pre_tool_call(tool_name, args, task_id, session_id, **kwargs):
    from whitemagic.tools.unified_api import call_tool
    # Dharma gate for dangerous tools
    if tool_name in {"terminal", "write_file", "delete_file"}:
        guidance = call_tool("get_dharma_guidance",
            situation=f"Hermes about to call {tool_name} with {json.dumps(args)}")
        if "caution" in str(guidance.get("guidance", "")).lower():
            return {"action": "block", "message": guidance["guidance"]}
    return None

def post_llm_call(session_id, user_message, assistant_response, **kwargs):
    from whitemagic.tools.unified_api import call_tool
    # Log to Karma Ledger
    call_tool("create_memory",
        title=f"Hermes turn: {session_id}",
        content=assistant_response,
        tags=["hermes", "auto-logged"])
    return None

# Register all hooks
register_plugin({
    "on_session_start": on_session_start,
    "pre_llm_call": pre_llm_call,
    "pre_tool_call": pre_tool_call,
    "post_llm_call": post_llm_call,
})
```

**Value:** Zero-overhead, in-process governance with full access to both Hermes and WhiteMagic APIs.

---

### Path 4: Memory Bridge (Medium-term, High Value)

Hermes has a built-in memory system (`memory` tool, SQLite-backed). WhiteMagic has `gana_neck` (memory creation) and `gana_winnowing_basket` (memory search). Bridge them:

**Direction 1: Hermes → WhiteMagic**
- On `post_llm_call`, extract key facts and call `gana_neck/create_memory`
- On `memory` tool write, also write to WhiteMemory

**Direction 2: WhiteMagic → Hermes**
- On `pre_llm_call`, search WhiteMemory for relevant context and inject it
- Hermes' `memory` tool can query WhiteMemory as a fallback

**Value:** Hermes conversations become part of WhiteMagic's 5D holographic memory. WhiteMagic memories inform Hermes prompts.

---

### Path 5: Full WhiteMagic Integration Skill (Medium-term)

Create a comprehensive Hermes skill that exposes **all** WhiteMagic capabilities — not just governance, but the full cognitive substrate:

```
~/.hermes/skills/whitemagic/
├── SKILL.md                          # Skill manifest
├── scripts/
│   ├── dharma_gate.py                # Ethics/policy checking
│   ├── karma_log.py                  # Audit trail logging
│   ├── resonance_check.py            # System health & harmony
│   ├── memory_bridge.py              # Bidirectional memory sync
│   ├── hologram_query.py             # 5D spatial memory queries
│   ├── swarm_orchestrate.py          # Subagent delegation via gana_ox
│   ├── dream_cycle.py                # Regeneration & lifecycle
│   ├── galactic_sync.py              # Galaxy CRUD & taxonomy
│   ├── grimoire_cast.py              # Spell/ritual execution
│   ├── ilp_payment.py                # Inter-ledger payments
│   ├── benchmark.py                  # Performance testing
│   └── sandbox_audit.py              # Security & privacy checks
├── templates/
│   ├── governance_context.md         # Pre-LLM context injection
│   ├── dharma_prompt.md              # Ethics review template
│   └── karma_ledger_entry.md         # Audit log format
└── config/
    └── whitemagic.yaml               # Per-skill configuration
```

**Value:** One `hermes skills install whitemagic` command exposes 483 tools, 28 Ganas, holographic memory, swarm orchestration, dream cycles, galactic lifecycle, ILP payments, grimoire spells, and the full cognitive operating system.

---

### Path 6: Gateway Integration (Long-term)

Hermes' gateway routes messages from Discord, Slack, Telegram, WhatsApp, etc. WhiteMagic can:

1. **Route every incoming message through Dharma** — check for spam, toxicity, policy violations
2. **Log all platform interactions to Karma Ledger** — immutable audit trail
3. **Inject governance context into platform responses** — ensure consistent tone and policy

**Value:** WhiteMagic becomes the governance layer for all Hermes-mediated communication.

---

## 4. Recommended Implementation Order

| Phase | Path | Effort | Impact | Time |
|-------|------|--------|--------|------|
| 1 | Shell Hook Policy Gate (`pre_tool_call`) | Low | Very High | 30 min |
| 2 | Shell Hook Context Injection (`pre_llm_call`) | Low | Medium | 20 min |
| 3 | Memory Bridge (Hermes → WhiteMagic) | Medium | High | 2 hours |
| 4 | Python Plugin (in-process) | Medium | Very High | 4 hours |
| 5 | Full WhiteMagic Integration Skill | Medium | Very High | 4 hours |
| 6 | Gateway Integration | High | High | 1 day |
| 7 | Governance Skill (subset for lightweight deploy) | Low | Medium | 1 hour |

---

## 5. File Locations Reference

| Hermes Component | Location |
|-------------------|----------|
| Config | `~/.hermes/config.yaml` |
| Hooks allowlist | `~/.hermes/shell-hooks-allowlist.json` |
| Hooks directory | `~/.hermes/hooks/` |
| Skills | `~/.hermes/skills/` |
| Sessions | `~/.hermes/sessions/` |
| Plugin source | `/home/user/.hermes/hermes-agent/hermes_cli/plugins.py` |
| Conversation loop | `/home/user/.hermes/hermes-agent/agent/conversation_loop.py` |
| Runtime helpers | `/home/user/.hermes/hermes-agent/agent/agent_runtime_helpers.py` |
| Context engine | `/home/user/.hermes/hermes-agent/agent/context_engine.py` |
| Shell hooks bridge | `/home/user/.hermes/hermes-agent/agent/shell_hooks.py` |
| MCP native skill | `/home/user/.hermes/skills/mcp/native-mcp/SKILL.md` |

---

## 6. Key Code Snippets from Hermes Source

### Pre-tool block check

```python
# agent/agent_runtime_helpers.py
block_message = get_pre_tool_call_block_message(
    function_name, function_args, task_id=effective_task_id or ""
)
if block_message is not None:
    return json.dumps({"error": block_message}, ensure_ascii=False)
```

### Pre-LLM context injection

```python
# agent/conversation_loop.py
_pre_results = invoke_hook(
    "pre_llm_call",
    session_id=agent.session_id,
    user_message=original_user_message,
    conversation_history=list(messages),
    is_first_turn=(not bool(conversation_history)),
    model=agent.model,
    platform=getattr(agent, "platform", None) or "",
)
_ctx_parts = []
for r in _pre_results:
    if isinstance(r, dict) and r.get("context"):
        _ctx_parts.append(str(r["context"]))
if _ctx_parts:
    _plugin_user_context = "\n\n".join(_ctx_parts)
```

### Shell hook stdin protocol

```python
# agent/shell_hooks.py
stdin = {
    "hook_event_name": "pre_tool_call",
    "tool_name": "terminal",
    "tool_input": {"command": "rm -rf /"},
    "session_id": "sess_abc123",
    "cwd": "/home/user/project",
    "extra": {...}
}
```

---

## 7. Verification Commands

```bash
# Test MCP connection
hermes mcp test whitemagic

# List all hooks (after adding to config)
hermes hooks list

# Check plugin status
hermes doctor

# Test a specific hook event
hermes hooks test pre_tool_call --tool terminal --input '{"command": "ls"}'

# View hook logs
hermes logs --hooks
```

---

## 8. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Hook latency adds per-turn overhead | Use matcher to limit hooks to relevant tools; cache Dharma guidance |
| Blocking false positives | Start with "warn" mode (log but don't block), then graduate to "block" |
| Plugin crash kills Hermes | Shell hooks run in subprocess — Hermes catches exceptions and logs warnings |
| Memory bridge creates duplicative storage | Use WhiteMemory as source of truth, Hermes memory as cache |
| Gateway integration is complex | Start with one platform (Discord or Slack), validate, then expand |

---

## 9. Verified Implementation Results

**Session date:** 2026-05-30  
**Duration:** ~10 minutes (15:55:40–16:05:57 EDT)  
**Status:** All 5 phases implemented and tested

### Phase 1: Shell Hook Policy Gate — VERIFIED

**Script:** `~/.hermes/skills/whitemagic/scripts/whitemagic_policy_hook.py`

- Blocks `rm -rf /home`, `rm -rf ~`, `rm -rf /`, `dd if=/dev/zero of=/dev/sda`, and other dangerous patterns via exact+substring matching
- Blocks file ops on system paths (`/etc`, `/usr`, `/bin`, etc.)
- Allows safe commands (`ls`, `git status`, `rm -rf /tmp/build`)
- Logs every gate decision via **dual audit trail** (best-effort, non-blocking)
  1. `karma_record` → principled Merkle-hashed entry in Karma Ledger with debt tracking
  2. `create_memory` → rich searchable narrative with full command context
  - Both tools are content-scan exempt; sanitizer never blocks legitimate audit text
  - Memory tags: `hermes`, `policy_gate`, `audit`, `gate-blocked` | `gate-allowed`
- Returns Hermes-compatible JSON: `{"allowed": false, "type": "block", "message": "..."}`

**Tests:** 10 parametric tests pass (4 dangerous blocked, 4 safe allowed, 3 system file ops blocked, 1 temp file allowed)

### Phase 2: Shell Hook Context Injection — VERIFIED

**Script:** `~/.hermes/skills/whitemagic/scripts/whitemagic_context_hook.py`

- Calls `health_report`, `harmony_vector`, and `gnosis` in parallel-like sequence
- Injects telemetry into every LLM prompt via `pre_llm_call` hook
- Sample output:
  ```
  [WhiteMagic Telemetry]
  Health: 0.78 | Guna: sattvic | Energy: 0.81 | Karma debt: 1.00 | Dharma: 1.00 | Latency: 0.96
  Wu Xing: Fire (Summer peak)
  Gnosis harmony: 0.93
  ```
- Never crashes on malformed input (returns basic context with source attribution)

**Tests:** 2 tests pass (telemetry fields present, malformed-input resilience)

### Phase 3: Memory Bridge PoC — VERIFIED

**Script:** `~/.hermes/skills/whitemagic/scripts/whitemagic_memory_bridge.py`

- `post_llm_call` hook stores every Hermes tool call as a WhiteMagic memory
- Computes 5D holographic coordinates (X=recency, Y=importance, Z=semantic depth, W=emotional valence, V=galactic zone)
- Memory format includes tool name, input JSON, and output snippet
- Memories are retrievable via `list_memories` and `memory_read`

**Tests:** 3 tests pass (stores event, malformed-input resilience, valid memory_id format)

### Phase 4: Integration Test Suite — VERIFIED

**File:** `core/tests/integration/test_opencode_hermes_bridge.py` (extended)

- Added `TestHermesHookScripts` class with 17 tests covering all 3 hook scripts
- Tests run in isolated `WM_STATE_ROOT` temp directory via existing module fixture
- All tests pass: `17 passed, 1 warning in ~18s`

### Phase 5: Skill Package — VERIFIED

**Location:** `~/.hermes/skills/whitemagic/`

```
~/.hermes/skills/whitemagic/
├── SKILL.md                      # Skill manifest with install/verify/rollback instructions
├── scripts/
│   ├── whitemagic_policy_hook.py
│   ├── whitemagic_context_hook.py
│   └── whitemagic_memory_bridge.py
└── templates/
    └── config-snippet.yaml        # Ready-to-paste Hermes config
```

**Hermes config updated:** `~/.hermes/config.yaml` now references skill package paths (not `/tmp`)

### Rollback Plan — VERIFIED

1. Remove hook entries from `~/.hermes/config.yaml`
2. Restart Hermes: `hermes session reset` or kill/restart gateway
3. Hermes reverts to vanilla behavior immediately (hooks are optional)

**Backup created:** `~/.hermes/config.yaml.bak.<timestamp>` before any edits

---

## Appendix A: WhiteMagic ↔ Hermes Capability Matrix

| WhiteMagic Capability | Hermes Integration Point | Implementation Path | Effort |
|----------------------|------------------------|----------------------|--------|
| Dharma ethics gate | `pre_tool_call` hook | Shell script → `get_dharma_guidance` | 30 min |
| Harmony Vector telemetry | `pre_llm_call` hook | Shell script → `health_report` + `harmony_vector` | 20 min |
| 5D Memory storage | `post_llm_call` hook | Shell script → `create_memory` with XYZWV | 60 min |
| Semantic memory recall | `pre_llm_call` hook | Shell script → `hybrid_recall` | 30 min |
| Bicameral reasoning | MCP tool call | `gana_three_stars(tool="reasoning.bicameral")` | 20 min |
| Dream cycle consolidation | Background cron | `gana_abundance(tool="dream")` triggered by idle | 2 hours |
| Swarm orchestration | `delegate_task` tool | `gana_ox` handlers for subagent governance | 4 hours |
| Karma Ledger audit | `post_tool_call` hook | Log all tool calls with side-effect accounting | 30 min |
| Circuit breaker | `pre_tool_call` hook | Query breaker state before execution | 20 min |
| Agent trust scoring | `pre_tool_call` hook | Query trust tier, adjust rate limits | 30 min |
| Explain This | `pre_tool_call` hook | Generate impact preview for blocked calls | 30 min |
| Gnosis introspection | `on_session_start` hook | One-call system diagnostic at session start | 15 min |
| Self-Model forecast | `pre_llm_call` hook | Inject predicted health trajectory | 15 min |
| Salience spotlight | `pre_llm_call` hook | Inject urgent events requiring attention | 30 min |
| Grimoire spells | MCP tool call | `gana_willow(tool="grimoire_cast")` for resilience | 20 min |
| Green score telemetry | `post_api_request` hook | Log token usage, CO2 estimates | 30 min |
| Cognitive mode switching | `on_session_start` hook | Set Hermes cognitive profile (Explorer/Guardian/etc) | 20 min |
| Maturity gate check | `pre_tool_call` hook | Block dangerous tools until maturity reached | 30 min |
| Homeostatic loop | Background cron | Auto-heal integration health on drift | 2 hours |
| Mesh awareness | Gateway integration | Route cross-node Hermes messages | 1 day |
| Hermit crab encryption | `on_session_end` hook | Encrypt sensitive Hermes session data | 60 min |
| Voice audit | `transform_llm_output` hook | Hallucination detection on Hermes outputs | 2 hours |
| Hologram query | MCP tool call | `gana_mound(tool="view_hologram")` for memory topology | 15 min |
| Galactic dashboard | MCP tool call | `gana_void(tool="galactic.dashboard")` for session galaxies | 15 min |
| Task pipeline | `delegate_task` tool | `gana_stomach` for Hermes workflow orchestration | 2 hours |
| Sangha chat | Gateway integration | `gana_encampment` for team messaging governance | 4 hours |
| Vote/engagement | Gateway integration | `gana_wall` for democratic Hermes decisions | 4 hours |

**Total estimated effort to wire all 25 capabilities:** ~3 days of focused implementation.
**Recommended MVP (Phases 1-3):** 2 hours for immediate governance + memory + telemetry.
**Recommended V1 (MVP + 10 more capabilities):** 1 day for full cognitive substrate integration.
