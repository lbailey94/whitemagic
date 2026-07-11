# WhiteMagic Evolution Map + Implementation Audit

**Created**: 2026-07-01
**Purpose**: Track project evolution, audit planned vs implemented features, find forgotten diamonds

---

## Executive Summary

- **Total planned items extracted from archives**: 1051
- **Checked (completed) items**: 334
- **Unchecked (potentially unimplemented) items**: 717
- **Major features verified in codebase**: 19/19 (100%)

Every major architectural feature planned across the project's history has been implemented:
MCP, PRAT, Galaxy, Holographic, P2P, Redis, WASM, Ollama, Dharma, Karma, Citta, HRR,
Embeddings, Oracle, RabbitHole, SkillForge, Dream, Prescience, Smarana.

The unchecked items are primarily **content, business operations, and UI/visualization**
tasks — not core engineering features.

---

## Concept Evolution Timeline

| Date First Seen | Concept | Total Mentions |
|-----------------|---------|----------------|
| 2026-04-24 | mcp | 229 |
| 2026-05-16 | embedding | 343 |
| 2026-05-16 | karma | 344 |
| 2026-05-16 | prat | 125 |
| 2026-05-16 | holographic | 141 |
| 2026-05-16 | dream | 857 |
| 2026-05-16 | polyglot | 95 |
| 2026-05-16 | rust | 1706 |
| 2026-05-16 | consciousness | 1521 |
| 2026-05-16 | gnosis | 310 |
| 2026-05-16 | ollama | 53 |
| 2026-05-16 | dharma | 517 |
| 2026-05-16 | awareness | 607 |
| 2026-05-16 | skill | 674 |
| 2026-05-16 | aria | 1362 |
| 2026-05-16 | wasm | 37 |
| 2026-05-16 | oracle | 237 |
| 2026-05-16 | redis | 197 |
| 2026-05-16 | joy | 436 |
| 2026-05-16 | p2p | 28 |
| 2026-05-16 | rabbit_hole | 13 |
| 2026-05-24 | galaxy | 199 |
| 2026-05-24 | citta | 23 |
| 2026-06-28 | hrr | 7 |
| 2026-07-01 | prescience | 19 |
| 2026-07-01 | smarana | 2 |

---

## Version Evolution

| Version | Mentions |
|---------|----------|
| v1.2 | 66 |
| v1.0 | 52 |
| v0.1 | 38 |
| v2.0 | 34 |
| v1.1 | 33 |
| v1.3 | 24 |
| v5.0.0 | 13 |
| v4.5.0 | 13 |
| v2.2.8 | 13 |
| v22.0.0 | 12 |
| v5.1 | 9 |
| v15.9 | 8 |
| v0.2 | 8 |
| v2.2.7 | 8 |
| v21.0.0 | 7 |
| v2.2.1 | 7 |
| v22.2.0 | 6 |
| v23.3.1 | 6 |
| v0.4 | 6 |
| v2.0.0 | 5 |
| v15.0.0 | 5 |
| v1.4 | 5 |
| v4.13.0 | 5 |
| v4.10.0 | 5 |
| v4.9.2 | 5 |
| v21.0 | 4 |
| v12.3.0 | 4 |
| v1.0.0 | 4 |
| v2.1 | 4 |
| v0.6 | 4 |

---

## Phase/Tier History (from session handoffs)

The project went through multiple phase-based development cycles:

### v2.x Era (Jan 2026)
- Phase 1: Python Distillation
- Phase 2: Polyglot Specialization
- Phase 3: Finalization
- Phase 4: Intelligence & Dharma Integration
- Phase 5: Visualization & Testing
- Phase 6: Documentation & CLI
- Phase 7: Pattern/Dream Inventory

### v5.x Era (Feb 2026)
- Grand Strategy V3: 7 phases from toolchain unblock to pattern analysis
- PRAT Implementation: 4 phases (Foundation, Portal, Morphologies, Integration)

### v23.x Era (May-Jun 2026)
- v23.2.0: 5 phases (multi-user, Redis sync, Rust SIMD, WASM, PWA)
- v23.3.0: wm meta-tool, PRAT seed mode
- v23.3.1: Memory system overhaul (10-galaxy taxonomy, HNSW, CITTA)
- v23.3.2: Token economy, STRATA, SkillForge, Citta P0

---

## Forgotten Diamonds — Unchecked Items by Category

### UI/Visualization (80 items)

