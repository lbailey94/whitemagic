# Grant Execution Plan — 2026-04-28

> **Status**: Active — Updated after 2026-04-28 strategy discussion
> **Owner**: Lucas Bailey / WhiteMagic Labs
> **Scope**: Consolidated action sequence derived from user decisions + research

---

## 0. Core Decisions (Locked)

| Decision | Rationale |
|---|---|
| **Schmidt Tier 1 → P3 (defer/skip)** | Perfectionism blocker + low solo odds (8–12%) + 19-day deadline. Revisit only if bandwidth remains after higher-ROI apps. |
| **BlueDot → Skip** | Not in network; eligibility blocker. Don't spend time. |
| **Manifund → P0 (immediate)** | 40–55% win rate, no entity required, fastest money. Target 3–5 scoped asks simultaneously across 2–3 regrantors. |
| **Foresight → P1 (target May 31)** | Better with LLC + project pages visible. Not rushing for Apr 30 deadline. |
| **SFF Rolling → P1 (after LLC)** | Life-changing if won; LLC unlocks it entirely. Funding arrives Q1 2027 regardless. |
| **SFF HSEE → P1 (target July 8)** | Comfortable timeline; strong framing fit. |
| **ACX → Defer to Dec 2026** | Line up wilder CODEX ideas for later. |
| **Federal Track → P2 (background)** | DOE/NSF SBIR + USDA REAP are Year 2–3 transformative bets, not survival money. Start SAM.gov + energy monitoring now; submit proposals in Q3 2026. |

---

## 0. Phase 0: Foundation — Entity & Federal Eligibility (Day 1–2)

### 0.1 File LLC + EIN (Day 1)
- **Action**: File Georgia LLC online via eCorp portal ($100)
- **Name**: "WhiteMagic Labs LLC" (verify availability first)
- **Wait**: 24–48 hours for Georgia approval

### 0.2 Get EIN (Day 1–2, after LLC approval)
- **Action**: Apply for EIN at irs.gov (free, 5 minutes)
- **Output**: EIN confirmation letter (CP 575) — save as PDF

### 0.3 Draft Operating Agreement (Day 1–2)
- **Must include**:
  - "Hereby assigns" IP clause (present tense, not future)
  - Exhibit A listing all pre-LLC assets (Project Whitemagic codebase, hardware designs, benchmarks)
  - AI-assisted work clause capturing prompt architectures and curated outputs
- **Template**: See `FEDERAL_GRANT_PLAYBOOK.md` §4

---

## 1. Immediate Actions — Track A: Fast Money (Apr 28–May 5)

### 1.1 Open Business Bank Account (Day 2–3, after EIN)
- **Primary recommendation**: Mercury ($0 minimum, $0 monthly, multiple sub-accounts)
  - Create 3 sub-accounts: "Restricted Grants", "Unrestricted Ops", "Payroll Reserve"
- **Alternative**: Truist Simple ($100 minimum, $0 monthly, $400 bonus if deposit $2K within 30 days using promo `SB26Q2CHECKING` through 7/9/2026)

