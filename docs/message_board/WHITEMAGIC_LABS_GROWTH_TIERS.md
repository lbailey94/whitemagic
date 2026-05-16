# WhiteMagic Labs — Growth Tiers & Strategic Roadmap

**Date**: 2026-04-30
**Purpose**: Clarified organizational growth model with entry/exit criteria, decision gates, failure modes, and concrete deliverables at each stage. Complements `GRANT_TIER_LIST_2026.md` (which ranks funding opportunities) and `GRANT_EXECUTION_PLAN_2026-04-28.md` (which drives week-by-week action).

**Relationship to other docs**:
- `GRANT_TIER_LIST_2026.md` = *Which grants to apply for, ranked by accessibility*
- `GRANT_EXECUTION_PLAN_2026-04-28.md` = *What to do this week*
- **This doc** = *How the organization itself evolves, stage by stage*

---

## Executive Summary

WhiteMagic Labs grows through **6 organizational tiers**, from legal formation to infrastructure provider. Each tier has:
- **Entry trigger**: What must happen to enter this tier
- **Duration**: Typical timeline (not a deadline)
- **Funding mix**: Where the money comes from
- **Core deliverables**: What must be produced to advance
- **Decision gate**: The go/no-go criteria for moving to the next tier
- **Failure mode**: What happens if the tier stalls, and how to recover
- **Pivot paths**: How robotics, energy, and other R&D fit at this stage

**The honest truth**: Most labs stall at Tier 2. The ones that reach Tier 4+ have one thing in common: they won **at least one federal grant** and used it to fund the jump from software to hardware. Federal grants are not optional for deep-tech scaling. They are the bridge.

---

## Tier 0: Legal Formation & First Dollars

**Entry trigger**: Decision to incorporate + $100 filing fee  
**Duration**: Days 1–30  
**State**: Bureaucratic boot-up. No revenue. No lab. Just paperwork and first applications.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Personal savings / bootstrapping | $0–$500 | 100% | Immediate |
| Business credit card (float) | $5K–$25K limit | 80% | Day 3 |
| Manifund regrants | $10K–$50K | 40–55% | 2–4 weeks |
| LTFF | $10K–$50K | 15–25% | 1–2 months |

**Total accessible**: $15K–$75K in first 60 days

### Core Deliverables
1. **Georgia LLC filed** (Day 1)
2. **EIN obtained** (Day 2)
3. **Mercury bank account** (Day 3)
4. **Business credit card** (Day 3)
5. **3+ Manifund asks submitted** (Day 1–7)
6. **LTFF application submitted** (Day 3–7)
7. **SAM.gov registration started** (Day 3–5)

### Decision Gate: Advance to Tier 1?
**GO if**: ≥1 Manifund grant approved OR ≥$15K total committed funding  
**NO-GO if**: All Manifund/LTFF rejections by Day 60  
**Recovery**: Refine and resubmit. Apply to more regrantors. Expand ask scope.

### Pivot Paths (Robotics/Energy/Other)
- **Robotics**: Not yet. No hardware, no fabrication space, no capital.
- **Energy**: Start monitoring only. Deploy Shelly Pro 3EM + Grafana for 12-month REAP baseline.
- **Other**: Focus. The only "other" at this tier is the Bounty Hunter node concept (Month 3+ project).

### Risk Register
| Risk | Likelihood | Mitigation |
|---|---|---|
| Manifund rejections | Medium (45–60%) | Submit 3+ asks; iterate on feedback |
| LLC name taken | Low | Have backup names ready |
| Personal credit limits card | Medium | Apply to 2 issuers; use personal card if needed |
| SAM.gov delays | Low | File immediately; 10-day typical processing |

---

## Tier 1: The Sovereign Sandbox