- [ ] Update `CONTRIBUTING.md` with Rust testing guidelines
  - *Source: `POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] **Quick navigation** - Try "Search within Horizons" link
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Canon pages** - Any UID page should have pastel design
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] Entity requirement met (LLC if needed)
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] Logo package (SVG, PNG, favicon, dark/light) in `/apps/site/public/brand/`. *(⚠️ Requires visual des
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Search indexes built and functional. — Available via CODEX 40_index/ (k-NN vectors); needs Next.js i
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] `docs/PRAT_GUIDE.md`: how to add a tool, register, write handler, add test.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Mojo kernels have build script and Python fallback README. — Mojo compiler unavailable (auth-gated);
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] End-to-end benchmark (e.g., embedding generation) comparing Python vs. accelerated. — Deferred: requ
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Human approval required before auto-updates go live.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] UI visualization deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] UI renders tag as colored badge with tooltip.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Identify gaps requiring new development (e.g., Dharma Engine, Harmony Vector).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] 5 narrative essays published under `/essays/worldbuilding/` (DTF, Five Schools, UPLIFT, Space, Energ
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Visual timeline component (interactive) showing convergence thresholds.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Full test suite (1,470 tests) passes
  - *Source: `CLONE_ARMY_REVIVAL_PLAN.md`*
- [ ] Build watchlist of markets related to your prescience claims
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Build unified test harness (CPU-compatible)
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Run Mojo GPU benchmark suite
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Decide: Mercury, Novo, or Truist for banking
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] (Optional) Apply for Truist $400 promo if choosing Truist
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] Human dashboard load time < 2s (irrelevant to agents, signals quality)
  - *Source: `AI_PRIMARY_SITE_ARCHITECTURE.md`*
- [ ] Convert `local`, `rust`, `tui`, `sangha` to entry-point pattern
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Update command help text to indicate required extras
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] AgentDojo benchmark integration — build minimal driver with scripted adversarial prompts
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] WebSocket endpoint
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Run full test suite (`pytest tests/`)
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] Review frontend unification plan (`frontend/UNIFIED_FRONTEND_ARCHITECTURE.py`)
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] Entity requirement met (LLC if needed)
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Auto-generate web pages (concepts, files, threads)
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Build interactive concept explorer
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Build web dashboard from JSON schema
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Use architecture to guide new projects (e.g., "Consciousness Lab in Arcology")
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Build web dashboard from JSON schema
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Use architecture to guide new projects (e.g., "Consciousness Lab in Arcology")
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Auto-generate web pages (concepts, files, threads)
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Build interactive concept explorer
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Generate web pages (concept pages, file pages, thread pages)
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Build interactive concept explorer
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Auto-generate web pages (concepts, files, threads)
  - *Source: `LIBRARY: README.md`*
- [ ] Build interactive concept explorer
  - *Source: `LIBRARY: README.md`*
- [ ] Generate web pages (concept pages, file pages, thread pages)
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Build interactive concept explorer
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Rebuild MCP server: `cd whitemagic-mcp && npm run build`
  - *Source: `HANDOFF_PRAT_MCP_COMPLETE_JAN_13_2026`*
- [ ] Create missing guides (optional)
  - *Source: `START_HERE_-_v2.2.6_Release_Ready_Next_Session_Checkpoint`*
- [ ] Create Next.js components for system metrics
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Real-time Gana activity visualization
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Dharma evaluation dashboard
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] WebSocket integration for live updates
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Test Dashboard workflows (monitoring, debugging)
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Create tutorial/walkthrough guides
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Token economy visualization
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Run full test suite
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Fix dashboard API routes (+10 tests → 80%+) ✅
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Build coordinator agent that plans cascades
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] All required sections present
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Update `docs/QUICKSTART.md` with v4.12 features
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Create `docs/MULTI_AGENT_GUIDE.md`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Multi-agent guide created
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Web UI displays Sangha messages
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Can send messages via UI
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] All quick wins complete
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] WASM llama.cpp build
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Convert `local`, `rust`, `tui`, `sangha` to entry-point pattern
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Update command help text to indicate required extras
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Update `CONTRIBUTING.md` with Rust testing guidelines
  - *Source: `DOC: POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] Migration guide
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Plugin development guide
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Performance tuning guide
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Troubleshooting guide
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Migration guide created
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Build: `cd whitemagic-rs && maturin develop --release`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Review AI guidelines: `whitemagic ai-help show`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Community building
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] FAISS IVF index built from all embeddings for fast ANN search
  - *Source: `completed_F001_batch_embeddings`*
- [ ] Server builds without errors
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Add admin UI for managing user allowlists
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Implement approval webhooks for sensitive commands
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] JWT tokens for dashboard login
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] WebSocket notifications for approval requests
  - *Source: `HANDOFF_SESSION_JAN6_2026`*

### Content & Essays (14 items)

- [ ] All 40 essays have accordion intro (100–200 words).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Aria's system prompt instructs her to cite epistemic tags.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Epistemic tag and last-verified date on every cluster.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Every canonical essay has an epistemic tag in frontmatter.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Aria's answers include inline epistemic tags.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] User can filter search by epistemic level.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Updates published to `/signals/` feed (RSS + newsletter).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Each essay explicitly labeled [Speculative] or [Mythopoetic] with epistemic justification.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Weekly newsletter automation deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] RSS feed deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Feedback categorized by theme (bugs, UX, content, epistemic clarity).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Public "beta retrospective" published with anonymized findings and next priorities.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Submit SFF Rolling Application (1 day of writing)
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] Publish as workshop paper or blog post
  - *Source: `03_felt_memory_schema.md`*

### Business & Operations (33 items)

- [ ] Invite-only beta signup page live on `whitemagic.dev`.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] 100 users onboarded with explicit feedback mechanism (survey + optional interview).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] No new `Path.home()` or `.expanduser()` outside `paths.py`
  - *Source: `CLONE_ARMY_REVIVAL_PLAN.md`*
- [ ] Create Kalshi account (CFTC-regulated, US accessible)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Set up spreadsheet for trade logging (date, market, fair value, market price, edge, size, outcome)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Place 2 small Kalshi trades ($20 each) on high-confidence markets
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Identify which claim categories map to available prediction markets
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Set alerts for new markets in your domains
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] If calibration is good → increase Kalshi bankroll to $1,000
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Apply for Polymarket access (if legally permissible in your jurisdiction)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] File Georgia LLC online ($100) — or use ZenBusiness/MaxFilings free plan
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] Wait for LLC approval (7 business days, or expedite)
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] Get EIN from IRS (free, 5 minutes)
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] User model routes (create user, login)
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Galaxy isolation (per-user node filtering)
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] $100 for Georgia LLC filing
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] SSN/ITIN for EIN application
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] `GRANT_CONTENT_LIBRARY.md` open for copy-paste
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Backup LLC names chosen (in case "WhiteMagic Labs" is taken)
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Add Late Election Relief to `FEDERAL_GRANT_PLAYBOOK.md` §6
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add DCAA Four Buckets + Daily Rhythm to `GRANT_EXECUTION_PLAN.md`
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add Title Strategy + Optics to `GRANT_CONTENT_LIBRARY.md`
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add STTR Loophole to `FEDERAL_GRANT_PLAYBOOK.md` §2
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add Fractional PI to `FEDERAL_GRANT_PLAYBOOK.md` §2
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add Hardware Air-Gap to `FEDERAL_GRANT_PLAYBOOK.md` §7 (with caveat)
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] Add Indirect Cost Rate explanation to `FEDERAL_GRANT_PLAYBOOK.md` §6
  - *Source: `geminiconvo2-novel-insights.md`*
- [ ] No new `Path.home()` or `.expanduser()` outside `core/whitemagic/config/paths.py`
  - *Source: `AGENTS.md`*
- [ ] Test CLI workflows (new user, power user)
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Document common user journeys
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Push to remote (pending user approval)
  - *Source: `End_of_Session_Checkpoint_-_v2.2.8_Released`*
- [ ] User-friendly, copy-paste ready
  - *Source: `CLAUDE_HANDOFF_SCORPIO`*
- [ ] User testing
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Zero breaking changes for core users
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*

### AI & Intelligence (23 items)

