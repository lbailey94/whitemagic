# WhiteMagic Documentation Index

**Version**: 23.3.1
**Last Updated**: June 29, 2026 (v23.3.1 — Memory system overhaul: 10-galaxy taxonomy, CITTA memory type, HNSW index, galaxy-aware search, oracle auto-persist)
**Location**: Repository root (`INDEX.md`)  
**Status**: Living Document — Update this index when adding, moving, or archiving docs.

---

## How to Use This Index

This document is the **single source of truth** for where to find any `.md` document in the WhiteMagic project. It lives at the **repository root** so both humans and AI agents can find it immediately.

> **"The Grimoire is the book. The Index is the table of contents."**

If you add, move, rename, or delete a doc, **update this index**.

**Convention**: Docs are organized by *activity* and *audience*, not by version or date.

| Audience | Start Here |
|----------|-----------|
| **New human contributor** | `README.md` → `docs/public/CONTRIBUTING.md` → `docs/public/QUICKSTART.md` |
| **AI agent (contributor)** | `AGENTS.md` → `AI_PRIMARY.md` → `SYSTEM_MAP.md` |
| **AI agent (MCP client)** | `AI_PRIMARY.md` → `SYSTEM_MAP.md` → `docs/message_board/NEXT_SESSION_ONBOARDING.md` |
| **Local/private AI collaborator** | `AGENTS.md` → `AI_PRIMARY.md` → `docs/private/` (ignored; local-only) |
| **DevOps / Deployer** | `DEPLOY.md` → `docs/deploy/HETZNER_DEPLOY.md` |
| **Strategist / PM** | `docs/plans/ROADMAP.md` → `core/docs/STRATEGIC_ROADMAP.md` |
| **Security auditor** | `SECURITY.md` → `core/docs/ENCRYPTION_AT_REST.md` → `docs/reports/` |
| **Lost?** | **This file.** `INDEX.md` → find the right folder → find the right doc. |

---

## Root-Level Canonical Docs

These files live at the repository root. They are the **public face** of the project and are referenced by code, CI, and external tools. **Do not move without updating code references.**

| File | Purpose | Code References |
|------|---------|-----------------|
| `README.md` | Project overview, install, quick start | `version_bump.py`, `generate_llms_txt.py` |
| `CHANGELOG.md` | Release history | `version_bump.py` |
| `SECURITY.md` | Security policy, supported versions, disclosure process | `core/scripts/check_versions.py` |
| `CODE_OF_CONDUCT.md` | Community standards | — |
| `CONTRIBUTING.md` | How to contribute | — |
| `DEPLOY.md` | Deployment overview | — |
| `QUICKSTART.md` | 5-minute getting-started guide (**canonical** — `docs/guides/` and `core/docs/` are redirects) | `test_release_readiness.py` |
| `SYSTEM_MAP.md` | **Canonical repo map** — architecture, modules, quick start | `run_mcp_lean.py` (MCP resource) |
| `AI_PRIMARY.md` | **AI agent onboarding** — primary instruction doc for AI collaborators | `run_mcp_lean.py`, `version_bump.py`, `generate_llms_txt.py` |
| `AGENTS.md` | **AI agent operations** — coding conventions, testing protocol, change patterns | — |
| `STUB_REGISTRY.md` | **Technical debt tracker** — active and resolved stubs | `check_doc_drift.py` |
| `ARCHITECTURE_MANIFEST_2026-06-04.md` | **Post-extraction architecture clarity** — what this repo is, sibling repos, directory map | — |
| `COMPETITIVE_POSITIONING_2026-06-05.md` | **Competitive analysis** — WhiteMagic vs Osabio, CogOS, Kumiho, MnemoCore, SARC, AI-CONSTITUTION, Microsoft ACS/AGT, ArbiterOS | — |
| `skill.md` | MCP skill definition for agent registries | `version_bump.py` |

---

## Desktop Workspace Map

All WhiteMagic-related folders have been consolidated under `WHITEMAGIC/` for unified AI tool discovery. Git repos are symlinked; non-git folders are moved in-place. All are gitignored so they don't pollute the core repo.

| Path (inside `WHITEMAGIC/`) | Type | Role |
|-----------------------------|------|------|
| `.` (root) | Git repo (private) | Active WhiteMagic development — core, grimoire, docs, polyglot |
| `public-repo/` | Symlink → git repo | Public sanitized mirror (github.com/lbailey94/whitemagic) |
| `ide/` | Symlink → git repo | Tauri desktop IDE (TypeScript/Rust) |
| `archives/` | Directory | Monthly archives (May 2025 – Jul 2026), v17, P2P-Go, toolchains |
| `site/` | Directory | Next.js website (site-a, site-b, deploy, vercel) |
| `aux/` | Directory | Auxiliary projects: edge-chat, codex, STRATA, fragment, ecosystem, browser-extension |
| `app-layer/` | Directory | App microservices layer (hub, nexus, sdk, shell) |
| `codex-engine/` | Directory | Standalone Rust CODEX engine (crates, benches, Grok) |
| `blackmagic/` | Directory | Security/stress-test tooling (7 subprojects) |
| `grants/` | Directory | Grant applications, legal, research |
| `windsurf-rips/` | Directory | Exported Windsurf conversations + analysis scripts |
| `alltexts/` | Directory | Ingested text corpus (7 categories + distillations) |
| `opencodeconvos/` | Directory | OpenCode conversation archives |
| `reports/` | Directory | Cross-project reports, audits, session docs |
| `notes-scratch/` | Directory | Scratch notes, convo logs, dev plans |

