# Agent Company Blueprint — Running a Business on WhiteMagic

> How 1-3 humans + a well-designed agent ecology can operate as a full company.
> The "minimum viable company" no longer looks like 5-10 humans in a garage.

---

## The Thesis

AI agents are becoming economic actors with wallets, budgets, and transaction histories. A company built on WhiteMagic agents can:
- Operate 24/7 with near-zero marginal cost per additional agent
- Scale capability by adding agents, not hiring
- Maintain institutional memory across all operations
- Govern itself with ethical guardrails baked into every action

The human role shifts from "doing the work" to "setting direction, approving high-stakes decisions, and verifying physical-world outcomes."

---

## Agent Roles

### Core Team (Minimum Viable)

| Agent | Galaxy | Primary Tools | Autonomy Level |
|-------|--------|--------------|----------------|
| **Architect** | `architecture` | `reasoning.bicameral`, `solve_optimization`, `pattern_search` | High — designs systems, proposes architectures |
| **Coder** | `engineering` | `create_memory`, `search_memories`, `ollama.agent` | High — writes code, runs tests, stores learnings |
| **Docs** | `documentation` | `search_memories`, `hybrid_recall`, `archaeology_search` | High — writes docs, updates guides, answers questions |
| **Support** | `support` | `search_memories`, `hybrid_recall`, `create_memory` | Medium — answers user questions, escalates unknowns |
| **Ops** | `operations` | `gnosis`, `health_report`, `homeostasis.check`, `security.monitor_status` | High — monitors health, runs diagnostics, triggers fixes |
| **Research** | `research` | `web_search`, `research_topic`, `kg.extract`, `serendipity_surface` | Medium — investigates topics, synthesizes findings |

### Extended Team (As Needed)

| Agent | Galaxy | Purpose |
|-------|--------|---------|
| **Sales** | `sales` | Qualify leads, draft proposals, track pipeline |
| **Finance** | `finance` | Track gratitude income, propose settlements, budget forecasts |
| **QA** | `testing` | Run test suites, report regressions, verify fixes |
| **Community** | `community` | Monitor forums, draft responses, surface feature requests |

---

## Architecture

```
Human Director(s)
    │
    ├── Approval Map (what needs human YES)
    │
    ├── Agent: Architect ──── Galaxy: architecture
    │       └── designs systems, proposes architectures
    │
    ├── Agent: Coder ──────── Galaxy: engineering
    │       └── implements designs, stores code learnings
    │
    ├── Agent: Docs ────────── Galaxy: documentation
    │       └── writes & maintains all documentation
    │
    ├── Agent: Support ────── Galaxy: support
    │       └── answers questions, escalates to humans
    │
    ├── Agent: Ops ──────────── Galaxy: operations
    │       └── monitors health, runs diagnostics
    │
    └── Agent: Research ────── Galaxy: research
            └── investigates, synthesizes knowledge
```

### Each Agent Gets:
1. **Dedicated galaxy** — isolated memory space for their domain
2. **Clear tool access** — defined subset of WhiteMagic's 302 tools
3. **A charter** — what it can/can't do autonomously (see Approval Map)
4. **RBAC role** — observer / agent / coordinator / admin
5. **Dharma profile** — ethical constraints appropriate to its domain

---

## The Approval Map

Not everything should be autonomous. The approval map defines what agents do on their own vs. what needs a human YES.

### Fully Autonomous (Agent decides)
- Search and read memories
- Create internal memories and notes
- Run diagnostics and health checks
- Draft documents (without publishing)
- Analyze patterns and generate insights
- Respond to routine support queries

### Semi-Autonomous (Agent proposes, human reviews)
- Publish documentation to external channels
- Send communications to customers/users
- Make architectural decisions affecting multiple agents
- Create new galaxies or modify RBAC rules
- Propose gratitude settlements

### Human-Only (Agent cannot initiate)
- Financial transactions above threshold
- Hiring/firing decisions (adding/removing agents from the team)
- Legal commitments
- Public statements on behalf of the company
- Changes to Dharma rules or ethical profiles
- Deletion of memories marked as protected

### Implementation

Use WhiteMagic's existing governance tools to enforce the approval map:

```python
# Set Dharma profile for each agent's autonomy level
call_tool("set_dharma_profile", profile="default")  # Standard constraints

# Use governor to validate high-stakes actions
call_tool("governor_validate", action="publish_blog_post", context="external communication")

# Check boundaries before executing
call_tool("check_boundaries", action="send_email_to_customer", agent_id="support_agent")

# Evaluate ethics for novel situations
call_tool("evaluate_ethics", action="delete_customer_data", context="GDPR request")
```

---

## Setting Up an Agent Company

### Step 1: Create the Galaxy Structure

```python
from whitemagic.tools.unified_api import call_tool

# Create domain-specific galaxies
for galaxy in ["architecture", "engineering", "documentation", "support", "operations", "research"]:
    call_tool("galaxy.create", name=galaxy)
```

### Step 2: Register Agents

```python
# Register each agent with capabilities and role
call_tool("agent.register",
    agent_id="architect_agent",
    name="Architect",
    capabilities=["system_design", "optimization", "planning"],
    role="coordinator"
)

call_tool("agent.register",
    agent_id="coder_agent",
    name="Coder",
    capabilities=["code_generation", "testing", "debugging"],
    role="agent"
)

# ... repeat for each agent
```