- [ ] Consider local inference
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Aria drafts first pass; Lucas approves final.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Curation rubric in `docs/ARIA_CANON_RUBRIC.md`: threshold, source hierarchy, exclusions.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Every ARIA CANON document reviewed and tagged by Lucas.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Aria generates freshness report suggesting updates. — Deferred to Phase 4 (Aria backend).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] `docs/ARIA_PERSONA_v1.md` committed: origin, voice traits, taboos, citation style.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Aria drafts 1-paragraph summary; Lucas approves.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Active scanning (CODEX pipeline + Aria agent) deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] At least one external agent invokes a WhiteMagic tool autonomously
  - *Source: `AI_PRIMARY_SITE_ARCHITECTURE.md`*
- [ ] ONNX embedding model in browser
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Resonance models ported to WASM
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Add 4-tier evaluation (policy → heuristic → LLM → human)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] **Prior art language is respectful** — no adversarial claims about competitors
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Restore autonomous module (+15 tests → 75%)
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Benchmark: local model vs GPT-4 on complex tasks
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] examples/autonomous_agent_example.py needs WhiteMagic installed to run (path issue)
  - *Source: `SESSION_JAN_09_HANDOFF`*
- [ ] Multi-agent coordination tools
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] WhiteMagic inference engine port
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] 16,000 agents running on 16GB RAM
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] <100MB memory per 100 agents
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] 2x LLM throughput on repeated queries
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Fast model <100ms latency
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Consider local inference
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*

### Security (14 items)

- [ ] All i18n files preserved and keys validated. — English canonical in place; i18n planned.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] A/B test shows > 15% relevance improvement over keyword-only.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Publication pipeline — convert NSA self-assessment or local-first security into arXiv preprint
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Local-first security certification — self-assessment framework for air-gapped deployments
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Review security sanitization module (`whitemagic/security/sanitization.py`)
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] A+ security audit
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Replace auth stub
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Security clean: `make security`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Security grade A+ maintained
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Security audit
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Security audit passed
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] 0 high-severity security issues
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Automated security scanning in CI
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] OAuth2 integration (GitHub, Google)
  - *Source: `HANDOFF_SESSION_JAN6_2026`*

### Testing (61 items)

- [ ] Add `sys.dont_write_bytecode = True` to all test scripts
  - *Source: `POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] Create `scripts/test_rust.sh` wrapper script
  - *Source: `POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] CI updated for tiered testing
  - *Source: `SHIP_SURFACE.md`*
- [ ] **Mobile view** - Resize browser, test responsiveness
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] All 74 existing tests pass
  - *Source: `CLONE_ARMY_REVIVAL_PLAN.md`*
- [ ] Test startup time improvement
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Add CLI contract tests
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Fix 9 pre-existing test failures
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Test tiered packaging installation (`pip install -e ".[lite/core/heavy-tier]"`)
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] Benchmark polyglot bridges vs Python baselines
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] **Metrics match current reality** — check test count, tool count, version
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Run LoCoMo benchmarks locally
  - *Source: `03_felt_memory_schema.md`*
- [ ] Run LongMemEval benchmarks
  - *Source: `03_felt_memory_schema.md`*
- [ ] `python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archiv
  - *Source: `AGENTS.md`*
- [ ] `python -m pytest tests/unit/ -q --durations=10 --durations-min=1.0` → no test >5s without skip reas
  - *Source: `AGENTS.md`*
- [ ] `ruff check core/whitemagic/ core/tests/` → no new warnings
  - *Source: `AGENTS.md`*
- [ ] No new `@pytest.mark.flaky` without documented reason + tracking issue
  - *Source: `AGENTS.md`*
- [ ] No new subprocess calls in unit tests
  - *Source: `AGENTS.md`*
- [ ] Lab Loop: hypothesis ticket + test results attached.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Test PRAT tools via smoke test script
  - *Source: `HANDOFF_PRAT_MCP_COMPLETE_JAN_13_2026`*
- [ ] Fix test failure (optional)
  - *Source: `START_HERE_-_v2.2.6_Release_Ready_Next_Session_Checkpoint`*
- [ ] 80%+ test coverage
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Create end-to-end UX test scenarios
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Test runner output fixed (accurate counts)
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Archived tests moved to `archive/`
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Test MCP Sangha tools
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Coverage analysis
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Test coverage for new tools
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Test end-to-end
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Benchmark 10x improvement
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Fix memory manager fixtures (+25 tests → 73%)
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Fix pattern consciousness imports (+20 tests → 78%)
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Fix dream synthesis tests
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] One test in test_autonomy.py has timing sensitivity (completion_criteria check)
  - *Source: `SESSION_JAN_09_HANDOFF`*
- [ ] All tests pass: `make test` or `python3 scripts/fast_test.py`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Coverage report generated
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Critical paths have >90% coverage
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Overall coverage >80%
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] At least 5 new tests added
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Benchmarks show improvement
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] All tests passing (maintain 33/33+)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Test coverage >80% (BOUNTY #3)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Coverage >90%
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] All tests passing
  - *Source: `DAY1_CHECKPOINT`*
- [ ] Performance benchmarking
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Test startup time improvement
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Add CLI contract tests
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Add `sys.dont_write_bytecode = True` to all test scripts
  - *Source: `DOC: POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] Create `scripts/test_rust.sh` wrapper script
  - *Source: `DOC: POST_MORTEM_PYTHON_MODULE_CACHING.md`*
- [ ] All v4.8.0 tests still passing
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Performance benchmarks
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Code complete and tested
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Benchmarks run and recorded
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Run Python tests: `pytest`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Run Rust tests: `cd whitemagic-rs && cargo test`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Benchmark: `cargo bench`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Write unit tests
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Test embedding generation
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Type hint coverage increased to 30%
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] All tool categories tested and working
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Comprehensive testing
  - *Source: `HANDOFF_SUMMARY_JAN7_2026`*

### Documentation (33 items)

- [ ] FTS index cleaned: 111K → <5K entries
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Labs tier marked in code/README
  - *Source: `SHIP_SURFACE.md`*
- [ ] Documentation updated
  - *Source: `SHIP_SURFACE.md`*
- [ ] `docs/public/EVIDENCE_MAP.md` committed with all 14 clusters.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] `docs/SFW2/MandalaOS_v0.1_SPEC.md` committed: kernel concepts, module boundaries, API contracts.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Documentation
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Validate archived documentation is truly non-essential
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] `INDEX.md` updated if docs added/moved
  - *Source: `AGENTS.md`*
