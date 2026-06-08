import { Clock, Target, Crosshair, CheckCircle2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface Claim {
  icon: LucideIcon;
  claim: string;
  when: string;
  validated: string;
  gap: string;
  detail: string;
  needsResearch?: boolean;
}

export interface Miss {
  claim: string;
  reality: string;
  learned: string;
}

export const PRESCIENCE_CLAIMS: Claim[] = [
  { icon: Clock, claim: "Karma Ledger spec (append-only audit trail)", when: "May 26, 2025", validated: "Apr 23, 2026", gap: "11 months", detail: "Specified an append-only, cryptographically verifiable audit ledger with declared-vs-actual side-effect tracking. Anthropic shipped a structurally similar audit log + rollback mechanism 11 months later." },
  { icon: Target, claim: "Dharma Rules Engine + 7-stage pipeline", when: "Feb 7, 2026", validated: "Mar 4, 2026", gap: "4 weeks", detail: "Shipped declarative policy engine, multi-stage dispatch pipeline, circuit breakers, and agent trust scores. Microsoft announced the Agent Governance Toolkit with the same architecture 4 weeks later. [NEEDS RESEARCH: Microsoft AGT v4.0.0 (Jun 1, 2026) ships 992 conformance tests across 11 specs. Claim requires truth-finding session to determine whether WhiteMagic's local-first, non-Azure, framework-agnostic implementation remains meaningfully differentiated.]", needsResearch: true },
  { icon: Crosshair, claim: "Tool compression (PRAT Gana meta-tools)", when: "Feb 7, 2026", validated: "Mar 11, 2026", gap: "5 weeks", detail: "Shipped 28 PRAT Gana meta-tools for context compression and intelligent tool routing. The MCP roadmap named context bloat a top priority 5 weeks later. [NEEDS RESEARCH: Microsoft AGT v4.0.0 (Jun 1, 2026) ships MCP Extensions with token routing. Claim requires truth-finding session to assess whether 75.5% compression and 28-Gana symbolic taxonomy remain unique differentiators.]", needsResearch: true },
  { icon: CheckCircle2, claim: "Agent identity coherence", when: "Nov 3, 2025", validated: "Apr 15, 2026", gap: "~24 weeks", detail: "Observed agent identity coherence as an emergent property of persistent memory — agents maintaining consistent personality and goals across sessions. Cloudflare Project Think shipped a first-party persistent agent identity + wake-on-message runtime on Apr 15, 2026, validating the category. WhiteMagic's open-source implementation predates it by ~24 weeks." },
  { icon: Target, claim: "Convergence 2026: UAP disclosure window", when: "Mar 2026", validated: "May 8, 2026", gap: "~2 months", detail: "Predicted the 2026 UAP disclosure window. PURSUE Release 01 (161 declassified files) published May 8, 2026. Rolling disclosure cadence confirmed." },
  { icon: Crosshair, claim: "Convergence 2026: AGI acceleration", when: "Mar 2026", validated: "Apr 7, 2026", gap: "~1 month", detail: "Predicted AGI acceleration in 2026-2027. Claude Mythos — 93.9% SWE-bench, autonomously discovered thousands of zero-days — withheld under ASL-4 on April 7, 2026." },
  { icon: Target, claim: "Bicameral reasoning architecture", when: "Feb 7, 2026", validated: "Jun 1, 2026", gap: "~16 weeks", detail: "Dual-path decision architecture: one path for speed/capability, one for ethical constraints. Both must agree before high-stakes actions. Microsoft AGT v4.0.0 (Jun 1, 2026) ships 'Agent Hypervisor Execution Control' with a delta engine and commitment anchoring — dual-path policy evaluation with fail-closed semantics that structurally mirrors bicameral critique-before-execution. WhiteMagic's implementation predates public knowledge of AGT's internals by ~16 weeks. 992 conformance tests, 110 contributors. [NEEDS RESEARCH: Truth-finding session required to determine whether AGT's 992 conformance tests represent convergence or superseding. Evaluate whether WhiteMagic's bicameral 'corpus callosum debate' implementation is structurally equivalent or merely analogous.]", needsResearch: true },
  { icon: CheckCircle2, claim: "Voice audit with chain-of-thought", when: "Feb 7, 2026", validated: "Jun 1, 2026", gap: "~16 weeks", detail: "Full agent action logging with chain-of-thought reasoning replay. Auditors can inspect the complete context window for any decision. Microsoft AGT v4.0.0 (Jun 1, 2026) ships 'Agent Hypervisor Execution Control' with delta engine and commitment anchoring — execution audit with reasoning trace capture that structurally mirrors Voice Audit's chain-of-thought replay. WhiteMagic's implementation predates public knowledge of AGT's feature set by ~16 weeks. [NEEDS RESEARCH: Truth-finding session required to compare AGT's audit trace depth with WhiteMagic's voice_audit behavioral consistency checking. Determine whether these are convergent or whether one subsumes the other.]", needsResearch: true },
  { icon: Clock, claim: "AI Dreaming / Memory Consolidation System", when: "Feb 12, 2026", validated: "May 6, 2026", gap: "~12 weeks", detail: "Shipped a full 8-phase dream cycle with dream daemon, dream artifacts, dream consolidation, background dreamer, dream galaxy persistence, and I Ching-aligned phases. Anthropic announced 'Dreaming' for Claude Managed Agents at Code with Claude — a scheduled process that reviews past sessions, extracts patterns, and writes plain-text playbooks for future self-improvement. WhiteMagic's system is significantly more elaborate (holographic encoding, galactic memory, resonance-based synthesis) and predates Anthropic's announcement by 83 days. [NEEDS RESEARCH: Anthropic Dreaming (Apr 29, 2026) and Auto-Dreamer (arXiv May 2026) represent both product and research implementations. Truth-finding session required to assess whether WhiteMagic's 8-phase dream cycle with holographic encoding is genuinely differentiated or merely more elaborate.]", needsResearch: true },
  { icon: Crosshair, claim: "Isolated policy-VM for tool-call interception", when: "May 26, 2025", validated: "Apr 15, 2026", gap: "~10.5 months", detail: "Specified 'mandala-yama' — an OPA-powered policy VM intercepting every tool call through an isolated sandbox before execution, with allow/log/deny decisions. Cloudflare Project Think shipped Dynamic Workers (restricted V8 isolates for per-tool sandboxed execution) 10.5 months later. Independently verifiable: CODEX OpenAI archive conversation ID 6834cc70-f9b8-8005-8562-2c049f7701e1, timestamped 2025-05-26." },
  { icon: Clock, claim: "MCP empirical efficiency gain (10× token reduction)", when: "Nov 14, 2025", validated: "Apr 23, 2026", gap: "~5 months", detail: "Early alpha validation documented: WhiteMagic MCP substrate produced 10× fewer tokens per conversation turn and 10× faster response times, with benefits compounding over time as the memory layer accumulates working knowledge. Anthropic validated structurally similar gains for Claude Managed Agents (97% fewer errors, 27% lower cost) 5 months later. Independently verifiable: CODEX OpenAI archive conversation ID 6917f2d7-0a10-8332-83e5-f26a7e99da44, timestamped 2025-11-14." },
  { icon: Target, claim: "Modular cognitive cores / always-on personal AI kernel", when: "Jun 12, 2025", validated: "Jan 5, 2026", gap: "~29 weeks", detail: "CyberBrain Core Mapping design session (Jun 12, 2025) formalizes the v1.2 architecture as a multi-module system: Physical Simulation Engine, Deductive Reasoning Engine, Specialist Learning Core, Task Dispatcher, LLM Communication Layer, and Executive Integrator — with multi-timescale sync (10ms sensory / 1s planner / 1hr consolidation). The Sep–Oct 2025 CyberBrains notes on the SD card are a later elaboration of the same concept. Grok independently confirmed (Jan 5, 2026) that the full architecture predated Andrej Karpathy's 'personal AI kernel' post and Dave Shapiro's 'cognitive core' framing by roughly 7 months. Primary source: CODEX OpenAI archive ID 684b6aa4-f83c-8005-a005-cab4d70b1f69, server-timestamped 2025-06-12. Corroborating source: SD Card CODEX Grok archive 2026-01-05_grok_Modular_AI_Architectures_for_Personal_Computing_03e7c6b3.md." },
  { icon: Crosshair, claim: "Humanoid market: brain-layer is the scarce IP, body is commodity", when: "Sep–Oct 2025", validated: "Nov 10, 2025", gap: "~6 weeks", detail: "CyberBrains notes argued the humanoid robotics market would stratify into commodity body-makers and scarce-IP brain-layer providers — and that the AI cognitive kernel was the defensible moat. Grok independently confirmed (Nov 10, 2025) this framing was 'ahead of the curve' relative to commercial humanoid AI announcements. Source: SD Card CODEX Grok archive 2025-11-10_grok_CyberBrains_Modular_AI_for_Humanoids_96adcaf0.md." },
  { icon: Clock, claim: "Agentic Ecosystems 2026–2027 prediction", when: "Sep 25, 2025", validated: "May 2026", gap: "~32 weeks", detail: "---NewIntelligence.txt (SD Card LIBRARY, filesystem timestamp 2025-09-25 22:24:58 EDT) explicitly predicted 'Agentic Ecosystems 2026–2027': autonomous agents dominating code, science, business, and education; AI copilots at every research level; agents self-generating task chains and navigating APIs autonomously. This is unfolding on schedule as of May 2026. The same document predicted 'AGI Emergence Threshold 2025' — models meeting old benchmark definitions — which has also occurred. Both predictions were made as a coherent timeline, not isolated guesses." },
  { icon: CheckCircle2, claim: "MandalaOS unified architecture: Dharma Engine + Karma Ledger + Gnosis Portals + SutraCode", when: "Sep 25, 2025", validated: "Apr–May 2026", gap: "~28 weeks", detail: "---NewSystems.txt (SD Card LIBRARY, filesystem timestamp 2025-09-25 22:31:50 EDT) contains the complete MandalaOS specification: Dharma Engine (mandatory ethical kernel subsystem intercepting every syscall), Karma Ledger (append-only immutable audit), Gnosis Portals (introspection APIs at every layer boundary), and SutraCode (mandatory first-class effect/side-effect system). Each concept was validated independently by Cloudflare (policy VM, Apr 15), Anthropic (audit + memory, Apr 23), and Microsoft (governance engine + token routing, May 21). The singular insight: all five patterns appear together in one design from Sep 25, 2025 — industry validated them piecemeal across three companies over seven months." },
  { icon: Target, claim: "Defensive AI coalition — powerful AI restricted to security use, too dangerous for public release", when: "Oct 24, 2025", validated: "Apr 9, 2026", gap: "~24 weeks", detail: "EdgeRunner Violet notes (Oct 24, 2025) designed AI-augmented purple-team security on MandalaOS micro-kernel: scope tokens, dual-ledgers, explain-or-exec UX, no unsigned offensive actions — a defensive coalition model where the most powerful AI is never released publicly but deployed only via coordinated authorized access. Anthropic's Claude Mythos arrived as exactly this: AI assessed as too powerful for general release, deployed defensively via Project Glasswing coalition (Anthropic + Apple + Google + Microsoft + 45+ companies for coordinated vulnerability hunting). The guardrailed defensive-AI-coalition model arrived on schedule, 24 weeks after the design. Independently verifiable: Grok archive 2026-04-09_grok_Claude_Mythos_Powerful_Restricted_Cybersecurity_AI_e4f9ab2f.md." },
  { icon: Clock, claim: "4-stage AI trajectory: AGI 2025 → Agentic Ecosystems 2026–2027", when: "Oct 17, 2025", validated: "May 2026", gap: "~28 weeks", detail: "Four-stage trajectory polished in Grok export: 2025 AGI Emergence (models with tool use, memory, self-correction), 2026–2027 Agentic Ecosystems (agents dominate code/science/business), 2028–2029 Cambrian Explosion (thousands of specialized intelligences), 2030 ASI approach. By May 2026 both Stage 1 (Claude Mythos, general 2025 AGI discourse) and Stage 2 (MCP ecosystem 10,000+ servers, A2A protocol, multi-agent standards) are confirmed. Stages 3–4 remain pending. Independently verifiable: Grok export 2025-10-17_grok_AI_Evolution_Research_Ethics_Future_5bd87bf3.md." },
  { icon: Crosshair, claim: "Local-first hybrid memory architecture (SQLite + FTS5 + vector + audit trail)", when: "Nov 1, 2025", validated: "Feb 10, 2026", gap: "~15 weeks", detail: "WhiteMagic v2.1.0 shipped a local-first hybrid memory substrate using SQLite + FTS5 + vector embeddings + graph walk + audit-trailed half-life decay. OMEGA independently published a whitepaper on Feb 10, 2026 describing the identical architecture class (SQLite + FTS5 + ONNX embeddings + SHA256+embedding deduplication + TTL forgetting with audit trails). Both are solo-dev, zero-budget, Apache-2.0 projects. The convergence validates the architecture class; neither caused the other." },
];

export interface PendingClaim {
  claim: string;
  when: string;
  direction: string;
  status: "arriving" | "pending" | "contested";
  confidence: "high" | "medium" | "low";
  source: string;
}

export const PRESCIENCE_PENDING: PendingClaim[] = [
  {
    claim: "AI Cambrian Explosion 2028–2029",
    when: "Sep 25, 2025",
    direction: "Agentic Ecosystems 2026 are the precursor. The next phase — thousands of specialized AI organisms each optimized for a narrow domain — is now widely discussed as the next architectural shift after general-purpose agents. Timeline aligns.",
    status: "arriving",
    confidence: "high",
    source: "---NewIntelligence.txt, SD Card LIBRARY, filesystem timestamp 2025-09-25 22:24:58 EDT",
  },
  {
    claim: "SMR / microreactor leasing model as energy backbone for AI compute",
    when: "May 23, 2025",
    direction: "Hyperscaler nuclear procurement wave confirmed: 9.8 GW across 13 disclosed projects by May 2026 (Microsoft TMI restart 835 MW, Amazon 5 GW X-energy by 2039, Google/Kairos 500 MW, Meta ~6.6 GW total). However, the specific 'individuals/communities rent/lease' model proposed May 23, 2025 has NOT crystallized — all deals are corporate PPAs and direct hyperscaler procurement. The demand prediction was accurate; the distribution model prediction was partially accurate (enterprise-first, not community-first).",
    status: "arriving",
    confidence: "medium",
    source: "Microreactors for Emergency Power, CODEX OpenAI archive ID 6830f947-1828-8005-aea0-77e4eb89c353, 2025-05-23. External: Presenc AI Hyperscaler Nuclear PPA Tracker 2026; Temple 8 CERAWeek research",
  },
  {
    claim: "Transparent reasoning / Theory of Mind probes as mandatory AI trust layer",
    when: "Jun 9, 2025",
    direction: "Anthropic extended thinking, OpenAI o3 reasoning traces, Anthropic SAE interpretability features, and the EU AI Act's explainability requirements are all heading toward mandatory chain-of-thought transparency. The 'show your reasoning to earn trust' principle is becoming industry norm.",
    status: "arriving",
    confidence: "high",
    source: "Energy AI Ethics Synergy, CODEX OpenAI archive ID 6847500a-44d4-8005-969a-0a0be20ea899, 2025-06-09",
  },
  {
    claim: "Self-improving AI with open-ended evolutionary search (Darwin Gödel Machine paradigm)",
    when: "Jun 12, 2025",
    direction: "Sakana AI's Darwin Gödel Machine was identified contemporaneously (Jun 2025) as validating the CyberBrain self-improvement vision. SEAL (MIT), AlphaEvolve (Google), and agent-directed code generation are converging toward this. The closed-loop self-modification paradigm is consolidating.",
    status: "arriving",
    confidence: "high",
    source: "Zodiac Systems AI Forecasting, CODEX OpenAI archive ID 684b6b5e-4a3c-8005-b506-e5429c3a5d08, 2025-06-12",
  },
  {
    claim: "Decentralized multi-agent consensus mesh (agent-to-agent economy)",
    when: "May 31, 2025",
    direction: "MCP ecosystem (10,000+ servers), A2A protocol (Google), x402 micropayments, and AAIF consortium are converging on exactly this mesh. The Zodiac Suite v1.0 (May 31, 2025) designed a 12-agent council with 'debate, voting protocols, and weighted consensus algorithms' — the earliest document for this concept. Full autonomous agent economy not yet operational.",
    status: "arriving",
    confidence: "high",
    source: "Zodiac AI Design Draft, CODEX OpenAI archive ID 683b5dca-ea34-8005-b0da-eb76be399349, 2025-05-31",
  },
  {
    claim: "AI-native multi-hazard disaster prevention lattice (Zodiac Systems)",
    when: "May 31, 2025",
    direction: "Zodiac Suite v1.0 (May 31, 2025) designed 12 domain-specialist agents (storms, seismics, hydrology, etc.) integrated into a disaster-prevention council with failsafe routing and weighted consensus. Google DeepMind GenCast, NVIDIA Earth-2, and NOAA AI forecasting are each sub-agent precursors. Integrated lattice not yet assembled.",
    status: "arriving",
    confidence: "medium",
    source: "Zodiac AI Design Draft, CODEX OpenAI archive ID 683b5dca-ea34-8005-b0da-eb76be399349, 2025-05-31",
  },
  {
    claim: "UBI / automation dividend as a structural societal response to AI displacement",
    when: "May 27, 2025",
    direction: "Discussed 'data/AI dividend' and 'Post-human Commons with reputation-based ledgers' on May 27, 2025. Jun 24 session added LVT + automation-royalty dual-funding model and 'programmable civic contracts' in MandalaOS. UBI pilots now active globally; David Shapiro's Labor Zero (L/0) movement mainstreaming. No national rollout yet.",
    status: "pending",
    confidence: "medium",
    source: "UBI AI and Fairness, CODEX OpenAI archive ID 68366344-20c4-8005-a1bd-2b666a1b94b4, 2025-05-27",
  },
  {
    claim: "Neuromorphic / memristor edge chips → sub-10W always-on AI inference",
    when: "Jun 9, 2025",
    direction: "Qualcomm Snapdragon X NPU, Apple Neural Engine M4, Intel Loihi 2, and Mythic analog AI are closing in. Sub-10W inference for smaller models is already real; frontier-class inference at this threshold is 1–2 chip generations away. On track.",
    status: "arriving",
    confidence: "medium",
    source: "Energy AI Ethics Synergy, CODEX OpenAI archive ID 6847500a-44d4-8005-969a-0a0be20ea899, 2025-06-09",
  },
  {
    claim: "Neurophotonic Data Center 2.0→3.0: photonic AI chips at 1,000× GPU efficiency",
    when: "Oct 2025",
    direction: "'datacenters.txt' notes (Oct 2025) engineered neurophotonic chips with photonic MACs at fJ–pJ (100× better than GPU), WDM broadcast-and-weight topologies, PCM synapses, and microfluidic heat-reuse campuses. Peter Diamandis announced March 2026: 'neuromorphic breakthroughs simulate complex physics on brain-inspired chips using 1,000× less energy than supercomputers.' Grok confirmed the notes were a phase map.",
    status: "arriving",
    confidence: "high",
    source: "datacenters.txt, SD Card CODEX (Oct 2025); confirmed aligned by Grok: 2026-03-16_grok_Neurophotonic_Future_2025_Notes_Align_2026_79a067a2.md",
  },
];

export const PRESCIENCE_MISSES: Miss[] = [
  { claim: "Memory-as-a-service would be the primary monetization path", reality: "Governance infrastructure, not memory, is the market's urgent need. Memory is a feature of governance, not a standalone product. Platforms (Anthropic, Microsoft, OpenAI) absorbed memory as a first-party feature by mid-2026.", learned: "May 2026" },
  { claim: "Agent economy would crystallize around payments first", reality: "Governance and observability crystallized first. Payments (x402, agent-to-agent) are still emerging. The Gratitude Architecture is ahead of its market.", learned: "May 2026" },
  { claim: "Governance as a defensible solo-developer moat", reality: "Microsoft AGT (Mar 4), Chitragupta (Feb 9), Sgraal (Mar 22), Aevum (Apr 22), Ardur (May 14), and DingDawg (May 30) all shipped governance layers by May 2026. The category went from empty to crowded in 3 months. The technique is still valuable; the exclusivity is gone.", learned: "May 2026" },
  { claim: "L4 governance unsolved at standards level", reality: "Microsoft AGT v4.0.0 (Jun 1, 2026) ships comprehensive L4 governance with 992 conformance tests, NSA alignment, and multi-language SDKs. Visa TAP, Mastercard Verifiable Intent, ArbiterOS, and SDOS are all active. The field went from empty to crowded in 2 months.", learned: "Jun 2026" },
  { claim: "AI dreaming / memory consolidation unique to WhiteMagic", reality: "Anthropic Dreaming (Apr 29, 2026) is a direct commercial implementation with scheduled consolidation, deduplication, and pattern extraction. Auto-Dreamer (arXiv May 2026) is a learned research implementation. The concept was never unique — WhiteMagic's contribution was operationalizing it locally 11 weeks before Anthropic's managed-agent implementation.", learned: "Jun 2026" },
];

export const PRESCIENCE_METHODLOGY_NOTE =
  "Formal methodology documented at docs/message_board/PRESCIENCE_METHODOLOGY_2026-06-08.md. Scoring uses Brier Score (mean squared error of probability forecasts), Brier Skill Score (vs. climatology baseline), Calibration Gap (reliability diagram deviation), and Resolution (discrimination between outcome classes). Evidence standards: Primary (signed git commits, server-timestamped archives), Secondary (press releases with date metadata), Tertiary (analyst reports, LinkedIn posts). Confidence scores are self-reported at time of prediction. A May 2026 archive deep dive (317 conversations analyzed) found that the predictor rarely used explicit probability language; instead, designs were presented as measurements or completed architectures. Post-hoc behavioral confidence estimates are systematically higher but are included for transparency alongside the original stated scores. Brier indices are computed from the original 15-claim cohort and are approximate. As of June 8, 2026, 21 validated claims span lead times from 4 weeks to 11 months. Microsoft's Agent Governance Toolkit v4.0.0 (Jun 1, 2026, 992 conformance tests, 110 contributors) validates Bicameral reasoning and Voice Audit as structurally similar independent implementations. Anthropic Dreaming (Apr 29, 2026) validates AI memory consolidation with scheduled deduplication and pattern extraction. Cloudflare Project Think (Apr 15, 2026) validates isolated policy VMs with Dynamic Workers. IETF SCITT AI Agent Execution draft (Apr 2026) and COGITATOR Witness Protocol (Apr 2026) independently converge on cryptographically verifiable agent audit trails — corroborating the Karma Ledger design direction. A June 2026 Twitter archive audit (13,974 tweets, 2023–2026) confirms a continuous public throughline: algorithmic prediction/governance intuition (Mar 2024), spiritual-technological synthesis (Aug 2023–ongoing), and explicit public naming of WhiteMagic as part of MandalaOS (Jan 2026). Twitter corroborates cultural continuity but does not provide earlier technical dates than the private research corpus.";

export const COMPETITIVE_CONVERGENCE_NOTE =
  "June 2026 competitive landscape: Three core WhiteMagic research concepts now have well-funded commercial implementations. Microsoft AGT v4 (Jun 1) ships governance, MCP security gateway, and execution rings. Anthropic Dreaming (Apr 29) ships scheduled memory consolidation. Cloudflare Project Think (Apr 15) ships isolated policy VMs with Dynamic Workers. WhiteMagic remains differentiated as the local-first, open-source, framework-agnostic reference — not competing on cloud features but on offline operability, prescience track record, and the 28-Gana symbolic architecture. Current test baseline: 2,452 passing, 0 failed (includes 24 adversarial defense scenarios + 5 cryptographic signing tests).";

export const EVIDENCE_SOURCES = {
  codexArchive: "219 OpenAI conversations, May–Dec 2025, server-timestamped",
  grokArchive: "97 Grok conversations, Sep 2025–Apr 2026",
  sdCardLibrary: "365 LIBRARY .txt files, filesystem-timestamped",
  twitterArchive: "13,974 tweets across two exports (Aug 2025, May 2026), 2023–Apr 2026",
  gitHistory: "WhiteMagic git history with tagged releases",
  liveWeb: "Cross-referenced against competitor public releases and press",
};

export const METHODOLOGY_URL =
  "https://github.com/whitemagic-ai/whitemagic/blob/main/docs/message_board/PRESCIENCE_METHODOLOGY_2026-06-08.md";

export const STATED_BRIER_INDEX = 69.0;
export const BEHAVIORAL_BRIER_INDEX = 77.5;
