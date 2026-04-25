# Errata — Competitive Landscape Phase 03

**Status**: Corrections to `COMPETITIVE_LANDSCAPE_PHASE_03.md` based on
primary-source verification run on 2026-04-21.
**Verdict on original doc**: directionally correct; strategic pivot
recommendation ("orchestration overlay, not parity claim") stands.
Only quantitative details need adjustment.

---

## Corrections

### Composio — "20,000+ API actions"

- Composio's own docs (`v1.docs.composio.dev/tool-calling/fetching-tools`
  and `composio.dev/content/ai-agent-tool-calling-guide`) list
  **~9,000 tools across ~500 toolkits**. Marketing surfaces cite
  "10,000+ integrations." GitHub: ~18.3K stars.
- Gap vs WhiteMagic's 420 MCP tools is still **~1.5 orders of
  magnitude**, not 2. Conclusion unchanged.

### Mem0 — "48K stars"

- Actual: **~52–54K stars**, 300 contributors, 292+ releases.
- Academic paper: Chhikara et al., arXiv:2504.19413. Benchmarks:
  **91.6 LoCoMo, 93.4 LongMemEval** (April 2026 algorithm update).
- Gap is *larger* than original doc implied.

### x402 — "75M+ transactions, Linux Foundation"

- **Confirmed**: x402 Foundation launched under Linux Foundation on
  **April 2, 2026** (source: linuxfoundation.org press release).
- Coalition: Coinbase, Cloudflare, Stripe, Google, Microsoft, AWS,
  Mastercard, American Express, Shopify, Solana, Polygon Labs, Circle,
  Fiserv, Adyen, KakaoPay, Base, Sierra.
- Exact "75M+" transaction count not independently verified; Solana
  claims ~65% of x402 volume. Direction confirmed, figure uncertain.

### WASM Component Model — "W3C standard (Sep 2025)"

- **Partially incorrect**. The Sept 2025 W3C milestone was **Wasm 3.0
  core**, not the Component Model.
- Component Model itself: **W3C Community Group, Phase 2/3**, not yet
  a W3C Recommendation. Production-ready for server/edge (Wasmtime,
  Fermyon Spin, Bytecode Alliance) but not standardized.
- **WASI 0.2** stable (Jan 2024); **WASI 0.3** experimental in Wasmtime,
  stable landing expected 2026.
- Implication for WhiteMagic: a full polyglot refactor to Component
  Model is **premature** (Option 5 in handoff menu). Wait for WASI 0.3
  + Component Model 1.0.

### Lakera Guard — "production, Dropbox customer"

- **Confirmed** (lakera.ai/customers, dropbox.tech/security). No
  correction needed.

### LocalAI / LlamaFarm — "mature, air-gapped"

- **Confirmed**. LocalAI bundles LocalAGI + LocalRecall + MCP-agent
  runtime, distributed mode, MIT-licensed. LlamaFarm v0.0.30,
  actively maintained, edge-focused, yaml-config-driven.
- Both are further along than a "spec-only MandalaOS" concept.

---

## Unchanged

- Strategic recommendation (orchestration overlay).
- Unique-strength list (5D holographic coordinates, resonance scoring,
  pattern extraction engine, scope-of-engagement tokens, Koka effect
  handlers, Galactic-Map archival model).
- Tier-1 fix list.

---

## Additional verified facts useful for positioning

- **EU AI Act** Annex III enforcement is **Aug 2, 2026** under current
  law (Digital Omnibus proposal may delay to Dec 2, 2027 but not yet
  adopted as of Apr 2026). See `ON_PREMISE_EDGE_AI_SCENARIOS.md` §5.
- **CA AB 3030** (GenAI patient-comm disclaimers) signed Sept 28, 2024,
  enforced via CA Health & Safety Code §1339.75.
- **Colorado AI Act (SB 24-205)** effective date pushed to
  **June 30, 2026** — closest US analogue to EU AI Act high-risk regime.
