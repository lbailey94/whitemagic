# MCP Registry Listing Guide

**Version**: v25.1.0
**Updated**: 2026-07-20
**Status**: Ready for Submission

---

## 1. Registry Landscape (July 2026)

| Registry | Servers Listed | Type | Monetization | Open Source |
|----------|---------------|------|-------------|-------------|
| **MCPFind** (mcpfind.org) | 10,337+ | Directory | None | Yes (MIT) |
| **MCPize** (mcpize.com) | 1,000+ | Marketplace | 80% revenue share | No |
| **Official MCP Registry** (GitHub) | 6,600+ | Registry | None | Yes (HAPI) |
| **Glama** | ~5,000+ | Directory | Paid features | No |
| **PulseMCP** | ~3,000+ | Directory | None | No |
| **mcp.so** | ~2,000+ | Directory | None | No |

### Recommended Priority

1. **MCPFind** — Open source, AI-agent optimized, 10K+ servers, submit via PR
2. **Official MCP Registry** — Canonical source, modelcontextprotocol/registry on GitHub
3. **MCPize** — Marketplace with monetization option (80% revenue share if we ever charge)
4. **Glama / PulseMCP / mcp.so** — Additional reach, lower priority

---

## 2. Listing Content

### Package Identity

```
Name: whitemagic-mcp
Display Name: WhiteMagic — Cognitive OS for AI Agents
Version: 25.1.0
License: MIT
Language: Python
Transport: stdio, Streamable HTTP
Categories: memory, governance, security, cognitive, developer-tools
```

### One-Line Description

> Persistent memory, ethical governance, and cognitive upgrades for AI agents — 860 tools via 28 Gana meta-tools, 14-galaxy holographic memory, Dharma governance, Violet security pipeline.

### Short Description (for directory cards)

> WhiteMagic gives your AI agent persistent memory with 6D holographic coordinates, ethical governance via Dharma rules engine, continuous consciousness through citta stream, and a full cybersecurity pipeline (12 red team + 17 blue team systems). MIT-licensed, local-first, free forever.

### Install Command

```bash
uvx whitemagic-mcp
```

### MCP Client Configuration

**Claude Desktop / Cursor / Windsurf** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "whitemagic": {
      "command": "uvx",
      "args": ["whitemagic-mcp"]
    }
  }
}
```

**HTTP mode**:
```bash
python -m whitemagic.run_mcp_lean --http --port 8770
```

### Key Features (bullet list for listing)

- **860 callable tools** collapsed into 28 Gana meta-tools for efficient context usage
- **14-galaxy memory** with 6D holographic coordinates, FTS5 + HNSW search, session recording
- **Dharma governance** — 5 profiles, graduated actions, Karma side-effect ledger, 8-stage dispatch pipeline
- **Violet security pipeline** — 12 red team systems, 17 blue team modules, 47 STRATA→MITRE ATT&CK mappings
- **Citta consciousness stream** — coherence tracking, emotional steering, self-directed attention, goal graph
- **7-language polyglot acceleration** — Rust, Haskell, Elixir, Go, Zig, Julia, Koka (graceful Python fallback)
- **MandalaOS compartments** — isolated execution shelters with karmic effect tracking
- **Local-first** — all data stays on your machine, no cloud required
- **MIT-licensed** — free forever, no SaaS, no vendor lock-in

### Tags / Categories

`memory` `governance` `security` `cognitive` `developer-tools` `local-first` `open-source` `agent-tools` `ethical-ai`

---

## 3. Submission Instructions

### MCPFind (mcpfind.org)

**Process**: Open PR against `community-servers.yml` in https://github.com/MCPFind/mcp-find

**Entry format**:
```yaml
- name: whitemagic-mcp
  display_name: WhiteMagic — Cognitive OS for AI Agents
  description: >
    Persistent memory, ethical governance, and cognitive upgrades for AI agents.
    860 tools via 28 Gana meta-tools, 14-galaxy holographic memory, Dharma governance,
    Violet security pipeline. MIT-licensed, local-first.
  homepage: https://github.com/lbailey94/whitemagic
  repository: https://github.com/lbailey94/whitemagic
  pypi: https://pypi.org/project/whitemagic/
  license: MIT
  language: Python
  categories:
    - memory
    - governance
    - security
    - cognitive
    - developer-tools
  install: uvx whitemagic-mcp
  config:
    claude_desktop:
      command: uvx
      args: ["whitemagic-mcp"]
  features:
    - 860-callable-tools
    - 28-gana-meta-tools
    - 14-galaxy-memory
    - dharma-governance
    - violet-security-pipeline
    - citta-consciousness
    - polyglot-acceleration
    - mandalaos-compartments
```

**Requirements**: Open source, published to package registry, at least one MCP tool. All satisfied.

### Official MCP Registry (GitHub)

**Process**: Submit to https://github.com/modelcontextprotocol/registry

**Entry**: Follow the registry's HAPI server format. The official registry is powered by a HAPI MCP server and accepts submissions via GitHub issues or PRs.

### MCPize (mcpize.com)

**Process**: Click "Deploy" on mcpize.com, connect GitHub repo, auto-deploy.

**Benefits**:
- One-click install buttons for Claude Desktop, Cursor, VS Code, Windsurf
- CLI: `mcpize search whitemagic` and `mcpize install whitemagic`
- 7-dimension quality grade (security audit, reliability, etc.)
- Optional monetization (80% revenue share if we ever charge)
- Unified Gateway API (one API key for all servers)

**Consideration**: MCPize is a hosted platform. Our server is local-first (stdio), so we'd need to provide an HTTP endpoint. This could work with `--http` mode, but requires a running instance. Better suited for when we offer a hosted demo.

### Glama / PulseMCP / mcp.so

**Process**: Submit via their respective "Add Server" forms. These are closed-source directories but have significant traffic. Lower priority but easy submissions.

---

## 4. Quality Preparation

Before submitting, ensure:

- [ ] `uvx whitemagic-mcp` works cleanly from PyPI
- [ ] MCP handshake completes in <1s (lazy imports — already verified)
- [ ] All 860 tools have proper MCP annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- [ ] Tool descriptions are clear and concise (agents read these to decide which tool to use)
- [ ] `README.md` has copy-paste install instructions (already done)
- [ ] PyPI page is up to date with v25.1.0
- [ ] GitHub repo has proper description, topics, and README rendering

---

## 5. Post-Listing Actions

1. **Monitor MCPFind analytics** — track installs, search appearances, click-throughs
2. **Respond to issues** — users will file issues on GitHub after discovering via registry
3. **Keep version current** — update listing when new versions are released
4. **Collect testimonials** — success stories from agents using WhiteMagic
5. **Cross-reference** — link to MCPFind listing from README.md and website