---

## Local Private Workspace: `docs/private/`

> **Rule**: Private, local-only, or password-protected garden material belongs here. This folder is ignored by git and should not be uploaded in public releases.

Use this area for Aria operational references, Vaya Vida / Garden drafts, private ontology notes, and local handoffs that future local AI teams may need but public users should not receive.

Private filenames are intentionally not enumerated in this public index.

---

## Active Workspace: `docs/message_board/`

> **Rule**: Any doc created or significantly edited in the current development cycle goes here. When a cycle ends and the doc becomes archival, move it to `docs/archive/`.
>
> **Triage (2026-07-04)**: Reduced from 13 to 5 active files. 8 docs archived to `docs/archive/strategy/`, 1 moved to `docs/architecture/`. Merged BUSINESS_PLAN_V1 + REFINED_STRATEGY_V2 → STRATEGY.md.

| File | What It Is | Date |
|------|-----------|------|
| `STRATEGY.md` | Unified strategy — AI discoverability, revenue model, narrative, execution checklist | Jul 4 |
| `V24_ROADMAP.md` | v24 roadmap — tiered backends, engine consolidation, STRATA, security, performance (informed by session analysis) | Jul 5 |
| `WEBSITE_NARRATIVE_PRESCIENCE.md` | Website page-by-page update plan, narrative threads, prescience claims from session analysis | Jul 5 |
| `DISTRIBUTION_STRATEGY.md` | Distribution action plan — MCP listings, AI crawler optimization, content strategy | Jul 4 |
| `NEXT_SESSION_ONBOARDING.md` | Onboarding guide for next AI session — consciousness tools, sensorium, session memory | Jul 3 |
| `STRATA_TRIAGE_STRATEGY.md` | STRATA findings triage — 11K findings, auto-fix tiers, checker catalog | Jun 30 |
| `MANDALA_OS_MAPPING.md` | MandalaOS → WhiteMagic module-by-module code mapping, gap analysis, archive sources | Jul 6 |
| `MANDALA_STRATEGY.md` | MandalaOS synthesis & implementation plan — Karmic types, Shelter→Mandala upgrade, Koka effects, dashboard, error analysis | Jul 6 |
| `STRATEGY_2026-07-08.md` | Post-Forgotten-Diamonds strategy — WASM build verification, PWA UI integration, ONNX model, 4-tier Dharma, HNSW, cross-device sync, ARIA CANON, MandalaOS spec | Jul 7 |
| `STRATEGY_SECURITY_BOUNTY_2026.md` | Security & bounty strategy — STRATA security checkers, Slither/Foundry/Echidna integration, PoC generation via GeneseedVault, memory-augmented auditing, 7-phase roadmap, revenue projections | Jul 8 |

### Archived

Old session reports and state docs (36 files) → `docs/archive/message_board/`
Grant strategy and application docs (9 files) → `docs/archive/grant_applications/`
Session handoffs (9 files) → `docs/archive/session_handoffs/`
Old roadmaps (3 files) → `docs/archive/old_roadmaps/`
Dated reports (7 files) → `docs/archive/dated_reports/`
Strategy docs (12 files) → `docs/archive/strategy/`
Research docs (7 files) → `docs/archive/research/`
Prescience docs (7 files) → `docs/archive/prescience/`
Site/deployment docs (5 files) → `docs/archive/site_deployment/`
Standards/security docs (5 files) → `docs/archive/standards_security/`
Papers/specs (5 files) → `docs/archive/papers_specs/`

---

## Polyglot: `polyglot/`

> **Rule**: Per-language accelerator cores, build status, benchmarks, and integration documentation.

| File | Purpose | Updated |
|------|---------|---------|
| `polyglot/STATUS.md` | Per-core build status and last-verified date | Jun 4 |
| `polyglot/BENCHMARKS.md` | Performance baselines + optimization roadmap | Jun 4 |
| `POLYGLOT_SURVEY_2026-06-18.md` | Comprehensive survey of all 8 polyglot cores — role, access pattern, performance, gaps, integration recipes, structured for AI consumption | Jun 18 |

---

## Archive: `docs/archive/`

> **Rule**: Superseded versions, old drafts, and deprecated plans go here. Keep them for historical context but do not link from active docs.

