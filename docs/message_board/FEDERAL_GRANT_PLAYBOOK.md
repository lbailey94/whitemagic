# Federal Grant Playbook — WhiteMagic Labs

**Date**: 2026-04-29
**Scope**: SBIR/STTR, USDA REAP, DOE/NSF federal grants — registration, narrative strategy, commercialization, compliance, and energy monitoring
**Status**: Active — integrate with EA/philanthropic track (`GRANT_TIER_LIST_2026.md`)

---

## 0. Executive Summary

Federal grants are **not a Year 1 survival strategy** — they are a **Year 2–3 transformative bet**. The SBIR pipeline takes 12–24 months from first application to Phase II funding. However, federal grants scale to $1M+ non-dilutive capital and validate technology for enterprise/defense customers in ways that philanthropic grants cannot.

**The two-track model**:
- **Track A (EA/Philanthropic)**: Manifund, Foresight, SFF, LTFF → fast money, $5K–$200K, 2 weeks–3 months to cash
- **Track B (Federal)**: DOE SBIR, NSF SBIR, USDA REAP → transformative money, $50K–$1.5M+, 12–24 months to cash

**Rule**: Run Track A for runway. Run Track B in parallel for scale. Do not replace Track A with Track B.

---

## 1. Federal Track vs. EA/Philanthropic — Key Differences

| Dimension | EA/Philanthropic (Track A) | Federal SBIR/STTR (Track B) |
|---|---|---|
| **Timeline to cash** | 2 weeks – 3 months | 6 – 18 months |
| **LLC required?** | Preferred, not required | **Required** |
| **SAM.gov / UEI / CAGE** | Not required | **Required** |
| **Commercialization required** | No | **Yes** — "America's Seed Fund" |
| **Typical amount** | $5K – $200K | Phase I: $50K–$275K; Phase II: $750K–$1.5M |
| **Compliance** | Light (time tracking helpful) | Moderate (SF1408 pre-award survey); DCAA only for DoD Phase II |
| **IP ownership** | Usually MIT/open-source | LLC retains IP; government gets license |
| **Narrative** | Public good, safety, governance | Product, market, defense/energy application |

**Critical insight**: SBIR is not a pure R&D grant. It is a commercialization engine disguised as research funding. Your proposal must articulate a **path to market**, even if that market is "government agencies needing secure edge-AI infrastructure."

---

## 2. Opportunity Map

### 2.1 NSF SBIR — Trustworthy AI Memory Systems (Strongest Current Federal Fit)

| Field | Detail |
|---|---|
| **Agency** | National Science Foundation |
| **Amount** | Phase I: $256K (6 months); Phase II: $1M (24 months) |
| **Win Rate** | **15–20%** for first-time applicants; **25–30%** with prior NSF funding |
| **Fit** | **Strong** — NSF funds fundamental AI research with commercial potential; WhiteMagic's Karma Ledger + PRAT are novel contributions to runtime verification |
| **Narrative** | "Verifiable memory substrate for trustworthy multi-agent coordination — from research tool to commercial governance API" |
| **Timeline** | Rolling submissions via SBIR.gov; 4–6 month review cycle |
| **Entity** | LLC required; must be US-owned and <500 employees |

**Why it fits**: NSF's "Safe Learning-Enabled Systems" and "Trustworthy AI" program areas explicitly fund runtime verification, audit substrates, and memory systems with safety guarantees. The Karma Ledger's declared-vs-actual side-effect tracking is a novel contribution. The commercialization path (governance API for enterprise AI orchestration) is more mature than the DOE energy angle.

---

### 2.2 DOE SBIR — Energy-Efficient Edge Computing

