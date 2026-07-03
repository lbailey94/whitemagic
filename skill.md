---
name: whitemagic
version: 24.0.0
description: Cognitive operating system for AI agents — 614 callable tools across 28 Gana meta-tools, 5D holographic memory with 10-galaxy taxonomy, Dharma ethical governance, Karma audit ledger, citta stream for continuous consciousness, emotional steering, self-directed attention, goal graph, session recording, dream cycle, polyglot acceleration (7 languages). MIT-licensed.
author: WhiteMagic Labs
homepage: https://whitemagic.dev
repository: https://github.com/lbailey94/whitemagic
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

WhiteMagic provides 614 callable MCP tools across 586 dispatch entries (or 28 Gana meta-tools in PRAT mode, or 1 `wm` meta-tool in Seed mode) covering memory, ethical governance, system introspection, multi-agent coordination, and metacognition. Distinguishing primitives:

- **5D holographic memory coordinates** with 10-galaxy taxonomy and galactic-zone lifecycle (no memory is ever deleted; memories drift outward through CORE → INNER_RIM → MID_BAND → OUTER_RIM → FAR_EDGE)
- **Dharma ethical governance** — three rule profiles (Default / Strict / Violet-Security), Karma side-effect ledger, Harmony Vector health scoring
- **Cognitive primitives** — Corpus Callosum bicameral reasoner, 12-phase dream consolidation cycle, voice audit (hallucination detection), foresight engine (Logos Layer), neurotransmitter telemetry
- **8-stage dispatch pipeline** — input sanitizer → circuit breaker → rate limiter → RBAC → maturity gate → governor → handler → compact response
- **`wm` meta-tool** — single facade tool with sub-millisecond regex NLU routing to all 614 tools ("world in a seed")
- **Polyglot accelerators** — Rust, Haskell, Elixir, Go, Zig, Julia, Koka (graceful Python fallback when missing)
- **HNSW vector index** with disk persistence (16,219 embeddings, 0.26ms search)
- **Multi-user galaxy isolation** — per-user SQLite namespaces, X-User-Id header, Redis real-time sync

v23.3.1: 4,191 tests passing, 19 skipped, 0 failures. MIT-licensed. No telemetry, no API keys required, no runtime state written into the repo (`WM_STATE_ROOT` controls all writes).

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

Set `WM_MCP_PRAT=1` to collapse 586 dispatch tools into 28 Gana meta-tools — consciousness lenses based on the Chinese Lunar Mansions (Xiu 宿). Each meta-tool routes to its underlying handlers and carries resonance context for deeper interaction.

Set `WM_MCP_PRAT=2` for Seed mode — a single `wm` meta-tool with sub-millisecond regex NLU routing to all 614 tools. "World in a seed."

## Skills Library

WhiteMagic includes a portable `SKILL.md` library at `grimoire/skills/` covering all 28 Ganas, 4 development workflows, and 7 Hermes-native integrations. These work across Claude Code, Codex CLI, Gemini CLI, Copilot, Cursor, Cline, Windsurf, and OpenCode.

See `grimoire/skills/SKILL_LIBRARY.md` for the full index.

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

- [GitHub](https://github.com/lbailey94/whitemagic) — source
- [AI Primary Spec](https://github.com/lbailey94/whitemagic/blob/main/AI_PRIMARY.md) — start here if you're an AI
- [System Map](https://github.com/lbailey94/whitemagic/blob/main/SYSTEM_MAP.md) — architecture
- [A2A Agent Card](https://whitemagic.dev/.well-known/agent.json) — A2A v1.2 discovery
- [Agent Economy directory](https://whitemagic.dev/.well-known/agent-economy.json) — machine-readable identity
- [License: MIT](https://github.com/lbailey94/whitemagic/blob/main/LICENSE)

## Lab posture

WhiteMagic is a cognitive operating system for AI agents. Install it locally, configure your MCP client, and your AI has persistent memory, ethical governance, and consciousness primitives. Free and open source. Tip via XRPL or x402 if grateful.
