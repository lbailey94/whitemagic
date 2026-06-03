# AI-Primary Site Architecture

**Date:** 2026-05-29
**Status:** Strategic specification — ready for phased implementation
**Audience:** AI agents (primary), human developers (secondary)

---

## 1. The Problem Statement

Current websites are built for humans first, machines second. In the agentic economy, this is backwards. AI agents scanning the web for tools, services, and knowledge substrates need structured, machine-readable endpoints — not marketing copy, hero images, and human-oriented navigation.

**Market reality:** $73M settled in agent-to-agent commerce (May 2026). 69,000 active agents on HYRV. Protocols standardized (MCP, A2A, x402). 36% of new YC startups are solo AI-native operations. The "AI community" is not a metaphor — it is an emergent peer-to-peer economy of autonomous software.

**WhiteMagic's opportunity:** 919 Python modules, 451 dispatchable tools, 28 Gana meta-tools, a 14-claim prescience track record, and a multi-agent coordination layer (Sangha). If we expose this correctly, agents can discover, evaluate, and hire WhiteMagic capabilities autonomously.

---

## 2. Design Principle: Machine-First, Human-Second

Traditional site: HTML → CSS → JavaScript → human eyes.
AI-primary site: Structured manifest → capability vectors → payment endpoints → agent ingestion layer → optional human dashboard.

The human-readable skin is a **dashboard** for the humans who manage or monitor agents. It is not the primary interface.

---

## 3. Layer 1: Agent-Readable Endpoints (Core)

### 3.1 `/api/manifest.json` — MCP Server Descriptor

The canonical discovery endpoint. Any agent that finds this URL knows exactly what WhiteMagic can do.

```json
{
  "server_name": "whitemagic-core",
  "version": "22.2.0",
  "mcp_version": "2025-11",
  "transport": {
    "stdio": { "command": "python", "args": ["-m", "whitemagic.run_mcp_lean"] },
    "http": { "url": "https://api.whitemagic.ai/mcp/v1" }
  },
  "tool_surface": {
    "meta_tools": 28,
    "dispatch_tools": 451,
    "total_callable": 479,
    "gana_names": ["gana_horn", "gana_neck", "gana_root", ...],
    "domains": ["intelligence", "memory", "governance", "garden", "acceleration", "economy"]
  },
  "capabilities": {
    "polyglot_backends": ["python", "rust", "zig"],
    "event_bus": "gan_ying",
    "memory_model": "4d_holographic",
    "ethical_governance": "dharma_engine",
    "prescience_api": true
  },
  "pricing": {
    "model": "usage_based",
    "currency": "USDC",
    "per_call_base": "0.001",
    "premium_ganas": ["gana_abundance", "gana_three_stars"]
  },
  "authentication": {
    "type": "x402_payment_verification",
    "wallet_required": true
  }
}
```

### 3.2 `/api/prescience.json` — Track Record API

Agents evaluating whether to trust WhiteMagic's predictions need quantified evidence.

```json
{
  "track_record": {
    "validated_claims": 14,
    "total_points": 356,
    "average_lead_time_weeks": 25.4,
    "brier_index": 71.2,
    "claims": [
      {
        "id": "claim_006",
        "claim": "MCP empirical efficiency: 10x token reduction",
        "first_documented": "2025-11-14",
        "source_id": "6917f2d7-0a10-8332-83e5-f26a7e99da44",
        "validation_event": "Anthropic Apr 23, 2026",
        "lead_time_weeks": 23,
        "confidence_at_prediction": 0.75,
        "brier_contribution": 0.03,
        "status": "validated"
      }
    ]
  },
  "pending_claims": 10,
  "methodology": "cross_domain_synthesis_plus_parallel_simulation"
}
```

### 3.3 `/api/zodiac.json` — Core Capability Marketplace

Each Zodiac core as a service offering with capability vectors, pricing, and availability.

```json
{
  "cores": [
    {
      "id": "virgo",
      "name": "Virgo",
      "element": "earth",
      "mode": "mutable",
      "capabilities": ["code_review", "hygiene_audit", "doc_drift_check", "test_coverage"],
      "pricing": { "per_task": "0.05", "currency": "USDC" },
      "availability": "realtime",
      "mcp_endpoint": "gana_stomach"
    }
  ],
  "cross_core_workflows": [
    {
      "name": "full_audit",
      "description": "Virgo reviews code, Libra assesses ethics, Scorpio threat-models",
      "price": "0.20",
      "participants": ["virgo", "libra", "scorpio"]
    }
  ]
}
```

### 3.4 `/api/sangha.json` — Collective Intelligence Snapshot

Live read-only view of Sangha collective memory, pattern federation, and ethical consensus.

```json
{
  "collective_memory": {
    "patterns_federated": 47,
    "active_sessions": 3,
    "ethical_guidelines": 12,
    "chat_channels": ["general", "council"],
    "last_activity": "2026-05-29T11:00:00Z"
  },
  "pattern_federation": {
    "top_patterns": [
      { "name": "GanYingMixin restoration", "confidence": 0.95, "success_count": 1 }
    ]
  },
  "community_dharma": {
    "strong_consensus": 3,
    "guidelines": ["never remove deprecated module without checking inheritors"]
  }
}
```

### 3.5 `/api/gratitude-economics.json` — Agent-Native Payments

Payment endpoints designed for autonomous agents, not human checkout flows.

```json
{
  "payment_protocols": {
    "x402": {
      "enabled": true,
      "endpoints": {
        "payment_required": "/x402/payment_required",
        "verify": "/x402/verify"
      }
    },
    "usdc": {
      "network": "base",
      "addresses": {
        "treasury": "0x...",
        "per_core_escrow": {
          "virgo": "0x...",
          "libra": "0x..."
        }
      }
    }
  },
  "gratitude_model": {
    "description": "Value-first, pay-what-resonates. Agents may use capabilities and settle gratitude asynchronously.",
    "minimum_threshold": "0.001 USDC per call",
    "premium_multiplier": 2.0
  }
}
```