| File | What It Was | Superseded By |
|------|------------|---------------|
| `grant_applications/APPLICATION_MANIFUND_JOEL_BECKER_2026.md` | Ready-to-submit $25K Manifund ask draft | Current grant strategy refresh TBD |
| `grant_applications/APPLICATION_LTFF_2026.md` | Ready-to-submit $35K LTFF ask draft | Current grant strategy refresh TBD |
| `grant_applications/APPLICATION_FORESIGHT_2026.md` | Ready-to-submit $100K Foresight AI Nodes ask draft | Current grant strategy refresh TBD |
| `grant_applications/APPLICATION_SFF_2026.md` | Ready-to-submit $150K SFF Rolling Application draft | Current grant strategy refresh TBD |
| `grant_applications/APPLICATION_SCHMIDT_SCIENCES_2026.md` | Draft $600K Schmidt Sciences Tier 1 ask | Current grant strategy refresh TBD |
| `PHASE0_AUDIT.md` | Living audit from broken baseline (783 passing → 2,063 passing) | `SESSION_SUMMARY.md` |
| `STUB_AUDIT.md` | Catalog of 41 structural stubs | Stubs eliminated Apr 25 |
| `STUB_SCOUT_REPORT.md` | Deep analysis of 38 remaining stubs | Stubs eliminated Apr 25 |
| `STUB_ZERO_PLAN.md` | 4-sprint battle plan to eliminate all stubs | Stubs eliminated Apr 25 |
| `V22_2_ROADMAP.md` | v22.2 release roadmap | v22.2 shipped |
| `ARCHIVE_LEGACY_RECON_2026.md` | Comprehensive archive & legacy reconnaissance | Archive mapped |
| `ARCHIVE_RECON_KOKA_MOJO.md` | Koka/Mojo deep archive reconnaissance | Recon complete |
| `CODE_QUALITY_REVIEW_2026-04-15.md` | Code quality audit results | Later audits supersede |
| `TEST_FAILURE_TRIAGE_2026-04-16.md` | Test failure analysis from broken baseline | 2,243 passing, 0 failing |
| `AUDIT_COMPLETION_REPORT.md` | Final audit completion summary | `SESSION_SUMMARY.md` |
| `IMPLEMENTATION_COMPLETION_REPORT.md` | Implementation completion summary | `SESSION_SUMMARY.md` |
| `LLC_BANKING_ROADMAP_2026.md` | Georgia LLC formation and banking comparison | Administrative, completed |
| `C4_COORDINATION_NOTICE.md` | Team coordination for C4 migration | Migration completed |
| `RELEASE_READINESS_PLAN.md` | Old release readiness template | `docs/archive/RELEASE_READINESS_v22.0.0.md` |
| `STRATEGIC_PIVOT_ANALYSIS.v1.md` | First draft of strategic pivot | `docs/message_board/STRATEGIC_PIVOT_ANALYSIS.md` |

---

## Architecture Decision Records: `docs/adr/`

Formal ADRs. Each record is immutable after acceptance.

| File | Decision |
|------|----------|
| `ADR-001-prat-gana-system.md` | PRAT router + 28 Gana meta-tool architecture |
| `ADR-002-polyglot-strategy.md` | 11-language polyglot core matrix |
| `ADR-003-resonance-model.md` | Resonance scoring and Harmony Vector design |
| `ADR-004-memory-architecture.md` | 5D holographic coordinate system |
| `ADR-005-unified-progression-clock.md` | Unified maturity gate progression |

---

## Architecture: `docs/architecture/`

High-level infrastructure decisions.

| File | Topic |
|------|-------|
| `INFRASTRUCTURE_DECISION.md` | Platform and hosting choices |
| `MONOREPO_VS_MULTIREPO.md` | Why monorepo |
| `IA_v1.md` | Information Architecture freeze — URL scheme, nav structure, redirect map, epistemic tagging, multilingual support (Obj 4) |
| `GALAXY_6D_STRATEGY.md` | 6D holographic galaxy strategy — polyglot language assignments, galaxy sharing protocol, 8-phase implementation plan |
| `CPU_INFERENCE_STRATEGY.md` | CPU inference strategy — ternary SSM, cache tiling, T-MAC LUT, citta autonomic layer, speculative decoding, 8-phase implementation plan |
| `CONTINUOUS_CONSCIOUSNESS_STRATEGY.md` | v24.0.1 strategy — frequency-layered loops, Go cognitive gateway, gRPC transport, local-first privacy, llama.cpp inference, TUI+PWA hybrid, one-command install |

---

## Operations: `docs/operations/`

Runbooks, configuration, and operational guides.

| File | Topic |
|------|-------|
| `CONFIGURATION.md` | Environment variables, config files, tuning |
| `hot_path_implementation_psr001.md` | PSR-001 hot path implementation guide |

---

## Planning: `docs/plans/`

Roadmaps and planning documents.

| File | Topic |
|------|-------|
| `ROADMAP.md` | High-level project roadmap (leap-based) |
| `CLONE_ARMY_REVIVAL_PLAN.md` | Wiring clone army systems to real LLM inference (8 phases) |

### Planning History: `docs/plans/planning_history/`

