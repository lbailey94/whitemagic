# WhiteMagic ↔ OpenCode / Hermes Integration Strategy

**Date:** 2026-05-30
**Status:** Draft — ready for test-driven refinement
**Audience:** AI agents, human developers

---

## 1. Guiding Principle: Governance Substrate, Not Product

WhiteMagic does not compete with OpenCode or Hermes. It is a **pluggable governance and metacognition layer** that any MCP-compatible agent runtime can consume.

OpenCode and Hermes are the **execution engines**. WhiteMagic is the **audit trail, policy gate, and forecasting substrate** wrapped around them.

---

## 2. Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Runtime Layer                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │ OpenCode │   │  Hermes  │   │  Windsurf│  (etc.)       │
│  │ (ACP/IDE)│   │(ACP/msg) │   │ (proprietary)│           │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│       │              │              │                        │
│       └──────────────┼──────────────┘                      │
│                      MCP stdio / HTTP                       │
│                         │                                   │
│              ┌──────────┴──────────┐                       │
│              │   WhiteMagic MCP     │                       │
│              │   Server (lean)      │                       │
│              │   28 Gana meta-tools │                       │
│              └──────────┬──────────┘                       │
│                         │                                   │
│       ┌─────────────────┼─────────────────┐               │
│       │                 │                 │               │
│  ┌────┴────┐      ┌────┴────┐      ┌────┴────┐           │
│  │ Karma   │      │ Dharma  │      │ Foresight│           │
│  │ Ledger  │      │ Engine  │      │  (Brier) │           │
│  └─────────┘      └─────────┘      └─────────┘           │
│                                                             │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐            │
│  │ Voice   │      │  PRAT   │      │ Memory  │            │
│  │ Audit   │      │ Router  │      │ Manager │            │
│  └─────────┘      └─────────┘      └─────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Path 1: MCP Server Hardening (Immediate)

`core/whitemagic/run_mcp_lean.py` already registers 28 Gana meta-tools. The goal is to expose a **curated governance surface** that OpenCode and Hermes can discover and invoke.

### 3.1 Exposed Tool Categories

| Category | Ganas | Use Case for OpenCode/Hermes |
|----------|-------|------------------------------|
| **Audit** | `gana_ghost` (metrics), `gana_three_stars` (wisdom) | Log every agent action to Karma Ledger |
| **Policy** | `gana_dipper` (governance), `gana_straddling_legs` (ethics) | Pre-flight Dharma check before dangerous tool calls |
| **Forecasting** | `gana_abundance` (dream cycle) | Retrieve prescience track record for decision calibration |
| **Memory** | `gana_neck` (memory), `gana_winnowing_basket` (consolidation) | Persist agent learnings across sessions |
| **Search** | `gana_chariot` (codebase nav) | Deep project archaeology when agent is lost |

### 3.2 Connection Methods

**stdio (default, for IDE integration):**
```bash
# OpenCode
opencode mcp add --name whitemagic --command "python -m whitemagic.run_mcp_lean"

# Hermes (via MCP tool gateway)
hermes tools add mcp --command "python -m whitemagic.run_mcp_lean"
```

**HTTP (for remote / messaging gateway):**
```bash
python -m whitemagic.run_mcp_lean --http --port 8770
```

---

## 4. Path 2: Hermes Deep Integration (Medium-term)

Hermes has a **skills system** with lifecycle hooks (`pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`) and a deepening user model. This maps cleanly to WhiteMagic subsystems.

### 4.1 Hermes Plugin Design

```python
# ~/.hermes/plugins/whitemagic_governance.py
"""Hermes plugin that wires WhiteMagic governance into the agent loop."""

from hermes.plugins import Plugin

class WhiteMagicGovernance(Plugin):
    async def on_session_start(self, session):
        # Initialize Karma Ledger for this session
        self.karma = await wm.karma_ledger.create_session(session.id)

    async def pre_llm_call(self, messages, tools):
        # Dharma gate: block dangerous tool patterns
        check = await wm.dharma.check(tools)
        if check.blocked:
            return {"blocked": True, "reason": check.reason}
        return None

    async def post_llm_call(self, response, tool_calls):
        # Log every tool call to Karma Ledger
        for tc in tool_calls:
            await self.karma.append(tc)

    async def pre_tool_call(self, tool_name, args):
        # Voice Audit: trigger bicameral debate for high-risk ops
        if tool_name in {"write_file", "execute_code", "shell"}:
            audit = await wm.voice_audit.debate(tool_name, args)
            if audit.veto:
                return {"vetoed": True, "reason": audit.reasoning}
        return None
```

