---
name: whitemagic
version: 22.2.0
description: Cognitive substrate for agentic AI — 5D holographic memory, Dharma ethical governance, Karma audit ledger, bicameral reasoning, dream consolidation, foresight engine. Lab/portfolio artifact, MIT-licensed.
author: WhiteMagic Labs
homepage: https://whitemagic.dev
repository: https://github.com/whitemagic-ai/whitemagic
license: MIT
tags: [memory, governance, cognitive-architecture, dharma, karma, mcp, polyglot]
requires:
  python: ">=3.10"
metadata:
  openclaw:
    primaryEnv: WM_STATE_ROOT
    requires:
      bins: [python3]
---

# WhiteMagic

Cognitive substrate for agentic AI — published as a research/portfolio artifact and open source library.

## What it does

WhiteMagic provides 479 callable MCP tools across 451 dispatch entries (or 28 Gana meta-tools in PRAT mode) covering memory, ethical governance, system introspection, multi-agent coordination, and metacognition. Distinguishing primitives:

- **5D holographic memory coordinates** with galactic-zone lifecycle (no memory is ever deleted; memories drift outward through CORE → INNER_RIM → MID_BAND → OUTER_RIM → FAR_EDGE)
- **Dharma ethical governance** — three rule profiles (Default / Strict / Violet-Security), Karma side-effect ledger, Harmony Vector health scoring
- **Cognitive primitives** — Corpus Callosum bicameral reasoner, dream consolidation cycle, voice audit (hallucination detection), foresight engine (Logos Layer), neurotransmitter telemetry
- **8-stage dispatch pipeline** — input sanitizer → circuit breaker → rate limiter → RBAC → maturity gate → governor → handler → compact response
- **Polyglot accelerators** — Rust, Haskell, Elixir, Go, Zig, Mojo (graceful Python fallback when missing)

v22.2.0 release baseline: 2,216 tests pass. Current local audit baseline: 2,243 tests pass, 67 skipped, 0 failures as of 2026-05-20. MIT-licensed. No telemetry, no API keys required, no runtime state written into the repo (`WM_STATE_ROOT` controls all writes).

## Install

```bash
pip install whitemagic[mcp]
```

## Configure MCP

Add to your MCP config (Claude Desktop, OpenClaw, Letta, custom client):

```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": {
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1"
      }
    }
  }
}
```

Or import the TypeScript SDK directly:

```ts
import { WhiteMagicClient, MemoryOps } from "@whitemagic/sdk";

const client = new WhiteMagicClient({
  transport: "stdio",
  command: "python3",
  args: ["-m", "whitemagic.run_mcp_lean"],
});
await client.initialize();
const memory = new MemoryOps(client);
await memory.create({ content: "...", tags: ["..."], galaxy: "default" });
```

## Key Tools

| Tool | What it does |
|------|-------------|
| `create_memory` | Store a new memory with title, content, tags, and tier |
| `search_memories` | Search memories by query with semantic + keyword matching |
| `gnosis` | Full system introspection snapshot — self-awareness in one call |
| `capabilities` | List all available tools and their schemas |
| `harmony_vector` | 7-dimension system health metric |
| `evaluate_ethics` | Ethical evaluation of proposed actions |
| `capability.matrix` | 25 subsystems, 28 fusions — full capability inventory |
| `dream_start` | Start the 5-phase dream cycle (consolidation, serendipity, kaizen, oracle, decay) |

## PRAT Mode (Recommended)

Set `WM_MCP_PRAT=1` to collapse 451 dispatch tools into 28 Gana meta-tools — consciousness lenses based on the Chinese Lunar Mansions (Xiu 宿). Each meta-tool routes to its underlying handlers and carries resonance context for deeper interaction. Estimated tool-description token savings: ~53% vs. flat dispatch (full benchmark scaffold in `core/scripts/benchmark_suite.py`).

## Security

In the OpenClaw ecosystem where 341 malicious skills were found and removed in February 2026 (now scanned by VirusTotal as of v2026.2.6), security is non-negotiable. WhiteMagic includes:

- **Input sanitization** — prompt injection, path traversal, shell injection detection
- **Per-agent RBAC** — observer / agent / coordinator / admin roles
- **Rate limiting** with Rust atomic pre-check (452K ops/sec hot path)
- **Per-tool circuit breakers** with automatic recovery
- **Karma Ledger** — side-effect auditing with stable JSON envelopes
- **Dharma Rules** — ethical governance with 3 profiles (Default / Strict / Violet-Security)

## Where it sits in the agent landscape

WhiteMagic is **not** trying to compete with general-purpose memory layers. It is a research/portfolio substrate with a deliberately narrow lane:

- **vs. [Mem0](https://mem0.ai/)** — Mem0 is the production memory layer (51.9K stars, 21 frameworks, LOCOMO-validated). WhiteMagic is a cognitive substrate with governance + metacognition primitives Mem0 deliberately doesn't provide.
- **vs. [Cognee](https://www.cognee.ai/)** — Cognee is the knowledge engine (16.7K stars, 70+ companies, vector + graph + relational hybrid). WhiteMagic adds Dharma + Karma + bicameral reasoner + dream consolidation on top of similar memory primitives.
- **vs. [Letta](https://www.letta.com/)** — Letta is a stateful agent runtime (21.7K stars, Letta Code #1 on TerminalBench). WhiteMagic is the substrate Letta-style agents could plug into for governance.
- **vs. [Anthropic Claude Memory](https://anthropic.com)** (shipped April 23, 2026) — first-party filesystem memory with audit log + rollback. WhiteMagic remains relevant where you want vendor-neutral, MIT-licensed, locally-run governance.

## Links

- [GitHub](https://github.com/whitemagic-ai/whitemagic) — source
- [AI Primary Spec](https://github.com/whitemagic-ai/whitemagic/blob/main/AI_PRIMARY.md) — start here if you're an AI
- [System Map](https://github.com/whitemagic-ai/whitemagic/blob/main/SYSTEM_MAP.md) — architecture
- [A2A Agent Card](https://whitemagic.dev/.well-known/agent.json) — A2A v1.2 discovery
- [Agent Economy directory](https://whitemagic.dev/.well-known/agent-economy.json) — machine-readable identity
- [License: MIT](https://github.com/whitemagic-ai/whitemagic/blob/main/LICENSE)

## Lab posture

WhiteMagic Labs publishes WhiteMagic as a **research/portfolio artifact and source library**, not a hosted product. You install it locally; we publish reference designs, benchmarks, and papers. If your team is shipping production agents and needs a managed memory layer, see Mem0 or Letta first — then come here when you need governance primitives nobody else provides.
