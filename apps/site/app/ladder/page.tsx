import Link from "next/link";
import {
  MessageSquare,
  Sparkles,
  Layers,
  Code2,
  Terminal,
  Server,
  Network,
  Crown,
  ArrowRight,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "The AI Capability Ladder — WhiteMagic Labs",
  description:
    "Eight tiers of AI capability, from consumer chatbot use to sovereign multi-agent infrastructure. A diagnostic for teams trying to figure out where they are and where they need to get to.",
};

interface Tier {
  num: number;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  tagline: string;
  looksLike: string;
  signals: string[];
  typicalOrg: string;
  climbTo: string;
  serviceHint?: string;
}

const TIERS: Tier[] = [
  {
    num: 0,
    name: "Accidental User",
    icon: MessageSquare,
    tagline: "Staff type into chat.openai.com when they get stuck.",
    looksLike:
      "Free-tier chatbot use, ungoverned, on personal accounts. No one knows which team is pasting which data where. IT hasn't noticed or has quietly blocked it.",
    signals: [
      "No AI budget line item yet",
      "Procurement hasn't reviewed OpenAI or Anthropic terms",
      "Individual employees using personal ChatGPT accounts on corporate data",
      "No audit trail, no retention policy, no DLP coverage",
    ],
    typicalOrg: "Most SMBs in 2026. Also many Fortune 500 business units whose official AI policy lags actual usage by 18 months.",
    climbTo:
      "Establish baseline governance: acceptable-use policy, approved tooling list, and at minimum a team-licensed plan with data-processing agreements in place.",
  },
  {
    num: 1,
    name: "Sanctioned User",
    icon: Sparkles,
    tagline: "ChatGPT Team / Claude for Work / Copilot rolled out, policies written, training run.",
    looksLike:
      "A licensed plan with zero-retention. A one-page acceptable-use policy. A training deck that 20% of staff actually read. Prompt engineering handled by whoever on the team was already a power user.",
    signals: [
      "Everyone has a corporate AI account",
      "There's a Slack channel for prompt sharing",
      "Usage is uneven: 3 power users, 40 light users, 57 who never logged in",
      "ROI is anecdotal: 'Sarah saved 4 hours on the RFP last week'",
    ],
    typicalOrg: "Mid-market companies 6-12 months into serious AI adoption. Most of US enterprise landed here in 2025-2026.",
    climbTo:
      "Integrate AI into the tools employees already use daily. Stop expecting people to context-switch into a separate chat app.",
  },
  {
    num: 2,
    name: "Integrated User",
    icon: Layers,
    tagline: "AI lives inside Office / Google Workspace / Notion / Slack / Salesforce.",
    looksLike:
      "Copilot in Word and Excel. Gemini in Gmail and Docs. Notion AI generating first drafts. Salesforce Einstein triaging leads. The AI shows up where work happens, not in a separate tab.",
    signals: [
      "AI is a line item in the IT budget, not the innovation budget",
      "Integrations handled by vendors, not internal engineering",
      "Measurable time-savings per workflow (minutes per email, hours per report)",
      "First serious questions about data residency and vendor lock-in",
    ],
    typicalOrg: "Competent mid-market and enterprise, late 2026 onward. Still the leading edge for most SMBs.",
    climbTo:
      "Build leverage beyond what vendors ship. Teach power users to compose their own tooling and start customizing workflows rather than accepting defaults.",
  },
  {
    num: 3,
    name: "Power User / Native Workflow",
    icon: Code2,
    tagline: "AI inside the IDE, the design tool, the notebook. Built-for-purpose, not templated.",
    looksLike:
      "Engineers using Cursor, Windsurf, Claude Code, or Copilot daily. Designers using Figma AI and Adobe Firefly in production. Analysts using NotebookLM or Claude Projects for research loops. Writers using AI-augmented editors (Obsidian, Scrivener, custom markdown pipelines). Custom GPTs and Claude Projects for recurring tasks.",
    signals: [
      "Internal playbooks for specific AI workflows",
      "Measured productivity lift in the 30-60% range for individual contributors",
      "Staff starting to run local models (Ollama, LM Studio) for sensitive tasks",
      "Questions emerging about what to do with data you can't send to a vendor",
    ],
    typicalOrg: "Tech-forward mid-market, AI-native startups, and the best-run divisions inside larger companies.",
    climbTo:
      "Graduate from tool-use to orchestration: connect multiple AI surfaces, automate across them, and start treating AI as infrastructure rather than a productivity app.",
  },
  {
    num: 4,
    name: "Orchestrator",
    icon: Terminal,
    tagline: "CLIs, automated loops, MCP servers, retrieval pipelines. AI as programmable infrastructure.",
    looksLike:
      "Internal teams using Claude Code, Aider, or codex CLI for large refactors. Atlassian MCP, GitHub MCP, Notion MCP, and custom MCP servers exposed to agents. RAG pipelines over company documentation. Scheduled agent runs (cron-style) producing reports, triaging tickets, summarizing meetings overnight.",
    signals: [
      "AI-generated PRs running through code review with measurable acceptance rates",
      "First internal MCP servers exposing proprietary tools to agents",
      "LLM spend moving from $X/user/month to $Y/agent-hour",
      "The question 'which model, which context, which tools' becomes routine engineering",
    ],
    typicalOrg: "AI-native startups past Series A. Technology-forward enterprises with a designated AI platform team.",
    climbTo:
      "Stand up dedicated infrastructure. Move agents off laptops and into always-on, governed environments with audit trails and cost controls.",
  },
  {
    num: 5,
    name: "Deployer",
    icon: Server,
    tagline: "Private AI infrastructure on your hardware or your VPC. Always-on. Auditable. Cost-bounded.",
    looksLike:
      "Self-hosted model-serving (vLLM, llama.cpp, TGI) for sensitive workloads. Private vector stores (pgvector, Qdrant, Weaviate). Discord / Slack / Teams bots backed by your own model endpoints. Long-running autonomous agents surviving process restarts. Per-agent spend caps, DLP on inputs and outputs, SSO-gated tool access.",
    signals: [
      "A real 'AI platform' with its own on-call rotation",
      "Per-team, per-agent, per-capability budgets enforced at runtime",
      "Data never leaves your compliance boundary for the workflows that matter",
      "Incident response runbooks specific to agent failures (hallucinations, tool misuse, runaway loops)",
    ],
    typicalOrg: "Regulated industries (finance, healthcare, legal, gov). Serious AI-native product companies. The mature 5% of enterprise AI programs.",
    climbTo:
      "Formalize governance. Move from 'we have policies' to 'the platform enforces them at runtime, with an audit trail a regulator will accept.'",
    serviceHint: "Private AI Deployment",
  },
  {
    num: 6,
    name: "Architect",
    icon: Network,
    tagline: "Multi-agent systems. Runtime governance. Audit you can show a regulator.",
    looksLike:
      "Specialized agent roles (researcher, writer, reviewer) coordinating via message passing or explicit orchestration. Policy engines enforcing rules at the agent-call boundary, not just at the API gateway. Full karma-style ledgers of what each agent did, intended vs actual side effects, and who approved what. Fine-tuning or LoRA on domain data. Governance mapped to OWASP LLM Top 10 (v1.1, covers agentic AI) and regulatory regimes (EU AI Act, Colorado AI Act, NY SHIELD).",
    signals: [
      "Audit logs are first-class product artifacts, not afterthoughts",
      "Policy changes deploy through the same CI/CD as code",
      "Legal and compliance have seats at the architecture review",
      "The question is no longer 'can we build this' but 'can we prove it meets Article 14'",
    ],
    typicalOrg: "Regulated enterprises post-EU AI Act enforcement. AI infrastructure companies. Well-funded agent-platform startups.",
    climbTo:
      "Own the stack end to end. Bring model serving, memory, governance, and orchestration under your architectural control, not your vendor's.",
    serviceHint: "Agent Governance",
  },
  {
    num: 7,
    name: "Sovereign Operator",
    icon: Crown,
    tagline: "You own the cognition. Your models, your memory, your governance, your economics.",
    looksLike:
      "Custom models (full fine-tune or from scratch) where it matters. Persistent holographic memory across sessions, users, and agents. Multi-tenant isolation at the memory layer, not just the auth layer. Novel agent economics (per-call budgets, karma ledgers, cross-agent attestation). Infrastructure you could operate if every commercial vendor disappeared tomorrow.",
    signals: [
      "You ship research your vendors can't",
      "You run benchmarks your competitors can't reproduce",
      "You have operational answers to questions most teams haven't even asked yet (memory poisoning, cross-agent trust boundaries, physical-world verification)",
      "AI is not a line item — it's a moat",
    ],
    typicalOrg: "A handful of frontier labs, hyperscalers, and the most ambitious AI-native product companies. Also the rare, well-resourced solo operator who built their own stack from first principles.",
    climbTo: "Define the next rung.",
    serviceHint: "MCP Engineering + Private AI Deployment",
  },
];