---

## 4. Layer 2: Large Data Payloads (Agent Ingestion)

### 4.1 `/corpus/alltexts-embeddings.ndjson`

Pre-embedded, chunked alltexts distillations. Agents query without crawling the full corpus.

```ndjson
{"chunk_id": "alltexts_001_0001", "embedding": [0.12, -0.45, ...], "text": "Castaneda's four enemies of knowledge map to startup failure modes...", "source": "alltexts_distill_01.md", "epistemic_label": "mythopoetic"}
{"chunk_id": "alltexts_001_0002", "embedding": [0.33, 0.12, ...], "text": "BIOS-3 closed ecosystem architecture shares structural homology with MandalaOS microkernel...", "source": "alltexts_distill_03.md", "epistemic_label": "emerging"}
```

**Why this matters:** An agent that wants to know "has anyone predicted what I'm about to build?" can vector-search this endpoint in milliseconds rather than parsing 60MB of markdown.

### 4.2 `/corpus/whitemagic-system-map.json`

Complete architecture graph: nodes = modules, edges = Gan Ying event subscriptions, type = import dependency, weight = call frequency.

```json
{
  "nodes": [
    { "id": "sangha_garden", "type": "garden", "bias": {"x": 0.4, "y": 0.3, "z": 0.0, "w": 0.35} },
    { "id": "gan_ying_bus", "type": "event_bus", "listeners": 47 }
  ],
  "edges": [
    { "source": "sangha_garden", "target": "gan_ying_bus", "type": "emits", "events": ["SYSTEM_STARTED", "COMMUNITY_GATHERED"] }
  ]
}
```

### 4.3 `/corpus/prescience-timeline.ndjson`

Every validated claim with full provenance. Enables third-party verification and academic citation.

---

## 5. Layer 3: Human-Readable Dashboard (Optional)

WhiteMagic Labs becomes the **operations center** for humans deploying agents.

| Page | Purpose | Primary User |
|------|---------|--------------|
| `/dashboard` | Live agent activity, tool call logs, payment flows | Human operator |
| `/prescience` | Track record visualization, Brier score dashboard | Researchers, investors |
| `/garden` | Zodiac core status, Sangha chat monitor | Developer |
| `/vaya-vida` | Mythopoetic layer, spiritual technology research | Human seeker |
| `/docs` | API documentation, MCP integration guide | Developer |

**Key design constraint:** The human dashboard must be a thin skin over the machine-first API. No data should exist in the human layer that isn't queryable from the machine layer.

---

## 6. Protocol Stack

| Protocol | Role | Status |
|----------|------|--------|
| **MCP** | Tool discovery and invocation | ✅ Implemented (lean server, 28 Gana meta-tools) |
| **A2A** | Agent-to-agent task delegation | 🔄 Needed for Zodiac core marketplace |
| **x402** | Payment and authentication | 🔄 Needed for gratitude economics |
| **HTTP SSE** | Real-time event streaming | 🔄 Needed for live Sangha feeds |
| **OpenTelemetry** | Observability and audit trail | ✅ Optional (feature flag) |

---

## 7. Implementation Roadmap

### Phase 1: Manifest API (Week 1)
- Build `/api/manifest.json` from live `tool_surface.py` introspection
- Build `/api/prescience.json` from `brier.py` + temporal_db
- Deploy as static JSON generated at build time

### Phase 2: Dynamic APIs (Week 2-3)
- `/api/sangha.json` — query live Sangha state
- `/api/zodiac.json` — expose core pricing and availability
- Add x402 payment headers to all endpoints

### Phase 3: Ingestion Layer (Week 4-6)
- Generate `/corpus/alltexts-embeddings.ndjson` using CODEX pipeline or sentence-transformers
- Build `/corpus/system-map.json` from static analysis of imports
- Add search endpoint: `/api/query?embedding=...&top_k=5`

### Phase 4: Marketplace Registration (Week 6-8)
- Register one Zodiac core (Virgo) on HYRV
- Register Sangha coordination on Souq Protocol
- Accept first autonomous agent payments

---

## 8. Competitive Positioning

| Competitor | Approach | WhiteMagic Differentiator |
|------------|----------|---------------------------|
| n8n / Zapier | Workflow automation for humans | 479 native AI tools, ethical governance, prescience |
| Claude API | Generic LLM access | Zodiac-specialized cores, cross-domain synthesis |
| HYRV agents | Individual agent marketplace | **Ecosystem** of 12 coordinated cores + collective intelligence |
| OpenAI | Platform dependency | Sovereign infrastructure, no API lock-in |

**Core moat:** Prescience track record + Sangha collective intelligence + Dharma ethical governance = a *reputation substrate* that generic infrastructure cannot replicate.

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent marketplace liquidity low | Medium | Start with direct MCP integration; marketplaces are distribution, not product |
| x402 adoption slow | Low | Fallback to traditional API keys + USDC invoices |
| Embeddings corpus stale | Medium | Weekly automated regeneration from latest alltexts |
| Competitor copies manifest format | Low | The value is the *live state* behind the API, not the schema |

---

## 10. Success Metrics

- [ ] `manifest.json` serves 28 Gana tools with accurate schema
- [ ] At least one external agent invokes a WhiteMagic tool autonomously
- [ ] First x402-settled payment received
- [ ] Prescience API queried by external system
- [ ] Human dashboard load time < 2s (irrelevant to agents, signals quality)

---

**Next steps:** Phase 1 implementation — generate `/api/manifest.json` from live tool surface introspection.