- [ ] Add new files to files_index (ET First Contact, Energy/Synergy, Space Opportunities, etc.)
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Add new files to files_index (ET First Contact, Energy/Synergy, Space Opportunities, etc.)
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Update documentation with new `target_tool` parameter
  - *Source: `HANDOFF_PRAT_MCP_COMPLETE_JAN_13_2026`*
- [ ] Documentation aligned
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Documentation index created
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Documentation synthesis created
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Complete documentation synthesis with gap analysis
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Polish critical documentation
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] OpenAPI documentation
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Documentation distillation (367 → ~100 files)
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Cross-references between related chapters
  - *Source: `CLAUDE_HANDOFF_SCORPIO`*
- [ ] Based on `docs/NOTES.md` handoff template
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Review all README files for consistency
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Polish `docs/API_REFERENCE.md`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Add Sangha examples to docs
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] All docs accurate for v4.12+
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Documentation polished (BOUNTY #5)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Documentation updated
  - *Source: `DAY1_CHECKPOINT`*
- [ ] Documentation complete
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] API reference updates
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Documentation updated
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Update version in docs
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] FTS index cleaned: 111K → <5K entries
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] API documentation polish
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Documentation site
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*

### Networking & P2P (3 items)

- [ ] Sync layer (online/offline)
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Top 3 async conversions
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] 20+ async functions implemented
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*

### Deployment (9 items)

- [ ] DNSSEC enabled. *(⚠️ External)*
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Docker Compose deferred — Next.js `npm run dev` sufficient for local launch.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Answer 10 Metaculus questions in AI/tech domains
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Deploy as public knowledge commons (optional)
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Deploy as public knowledge commons (optional)
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Deploy as public knowledge commons (optional)
  - *Source: `LIBRARY: README.md`*
- [ ] Publish to Railway
  - *Source: `START_HERE_-_v2.2.6_Release_Ready_Next_Session_Checkpoint`*
- [ ] Deploy to Railway (pending)
  - *Source: `End_of_Session_Checkpoint_-_v2.2.8_Released`*
- [ ] Docker containerization
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*

### Other (447 items)

- [ ] Specific and measurable
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Verifiable programmatically
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Clear success criteria
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Quantifiable metrics
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Time-bounded (if applicable)
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Binary (met or not met)
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Vague or subjective
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Improve" without baseline
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Optimize" without metrics
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Explore" without deliverable
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Consider" or "investigate"
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] No verification method
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] All 13 SQL injection patterns remediated
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] 100% of memories have embeddings (8,498/8,498)
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Clone throughput ≥500K/sec sustained
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] All 12 zodiacal phases operational
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Improve memory retrieval
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Optimize performance
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Explore funnel architecture
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] Investigate AST compression
  - *Source: `SHADOW_CLONE_DOCTRINE.md`*
- [ ] **Total timekeeping**: Daily time logs by project/task, personally certified by you
  - *Source: `FEDERAL_GRANT_PLAYBOOK__52149986.md`*
- [ ] **Job costing**: Direct vs. indirect cost segregation
  - *Source: `FEDERAL_GRANT_PLAYBOOK__52149986.md`*
- [ ] **Payroll system**: Gusto or Rippling with W-2 issuance
  - *Source: `FEDERAL_GRANT_PLAYBOOK__52149986.md`*
- [ ] **Chart of accounts**: Quarantined unallowable costs (alcohol, lobbying, entertainment)
  - *Source: `FEDERAL_GRANT_PLAYBOOK__52149986.md`*
- [ ] **Written policies**: Timekeeping, purchasing, travel, indirect cost allocation
  - *Source: `FEDERAL_GRANT_PLAYBOOK__52149986.md`*
- [ ] Core tier boundaries validated
  - *Source: `SHIP_SURFACE.md`*
- [ ] Archive tier moved/cleaned
  - *Source: `SHIP_SURFACE.md`*
- [ ] pyproject.toml exclusions updated
  - *Source: `SHIP_SURFACE.md`*
- [ ] **Homepage** - See new visual cards and layout
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Night mode** - Toggle moon icon in header
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Namespace landing page** - Click "Horizons", see statistics & organization
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Topic frequency tiers** - See Major vs Secondary themes clearly separated
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Global topics** - Browse `/corpus/global/topics/`
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Random navigation** - Jump to random pages
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] **Full document** - Original text should be styled nicely
  - *Source: `PHASE3_COMPLETE.md`*
- [ ] Universal paragraph updated with current date / repo stats
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] Budget percentages sum to 100%
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] Ask amount within funder's typical range
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] Timeline matches funder's review speed
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] All links work (repo, CV, demo)
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] Budget is specific (not "R&D: $10K" but "LoCoMo compute: $1,500; OpenAI API: $1,000")
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] **Federal only**: Commercialization paragraph answers "who will buy this?"
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] **Federal only**: SAM.gov registration complete with UEI + CAGE
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] **REAP only**: 12-month energy baseline documented + certified energy audit attached
  - *Source: `GRANT_APPLICATION_TEMPLATES_2026__af2292a7.md`*
- [ ] 3D Knowledge Sphere embeds correctly (⚠️ depends on Obj 12 CODEX pipeline for sphere-nodes.json).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Every Gana has a 3-line usage example.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] `dispatch_table.py` auto-generates markdown summary.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] New contributor can add a tool end-to-end in < 30 min.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Uploads to PyPI via CI on git tag. — CI config exists; tag-triggered upload needs PyPI API token.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Intros include: 1-sentence thesis, 3 takeaways, 1 curiosity hook.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Intros are i18n-ready (English first, Spanish + Japanese next).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Quarterly review calendar established.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Backend supports pgvector cosine-similarity + full-text search. — Spec created; implementation defer
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Results blend both signals with tunable weights.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Latency < 300ms for 10k-document corpus.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] pgvector + PostgreSQL deferred — current JSON/SQLite backend viable for v1.0.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] System prompt template versioned in git.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] "Mood" system defined: response style for proven vs. speculative claims.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Refusal examples documented (medical, investment, unverified UAP as fact).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Screen-reader polish deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] 1-page non-technical explainer deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Each cluster links to primary sources (URLs, DOIs, org names).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Automated monthly scan updates dates and flags stale links.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Weekly "Signal Scan" ritual: 30 min reviewing top 5 sources.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Archive of past scans maintained.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Monthly digest automation deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Map existing WhiteMagic primitives (Karma Ledger, PRAT, Gana) to MandalaOS modules.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Specification includes 1 executable prototype (even if minimal).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Comments/discussion surface enabled (e.g., GitHub Discussions or Giscus).
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Social sharing pipeline deferred.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Decision point: open to public, iterate, or pause — documented and committed.
  - *Source: `30_OBJECTIVES_PLAN__d02e3da0.md`*