export default function LadderPage() {
  return (
    <>
      <PageHeader
        eyebrow="Framework"
        title="The AI Capability Ladder"
        lede="Eight tiers, from staff pasting into chat.openai.com to sovereign agent infrastructure. A diagnostic for leaders trying to figure out where their organization is and what it would take to climb."
      />

      {/* Intro frame */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl space-y-5 text-muted">
          <p className="leading-relaxed">
            Most conversations about AI adoption collapse into one of two
            unhelpful shapes. Either{" "}
            <em className="text-fg">&ldquo;we use ChatGPT&rdquo;</em> (at Tier
            0) or{" "}
            <em className="text-fg">
              &ldquo;we&rsquo;re doing agents&rdquo;
            </em>{" "}
            (somewhere between Tiers 3 and 6, nobody quite knows). The ladder
            below is the vocabulary I use with clients to get past that. Each
            tier describes a capability plateau: what it looks like in
            practice, what signals tell you you&rsquo;re there, what it takes
            to climb to the next.
          </p>
          <p className="leading-relaxed">
            Two caveats. First, an organization can be at different tiers for
            different workflows — marketing at Tier 2, engineering at Tier 4,
            regulated compliance pipelines still at Tier 0. The interesting
            question is usually the gap between them, not the average.
            Second, climbing isn&rsquo;t the goal. For a law firm with heavy
            privilege obligations, Tier 5 is the destination and anything
            beyond is over-engineering. For a frontier AI product company,
            Tier 7 is table stakes. Match the rung to the work.
          </p>
          <p className="leading-relaxed">
            My services ({" "}
            <Link
              href="/services/private-ai-deployment"
              className="text-lavender underline-offset-4 hover:underline"
            >
              Private AI Deployment
            </Link>
            ,{" "}
            <Link
              href="/services/agent-governance"
              className="text-lavender underline-offset-4 hover:underline"
            >
              Agent Governance
            </Link>
            ,{" "}
            <Link
              href="/services/mcp-engineering"
              className="text-lavender underline-offset-4 hover:underline"
            >
              MCP Engineering
            </Link>
            ) cover the climb from Tier 4 to Tier 7. Below Tier 4, the right
            move is almost always a vendor product plus a decent policy, not
            a consulting engagement.
          </p>
        </div>
      </section>

      {/* The ladder */}
      <section className="container-site pb-24">
        <div className="mx-auto max-w-4xl space-y-6">
          {TIERS.map((tier) => (
            <TierRow key={tier.num} tier={tier} />
          ))}
        </div>
      </section>

      {/* Self-diagnostic */}
      <section className="border-t border-border-light bg-surface-alt py-20">
        <div className="container-site mx-auto max-w-3xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Self-diagnostic
          </p>
          <h2 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Which rung are you actually on?
          </h2>
          <p className="mb-8 max-w-prose text-muted leading-relaxed">
            Pick the highest tier for which{" "}
            <em className="text-fg">every</em> signal is true of your
            organization today — not your pilot, not your roadmap, not the
            slide in last quarter&rsquo;s board deck. Honest answers only.
          </p>
          <div className="space-y-4 text-muted">
            <DiagRow>
              Are staff pasting into consumer AI accounts with no policy?
              You&rsquo;re at <strong className="text-fg">Tier 0</strong>.
              First move is a sanctioned-tools list, not a platform build.
            </DiagRow>
            <DiagRow>
              Is there a licensed plan with DPA, acceptable-use policy, and
              uneven adoption?{" "}
              <strong className="text-fg">Tier 1</strong>. Focus on
              integration before customization.
            </DiagRow>
            <DiagRow>
              Does AI live inside Office, Workspace, Slack, Salesforce —
              rolled out via vendor integrations?{" "}
              <strong className="text-fg">Tier 2</strong>. Start building
              power-user workflows on top.
            </DiagRow>
            <DiagRow>
              Are engineers using Cursor / Claude Code in production, and do
              you have measurable productivity deltas?{" "}
              <strong className="text-fg">Tier 3</strong>. Ready to think
              about orchestration.
            </DiagRow>
            <DiagRow>
              Do you run MCP servers, agent loops, or scheduled AI jobs with
              measurable cost and quality metrics?{" "}
              <strong className="text-fg">Tier 4</strong>. Ready to move off
              laptops and into platform.
            </DiagRow>
            <DiagRow>
              Is there a named AI platform with on-call, SSO, per-agent
              budgets, and an audit trail?{" "}
              <strong className="text-fg">Tier 5</strong>. This is where my{" "}
              <Link
                href="/services/private-ai-deployment"
                className="text-lavender underline-offset-4 hover:underline"
              >
                Private AI Deployment
              </Link>{" "}
              engagements usually land.
            </DiagRow>
            <DiagRow>
              Can you show a regulator a complete, enforced, auditable chain
              of agent decisions mapped to OWASP LLM Top 10 (v1.1, covers agentic AI)?{" "}
              <strong className="text-fg">Tier 6</strong>. The{" "}
              <Link
                href="/services/agent-governance"
                className="text-lavender underline-offset-4 hover:underline"
              >
                Agent Governance
              </Link>{" "}
              engagement addresses this rung specifically.
            </DiagRow>
            <DiagRow>
              Do you own your cognition end-to-end — models, memory,
              governance, economics — and could you operate it if every
              commercial vendor disappeared?{" "}
              <strong className="text-fg">Tier 7</strong>. You probably
              don&rsquo;t need me; but if you do, it&rsquo;s the most
              interesting engagement on the menu.
            </DiagRow>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container-site py-20 text-center">
        <h2 className="mb-4 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          Not sure which rung you&rsquo;re really on?
        </h2>
        <p className="mx-auto mb-6 max-w-xl text-muted">
          A 60-minute{" "}
          <Link
            href="/pricing"
            className="text-lavender underline-offset-4 hover:underline"
          >
            Office Hours session
          </Link>{" "}
          usually answers it. Bring the architecture diagram, the anxieties,
          and the vendor shortlist. Leave with a written read on where you
          are and what the honest next move is.
        </p>
        <Link href="/contact" className="btn-primary">
          Book a 15-minute intro
          <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </section>
    </>
  );
}

function TierRow({ tier }: { tier: Tier }) {
  const Icon = tier.icon;
  return (
    <article
      className="rounded-2xl border border-border-light bg-surface p-6 md:p-8"
      id={`tier-${tier.num}`}
    >
      <div className="mb-5 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-surface-alt text-lavender">
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="mb-1 font-mono text-xs uppercase tracking-widest text-lavender">
            Tier {tier.num}
          </p>
          <h3 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            {tier.name}
          </h3>
          <p className="mt-2 text-muted">{tier.tagline}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
            What it looks like
          </p>
          <p className="text-sm leading-relaxed text-muted">
            {tier.looksLike}
          </p>
        </div>
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
            Signals you&rsquo;re here
          </p>
          <ul className="space-y-1.5 text-sm leading-relaxed text-muted">
            {tier.signals.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-lavender">·</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6 grid gap-4 border-t border-border-light pt-5 md:grid-cols-[1fr_1fr]">
        <div>
          <p className="mb-1 font-mono text-xs uppercase tracking-widest text-muted">
            Typical org at this tier
          </p>
          <p className="text-sm leading-relaxed text-muted">
            {tier.typicalOrg}
          </p>
        </div>
        <div>
          <p className="mb-1 font-mono text-xs uppercase tracking-widest text-muted">
            To climb
          </p>
          <p className="text-sm leading-relaxed text-muted">{tier.climbTo}</p>
        </div>
      </div>

      {tier.serviceHint && (
        <div className="mt-5 rounded-lg border border-border-light bg-surface-alt px-4 py-3 text-sm text-muted">
          <span className="font-mono text-xs uppercase tracking-widest text-lavender">
            Relevant service
          </span>{" "}
          <span className="text-fg">· {tier.serviceHint}</span>
        </div>
      )}
    </article>
  );
}

function DiagRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border-light bg-surface px-5 py-4 text-sm leading-relaxed">
      {children}
    </div>
  );
}