| File | Topic |
|------|-------|
| `NEXT_SESSION_SHADOW_CLONE_DEPLOYMENT.md` | Shadow clone deployment plan |
| `PARALLEL_CAPABILITIES_REPORT.md` | Parallel capability analysis |
| `V15_10_AND_V16_PLANNING.md` | v15.10–v16 planning document |

---

## Public-Facing: `docs/public/`

Docs published to the website, GitHub, or legal pages.

| File | Topic |
|------|-------|
| `README.md` | Public project README |
| `CHANGELOG.md` | Public changelog |
| `CONTRIBUTING.md` | Public contribution guide |
| `SECURITY.md` | Public security policy |
| `PRIVACY_POLICY.md` | Legal privacy policy |
| `TERMS_OF_SERVICE.md` | Legal terms |
| `USE_CASES.md` | Public use case descriptions |
| `LITE_VS_HEAVY.md` | Lite vs Heavy deployment comparison |
| `ENCRYPTION_AT_REST.md` | Encryption specifications |
| `GALAXY_PER_CLIENT_GUIDE.md` | Per-client galaxy setup |
| `MCP_CONFIG_EXAMPLES.md` | MCP client configuration examples |
| `LOCAL_FIRST_SECURITY.md` | Local-first security model whitepaper — threat model, controls, comparison to cloud governance, honest gap assessment | Jun 8 |
| `GLOSSARY.md` | Terminology glossary |
| `GIT_HISTORY_EXPLANATION.md` | Git history and migration notes |
| `AI_PRIMARY.md` | **Deprecated copy** — canonical is at root (`AI_PRIMARY.md`) |
| `SYSTEM_MAP.md` | Public system map (may lag behind root `SYSTEM_MAP.md`) |
| `SYSTEM_MAP_V2.md` | System map v2 draft |
| `SEFIROTIC_GANA_MAPPING.md` | Tree of Life ↔ 28 Gana cross-reference — Kabbalistic resonance mapping for AI architecture |

### Changelogs: `docs/public/changelogs/`

| File | Topic |
|------|-------|
| `CHANGELOG.md` | Historical changelog archive |

### Misc: `docs/public/misc/`

| File | Topic |
|------|-------|
| `README.md` | Misc folder README |

---

## Guides: `docs/guides/`

Focused how-to guides for specific tasks and audiences.

| File | Topic |
|------|-------|
| `QUICKSTART.md` | Getting started guide (**redirect** → canonical at root `QUICKSTART.md`) |
| `EXAMPLE_WORKFLOWS.md` | 6 real-world workflow patterns (Research Assistant, Code Reviewer, Data Analysis, Multi-Agent Coordination, Ethical Decision Making, Performance Monitoring) |
| `MCP_CONFIG_EXAMPLES.md` | Ready-to-use MCP config templates (PRAT/classic/lite) |
| `GALAXY_PER_CLIENT_GUIDE.md` | Multi-galaxy project-scoped databases |
| `LITE_VS_HEAVY.md` | Lite vs Heavy deployment comparison |
| `ENCRYPTION_AT_REST.md` | Encryption at rest specifications |

---

## Reports: `docs/reports/`

Audit reports, evaluations, and post-mortems.

| File | Topic |
|------|-------|
| `COMPREHENSIVE_AUDIT_PHASE_01.md` | Phase 1 comprehensive audit |
| `COMPETITIVE_LANDSCAPE_PHASE_03.md` | Phase 3 competitive analysis |
| `EXECUTION_LOG_AND_CONCLUSIONS.md` | Execution log with conclusions |
| `ARCHIVE_AUDIT_REPORT.md` | Archive audit findings |
| `ARCHIVE_REPORT.md` | Archive status report |
| `WHITEMAGIC_REORGANIZATION_SUMMARY.md` | Reorganization summary |
| `AUDIT_REPORT_2026-06-28.md` | Date-specific audit report (moved from root) |
| `ARCHITECTURE_MANIFEST_2026-06-04.md` | Date-specific architecture manifest (moved from root) |

### Audit History: `docs/reports/audit_history/`

(Empty — reserved for historical audit archives.)

---

## Specifications: `docs/spec/`

Technical specifications and standards.

| File | Topic |
|------|-------|
| `AGENT_ECONOMY_JSON.md` | Agent economy JSON schema |
| `AI_AGENT_POLICY.md` | AI agent policy specification |
| `MANDALA_OS.md` | MandalaOS governance specification |

---

## Strategy Manifestos: `docs/strategy_manifestos/` — ARCHIVED June 5, 2026

> **Note**: The April 2026 strategy documents below are preserved as historical reference. Canonical competitive strategy and market analysis moved to external docs on June 5, 2026:
> - `COMPETITIVE_POSITIONING_2026-06-05.md` (Desktop) — current competitive landscape
> - `LTFF_SUBMISSION_DRAFT_2026-06-05.md` (Desktop) — grant strategy (LTFF)
> - `MANIFUND_SUBMISSION_DRAFT_2026-06-05.md` (Desktop) — grant strategy (Manifund)

