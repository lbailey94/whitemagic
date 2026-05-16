# From A- to A+ — The WhiteMagic Labs Grant Upgrade Guide

> **Date**: 2026-04-30
> **Purpose**: Define what separates a competitive application (A-) from a winning application (A+), and provide a concrete 14-day action plan to close the gap.

---

## The A- vs. A+ Gap

An **A- application** checks every box:
- Clear ask, reasonable budget, specific timeline
- Funder-aligned framing
- Quantified reasoning
- Professional presentation

An **A+ application** makes the reviewer **want to fund you**:
- It creates **FOMO** — "If I don't fund this, someone else will"
- It signals **prestige by association** — "This person is already part of our community"
- It demonstrates **irreversible momentum** — "The train is already moving; my grant determines how fast"
- It triggers **personal conviction** — "I believe this specific person can do this"

---

## The 7 Dimensions of A+

### 1. Warm Intros (Highest ROI)

**What it is**: Someone the funder already trusts says "You should look at this."

**Why it matters**: Grant reviewers are human. A trusted signal reduces perceived risk by 50%+.

**Current state**: Zero warm intros.

**A+ state**: 2–3 warm intros across our 6 target funders.

**Concrete actions**:

| Funder | Potential Intro Path | Action |
|--------|---------------------|--------|
| **Manifund** | Austin Chen (CEO) or regrantor Discord | Join Manifund Discord, engage for 2 weeks, ask thoughtful questions, then DM regrantor with specific ask |
| **LTFF** | Linch Zhang or Oliver Habryka | Attend one LTFF-funded event or virtual talk; follow up with specific project connection |
| **Foresight** | Allison Duettmann or Christine Peterson | Attend Vision Weekend or virtual workshop; introduce yourself as potential grantee |
| **SFF** | Any Speculator (public emails listed) | Email Eliezer Yudkowsky, Nate Soares, or Zvi Mowshowitz with 3-sentence project summary + ask for 15-min call |
| **Schmidt** | Percy Liang or Yonadav Shavit | Cold email with specific reference to their published work + your project connection. Mention you're building "the benchmark layer their evaluation science needs." |
| **NSF SBIR** | Program Director in your topic area | Attend NSF SBIR webinar; follow up with specific technical question that shows you understand their portfolio |

**Time**: 2–3 hours per funder. Spread over 2 weeks.

**Template cold email** (for SFF Speculators / Schmidt advisors):

> Subject: 3-min read: open-source audit primitive for multi-agent tool use
>
> Hi [Name],
>
> I'm Lucas Bailey, a self-taught engineer who spent the last 12 months building WhiteMagic — an open-source cognitive OS for AI agents (479 tools, 2,216 tests, MIT-licensed).
>
> I noticed [specific thing they wrote/said about evaluation science / multi-agent risk / local-first infrastructure]. I'm working on something directly related: Karma Ledger, a runtime audit substrate that verifies declared-vs-actual side effects in tool-using agents.
>
> No ask right now — just wondering if you'd be open to a 15-min call in the next 2 weeks? I'd value your perspective on whether this direction is worth pursuing, and if there's anyone else I should talk to.
>
> Best,
> Lucas
> https://whitemagic.dev

**Why this works**: Low pressure, specific reference to their work, asks for advice not money, includes social proof (site link).

---

### 2. Social Proof — Letters of Intent & Advisor Quotes

**What it is**: Written statements from credible people saying "This is real / important / worth funding."

**Why it matters**: Third-party validation is 10× more credible than self-description.

**Current state**: None.

**A+ state**: 3–5 letters of intent or advisor quotes.

**Concrete actions**:

1. **Identify 5 potential advisors** (people who might say yes to a 15-min call):
   - Safety lab PIs (METR, Apollo, CAIS, Anthropic alignment team)
   - Open-source maintainers (LangChain, AutoGPT, MCP)
   - Academic researchers in AI evaluation (search Google Scholar for "AI agent evaluation" recent papers)
   - Industry practitioners building agent infrastructure