### 1.2 Start SAM.gov Registration (Day 3, after bank account opens)
- **Action**: Register at [sam.gov](https://sam.gov) using exact LLC legal name
- **Required**: Bank routing/account numbers for EFT verification
- **Timeline**: 2–8 weeks (start immediately; do not wait)
- **Output**: UEI (auto-assigned) + CAGE code (1–2 weeks after SAM review)

### 1.3 Submit Manifund Applications (Day 1–3)
- **Target regrantors**: Joel Becker (AI safety infra), Neel Nanda (interpretability), Gavin Leech (forecasting)
- **Scoped asks**:
  1. **Joel Becker**: "$25K — Karma Ledger benchmark on 100+ tool interactions; publish open-source evaluation protocol"
  2. **Neel Nanda**: "$15K — Voice Audit for tool-selection hallucination detection; adversarial red-team + measurement"
  3. **Gavin Leech**: "$10K — Foresight Engine drift prediction validation; 3-month forecasting benchmark"
- **Effort**: 2–3 hours per ask (6–9 hours total)

### 1.4 Submit LTFF Application (Day 3–4)
- **Frame**: "Open-source governance infrastructure for multi-agent AI safety"
- **Ask**: $25K–$50K for 6 months
- **Effort**: 4–6 hours

---

## 2. Credibility Building (May 5–20)

### 2.1 arXiv Preprint (Highest ROI Action)
- **Action**: Convert `KARMA_LEDGER_PAPER_OUTLINE.md` → LaTeX → arXiv submission
- **Effort**: 8–12 hours
- **Impact**: Strengthens every grant application simultaneously
- **Deadline**: Submit by May 10 (before Foresight and SFF applications)

### 2.2 Run LoCoMo Benchmark (Optional)
- **Action**: Execute `core/eval_aux/locomo_v019_benchmark.py` or equivalent
- **Effort**: 4–8 hours
- **Impact**: Removes Schmidt blocker; signals technical depth for all apps
- **Decision**: Only if bandwidth remains after Manifund + LTFF + arXiv

### 2.3 Submit Foresight AI Nodes (By May 31)
- **Focus area**: "Decentralized & Cooperative AI" or "AI for Security"
- **Engagement plan**: Propose quarterly SF/Berlin visits + remote participation + workshop hosting
- **Ask**: $75K–$125K for 12 months
- **Effort**: 6–8 hours

---

## 3. Long-Term Runway — Track A Continued (May 20–July 8)

### 3.1 Submit SFF Rolling Application (After LLC + bank account)
- **Track**: Freedom Track
- **Ask**: $120K–$180K over 18 months
- **Effort**: 12–16 hours
- **Expected funding**: Q1 2027 (6–8 month S-Process)

### 3.2 Submit SFF HSEE Theme (By July 8)
- **Frame**: "Cognitive infrastructure for human-AI co-intelligence"
- **Ask**: $50K–$200K
- **Effort**: 15–20 hours
- **Condition**: Only if SFF Rolling is already submitted; otherwise prioritize Rolling

---

## 4. Track B: Federal Grants — Background Execution (May–Dec 2026)

> **Rule**: Track B runs in parallel with Track A. It does not replace Track A. Federal grants are Year 2–3 transformative bets, not survival money.

### 4.1 SAM.gov / UEI / CAGE (May, ongoing)
- **Action**: Monitor SAM.gov registration status; respond to any kickbacks within 24 hours
- **Output**: Active SAM.gov profile with UEI and CAGE code

### 4.2 Energy Monitoring Stack (May, Day 1 of lab operation)
- **Action**: Deploy Shelly Pro 3EM (panel-level) + APC Metered PDU (rack-level) + Prometheus/Grafana (data historian)
- **Cost**: ~$300–$500 in hardware
- **Output**: Minute-by-minute energy logs starting Day 1

### 4.3 Draft DOE SBIR Phase I (May–July)
- **Narrative**: "Self-optimizing, energy-aware AI substrate for low-power edge compute"
- **Commercialization**: Hardened edge appliance for DOE National Labs / DOD forward operating bases
- **Effort**: 20–30 hours
- **Submit**: Next DOE SBIR solicitation window (likely Q3 2026)

### 4.4 Draft NSF SBIR Phase I (May–July)
- **Narrative**: "Karma Ledger — runtime audit substrate for trustworthy multi-agent coordination"
- **Commercialization**: Governance API for enterprise AI orchestration ($0.01–$0.05 per audit call)
- **Effort**: 20–30 hours
- **Submit**: Rolling via SBIR.gov

### 4.5 USDA REAP Preparation (May 2026–May 2027)
- **Action**: Maintain 12-month energy baseline; schedule certified energy audit in Month 10
- **Apply**: May 2027 (first eligible cycle after baseline)
- **Expected award**: $45K–$200K (25–50% cost share)

---

## 5. Deferred / Background

| Opportunity | Trigger | Action |
|---|---|---|
| **Schmidt Tier 1** | Only if bandwidth by May 10 | 40–60 hours; arXiv preprint + LoCoMo benchmark would be prerequisites |
| **Coefficient Giving** | After first Manifund/Foresight win | Use as credibility signal in 1–2 page unsolicited proposal |
| **ACX Grants** | December 2026 | Scope wilder CODEX ideas then |
| **GitHub Sponsors** | Anytime | 2 hours to set up; low priority but good signal |

---

## 6. Expected Value Math

### Scenario A: Track A Only (EA/Philanthropic)

| Source | Ask | Win Rate | Expected Value | Timeline |
|---|---|---|---|---|
| Manifund (3 asks) | $50K combined | 45% | $22.5K | 2–4 weeks |
| LTFF | $30K | 20% | $6K | 1–2 months |
| Foresight | $100K | 30% | $30K | 2 months |
| SFF Rolling | $150K | 22% | $33K | Q1 2027 |
| SFF HSEE | $125K | 18% | $22.5K | Nov 2026 |
| **Combined estimated chance of ≥1 success** | — | **~60–70%** | — | — |

**Most likely near-term outcome**: $25K–$75K from Manifund + LTFF + Foresight within 3 months.
**Most likely total outcome**: $50K–$150K across all Track A sources by Q1 2027. These are heuristic estimates based on base-rate analysis, not guarantees.

### Scenario B: Track A + Track B (Federal)

| Source | Ask | Win Rate | Expected Value | Timeline |
|---|---|---|---|---|
| Track A (above) | $455K combined | ~60–70% P≥1 | $114K | 0–18 months |
| DOE SBIR Phase I | $200K | 15% | $30K | Q4 2026–Q1 2027 |
| NSF SBIR Phase I | $256K | 18% | $46K | Q4 2026–Q1 2027 |
| USDA REAP | $90K | 50% | $45K | Q2 2027 |
| DOE SBIR Phase II* | $1.1M | 40% | $440K | Q3 2027–Q4 2028 |
| **Combined estimated chance of ≥1 success** | — | **~70–85%** | — | — |

*Phase II win rate assumes successful Phase I completion.

**Most likely total outcome (both tracks)**: $100K–$300K by Q1 2027; $300K–$1M+ by Q4 2027 if Phase II hits.
**Best case**: $1.5M+ if SFF + DOE Phase II + REAP all hit.

**Key insight**: Track B adds **$0 upfront cost** (just time) but increases the ceiling by 10x. The federal proposals can reuse 80% of the Track A narrative (team, prior art, technical approach) with a commercialization paragraph added.

---

## 6. Tracking & Compliance

### If Multiple Grants Approved

| Requirement | Tool | Cost |
|---|---|---|
| Time-and-expense tracking | Toggl (free) or Harvest ($12/mo) | $0–$12/mo |
| Accounting / sub-ledgers | Wave (free) or QuickBooks ($15/mo) | $0–$15/mo |
| Grant-specific bank accounts | One Mercury/Novo account + sub-ledgers | $0 |

**Recommendation**: One business account + Wave accounting software with separate "classes" or tags per grant. Simpler than multiple accounts for sub-$200K total funding.

**Schmidt + SFF specifically**: Require periodic reports. Track everything from Day 1.

---

## 7. Weekly Pulse Check

| Week | Deliverable | Blocker |
|---|---|---|
| Apr 28–May 3 | LLC filed; Manifund submitted; LTFF submitted | LLC approval wait (7 days) |
| May 4–10 | arXiv preprint submitted; bank account opened | None |
| May 11–17 | Foresight application drafted; SFF Rolling drafted | Schmidt decision (skip or sprint) |
| May 18–24 | Foresight submitted; SFF Rolling submitted | None |
| May 25–31 | Buffer / polish | None |
| Jun 1–Jul 8 | SFF HSEE drafted + submitted | None |

---

*Last updated: 2026-04-28*
