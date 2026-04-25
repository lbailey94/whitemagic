# On-Premise / Edge AI Scenarios — Where WhiteMagic Has Unusual Leverage

**Status**: Private working strategy. Sales-facing concepts, not yet public copy.
**Audience**: Lucas + WhiteMagic Labs (internal).
**Last updated**: 2026-04-21 (regulatory dates refreshed; AB 489,
CMMC 2.0, NYDFS, NAIC, CO SB 205 added)
**Companion to**:
- `docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md` — the lab thesis
- `docs/strategy_manifestos/STRATEGY_AGENT_ECONOMY.md` — market read + financials
- `docs/ROADMAP.md` — 12-month direction

---

## 0. Thesis

The generic pitch "we build AI solutions" has ~infinite competitors. The
specific pitch **"we build AI that cannot leave your building, and we
make it auditable"** has almost none — and the buyers who need that
pitch have large budgets, regulatory tailwinds, and no acceptable
alternatives.

WhiteMagic's accidental/intentional technical posture — Rust + Python
polyglot, WASM target, local-first PWA, Ollama/vLLM-compatible,
no hard cloud dependencies, declarative NixOS deploy, Karma Ledger for
audit, Dharma rules for policy — is an almost exact fit for this
segment. This document enumerates the buyer scenarios where that fit
is strongest, and what the concrete engagement shape looks like for
each.

**Common thread**: the buyer's problem is *"we need AI and we cannot
use cloud AI."* Small market. High willingness to pay. Almost no
qualified vendors. Regulatory tailwinds instead of headwinds.

---

## 1. Mid-sized hospital system (500–2000 beds)

### The pain
- Clinical decision support, ambient documentation, clinical-note
  summarization, imaging triage — all have clear AI use cases.
- PHI legally cannot leave the building without a BAA, and many health
  systems don't trust BAAs for generative AI vendors whose data-
  handling practices are opaque.
- HIPAA audit-log requirements (45 CFR §164.312(b)) are getting
  stricter interpretations post-2024 OCR guidance on AI.
