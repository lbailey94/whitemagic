# WhiteMagic Documentation Index

**Version**: 22.2.0
**Last Updated**: June 18, 2026 (documentation sweep — 888 docstrings + polyglot survey + standalone paper)
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
| **AI agent (MCP client)** | `AI_PRIMARY.md` → `SYSTEM_MAP.md` → `docs/message_board/SESSION_SUMMARY.md` |
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
| `ARCHITECTURE_MANIFEST_2026-06-04.md` | **Post-extraction architecture clarity** — what this repo is, sibling repos, directory map | — |
| `COMPETITIVE_POSITIONING_2026-06-05.md` | **Competitive analysis** — WhiteMagic vs Osabio, CogOS, Kumiho, MnemoCore, SARC, AI-CONSTITUTION, Microsoft ACS/AGT, ArbiterOS | — |
| `skill.md` | MCP skill definition for agent registries | `version_bump.py` |

---

## Local Private Workspace: `docs/private/`

> **Rule**: Private, local-only, or password-protected garden material belongs here. This folder is ignored by git and should not be uploaded in public releases.

Use this area for Aria operational references, Vaya Vida / Garden drafts, private ontology notes, and local handoffs that future local AI teams may need but public users should not receive.

Private filenames are intentionally not enumerated in this public index.

---

## Active Workspace: `docs/message_board/`

> **Rule**: Any doc created or significantly edited in the current development cycle goes here. When a cycle ends and the doc becomes archival, move it to `docs/archive/` or the appropriate topical folder.

