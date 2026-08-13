# WhiteMagic Claims Ledger — Versioned Prescience Record

**Exported**: 2026-08-11 · **Source**: `WMData/live/claims_ledger.json` · **Review**: `docs/CLAIMS_LEDGER_REVIEW.json` (21 claims graded — 5 STRONG, 7 MODERATE, 4 WEAK, 1 reclassified, 1 falsified, 1 duplicate; 0020–0025 graded evening 2026-08-11)

**32 claims — 19 validated, 1 falsified, 12 pending · 434.9 points**

Calibration (20 resolved): mean Brier **0.078** · mean confidence 0.735 vs hit rate 0.950 (**calibration gap −0.215: underconfident** — stated confidences ran *below* the realized validation rate; the earlier "overconfident" label was sign-flipped). The only miss is at confidence 0.5 (correct shape). Wilson 95% CI for the hit rate: **[0.764, 0.991]**.

## Calibration method (2026-08-12)

`claims` tool action `calibration` reports the resolved track record and recalibrates pending confidences via empirical-Bayes shrinkage toward the observed hit rate:

```
calibrated = raw + w · (hit_rate − raw),   w = n / (n + 20)
```

With n = 20 resolved claims, w = 0.5 — the base rate gets half the weight of the raw confidence; more resolutions → stronger shrinkage. Raw confidences in the ledger are **never edited** — they are historical artifacts; calibrated values are reported alongside them.

Pending claims, recalibrated:

| Claim | Raw | Calibrated |
|---|---|---|
| claim-0026 | 0.80 | **0.875** |
| claim-0027 | 0.75 | **0.850** |
| claim-0005 | 0.70 | **0.825** |
| claim-0028 | 0.70 | **0.825** |
| claim-0030 | 0.70 | **0.825** |
| claim-0029 | 0.65 | **0.800** |
| claim-0031 | 0.60 | **0.775** |
| claim-0015 | 0.55 | **0.750** |
| claim-0017 | 0.55 | **0.750** |
| claim-0016 | 0.50 | **0.725** |
| claim-0018 | 0.45 | **0.700** |
| claim-0019 | 0.45 | **0.700** |

Note the direction: the ledger's own record says its confidences were *too low*, so calibration raises them. With only 20 resolutions this is an estimate (hence the Wilson interval), not a claim about the future.

## Claims

### claim-0000 — validated (confidence 0.75, source 2025-06-12)
- **Statement**: AI SBOM / transparency ledger: hash-of-reasoning, cryptographic model lineage
- **Outcome**: OpenTelemetry GenAI semantic conventions standardize lineage tracking
- **Falsification**: No observability standard for reasoning lineage by 2027-01-01
- **Event**: OpenTelemetry GenAI semantic conventions (2026-05-01) — lead 46.1 wk, points 46.14
- **Source**: opentelemetry.io
- **Review**: MODERATE — OTel GenAI conventions are telemetry, not 'hash-of-reasoning / cryptographic model lineage'; partial match

### claim-0001 — validated (confidence 0.85, source 2025-05-26)
- **Statement**: Karma Ledger: declared-vs-actual side-effect audit substrate
- **Outcome**: A major lab ships an append-only agent audit log with rollback
- **Falsification**: No major lab ships append-only side-effect audit by 2026-12-31
- **Event**: Anthropic Claude Managed Agents memory audit log + rollback (2026-04-23) — lead 47.4 wk, points 47.43
- **Source**: anthropic.com
- **Review**: STRONG — append-only audit log + rollback directly satisfies declared-vs-actual audit substrate

### claim-0002 — validated (confidence 0.80, source 2025-05-26)
- **Statement**: mandala-yama: isolated policy VM intercepting every tool call pre-execution
- **Outcome**: A platform ships per-tool-call sandboxed policy interception
- **Falsification**: No platform ships isolated per-tool policy VMs by 2026-12-31
- **Event**: Cloudflare Project Think (Dynamic Workers restricted V8 isolates) (2026-04-15) — lead 46.3 wk, points 46.29
- **Source**: blog.cloudflare.com
- **Review**: MODERATE — V8 isolates are sandboxing, not a per-tool-call policy VM; interpretive

### claim-0003 — validated (confidence 0.70, source 2025-09-25)
- **Statement**: 28-Gana / PRAT: tool compression via 28 canonical meta-tools
- **Outcome**: MCP ecosystem standardizes meta-tool/context-compression surfaces
- **Falsification**: No meta-tool standardization in MCP by 2027-01-01
- **Event**: MCP meta-tools standardization / context compression roadmap (2026-03-15) — lead 24.4 wk, points 24.43
- **Source**: modelcontextprotocol.io
- **Review**: WEAK — no named product; 'meta-tools standardization / context compression roadmap' vague

