# Grant Strategy Deep Dive — 2026

**Date**: 2026-04-27
**Scope**: Mathematical likelihood of success, tailored application strategies, prerequisites, and fund-usage implications for every active funding opportunity mapped to WhiteMagic Labs.
**Status**: Living document — update after every submission and decision.

---

## 0. Executive Summary

| Opportunity | Deadline | Ask Range | Estimated Success Rate | Effort Hours | Priority |
|---|---|---|---|---|---|
| Schmidt Sciences — Trustworthy AI RFP | **May 17, 2026** | $300K–$1M (Tier 1) | **12–18%** | 40–60 | 🔴 P0 |
| SFF Rolling Application | Rolling | $50K–$200K | **18–25%** | 15–25 | 🟡 P1 |
| Foresight Institute — AI Nodes | Monthly (last day) | $10K–$100K | **25–35%** | 10–15 | 🟡 P1 |
| Manifund Regrants | Rolling | $5K–$50K | **40–55%** | 4–8 | 🟢 P2 |
| BlueDot Rapid Grants | Rolling | $50–$10K | **50–65%** | 2–4 | 🟢 P2 |
| SFF 2026 Theme Round — HSEE | July 8, 2026 | $50K–$200K | **15–22%** | 20–30 | 🟡 P1 (defer) |
| SFF 2026 Theme Round — Climate | June 10, 2026 | $50K–$200K | **10–15%** | 20–30 | 🔵 P3 |

**Total addressable non-dilutive capital in next 6 months**: $435K–$1.56M
**Combined probability of receiving ≥$100K**: ~65% (assuming we apply to 4+ opportunities)

---

## 1. Methodology: How These Numbers Were Derived

### 1.1 Base-rate reasoning

Success rates for competitive grants are notoriously hard to estimate because:
- **Selection bias**: Funders report aggregate acceptance rates, not rates for first-time applicants or unaffiliated labs.
- **Heterogeneity**: A well-crafted application from a team with verifiable prior art performs very differently from a cold email.
- **Timing**: Rolling deadlines have different dynamics than fixed RFPs.

Our estimates combine:
1. **Publicly stated or leaked acceptance rates** (where available)
2. **Structural fit analysis** — how closely WhiteMagic's documented capabilities map to the funder's stated priorities
3. **Network proximity** — whether we have a warm intro, shared contact, or prior interaction
4. **Competitive density** — how many applicants we expect for this specific opportunity
5. **Risk-adjusted heuristic**: multiply the optimistic estimate by 0.6 and the pessimistic by 1.4, then take the geometric mean.

### 1.2 The WhiteMagic "portfolio effect"

Because these applications are **not mutually independent** (they all reference the same codebase, paper outline, and competitive-landscape analysis), the combined probability of receiving *at least one* grant is higher than naive multiplication would suggest.

Assuming moderate positive correlation (ρ ≈ 0.35) between outcomes:
- P(at least one success | apply to 4) ≈ **65%**
- P(at least one success | apply to 6) ≈ **78%**

This is the single most important strategic insight: **volume of well-targeted applications is itself a strategy.**

---

## 2. Opportunity-by-Opportunity Analysis

---

### 2.1 Schmidt Sciences — Science of Trustworthy AI RFP

**Deadline**: May 17, 2026 (11:59pm AoE)
**Amount**: Tier 1 up to $1M (1–3 years); Tier 2 $1M–$5M+ (1–3 years)
**Contact**: trustworthyai@schmidtsciences.org

#### 2.1.1 Structural Fit Assessment

| Research Agenda Aim | WhiteMagic Mapping | Strength |
|---|---|---|
| **Aim 1: Characterize/forecast misalignment** | Foresight Engine (Logos Layer) predicts memory decay and association-path convergence — a novel *operationalization* of misalignment at the agent-substrate level. | Medium |
| **Aim 2: Generalizable measurements & interventions** | **Karma Ledger** = runtime measurement of declared-vs-actual side-effects. **Dharma Rules Engine** = preventive intervention (LOG→TAG→WARN→THROTTLE→BLOCK). Both are *generalizable* across any MCP tool surface. | **Strong** |
| **Aim 3: Oversight under capability gaps + multi-agent** | **Bicameral Reasoning (Corpus Callosum)** = dual-hemisphere debate for oversight. **Voice Audit** = hallucination detection at the cognitive layer before tool execution. **Multi-agent**: Karma Ledger extends to multi-agent networks via `mcp_lieutenants.py`. | **Strong** |

#### 2.1.2 Estimated Success Rate

- **Tier 1 as solo applicant**: 8–12% (base rate for first-time solo applicants to major science RFPs ≈ 5–10%; our structural fit and prior-art documentation push this up)
- **Tier 1 with a co-PI or institutional affiliation**: 15–22% (Schmidt explicitly prefers multi-PI for Tier 2; even Tier 1 benefits from affiliation signal)
- **Tier 2 as solo**: <3% (Tier 2 is explicitly for multi-lab collaborations; solo applicants are effectively screened out)