| Field | Detail |
|---|---|
| **Agency** | U.S. Department of Energy |
| **Amount** | Phase I: ~$200K (6–12 months); Phase II: ~$1.1M (24 months) |
| **Win Rate** | **12–18%** for well-matched tech; **20–25%** with prior Phase I success |
| **Fit** | **Medium-Strong** — Requires an energy-aware compute benchmark or prototype to be competitive. WhiteMagic's tiered memory + local-first architecture are promising but need validation data. |
| **Narrative** | "Self-optimizing, energy-aware AI substrate for low-power, austere-environment edge compute" |
| **Timeline** | Solicitations open periodically; next likely window: Q3 2026 |
| **Entity** | LLC required; must be US-owned and <500 employees |

**Why it fits**: DOE is actively funding "energy-efficient AI inference at the edge" and "resilient distributed energy systems." A WhiteMagic node that throttles non-essential compute during low-solar-generation periods is a plausible fit, but this narrative needs actual power-consumption benchmark data to be competitive. **Prioritize NSF SBIR unless an energy benchmark is ready.**

---

### 2.3 USDA REAP — Rural Energy Infrastructure

| Field | Detail |
|---|---|
| **Agency** | USDA Rural Energy for America Program |
| **Amount** | Renewable Energy Systems: up to $1M (25–50% cost share); Energy Efficiency: up to $500K |
| **Win Rate** | **40–60%** for well-documented applications with energy audits |
| **Fit** | **Strong** — if lab is in a USDA-defined rural area (outside city of 50,000) |
| **Narrative** | "High-efficiency, off-grid R&D facility powered by solar/battery microgrid — reducing indirect costs for federal research contracts" |
| **Timeline** | Annual cycles; 12-month baseline energy data **required** |
| **Entity** | For-profit or agricultural producer; LLC qualifies |

**Why it fits**: REAP pays for 25–50% of solar/battery/efficiency upgrades. Combined with Section 48E ITC (30% federal tax credit), you can cover 55–80% of infrastructure costs. The 12-month energy baseline requirement means you must start monitoring **now** to apply in Year 2.

---

## 3. SAM.gov Registration Guide

You cannot submit a federal grant application without an active SAM.gov profile. This is the hard gate.

### Step-by-Step