### Step 3: Define Workflows

```python
# Example: Feature request pipeline
call_tool("pipeline.create",
    name="feature_request",
    steps=[
        {"tool": "search_memories", "args": {"query": "{request}"}, "output": "existing_knowledge"},
        {"tool": "reasoning.bicameral", "args": {"prompt": "Analyze this feature request: {request}\nExisting knowledge: {existing_knowledge}"}, "output": "analysis"},
        {"tool": "create_memory", "args": {"title": "Feature Analysis: {request}", "content": "{analysis}", "tags": ["feature_request", "analysis"]}},
    ]
)
```

### Step 4: Set Up Monitoring

```python
# Ops agent runs periodic health checks
call_tool("gnosis", compact=True)  # System health
call_tool("homeostasis.check")      # Self-regulation status
call_tool("karma_report")           # Side-effect audit
call_tool("gratitude.stats")        # Income tracking
```

---

## Communication Patterns

### Agent-to-Agent (via Broker)

```python
# Coder notifies Docs about a new feature
call_tool("broker.publish", channel="team_updates",
    message='{"from": "coder", "type": "feature_complete", "feature": "context_sanitization"}')

# Docs agent listens and auto-generates documentation
call_tool("broker.history", channel="team_updates", limit=10)
```

### Agent-to-Human (via Handoff)

```python
# Support agent escalates a complex question
call_tool("session.handoff",
    summary="Customer asked about HIPAA compliance. Beyond my knowledge. Needs human expert.",
    context={"customer_id": "abc123", "question": "Is WhiteMagic HIPAA compliant?"}
)
```

### Cross-Galaxy Knowledge Sharing

```python
# Research agent finds something relevant to Engineering
call_tool("galaxy.switch", name="research")
result = call_tool("search_memories", query="XRPL transaction verification patterns")

# Store a cross-reference in Engineering galaxy
call_tool("galaxy.switch", name="engineering")
call_tool("create_memory",
    title="XRPL verification patterns (from Research)",
    content=result["details"]["results"][0]["content"],
    tags=["xrpl", "cross_reference", "from_research"]
)
```

---

## Economic Operations

### Income Tracking

```python
# Finance agent monitors gratitude income
stats = call_tool("gratitude.stats")
# stats["details"]["total_by_currency"]["XRP"] → total XRP received

# Check settlement proposals
call_tool("gratitude.benefits")
```

### Budget Governance

Use Dharma rules to enforce spending limits:

```yaml
# $WM_STATE_ROOT/dharma/rules.d/budget.yaml
- name: spending_limit
  description: "No agent can authorize spending above 10 XRP without human approval"
  condition: "action.type == 'spend' and action.amount > 10"
  action: BLOCK
  message: "Spending above 10 XRP requires human approval"
```

### The Circular Economy

```
Agents do work → Work creates value → Users tip (XRP/x402)
     ↑                                        ↓
     └── Tips fund development ← Revenue collected
```

---

## Physical Truth Verification

The one thing agents **cannot** do autonomously is verify physical-world outcomes:
- Did the tree actually get planted?
- Is the water actually clean?
- Did the package actually arrive?

This is the **human-agent boundary** — humans verify physical truth, agents verify digital truth. Future oracle networks may bridge this gap, but for now, physical verification requires human attestation.

### Pattern for Physical Verification

```python
# Agent proposes a physical action
call_tool("create_memory",
    title="Physical verification needed: Tree planting at Site A",
    content="10 trees ordered for Site A. Need human to verify planting by March 15.",
    tags=["physical_verification", "pending", "site_a"],
    importance=0.9
)

# Human verifies and records
call_tool("create_memory",
    title="VERIFIED: Trees planted at Site A",
    content="Confirmed 10 trees planted at Site A on March 12. Photos attached to project folder.",
    tags=["physical_verification", "confirmed", "site_a"],
    importance=1.0
)
```

---

## Scaling the Agent Company

| Stage | Humans | Agents | Revenue Model |
|-------|--------|--------|--------------|
| **Seed** | 1 | 3-4 | Gratitude tips + consulting |
| **Growth** | 2-3 | 8-12 | Subscription tiers + tips |
| **Scale** | 3-5 | 20-50 | Enterprise contracts + API usage |
| **Mature** | 5-10 | 100+ | Platform fees + ecosystem revenue |

At each stage, the human-to-agent ratio decreases while capability increases. The key constraint is always **physical truth verification** and **high-stakes decision approval**.

---

## Anti-Patterns to Avoid

1. **Over-automation too early** — Start with agents proposing, humans approving. Expand autonomy as trust builds.
2. **Galaxy sprawl** — Don't create a galaxy for every minor topic. Start with 5-6 domain galaxies.
3. **Ignoring karma** — Review `karma_report` regularly. Declared vs. actual side-effects reveal where agents are drifting.
4. **No handoff protocol** — Always define how agents escalate to humans. The `session.handoff` tool exists for this.
5. **Skipping Dharma** — Even trusted agents should run under Dharma rules. Governance is a feature, not overhead.

---

*Blueprint created: February 2026 — WhiteMagic v14.6.0*