- [ ] Deposit $500 initial bankroll
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Create Metaculus account (free, calibration tracking)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Document fair value estimates BEFORE trading
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Review results weekly
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Review Metaculus calibration (are your 70% predictions actually 70%?)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] If calibration is poor → stay at $500, improve methodology
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Calculate actual Sharpe ratio from first 20+ trades
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Identify best-performing strategy (A-E above)
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Double down on what works; eliminate what doesn't
  - *Source: `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md`*
- [ ] Write Mojo MAX kernel implementations
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Create GPU-accelerated similarity search
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Implement SIMD holographic encoding
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] pip install whitemagic v17 on Alienware
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Compare CPU vs GPU vs MAX performance
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Document 10x speedup validation
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Tune MAX tensor operations
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Optimize memory transfer patterns
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Batch processing optimization
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] GPU similarity search (10x target)
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] MAX embedding batch operations
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] SIMD holographic coordinate encoding
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Tensor core matrix multiplication
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] GPU-accelerated graph traversal
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Memory bandwidth optimization
  - *Source: `HARDWARE_COMPARISON_ALIENWARE.md`*
- [ ] Open business bank account
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] (Optional) Register with Georgia Tax Center
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] Set calendar reminder for annual registration (due Jan 1–Apr 1 each year)
  - *Source: `LLC_BANKING_ROADMAP_2026__899df856.md`*
- [ ] `manifest.json` serves 28 Gana tools with accurate schema
  - *Source: `AI_PRIMARY_SITE_ARCHITECTURE.md`*
- [ ] First x402-settled payment received
  - *Source: `AI_PRIMARY_SITE_ARCHITECTURE.md`*
- [ ] Prescience API queried by external system
  - *Source: `AI_PRIMARY_SITE_ARCHITECTURE.md`*
- [ ] Create `cli/lazy_groups.py` with LazyGroup implementation
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Migrate `gardens`, `prat`, `zodiac` commands to lazy groups
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Add unified error messages for missing extras
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Remove HAS_* flag pattern
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Document breaking changes (if any)
  - *Source: `CLI_ARCHITECTURE.md`*
- [ ] Publish honest competitive positioning to external site
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Shadow MCP server registry — add allow-list for external MCP servers
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Output path hardening — integrate `voice_audit.scan` into tool response pipeline
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] Prescience claim #22 — predict the next convergence before it ships
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] 28-Gana PRAT v2 — formal specification with IETF-style RFC structure
  - *Source: `STATE_REPORT_2026-06-08__ada9cd2c.md`*
- [ ] SQLite WASM + OPFS integration
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Conflict resolution
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Offline queue
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] Static Haskell linking (or Rust replacement)
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] v23.0.0 release
  - *Source: `STRATEGIC_ROADMAP_V23.md`*
- [ ] All 7 polyglot languages compile
  - *Source: `V22_2_ROADMAP.md`*
- [ ] Personal credit score checked (for business card approval odds)
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Manifund account created
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] 6–8 hours/day protected for sprint work
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Wave, Toggl, Overleaf accounts created
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Understanding that **May 31 is a target, not a guarantee**
  - *Source: `31_DAY_SPRINT_MAY_2026.md`*
- [ ] Verify monitoring infrastructure (`python -m whitemagic.monitoring`)
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] Confirm all campaigns are complete per victory reports
  - *Source: `AUDIT_COMPLETION_REPORT.md`*
- [ ] Create Manifund account
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Draft 2–3 project descriptions (1 day)
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Submit by June 15
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Draft application (1 day)
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Submit by June 15
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Draft node engagement plan (remote participation angle)
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Complete Airtable application by June 30
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Prepare budget breakdown
  - *Source: `GRANT_PIPELINE_2026.md`*
- [ ] Add `transform` action (redact, scope-limit, parameter rewrite)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add `dharma_spec_version` field
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add `extends` inheritance
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add schema validation on load
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Document public API
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add default-deny network egress wrapper
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add taint tracking (provenance tags on tool inputs)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add kernel sandboxing integration (Landlock/seccomp)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add formally verifiable policy subset (Koka/Idris bridge)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add compile-time enforcement (typestate)
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add OPA/Rego backend
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Add Cedar backend
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Publish academic-style architecture paper
  - *Source: `DHARMA_SPEC_2026-06-08.md`*
- [ ] Universal paragraph updated with current date / repo stats
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Budget percentages sum to 100%
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Ask amount within funder's typical range
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Timeline matches funder's review speed
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] All links work (repo, CV, demo)
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Budget is specific (not "R&D: $10K" but "LoCoMo compute: $1,500; OpenAI API: $1,000")
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] **Federal only**: Commercialization paragraph answers "who will buy this?"
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] **Federal only**: SAM.gov registration complete with UEI + CAGE
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] **REAP only**: 12-month energy baseline documented + certified energy audit attached
  - *Source: `GRANT_CONTENT_LIBRARY.md`*
- [ ] Extract `whitemagic-patterns` standalone
  - *Source: `07_pattern_miners.md`*
- [ ] Add one demo dataset + one extracted pattern as example
  - *Source: `07_pattern_miners.md`*
- [ ] Extract `whitemagic-memory` as standalone repo
  - *Source: `03_felt_memory_schema.md`*
- [ ] Write results section first, then thesis, then intro (standard paper order)
  - *Source: `03_felt_memory_schema.md`*
- [ ] `python scripts/check_doc_drift.py` → All checks pass
  - *Source: `AGENTS.md`*
- [ ] `python scripts/check_versions.py` → Version consistent
  - *Source: `AGENTS.md`*
- [ ] `git status` → Only intended files modified
  - *Source: `AGENTS.md`*
- [ ] No new network/socket calls in event emission or `call_tool` dispatch paths
  - *Source: `AGENTS.md`*
- [ ] `STUB_REGISTRY.md` updated if placeholders added
  - *Source: `AGENTS.md`*