**Recommended ask**: **Tier 1, $400K–$800K, 2 years.**

#### 2.1.3 Why the Rate Is What It Is

**Positive factors:**
- WhiteMagic has a **verifiable prior-art trail** (Karma Ledger spec: May 26, 2025; implementation: Feb 7, 2026; Anthropic's structurally similar audit log: Apr 23, 2026). This is the kind of citation-friendly story peer reviewers like.
- The codebase is **real and testable** (2,185 tests, MIT-licensed, public GitHub). Reviewers can clone and run it.
- The framing as "governance + metacognition substrate" is **novel** — not "another memory startup."
- We have a **pre-existing paper outline** (`KARMA_LEDGER_PAPER_OUTLINE.md`) that can be adapted into the proposal's "intellectual merit" section.

**Negative factors:**
- **No academic affiliation.** Schmidt Sciences strongly prefers university, national lab, or non-profit research organization PIs. Solo independent researchers are eligible but at a steep disadvantage.
- **No LoCoMo benchmark number.** The RFP explicitly warns against "proposals suggest tools/benchmarks/evaluations without a credible validity argument." We have tests but no published benchmark.
- **No co-PI.** The language for Tier 2 is explicit: "preference will be given to proposals from collaborations among multiple PIs and labs." Even Tier 1 benefits from a team.
- **Deadline is 3 weeks away.** A competitive Tier 1 application typically takes 6–8 weeks to write and refine.

#### 2.1.4 Tailored Strategy

**Option A: Sprint for Tier 1 solo (highest risk/reward)**
1. **Anchor the proposal on Aim 2 + Aim 3**, not Aim 1. Our weakest fit is forecasting misalignment; our strongest is measurement + oversight.
2. **Lead with the Karma Ledger as a "model organism" for evaluation science.** Frame it as: "We have built a controlled testbed where declared-vs-actual side-effect mismatch can be systematically measured, intervened upon, and audited — a model organism for the science of trustworthy tool use."
3. **Explicitly address the "construct validity" requirement.** Define:
   - Construct: "side-effect fidelity" — the degree to which an agent's runtime behavior matches its statically declared effect manifest.
   - Measurement: Karma debt score (0–1 scalar).
   - Predictive validity: Correlation between karma debt and downstream task failure rates.
   - Robustness: Behavior under adversarial optimization pressure (red-team the Dharma rules).
4. **Include a concrete work plan with milestones:**
   - Month 1–3: Formalize the Karma Ledger evaluation protocol; submit arxiv preprint.
   - Month 4–9: Run controlled experiments on multi-agent misalignment scenarios using the Bicameral Reasoner as oversight.
   - Month 10–18: Develop the "EU AI Act Article 12 evidence-pack generator" as a real-world deployment test.
   - Month 19–24: Publish results + open-source all tooling.
5. **Request budget breakdown:**
   - 50% salary/support for PI (Lucas Bailey) — $200K–$400K
   - 20% compute + API credits — $80K–$160K
   - 15% contractor/consultant (for benchmark runs, paper editing) — $60K–$120K
   - 10% travel/convenings — $40K–$80K
   - 5% overhead (equipment, software) — $20K–$40K

**Option B: Find a co-PI and apply jointly (recommended if feasible)**
- Ideal co-PI profile: Assistant/associate professor in CS/AI safety at a US or UK university, with publications in agent safety, evaluation, or interpretability.
- Value proposition for the co-PI: They get a working codebase (2,185 tests), a paper idea, and a funded research stream without having to build infrastructure from scratch.
- Timeline: Would need to identify, pitch, and align with a co-PI within **7–10 days** to have any chance of a May 17 submission. Extremely tight.

#### 2.1.5 What We Need for Highest Success

| Prerequisite | Status | Action |
|---|---|---|
| Academic or non-profit affiliation | ❌ Missing | **Critical blocker.** Options: (a) incorporate as non-profit, (b) fiscal sponsorship through an existing 501(c)(3), (c) partner with a university PI. |
| LoCoMo benchmark run | ❌ Missing | High-risk to start now; may be better to honestly state "benchmark run is Year 1 Milestone 1" rather than claim a number we don't have. |
| Arxiv preprint | 🟡 Partial | `KARMA_LEDGER_PAPER_OUTLINE.md` exists but is not a formatted paper. Need 2–3 days to convert to LaTeX/arxiv. |
| Letters of support | ❌ Missing | Need 2–3 letters from credible voices. Best candidates: anyone who has reviewed the codebase, used the MCP server, or collaborated on the design. |
| Prior funding history | ❌ None | First-time applicants are at a disadvantage. Mitigate by emphasizing the 8.5-month prior-art trail and the public release history. |

#### 2.1.6 Fund Usage & Restrictions

**What the money can be used for:**
- Salary and benefits for PI and research staff
- Compute (GPUs, cloud credits) — Schmidt offers their own compute resources as an alternative to budgeted compute
- API credits with frontier model providers (Schmidt can provide these directly)
- Travel to convenings, workshops, collaborator sites
- Software engineering support through VISS (Virtual Institute for Scientific Software)
- Equipment, subcontractors, open-access publication fees

**Restrictions:**
- Indirect costs ≤10% (very low by academic standards; most universities charge 50%+)
- Must produce generalizable scientific insight, not just a product
- Tier 2 requires "demonstrably a primary focus" for lead investigator(s)
- Funding is for research, not commercialization

**Implications of receiving $400K–$800K:**
- **2 years of full-time research runway** for Lucas + one part-time contractor
- **Compute budget** to run LoCoMo, PRAT-vs-SAIQL benchmarks, and large-scale multi-agent experiments
- **Credibility signal** that unlocks downstream funding (SFF, Open Phil, Foresight will take a funded project more seriously)
- **Constraint**: Must prioritize research publications over product development. The Karma Ledger audit-pack generator (a product feature) could be spun out as a "deployment test" but the core deliverable must be science.

---

### 2.2 Survival and Flourishing Fund (SFF) — Rolling Application

**Deadline**: Rolling (submissions after Apr 22, 2026 are auto-deferred to next round)
**Amount**: $50K–$200K typical for first-time grantees; up to $500K+ for established orgs
**Process**: Submit Rolling Application → Auto-submits Speculation Grant request → 95%+ get Speculation Grant → S-Process evaluation (6–8 months) → Recommendation

#### 2.2.1 Structural Fit Assessment

| SFF Track | WhiteMagic Mapping | Strength |
|---|---|---|
| **Main Track** | Open-source governance substrate for AI agents; long-term survival/flourishing via trustworthy multi-agent coordination. | Medium |
| **Freedom Track** | Dharma rules engine enforces boundaries; Karma Ledger prevents unaccountable side-effects; MIT license preserves user sovereignty. **Strong fit.** | **Strong** |
| **Fairness Track** | Locally-runnable, vendor-neutral substrate empowers non-Big-Tech actors; prevents monopolistic concentration of agent governance. | Medium |

#### 2.2.2 Estimated Success Rate

- **Rolling Application → Speculation Grant**: **95%+** (historical rate; auto-submitted with rolling app)
- **Speculation Grant → S-Process Recommendation**: **15–25%** for first-time applicants; **30–45%** for orgs with prior SFF funding
- **Overall**: **18–25%** for a well-crafted first application

The SFF process is deliberately designed to be more accessible than traditional RFPs. The S-Process uses independent assessors who evaluate applications over 6–8 months, and the "speculation grant" mechanism means you get a small, fast approval that guarantees eligibility.

#### 2.2.3 Why the Rate Is What It Is

**Positive factors:**
- SFF has a **proven track record of funding AI safety infrastructure** (FAR AI, METR, CAIS, Apollo Research, PIBBSS all received SFF funding).
- The **Freedom Track** is a remarkably good fit: "Protecting meaningful freedom of speech... ensuring the continuation of individual liberties such as privacy, private property, and freedom of association." A locally-runnable, auditable agent substrate is directly on this vector.
- **Default open-source IP policy** (MIT + CC-BY) matches WhiteMagic's existing license. No negotiation needed.
- SFF funds **for-profits** (non-dilutive grants) and **charities**. We can apply as a for-profit LLC.

**Negative factors:**
- **Main Round deadline (Apr 22) has passed.** Rolling applications submitted now are deferred to the next round (likely 2027).
- **S-Process takes 6–8 months.** If we submit now, we wouldn't see funding until early 2027.
- **No warm intro.** The FAQ says "Best approached through a referral" for competitive rounds.
- **Individual researchers need a fiscal sponsor.** We are currently an unincorporated solo operation.

#### 2.2.4 Tailored Strategy

**Action: Submit the Rolling Application immediately, flag for Freedom Track.**

1. **Frame as infrastructure for "sovereign AI."** Use language from `AGENT_FIRST_LAB_STRATEGY.md`: "A lab's output is artifacts; the consultancy is how we eat while we publish them." SFF funds labs that produce public goods.
2. **Emphasize the Freedom Track alignment explicitly.** The application form allows flagging a track. State: "WhiteMagic is designed to prevent concentrations of authority in the agent layer. Every tool call is auditable, every side-effect is declared, and the entire stack runs locally without vendor lock-in."
3. **Include the competitive-landscape analysis.** SFF assessors are sophisticated; showing that we understand the field (Mem0, Cognee, Anthropic Claude Memory) and have identified a narrow lane (governance + metacognition) builds credibility.
4. **Budget ask**: $120K–$180K over 18 months. This is in the sweet spot for first-time SFF grantees.
   - 60% salary ($72K–$108K)
   - 20% compute + infrastructure ($24K–$36K)
   - 10% contractor (paper writing, benchmark design) ($12K–$18K)
   - 10% travel + convenings ($12K–$18K)

#### 2.2.5 What We Need for Highest Success

| Prerequisite | Status | Action |
|---|---|---|
| Fiscal sponsor (if applying as individual) or incorporation | ❌ Missing | **Critical.** Easiest path: incorporate as a single-member LLC (Delaware or Wyoming, ~$200 + $50/year). SFF accepts for-profits. |
| Rolling application submitted | ❌ Missing | Can be done in 1 day once prerequisites are met. |
| Public signal / reference | 🟡 Partial | GitHub repo + PyPI package history + 2,185 tests. Need to ensure these are prominently linked. |

#### 2.2.6 Fund Usage & Restrictions

**What the money can be used for:**
- Almost anything related to the project's mission. SFF is famously flexible.
- Salary, rent, compute, contractors, travel, equipment, software
- For for-profits: non-dilutive grant (no equity taken)

**Restrictions:**
- Default IP release: MIT + CC-BY (already matches us)
- Must be a for-profit (US/UK/Canada/Australia) or charity (any non-adversarial country)
- No funding to individuals without fiscal sponsor
- SFF does not fund "basic income" — the grant must be for project execution

**Implications of receiving $120K–$180K:**
- **18 months of lean runway** ($6.5K–$10K/month effective burn)
- **No equity dilution** — we retain 100% ownership
- **Credibility signal** for downstream funders (Schmidt, Open Phil, Foresight)
- **Constraint**: S-Process funding is disbursed after recommendation announcement (Sept 2026 for Main Round, Nov 2026 for Theme Rounds). If we submit now for next round, funding arrives ~Q1 2027.

---

### 2.3 Foresight Institute — AI for Science & Safety Nodes

**Deadline**: Last day of every month (next: April 30, 2026)
**Amount**: $10K–$100K typical; up to $300K for exceptional AI safety projects
**Focus Areas**: AI for Security, Private AI, Decentralized & Cooperative AI, AI for Science & Epistemics
**Node Locations**: San Francisco, Berlin

#### 2.3.1 Structural Fit Assessment

| Focus Area | WhiteMagic Mapping | Strength |
|---|---|---|
| **AI for Security** | Dharma rules engine + Karma Ledger = self-improving defense against unaccountable agent behavior. Runtime audit is a security primitive. | **Strong** |
| **Private AI** | WhiteMagic is locally-runnable, vendor-neutral, with no cloud dependency. Fits "local, private compute stack." | **Strong** |
| **Decentralized & Cooperative AI** | Multi-agent Karma Ledger, Bicameral oversight, and the 28-Gana cultural mapping are explicitly designed for cooperative multi-agent ecosystems. | **Strong** |
| **AI for Science & Epistemics** | Foresight Engine (predictive metacognition) and Voice Audit (hallucination detection) improve epistemic preparedness. | Medium |

#### 2.3.2 Estimated Success Rate

- **Overall**: **25–35%** for a well-matched project
- **AI safety focus areas get larger grants** and are prioritized
- **"Funding-only" applications are accepted only in exceptional cases** — we need to express interest in being an active node member

Foresight is smaller and more niche than Schmidt or SFF. They receive fewer applications per slot, but they are highly selective on fit. A project that clearly maps to one of their focus areas and is willing to engage with the node community has a good shot.

#### 2.3.3 Why the Rate Is What It Is

**Positive factors:**
- Three of our four strongest differentiators (Dharma/Karma, Bicameral, local-first) map directly to Foresight focus areas.
- Foresight has funded **MATS, PIBBSS, FAR AI, Apart Research** — they understand the AI safety research ecosystem.
- Monthly deadline means **we can iterate** based on feedback.
- They prefer **open source** (our default).

**Negative factors:**
- **Physical presence expected.** "Grantees are invited to build together in Berlin or San Francisco." We are not currently in either city.
- **Review time is ~2 months** after each deadline. First payment may not arrive until July 2026.
- **Smaller grant sizes** than Schmidt or SFF. $10K–$100K is meaningful but not transformative.

#### 2.3.4 Tailored Strategy

**Action: Apply by April 30 for the Decentralized & Cooperative AI focus area.**

1. **Lead with the multi-agent governance story.** The Foresight agenda explicitly asks: "How can we ensure a verifiable chain from agent actions back to an authenticated human or organizational principal?" The Karma Ledger is literally this.
2. **Propose a concrete node engagement plan.** Even if we can't relocate full-time, propose:
   - Quarterly visits to the SF node for workshops/sprints
   - Remote participation in node events
   - Hosting a workshop on "Agent Governance Primitives" at a Foresight convening
3. **Budget ask**: $75K–$125K for 12 months.
   - 50% salary ($37.5K–$62.5K)
   - 25% compute + infrastructure ($18.75K–$31.25K)
   - 15% travel to node ($11.25K–$18.75K)
   - 10% contractor/paper ($7.5K–$12.5K)

#### 2.3.5 What We Need for Highest Success

| Prerequisite | Status | Action |
|---|---|---|
| Willingness to engage with SF/Berlin node | 🟡 Partial | We need to state a credible engagement plan. Remote participation is acceptable if framed as "distributed contributor." |
| Airtable application form | ❌ Missing | Straightforward; takes 2–3 hours to complete thoughtfully. |
| Project plan + milestones | 🟡 Partial | Can adapt from Schmidt Sciences proposal. |

#### 2.3.6 Fund Usage & Restrictions

**What the money can be used for:**
- Project execution, salary, compute, travel, events, contractors
- Node access is free (office space, community, meals)
- Compute budget can be requested separately

**Restrictions:**
- Must be an active member of the node community (strongly preferred)
- Overhead ≤10% of direct research costs
- Grantees must pass due diligence (itemized budget, project plan, org documents)
- Basic reporting requirements (progress updates at intervals)

**Implications of receiving $75K–$125K:**
- **12 months of focused runway** on governance substrate work
- **Network access** to Foresight's ecosystem (workshops, other grantees, potential collaborators)
- **Credibility signal** — Foresight-funded projects are respected in the AI safety longtermist community
- **Constraint**: Must prioritize node engagement. If we can't travel to SF/Berlin quarterly, this may not be the right fit.

---

### 2.4 Manifund Regrants

**Deadline**: Rolling
**Amount**: $5K–$50K typical; some regrantors go higher
**Regrantors**: Neel Nanda (interpretability), Joel Becker (AI safety), Gavin Leech (forecasting), and others
**Decision time**: 2–4 weeks

#### 2.4.1 Structural Fit Assessment

Manifund is a prediction-market-shaped grant platform. Regrantors have personal budgets and make individual decisions. The best fit is with **Neel Nanda** (mechanistic interpretability) and **Joel Becker** (AI safety infrastructure).

| Regrantor | Fit | Strength |
|---|---|---|
| **Neel Nanda** | Karma Ledger + Voice Audit as mechanistic tools for understanding what agents actually do (not just what they say). | Medium |
| **Joel Becker** | Governance infrastructure, evaluation tooling, open-source safety work. | **Strong** |
| **Gavin Leech** | Foresight Engine as predictive infrastructure; epistemic tooling. | Medium |

#### 2.4.2 Estimated Success Rate

- **Well-targeted $20K–$40K ask**: **40–55%**
- **Vague or overly large ask**: <10%

Manifund is fast and personal. A regrantor who understands the project and believes in the applicant can approve quickly. The key is **specificity** — not "fund WhiteMagic" but "fund the LoCoMo benchmark run for WhiteMagic's memory substrate" or "fund the arxiv preprint on Corpus Callosum + Voice Audit."

#### 2.4.3 Tailored Strategy

**Action: Submit 2–3 scoped, small asks to different regrantors simultaneously.**

1. **Ask Joel Becker**: $25K for "Governance primitives for multi-agent systems: implementing and benchmarking the Karma Ledger on 100+ tool interactions."
2. **Ask Neel Nanda**: $15K for "Mechanistic interpretability for agent runtimes: using the Voice Audit subsystem to detect hallucination patterns in tool-selection chains."
3. **Ask Gavin Leech**: $10K for "Predictive metacognition for agent safety: validating the Foresight Engine's drift predictions against empirical memory decay curves."

Each ask should be:
- **Specific** (one subsystem, one outcome)
- **Time-bounded** (3–6 months)
- **Measurable** (benchmark number, paper submission, code release)
- **Low-risk** (we already have the code; we're asking for runway to validate it)

#### 2.4.4 What We Need for Highest Success

| Prerequisite | Status | Action |
|---|---|---|
| Manifund account | ❌ Missing | Sign up at manifund.org (free, 5 minutes) |
| Scoped project descriptions | 🟡 Partial | Need to tailor 2–3 specific asks from existing codebase. Can be done in 1 day. |
| Regrantor relationship | ❌ None | Cold outreach is acceptable on Manifund; the platform is designed for it. |

#### 2.4.5 Fund Usage & Restrictions

**What the money can be used for:**
- Extremely flexible. Regrantors trust the grantee to spend wisely.
- Salary, compute, contractors, equipment, travel

**Restrictions:**
- None significant. Manifund does not impose IP requirements (though we should still open-source).
- Grant is typically a one-time transfer.

**Implications of receiving $25K–$50K:**
- **3–6 months of focused runway** on a specific validation task
- **Fast feedback loop** — if we deliver, regrantors will fund follow-on work
- **No strings attached** — the most flexible funding source on this list
- **Constraint**: Small amounts mean we need to be efficient. Can't hire full-time help.

---

### 2.5 BlueDot Rapid Grants

**Deadline**: Rolling
**Amount**: $50–$10K
**Decision time**: ~5 working days
**Eligibility**: BlueDot course participants, alumni, facilitators, active community members

#### 2.5.1 Structural Fit Assessment

BlueDot Rapid Grants are designed for "impactful work where money is the bottleneck." They fund compute, events, research access, travel, community chapters, and project tooling.

If Lucas is a BlueDot alumnus or has taken a BlueDot course, this is a **fast, low-effort** source of $1K–$5K for:
- API credits for benchmark runs
- Travel to an AI safety conference
- Compute for LoCoMo evaluation
- Hosting a WhiteMagic community meetup

#### 2.5.2 Estimated Success Rate

- **BlueDot community member, specific ask**: **50–65%**
- **Non-member**: 0% (eligibility barrier)

#### 2.5.3 Tailored Strategy

**Action: If eligible, submit a $2K–$5K ask for "Compute and API credits for open-source agent governance benchmarking."**

1. **Specific ask**: "$3,000 for compute credits to run the LoCoMo long-context memory benchmark on WhiteMagic's tiered memory system, with results published open-source."
2. **Timeline**: 2 months
3. **Deliverable**: Benchmark report + code release

#### 2.5.4 What We Need for Highest Success

| Prerequisite | Status | Action |
|---|---|---|
| BlueDot community membership | ❓ Unknown | Check if Lucas has taken a BlueDot course or is active in the community. |
| Specific budget | 🟡 Partial | Need itemized list (e.g., $1,500 AWS credits + $1,000 OpenAI API credits + $500 compute). |

#### 2.5.5 Fund Usage & Restrictions

- Extremely flexible. Upfront payment by default.
- Requires a short impact update upon completion.

**Implications of receiving $2K–$5K:**
- **Removes compute/API bottlenecks** for benchmark runs
- **Fastest turnaround** of any source on this list
- **Community access** — grantees get intros and follow-on opportunities

---

### 2.6 SFF 2026 Theme Rounds

#### 2.6.1 HSEE (Human Self-Enhancement & Empowerment) — July 8, 2026

**Fit**: Moderate. WhiteMagic is a cognitive enhancement tool for agents, not humans. However, the framing "human self-enhancement via better cognitive tooling" could work if we position the Karma Ledger + Bicameral Reasoner as "cognitive prosthetics for human-AI collaboration."

**Estimated Success Rate**: 15–22% (new theme, unclear competitive density)

**Strategy**: Defer until after we have Schmidt/Foresight/Manifund outcomes. If we have momentum, submit a $100K–$150K ask framing WhiteMagic as "cognitive infrastructure for human-AI co-intelligence."

#### 2.6.2 Climate Change — June 10, 2026

**Fit**: Weak-to-moderate. Unless we can articulate a clear "AI for climate" angle (e.g., using the Foresight Engine for climate modeling, or multi-agent coordination for carbon markets), this is not our lane.

**Estimated Success Rate**: 10–15%

**Strategy**: Skip unless a specific climate-AI use case emerges.

---

## 3. Cross-Cutting Strategy: The "Layer Cake" Approach

Rather than treating each application as independent, we should structure them as a **layered funding stack**:

### Layer 1: Fast validation money (Month 0–2)
- **Manifund** ($25K–$50K) + **BlueDot** ($2K–$5K)
- Purpose: Run LoCoMo benchmark, publish arxiv preprint, fix critical gaps
- Timeline: Submit within 1 week; receive funds within 2–4 weeks

### Layer 2: Medium-term runway (Month 2–8)
- **Foresight AI Nodes** ($75K–$125K)
- Purpose: 12 months of focused governance-substrate development
- Timeline: Submit by Apr 30 or May 31; receive funds by July–Aug 2026

### Layer 3: Transformative research funding (Month 6–24)
- **Schmidt Sciences Tier 1** ($400K–$800K) OR **SFF Main Round** ($120K–$180K)
- Purpose: Multi-year research program, multiple publications, team expansion
- Timeline: Schmidt by May 17 (urgent); SFF rolling (deferred to next round)

### Why this layering works
1. **Layer 1 validates the approach.** A LoCoMo number + arxiv preprint makes Layers 2 and 3 significantly stronger.
2. **Layer 2 provides credibility.** Foresight funding is a signal that a respected institution vetted the project.
3. **Layer 3 scales the impact.** Schmidt or SFF money turns a solo project into a sustained research program.

---

## 4. What Receiving One or More Grants Enables

### 4.1 If we receive $25K–$50K (Manifund + BlueDot)

**What we can do:**
- Run the LoCoMo benchmark on WhiteMagic's memory system
- Convert `KARMA_LEDGER_PAPER_OUTLINE.md` into a formatted arxiv preprint
- Fix the remaining test failures in the contract/router layer
- Hire a part-time contractor for 2–3 months (paper editing, benchmark design)

**What we cannot do:**
- Hire full-time help
- Relocate to SF/Berlin for node engagement
- Run large-scale multi-agent experiments

### 4.2 If we receive $100K–$150K (+ Foresight)

**What we can do:**
- 12 months of lean full-time runway for Lucas
- Quarterly travel to SF or Berlin for node workshops
- Hire a part-time research assistant or contractor for 6 months
- Run PRAT-vs-SAIQL compression benchmark
- Submit to ICML/NeurIPS Workshop

**What we cannot do:**
- Build a multi-person team
- Fund major compute clusters
- Scale to enterprise consulting

### 4.3 If we receive $400K–$800K (+ Schmidt Tier 1)

**What we can do:**
- 24 months of full-time research
- Hire one full-time research engineer or PhD student
- Run large-scale controlled experiments on multi-agent misalignment
- Develop the EU AI Act audit-pack generator as a real-world deployment
- Publish 2–3 peer-reviewed papers
- Present at major conferences (NeurIPS, ICML, FAccT)
- Build a genuine academic collaboration network

**What we cannot do:**
- Commercialize aggressively (grant is for research, not product)
- Take on VC funding without disclosure
- Divert funds to unrelated projects

### 4.4 If we receive $500K+ (combinatorial scenario)

If we secure Schmidt + Foresight + Manifund simultaneously (low probability but possible):
- **Total**: $500K–$975K over 2 years
- **Enables**: A 2-person research team (Lucas + 1 FTE), 2 years of compute, 3+ papers, active node engagement, and a credible consulting practice on the side
- **Constraint**: Must carefully segregate fund usage (Schmidt for research, Foresight for node engagement, Manifund for specific validation tasks)

---

## 5. Risk Analysis: What Could Go Wrong

| Risk | Probability | Mitigation |
|---|---|---|
| **Schmidt deadline passes without submission** | 40% | Solo applications are at a steep disadvantage. Mitigate by preparing the strongest possible solo application and accepting that Tier 1 solo is a stretch. |
| **No academic affiliation blocks all major grants** | 60% | Most large funders prefer affiliated PIs. Mitigate by (a) incorporating as LLC for SFF/Manifund, (b) finding a co-PI or fiscal sponsor, (c) leading with Foresight + Manifund which are more flexible. |
| **LoCoMo benchmark performs poorly** | 30% | If WhiteMagic scores below Mem0/Cognee, it damages credibility. Mitigate by honestly framing the benchmark as "Year 1 Milestone" rather than a current claim. |
| **SFF deferred to 2027** | 90% | Main Round is closed; rolling apps are deferred. Accept this and use the time to strengthen the application. |
| **Foresight requires relocation** | 50% | They strongly prefer active node members. Mitigate by proposing a "distributed contributor" model with quarterly visits. |
| **Grant funds create tax/compliance burden** | 25% | Receiving $100K+ as an individual creates tax liability. Mitigate by incorporating before receiving large grants. |

---

## 6. Action Plan: Next 7 Days

| Day | Action | Owner | Deliverable |
|---|---|---|---|
| **Day 1 (Apr 28)** | Incorporate WhiteMagic Labs LLC (Delaware or Wyoming) | Lucas | Certificate of Formation, EIN |
| **Day 1 (Apr 28)** | Open business bank account | Lucas | Account ready for grant deposits |
| **Day 2 (Apr 29)** | Submit Manifund applications (2–3 scoped asks) | Lucas | 3 live Manifund project pages |
| **Day 2 (Apr 29)** | Submit BlueDot Rapid Grant (if eligible) | Lucas | Airtable form submitted |
| **Day 3 (Apr 30)** | Submit Foresight AI Nodes application | Lucas | Airtable form submitted |
| **Day 3–5 (Apr 30–May 2)** | Draft Schmidt Sciences proposal | Lucas | Full proposal draft (6,000 words) |
| **Day 5 (May 2)** | Identify 2–3 letter-of-support writers | Lucas | Email requests sent |
| **Day 6–7 (May 3–4)** | Polish + submit Schmidt application | Lucas | Submitted via SurveyMonkey Apply |
| **Day 7 (May 4)** | Submit SFF Rolling Application | Lucas | Google Form submitted |

**Total effort**: ~60 hours over 7 days. This is aggressive but feasible if prioritized.

---

## 7. Appendix: Fund-Specific Application Mechanics

### 7.1 Schmidt Sciences — Application Portal

- **Portal**: SurveyMonkey Apply (`schmidtsciences.smapply.io`)
- **Requires**: Registration, then multi-section form
- **Sections**: Contact info, project summary, research agenda fit, budget, team, references, supporting documents
- **File uploads**: PDF proposal (max 10 pages), budget spreadsheet, CV, letters of support
- **Tips**: The FAQ explicitly warns against "vague methods" and "tools without validity arguments." Be concrete. Use the word "experiment" frequently.

### 7.2 SFF — Rolling Application

- **Portal**: Google Form (`survivalandflourishing.fund/rolling-application`)
- **Requires**: Google account, basic org info, budget, project description
- **Preview**: Available at [this preview doc](https://docs.google.com/document/d/1oxlVMBkI4sQ9Ln1G5Ig8NBxpD6b282RBAUukAmXzPAs/edit?tab=t.0)
- **Tips**: The form is shorter than Schmidt's but requires clarity on "what would happen if this project succeeds." Use the AGENT_FIRST_LAB_STRATEGY.md thesis language.

### 7.3 Foresight AI Nodes

- **Portal**: Airtable form (`airtable.com/appyVXc5SMPAvIKpP`)
- **Requires**: Project description, budget, team, node engagement plan
- **Tips**: Emphasize community participation. They are funding a network, not just individual projects.

### 7.4 Manifund

- **Portal**: manifund.org (create project page)
- **Requires**: Project description, budget, timeline, regrantor selection
- **Tips**: Write for a specific regrantor, not "the platform." Reference their past grants. Keep asks small and scoped.

---

---

## Appendix: User Decisions & Updated Strategy (2026-04-28)

### A1. The Perfectionism Tax

**User stance**: "If it's less than 100%, I don't want to send it out."

**Reality check**: Grant funding is a rejection-tolerant game. The optimal strategy is not "one perfect application" but **five good applications where each is 80% as good as your best possible version.** The portfolio math wins. Submitting a solid 80% Schmidt application + three 90% Manifund/Foresight/LTFF applications yields higher expected value than one perfect application and nothing else.

That said — **you control your energy.** If Schmidt feels like a drag, skip it. The other applications are higher probability and lower stress. The proposal-writing exercise itself strengthens every future pitch even if the specific application is rejected.

### A2. Parallel Applications & Fund Conflicts

**Can you apply to multiple grants simultaneously?**

- **Non-dilutive grants from different funders do not conflict contractually.**
- **Time is the real constraint**, not contractual exclusivity. You cannot charge the same salary hour to two grants, but funders expect overlapping support.
- **IP / scope overlap is fine** if both result in open-source MIT code. If one demands exclusive commercial rights, that's different — but none of these do.
- **The only real conflict is your attention.** Sequence by deadline, not by exclusivity.

**Tracking requirement**: If you receive multiple grants, you need **sophisticated time-and-expense tracking** (e.g., Harvest, Toggl, or a simple spreadsheet) to allocate hours and costs cleanly per grant. Some funders (Schmidt, SFF) require periodic reports; others (Manifund, BlueDot) are more flexible. Clean accounting from Day 1 prevents audit headaches later.

**Bank accounts**: One business checking account is sufficient for all grant deposits if the institution allows. However, some funders prefer or require separate accounts. For the scale we're targeting ($5K–$200K), a single business account with clear sub-ledgers (via accounting software like Wave or QuickBooks) is simpler and legally sufficient.

### A3. SFF LLC Visibility

**Can SFF see how long your LLC has been active?**

- **Yes** — Georgia LLC formation date is public record via the Secretary of State eCorp portal.
- **Timeline math**: File LLC today → approve ~7 business days → SFF Rolling application submitted → S-Process evaluation 6–8 months → decision Q1 2027. By decision time, your LLC is 8+ months old. This is perfectly credible.
- **Team size**: You disclose team size on the application. There is no public registry. "Solo founder with AI collaborators" is a valid SFF story — they fund individuals and small teams.
- **No red flag** in having a recently formed LLC if the project and prior art are substantive.

### A4. Ranked Actions by ROI

| Rank | Action | Effort | Impact | Timeline |
|------|--------|--------|--------|----------|
| 1 | **Convert `KARMA_LEDGER_PAPER_OUTLINE.md` → arXiv preprint** | 8–12 hrs | **Massive** — strengthens every application | 2–3 days |
| 2 | **Run LoCoMo benchmark** | 4–8 hrs | **High** — removes Schmidt blocker, signals technical depth | 1–2 days |
| 3 | **File LLC ($100)** | 1–2 hrs active | **High** — unlocks SFF, improves posture everywhere | 7–10 days wait |
| 4 | **Submit 3 Manifund asks** | 6–10 hrs | **High** — fastest money, credibility signal | 1–2 days |
| 5 | **Submit Foresight (May 31)** | 6–8 hrs | **Medium-High** — good fit, 2-month review | By May 31 |
| 6 | **Submit LTFF** | 4–6 hrs | **Medium** — low pressure, rolling | Anytime |
| 7 | **Submit SFF Rolling** | 12–16 hrs | **High** — largest single source | After LLC formed |
| 8 | **Submit SFF HSEE (July 8)** | 15–20 hrs | **Medium** — comfortable deadline | By July 8 |
| 9 | **Engage Foresight node community** | Ongoing | **Medium** — warm intros beat cold apps | Start now |
| 10 | **Set up GitHub Sponsors** | 2 hrs | **Low** — small income, community signal | 1 day |

The **arXiv preprint is the single highest-ROI action.** It converts your outline into a citable artifact every grantor can reference. Cost: $0. Time: 8–12 hours. Do this first.

---

*Document maintained by WhiteMagic Labs. Last updated: 2026-04-28.*