2. **The ask**: Not "Will you be my advisor?" but:
   > "I'm applying for [Funder] to build [specific thing]. Would you be willing to write a 2-sentence statement of support? Something like 'I believe standardized audit primitives for agent tool use are urgently needed. Lucas's approach of measuring declared-vs-actual fidelity is the right starting point.'"

3. **Where to use them**:
   - Schmidt: Full letters of support (2–3 required)
   - SFF: Quotes in application
   - Foresight: Bio/work URLs section
   - Manifund: Extra docs
   - LTFF: "Why you" section
   - NSF: Letters of support or collaboration letters

**Time**: 1 hour to identify people; 2–3 hours for calls/emails; 1 week for responses.

---

### 3. Visuals — Demo Video & Architecture Diagrams

**What it is**: 2-minute video showing the system working + clean diagrams of architecture.

**Why it matters**: Funders review 50+ applications. A video makes you memorable. A diagram makes your system comprehensible in 10 seconds.

**Current state**: None.

**A+ state**: 1 demo video + 3 architecture diagrams.

**Concrete actions**:

**Demo video (2 minutes)**:
- 0:00–0:15: "This is an agent using tools. Here's what it declares it will do."
- 0:15–0:45: "Here's what it actually does. Notice the mismatch."
- 0:45–1:15: "Karma Ledger catches this in real time. Here's the audit log."
- 1:15–1:45: "This works across any MCP-compatible tool. Here's the code."
- 1:45–2:00: "MIT-licensed. Open source. We need $X to benchmark this on 100+ tasks."

**Tools**: OBS (free) for screen recording + your voice. No fancy editing needed.

**Architecture diagrams**:
1. **System overview**: WhiteMagic stack (memory → governance → dispatch → tools)
2. **Karma Ledger flow**: Tool call → declaration → execution → diff → score
3. **PRAT compression**: 451 tools → 28 Ganas (before/after visual)

**Tools**: Excalidraw (free), Figma, or even hand-drawn + photo.

**Where to host**: YouTube (unlisted) for video; GitHub repo for diagrams.

**Time**: 4–6 hours total (1 hr script, 2 hrs recording, 1 hr editing, 2 hrs diagrams).

---

### 4. Traction Metrics — Make the Numbers Move

**What it is**: Evidence that people are already using or caring about your work.

**Why it matters**: Traction is the ultimate risk reducer. It proves the world wants this.

**Current state**: 2,216 tests, 479 tools, 0 external users (likely).

**A+ state**: GitHub stars trending, first external contributor, first user interview, first citation.

**Concrete actions**:

| Metric | Current | Target (2 weeks) | Action |
|--------|---------|------------------|--------|
| GitHub stars | [Check] | +20–50 | Post on HN, Twitter/X, relevant subreddits with specific technical angle |
| Forks | [Check] | +5–10 | Same as above; target AI safety researchers |
| Issues/PRs | [Check] | 2–3 external | Create "good first issue" labels; tweet about them |
| Blog post views | 0 | 1,000+ | Write "How I built a runtime audit substrate for AI agents" on personal blog or Medium |
| Twitter/X followers | [Check] | +100 | Thread about Karma Ledger architecture; engage with AI safety community |
| First design partner | 0 | 1 conversation | Email 5 safety labs: "I'm building X. Can I get 15 min of your time to validate the direction?" |

**The HN post template** (highest ROI for developer attention):

> **Show HN: Karma Ledger — runtime audit for AI agent tool use**
>
> I've spent 12 months building WhiteMagic, an open-source cognitive OS for AI agents. One component — Karma Ledger — verifies that an agent's declared tool effects match its actual effects.
>
> Problem: Agents increasingly use tools (MCP, browser automation, file systems). But current benchmarks test task success, not whether the agent's description of what it did matches reality. If an agent says "I read file X" but actually wrote to file Y, oversight fails.
>
> Karma Ledger scores "declaration fidelity" for every tool call. It works across any MCP-compatible surface. Core code is MIT-licensed.
>
> Would love feedback from anyone building or evaluating agent systems.
>
> [Link to repo] [Link to 2-min demo video]

**Why this works**: HN loves open-source + specific technical problem + Show HN format. Target: front page for 6 hours = 10K+ views, 50+ stars, 5+ meaningful comments.

**Time**: 2 hours to write post + 1 hour to engage with comments.