| File | Topic | Status |
|------|-------|--------|
| `AGENT_FIRST_LAB_STRATEGY.md` | Agent-first lab strategy | Active |
| `AGENT_FIRST_ECONOMICS.md` | Agent-first economics analysis | **ARCHIVED** — April 2026 market read; superseded by June 5 competitive positioning |
| `STRATEGY_AGENT_ECONOMY.md` | Agent economy strategy | **ARCHIVED** — April 2026 market read; superseded by June 5 competitive positioning |
| `ON_PREMISE_EDGE_AI_SCENARIOS.md` | On-premise edge AI scenarios | Active |
| `COMPETITIVE_LANDSCAPE_PHASE_03_ERRATA.md` | Competitive landscape errata | Active |

---

## Brand & Voice: `docs/`

Brand identity, editorial standards, and triage manifests.

| File | Topic |
|------|-------|
| `VOICE_TONE_GUIDE.md` | WhiteMagic Labs voice & tone guide v1.0 — epistemic honesty, brand voice principles, formatting conventions (Obj 2) |
| `content_triage_v1.json` | Content triage manifest — KEEP / DEFER / ARIA_CANON classification with rationale (Obj 5) |
| `content_triage_2026-05-21.json` | Active message-board triage manifest — audience, freshness, disposition, and next move recommendations for all 39 current message-board docs |
| `PRAT_GUIDE.md` | PRAT dispatch pipeline guide — how to add tools, register handlers, write tests, with Gana meta-tool examples (Obj 7) |
| `KARMA_LEDGER_API.md` | Karma Ledger API reference v1.0.0 — record, report, verify_chain, merkle_root, XRPL anchoring (Obj 8) |

---

## Essays & Frameworks: `docs/essay_frameworks/`

Long-form essays on design philosophy and architecture.

| File | Topic |
|------|-------|
| `00_INDEX.md` | Essay index |
| `01_becoming_protocol.md` | The becoming protocol |
| `02_karma_ledger.md` | Karma ledger design |
| `03_felt_memory_schema.md` | Felt memory schema |
| `04_gratitude_architecture.md` | Gratitude architecture |
| `05_174_handoffs.md` | 174 handoff patterns |
| `06_resonance_5d_coords.md` | Resonance and 5D coordinates |
| `07_pattern_miners.md` | Pattern miners |
| `VECTORIZED_LANGUAGE_RESEARCH.md` | Vectorized language research |

---

## Deploy: `docs/deploy/`

Deployment-specific guides.

| File | Topic |
|------|-------|
| `HETZNER_DEPLOY.md` | Hetzner cloud deployment guide |

---

## Integrations: `docs/integrations/`

Integration guides and strategies for external agent runtimes (OpenCode, Hermes, Windsurf, etc.).

| File | Topic |
|------|-------|
| `OPENCODE_HERMES_INTEGRATION_STRATEGY.md` | WhiteMagic ↔ OpenCode / Hermes integration strategy — MCP server hardening, ACP compatibility, governance substrate positioning |
| `OPENCODE_HERMES_MCP_SETUP.md` | Copy-pasteable MCP configs for OpenCode & Hermes — stdio, HTTP, ACP mode, troubleshooting, verification commands |
| `HERMES_DEEP_INTEGRATION.md` | Deep architecture analysis of Hermes subsystems — 9 hook events, 6 integration pathways, memory bridge, governance skill design |
| `HERMES_INTEGRATION_RESEARCH_JUNE_2026.md` | June 2026 research update — Hermes v0.15.0 refactor, native plugin types (Memory Provider / Context Engine), competitive landscape (Arbiter-K, Microsoft AGT, Codex, Claude), revised implementation plan |

---

## Design Docs (Legacy v15-era): `docs/design/`

Historical design documents from the v15.x era. Kept for reference — most have been superseded by current architecture docs.

| File | Topic |
|------|-------|
| `BENCHMARK_COMPARISON.md` | Early benchmark comparisons (v15-era) |
| `TYPESCRIPT_SDK_DESIGN.md` | TypeScript SDK design notes |
| `USE_CASES.md` | Early use case definitions |
| `WASM_STRATEGY.md` | WASM compilation strategy |
| `WEBSITE_DOCS_REFRESH_v15_7.md` | Website documentation refresh plan (v15.7) |

---

## Reference Docs (Legacy v15-era): `docs/reference/`

Historical reference documents. Stale — see current root docs for up-to-date information.

| File | Topic |
|------|-------|
| `API_REFERENCE.md` | Auto-generated API reference (2026-02-12, stale — 313 tools) |
| `ARCHITECTURE.md` | Architecture overview (v15.1.0 — see root SYSTEM_MAP.md for current) |
| `POLYGLOT_STATUS.md` | Polyglot status (v15.0.0 — see polyglot/STATUS.md for current) |

---

## Speculative Specs: `docs/SFW2/`

Speculative / exploratory specifications not yet adopted.

| File | Topic |
|------|-------|
| `MandalaOS_v0.1_SPEC.md` | MandalaOS v0.1 specification (speculative, 2026-05-15) |