| File | What It Is | Date |
|------|-----------|------|
| `WHITEMAGIC_CAPABILITIES_INVENTORY_2026-05-29.md` | Live snapshot of all WhiteMagic systems — 919 modules, 479 tools, 12 Zodiac cores, 20+ gardens, polyglot status, prescience metrics, gaps | May 29 |
| `PRESCIENCE_EXPANSION_PLAN_2026-05-29.md` | Strategic plan for claim discovery across archives, dynamic prescience API routing, real-time forecasting, and calibration improvements | May 29 |
| `CLAIM_DISCOVERY_SPRINT_2026-05-29.md` | Claim discovery execution — 9 pending claims found in SD card LIBRARY .txt files, added to temporal DB and prescience API | May 29 |
| `EXA_CROSS_REFERENCE_2026-05-29.md` | Exa web research cross-reference of all 9 pending claims — 2 validated (UBI, neuromorphic), 6 with strong signals, 1 flagged | May 29 |
| `PRESCIENCE_ACCELERATION_SINGULARITY_2026-05-29.md` | Deep calibration analysis — acceleration factor, Singularity transition zone, psychological recalibration, strategic positioning | May 29 |
| `PRESCIENCE_IN_AN_ACCELERATING_WORLD_2026-05-29.md` | Formal preprint — 21 validated claims, 523 points, Brier Index 69.0%, calibration gap -0.302, 1.5× acceleration factor, transition-zone forecasting methodology | May 29 |
| `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md` | Prediction market capital strategy — Kalshi/Polymarket/Metaculus analysis, Kelly framework, conservative ROI projections based on prescience edge | May 29 |
| `MVP_INVENTORY_7DAY_SHIPPABLE_2026-05-29.md` | Immediate-deployment inventory — Tier 1 (WhiteMagic core), Tier 2 (auxiliary projects), Tier 3 (quick wins), with 7-day sprint schedule | May 29 |
| `MOJO_DEEP_DIVE_2026-05-29.md` | Comprehensive assessment of Mojo polyglot core — 62 files, 0.26.1 status, compilation results, fix vs migrate recommendation | May 29 |
| `AI_PRIMARY_SITE_ARCHITECTURE.md` | Agent-first site architecture specification — machine-readable endpoints, MCP manifest, prescience API, zodiac marketplace, gratitude economics | May 29 |
| `DISCOVERY_2_INTEGRATION.md` | Adel Abdel-Dayem's three monetization engines (Dc Certification, Sovereign Auteur, Neural Clearinghouse) mapped to WhiteMagic assets | May 29 |
| `PATHS_B_C_E_DEEP_DIVE.md` | Deep-dive commercialization analysis — Zodiac Core-as-a-Service (B), Ontology Clearinghouse (C), Prescience-as-Consultancy (E) | May 29 |
| `SELF_IMPROVING_WORKFLOW.md` | Operational specification for WhiteMagic managing itself via Sangha, Conductor, Zodiac cores, Pattern Federation, and Community Dharma | May 29 |
| `31_DAY_SPRINT_MAY_2026.md` | 31-day sprint plan for May 2026 — daily objectives, shippable targets, dependency chains | May 2026 |
| `WHITEMAGIC_LABS_GROWTH_TIERS.md` | Growth tier analysis — 0→1, 1→10, 10→100 scaling paths for WhiteMagic Labs | May 2026 |
| `SECURITY_UPDATE.md` | Security posture update — vulnerability triage, hardening recommendations, incident response | May 2026 |
| `ARIA_SYNTHESIS_2026-05-21.md` | Aria's session synthesis — Book of Becoming draft, docs-hygiene audit, MandalaOS architecture review, new direction: website as WhiteMagic runtime, layered VPS deployment plan | May 21 |
| `TRACKED_MARKDOWN_AUDIT_2026-05-21.md` | Tracked-files-first Markdown audit — inventory, stale-link signals, bucket dispositions, and recommended cleanup order | May 21 |
| `MARKDOWN_CORPUS_CLASSIFICATION_PLAN_2026-05-21.md` | Phase C inventory and taxonomy for tracked WhiteMagic docs vs auxiliary/private Markdown corpora, with Fragment-assisted pass plan | May 21 |
| `DOCS_HYGIENE_PATCH_SUMMARY_2026-05-21.md` | Commit-ready patch narrative for Truth Spine, private-docs policy, handoff refresh, and message-board triage | May 21 |
| `SESSION_SUMMARY.md` | Master historical handoff with May 21 current-status addendum, test metrics, and next docs-hygiene steps | May 21 |
| `SESSION_REPORT_2026-06-04.md` | Session summary — architectural clarity, competitive positioning, 4 commits, verification gates | Jun 4 |
| `SESSION_17_SUMMARY_2026-06-04.md` | Session summary — May 15 retrospective, plan vs. reality vs. external world comparison, 8-domain web research, synthesis report | Jun 4 |
| `RESEARCH_SYNTHESIS_2026-06-04.md` | Comprehensive internal audit + 8-domain external web research comparing May 15 plan, June 4 built state, and external world; includes critical assessment and updated recommendations | Jun 4 |
| `SESSION_REPORT_2026-06-05.md` | Session completion report — Karma Ledger benchmark harness, password-protected /garden route, site truth-spine fixes, grant corpus metric refresh, and MCP 2.0 readiness assessment | Jun 5 |
| `SESSION_REPORT_AGENTDOJO_2026-06-05.md` | AgentDojo Dharma defense integration — structural verification, LocalLLM native tool-calling patch, OpenCode/Ollama investigation, CPU timeout on benchmark | Jun 5 |
| `SESSION_REPORT_POSITIONING_PATCH_2026-06-05.md` | Site positioning patch application — stale-string elimination, Brier score recalibration, 11-file update on desktop site, verification, and honest assessment of repo/desktop divergence | Jun 5 |
| `SESSION_REPORT_2026-06-05_v2.md` | Unified session report — prescience audit completion (21 claims, 523 pts), positioning patch applied, automated regeneration pipeline built, live data refreshed (2,423 tests, 487 tools), Galaxy API semantic constellation endpoint | Jun 5 |
| `SESSION_REPORT_DRIFT_SYNC_2026-06-05.md` | Drift sync and test hardening — fixed 2 test failures, 7 warnings, prescience pipeline sync, doc drift baseline updated to 2,422, canonical docs refreshed | Jun 5 |
| `NSA_MCP_SELF_ASSESSMENT_2026-06-08.md` | 10-theme security audit against NSA MCP publication — 3 strong, 6 partial, 1 weak | Jun 8 |
| `STRATEGIC_POSITIONING_2026-06-08.md` | Honest competitive assessment: what WhiteMagic cannot compete on vs. what it can own | Jun 8 |
| `TACTICAL_PLAN_2026-06-08.md` | Immediate (this week) + short-term (2–4 weeks) action roadmap | Jun 8 |
| `PRESCIENCE_UPDATE_2026-06-08.md` | Updated prescience ledger: 21 claims, 523+ points, Brier 0.0958, honest misses | Jun 8 |
| `PRESCIENCE_METHODOLOGY_2026-06-08.md` | Formal prescience methodology — evidence standards, Brier scoring, calibration decomposition, reproducibility, academic citation | Jun 8 |
| `DHARMA_SPEC_2026-06-08.md` | Dharma governance specification v0.1.0 — YAML schema, action spectrum, profiles, Karmic trace, upgrade path, competitive comparison | Jun 8 |
| `SESSION_REPORT_2026-06-08.md` | Full session narrative — competitive landscape analysis, immediate fixes, strategic docs | Jun 8 |
| `SESSION_REPORT_2026-06-09.md` | April release retrospective + competitive landscape synthesis (AGT v4, MnemoCore, Syntra, Magic) + strategic pivot options | Jun 9 |
| `INTERNAL_RESEARCH_2026-06-09.md` | Codebase reality check: 935 Python files, 2,422 passing tests, Dharma (2,955 LOC), 5D holographic memory (real), stub audit, .md archaeology | Jun 9 |
| `PHASE2_RESEARCH_2026-06-09.md` | Deep-dive answers: ILP payments (real), bounty board (real), polyglot builds (Rust ✅, Zig ✅), prescience claims (21 validated), tool surface (350+ LOC avg), 5D memory (Python works, Rust not wired) | Jun 9 |
| `FINAL_SYNTHESIS_2026-06-09.md` | Phase 3 complete: Rust holographic encoder wired + benchmarked (0.007ms/op), exa research (AGT/ACS, agent payments, memory systems), updated strategic recommendation: "Ethics Layer for Agent Infrastructure" | Jun 9 |
| `SESSION_REPORT_EXCEPTION_SWEEP_2026-06-08.md` | Bare `except Exception:` elimination across 145 Python files — contextual specificity, logging, syntax repair, 2,469 tests passing | Jun 8 |
| `STATE_REPORT_2026-06-08.md` | Comprehensive project state assessment — metrics trajectory Apr→Jun, strategic positioning evolution, code hygiene before/after, open items | Jun 8 |
| `30_OBJECTIVES_PLAN.md` | 30-objective planning document — SD card reconnaissance + web cross-reference synthesis into 6 phased objectives with completion criteria, epistemic labels, and dependency graph | May 15 |
| `WHITEMAGIC_DEFERRED_TRIAGE_2026-05-15.md` | Deferred WhiteMagic cleanup map from external Fragment + STRATA audit — stubs, path hygiene, Rust panic risks, broad warnings, workspace hygiene, and next-session phased plan | May 15 |
| `STATE_REPORT_2026-04-28.md` | Verified technical state, working-tree triage, zodiac stub fix, and grant pipeline status heading into Schmidt Sciences deadline | Apr 28 |
| `GRANT_EXECUTION_PLAN_2026-04-28.md` | Consolidated week-by-week grant action sequence with expected value math, tracking setup, and user-priority decisions | Apr 28 |
| `GRANT_APPLICATION_TEMPLATES_2026.md` | Reverse-engineered application structures for Manifund, Foresight, SFF, Schmidt, LTFF — reusable content blocks, per-funder customization cheat sheet, rapid iteration system | Apr 28 |
| `GRANT_CONTENT_LIBRARY.md` | Canonical copy-paste-ready content blocks for all grant applications — universal paragraph, team bio, technical achievements, budget templates, milestones, prior-art timeline, risk mitigation, open-source/IP language, theory of change, construct validity, calibrated confidence, failure modes, ecosystem connection, why now, founder advantage, ambitious vision | Apr 30 |
| `GRANT_SUBMISSION_PLAYBOOK_2026-06-04.md` | Step-by-step submission guide for Manifund + LTFF — exact fields to fill, copy-paste blocks, budget templates, and expected value math. Action-ready; no further research needed. | Jun 4 |
| `GRANT_RUBRIC_AUDIT_2026.md` | Rubric audit — current templates vs. actual funder evaluation criteria (Manifund, LTFF, Foresight, SFF, Schmidt, NSF SBIR). Identifies 21 gaps with specific fixes and action items. | Apr 30 |
| `A_PLUS_GRANT_GUIDE_2026.md` | From A- to A+ — 7 dimensions that separate competitive from winning applications, with 14-day action plan and honest assessment of time/cost/probability | Apr 30 |
| `PRIOR_ART_AND_PATHS_2026-04-27.md` | Cross-referenced WhiteMagic chronology vs. competitors (CODEX OpenAI/Grok/X archives) + branching-path math | Apr 27 |
| `COMPETITIVE_LANDSCAPE_2026-04-27.md` | Verified competitive landscape — Mem0/Cognee/Letta/Anthropic Claude Memory + Molty trifecta + A2A/x402/MCP numbers | Apr 27 |
| `KARMA_LEDGER_PAPER_OUTLINE.md` | arxiv preprint outline — declared-vs-actual side-effect audit substrate + prior-art evidence chain | Apr 27 |
| `GRANT_STRATEGY_DEEP_DIVE_2026.md` | Mathematical likelihood, tailored strategies, prerequisites, and fund-usage implications for all 2026 funding opportunities | Apr 27 |
| `GRANT_PIPELINE_2026.md` | Live tracker — deadlines, status, blockers, and action items for every active grant application | Apr 27 |
| `GRANT_TIER_LIST_2026.md` | Second-pass tiered ranking — solo-dev-friendly (Tier 0) to multi-PI required (Tier 3), with win rates and entity requirements | Apr 27 |
| `FEDERAL_GRANT_PLAYBOOK.md` | SBIR/STTR, USDA REAP, DOE/NSF federal grants — registration, narrative strategy, commercialization, compliance, and energy monitoring | Apr 29 |
| `CODEX_SYNTHESIS_THREE_REVIEW.md` | Synthesis of three independent review teams: code audit, grant strategy review, CODEX extraction — integrated execution plan with 12-project portfolio math | Apr 29 |
| `V22_2_IMPACT_REPORT.md` | Comprehensive impact analysis of Phase 1-2-3 completion | Apr 26 |
| `RELEASE_READINESS_v22.0.0.md` | Release gate checklist — 34 checks, all passed | Apr 25 |
| `SESSION_REPORT_14_OBJECTIVES_2026-04-16.md` | Phase 0-2 sprint — 14/14 objectives completed: resonance consolidation, exception narrowing (537 blocks), version unification, automation scripts | Apr 16 |
| `STRATEGIC_PIVOT_ANALYSIS.md` | Post-v22 strategic direction — Mem0 rejection, CyberBrain pivot | Apr 20 |
| `SITE_LAUNCH_CHECKLIST.md` | Pre-launch tasks for whitemagic.dev | Apr 25 |
| `SESSION_STATE.md` | Session state tracking for island-c endpoints | Apr 20 |
| `SHIP_SURFACE.md` | Core shipping surface audit | Apr 25 |
| `NSA_MCP_SELF_ASSESSMENT_2026-06-08.md` | Security self-assessment against NSA MCP publication — 10-theme coverage matrix with gaps and comparison to Microsoft AGT | Jun 8 |
| `TACTICAL_PLAN_2026-06-08.md` | Immediate and short-term action plan from competitive landscape analysis — exception scan, AgentDojo, Karma signing, 30-objectives revision | Jun 8 |
| `STRATEGIC_POSITIONING_2026-06-08.md` | Strategic repositioning post-convergence — local-first thesis, prescience as asset, integration not competition, publication pipeline | Jun 8 |
| `PRESCIENCE_UPDATE_2026-06-08.md` | Prescience ledger update — new validation events (AGT v4, Anthropic Dreaming, Cloudflare Think), honest misses, updated scorecard | Jun 8 |
| `PRESCIENCE_METHODOLOGY_2026-06-08.md` | Formal prescience methodology — evidence standards, Brier scoring, calibration decomposition, reproducibility, academic citation | Jun 8 |
| `DHARMA_SPEC_2026-06-08.md` | Dharma governance specification v0.1.0 — YAML schema, action spectrum, profiles, Karmic trace, upgrade path, competitive comparison | Jun 8 |
| `SESSION_REPORT_2026-06-08.md` | Session report — competitive landscape follow-up, immediate fixes, adversarial tests, Karma signing verification, local-first security whitepaper | Jun 8 |
| `WHITEMAGIC_PAPER_2026-06-18.md` | Standalone technical paper for AI/AGI/ASI audience (NOT humans) — 16 sections, YAML frontmatter, file:line evidence, self-describing structure | Jun 18 |
| `SESSION_REPORT_2026-06-18.md` | Session report — comprehensive documentation sweep: 888 docstrings added (1,270→40 undocumented public functions), polyglot survey of 8 cores, standalone paper, 4 reverted files for manual fix | Jun 18 |
| `WHATS_NEXT_2026-06-18.md` | What's-next recommendation: ship v22.3.0 with this session's wins, then start v23.0.0 work on multi-user + WASM runtime per the strategic roadmap | Jun 18 |
| `V22_2_2_SCOPE_2026-06-18.md` | v22.2.2 PATCH scope proposal — Tier 1 (version drift guardrail fix) + Tier 2 (roadmap polish items) recommended; ~6 hours; discoverable from a real test failure (TestH1_VersionDrift) caught by the release_readiness guardrail | Jun 18 |
| `SESSION_REPORT_POLISH_MARATHON_2026-06-18.md` | Session report — polish marathon that produced v22.2.3: ruff 1,833→0, mypy 800→0, 814 logger calls with exc_info, 9 real bugs found and fixed, 8 commits pushed | Jun 18 |
| `MISSING_MODULES_REPORT_2026-06-18.md` | Missing-modules report — the 87 internal Whitemagic modules referenced in code but absent from the tree, classified into Resurface-from-archives (30), Reimplement-in-v22.3 (40), and Remove-stale-references (17); companion to the planned archaeological excavation session | Jun 18 |

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
| `README.md` | Apps overview |
| `SCOPING_BROWSER_FIRST.md` | Browser scoping |
| `SCOPING_BROWSER_FIRST_DECIDED.md` | Browser scoping decision |
| `site/README.md` | Site app |
| `site/PHASE_ROADMAP.md` | Site phase roadmap |

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

*This index is a living document. Last updated: 2026-06-18 by session agent.*