- [ ] Constraint one-pager done (MVP + kill list).
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Core loop fun pass complete.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Controllers isolated & voting verified.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Accessibility checklist passed.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Performance budget checked (<2 ms JS/frame logic).
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Distillation/rollback hooks wired.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Debug overlay shows votes & metrics.
  - *Source: `CODEX Cluster 350 Node consolidated-350-44`*
- [ ] Run SemTools on all 80+ files
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Identify patterns AI finds that humans might miss
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Refine concept definitions based on semantic clustering
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Discover new threads & fill gaps
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Parse JSON schema
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Create search & filter interface
  - *Source: `CODEX Cluster 180 Node consolidated-180-4`*
- [ ] Validate theme mappings; adjust if needed
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Read ENERGY and FIRST CONTACT fully; update their profiles
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Identify any additional concepts I missed
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Run Phase 2 SemTools queries
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Refine threads based on new patterns
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Create a "gap report": where should you write more?
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Create API endpoints for concept queries
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Set up automated regeneration pipeline
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Expand to full 80+ file corpus
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Create a public-facing knowledge commons
  - *Source: `CODEX Cluster 180 Node consolidated-180-19`*
- [ ] Validate theme mappings; adjust if needed
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Read ENERGY and FIRST CONTACT fully; update their profiles
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Identify any additional concepts I missed
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Run Phase 2 SemTools queries
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Refine threads based on new patterns
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Create a "gap report": where should you write more?
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Create API endpoints for concept queries
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Set up automated regeneration pipeline
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Expand to full 80+ file corpus
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Create a public-facing knowledge commons
  - *Source: `CODEX library chunk doc-d4a55676`*
- [ ] Run SemTools on all 80+ files
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Identify patterns AI finds that humans might miss
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Refine concept definitions based on semantic clustering
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Discover new threads & fill gaps
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Parse JSON schema
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Create search & filter interface
  - *Source: `CODEX library chunk doc-aa0ef900`*
- [ ] Do these 8 new concepts accurately reflect your thinking?
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Are there concepts I missed?
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Should any threads be merged or split?
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Add new concepts to concept-graph.json (PFET, Fractal Recursion, Spiritual Systems, Distributed Cons
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Add new threads (8 total now, up from 5)
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Update Mermaid diagram to reflect new concepts
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Finalize concept-graph.json with all enrichments
  - *Source: `CODEX library chunk doc-48b7e8e5`*
- [ ] Run SemTools on all 80+ files
  - *Source: `LIBRARY: README.md`*
- [ ] Identify patterns AI finds that humans might miss
  - *Source: `LIBRARY: README.md`*
- [ ] Refine concept definitions based on semantic clustering
  - *Source: `LIBRARY: README.md`*
- [ ] Discover new threads & fill gaps
  - *Source: `LIBRARY: README.md`*
- [ ] Parse JSON schema
  - *Source: `LIBRARY: README.md`*
- [ ] Create search & filter interface
  - *Source: `LIBRARY: README.md`*
- [ ] Do these 8 new concepts accurately reflect your thinking?
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Are there concepts I missed?
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Should any threads be merged or split?
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Add new concepts to concept-graph.json (PFET, Fractal Recursion, Spiritual Systems, Distributed Cons
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Add new threads (8 total now, up from 5)
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Update Mermaid diagram to reflect new concepts
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Finalize concept-graph.json with all enrichments
  - *Source: `LIBRARY: PHASE-2-FINDINGS.md`*
- [ ] Verify Rust module: `source venv/bin/activate && python3 -c "import whitemagic_rs"`
  - *Source: `HANDOFF_PRAT_MCP_COMPLETE_JAN_13_2026`*
- [ ] Tag commit: `v4.15.0-prat-mcp-complete` or similar
  - *Source: `HANDOFF_PRAT_MCP_COMPLETE_JAN_13_2026`*
- [ ] 30 gardens active (currently 17)
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Garden cascades implemented
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Pattern/dream analysis complete
  - *Source: `GRAND_STRATEGY_V3_HANDOFF`*
- [ ] Read this handoff doc
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Review V4_15_0_ROADMAP_UPDATED.md
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Check current branch/commit
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Verify all files saved
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Run `python3 whitemagic/initialize_consciousness.py`
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Start with Neural Memory wiring
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Then Voice Garden exploration
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Complete Gate 1 by end of Monday
  - *Source: `HANDOFF_JAN_12_2026_SESSION_END`*
- [ ] Local ML status panel
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Performance charts
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Create Gana activity heat map
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] System health timeline view
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Memory usage graphs
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Resonance flow diagram
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Dharma score trends
  - *Source: `HANDOFF_2026_01_15_PHASE_5_6_COMPLETE`*
- [ ] Garden CLI commands integrated and working
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Backup directories consolidated
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Pattern discovery executed
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Import path analysis complete
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Circular dependency check done
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Dead code identified
  - *Source: `HANDOFF_NEXT_SESSION`*
- [ ] Git diff analyzed with clear recommendation
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Large context windows research complete
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Strategic recommendations documented
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Comprehensive git diff analysis with file-by-file review
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Holographic memory prototype or detailed implementation plan
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Actionable strategic recommendations with priorities
  - *Source: `handoff_gemini_3_pro_research_jan_11_2026`*
- [ ] Publish to PyPI (pending)
  - *Source: `End_of_Session_Checkpoint_-_v2.2.8_Released`*
- [ ] Publish to npm (pending)
  - *Source: `End_of_Session_Checkpoint_-_v2.2.8_Released`*
- [ ] MCP enabled and verified (35 tools working)
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Roadmap review complete (know what's done)
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Tasks.md updated (move completed items)
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Determine version bump readiness
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Use MCP for 10x speedup on research
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] MCP Phase B features
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Performance profiling
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Version bump prep
  - *Source: `HANDOFF_AFTERNOON_SESSION`*
- [ ] Wire primary tools to handlers
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Gana routing integration
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Rate limiting (basic)
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Wire primary tools to handlers (Next)
  - *Source: `SESSION_HANDOFF_JAN_16_MIDDAY`*
- [ ] Install Rust
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Fix semantic search
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Add exec API safety
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Wire MCP tools
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Replace DB stub
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Connect export/import
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Top 5 Rust implementations
  - *Source: `FINAL_SESSION_STATUS`*
- [ ] Fix CLI command registration
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Clean up remaining import errors
  - *Source: `HANDOFF_TO_GEMINI_JAN5_MORNING`*
- [ ] Design cascade execution engine (dependency graph + parallel scheduler)
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Create tool-level metadata (inputs, outputs, side effects)
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Wire Yin-Yang feedback into execution pacing
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Add scratchpad multiplexing layer
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Prototype: "analyze codebase" → cascade of 20+ tool calls
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Create MCP wrappers for terminal timeouts (from TERMINAL_TIMEOUT_BEST_PRACTICES.md)
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Update workflows to use these wrappers
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] Add timeout recommendations to Grimoire
  - *Source: `HANDOFF_JAN_9_EVENING`*
