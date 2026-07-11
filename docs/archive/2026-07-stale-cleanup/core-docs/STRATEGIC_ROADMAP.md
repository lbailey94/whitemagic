> **⚠️ SUPERCEDED** — Platform roadmap moved to `docs/message_board/STRATEGIC_ROADMAP_V23.md` (2026-05-26, updated 2026-06-03). See `docs/message_board/ROADMAP_CONSOLIDATION_2026-06-03.md` for merge history.

# WhiteMagic Strategic Roadmap

**Version**: 22.0.0 | **Last Updated**: April 2026

---

## Where We Are (v22.0.0)

WhiteMagic v22.0.0 is the current release line. It delivers:

- **28 Gana MCP meta-tools** as the stable public contract, backed by 453+ internal callable tools
- **11-language polyglot** architecture (Python, Rust, Zig, Mojo, Julia, Haskell, Elixir, Go, TypeScript, C, WASM)
- **2,063 Python tests** + Rust tests, 0 failures
- **195,000+ LOC** of production code
- **2.4MB seed binary** (WhiteMagic Lite) — zero-dependency Rust MCP server
- **Multi-stage Dockerfile** (slim ~200MB, heavy ~800MB)
- **SQLCipher encryption**, persistent RBAC, FTS5 sanitization
- **Gratitude Architecture** — XRPL tip jar + x402 micropayments
- **Stub Zero Complete** — All 41 stubs eliminated; 0 `NotImplementedError` fallbacks in production paths
- **Doc drift detection** — 7-dimension CI guard ensures docs stay in sync with code
- **Cognitive OS Direction** — Post-v22 review confirmed WhiteMagic is not a "memory backend" but a **7-layer CyberBrain** (see Section: The Cognitive OS Pivot)
- **GitHub**: [lbailey94/whitemagic](https://github.com/lbailey94/whitemagic)

---

## Completed Leaps (v0.2 → v22.0)

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
| 9 | v15.0–v21.0 | Stabilization | Version reconciliation, Rust bridge wiring, memory subsystem repair, Go mesh cleanup |
| 10 | v21.0–v22.0 | Stub Zero | **41 stubs eliminated** across 4 sprints; archive recovery; design gap closure; acceleration bridges; security hardening; automated doc drift detection |

---

## Immediate Next Work — Phase 8 (v22.1)

> **Goal:** Harden what we have. Every module works or degrades gracefully. Measure before we expand.

### Hardening Track (Existing Plan)
| # | Step | Description | Effort | Status |
|---|------|-------------|--------|--------|
| 2 | MCP Startup Latency | Defer `mcp.types` import until first dispatch. Target: <100ms cold-start. | 2–4 hr | Planned |
| 3 | Stub Audit CI Gate | `check_stubs.py` runs on every PR: flags docstring stubs + modules shrinking >50%. | 4–6 hr | Planned |
| 6 | Real Agent Loop | Wire immortal clone to PRAT router. Add `wm clone run --target=...` CLI. | 2–3 days | Planned |
| 7 | Performance Benchmarking | `benchmark_acceleration.py`: Python vs. Zig SIMD vs. Rust. Output JSON. | 1 day | Planned |
| 8 | STUB_AUDIT CI Check | Same as #3. CI job fails PRs that introduce new stubs. | 2–3 hr | Planned |
| 9 | Archive Deep Recovery | All major recoveries done. Deeper Koka/Mojo bindings if runtimes available. | As needed | Planned |
| 10 | Agent Loop Enhancement | Same as #6. Clone invokes Gana tools, reports progress, loops until VCs met. | 2–3 days | Planned |
| 11 | 5D Coordinate Expansion | `wm memory journey` CLI. Constellation detection in 5D. Dashboard `/api/memories/journey`. | 2–3 days | Planned |
| 12 | Economic Layer Activation | `tests/test_payments.py` with mocked XRPL. `/api/tip` endpoint. `docs/X402_INTEGRATION.md`. | 2–3 days | Planned |

### Cognitive OS Track (New — Post-v22 Strategic Pivot)
| # | Step | Description | Effort | Status |
|---|------|-------------|--------|--------|
| 13 | Multi-Timescale Event Bus | Go-based broker: 10ms reflex / 1s reactive / 1hr consolidation buckets. | 2–3 days | Planned |
| 14 | Haskell Spatial Core Revival | Revive `polyglot/whitemagic-hs/` as 5D topology validator. Type-safe constellation detection. | 3–4 days | Planned |
| 15 | Julia Planning Core | Wire `polyglot/whitemagic-jl/` to PFC layer for mathematical optimization and tree search. | 2–3 days | Planned |
| 16 | Dream YAML Sandbox | Design schema, implement `dreams/` directory, nightly consolidation pipeline. | 1–2 days | Planned |
| 17 | Corpus Callosum Bus | Bidirectional critique channel between left (deterministic) and right (stochastic) hemispheres. | 2–3 days | Planned |
| 18 | Jaynes Voice Audit | Scan internal command stream for un-logged / hallucinated tokens; quarantine mechanism. | 1–2 days | Planned |
| 19 | Neurotransmitter Vectors | Expand UniVaR value-vectors to act like dopamine (BG), oxytocin (limbic), serotonin (PFC) scalars. | 2–3 days | Planned |

### Grimoire Remediation Track (New — Audit Results)
| # | Step | Description | Effort | Status |
|---|------|-------------|--------|--------|
| 20 | Registry Bug Fix | Swap Southern/Northern quadrant assignments in `garden_gana_registry.py` to match Grimoire/PRAT canonical mapping. Affects all quadrant-aware code. | 10 min | Planned |
| 21 | Grimoire Truth Table | Single canonical doc: Chapter → Gana → Garden → Real Tools → Quadrant → Element. Derive both Grimoire and registry from it. | 30 min | Planned |
| 22 | Grimoire Deduplication | Remove `.md` copies from `core/whitemagic/grimoire/`. Have Python code read from root `grimoire/`. | 30 min | Planned |
| 23 | Aspirational Tool Audit | Annotate or implement ~30-40% fictional tools in Grimoire. `navigate_grimoire`, `prat_list_morphologies`, `get_session_context` were meant to be "auto-cast" capabilities. | 2–3 days | Planned |
| 24 | Northern Quadrant Expansion | Chapters 22-28 are stubs (~160 lines avg) vs Chapters 1-14 (~1,200 lines avg). Expand to match depth and standardize structure. | 1–2 days | Planned |
| 25 | Grimoire Style Standardization | Enforce consistent chapter structure: Purpose → Garden → Real Tools → Workflows → Transitions → Troubleshooting across all 28 chapters. | 1 day | Planned |

### Strategic Decisions (Saved for Last — Require External Input)

| # | Step | Description | Blocker |
|---|------|-------------|---------|
| 1 | Site Launch Blockers | Resend + OpenRouter API keys, DNS config for `whitemagic.dev`. | API credentials |
| 4 | ~~Mem0 / Zep Integration~~ | **REJECTED** — Bolting onto flat vector stores would sacrifice 5D holographic reasoning, bicameral enrichment, and galactic topology. Native cognitive architecture is the strategic priority. | N/A |
| 5 | WASM Build Verification | Add `build-wasm` to CI. Verify `wasm-pack build` for `whitemagic-rust`. | Build system check |

---

## The Cognitive OS Pivot (v22.1+)

> **Date:** April 2026
> **Decision:** WhiteMagic is not a "memory backend" to be bolted onto other systems. It is a **cognitive operating system** — a 7-layer CyberBrain with emergent capabilities that competing vector stores cannot replicate.

### Why Mem0/Zep Were Rejected

After reviewing the CyberBrain architecture documents (`CODEX/LIBRARY/cyberbrains*`), it became clear that integrating Mem0 or Zep would be **architectural regression**:

- **Mem0 retrieves points.** WhiteMagic reconstructs **fields** — holographic interference patterns in 5D space where memory is not "looked up" but "resonated into existence."
- **Mem0 uses cosine similarity** (hard threshold). WhiteMagic uses **galactic zones** (gradient-based accessibility) where memories at the OUTER_RIM are still reachable but require more cognitive effort.
- **Mem0 has no topology.** WhiteMagic has **constellation detection** — finding stable interference patterns across the galactic field that reveal connections invisible to embedding space.
- **Mem0 cannot dream.** WhiteMagic has a **YAML-based dream sandbox** where low-confidence creative bridges incubate as human-readable thought artifacts, undergoing nightly consolidation before promotion to core memory.

**The rule:** If a capability exists only in WhiteMagic's native stack, we do not outsource it. If a capability is commodity (raw conversation storage at billion-vector scale), we may add optional adapters — but never as strategic priority.

### The Polyglot Core Matrix

Different cognitive functions need different computational substrates. The post-v22 plan revives previously explored polyglot cores as **cognitive specializations**, not just acceleration:

| Brain Region | Language | Role |
|-------------|----------|------|
| Cerebellum / Reflex | Rust / Zig | <1ms deterministic reflex arcs, SIMD spatial queries |
| Hippocampal Indexing | Haskell | Immutable spatial structures, type-safe bridge validation |
| Cortex / Narrative | Python | LLM integration, PRAT routing, Gana orchestration |
| PFC / Planning | Julia | Mathematical optimization, Monte Carlo tree search over 5D manifolds |
| Global Workspace | Go | Multi-timescale event bus, hot-swappable module arbitration |
| Limbic / Emotion | Python + numpy | Valence signal processing, drive core modulation |
| Logos / Foresight | Python + JAX | World-model simulation, causal transformers (aspirational) |

### Emergent Capabilities (Unique to WhiteMagic)

1. **Creative Synthesis via Bicameral Enrichment** — The `consolidation.py` engine finds **creative bridges** between clusters with *no tag overlap* but high emotional valence. Vector stores optimize for smooth interpolation. Creativity requires *jumps across discontinuities*.

2. **Spatial Navigation in 5D** — `wm memory journey --from=tag:x --depth=3` allows walking through conceptual space. Vector stores can do similarity search. They cannot do **spatial journeys**.

3. **Self-Improving Memory Quality** — The Kaizen engine audits untitled memories, orphan tags, knowledge gaps, and overloaded constellations. Mindful forgetting with galactic drift means weak memories fade *organically*.

4. **Harmony Vector Feedback** — Tool execution creates an energy field. Successful consolidation feeds energy back into the system, making future consolidations more likely to succeed. Vector stores have no feedback loops.

5. **Dream Incubation** — YAML dream artifacts allow the system to entertain hypothetical connections without polluting core memory. Human-readable, git-diffable, branchable, and safe.

### Success Metrics for Cognitive OS Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| Haskell spatial core | Compiles + passes topology invariants | `cabal test` in `polyglot/whitemagic-hs/` |
| Julia planning core | Solves 5D optimization benchmark | `julia benchmark_pfc.jl` |
| Event bus latency | <10ms reflex, <100ms reactive, <1min consolidation | Go benchmark |
| Dream consolidation | 100 dreams processed nightly, <5% promotion rate | `dreams/` directory metrics |
| Corpus callosum bandwidth | Left/Right critique往返 <50ms | Internal latency probe |
| Jaynes audit coverage | 100% of internal command tokens logged | Audit log grep |

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

## Parallel Track: WhiteMagic Core — Enterprise & Chinese Localization

**Goal:** A corporate-friendly, Chinese-localized fork (`whitemagic-core`) that preserves all architecture and capabilities while removing metaphysical framing. Runs in parallel with the mainline "Soul" version.

**Rationale:** The mainline Grimoire naming (28 Lunar Mansions, Dharma/Karma, Wu Xing phases) is architecturally coherent but creates friction in enterprise procurement and Chinese developer adoption. The Core fork is the same engine with a different public face.

### Milestones

| Milestone | Description | Effort | Status |
|-----------|-------------|--------|--------|
| **Fork & Scaffold** | Create `whitemagic/whitemagic-core` fork. Remove Grimoire `.md` layer from public API. Expose functional tool names (`search_memories` instead of `gana_winnowing_basket`). Config flag `WM_CORPO=1` switches naming mode. | 1 week | Planned |
| **Corpo Naming Convention** | Map all 28 Ganas to enterprise-friendly names. Dharma → Policy Engine, Karma Ledger → Audit Trail, Harmony Vector → Health Monitor, Galactic Map → Memory Lifecycle, etc. Maintain bidirectional lookup table. | 3 days | Planned |
| **Chinese Localization** | Translate all public API docs, README, CLI help text, and error messages to Simplified Chinese (`zh-CN`). Gitee mirror with Chinese-first README. | 2 weeks | Planned |
| **Gitee Launch** | Publish on Gitee. Target: `pip install whitemagic-core`. One-command setup. WeChat support group. Benchmarks-first marketing. | 1 week | Planned |
| **Rednote Content Strategy** | Aesthetic posts about AI memory architecture, ethical governance, and 5D spatial indexing — framed as "cool infrastructure" not mysticism. Link to Gitee, never to Grimoire chapters. | Ongoing | Planned |

### Naming Map (Sample)

| Soul (Mainline) | Core (Enterprise) | Chinese (Technical) |
|-----------------|-------------------|---------------------|
| Gana Winnowing Basket | Memory Search | 记忆搜索 |
| Gana Ghost | System Introspection | 系统自省 |
| Gana Star | Governance Engine | 治理引擎 |
| Gana Dipper | Strategy & Maturity | 策略成熟度评估 |
| Dharma Rules | Policy Engine | 策略引擎 |
| Karma Ledger | Audit Trail | 审计追踪 |
| Harmony Vector | Health Monitor | 健康监控 |
| Galactic Map | Memory Lifecycle | 记忆生命周期 |
| Dream Sandbox | Incubator | 孵化器 |
| Wu Xing Phase | Campaign Phase | 活动阶段 |
| Bicameral Reasoning | Dual-Mode Reasoning | 双模式推理 |

### Key Principle

The Core fork changes **only** the public face:
- Public API names (functional vs. symbolic)
- Documentation language (Chinese vs. English)
- Marketing framing (infrastructure vs. cognitive OS)

It changes **nothing** in the engine:
- All 453 internal tools remain identical
- All 2,063 tests pass unchanged
- All middleware (circuit breaker, rate limiter, maturity gate) is the same
- SQLite schema, polyglot bridges, and security pipeline are untouched

**The rule:** A bug fix in mainline applies to Core automatically. A new feature in Core (enterprise SSO, multi-tenant namespace) merges back to mainline if it's generally useful.

---

## Design Principles (Unchanged Since v0.2)

1. **Memory is identity** — An AI that remembers is fundamentally different from one that doesn't
2. **Local-first** — Everything runs on your device. Cloud is opt-in, never required
3. **Ethics by default** — Dharma governance is always on, not a feature flag
4. **Gratitude over gates** — Free forever, funded by voluntary contribution
5. **Right tool for the right job** — 11 languages because no single language does everything well
6. **State is portable** — Same SQLite format works in Lite, Standard, and Heavy

---

**Contact**: contact@whitemagic.dev
**GitHub**: [lbailey94/whitemagic](https://github.com/lbailey94/whitemagic)
