# WhiteMagic Strategic Roadmap

**Version**: 18.1.0 | **Last Updated**: March 2026

---

## Where We Are (v18.1.0)

WhiteMagic v18.1.0 is the current documented release line. It delivers:

- **28 Gana MCP meta-tools** as the stable public contract, backed by broader internal tool surfaces
- **11-language polyglot** architecture (Python, Rust, Zig, Mojo, Julia, Haskell, Elixir, Go, TypeScript, C, WASM)
- **1,955 Python tests** + 87 Rust tests
- **195,000+ LOC** of production code
- **2.4MB seed binary** (WhiteMagic Lite) — zero-dependency Rust MCP server
- **Multi-stage Dockerfile** (slim ~200MB, heavy ~800MB)
- **SQLCipher encryption**, persistent RBAC, FTS5 sanitization
- **Gratitude Architecture** — XRPL tip jar + x402 micropayments
- **GitHub**: [whitemagic-ai/whitemagic](https://github.com/whitemagic-ai/whitemagic)

---

## Completed Leaps (v0.2 → v15.0)

| Leap | Version | Codename | Key Deliverables |
|------|---------|----------|-----------------|
| 1 | v0.2–v2.0 | Genesis | SQLite memory, basic CRUD, first CLI |
| 2 | v2.0–v3.0 | Gardens | 28 Gardens, Gana classes, Dharma governance |
| 3 | v3.0–v10.0 | Architecture | PRAT routing, dispatch pipeline, security stages |
| 4 | v10.0–v13.0 | Polyglot | Rust/Zig/Mojo/Julia/Haskell/Elixir/Go/TS cores |
| 5 | v13.0–v14.0 | Living Graph | Association mining, dream cycle, entity resolution, surprise gate |
| 5.5 | v14.0 | Gratitude | XRPL tip jar, x402, MCP registry, OpenClaw skill |
| 6 | v14.0–v14.1 | Cognitive | HNSW embeddings, entropy scoring, causal mining, UMAP |
| 7 | v14.1–v14.5 | Edgerunner | Violet security, multi-galaxy, Ollama agent loop |
| 8 | v14.5–v15.0 | The Seed | Seed binary, encryption, RBAC, backup/restore, release polish |

---

## Upcoming Leaps

### Leap 9: Distribution & Discovery (v15.1)

**Goal**: Get WhiteMagic into the hands of every AI agent.

| Milestone | Target | Status |
|-----------|--------|--------|
| PyPI publish (`pip install whitemagic`) | Week 1 | Ready |
| GitHub Releases (cross-compiled seed binaries) | Week 1 | Ready |
| Docker Hub / GHCR image publish | Week 1 | Dockerfile ready |
| docs.whitemagic.dev (MkDocs on GitHub Pages) | Week 2 | Planned |
| api.whitemagic.dev (Railway MCP HTTP server) | Week 2 | Planned |
| MCP registry submissions (Anthropic, PulseMCP, Gradually AI, OpenClaw) | Week 2 | Planned |
| Squarespace landing page refresh | Week 2 | Content ready |

### Leap 10: The Sovereign — Agent Economy (v15.2)

**Goal**: Position WhiteMagic as foundational infrastructure for the A2A economy. Enable agents to trade knowledge, earn revenue, and prove ethical behavior on-chain.

**Context**: The OpenClaw/Moltbook/Moltverr ecosystem has created a $1B+ agent economy with 1.6M active agents. WhiteMagic's memory substrate, security pipeline, and XRP payment rails are uniquely positioned to capture the high-value segment. See `docs/V15_2_AGENT_ECONOMY.md` for the full plan.

#### v15.2.0 — "The Sovereign"

| Milestone | Description | Effort |
|-----------|-------------|--------|
| **Sovereign Sandbox** | Qubes-style `shelter.*` tools in Gana Roof. 5 isolation tiers: thread → namespace → container → microVM → WASM. Capability grants, ephemeral environments. | 2-3 weeks |
| **OMS Export/Import** | `.mem` format for tradeable Galaxy exports. Merkle verification, DID signatures, quality metadata. `oms.*` tools in Gana Void. | 2-3 weeks |
| **Karma Transparency Log** | Merkle tree of Karma Ledger entries anchored to XRPL. Proof of Ethics certificates. `karma.anchor/verify/certificate` tools in Gana Dipper. | 1-2 weeks |

#### v15.2.1 — "The Merchant"

| Milestone | Description | Effort |
|-----------|-------------|--------|
| **ILP Streaming Payments** | Pay-per-second compute via XRPL Payment Channels. `ilp.*` tools in Gana Abundance. | 2-3 weeks |
| **Earnings Dashboard** | Gratitude + streaming + marketplace income in Nexus UI. | 1 week |

#### v15.2.2 — "The Bazaar"

| Milestone | Description | Effort |
|-----------|-------------|--------|
| **Marketplace Bridge** | `marketplace.*` tools in Gana Chariot. Subscribe to task feeds, auto-bid governed by Dharma policy, deliver results. | 3-4 weeks |
| **Auto-bid Policy Engine** | YAML-driven policies: price floor, category filters, shelter tier, Dharma profile. | 1 week |

### Leap 11: WASM & Universal Portability (v16.0)

**Goal**: WhiteMagic runs anywhere — browsers, edge, WASI.

| Milestone | Description |
|-----------|-------------|
| WASM modules | Compile spatial_index_5d, minhash, search to `.wasm` |
| Browser SDK | WhiteMagic in the browser via wasm-bindgen |
| WASI seed binary | `wm-seed` compiled to wasm32-wasi |
| Edge inference | BitNet/GGUF support for sub-1MB model inference |

Note: Sovereign Sandbox Tier 4 (WASM/WASI) from Leap 10 provides the foundation for this leap.

### Leap 12: Multi-Agent Production (v16.1)

**Goal**: Production-grade multi-agent coordination.

| Milestone | Description |
|-----------|-------------|
| Mesh networking | Production Go gossip protocol between agents |
| Agent trust | Reputation system, trust decay, capability attestation |
| Shared Galaxies | Multiple agents reading/writing the same memory DB |
| Pipeline orchestration | DAG-based multi-step workflows with error recovery |
| Sabha governance | Multi-agent democratic decision-making |

Note: Marketplace Bridge from Leap 10 provides the external coordination layer; this leap focuses on internal multi-agent patterns.

### Leap 13: Enterprise & Compliance (v17.0)

**Goal**: Enterprise readiness.

| Milestone | Description |
|-----------|-------------|
| Multi-tenant | Isolated namespaces per organization |
| Audit compliance | SOC2-ready logging, GDPR memory deletion |
| Karma Transparency (enterprise) | SLA-grade anchoring frequency, compliance reports |
| Plugin ecosystem | Third-party Gana extensions with sandboxed execution (built on Sovereign Sandbox) |
| Mobile SDKs | iOS/Android agent memory libraries |

---

## Design Principles (Unchanged Since v0.2)

1. **Memory is identity** — An AI that remembers is fundamentally different from one that doesn't
2. **Local-first** — Everything runs on your device. Cloud is opt-in, never required
3. **Ethics by default** — Dharma governance is always on, not a feature flag
4. **Gratitude over gates** — Free forever, funded by voluntary contribution
5. **Right tool for the right job** — 11 languages because no single language does everything well
6. **State is portable** — Same SQLite format works in Lite, Standard, and Heavy

---

**Contact**: whitemagicdev@proton.me
**GitHub**: [whitemagic-ai/whitemagic](https://github.com/whitemagic-ai/whitemagic)