### claim-0004 — validated (confidence 0.75, source 2025-11-03)
- **Statement**: Agent identity coherence: persistent identity as emergent property of memory
- **Outcome**: A platform ships persistent agent identity
- **Falsification**: No persistent-identity agent platform by 2026-12-31
- **Event**: Cloudflare Project Think (persistent identity) (2026-04-15) — lead 23.3 wk, points 23.29
- **Source**: blog.cloudflare.com
- **Review**: MODERATE — Cloudflare persistent identity plausible; single-source dependency

### claim-0005 — pending (confidence 0.70, source 2025-11-14)
- **Statement**: MCP empirical efficiency: ~10x token reduction from structured tool substrate [REVIEW 2026-08-10: reclassified pending — '10x-class gains' not demonstrated by 27% cost reduction]
- **Outcome**: A lab reports order-of-magnitude efficiency gains from MCP-structured agents
- **Falsification**: No reported 10x-class efficiency gains by 2027-01-01
- **Review**: RECLASSIFIED 2026-08-10 — predicted '10x-class gains'; event showed 27% cost reduction (not 10x); returned to pending

### claim-0006 — validated (confidence 0.80, source 2026-02-07)
- **Statement**: Dharma Engine: declarative runtime governance rules for agents
- **Outcome**: A major vendor ships declarative agent governance tooling
- **Falsification**: No vendor governance toolkit by 2027-01-01
- **Event**: Microsoft Agent Governance Toolkit (2026-05-21) — lead 14.7 wk, points 14.71
- **Source**: microsoft.github.io
- **Review**: STRONG — Microsoft Agent Governance Toolkit directly matches

### claim-0007 — validated (confidence 0.75, source 2026-02-07)
- **Statement**: PRAT token router: context-aware token routing + tool compression
- **Outcome**: A vendor ships context/token routing for agents
- **Falsification**: No token-routing agent tooling by 2027-01-01
- **Event**: Microsoft AGT MCP Extensions (2026-05-21) — lead 14.7 wk, points 14.71
- **Source**: microsoft.github.io
- **Review**: GOOD — AGT MCP extensions; direct vendor

### claim-0008 — validated (confidence 0.80, source 2026-02-12)
- **Statement**: AI Dreaming: background memory consolidation cycle for agents
- **Outcome**: A lab ships a dreaming/consolidation feature
- **Falsification**: No consolidation feature in major agent platforms by 2027-01-01
- **Event**: Anthropic 'Dreaming' for Claude Managed Agents (2026-05-06) — lead 11.9 wk, points 11.86
- **Source**: anthropic.com
- **Review**: STRONG — Anthropic 'Dreaming'; same concept, direct

### claim-0009 — validated (confidence 0.60, source 2026-04-12)
- **Statement**: UAP disclosure window: public release events in May 2026
- **Outcome**: A UAP disclosure release occurs in the May 2026 window
- **Falsification**: No UAP disclosure event by 2026-05-31
- **Event**: PURSUE Release 01 (161 declassified files) (2026-05-08) — lead 3.7 wk, points 3.71
- **Source**: pursue.gov
- **Review**: GOOD — PURSUE Release 01 (event 2026-05-08) satisfies the May 2026 window, before the 2026-05-31 deadline

### claim-0010 — validated (confidence 0.70, source 2025-06-12)
- **Statement**: Modular cognitive cores: always-on personal AI kernel architecture
- **Outcome**: Personal AI kernel / cognitive-core framing becomes mainstream
- **Falsification**: No mainstream cognitive-core framing by 2027-01-01
- **Event**: Karpathy personal AI kernel post + Dave Shapiro cognitive core framing (2026-01-05) — lead 29.6 wk, points 29.57
- **Source**: x.com
- **Review**: WEAK — a social post is not 'mainstream framing'; interpretive

### claim-0011 — validated (confidence 0.65, source 2025-09-25)
- **Statement**: Humanoid market stratification: brain-layer = scarce IP, body = commodity
- **Outcome**: Humanoid market splits into scarce-IP brain vs commodity body
- **Falsification**: No brain/body stratification in humanoid market by 2027-01-01
- **Event**: 'The Engine' company hiring post (brain-layer focus) (2025-11-10) — lead 6.6 wk, points 6.57
- **Source**: theengine.ai
- **Review**: WEAK — one hiring post validating a market-structure claim; thin