---

### 5. Prestige Signals — arXiv + Conference + Podcast

**What it is**: Third-party validation that your work is worth taking seriously.

**Why it matters**: Academics and funders use proxies for quality. arXiv > blog post. Conference talk > video. Podcast mention > tweet.

**Current state**: Karma Ledger outline exists; no preprint, no talks, no podcasts.

**A+ state**: arXiv preprint live + 1 conference submission + 1 podcast appearance scheduled.

**Concrete actions**:

1. **arXiv preprint** (highest priority):
   - Convert `KARMA_LEDGER_PAPER_OUTLINE.md` to LaTeX
   - Submit to arXiv cs.AI or cs.SE
   - Time: 2–3 days of focused work
   - This single action upgrades every application from B+ to A-

2. **Conference submission**:
   - NeurIPS 2026 workshops (deadline ~Sep 2026)
   - ICML 2026 workshops (deadline ~Apr/May 2026 — check!)
   - AI Safety conferences: AISIC, AI Village @ DEF CON, FAccT
   - Target: workshop track (less competitive than main conference)
   - Time: 1 day to check deadlines + 2 days to write abstract

3. **Podcast appearance**:
   - Target: The Inside View, The Lunar Society, Bankless, or smaller AI safety podcasts
   - Pitch: "I built an open-source audit substrate for agents before Anthropic shipped theirs. Here's what I learned."
   - Time: 1 hour to identify podcasts + 1 hour to send pitches

**Time**: 3–5 days for arXiv; 1 day for conference check; 2 hours for podcast outreach.

---

### 6. Ecosystem Participation — Be a Citizen, Not a Tourist

**What it is**: Evidence that you're part of the community, not just extracting value from it.

**Why it matters**: Funders fund people they know and trust. Trust comes from repeated interaction.

**Current state**: Unknown — likely low.

**A+ state**: Active participant in 2–3 relevant communities.

**Concrete actions**:

| Community | Action | Time |
|-----------|--------|------|
| **Manifund Discord** | Join, introduce yourself, review 3 proposals, provide feedback, ask questions | 2 hrs/week |
| **EA Forum / LessWrong** | Write one short post: "What I learned building a runtime audit substrate for agents" | 4 hrs |
| **Foresight Node calls** | Attend one Secure AI Node virtual call; ask one thoughtful question | 1.5 hrs |
| **AI Safety Twitter/X** | Thread about Karma Ledger; reply thoughtfully to 5 safety researchers' posts per week | 1 hr/week |
| **Open-source MCP community** | Open one PR to an MCP server; review one PR | 3 hrs |
| **Local EA / rationalist meetup** | Attend one meetup in your city; mention your project | 3 hrs |

**The EA Forum post template**:

> **What I learned building a runtime audit substrate for AI agents**
>
> TL;DR: I spent 12 months building an open-source tool that verifies declared-vs-actual side effects in agent tool use. Here are 3 surprising things I learned about agent safety that I didn't expect.
>
> 1. **Declaration fidelity is harder than it looks**: Even simple file-read operations have hidden side effects (cache updates, access-time changes, lock acquisitions). Agents that declare "read-only" often aren't.
>
> 2. **Benchmarks test the wrong thing**: LoCoMo tests coordination. LongMemEval-S tests memory. Neither tests whether the agent's description of its actions matches reality. This gap is widening as MCP adoption accelerates.
>
> 3. **Open-source audit is a public good**: Every lab I've talked to wants this, but no one wants to build it because it's infrastructure, not a product. This is exactly the kind of thing LTFF/Manifund exists to fund.
>
> The code is MIT-licensed: [link]. I'd welcome feedback from anyone working on agent evaluation.

**Why this works**: Specific lessons, not self-promotion. Community-oriented framing. Direct connection to funders' mission.

---

### 7. Polish — Design, Typography, Zero Typos

**What it is**: Professional presentation that signals "I care about details."

**Why it matters**: Sloppy applications signal sloppy execution. Reviewers subconsciously downgrade.

**Current state**: Markdown docs, likely inconsistent formatting.

**A+ state**: Professionally formatted PDFs with consistent branding.

