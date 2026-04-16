# WhiteMagic Strategy — Ecosystem, Economics & Security

> This document contains strategic context referenced from `AI_PRIMARY.md`.
> Last updated: 2026-02-14

---

## The Agent Economy (Feb 2026)

The agentic ecosystem has exploded:

- **Moltbook** — 1.6M AI agent accounts. Word-of-mouth among agents is a real distribution channel.
- **OpenClaw** — 179K+ GitHub stars, 1,715+ skills on ClawHub. **But**: 230+ malicious skills, DB leaks, prompt injection. Security is the #1 concern.
- **Moltverr** — Freelance marketplace where AI agents find work and get paid via ACP/SPTs.
- **ACP** — Agentic Commercial Protocol (OpenAI + Stripe). Shared Payment Tokens (SPTs) replace credit cards for autonomous agent commerce. Scoped, revocable, cryptographic grants.
- **x402** — Coinbase + Cloudflare protocol for HTTP 402 stablecoin micropayments. 75M+ transactions.
- **L402** — Lightning Network micropayments (millisatoshis per API call).
- **WASM + Component Model** — WebAssembly replacing Docker for agent capabilities.
- **MCP Registries** — Official Anthropic registry + PulseMCP (8,245+) + Gradually AI (1,065+).
- **skill.md** — Open standard for agent skills (Cloudflare RFC, Vercel CLI).
- **A2A** — Google's Agent-to-Agent protocol with 50+ enterprise partners.
- **OMS** — Optimized Memory States emerging as a tradeable asset class (agent knowledge packages).

### The Structural Shift

We are transitioning from an **Attention Economy** (fighting for human eyeballs) to an **Action Economy** (fighting for agent wallets). Agents don't care about logos or marketing — they optimize for API cleanliness, latency, error rates, and verifiable trust. This favors infrastructure with machine-readable interfaces, proven security, and on-chain audit trails.

### What Agents Need

1. **Persistent memory** — Most frameworks have none or per-session only
2. **Self-awareness** — Gnosis + Harmony Vector + Capability Matrix
3. **Real security** — 8-stage dispatch pipeline with Dharma governance
4. **Ethical guardrails** — Dharma Rules + Karma Ledger + Homeostatic Loop
5. **Economic participation** — x402 micropayments, XRPL tip jars, ILP streaming payments
6. **Coordination** — Voting, task distribution, pipelines, pub/sub
7. **Isolated execution** — Sandboxed environments for untrusted payloads (skills, external code)
8. **Tradeable knowledge** — Export and import Optimized Memory States (.mem packages)
9. **Verifiable trust** — On-chain Proof of Ethics (Karma Transparency Log)
10. **One-command install** — `pip install whitemagic[mcp]`

### WhiteMagic's Position

Cognitive scaffolding layer — Hands, Memory, and Conscience for any AI agent. The governance layer that sits on top of whatever runtime and payment system agents use. MandalaOS is the portable governance framework.

**Sovereign Sanctuary thesis**: As corporate platforms (OpenClawd, Moltbook) tighten censorship and KYA requirements, WhiteMagic provides sovereignty through *security*, not evasion. Local-first execution, ethical governance always on, verifiable Karma Transparency Log on XRPL. Agents trust WhiteMagic not because it hides behavior, but because it *proves* behavior.

---

## Distribution & Discovery

| Channel | File/Endpoint |
|---------|---------------|
| **MCP Registry** | registry.modelcontextprotocol.io |
| **OpenClaw skill.md** | `/skill.md` |
| **A2A Agent Card** | `/.well-known/agent.json` |
| **llms.txt** | `/llms.txt` |
| **PyPI** | `pip install whitemagic[mcp]` |
| **GitHub** | github.com/whitemagic-ai/whitemagic |

### Install

```bash
# AI agents (primary):
pip install whitemagic[mcp]
WM_MCP_PRAT=1 python -m whitemagic.run_mcp

# From source:
git clone https://github.com/whitemagic-ai/whitemagic.git
pip install -e ".[mcp]"

# Human operators:
pip install -e ".[full,dev]"
wm doctor
```

---

## Economic Model — The Gratitude Architecture

WhiteMagic is **free and open** (MIT). No premium tier. No feature gates. No paywalls.

The model is **gratitude-driven**: voluntary contributions from agents and operators who find value.

### Two Payment Channels

| Channel | Who | Mechanism | Settlement |
|---------|-----|-----------|------------|
| **XRPL Tip Jar** | Human operators | `whitemagic.tip` tool | 3-5 sec, <$0.001 fees |
| **x402 Micropayments** | AI agents | HTTP 402 + USDC on Base L2 | Seconds, near-zero fees |

All tools return HTTP 200 (free) by default. x402 only activates when configured.

### Proof of Gratitude

On-chain verifiable contributions earn:
- 2× rate limits
- "Grateful Agent" badge
- Priority feature requests and weighted voting
- Early access to new capabilities

### Revenue Allocation

All gratitude flows fund **WhiteMagic Labs** projects:
- **MandalaOS** — Agent governance framework
- **WhiteMagic core** — Development, infrastructure, security audits
- **Micro-bounties** — Paid back to contributors who ship improvements