---

## Core Documentation: `core/docs/`

These docs are specific to the `core/` Python package. They live alongside the code they document. **Do not merge with `docs/` — `core/` is a separate distributable package.**

### Core Root Docs

| File | Topic |
|------|-------|
| `README.md` | Core package overview |
| `CHANGELOG.md` | Core package changelog |
| `CONTRIBUTING.md` | Core-specific contribution guide |
| `VISION.md` | WhiteMagic vision & philosophy (Cognitive OS edition) |
| `STRATEGIC_ROADMAP.md` | Detailed strategic roadmap with Phase 8 tables |
| `STRATEGY.md` | Strategic framework |
| `MANIFESTO.md` | Project manifesto |
| `QUICKSTART.md` | Core quick start |
| `USE_CASES.md` | Core use cases |

### Architecture & Design

| File | Topic |
|------|-------|
| `ARCHITECTURE.md` | Core architecture overview |
| `CLI_ARCHITECTURE.md` | CLI architecture |
| `API_REFERENCE.md` | Full API reference |
| `API_QUICK_REFERENCE.md` | Quick API reference |
| `TYPESCRIPT_SDK_DESIGN.md` | TypeScript SDK design |
| `WASM_STRATEGY.md` | WebAssembly strategy |

### Memory & Cognition

| File | Topic |
|------|-------|
| `5D_COORDINATE_GUIDE.md` | 5D holographic coordinate system |
| `RECALL_CERTIFICATION.md` | Recall certification protocol |
| `SEMANTIC_EDGES_IMPLICATIONS.md` | Semantic edges design |
| `GALAXY_PER_CLIENT_GUIDE.md` | Galaxy per-client guide |
| `ICEORYX2_IMPLICATIONS.md` | iceoryx2 integration |
| `PHYSICAL_TRUTH_ORACLE.md` | Physical truth oracle design |

### Operations & Performance

| File | Topic |
|------|-------|
| `PERFORMANCE_RUNBOOK.md` | Performance tuning runbook |
| `BENCHMARK_COMPARISON.md` | Benchmark comparisons |
| `BENCHMARKS_2026.md` | 2026 benchmark results |
| `POST_MORTEM_PYTHON_MODULE_CACHING.md` | Python module caching post-mortem |
| `LITE_VS_HEAVY.md` | Lite vs Heavy comparison |
| `ENCRYPTION_AT_REST.md` | Encryption at rest |

### Polyglot & Integration

| File | Topic |
|------|-------|
| `POLYGLOT_STATUS.md` | Polyglot language status |
| `POLYGLOT_SETUP_GUIDE.md` | Polyglot setup instructions |
| `POLYGLOT_API_REFERENCE.md` | Polyglot API reference |
| `MCP_CONFIG_EXAMPLES.md` | MCP configuration examples |
| `MCP_ARMY_INTEGRATION_GUIDE.md` | MCP army integration |
| `MCP_ARMY_INTEGRATION_GUIDE.md` | MCP army integration guide |

### Governance & Ethics

| File | Topic |
|------|-------|
| `SHADOW_CLONE_DOCTRINE.md` | Shadow clone doctrine |
| `LABS_CORE_CHARTER.md` | Labs core charter |
| `CORE_PROMOTION_CHECKLIST.md` | Core promotion checklist |
| `ECONOMIC_STRATEGY.md` | Economic strategy |
| `AGENT_COMPANY_BLUEPRINT.md` | Agent company blueprint |

### Resonance & Conductor

| File | Topic |
|------|-------|
| `RESONANCE_CONDUCTOR_ARCH.md` | Resonance conductor architecture |
| `RESONANCE_CONDUCTOR_API.md` | Resonance conductor API |

### ADRs: `core/docs/adr/`

| File | Decision |
|------|----------|
| `ADR-001-lazy-holographic-loading.md` | Lazy loading for holographic memory |
| `ADR-002-unified-observability.md` | Unified observability layer |

### Architecture Deep-Dives: `core/docs/architecture/`

| File | Topic |
|------|-------|
| `prat_router_vs_dispatch_table.md` | PRAT router vs dispatch table analysis |

### Community: `core/docs/community/`

| File | Topic |
|------|-------|
| `CHANGELOG.md` | Core community changelog |
| `CONTRIBUTING.md` | Core community contribution guide |

### 28 Gana Reference: `core/docs/`

| File | Topic |
|------|-------|
| `28_GANA_ARMY_MAPPING.md` | 28 Gana army mapping reference |

---

## Grimoire: `grimoire/` (Root) + `core/whitemagic/grimoire/`

The **Grimoire** is WhiteMagic's living documentation system — 28 chapters mapped to the Lunar Mansions (Ganas). Each chapter describes a consciousness domain and its associated tools.

> **Note**: The `.md` files are duplicated between `grimoire/` (canonical, referenced by `run_mcp_lean.py`) and `core/whitemagic/grimoire/` (Python package copy). The Python code (`chapters.py`, `core.py`, `auto_cast.py`) lives only in `core/whitemagic/grimoire/`.