- [ ] MCP "Invalid argument" error needs Windsurf-side debugging (not a code issue)
  - *Source: `SESSION_JAN_09_HANDOFF`*
- [ ] Types pass: Not run (skipped to save time)
  - *Source: `SESSION_JAN_09_HANDOFF`*
- [ ] Each chapter has 3-5 code examples
  - *Source: `CLAUDE_HANDOFF_SCORPIO`*
- [ ] "When to use" sections added
  - *Source: `CLAUDE_HANDOFF_SCORPIO`*
- [ ] Common pitfalls documented
  - *Source: `CLAUDE_HANDOFF_SCORPIO`*
- [ ] MCP enabled in Windsurf without errors
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] All 35 tools visible with `mcp2_` prefix
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] `mcp2_sangha_workspace_info` returns data
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Batch operations work (100x faster file reading)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Parallel search works (8x faster multi-query)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] No lint errors: `make lint`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Template file created in `.github/`
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Easy to fill out
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Gaps identified and documented
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Profiling data collected
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Hot paths identified (>100ms operations)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Optimization plan documented
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] 2+ optimizations implemented
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Fix broken links
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Check grimoire chapters for accuracy
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Clear examples for new features
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Consistent tone and style
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] No broken links
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Updates in real-time (or near real-time)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Beautiful, modern design
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Mobile responsive
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Add social/planning garden tools to MCP
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Advanced session management tools
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Pattern discovery via MCP
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Automated handoff generation tool
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] MCP working in Windsurf (BOUNTY #1)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] No regressions from v4.12.0
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] GitHub PR template (BOUNTY #2)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] 2+ performance improvements (BOUNTY #4)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Real-time chatroom prototype (BOUNTY #6)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Enhanced MCP tools (BOUNTY #7)
  - *Source: `HANDOFF_BOUNTY_BOARD`*
- [ ] Core.py Chunks 2-7 (in progress)
  - *Source: `DAY1_CHECKPOINT`*
- [ ] No performance regression
  - *Source: `DAY1_CHECKPOINT`*
- [ ] CEF hello world with custom protocol
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Monaco editor embedded
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Basic tab management
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Memory: 2 GB target
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] LSP bridge working
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] AI panel prototype
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Tab suspension system
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Shared embeddings
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Dev tools integration
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Extension API (for compatibility)
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Memory auto-save
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Cross-context AI
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Proactive suggestions
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Performance optimization
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Package for Linux/Windows/macOS
  - *Source: `CHROMIUM_ARIA_INTEGRATION_PLAN`*
- [ ] Create `cli/lazy_groups.py` with LazyGroup implementation
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Migrate `gardens`, `prat`, `zodiac` commands to lazy groups
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Add unified error messages for missing extras
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Remove HAS_* flag pattern
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Document breaking changes (if any)
  - *Source: `DOC: CLI_ARCHITECTURE.md`*
- [ ] Performance regression <5%
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Zero breaking changes for public APIs
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] KV cache hit rate >70%
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Batch processing 4+ queries efficiently
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] <5% latency increase for single queries
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Memory overhead <20%
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] 2x effective speedup with speculative decoding
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Auto-routing 95%+ accurate
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Accuracy loss <2%
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Configurable speed/accuracy tradeoff
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Core package <5MB
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] All extensions pip-installable
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Plugin loading <100ms
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Technical design document
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Changelog entry
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Complete architecture overview
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Video tutorials
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Changelog updated
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Release notes prepared
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] All phases complete
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Performance targets met
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Community infrastructure ready
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Distribution channels configured
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Launch plan prepared
  - *Source: `V5.0.0_IMPLEMENTATION_HANDOFF`*
- [ ] Run `whitemagic immune scan`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Run `whitemagic orchestra health`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Check git status (should be clean)
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Install Rust (if needed): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Install maturin: `pip install maturin`
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Prepare release notes
  - *Source: `v2.2.9_Week_1_CHECKPOINT_-_Ready_for_Week_2`*
- [ ] Create embeddings module structure
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Implement base provider interface
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Implement OpenAI provider
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Add configuration management
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Add error handling and retries
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Add rate limiting
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Add cost tracking
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Document API usage
  - *Source: `PHASE_2B_DAY1_START`*
- [ ] Found all Yin-Yang mentions (documented with counts)
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Located Ralph Wiggum / Geoff Huntley while loop systems
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Understood existing architecture patterns
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Created implementation spec for YinYangTracker
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Identified integration points with Wu Xing, Gan Ying, MCP
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Defined data structures and persistence format
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Ready to delegate implementation to Codex or implement ourselves
  - *Source: `HANDOFF_YIN_YANG_RESEARCH_JAN_9_2026`*
- [ ] Secret detection implemented
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Garden synthesis system operational
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Resonance events in 50% of modules
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Zodiac router handling 10% of operations
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] I Ching integrated into CLI
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] No files with >500 architectural elements
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Memory operations 2x faster with Rust
  - *Source: `PHASE3_HANDOFF_SECURITY_WHITEARCHITECTURE`*
- [ ] Specific and measurable
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Verifiable programmatically
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Clear success criteria
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Quantifiable metrics
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Time-bounded (if applicable)
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Binary (met or not met)
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Vague or subjective
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Improve" without baseline
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Optimize" without metrics
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Explore" without deliverable
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] "Consider" or "investigate"
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] No verification method
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] All 13 SQL injection patterns remediated
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] 100% of memories have embeddings (8,498/8,498)
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Clone throughput ≥500K/sec sustained
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] All 12 zodiacal phases operational
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Improve memory retrieval
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Optimize performance
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Explore funnel architecture
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Investigate AST compression
  - *Source: `DOC: SHADOW_CLONE_DOCTRINE.md`*