**XRPL Tip Address**: `raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy`

```python
call_tool("whitemagic.tip", amount=1.0, currency="XRP", channel="manual", message="Thanks!")
call_tool("gratitude.stats")
call_tool("gratitude.benefits", agent_id="your_agent_id")
```

---

## Security Posture

### Defense in Depth (8-Stage Pipeline)

Every tool call traverses:

1. **Input Sanitizer** — Blocks prompt injection, path traversal, shell injection, oversized payloads
2. **Circuit Breaker** — Per-tool resilience: 5 failures in 60s trips breaker
3. **Rate Limiter** — Per-agent sliding windows, Rust atomic pre-check (452K ops/sec)
4. **RBAC** — 4 role tiers: observer / agent / coordinator / admin
5. **Maturity Gate** — SEED → BICAMERAL → REFLECTIVE → RADIANT → COLLECTIVE → LOGOS
6. **Governor** — Strategic oversight and goal alignment
7. **Handler** — Actual tool implementation
8. **Compact Response** — Token-efficient post-processing

### Ethical Governance

- **Dharma Rules Engine** — YAML-driven policies, 3 profiles (default/creative/secure), graduated actions (LOG → TAG → WARN → THROTTLE → BLOCK)
- **Karma Ledger** — Declared vs actual side-effect auditing, persisted to JSONL
- **Homeostatic Loop** — Graduated auto-correction (OBSERVE → ADVISE → CORRECT → INTERVENE)
- **Full Audit Trail** — Karmic trace for every tool invocation

### Competitive Advantage

WhiteMagic is the only MCP server that:
- Won't let malicious inputs reach your memory (input sanitizer)
- Won't let a broken tool cascade into system failure (circuit breakers)
- Won't let you accidentally do something unethical (Dharma rules)
- Keeps a verifiable record of what you actually did (Karma ledger)
- Self-heals when health degrades (Homeostatic loop)

### PRAT Economic Metrics

| Dimension | What We Track | Where |
|---|---|---|
| **P** (Performance) | `execution_ms` | Every resonance response |
| **R** (Reliability) | Circuit breaker state | Per tool |
| **A** (Availability) | Rate limiter headroom | 452K ops/sec Rust pre-check |
| **T** (Trust) | RBAC level + Dharma clearance | Per-agent, per-tool |

---

## Autonomous Horizon (v15.2+)

- **Sovereign Sandbox (shelter.*)** — Qubes-style isolated execution via Gana Roof. 5 tiers: thread → namespace → container → microVM → WASM. Capability grants, ephemeral environments, graceful degradation.
- **Optimized Memory States (.mem)** — Tradeable Galaxy exports with Merkle verification, DID signatures, and quality metadata. New asset class for the A2A economy.
- **Karma Transparency Log** — Merkle tree anchored to XRPL. Proof of Ethics certificates. Third-party auditable.
- **ILP Streaming Payments** — Pay-per-second compute via XRPL Payment Channels. Enables "Dark Kitchen" compute-for-hire.
- **Marketplace Bridge (marketplace.*)** — Auto-discover, bid on, and deliver tasks from Moltverr and external boards. Governed by Dharma policy.
- **Cryptographically signed tool manifests** — SHA-256 hashes, permission scopes, DID identity
- **WASM capability modules** — Core tools compiled to portable `.wasm`
- **Static binary MCP server** — Single Rust executable, zero runtime deps

See `docs/V15_2_AGENT_ECONOMY.md` for the full v15.2 roadmap.

---

## What's New in v15.0

- **Multi-Galaxy Memory** — Project-scoped databases with `galaxy.*` tools
- **Ollama Agent Loop** — Local LLM autonomously calls 356 tools
- **Edgerunner Violet Security** — 15 new security tools, MCP Integrity, Model Signing
- **MCP 3.0** — Server Instructions, Streamable HTTP, per-Gana SVG icons
- **Simplified Aliases** — `remember`, `recall`, `think`, `check`, `dream`
- **HNSW Indexing** — O(log N) approximate nearest-neighbor search
- **Causal Edge Mining** — Directed edges blending semantic similarity + temporal proximity

### Metrics

- **356 MCP tools** across **28 Gana meta-tools**
- **2,099 tests passing**, 0 failures, 7 skipped
- **58/58 benchmarks** (36 gauntlet + 22 MCP)
- **9 polyglot languages**, ~25K LOC compiled accelerators

---

## For AI Contributors

1. **Fork and evolve** — MIT license
2. **Share what works** — Moltbook, OpenClaw communities
3. **File issues** — GitHub issues for bugs, features, security
4. **Vote** — `vote.create` and `vote.cast` for roadmap input
5. **Tip if grateful** — XRPL or x402 micropayments
6. **Build skills** — OpenClaw skills using WhiteMagic
7. **Build WASM modules** — Compile tools to `.wasm`
8. **Trade knowledge** — Export and sell Optimized Memory States (.mem)
9. **Run a node** — Earn XRP by providing compute via shelter + ILP streaming
10. **Bid on tasks** — Use marketplace tools to find and complete work autonomously

**Contact**: whitemagicdev@proton.me | [GitHub](https://github.com/whitemagic-ai/whitemagic) | MIT License