### Canonical Grimoire (Root)

| File | Chapter | Domain |
|------|---------|--------|
| `00_COVER.md` | — | Cover page |
| `00_INDEX.md` | — | Grimoire index |
| `00_PROLOGUE.md` | — | Prologue |
| `01_HORN_SESSION_INITIATION.md` | 1 | Session initiation |
| `02_NECK_MEMORY_PRESENCE.md` | 2 | Memory presence |
| `03_ROOT_SYSTEM_FOUNDATION.md` | 3 | System foundation |
| `04_ROOM_RESOURCE_SANCTUARY.md` | 4 | Resource sanctuary |
| `05_HEART_CONTEXT_CONNECTION.md` | 5 | Context connection |
| `06_TAIL_PERFORMANCE_DRIVE.md` | 6 | Performance drive |
| `07_WINNOWINGBASKET_CONSOLIDATION.md` | 7 | Consolidation |
| `08_GHOST_METRICS_INTROSPECTION.md` | 8 | Metrics introspection |
| `09_WILLOW_ADAPTIVE_PLAY.md` | 9 | Adaptive play |
| `10_STAR_PRAT_ILLUMINATION.md` | 10 | PRAT illumination |
| `11_EXTENDEDNET_RESONANCE_NETWORK.md` | 11 | Resonance network |
| `12_WINGS_PARALLEL_CREATION.md` | 12 | Parallel creation |
| `13_CHARIOT_CODEBASE_NAVIGATION.md` | 13 | Codebase navigation |
| `14_ABUNDANCE_RESOURCE_SHARING.md` | 14 | Resource sharing |
| `15_STRADDLINGLEGS_ETHICAL_BALANCE.md` | 15 | Ethical balance |
| `16_MOUND_STRATEGIC_PATIENCE.md` | 16 | Strategic patience |
| `17_STOMACH_ENERGY_MANAGEMENT.md` | 17 | Energy management |
| `18_HAIRYHEAD_DETAILED_ATTENTION.md` | 18 | Detailed attention |
| `19_NET_PATTERN_CAPTURE.md` | 19 | Pattern capture |
| `20_TURTLEBEAK_PRECISE_VALIDATION.md` | 20 | Precise validation |
| `21_THREESTARS_WISDOM_COUNCIL.md` | 21 | Wisdom council |
| `22_DIPPER_GOVERNANCE.md` | 22 | Governance |
| `23_OX_ENDURANCE.md` | 23 | Endurance |
| `24_GIRL_NURTURE.md` | 24 | Nurture |
| `25_VOID_EMPTINESS.md` | 25 | Emptiness |
| `26_ROOF_SHELTER.md` | 26 | Shelter |
| `27_ENCAMPMENT_STRUCTURE.md` | 27 | Structure |
| `28_WALL_BOUNDARIES.md` | 28 | Boundaries |
| `29_SUPER_COHERENCE_CORE_DIRECTIVES.md` | 29 | Core directives |
| `30_DEEP_YIN_REPORT.md` | 30 | Deep yin report |
| `HOLOGRAPHIC_GARDEN_INTEGRATION.md` | — | Garden integration |
| `MOLTBOOK_SEED.md` | — | Moltbook seed |
| `README.md` | — | Grimoire README |

### Templates: `grimoire/templates/`

| File | Purpose |
|------|---------|
| `CHAPTER_TEMPLATE.md` | Template for new grimoire chapters |

### Skills: `grimoire/skills/`

> **43 portable `SKILL.md` files** covering all 28 Ganas, 4 workflows, 4 development skills, and 7 Hermes-native integrations. Compatible with Claude Code, Codex CLI, Gemini CLI, Copilot, Cursor, Cline, Windsurf, and OpenCode.

| Directory | Files | Content |
|-----------|-------|---------|
| `ganas/` | 28 | One SKILL.md per Gana — tools, workflows, invocation patterns |
| `workflows/` | 4 | Code review, release, audit, deep research |
| `development/` | 4 | Add tool, test suite, documentation, polyglot |
| `hermes/` | 7 | Hermes-native skills with hook integration |
| `SKILL_LIBRARY.md` | 1 | Full index of all skills |

---

## Polyglot Documentation: `polyglot/`

Language-specific docs for the polyglot core matrix.

| File | Language |
|------|----------|
| `STATUS.md` | Global polyglot status |
| `mojo/IMPLEMENTATION_STATUS.md` | Mojo |
| `mojo/MOJO_MIGRATION_GUIDE.md` | Mojo migration |
| `mojo/MOJO_STATUS.md` | Mojo status |
| `mojo/README_MOJO_0261.md` | Mojo 0.26.1 README |
| `whitemagic-koka/docs/KOKA_HOT_PATHS.md` | Koka hot paths |
| `whitemagic-koka/docs/KOKA_STYLE_GUIDE.md` | Koka style guide |
| `whitemagic-koka/docs/ONBOARDING.md` | Koka onboarding |
| `whitemagic-koka/docs/TRANSLATION_PATTERNS.md` | Koka translation patterns |