| Step | Action | Cost | Time | URL |
|---|---|---|---|---|
| 1 | **File LLC** (Georgia) | $100 | 24–48 hrs | [ecorp.sos.ga.gov](https://ecorp.sos.ga.gov) |
| 2 | **Get EIN** from IRS | $0 | 5 min | [irs.gov/ein](https://irs.gov/ein) |
| 3 | **Open business bank account** | $0 | 1–3 days | Mercury / Novo / Truist |
| 4 | **Get Unique Entity ID (UEI)** | $0 | Instant | [sam.gov](https://sam.gov) — auto-assigned on registration |
| 5 | **Complete SAM.gov registration** | $0 | 2–8 weeks | [sam.gov](https://sam.gov) |
| 6 | **Receive CAGE Code** | $0 | 1–2 weeks (after SAM review) | Assigned by Defense Logistics Agency |

### SAM.gov Pro Tips
- **Do not wait** to start SAM.gov. It is notoriously slow (2–8 weeks) and often kicks back applications for minor formatting issues.
- **Use your LLC's legal name exactly** as it appears on the Georgia Secretary of State website. Any mismatch blocks approval.
- **Physical address**: Use your home address if you don't have a commercial lab yet. You can update it later.
- **NAICS codes**: Select **541715** (R&D in Physical/Engineering/Life Sciences) as primary. Add **541511** (Custom Computer Programming) as secondary.
- **Electronic Funds Transfer (EFT)**: The government verifies your bank routing and account numbers. You cannot complete SAM.gov without an active business bank account.

---

## 4. Commercialization Strategy for WhiteMagic

SBIR reviewers score "Commercialization Potential" as a major criterion. You cannot win with "this is open-source research." You need a **dual-track commercialization story**:

### Track 1: Government/Defense Market
- **Product**: Hardened, air-gapped WhiteMagic node for secure facilities
- **Customer**: DoD, DOE National Labs, DHS, intelligence community
- **Revenue model**: Per-seat license + annual support contract
- **Differentiator**: Only locally-runnable, verifiable AI memory substrate with runtime audit (Karma Ledger) and cognitive oversight (Voice Audit)

### Track 2: Enterprise Edge-AI Market
- **Product**: WhiteMagic Edge Appliance — pre-loaded on sovereign hardware (Arch Linux + custom SD-card key)
- **Customer**: Financial services, healthcare, critical infrastructure operators who cannot send data to cloud AI
- **Revenue model**: Hardware + software bundle, $5K–$25K per node
- **Differentiator**: Vendor-neutral, air-gappable, energy-efficient — runs on solar/battery microgrids

### The Open-Source Hook
Frame open-source (MIT license) as a **commercialization accelerant**, not a blocker:
> "Open-sourcing the core memory substrate builds developer trust and creates a talent pipeline. Revenue comes from hardened, supported deployments for security-conscious government and enterprise customers who require SLAs, compliance certification, and air-gapped operation."

This is the Redis / MongoDB model: open-core + commercial add-ons.

---

## 5. SBIR Narrative Templates

### 5.1 DOE SBIR — Energy-Efficient Edge Compute

**Technical Abstract (300 words)**:
> WhiteMagic Labs proposes to develop an energy-aware cognitive operating system for edge AI that dynamically optimizes compute allocation based on real-time renewable energy availability. Current AI inference at the edge is power-agnostic — servers draw maximum load regardless of solar generation, draining batteries and requiring oversized infrastructure. Our innovation is a self-optimizing memory substrate that throttles non-essential processes during low-generation periods while maintaining guaranteed uptime for security-critical tasks. Phase I will demonstrate a 30% reduction in peak power draw on a representative AI workload using a solar/battery testbed. Phase II will prototype a commercial-grade appliance for DOE National Lab deployment.

**Commercialization Paragraph**:
> The addressable market for edge AI in energy-constrained environments is estimated at $4B+ (industry reports, 2026) with strong growth driven by defense and microgrid investment. Initial customers will be DOE National Labs and DOD forward operating bases requiring off-grid AI capability. Within 18 months, we will expand to commercial microgrid operators and remote industrial facilities. Revenue model: per-node license ($15K–$50K) + annual support (20% of license). By Year 3, projected revenue: $2M ARR. *Market size and growth figures require independent citation before submission.*

### 5.2 NSF SBIR — Trustworthy AI Memory

**Technical Abstract**:
> WhiteMagic Labs proposes to commercialize Karma Ledger, a runtime audit substrate for AI agent tool-use that verifies declared-vs-actual side effects in real time. Current AI safety research lacks standardized, deployable measurement tools for multi-agent coordination failures. Karma Ledger provides a generalizable evaluation primitive applicable to any MCP-compatible tool surface. Phase I will benchmark Karma Ledger against LoCoMo and LongMemEval-S, producing an open-source evaluation protocol and peer-reviewed results. Phase II will productize the substrate as a commercial governance API for enterprise AI orchestration platforms.

**Commercialization Paragraph**:
> Enterprise AI orchestration is an estimated $10B+ market with no dominant governance layer. Karma Ledger will be offered as a SaaS API ($0.01–$0.05 per tool call audited) and as an on-premise license for air-gapped environments ($50K–$200K/year). Initial design partners: AI safety research orgs (METR, Apollo, CAIS). Year 2 target: 3 enterprise pilots. Year 3 target: $1.5M ARR. *Market size figures require independent citation before submission.*

---

## 6. REAP Application Template

### Prerequisites (Must Start Now)
- **12-month energy baseline**: Install monitoring hardware on Day 1. REAP requires historical data.
- **Energy audit**: Must be conducted by a certified energy assessor (USDA-approved). Cost: $500–$2,000. Can be reimbursed by REAP if funded.
- **Rural location**: Property must be outside a city/town of 50,000 population. Check [USDA eligibility map](https://www.rd.usda.gov/programs-services/reap).

### Application Structure

**Section 1 — Project Description (2 pages)**:
- Describe the facility: "WhiteMagic Labs R&D facility conducting AI memory system benchmarking and sovereign hardware prototyping"
- Current energy consumption: [X] kWh/year baseline from monitoring data
- Proposed system: Solar array (X kW) + battery storage (X kWh) + high-efficiency HVAC
- Expected outcomes: 60–80% reduction in grid dependency; PUE improvement from [current] to [target]

**Section 2 — Energy Assessment (1–2 pages)**:
- Attach certified energy audit report
- Highlight peak loads from server racks and fabrication equipment
- Show load-duration curves demonstrating solar/battery sizing rationale

**Section 3 — Budget & Cost Share**:
| Item | Total Cost | REAP Request (50%) | WhiteMagic Match (50%) |
|---|---|---|---|
| Solar array (20kW) | $40,000 | $20,000 | $20,000 |
| Battery storage (40kWh) | $30,000 | $15,000 | $15,000 |
| High-efficiency HVAC | $15,000 | $7,500 | $7,500 |
| Energy monitoring upgrade | $5,000 | $2,500 | $2,500 |
| **Total** | **$90,000** | **$45,000** | **$45,000** |

**Section 4 — Financial Statements**:
- 3 years of tax returns (if LLC existed) OR personal tax returns + projected LLC financials
- Balance sheet showing ability to provide 50% cost share

---

## 7. DCAA Compliance — Year 2 Checklist (Not Day 1)

**Do not over-engineer your bookkeeping for Day 1.** DCAA (Defense Contract Audit Agency) only audits DoD Phase II contracts. NSF, DOE civilian SBIR, and USDA REAP do not require DCAA.

**What you need on Day 1** (adequate for all non-DoD federal grants):
- Clean bookkeeping (Wave: free; QuickBooks Simple Start: $15/mo)
- Expense categorization by project/grant
- Time tracking by project (Toggl: free; Harvest: $12/mo)
- Separate bank accounts or sub-ledgers for restricted vs. unrestricted funds

**What you need before DoD Phase II** (DCAA SF1408 pre-award survey):
- [ ] **Total timekeeping**: Daily time logs by project/task, personally certified by you
- [ ] **Job costing**: Direct vs. indirect cost segregation
- [ ] **Payroll system**: Gusto or Rippling with W-2 issuance
- [ ] **Chart of accounts**: Quarantined unallowable costs (alcohol, lobbying, entertainment)
- [ ] **Written policies**: Timekeeping, purchasing, travel, indirect cost allocation

**Rule**: Start with Wave + Toggl. Upgrade to QuickBooks + Harvest when you hit $100K annual grant revenue. Add Gusto + DCAA policies only when you pursue DoD Phase II.

---

## 8. Energy Monitoring Stack for REAP Baseline

To build an auditable 12-month energy trail, deploy this stack on Day 1:

### 8.1 Panel-Level Monitoring (Macro View)
- **Hardware**: Shelly Pro 3EM or Emporia Vue (flashed with custom firmware for local-only operation)
- **Placement**: CT clamps on main incoming lines from solar inverter/battery + dedicated circuits for HVAC, lighting, wall outlets
- **Data**: Logged locally via MQTT to avoid cloud dependency

### 8.2 Server Rack Monitoring (AI Compute Load)
- **Hardware**: Metered Smart PDU (APC, Eaton, CyberPower)
- **Data**: Per-rack voltage, amperage, kWh — isolate the cost of specific training runs or benchmark suites

### 8.3 Fabrication Tools (Transient Spikes)
- **Hardware**: Heavy-duty inline power meters rated for 15A–20A loads
- **Data**: Tag each tool in the ledger. When auditors ask why consumption spiked 3,000W for 4 hours, your logs show "CNC fabrication run — Project X prototype"

### 8.4 The Sovereign Data Ledger (Software)
- **Stack**: Raspberry Pi or Arch Linux node running Home Assistant → Prometheus time-series DB → Grafana dashboards
- **Export**: CSV with minute-by-minute resolution. Hand this to the USDA energy auditor in Month 12.
- **Bonus**: Use these same logs to bill "direct utility costs" to DOE/NSF grants for specific benchmark runs.

---

## 9. Timeline & Parallel Execution

### Track A (EA/Philanthropic) — Run in Foreground
| Month | Action | Output |
|---|---|---|
| 0–1 | Manifund + LTFF + Foresight | $25K–$75K runway |
| 2–3 | SFF Rolling submitted | Credibility signal building |
| 3–6 | arXiv preprint + LoCoMo benchmark | Strengthens all future apps |
| 6–12 | SFF HSEE + ongoing Manifund follow-ons | $50K–$150K total |

### Track B (Federal) — Run in Background
| Month | Action | Output |
|---|---|---|
| 0–1 | File LLC → EIN → Bank → SAM.gov/UEI/CAGE | Federal eligibility unlocked |
| 1–2 | Draft DOE + NSF SBIR Phase I proposals | Submission-ready narratives |
| 2–3 | Submit SBIR proposals (next solicitation window) | Applications in review |
| 3–6 | Energy monitoring baseline established | 3 months of REAP-ready data |
| 6–9 | SBIR Phase I award decisions | Possible $200K–$256K award |
| 9–12 | Energy audit + REAP application submitted | Possible $45K–$500K cost share |
| 12–18 | SBIR Phase I execution + Phase II application | $1M+ potential |
| 18–24 | Phase II execution + commercialization pilots | Product-market fit validation |

**Combined EV**: Track A ($50K–$150K by Q1 2027) + Track B ($0–$1.5M+ by Q4 2027) = **$50K–$1.65M total non-dilutive capital over 24 months.**

---

## 10. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SAM.gov delays block SBIR submission | Medium | High | Start SAM.gov immediately after LLC approval; expect 4–8 weeks |
| SBIR commercialization requirement conflicts with open-source mission | Low | Medium | Frame open-source as accelerant, not blocker (Redis model) |
| REAP rural eligibility denied | Medium | High | Verify USDA map before lease/signing; Thunderbolt/Effingham County likely qualify |
| 12-month energy baseline insufficient for REAP | Low | High | Start monitoring Day 1; 12 months is a hard requirement |
| DCAA audit failure on DoD Phase II | Low | High | Only pursue DoD after $100K+ revenue; hire DCAA consultant for $3K–$5K |
| LLC formation delays SFF submission | Low | Medium | Georgia approval is 24–48 hours; EIN is instant; bank is 1–3 days |
| Federal grant narrative is too "researchy" | Medium | High | Use templates in §5; every paragraph must answer "who will buy this?" |

---

## 11. Quick-Reference: Federal Grant Acronyms

| Acronym | Meaning | Context |
|---|---|---|
| **SBIR** | Small Business Innovation Research | Federal R&D grants for small businesses |
| **STTR** | Small Business Technology Transfer | SBIR variant requiring university partner |
| **REAP** | Rural Energy for America Program | USDA grants for rural energy upgrades |
| **SAM.gov** | System for Award Management | Federal contractor registry |
| **UEI** | Unique Entity Identifier | Your business's federal ID (replaced DUNS) |
| **CAGE** | Commercial and Government Entity | DoD-specific location code |
| **DCAA** | Defense Contract Audit Agency | Audits DoD contractor accounting |
| **SF1408** | Pre-Award Survey of Prospective Contractor Accounting System | DCAA compliance checklist |
| **PUE** | Power Usage Effectiveness | Data center efficiency metric (total power / IT power) |
| **ITC** | Investment Tax Credit | Section 48E federal tax credit for clean energy |
| **NAICS** | North American Industry Classification System | Business category codes |

---

*Document maintained by WhiteMagic Labs. Last updated: 2026-04-29.*