**Entry trigger**: ≥$15K committed funding + active SAM.gov registration  
**Duration**: Months 1–6  
**State**: First revenue. Dedicated workspace (even if that's a spare room). Software finalized. Energy baseline started.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Manifund (follow-on) | $10K–$30K | 30–40% | Month 2–4 |
| Foresight AI Nodes | $25K–$75K | 25–35% | Month 2–3 |
| SFF Speculation Grant | $5K–$20K | 90%+ (auto-approved if SFF Rolling submitted) | Month 3–4 |
| SBA Microloan | $5K–$25K | 50% | Month 3–6 |
| **Total accessible** | **$45K–$175K** | | |

**Critical assumption**: This tier assumes you win **at least one** additional grant beyond Tier 0. If not, you burn runway and drop back to Tier 0.

### Core Deliverables
1. **Dedicated workspace secured** (Month 1) — even a spare room with a door that closes
2. **Solar/battery microgrid baseline started** (Month 1) — Shelly Pro 3EM deployed, Grafana logging
3. **Karma Ledger benchmark run** (Month 2) — LoCoMo or LongMemEval-S results published
4. **arXiv preprint submitted** (Month 2) — citable artifact for all future applications
5. **Foresight AI Nodes application submitted** (Month 2) — target May 31
6. **SFF Rolling Application submitted** (Month 2–3) — requires LLC + bank account
7. **First paying customer or design partner** (Month 3–6) — even $1K/month consulting proves commercial viability

### Decision Gate: Advance to Tier 2?
**GO if**: ≥$50K annualized revenue (grants + consulting + prizes) AND working hardware prototype  
**NO-GO if**: Revenue <$30K by Month 6 AND no hardware prototype  
**Recovery**: Extend runway with more Manifund asks, consulting, or prize competitions. Do not advance to Tier 2 underfunded.

### Pivot Paths
- **Robotics**: Still not yet. But start **designing** the first physical prototype. Sketch chassis concepts. Research actuator costs. Build a BOM (bill of materials).
- **Energy**: The microgrid is now a **deliverable**, not just monitoring. Document power optimization algorithms. Package as IP.
- **Systems design**: Start the "Civilization Dashboard" as a **software prototype** — ingest weather, energy, and supply chain data. Prove the concept before building hardware.

### Bounty Hunter Node
**Build it now** (Month 3–4). You have enough of a codebase, schematics directory, and proposal drafts to make RAG matching useful. This is when the ROI starts.

---

## Tier 2: The Funded Edge

**Entry trigger**: ≥$50K annualized revenue + working hardware prototype (even crude)  
**Duration**: Months 6–18  
**State**: First federal grant (Phase I) or major philanthropic grant ($100K+). DCAA-compliant timekeeping. Physical fabrication begins.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Federal SBIR Phase I (NSF/DOE/DOD) | $150K–$275K | 12–20% | Month 6–12 |
| SFF Main Round or HSEE | $50K–$200K | 15–25% | Month 6–12 |
| SFF Rolling (if deferred) | $50K–$200K | 18–25% | Month 9–15 |
| USDA REAP | $20K–$100K | 40–60% | Month 12–15 |
| Challenge.gov / DIU prizes | $10K–$50K | 20–30% | Ongoing |
| Consulting / B2B services | $2K–$10K/month | 60% | Ongoing |
| **Total accessible** | **$280K–$825K** | | |

**Critical assumption**: This tier assumes you win **at least one** Phase I federal grant OR a major philanthropic grant. If neither hits by Month 12, you are in a danger zone.

### Core Deliverables
1. **SBIR Phase I execution** (Month 6–12) — feasibility study, benchmark results, prototype demonstration
2. **USDA REAP application** (Month 12) — 12-month energy baseline complete, certified audit attached
3. **First physical product** (Month 9–12) — milled enclosure, assembled edge node, thermal testing
4. **Commercialization plan** (Month 9) — "Who will buy this?" answered with customer conversations
5. **Bounty Hunter node operational** (Month 6) — generating 2–5 opportunity briefs/month
6. **DCAA-compliant bookkeeping** (Month 6) — if federal grants hit, this is mandatory

### Decision Gate: Advance to Tier 3?
**GO if**: ≥$200K annualized revenue AND ≥1 federal Phase I award AND ≥2 design partners/customers  
**NO-GO if**: No federal grant by Month 18 AND revenue <$100K  
**Recovery**: Double down on prize competitions (Challenge.gov, DIU CSO) and consulting. Use prize money to fund prototype improvements. Reapply to same SBIR programs with stronger data.

### Pivot Paths
- **Robotics**: **NOW**. First robotic prototype. Start with a simple platform: ROS-based autonomous ground vehicle or drone. Integrate the WhiteMagic edge node as the "brain." Target environmental monitoring or security patrol use cases.
- **Energy**: The microgrid is now a **standalone product**. Package the control algorithms as licensable IP. Offer "sovereign microgrid design" as a consulting service.
- **Alternative R&D**: Use IR&D (Internal Research & Development) budget from Phase I grants to explore adjacent areas. SBIR rules allow up to ~10% of direct costs for IR&D.

### Honest Reality Check
**Most labs stall here.** The jump from Tier 2 to Tier 3 requires winning a **Phase II federal grant** ($750K–$1.5M). Phase II win rates are 30–40% for Phase I awardees, but you need a **compelling prototype and commercial traction** to be competitive. Start building both on Day 1 of Phase I.

---

## Tier 3: Physical Automation & Tactical Deployment

**Entry trigger**: ≥$200K annualized revenue + ≥1 federal Phase I award + ≥2 design partners  
**Duration**: Years 2–3  
**State**: Phase II federal funding. Full-time R&D team (2–3 people). Robotics prototypes operational. Revenue from products, not just grants.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Federal SBIR Phase II | $750K–$1.5M | 30–40% (if Phase I awardee) | Year 2 |
| SFF follow-on | $100K–$300K | 25–35% | Year 2–3 |
| Direct B2B contracts | $5K–$25K/month | 40% | Ongoing |
| Equipment financing | $25K–$100K | 60% | As needed |
| Licensing revenue | $1K–$10K/month | 30% | Ongoing |
| **Total accessible** | **$900K–$2.5M** | | |

### Core Deliverables
1. **SBIR Phase II execution** (Year 2) — full-scale prototype, pilot deployment, commercialization
2. **First robotic product** (Year 2) — autonomous unit with WhiteMagic edge compute, off-grid capable
3. **First commercial sale** (Year 2) — not a grant, not consulting, but a product sale
4. **Expanded lab facility** (Year 2) — commercial space, not spare room
5. **Full-time hires** (Year 2) — 1–2 engineers or technicians
6. **IP portfolio** (Year 2–3) — 1–2 patents filed (optional but helpful for defense contracts)

### Decision Gate: Advance to Tier 4?
**GO if**: ≥$500K annualized revenue AND ≥1 commercial product AND ≥1 Phase II award  
**NO-GO if**: Revenue <$300K by Year 3 OR no commercial product  
**Recovery**: Pivot to pure consulting/services if product development stalls. Use established relationships to win OTA (Other Transaction Authority) contracts. Consider strategic partnership with a prime contractor (Lockheed, Raytheon) as a subcontractor.

### Pivot Paths
- **Robotics**: Full product line. Environmental monitoring units (solar-powered, long-endurance). Tactical edge-compute platforms (ruggedized, air-gapped). Maybe both.
- **Energy**: Turnkey microgrid product. Sell to remote facilities, data centers, or government installations. The lab itself is the demo.
- **Macro-systems**: Start networking multiple edge nodes. Demonstrate distributed coordination. Build the "Civilization Dashboard" as a B2B product for infrastructure operators.

---

## Tier 4: Infrastructure Provider

**Entry trigger**: ≥$500K annualized revenue + ≥1 commercial product + ≥1 Phase II award  
**Duration**: Years 3–5  
**State**: Multi-product company. 5–10 employees. Revenue from products, licensing, and federal contracts. Recognized player in sovereign compute / edge AI.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Multi-agency federal contracts | $500K–$2M/year | 20–30% | Ongoing |
| SBIR Phase II extensions / follow-on | $250K–$500K | 25–35% | Ongoing |
| B2B product sales | $20K–$100K/month | 40% | Ongoing |
| Licensing + royalties | $5K–$20K/month | 30% | Ongoing |
| Strategic partnerships | Varies | 15–25% | Ad hoc |
| **Total accessible** | **$1M–$5M/year** | | |

### Core Deliverables
1. **Product line**: 2–3 distinct products (edge node, robotics platform, microgrid controller)
2. **Customer base**: 5–10 paying customers, including ≥1 government agency
3. **Team**: 5–10 full-time employees
4. **Facilities**: Dedicated commercial lab + light manufacturing capability
5. **Revenue**: 60%+ from products/services, not grants
6. **Brand**: Recognized in sovereign compute / edge AI / tactical robotics communities

### Decision Gate: Advance to Tier 5?
**GO if**: ≥$2M annualized revenue AND profitable OR clear path to profitability within 12 months  
**NO-GO if**: Still grant-dependent (>50% revenue from grants) by Year 5  
**Recovery**: If still grant-dependent, either (a) double down on commercialization, (b) seek acquisition by a prime contractor, or (c) pivot to pure R&D services (become a specialized subcontractor).

### Pivot Paths
- **Robotics**: Full autonomous systems integrator. Not just the brain — the whole platform. Possible defense contracts for perimeter security, logistics, or environmental monitoring.
- **Energy**: Regional microgrid designer/installer. Partner with solar installers. Offer "sovereign facility" packages (compute + energy + security).
- **Macro-systems**: The "Civilization Dashboard" is now a real product. Sell to cities, states, or large infrastructure operators for resilience planning.

---

## Tier 5: Deep Technology & Strategic R&D

**Entry trigger**: ≥$2M annualized revenue + profitability + established market position  
**Duration**: Years 5+  
**State**: Not a startup. A sustainable R&D organization with the freedom to pursue high-risk, long-term projects.

### What This Actually Means (Grounded)
This is not "shaping how humanity interacts with matter and energy." That is vision-speak. Here is the operational reality:

**Tier 5 is when WhiteMagic Labs has enough recurring revenue and credibility to pursue 10-year bets without betting the company.**

### Examples of Tier 5 Projects (Concrete)
1. **Advanced materials**: Develop novel thermal interface materials for edge-compute cooling. Partner with a university materials lab.
2. **Orbital/aerial platforms**: Adapt the edge-compute node for high-altitude balloon or satellite applications. Partner with NASA or Space Force.
3. **Autonomous fabrication**: Robotic systems that can manufacture custom hardware in austere environments (forward operating bases, disaster zones, remote facilities).
4. **Distributed intelligence networks**: Coordinate 100+ autonomous nodes in real-time for large-area monitoring or logistics.

### Funding Mix
| Source | Amount | Probability | Timeline |
|---|---|---|---|
| Multi-year federal contracts | $1M–$5M/year | 25–35% | Ongoing |
| ARPA-E / DARPA programs | $500K–$3M | 15–25% | Per program |
| Commercial revenue | $200K+/month | 60% | Ongoing |
| Strategic partnerships | Varies | 20–30% | Ad hoc |
| **Total accessible** | **$3M–$10M+/year** | | |

### Decision Gate: Stay at Tier 5?
**STAY if**: Revenue is growing, team is stable, and R&D pipeline is healthy  
**EXIT if**: Market shifts, technology obsoletes, or founder wants to move on  
**EXIT options**: Acquisition by prime contractor, merger with complementary firm, or spin off divisions as separate entities

---

## Cross-Reference: How Grant Tiers Map to Growth Tiers

| Growth Tier | Grant Tier (from `GRANT_TIER_LIST`) | Primary Funding |
|---|---|---|
| **Tier 0** (Formation) | Tier 0: Manifund, BlueDot, GitHub Sponsors | Philanthropic / personal |
| **Tier 1** (Sandbox) | Tier 1: Foresight, LTFF, Schmidt Tier 1 | Philanthropic / prizes |
| **Tier 2** (Funded Edge) | Tier 1.5: DOE/NSF SBIR Phase I, USDA REAP | Federal Phase I / philanthropic |
| **Tier 3** (Automation) | Tier 2: SFF Rolling/HSEE, SBIR Phase II | Federal Phase II / commercial |
| **Tier 4** (Infrastructure) | Tier 3: Multi-PI collaborations, ARIA | Federal contracts / commercial |
| **Tier 5** (Deep Tech) | N/A — self-funded R&D | Commercial revenue / DARPA |

---

## Failure Modes & Recovery at Every Tier

### Tier 0 Failure: Can't raise first $15K
**Symptoms**: All Manifund/LTFF rejections, no consulting clients  
**Recovery**:
- Refine asks based on feedback
- Expand to more regrantors (don't just hit 3; hit 10)
- Take short-term consulting gigs to build credibility
- Apply to prize competitions (even $5K bounties)
- **Do not** take on debt or VC at this stage

### Tier 1 Failure: Revenue <$30K by Month 6
**Symptoms**: Grants too small, no consulting, burning savings  
**Recovery**:
- Extend runway by taking on more consulting (B2B AI safety, secure LLM setup)
- Lower burn rate (work from home, no lab rent)
- Reapply to same grantors with improved proposals
- Consider part-time employment while building WhiteMagic nights/weekends

### Tier 2 Failure: No federal grant by Month 18
**Symptoms**: Revenue stuck at $50K–$100K, no Phase I award  
**Recovery**:
- Double down on prize competitions (Challenge.gov, DIU CSO) — faster than SBIR
- Use prize money to fund prototype improvements
- Partner with a university for STTR (university co-PI improves odds)
- Consider subcontracting to a prime contractor (they have the relationships; you have the tech)

### Tier 3 Failure: No commercial product by Year 3
**Symptoms**: Revenue still grant-dependent, no product sales  
**Recovery**:
- Pivot to services: "WhiteMagic Labs designs and deploys sovereign AI infrastructure"
- Become a specialized subcontractor for prime contractors
- License IP to larger companies rather than building products yourself
- Consider merger with a complementary firm

### Tier 4+ Failure: Grant dependency >50% at Year 5
**Symptoms**: Revenue spikes and crashes with grant cycles, unstable team  
**Recovery**:
- Halt new R&D, focus entirely on commercialization of existing IP
- Raise prices on consulting/services
- Seek acquisition by a prime contractor who wants your tech + team
- Or: accept that WhiteMagic Labs is a niche R&D shop, not a product company, and optimize for that

---

## Honest Assessment: What Are the Odds?

**Probability of reaching each tier** (based on SBIR base rates and deep-tech startup data):

| Tier | Probability (from Tier 0 start) | Key Dependency |
|---|---|---|
| **Tier 1** (Sandbox) | **85%** | File LLC + submit grants |
| **Tier 2** (Funded Edge) | **60%** | Win ≥1 additional grant |
| **Tier 3** (Automation) | **30%** | Win federal Phase I |
| **Tier 4** (Infrastructure) | **15%** | Win federal Phase II + commercial traction |
| **Tier 5** (Deep Tech) | **5%** | Sustained profitability + market position |

**Translation**: You are very likely to reach Tier 1 ( Sandbox). You have a coin-flip chance of reaching Tier 2. Tier 3+ is a long shot — but the expected value is still massive because the upside ($1M+ non-dilutive capital) is so high relative to the cost ($100 LLC fee + time).

**The strategy**: Treat Tier 0–2 as the goal. Tier 3+ is a bonus. Don't sacrifice Tier 0–2 execution by daydreaming about Tier 5.

---

## Pivot Architecture: How Robotics, Energy, and Systems Design Fit

### The Core Insight
WhiteMagic Labs is not "an AI company that might do robotics." It is a **sovereign compute substrate** that can be deployed in any physical form factor. The pivot is not a change of direction — it is a change of **packaging**.

| Pivot | Current Form | Future Form | Funding Path |
|---|---|---|---|
| **Robotics** | Edge-compute node (software + hardware) | Edge-compute node + robotic chassis (mobile autonomous platform) | DoD SBIR (tactical autonomy), NSF SBIR (robotics), DIU CSO |
| **Alternative Energy** | Power optimization algorithms | Turnkey microgrid controller (software + hardware) | DOE SBIR, ARPA-E, USDA REAP, Section 48E ITC |
| **Macro-Systems** | Single-node memory substrate | Distributed network of coordinated nodes (federated intelligence) | DARPA, IARPA, multi-agency contracts |
| **Materials Science** | Standard thermal solutions | Novel cooling materials for edge compute | NSF MRSEC, DOE BES, university partnerships |

### The Pivot Rule
**You can pivot at any tier, but each pivot requires a new grant cycle.** Do not pivot until you have:
1. Won at least one grant in your current focus area
2. Published results (arXiv, benchmark, demo)
3. Built a working prototype
4. Secured funding for the pivot (either IR&D from existing grants or new grant)

**Example**: Don't build a robot in Tier 1. Build the edge node in Tier 1, win a grant for it in Tier 2, then use IR&D budget or a new SBIR topic to add the chassis in Tier 3.

---

## Bounty Hunter Node: Where It Fits

| Tier | Bounty Hunter Role | Value |
|---|---|---|
| **Tier 0** | Not built yet | N/A |
| **Tier 1** | **Build it** (Month 3–4) | Discovers prize competitions and fast-track opportunities |
| **Tier 2** | Operational | Generates 2–5 opportunity briefs/month; submits to Challenge.gov/DIU |
| **Tier 3** | Integrated into BD workflow | Replaces manual solicitation reading; scales application volume 5x |
| **Tier 4+** | Legacy system | Replaced by dedicated BD hire; becomes internal research tool |

---

## Summary: The One-Page Cheat Sheet

| Tier | Time | Revenue | Key Deliverable | Go/No-Go |
|---|---|---|---|---|
| **0** | Days 1–30 | $0–$75K | LLC + 3+ Manifund asks | ≥1 Manifund win |
| **1** | Months 1–6 | $15K–$175K | arXiv preprint + workspace | ≥$50K annualized |
| **2** | Months 6–18 | $50K–$825K | SBIR Phase I + hardware prototype | ≥$200K + Phase I |
| **3** | Years 2–3 | $200K–$2.5M | Phase II + robotic product | ≥$500K + commercial product |
| **4** | Years 3–5 | $1M–$5M/year | Product line + team + facilities | ≥$2M + profitability |
| **5** | Years 5+ | $3M–$10M+/year | 10-year R&D bets | Self-sustaining |

---

*Document maintained by WhiteMagic Labs. Last updated: 2026-04-30.*
*For week-by-week execution, see `GRANT_EXECUTION_PLAN_2026-04-28.md`.*
*For grant opportunity rankings, see `GRANT_TIER_LIST_2026.md`.*
