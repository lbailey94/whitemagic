# MVP Inventory: 7-Day Shippable Artifacts
## WhiteMagic Labs — Immediate Deployment Candidates

**Date:** 2026-05-29
**Status:** Active — Prioritized by leverage and effort

---

## Tier 1: WhiteMagic Core (Highest Leverage)

### 1.1 TZPF Scorecard CLI + API Update
- **What:** `python -m whitemagic.forecasting tzpf` command + updated `prescience.json` with TZPF composite metrics
- **Status:** Code complete, tests passing (8/8)
- **Ship effort:** 1 day — regenerate `prescience.json`, update site to display DFI/TAR/HC/BCI/PVS/NRS/PI
- **Action:** Regenerate API JSON with TZPF fields; add TZPF section to site dashboard

### 1.2 Prescience Paper (Public Blog Post)
- **What:** `PRESCIENCE_IN_AN_ACCELERATING_WORLD_2026-05-29.md` → published article
- **Status:** Draft complete, peer-reviewed by Aria/Grok
- **Ship effort:** 1 day — convert to HTML/blog format, add charts, publish
- **Platform:** WhiteMagic Labs site blog, Medium, Substack, or arXiv preprint
- **Action:** Format for web, add DFI visualization, publish

### 1.3 Prediction Market Tactical Plan
- **What:** `PREDICTION_MARKET_TACTICAL_PLAN_2026-05-29.md` → public strategy post
- **Status:** Draft complete, research-backed with Exa data
- **Ship effort:** 1 day — anonymize personal details, publish as "WhiteMagic Forecasting Division"
- **Action:** Redact bankroll specifics, publish as research artifact

### 1.4 WhiteMagic Labs Site — Agent-First Architecture
- **What:** `AI_PRIMARY_SITE_ARCHITECTURE.md` → implemented site features
- **Status:** Spec complete, partial implementation exists
- **Ship effort:** 2-3 days — add `/api/prescience` endpoint display, MCP manifest, machine-readable endpoints
- **Action:** Implement spec as MVP (skip zodiac marketplace for v0)

---

## Tier 2: Auxiliary Projects (Medium Leverage)

### 2.1 Aether — Live Air Quality Intelligence
- **What:** Air quality monitoring dashboard with SQLite + Express API + Vite frontend
- **Status:** Has API, collector, DB, frontend skeleton. Version 0.2.0.
- **Ship effort:** 3-5 days — polish frontend, add data visualization, deploy to VPS
- **Blocker:** Needs data source API keys (OpenAQ, PurpleAir, etc.)
- **Action:** Acquire free tier API keys, deploy static frontend + simple API

### 2.2 Project HALO (games/HAWO) — Tactical Arena Combat
- **What:** Canvas-based tactical game with AI pathfinding, unit control, PWA support
- **Status:** Version 2.8.0, has tests, build pipeline, PWA plugin
- **Ship effort:** 2-3 days — build for production, deploy to itch.io or GitHub Pages
- **Action:** `npm run build:prod`, deploy static build

### 2.3 TREMULOUS — Modern Build System
- **What:** Game mod with modern build scripts, launcher, server
- **Status:** Has build-modern/, launch scripts, docs, .desktop files
- **Ship effort:** 3-5 days — package release, write install instructions, publish release
- **Action:** Test build on clean system, create GitHub release with binaries

---

## Tier 3: Quick Wins (Low Effort, Immediate Value)

### 3.1 WhiteMagic GitHub README Refresh
- **What:** Update `README.md` with current stats (2290 tests, TZPF metrics, prescience score)
- **Status:** Current README is stale (says "Agentic AI Platform")
- **Ship effort:** 2-3 hours
- **Action:** Rewrite lede to emphasize forecasting/governance edge

### 3.2 Twitter/X Thread — "523 Weeks of Prescience"
- **What:** 10-tweet thread summarizing TZPF metrics and calibration insights
- **Ship effort:** 1 hour
- **Action:** Write, schedule, publish

### 3.3 Kalshi Account + First Trades
- **What:** Open Kalshi, deposit $500, place 2 calibration trades
- **Ship effort:** 2-3 hours (mostly KYC/setup)
- **Action:** Follow Week 1 infrastructure plan from tactical plan

### 3.4 Metaculus Account + 10 Predictions
- **What:** Create account, answer 10 AI/tech questions for calibration tracking
- **Ship effort:** 2 hours
- **Action:** Free, zero risk, builds track record

---

## Recommended 7-Day Sprint Priority

| Day | Action | Project | Effort |
|-----|--------|---------|--------|
| 1 | Regenerate prescience.json with TZPF; update site API | WhiteMagic | 4h |
| 1 | Open Kalshi account + deposit $500 | Personal | 3h |
| 2 | Publish Prescience Paper to site blog | WhiteMagic | 4h |
| 2 | Create Metaculus account + 5 predictions | Personal | 2h |
| 3 | Publish Prediction Market Tactical Plan (anonymized) | WhiteMagic | 3h |
| 3 | Write + schedule Twitter thread | Personal | 2h |
| 4 | Implement site architecture MVP (endpoints, manifest) | WhiteMagic | 6h |
| 5 | Place first 2 Kalshi trades ($20 each) | Personal | 1h |
| 5 | Build + deploy Project HALO to itch.io | HALO | 4h |
| 6 | Update README.md with current stats | WhiteMagic | 3h |
| 6 | 5 more Metaculus predictions | Personal | 2h |
| 7 | Review all shipped items, plan next sprint | All | 2h |

**Total committed effort: ~36 hours over 7 days (~5h/day)**

---

## The One Arrow

If only ONE thing ships this week, it should be:

> **Publish the Prescience Paper + regenerate the TZPF API**

Why: It converts your greatest asset (proven prescience) into a public credential. It is the foundation for everything else — grants, consulting, prediction market credibility, and investor conversations.

The second arrow: **Open the Kalshi account.**

The third arrow: **Deploy Project HALO.** Because shipping a game proves you can finish things.