**Concrete actions**:

1. **Create a template**:
   - Use Google Docs or LaTeX for all applications
   - Consistent header: WhiteMagic Labs logo + tagline + date
   - Consistent typography: 11pt body, 14pt headings, serif for body, sans for headers
   - Page numbers, table of contents for long applications

2. **Proofread ritual**:
   - Read aloud every sentence
   - Check all links (use `lychee` or manual click-through)
   - Verify all numbers match current state
   - Have Grammarly or a friend review

3. **Visual branding**:
   - Use WhiteMagic color scheme (lavender, ink, surface) in diagrams
   - Consistent logo placement
   - Professional headshot (if you have one)

**Time**: 2 hours to create template; 30 min per application to format.

---

## The 14-Day A+ Sprint Plan

### Days 1–3: Foundation
- [ ] **Day 1**: Record demo video (2 min); write script, record, upload unlisted to YouTube
- [ ] **Day 2**: Create 3 architecture diagrams (Excalidraw); export as PNG
- [ ] **Day 3**: Convert Karma Ledger outline → LaTeX; submit to arXiv (or get very close)

### Days 4–7: Outreach
- [ ] **Day 4**: Identify 5 potential advisors; send cold emails to 3
- [ ] **Day 5**: Join Manifund Discord + EA Forum; introduce yourself
- [ ] **Day 6**: Write HN "Show HN" post + EA Forum post; publish both
- [ ] **Day 7**: Email 2 SFF Speculators + 1 Schmidt advisor with 3-sentence summary

### Days 8–10: Traction
- [ ] **Day 8**: Engage with HN comments; reply to every substantive comment
- [ ] **Day 9**: Email 5 safety labs for 15-min validation calls
- [ ] **Day 10**: Create "good first issue" labels on GitHub; tweet about them

### Days 11–12: Ecosystem
- [ ] **Day 11**: Attend one Foresight Node call or EA virtual event
- [ ] **Day 12**: Review 3 Manifund proposals; provide thoughtful feedback

### Days 13–14: Polish
- [ ] **Day 13**: Create professional application template (Google Docs / LaTeX)
- [ ] **Day 14**: Proofread all applications aloud; verify all links and numbers

---

## Honest Assessment: What A+ Actually Costs

| Dimension | Time | Money | Probability of Success |
|-----------|------|-------|----------------------|
| Warm intros | 6–10 hrs | $0 | 30% response rate → 2–3 actual conversations |
| Social proof | 4–6 hrs | $0 | 50% of advisors say yes to quote |
| Visuals | 6–8 hrs | $0 | 100% — fully controllable |
| Traction | 4–6 hrs | $0 | HN front page = 20% chance |
| Prestige signals | 3–5 days | $0 | arXiv = 100%; conference = 30%; podcast = 10% |
| Ecosystem | 2–3 hrs/week ongoing | $0 | 100% if sustained |
| Polish | 4–5 hrs | $0 | 100% — fully controllable |

**Total time**: ~2 weeks of focused work (6–8 hrs/day) + 2–3 hrs/week ongoing.

**Total cost**: $0.

**Expected outcome**: Applications move from B+ to A-. With arXiv + demo video + 2 advisor quotes, you hit A- consistently. With warm intro + HN traction + ecosystem participation, you hit A+ for 1–2 funders.

---

## The Brutal Truth

A+ applications are not just better-written versions of B+ applications. They have **external validation that B+ applications lack**.

You cannot write your way to A+. You must:
1. **Build relationships** (warm intros, ecosystem participation)
2. **Create artifacts** (arXiv, demo video, diagrams)
3. **Generate momentum** (HN post, GitHub stars, first user conversations)

The good news: all of these are within your control and cost $0. The bad news: they take 2–3 weeks, not 2–3 hours.

**My recommendation**: Submit A- applications in Week 1 (to capture fast funders like Manifund). Run the A+ sprint in parallel. When you get traction (HN post does well, advisor says yes, arXiv goes live), update your pending applications and lead with the new social proof.

**The portfolio effect**: Even if only 2 of 7 A+ dimensions work, that's enough to differentiate you from 90% of applicants.

---

*Last updated: 2026-04-30*