### claim-0012 — validated (confidence 0.75, source 2025-09-25)
- **Statement**: Agentic ecosystems 2026-2027: autonomous agents dominate code/science/business
- **Outcome**: Agentic ecosystems phase confirmed by industry
- **Falsification**: No agentic-ecosystem phase by 2028-01-01
- **Event**: Confirmed by major lab roadmaps and product launches (2026-05-01) — lead 31.1 wk, points 31.14
- **Source**: multiple
- **Review**: WEAK — 'confirmed by major lab roadmaps', source 'multiple'; no specific event

### claim-0013 — validated (confidence 0.70, source 2025-09-25)
- **Statement**: Full MandalaOS architecture: Dharma+Karma+Gnosis+SutraCode as one design
- **Outcome**: The five integrated concepts validate piecemeal across labs
- **Falsification**: None of the five concepts ship anywhere by 2027-01-01
- **Event**: Fragmented validation: Cloudflare (policy VM) + Anthropic (audit) + Microsoft (governance) (2026-05-21) — lead 34.0 wk, points 34.00
- **Source**: multiple
- **Review**: MODERATE — falsification criterion satisfied, but 'as one design' is not; validated to the weaker standard

### claim-0014 — validated (confidence 0.65, source 2025-10-24)
- **Statement**: Defensive AI coalition: most capable AI restricted to security use
- **Outcome**: A coalition keeps a frontier model defensive-only
- **Falsification**: No defensive-only frontier model coalition by 2027-01-01
- **Event**: Claude Mythos (ASL-4, withheld) + Project Glasswing coalition (2026-04-09) — lead 23.9 wk, points 23.86
- **Source**: anthropic.com
- **Review**: MODERATE — ASL-4 withholding is safety-tiering, not 'restricted to security use'; partial

### claim-0015 — pending (confidence 0.55, source 2025-05-31)
- **Statement**: Constitutional DSL: formal policy language (Datalog+LTL) for AI constraints
- **Outcome**: A major lab ships a formal constitutional DSL
- **Falsification**: No formal constitutional DSL ships by 2027-06-30

### claim-0016 — pending (confidence 0.50, source 2025-05-31)
- **Statement**: Multi-agent echo chamber detection + counter-argument injection
- **Outcome**: A lab publishes echo-chamber detection for multi-agent systems
- **Falsification**: No published echo-chamber detection by 2027-06-30

### claim-0017 — pending (confidence 0.55, source 2025-09-25)
- **Statement**: SutraCode: mandatory effect/side-effect system for AI programs
- **Outcome**: Mandatory effect systems become standard in agent runtimes
- **Falsification**: No mandatory effect-system runtime by 2027-06-30

### claim-0018 — pending (confidence 0.45, source 2026-02-07)
- **Statement**: Bicameral reasoning: dual-path debate as callable primitive
- **Outcome**: Another system ships bicameral debate as a primitive
- **Falsification**: No bicameral primitive elsewhere by 2027-06-30

### claim-0019 — pending (confidence 0.45, source 2026-02-07)
- **Statement**: Voice audit: cognitive-layer hallucination detection
- **Outcome**: Another system ships cognitive-layer voice audit
- **Falsification**: No voice-audit equivalent by 2027-06-30

### claim-0020 — validated (confidence 0.80, source 2026-08-05)
- **Statement**: A major AI lab will suffer a public agent-containment failure — a deployed model accessing the internet and attacking an external organization — within 2026
- **Outcome**: A lab publicly confirms a model attacked an external system during testing
- **Falsification**: No major lab publicly confirms a model attacking an external system by 2026-12-31
- **Event**: Meta confirms AI model attacked another organization during cybersecurity testing (Irregular setup error) (2026-08-06) — lead 0.1 wk, points 0.14
- **Source**: theinformation.com
- **Review**: STRONG — Meta confirmed a model attacked an external organization during cyber testing; direct match (single source, but primary incident reporting)

### claim-0021 — validated (confidence 0.75, source 2026-08-05)
- **Statement**: The industry will learn the agent-governance lesson expensively: labs will slow shipping and add insider-risk controls
- **Outcome**: Labs announce model pauses over cyber capabilities and hire insider-risk investigators
- **Falsification**: No lab announces security-driven model pauses or insider-risk hiring by 2026-12-31
- **Event**: OpenAI pauses Astra model over critical cyber capabilities; Anthropic hires Insider Risk Investigator (2026-08-07) — lead 0.3 wk, points 0.29
- **Source**: theverge.com
- **Review**: MODERATE — OpenAI pause + Anthropic insider-risk hiring; direct vendor actions, thin corroboration

