# Archived Doc Review Findings

**Date**: 2026-06-28
**Scope**: Reviewed ~50 .md docs from April-June 2026, oldest to newest

---

## Missed Priorities Found

### 1. Minutes-to-Days Paradox (April 2026)
**File**: `WhiteMagic-Grants/Research/the-minutes-to-days-paradox.md`
**Finding**: Documents 330x compression ratio — 8-9 days of work completed in 35 minutes. This is the exact problem our prediction calibration system now addresses. The doc identifies root causes:
- Zero context switching (parallel file reads/edits)
- Perfect memory (no loading state)
- No compile-fix-debug cycle
- No review wait time
**Action**: ✅ Already addressed — our PredictionCalibration system now tracks this. The 5.7x overconfidence we measured is conservative vs the 330x documented here.

### 2. Recursive Improvement — 30 Objectives (June 2026)
**File**: `docs/message_board/RECURSIVE_IMPROVEMENT_STRATEGY.md`
**Finding**: 30 objectives for self-improvement, all implemented as modules. Key unfinished items:
- **A — Automated Outcome Detection**: After auto-fixable improvement, re-run kaizen check and compute delta. Currently manual.
- **B — Interaction-Aware Monte Carlo**: Correlated trial sampling (Ledoit-Wolf covariance). Currently independent Bernoulli.
- **C — Counterfactual Estimation**: Synthetic control / difference-in-differences. Currently correlational, not causal.
- **X/Y/Z — Meta objectives**: Improving the improvement process itself.
**Action**: These are advanced features for after Citta Architecture completion. The prediction calibration system partially addresses A (tracking outcomes).

### 3. I Ching SIMD Strategy (June 2026)
**File**: `docs/message_board/SIMULATION_ICHING_STRATEGY.md`
**Finding**: 4-phase plan to upgrade simulation/MC systems + expand I Ching into 64-lane SIMD dispatch. Phase 1 has concrete technical fixes:
- **1a**: Analytical oscillator solution (1000x faster, removes scipy dependency)
- **1b**: FFT crate for HRR composition (32x speedup on bind/unbind)
- **1c**: Sobol sequences for MC (5-10x variance reduction)
- **1d**: Claim-specific Beta precision (more honest calibration)
- **1e**: Stratified lead-time noise (realistic distributions)
**Action**: These are high-impact, low-effort fixes. Should be prioritized after Tier 1.

### 4. Archive Excavation — 130+ Unique Modules (June 2026)
**File**: `docs/message_board/ARCHIVE_EXCAVATION_REPORT_2026-06-27.md`
**Finding**: 130+ unique modules across 6 archive sources not in v23.3.0. Key gaps:
- v0.2 modules significantly larger than v23: cli_app.py (1111 lines larger), web_research.py (731), gan_ying_enhanced.py (726), governor.py (699), graph_engine.py (679)
- v17 has 97 unique modules (most mature archived version)
- Windsurf history has 217 unique files with version history
**Action**: These are recovery candidates. Should be diffed against current versions before copying.

### 5. Clone Army Revival (June 2026)
**File**: `docs/plans/CLONE_ARMY_REVIVAL_PLAN.md`
**Finding**: All 8 phases implemented. Clone army has real infrastructure (Rust tokio, geneseed mining, victory tracking) but core "thinking" is simulated. `ollama_agent.py` has a functional LLM agent loop with tool-calling that could be wired in.
**Action**: Wire `ollama_agent` into clone systems. Low priority — needs local LLM running.

### 6. STRATA False Positive Refinement (June 2026)
**File**: `docs/message_board/STRATA_SESSION_HANDOFF_2026-06-25.md`
**Finding**: 1,485 false positives eliminated (28.2% reduction). Started at 5,272 findings, reduced to 3,787. Remaining work:
- Batch 4+ not done (more checker refinements needed)
- 9 files had logging f-string fixes reverted due to script errors
**Action**: Continue STRATA refinement in future cleanup session.

### 7. VPS Deployment Scripts Ready (June 2026)
**File**: `docs/message_board/VPS_DEPLOYMENT_HANDOFF.md`
**Finding**: Deployment scripts ready in `ops/` directory. Not yet executed. Needs interactive VPS session.
- `phase-b-harden.sh`: SSH lockdown, fail2ban, UFW
- `phase-c-deploy.sh`: Clone repos, build venv + Next.js
- `phase-d-start.sh`: Start services, health checks
- `redeploy.sh`: Quick update + restart
**Action**: Execute when VPS is provisioned. Blocked on infrastructure.

### 8. Cognitive Gaps Handoff (June 2026)
**File**: `docs/message_board/COGNITIVE_GAPS_HANDOFF.md`
**Finding**: Lists specific cognitive gaps to close. Need to review for overlap with Tier 1 Citta items.
**Action**: Review in detail during Tier 1 work.

### 9. Competitive Landscape (April 2026)
**File**: `core/docs/COMPETITIVE_LANDSCAPE_2026.md`
**Finding**: WhiteMagic vs Mem0/Zep/LangMem. Key differentiator: "Not RAG — cognitive physics." 7-layer cyberbrain vs vector store. Polyglot cognitive stack.
**Action**: Update with v23.3 features for grant applications and marketing.

### 10. LLC Banking Roadmap (April 2026)
**File**: `docs/archive/LLC_BANKING_ROADMAP_2026.md`
**Finding**: Georgia LLC formation costs $100 minimum. Fastest path: file online → EIN same day → open Axos/Mercury account → 48 hours.
**Action**: Blocked on $100 filing fee. Business infrastructure.

---

## Summary: What We Missed

| Priority | Item | Status | Action |
|----------|------|--------|--------|
| High | Prediction calibration | ✅ Done this session | — |
| High | I Ching Phase 1 fixes (5 items) | Not started | After Tier 1 |
| Medium | Recursive improvement A/B/C | Not started | After Tier 1 |
| Medium | STRATA false positive reduction | 28% done, 72% remaining | Future cleanup |
| Medium | Archive module recovery (130+) | Not started | Diff and recover |
| Medium | VPS deployment | Scripts ready, not executed | Blocked on VPS |
| Low | Clone army LLM wiring | Infrastructure ready | Needs local LLM |
| Low | LLC formation | Roadmap ready | Blocked on $100 |
| Low | Competitive landscape update | Needs v23.3 update | For grants/marketing |

---

## Docs That Can Be Archived

These are superseded or no longer actionable:
- `docs/archive/STRATEGIC_PIVOT_ANALYSIS.v1.md` — Recommended sunsetting WhiteMagic, clearly not pursued
- `docs/archive/RELEASE_READINESS_PLAN.md` — v22.0.0 release, long past
- `docs/archive/STUB_ZERO_PLAN.md` — Stubs addressed in this session
- `docs/archive/STUB_SCOUT_REPORT.md` — Superseded by AUDIT_REPORT_2026-06-28.md
- `docs/archive/STUB_AUDIT.md` — Superseded by AUDIT_REPORT_2026-06-28.md
- `docs/archive/PHASE0_AUDIT.md` — April 2026 audit, long past
