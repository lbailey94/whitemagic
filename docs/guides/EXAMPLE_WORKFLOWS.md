# Example Workflows

Real-world usage patterns showing how to combine WhiteMagic tools for common tasks.

---

## 1. Research Assistant

**Use case**: Deep research on a topic with memory persistence and ethical review.

```python
from whitemagic.tools.unified_api import call_tool

# 1. Discover available research tools
out = call_tool("list_ganas", search="research")
print("Research Ganas:", [g["id"] for g in out["details"]["ganas"]])

# 2. Start a research session
call_tool("dream_start")

# 3. Store research findings
call_tool(
    "create_memory",
    title="AI Safety: Key Papers",
    content="Anthropic's Constitutional AI (2022), DeepMind's Scalable Oversight (2023)",
    tags=["research", "ai-safety", "papers"],
    type="long_term",
)

# 4. Search for related work
out = call_tool("search_memories", query="AI alignment", limit=10)
for result in out["details"]["results"]:
    print(f"  {result['entry']['title']}: {result['score']:.2f}")

# 5. Ethical review before publishing
out = call_tool("evaluate_ethics", action="Publish research findings on AI safety")
print("Ethics check:", out["details"])

# 6. End session and consolidate
call_tool("dream_stop")
```

**Why this works**: Combines memory persistence, search, and ethical governance into a coherent research workflow.

---

## 2. Code Reviewer with Audit Trail

**Use case**: Review code changes with full audit trail and Karma tracking.

```python
# 1. Check system health
out = call_tool("gnosis", compact=True)
print("System status:", out["details"]["gnosis"]["status"])

# 2. Store the review context
call_tool(
    "create_memory",
    title="Code Review: PR #123",
    content="Reviewing authentication module refactor",
    tags=["code-review", "pr-123", "auth"],
    type="short_term",
)

# 3. Use capability matrix to find relevant tools
out = call_tool("capability.matrix")
security_tools = [t for t in out["details"]["tools"] if "security" in t.get("tags", [])]
print("Security tools:", [t["name"] for t in security_tools])

# 4. Check Karma ledger for side effects
out = call_tool("karma_report")
print("Recent side effects:", out["details"]["recent_entries"])

# 5. Store review findings
call_tool(
    "create_memory",
    title="Code Review Findings: PR #123",
    content="Approved with minor security concerns in token validation",
    tags=["code-review", "pr-123", "approved"],
    type="long_term",
)
```

**Why this works**: Uses Gnosis for health checks, capability matrix for tool discovery, and Karma for audit trails.

---

## 3. Data Analysis with Holographic Memory

**Use case**: Analyze data with persistent memory and 5D holographic coordinates.

```python
# 1. Check memory health
out = call_tool("gnosis")
galactic = out["details"].get("galactic", {})
print("Memory zones:", galactic.get("zones", {}))

# 2. Store analysis context in CORE zone (high priority)
call_tool(
    "create_memory",
    title="Q4 Sales Analysis",
    content="Analyzing Q4 2025 sales data for trends",
    tags=["analysis", "sales", "q4-2025"],
    type="long_term",
    zone="CORE",  # High-priority zone
)

# 3. Store intermediate results in INNER_RIM
call_tool(
    "create_memory",
    title="Q4 Sales: Preliminary Findings",
    content="15% increase in enterprise segment",
    tags=["analysis", "sales", "preliminary"],
    type="short_term",
    zone="INNER_RIM",
)

# 4. Search for related analyses
out = call_tool("search_memories", query="sales trends", limit=5)
for result in out["details"]["results"]:
    print(f"  {result['entry']['title']}")

# 5. Store final report in CORE
call_tool(
    "create_memory",
    title="Q4 Sales: Final Report",
    content="Enterprise +15%, SMB +8%, Consumer -3%. Recommend focus on enterprise.",
    tags=["analysis", "sales", "final", "q4-2025"],
    type="long_term",
    zone="CORE",
)
```

**Why this works**: Leverages the galactic memory map for priority-based storage, with automatic lifecycle management.

---

## 4. Multi-Agent Coordination

**Use case**: Coordinate multiple agents working on a shared project.

```python
# 1. Register this agent
call_tool(
    "agent.register",
    name="research-agent-1",
    capabilities=["research", "analysis", "writing"],
    metadata={"project": "ai-safety-survey"},
)

# 2. Check other active agents
out = call_tool("agent.list", only_active=True)
print("Active agents:", [a["name"] for a in out["details"]["agents"]])

# 3. Store shared context
call_tool(
    "create_memory",
    title="AI Safety Survey: Shared Outline",
    content="1. Introduction 2. Current Approaches 3. Open Problems 4. Future Directions",
    tags=["project", "ai-safety-survey", "shared"],
    type="long_term",
)

# 4. Send heartbeat to stay active
call_tool("agent.heartbeat", workload=0.3, current_task="writing-section-2")

# 5. Check agent trust scores
out = call_tool("agent.trust")
print("Trust scores:", out["details"])
```

**Why this works**: Uses the agent registry for coordination, with shared memory for context and trust scores for reliability.

---

## 5. Ethical Decision Making

**Use case**: Make ethical decisions with Dharma governance and Harmony monitoring.

```python
# 1. Check current Dharma profile
out = call_tool("gnosis")
dharma = out["details"].get("dharma", {})
print("Active profile:", dharma.get("profile"))

# 2. Evaluate a proposed action
out = call_tool(
    "evaluate_ethics",
    action="Deploy autonomous trading bot with $10k budget",
    context="Financial trading with real money",
)
print("Ethics assessment:", out["details"])

# 3. Check Harmony vector (7-dimensional health)
out = call_tool("harmony_vector")
print("Harmony:", out["details"]["vector"])

# 4. Switch to secure profile if needed
call_tool("set_dharma_profile", profile="secure")

# 5. Re-evaluate with stricter governance
out = call_tool(
    "evaluate_ethics",
    action="Deploy autonomous trading bot with $10k budget",
    context="Financial trading with real money",
)
print("Secure profile assessment:", out["details"])
```

**Why this works**: Combines Dharma governance with Harmony monitoring for comprehensive ethical oversight.

---

## 6. Performance Monitoring

**Use case**: Monitor system performance and tool health.

```python
# 1. Get full system snapshot
out = call_tool("gnosis", compact=False)
details = out["details"]

# 2. Check circuit breakers
breakers = details.get("circuit_breakers", {})
print("Open breakers:", [k for k, v in breakers.items() if v.get("state") == "OPEN"])

# 3. Check tool vitality
out = call_tool("vitality")
for gana, stats in out["details"]["reputation"].items():
    if stats.get("success_rate", 1.0) < 0.95:
        print(f"  {gana}: {stats['success_rate']:.2%} success rate")

# 4. Check anomaly detector
out = call_tool("anomaly.check")
print("Active anomalies:", out["details"]["anomalies"])

# 5. View metrics summary
out = call_tool("get_metrics_summary")
print("Metrics:", out["details"])
```

**Why this works**: Uses multiple monitoring tools for comprehensive system health visibility.

---

## Next Steps

- **[Quickstart](../../QUICKSTART.md)** — Get started in 5 minutes
- **[Use Cases](../design/USE_CASES.md)** — More detailed scenarios
- **[MCP Config Examples](./MCP_CONFIG_EXAMPLES.md)** — Client-specific setups
- **[Performance Benchmarks](https://whitemagic.dev/performance)** — Speed and reliability data