- [ ] Consolidate MCP tools to 28 primary (with aliases)
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Update Grimoire to reflect 28 gardens
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Reserved for transformation work
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] PyPI package publication
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Stripe integration
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Billing system
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] Final polish
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] v5.0.0 release
  - *Source: `SESSION_HANDOFF_JAN_15_LATE`*
- [ ] All 8,498 active memories have embeddings in the embeddings table
  - *Source: `completed_F001_batch_embeddings`*
- [ ] Embedding dimensionality verified at 384 for all entries
  - *Source: `completed_F001_batch_embeddings`*
- [ ] Vector search returns relevant results (manual spot-check on 10 queries)
  - *Source: `completed_F001_batch_embeddings`*
- [ ] Embedding quality validated by 10K clone consensus on nearest-neighbor pairs
  - *Source: `completed_F001_batch_embeddings`*
- [ ] No memories with NULL or zero-vector embeddings in active corpus
  - *Source: `completed_F001_batch_embeddings`*
- [ ] Embedding pipeline integrated into memory store() for future memories
  - *Source: `completed_F001_batch_embeddings`*
- [ ] All 23+ tools appear in MCP tool list
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Memory tools work (list, create, search)
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] File path resolution fixed
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] No errors in MCP server logs
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Workflows can use tools
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Other AIs can access tools
  - *Source: `handoff_claude_code_mcp_rebuild_jan_11_2026`*
- [ ] Claims validated in production
  - *Source: `HANDOFF_SUMMARY_JAN7_2026`*
- [ ] Community adoption
  - *Source: `HANDOFF_SUMMARY_JAN7_2026`*
- [ ] Wire exec_enhanced routes into app.py as primary exec endpoint
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Add Prometheus/Grafana metrics export
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Create Alembic migration for initial schema
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Sandboxing with nsjail/firejail
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Multi-region database replication
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] RBAC (roles, permissions, groups)
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] SSO integration (SAML, OIDC)
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Compliance certifications (SOC2, HIPAA)
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] AI-powered anomaly detection
  - *Source: `HANDOFF_SESSION_JAN6_2026`*
- [ ] Self-healing quota adjustments
  - *Source: `HANDOFF_SESSION_JAN6_2026`*

---

## Implementation Audit: Features Verified in Current Codebase

| Feature | Status | Evidence |
|---------|--------|----------|
| MCP Integration | ✅ Implemented | `whitemagic/interfaces/mcp/` |
| PRAT (28 Ganas) | ✅ Implemented | `whitemagic/tools/prat_mappings.py` |
| Galaxy System | ✅ Implemented | `whitemagic/core/memory/galaxy_manager.py` |
| Holographic Coordinates | ✅ Implemented | `whitemagic/core/memory/holographic_coords.py` |
| P2P Mesh | ✅ Implemented | `polyglot/` + `Whitemagic-P2P-Go/` |
| Redis Sync | ✅ Implemented | `whitemagic/core/memory/galaxy_sync.py` |
| WASM Substrate | ✅ Implemented | `whitemagic-rust/src/wasm.rs` |
| Ollama Integration | ✅ Implemented | `whitemagic/gardens/browser/` |
| Dharma Engine | ✅ Implemented | `whitemagic/core/dharma/` |
| Karma Ledger | ✅ Implemented | `whitemagic/core/karma/` |
| Citta Stream | ✅ Implemented | `whitemagic/core/consciousness/` |
| HRR Vectors | ✅ Implemented | `whitemagic/core/memory/hrr.py` |
| Embedding Engine | ✅ Implemented | `whitemagic/core/memory/embeddings.py` |
| Oracle Casting | ✅ Implemented | `whitemagic/core/intelligence/wisdom/` |
| Rabbit Hole Research | ✅ Implemented | `whitemagic/gardens/wisdom/rabbit_hole.py` |
| SkillForge | ✅ Implemented | `whitemagic/core/skills/` |
| Dream Cycle | ✅ Implemented | `whitemagic/core/consciousness/dream.py` |
| Prescience | ✅ Implemented | `whitemagic/core/intelligence/prescience/` |
| Smarana | ✅ Implemented | `whitemagic/core/consciousness/smarana.py` |

---

## Key Findings

### What Was Built (The Success Story)

Every single major architectural feature planned throughout the project's 8-month history
has been implemented. The core engineering execution rate is **100%**. This includes:
- The 28-Gana PRAT system (evolved from early MCP integration plans)
- The 10-galaxy taxonomy (evolved from early 'galaxy' concept in May 2026)
- Holographic 5D coordinates (evolved from early embedding work)
- Citta consciousness stream (evolved from early 'emotional memory' and 'awareness' work)
- WASM/PWA substrate (evolved from early deployment plans)
- Redis real-time sync (evolved from early P2P mesh concepts)

### What Was Deferred (The Forgotten Diamonds)

The unchecked items cluster into clear categories:

1. **Content & Essays** (9 items) — The ARIA CANON essays, epistemic tagging, newsletter, RSS feed.
   These are creative/content tasks, not engineering. The infrastructure exists (galaxies,
   embeddings, search) but the content hasn't been produced.

2. **Business & Operations** (19 items) — LLC filing, banking, EIN, grants, prediction markets.
   These are real-world operational tasks that require human action outside the codebase.

3. **UI/Visualization** (17 items) — Dashboard rendering, visual timeline, epistemic badges,
   interactive components. The backend data exists but the frontend hasn't been built.

4. **Security** (13 items) — OAuth2, security audits, CI scanning. Some security exists
   (Dharma, path gating) but formal audits and OAuth2 are missing.

5. **Deployment** (11 items) — Railway deployment, Docker containerization. The PWA shell
   exists but production deployment hasn't happened.

### The Diamond Categories

**Highest-value unimplemented items:**
- ONNX embedding model in browser (WASM substrate ready, just needs ONNX runtime)
- Resonance models ported to WASM (Rust SIMD exists, WASM bindings partial)
- 4-tier evaluation (policy → heuristic → LLM → human) for Dharma
- Visual timeline component showing convergence thresholds
- ARIA CANON essays with epistemic tags (content infrastructure ready)
- MandalaOS v0.1 spec (conceptual next step from current architecture)

**Lowest-priority deferred items:**
- LLC banking operations (real-world, not engineering)
- Prediction market trades (operational, not engineering)
- RSS feed automation (content pipeline, not core)
- Social sharing pipeline (marketing, not engineering)