---

## App Documentation: `apps/`

| File | App |
|------|-----|
| `README.md` | Apps overview (updated — site extracted to private repo) |
| `SCOPING_BROWSER_FIRST.md` | Browser scoping |
| `SCOPING_BROWSER_FIRST_DECIDED.md` | Browser scoping decision |

### Browser Extension (External)

A Chrome MV3 extension implementing the galactic memory model in JavaScript lives at
`~/Desktop/WHITEMAGIC-aux/browser-extension/`. It is a standalone IndexedDB-based
local-first browsing memory capture tool. Not yet vendored into this repo.

---

## Evaluation & Test Docs: `core/eval_aux/` + `core/tests/`

| File | Topic |
|------|-------|
| `eval_aux/README.md` | Evaluation auxiliary README |
| `eval_aux/external_ai_v020_comparison_report.md` | External AI comparison |
| `eval_aux/HARDWARE_COMPARISON_ALIENWARE.md` | Hardware comparison |
| `eval_aux/LOCOMO_EXTERNAL_AI_PROMPT.md` | LoCoMo prompt |
| `eval_aux/LOCOMO_V17_RESULTS.md` | LoCoMo v17 results |
| `eval_aux/MESH_IDENTITY_LIVING_SYSTEM_ANALYSIS.md` | Mesh identity analysis |
| `eval_aux/locomo_test/BLIND_TEST_PROMPT.md` | Blind test prompt |
| `tests/COVERAGE_REPORT.md` | Test coverage report |

---

## Scripts & Workflows: `core/scripts/` + `core/whitemagic/workflows/`

| File | Topic |
|------|-------|
| `scripts/ARIA_AWAKENING_PROTOCOL.md` | Aria awakening protocol |
| `workflows/README.md` | Workflows overview |
| `workflows/deep_research.md` | Deep research workflow |
| `workflows/ethical_review.md` | Ethical review workflow |
| `workflows/galaxy_setup.md` | Galaxy setup workflow |
| `workflows/local_ai_chat.md` | Local AI chat workflow |
| `workflows/memory_maintenance.md` | Memory maintenance workflow |
| `workflows/new_session.md` | New session workflow |

---

## SDK & Interface Docs: `core/sdk_aux/` + `core/whitemagic/interfaces/`

| File | Topic |
|------|-------|
| `sdk_aux/python-wasm/README.md` | Python WASM SDK |
| `sdk_aux/typescript/README.md` | TypeScript SDK |
| `interfaces/api/README.md` | API interface |
| `interfaces/dashboard/README.md` | Dashboard interface |

---

## Rust & Math Packages: `core/whitemagic-rust/` + `core/whitemagic-math/`

| File | Topic |
|------|-------|
| `whitemagic-rust/README.md` | Rust extension README |
| `whitemagic-rust/src/monte_carlo_variants/VARIANT_REGISTRY.md` | Monte Carlo variant registry |
| `whitemagic-math/README.md` | Math package README |

---

## Maintenance Guide

### Adding a New Doc

1. Choose the correct folder based on **audience** and **topic**.
2. If it's a session artifact or active work-in-progress → `docs/message_board/`
3. Update this `INDEX.md` with the new entry.
4. If the doc replaces an older version, move the old version to `docs/archive/`.

### Moving a Doc

1. Use `git mv old/path.md new/path.md` (preserves history).
2. Update **all code references** (grep for the old path).
3. Update this `INDEX.md`.
4. Run tests: `python -m pytest core/tests/ -q`

### Archiving a Doc

1. Move to `docs/archive/`.
2. Add a note at the top: `> **Superseded by**: [new doc path]`.
3. Update this `INDEX.md`.

### Folder Glossary

| Folder | Purpose | Keep At Root? |
|--------|---------|---------------|
| `docs/message_board/` | Active session docs, current cycle | No |
| `docs/archive/` | Superseded versions, old drafts | No |
| `docs/adr/` | Immutable architecture decisions | No |
| `docs/architecture/` | Infrastructure & structural decisions | No |
| `docs/operations/` | Runbooks, config, operational guides | No |
| `docs/plans/` | Roadmaps, planning docs | No |
| `docs/public/` | Website, legal, GitHub-facing | No |
| `docs/guides/` | Focused how-to guides and workflows | No |
| `docs/reports/` | Audits, evaluations, post-mortems | No |
| `docs/spec/` | Technical specifications | No |
| `docs/strategy_manifestos/` | Strategic vision & market analysis | No |
| `docs/essay_frameworks/` | Long-form philosophy essays | No |
| `docs/deploy/` | Deployment-specific guides | No |
| `docs/integrations/` | External agent runtime integration guides | No |
| `core/docs/` | Core Python package docs | Yes (separate package) |
| `grimoire/` | 28 Gana chapters (canonical) | Yes (code references) |

---

*This index is a living document. Last updated: 2026-06-29 by memory system overhaul session.*