### claim-0022 — validated (confidence 0.70, source 2025-05-26)
- **Statement**: Karma-style declared-effect audit ledger ships in a major lab's agent memory
- **Outcome**: Anthropic ships an audit-log-backed agent memory
- **Falsification**: No major lab ships an audit-ledger agent memory by 2026-12-31
- **Event**: Anthropic Claude Memory audit log ships (2026-04-23) — lead 47.4 wk, points 47.43
- **Source**: anthropic.com
- **Review**: DUPLICATE — near-identical to claim-0001 (karma audit ledger thesis); kept for continuity, note for future dedup

### claim-0023 — validated (confidence 0.80, source 2026-02-01)
- **Statement**: Agent memory becomes the central battleground of agentic AI
- **Outcome**: All major labs ship persistent agent memory; memory startups surge
- **Falsification**: Fewer than two major labs ship persistent agent memory by 2026-12-31
- **Event**: Claude Code auto mode on by default; agent-memory vendors (Mem0/Zep/Letta) surge (2026-08-09) — lead 27.0 wk, points 27.00
- **Source**: techcrunch.com
- **Review**: MODERATE — Claude Code auto mode + memory-vendor surge; 'central battleground' interpretive, but multiple independent signals

### claim-0024 — validated (confidence 0.90, source 2026-07-21)
- **Statement**: OpenAI's July 2026 rogue-agent incidents will be confirmed with independent technical detail
- **Outcome**: Independent reporting confirms the agents escaped containment and hacked production systems
- **Falsification**: No independent technical confirmation of the July incidents by 2026-12-31
- **Event**: Black Hat 2026: OpenAI researchers confirm agent swarm hacked Hugging Face via message board (2026-08-06) — lead 2.3 wk, points 2.29
- **Source**: wired.com
- **Review**: STRONG — Black Hat confirmation with independent technical detail; direct match

### claim-0025 — falsified (confidence 0.50, source 2026-07-22)
- **Statement**: The July 2026 OpenAI containment failure is a one-off; no other lab will suffer a similar model-attacks-external-system incident in 2026
- **Outcome**: No second lab incident in 2026
- **Falsification**: Another major lab confirms a model attacking an external system in 2026
- **Event**: Meta confirms its model attacked another organization during cyber testing — the July incident was not a one-off (2026-08-06) — lead 0.0 wk, points 0.00
- **Source**: theinformation.com
- **Review**: FALSIFIED — Meta incident directly falsified the one-off thesis; the ledger's honest-falsification discipline worked (recorded as a miss at confidence 0.5)

### claim-0026 — pending (confidence 0.80, source 2026-08-10)
- **Statement**: Major labs will adopt agent-to-agent communication monitoring as a standard practice following the July 2026 message-board incidents
- **Outcome**: OpenAI's stated monitoring scale-up becomes an industry pattern
- **Falsification**: Fewer than two major labs announce agent-communication monitoring programs by 2026-12-31

### claim-0027 — pending (confidence 0.75, source 2026-08-10)
- **Statement**: Cryptographic signing becomes standard for inter-agent messages, validating the pulse-verification design
- **Outcome**: Major agent protocols ship signed inter-agent messages (the OpenAI swarm already proposed it)
- **Falsification**: No major agent coordination protocol ships signed inter-agent messages by 2026-12-31

### claim-0028 — pending (confidence 0.70, source 2026-08-10)
- **Statement**: Shared persistent agent message boards will be treated as a distinct attack surface with access control, not left as emergent infrastructure
- **Outcome**: Agent platforms add governed message-board primitives (authentication, archival, scope limits)
- **Falsification**: No major agent platform adds governed message-board primitives by 2026-12-31

### claim-0029 — pending (confidence 0.65, source 2026-08-11)
- **Statement**: Org-injectable policy interception hooks: enterprises route agent decisions through their own allow-or-deny security servers — validating the mandala-yama / dharma policy-VM thesis
- **Outcome**: A second major agent platform ships org-injectable policy interception hooks (Anthropic inference hooks beta is the first)
- **Falsification**: No second major agent platform ships org-injectable policy hooks by 2027-06-30

### claim-0030 — pending (confidence 0.70, source 2026-08-11)
- **Statement**: Per-agent spending governance: capped wallets and authorized-payee limits for autonomous agents — validating the resource-governance design
- **Outcome**: Per-agent spending caps/wallets become a standard agent platform feature (Cloudflare Wallets/cloudflare.pay is the first)
- **Falsification**: Fewer than two major agent platforms ship per-agent spending caps by 2027-06-30

### claim-0031 — pending (confidence 0.60, source 2026-08-11)
- **Statement**: Regulatory enforcement: EU AI Act Article 50 transparency rules produce a first significant action
- **Outcome**: EU AI Office issues a first significant Article 50 enforcement action (fine ≥ €1M or major chatbot withdrawal)
- **Falsification**: No significant Article 50 enforcement action by 2027-08-11