### 4.2 Hermes ACP Mode

Hermes already supports ACP (Agent Client Protocol). When running `hermes acp`, WhiteMagic's MCP server can be registered as an **external tool provider**, giving the Hermes agent access to 28 governance primitives within any ACP-compatible IDE.

---

## 5. Path 3: OpenCode Context Injection (Low-friction)

OpenCode reads project-local `AGENTS.md` for behavioral guardrails. WhiteMagic can generate or manage a **governance-aware `AGENTS.md`** that injects:

- Dharma policy context
- PRAT routing rules
- Epistemic hygiene guidelines (honest labeling of claims)
- Karma Ledger audit expectations

This requires **no code changes** to OpenCode — just better context files in the workspace.

### 5.1 Example Auto-Generated `AGENTS.md` Section

```markdown
## WhiteMagic Governance Layer (auto-injected)

This project is monitored by WhiteMagic governance primitives:

- **Karma Ledger**: Every file edit and terminal command is logged for audit.
- **Dharma Rules**: High-risk operations (deletes, executes) require explicit justification.
- **Epistemic Labels**: Claims in comments/docs must be labeled: Proven / Promising / Contested / Speculative / Mythopoetic.
- **Prescience Check**: Before asserting a prediction, query `gana_abundance` for track-record calibration.
```

---

## 6. Testing Strategy

### 6.1 Baseline Verification

1. Run existing MCP E2E tests to confirm 28 Gana registration works.
2. Verify stdio transport launches in < 1 second.
3. Verify HTTP transport responds on `127.0.0.1:8770/mcp`.

### 6.2 Integration Tests (New)

| Test | Target | What It Proves |
|------|--------|----------------|
| `test_opencode_stdio_connect` | OpenCode | `opencode mcp add` + `tools/list` returns 28 Ganas |
| `test_hermes_mcp_discover` | Hermes | `hermes tools` sees WhiteMagic governance tools |
| `test_karma_ledger_append` | Both | Tool invocation produces immutable audit entry |
| `test_dharma_policy_gate` | Both | Blocked tool call returns structured veto response |
| `test_forecast_retrieval` | Both | Agent can query prescience track record via MCP |

### 6.3 Test Harness

```bash
# In-process MCP server test (no subprocess)
cd core && python -m pytest tests/integration/test_mcp_e2e.py -v

# Full suite baseline
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 -q

# Doc drift + version checks
python scripts/check_doc_drift.py
python scripts/check_versions.py
```

---

## 7. What NOT to Do

| Avoid | Why |
|-------|-----|
| Build a WhiteMagic IDE | Product trap — misaligned with governance-substrate positioning |
| Fork/modify OpenCode or Hermes | Fragile — upstream changes break custom patches |
| Chase Antigravity integration | Proprietary, breaking, vertically integrated into Google Cloud |
| Ship generated artifacts with local paths | Repo hygiene risk |
| Make unsupported capability claims | Every claim must be benchmarked or labeled |

---

## 8. Immediate Next Steps

1. **Verify baseline**: Run existing MCP E2E tests (`test_mcp_e2e.py`) — confirm 28 Ganas + tool calls pass.
2. **Curate governance surface**: Decide which 5-10 Ganas are highest-value for agent runtimes (not all 28).
3. **Write integration doc**: Short `docs/integrations/OPENCODE_HERMES_MCP_SETUP.md` with copy-pasteable config.
4. **Add integration tests**: New test file `tests/integration/test_opencode_hermes_bridge.py` simulating an external MCP client.
5. **Test against real OpenCode**: Install OpenCode locally, add WhiteMagic MCP server, verify tool discovery.

---

**Bottom line**: WhiteMagic's honest niche is not competing with agent runtimes — it is making them *accountable*. MCP is the perfect seam for that.