- Emerging state-level laws (CA **AB 3030** — GenAI patient-communication
  disclaimers, signed Sept 2024; CA **AB 489** — "Identity Law," patients
  must know they're not talking to a human; TX HB 3062) require disclosure
  and human oversight for AI-assisted clinical decisions.

### Why WhiteMagic fits
- **On-prem inference**: Ollama / vLLM / llama.cpp running on their
  hardware. We bring the governance layer, not the model.
- **Karma Ledger**: the audit-trail artifact almost maps 1:1 to HIPAA
  §164.312(b) technical-safeguards requirements. Merkle-verified so
  tampering is detectable.
- **Dharma rules**: "never suggest medication dose without explicit
  confirmation," "always flag differential diagnoses below confidence
  X," "no PHI egress under any circumstances." Policy as code.
- **Harmony Vector**: board-level health metric for AI system
  behavior; aligns with what risk committees want to see quarterly.

### Engagement shape
- **Scoping (paid)**: 2 weeks, $12,000 fixed. Produces a tailored
  deployment plan + risk register. Credits toward full engagement.
- **Deployment**: 10–12 weeks, $80,000–$150,000 fixed. Install, wire to
  one clinical workflow (start narrow — e.g. ambient documentation
  in outpatient clinic), full audit integration, staff training.
- **Ongoing support retainer**: $4,500–$8,000/mo. Rule tuning, new
  workflow onboarding, compliance refresh as regs change.

### Buyer triad
- **CMIO** (Chief Medical Information Officer) — clinical owner.
- **CISO / CIO** — security and infrastructure owner.
- **Compliance / Chief Privacy Officer** — regulatory owner.

All three must be in the first real meeting. If only one is engaged,
the deal stalls.

### Sales cycle
4–8 months from first contact to signed SOW. Procurement involvement
guaranteed. Expect one formal security questionnaire (SIG-Lite or
custom).

### Differentiation language for the site
> "Ambient clinical AI that never leaves your network, with an audit
> trail your compliance team can export to Excel."

---

## 2. Defense contractor subsidiary / defense-adjacent R&D lab

### The pain
- Small-to-mid defense contractors (not the top 5) have growing
  pressure to use LLMs for document analysis, knowledge management,
  RFP response drafting, and threat-intel synthesis.
- Most operate in cleared / IL4-IL5 environments where any external
  network touch is forbidden or requires massive ATO overhead.
- **CMMC 2.0 Level 2** (phased rollout 2025–2028) is the bigger near-term
  driver for non-top-5 contractors than raw IL4/IL5 — every prime's
  subcontractor flow-down now asks about it.
- Cloud AI vendors (including "GovCloud" offerings) are either too
  expensive, not yet authorized at the right impact level, or create
  ATO burdens the contractor doesn't want to own.

### Why WhiteMagic fits
- **True air-gap capability**: no telemetry, no phone-home, no
  hidden dependencies. We can demonstrate this with a packet capture.
- **Reproducible deploy** via declarative NixOS `configuration.nix` —
  produces the same build artifact every time. Security reviewers
  love this.
- **SBOM-friendly**: polyglot stack but each component has a clear
  dependency manifest (Cargo.lock, requirements.txt, etc.).
- **Karma Ledger** maps to NIST SP 800-53 AU-family controls (audit
  and accountability).
- **MandalaOS concept** (spec-only today) offers a longer-term story
  for compartmentalized agent workloads — relevant at higher impact
  levels.

### Engagement shape
- **Scoping (paid)**: 3 weeks, $18,000 fixed. Includes classified-
  environment deployment readiness review.
- **Deployment**: 12–16 weeks, $120,000–$250,000. Includes SCIF-
  compatible install procedures, offline update process design, and
  documentation for their ISSM.
- **ATO-support retainer**: $6,000–$10,000/mo. Keep documentation
  current, answer auditor questions, patch cycle management.

### Buyer triad
- **CTO** or **VP Engineering** — technical owner.
- **ISSM** (Information Systems Security Manager) — compliance /
  authorization owner.
- **Program manager** for the specific cleared program using it.

### Sales cycle
6–12 months. Very long. But once inside, extremely sticky — the
cost of switching AI vendors inside a cleared environment is higher
than the cost of tolerating mediocre fit.

### Cautions
- Do not pitch this unless you are prepared for long dormant periods
  in the pipeline.
- US-only (or Five Eyes-only) market. Lucas's jurisdiction and
  citizenship affect eligibility for some contracts.
- Requires credible references eventually — first engagement may need
  to come through a prime contractor referral.

### Differentiation language (internal use only)
> "The only AI governance stack that ships with a `configuration.nix`
> your ISSM can read in one sitting."

---

## 3. AmLaw 100 or large regional law firm

### The pain
- LLMs are useful for: privilege review, contract analysis, discovery
  triage, brief drafting, deposition summarization, client-intake
  classification.
- Attorney-client privilege means client documents cannot touch a
  third-party system without privilege-waiver risk or explicit BAA-
  equivalent engagement letters.
- Partner resistance is high. A 2023–2025 wave of vendor rollouts
  (Harvey, CoCounsel, Spellbook, Thomson Reuters CoCounsel) hit
  resistance from partners who don't trust cloud AI with their
  clients' crown jewels.
- Insurance carriers are beginning to ask explicit AI-related
  questions on malpractice policies.

### Why WhiteMagic fits
- **On-prem LLM** + MCP server wired to iManage, NetDocuments,
  Relativity, or whatever their DMS is.
- **Dharma rules**: "never summarize privileged documents without
  applying the [firm-specific] confidentiality label," "always cite
  source documents by Bates number," "no client data to any external
  endpoint ever."
- **Karma Ledger**: every document accessed, every tool call, every
  output generated — logged, exportable, discovery-ready.
- **Matter-based isolation**: Dharma supports per-matter scoping of
  agent access. Matches the conflict-check logic firms already run.

### Engagement shape
- **Pilot**: 6–8 weeks, $50,000–$80,000 fixed. One practice group,
  one workflow (usually contract review or discovery triage).
- **Firm-wide deployment**: 10–14 weeks follow-on, $80,000–$160,000.
- **Ongoing**: $5,000–$10,000/mo retainer.

### Buyer triad
- **General Counsel** (of the firm itself, not of its clients).
- **Chief Innovation Officer** (increasingly a real AmLaw role).
- **CIO / Director of IT**.
- Occasional 4th: the practice group chair who will use it first.

### Sales cycle
3–6 months for pilot. Faster than hospital or defense. AmLaw firms
can move when they decide to.

### Differentiation language for the site
> "Generative AI for legal work that keeps privilege intact and
> produces a matter-keyed audit trail every partner can review."

---

## 4. Financial services compliance team

### The pain
- Regional banks, credit unions, asset managers, insurance carriers
  — all want LLMs for KYC document review, suspicious-activity
  narrative drafting, regulatory-filing prep, customer-complaint
  triage, internal policy Q&A.
- Model-risk-management (SR 11-7 / OCC 2011-12) requirements mean any
  model used in a regulated decision path needs documented
  development, validation, monitoring, and governance.
- Third-party cloud LLMs fail this by default: no visibility into
  training data, no reproducibility, no model-version pinning, no
  audit trail the examiner will accept.

### Why WhiteMagic fits
- **Local / on-prem models with version pinning** — every inference
  is traceable to an exact model weight file and config.
- **Karma Ledger**: SR 11-7 §V.4 calls for "ongoing monitoring" with
  "continual testing and analysis" — our ledger is the instrumentation
  layer that makes this possible.
- **Dharma rules**: hard-coded policy constraints that the validation
  team can review as text, not as a black-box prompt.
- **Harmony Vector + export**: MRM committees want quarterly model
  performance reports. We produce them.

### Engagement shape
- **Scoping**: 2 weeks, $12,000 fixed.
- **Deployment + MRM-documentation package**: 8–12 weeks,
  $80,000–$180,000. The deliverable is as much *documentation* (for
  the examiner) as it is software.
- **Ongoing**: $4,500–$8,000/mo. Quarterly reports, annual revalidation
  support.

### Buyer triad
- **Chief Risk Officer** — MRM owner.
- **Head of Compliance** — regulatory liaison.
- **CTO / CIO** — infrastructure.
- Occasional 4th: **Chief Data Officer** if they have one.

### Adjacent regulatory drivers worth naming
- **NYDFS Part 500** (cybersecurity) — applies to all covered financial
  entities, AI question added in 2024 amendment cycle.
- **NAIC Model Bulletin on the Use of AI by Insurers** (adopted 2023,
  adopted by 20+ states as of 2026) — MRM-adjacent insurance overlay.

### Sales cycle
4–9 months. Bank procurement is slow. Expect vendor onboarding that
includes SOC 2 Type II questions (we have an honest answer: "we are
a small consulting firm, here is our attestation path").

### Differentiation language for the site
> "Model-risk-management-ready AI: pinned models, declarative policy,
> exportable audit trail. Every artifact your examiner will ask for,
> already in the box."

---

## 5. EU industrial / manufacturing company preparing for AI Act

### The pain
- EU AI Act entered into force August 2024. Key enforcement dates
  (current law, as of April 2026):
  - **Feb 2, 2025** — prohibited-practice ban + AI-literacy obligation.
  - **Aug 2, 2025** — GPAI-model rules + national governance stand-up.
  - **Aug 2, 2026** — **Annex III standalone high-risk obligations**
    (Art. 8–15: risk mgmt, data governance, technical docs, **Art. 12
    record-keeping**, Art. 13 transparency, **Art. 14 human oversight**,
    Art. 15 robustness) + deployer obligations (Art. 26) + FRIA (Art. 27).
    **This is the date that matters.**
  - **Aug 2, 2027** — Annex I product-embedded high-risk (AI inside
    regulated products — medical devices, machinery, vehicles).
- **Digital Omnibus proposal** (IMCO/LIBE voted 101-9-8 on Mar 18, 2026)
  would push Annex III to **Dec 2, 2027** and Annex I to **Aug 2, 2028**.
  *Not yet law* — pending trilogue and final adoption mid-to-late 2026.
  Pitch implication: help clients comply for Aug 2026 *and* be robust to
  a 16-month slip. This is a stronger pitch than either date alone.
- Many industrial AI uses (quality control, predictive maintenance
  with safety implications, HR screening, access control) fall under
  Annex III "high-risk" categories.
- Article 12 (record-keeping), Article 14 (human oversight), Article
  17 (quality management system), and Article 72 (post-market
  monitoring) all require technical implementations most companies
  are scrambling to deliver.
- National competent authorities are still standing up; companies
  would rather over-comply now than explain under-compliance later.

### Why WhiteMagic fits
- **Karma Ledger = Article 12** implementation. Near-literal.
- **Dharma rules + human-approval workflows = Article 14** operationalization.
- **Harmony Vector + Gnosis introspection = Article 72** post-market
  monitoring.
- **Reproducible NixOS deploy + SBOM = Article 17** quality management
  system substrate.

This is probably the tightest regulatory fit in the entire list.

### Engagement shape
- **AI Act Readiness Assessment**: 4 weeks, €25,000–€40,000 fixed.
  Gap analysis against their high-risk AI inventory, produces a
  remediation plan.
- **Implementation**: 10–14 weeks, €80,000–€180,000. Deploy the
  governance stack against one or more of their high-risk systems.
- **Ongoing compliance retainer**: €5,000–€10,000/mo.

### Buyer triad
- **CTO** or **Head of Digital/Industry 4.0**.
- **Data Protection Officer** (legally required for most EU
  companies over certain size).
- **Internal audit lead** or **Chief Compliance Officer**.

### Sales cycle
3–6 months, accelerating as the 2027 enforcement deadline approaches.
Expect this to become the dominant engagement type by mid-2027.

### Differentiation language for the site
> "Make your high-risk AI systems AI Act Article 12 / 14 / 72
> compliant — before the auditor asks."

### Practical note
Requires ability to invoice in EUR and an approach to VAT. Lucas's
current setup may need an adjustment (possible routing through a UK/
Irish/Estonian e-residency entity depending on volume).

---

## 6. Research lab / university department with sensitive data

### The pain
- Genomics, clinical trials, classified research, restricted human-
  subjects data, pre-publication IP.
- Want LLM assistance but cannot use public APIs.
- Budgets are grant-bound and often modest ($50K–$150K range).
- Often sophisticated technical users — they can run the infrastructure,
  they need the governance + audit layer and someone who knows
  where the edges are.

### Why WhiteMagic fits
- **Open-source posture** is a perfect match for academic/research
  culture. Many won't engage with closed-source vendors for
  ideological as well as practical reasons.
- **Reproducibility as first-class** aligns with research values.
- **Polyglot platform** appeals to engineering-heavy labs.
- **Smaller deployment** = we don't need a huge platform buy-in,
  one lab / one PI can get started.

### Engagement shape
- **Short sprint**: 4–6 weeks, $40,000–$80,000 fixed. Install,
  wire one data source, train the team to extend it.
- **Optional ongoing**: $2,500–$5,000/mo, usually only during the
  first year.

### Buyer profile
- **Principal Investigator** who controls a grant budget.
- Occasionally **Department Chair** or **Research Computing
  Director**.

### Sales cycle
2–4 months. Faster than commercial. Grant cycles matter — know
when the PI's next fiscal year starts.

### Strategic value beyond revenue
- **Testimonials** and **case studies** from named academic
  institutions carry disproportionate weight with commercial buyers
  later.
- **Publications** may emerge from the collaboration — a joint paper
  with a Harvard / Stanford / Max Planck lab is worth more than the
  engagement fee.
- **Standards-body pipeline**: academic contacts often serve on
  working groups we want seats at.

### Differentiation language for the site
> "Reproducible, auditable, open-source AI infrastructure for research
> teams who need to cite what they used, to the commit hash."

---

## 7. Municipal / state government IT modernization

### The pain
- Cities, counties, and states are piloting AI for constituent
  services (311 triage), code enforcement, permit processing, tax
  appeals assistance, benefits screening.
- FOIA / public records requirements: every AI-assisted decision
  may be subject to disclosure, which means every AI input and output
  may need to be retained and producible.
- Emerging state AI laws: **CO SB 205** (Colorado AI Act — broad
  high-risk AI regulation, effective date pushed from Feb 1, 2026 to
  **June 30, 2026**) is the closest US analogue to the EU AI Act;
  **NY Local Law 144** is narrower (hiring-bias audits only);
  **CA SB 53** (frontier-model transparency, signed Sept 2025) affects
  a few large model providers but not most public-sector deployments.
- Deep skepticism of cloud AI vendors, especially after high-profile
  failures (Michigan MiDAS, Amsterdam welfare-fraud algorithm, etc.).
- Budget process is rigid but once funded, execution timelines are
  long and vendors are hard to dislodge.

### Why WhiteMagic fits
- **Karma Ledger = FOIA readiness**: every prompt, response, tool
  call, and decision — retrievable and exportable in a format a
  records officer can hand to a requestor.
- **Dharma rules = policy-as-code** that civil-rights auditors
  can read.
- **On-prem** addresses the "where does constituent data go?"
  question at the hearing the Council will hold.
- **Open-source stance** addresses "why did we pick this vendor?"
  in procurement review.

### Engagement shape
- **Pilot**: 10–14 weeks, $100,000–$200,000. One agency, one workflow
  (usually 311 or permit triage).
- **Expansion**: $200,000–$400,000 for follow-on agencies over 12–18
  months.
- **Long-term**: multi-year retainer or master services agreement,
  $60,000–$120,000/year.

### Buyer profile
- **State / City CIO** or **Chief Data Officer**.
- **Chief Innovation Officer** (common in larger cities).
- Often gated through a **systems integrator** (Deloitte, Accenture,
  smaller GovTech specialists) for procurement reasons.

### Sales cycle
6–18 months. RFP-driven. Response-writing burden is real.

### Cautions
- Requires capacity to respond to RFPs. First one is painful; templates
  get reused.
- Public procurement usually requires bid bonds, insurance minimums,
  small business certifications. Some of this is rateable effort.
- Partnership with an existing small GovTech integrator may be the
  fastest path in — WhiteMagic as the AI governance layer inside
  their proposal, not as prime.

### Differentiation language for the site
> "Public-sector AI governance that satisfies FOIA and civil-rights
> audit requirements by design, not by retrofit."

---

## 8. Cross-cutting sales patterns

### 8.1 The "scoping engagement" as sales tool

In every scenario above, the recommended entry point is a **paid
scoping engagement** ($8K–$18K, 2–4 weeks), not a free proposal or a
multi-month prospecting phase. Reasons:

- Serious buyers pay for scoping; tire-kickers don't. It qualifies
  automatically.
- Produces a real deliverable (gap analysis + remediation plan) that
  is valuable even if the buyer doesn't proceed to the full engagement.
- Credits toward the full engagement, removing the "pay twice"
  objection.
- Builds trust without requiring a 6-figure commitment from a stranger.

### 8.2 The audit-trail deliverable as leave-behind

Every engagement should produce, in addition to the deployed software,
a **"compliance evidence package"** — a structured export showing:

- Which regulations / frameworks were mapped to which system components.
- Where the audit trail lives and how to export it.
- Who signs off on what (the RACI for AI governance in their org).
- Incident response runbook.
- Documentation for the next auditor.

This package is valuable beyond the engagement — it travels through
the buyer's organization. It is the closest thing to a physical product
an on-prem consulting engagement can produce.

### 8.3 Geographic and vertical concentration

Rather than spreading thin across all seven scenarios, the first 12
months should probably concentrate on **two**. Based on fit to
existing WhiteMagic strengths and market timing, my recommendation:

- **Primary**: Financial services compliance (#4) — largest market,
  clearest regulatory driver, buyer is organizationally set up to
  procure this kind of thing.
- **Secondary**: EU industrial / AI Act (#5) — strongest regulatory
  fit, accelerating timeline, builds international credibility.

Keep a live prospect in 1–2 of the others to preserve option value
but do not pursue aggressively until primary/secondary are producing.

### 8.4 The reference client problem

For every scenario, the hardest dollar is the first. Strategies:

- **Discounted first engagement** (30% off) in exchange for a named
  case study. Communicated in conversation, not on the site.
- **Grant-backed academic engagement** (#6) as proof-of-concept
  before commercial pitches.
- **Pilot-first pricing** (one practice group, one agency, one line
  of business) to lower initial commitment.
- **Co-delivery with an existing systems integrator** who already has
  the client relationship.

### 8.5 What to build next that expands this list

Each scenario has one or two capabilities that would meaningfully
increase close rate if they existed. Rough ranking:

- **HIPAA-specific audit-log schema preset** — turns a 6-week
  hospital engagement into 4. High ROI.
- **EU AI Act Article-12 / 14 / 72 evidence-report generator** —
  one-click quarterly compliance pack. Could be the most leveraged
  feature addition of the year.
- **Matter-scoped Dharma rule pack for legal** — takes the Law Firm
  pitch from concept to concrete.
- **SR 11-7 MRM documentation generator** — pulls audit-trail data
  into the format bank examiners expect.

These are natural extensions of the existing platform, not new
products. Each is a week or two of focused work and materially changes
the sales conversation in that vertical.

---

## 9. One-line summary per scenario

| # | Buyer | Why they can't use cloud AI | Engagement $ | Cycle |
|---|---|---|---|---|
| 1 | Hospital system | PHI + HIPAA audit | $80–150K | 4–8 mo |
| 2 | Defense contractor | Air-gap + ATO | $120–250K | 6–12 mo |
| 3 | AmLaw firm | Privilege + partner resistance | $50–160K | 3–6 mo |
| 4 | Financial services | SR 11-7 MRM + examiner | $80–180K | 4–9 mo |
| 5 | EU industrial | AI Act Art. 12/14/72 | €80–180K | 3–6 mo |
| 6 | Research lab | Data sensitivity + ideology | $40–80K | 2–4 mo |
| 7 | Public sector | FOIA + skepticism | $100–400K | 6–18 mo |

---

## 10. What to do with this document

This doc is a **reference for:**
- Writing the `/services` page copy (one-line summary per scenario
  goes on the site; the rest stays internal).
- Qualifying inbound leads (which of the 7 do they look like?).
- Targeting warm outbound (name-by-name, mapped to scenario).
- Writing case studies (structured around the buyer triad and the
  regulatory driver).
- Deciding what platform features to build next (§8.5).

It is **not** for public publication as-is. The buyer-triad mapping
and pricing specifics are strategic information; the scenarios
themselves, at high level, can inform public copy.

Revisit quarterly. The regulatory landscape shifts fast; the fit
ranking may change within 12 months.
