import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ArrowRight, Users, User, Wrench, Building2 } from "lucide-react";

export const metadata = {
  title: "Workshops — WhiteMagic Labs",
  description:
    "Hands-on AI literacy workshops and done-with-you sessions. From $79 group classes to custom private deployments.",
};

interface Workshop {
  tier: string;
  title: string;
  price: string;
  format: string;
  audience: string;
  outcomes: string[];
  icon: React.ComponentType<{ className?: string }>;
}

const WORKSHOPS: Workshop[] = [
  {
    tier: "Tiers 0–1",
    title: "AI Basics for Busy People",
    price: "$79",
    format: "2-hour group workshop (online or Savannah, GA)",
    audience: "Small business owners, professionals, students",
    outcomes: [
      "Write prompts that actually get useful results",
      "Know which tool to use for which task (ChatGPT vs Claude vs Gemini)",
      "Build a simple AI-assisted workflow for your daily work",
      "Understand privacy basics: what data goes where",
    ],
    icon: Users,
  },
  {
    tier: "Tiers 1–2",
    title: "Prompt Engineering & Workflow Design",
    price: "$79",
    format: "2-hour group workshop",
    audience: "Knowledge workers, marketers, writers, analysts",
    outcomes: [
      "Chain prompts for complex multi-step tasks",
      "Use system prompts to enforce tone and constraints",
      "Build reusable prompt templates for your team",
      "Integrate AI into existing tools (Docs, Sheets, email)",
    ],
    icon: Users,
  },
  {
    tier: "Tier 2–3",
    title: "AI in Your Daily Tools",
    price: "$119",
    format: "3-hour hands-on session",
    audience: "Power users, developers, designers",
    outcomes: [
      "Set up Cursor, Windsurf, or VS Code Copilot for your stack",
      "Use Claude Projects / Custom GPTs for recurring work",
      "Build a personal knowledge base with AI augmentation",
      "Automate repetitive tasks with AI + no-code tools",
    ],
    icon: Users,
  },
  {
    tier: "Tier 3–4",
    title: "Power User Setup Sprint",
    price: "$299",
    format: "1:1 done-with-you (2 hours, online)",
    audience: "Solo operators, founders, technical professionals",
    outcomes: [
      "Install and configure local models (Ollama + your hardware)",
      "Set up a multi-model workflow (local + cloud)",
      "Configure your IDE, terminal, and browser for AI-native work",
      "Leave with a working setup, not just a plan",
    ],
    icon: User,
  },
  {
    tier: "Tier 4–5",
    title: "Agent Builder Intensive",
    price: "$499",
    format: "1:1 done-with-you (half day, online)",
    audience: "Developers, technical founders, AI-curious engineers",
    outcomes: [
      "Build your first MCP server or agent loop",
      "Connect tools to LLMs with structured outputs",
      "Set up observability and cost tracking",
      "Deploy a working agent to your infrastructure",
    ],
    icon: Wrench,
  },
  {
    tier: "Tiers 5–7",
    title: "Custom AI Infrastructure",
    price: "$2,500+",
    format: "Custom engagement (scoping call → proposal → delivery)",
    audience: "Regulated teams, product companies, research labs",
    outcomes: [
      "Private AI deployment on your hardware or VPC",
      "Governance middleware: policy engine, audit, compliance",
      "Multi-agent orchestration with provenance tracking",
      "Documentation and operator handoff",
    ],
    icon: Building2,
  },
];

export default function WorkshopsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Teaching"
        title="Workshops & Sessions"
        lede="Hands-on, no-fluff AI literacy for individuals and small teams. Every session is designed around a concrete outcome: you leave with a skill or a setup, not just inspiration."
      />

      {/* Intro */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl space-y-5 text-muted">
          <p className="leading-relaxed">
            The free AI training wave (Google/Goodwill, Anthropic, SBDC) has
            created millions of people who <em className="text-fg">know AI exists</em>{" "}
            but don&apos;t know how to make it work for their specific situation.
            These workshops bridge that gap.
          </p>
          <p className="leading-relaxed">
            Every workshop is grounded in what I&apos;ve built and validated in
            the open-source WhiteMagic project —{" "}
            <strong className="text-fg">2,243 passing tests</strong>,{" "}
            <strong className="text-fg">18 prescience-validated claims</strong>,
            and a year of living inside this technology full-time. You get a
            guide who has already made the expensive mistakes on his own time.
          </p>
        </div>
      </section>

      {/* Workshop cards */}
      <section className="container-site pb-24">
        <div className="mx-auto max-w-4xl space-y-6">
          {WORKSHOPS.map((w) => {
            const Icon = w.icon;
            return (
              <article
                key={w.title}
                className="rounded-2xl border border-border-light bg-surface p-6 md:p-8"
              >
                <div className="mb-4 flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-surface-alt text-lavender">
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="mb-1 font-mono text-xs uppercase tracking-widest text-lavender">
                      {w.tier}
                    </p>
                    <h3 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
                      {w.title}
                    </h3>
                    <p className="mt-1 text-muted">
                      {w.format} · {w.price}
                    </p>
                  </div>
                </div>

                <div className="mb-5">
                  <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
                    Who it&apos;s for
                  </p>
                  <p className="text-sm leading-relaxed text-muted">
                    {w.audience}
                  </p>
                </div>

                <div>
                  <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
                    What you leave with
                  </p>
                  <ul className="space-y-1.5 text-sm leading-relaxed text-muted">
                    {w.outcomes.map((o, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-lavender">·</span>
                        <span>{o}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border-light bg-surface-alt py-20">
        <div className="container-site mx-auto max-w-3xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            How it works
          </p>
          <h2 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            No pitch decks. No upsell. Just outcomes.
          </h2>
          <div className="space-y-4 text-muted">
            <div className="rounded-lg border border-border-light bg-surface px-5 py-4 text-sm leading-relaxed">
              <strong className="text-fg">1. Book a free 15-minute call.</strong>{" "}
              Tell me where you are, what you do, and what frustrates you about
              AI. I&apos;ll tell you honestly which tier you&apos;re on and
              whether a workshop is the right move.
            </div>
            <div className="rounded-lg border border-border-light bg-surface px-5 py-4 text-sm leading-relaxed">
              <strong className="text-fg">2. Pick your format.</strong>{" "}
              Group workshops run monthly in Savannah/online. 1:1 sprints are
              scheduled around your calendar. Custom engagements start with a
              scoping call and a written proposal.
            </div>
            <div className="rounded-lg border border-border-light bg-surface px-5 py-4 text-sm leading-relaxed">
              <strong className="text-fg">3. Show up with your actual work.</strong>{" "}
              The best sessions use your real tasks, documents, and tools — not
              generic examples. Bring a project you&apos;re stuck on and we&apos;ll
              make AI handle it.
            </div>
            <div className="rounded-lg border border-border-light bg-surface px-5 py-4 text-sm leading-relaxed">
              <strong className="text-fg">4. Leave with working output.</strong>{" "}
              Group workshops: skills + templates + a 30-day action plan. 1:1
              sprints: a configured setup, working code, or deployed agent.
              Custom: documented infrastructure + operator handoff.
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container-site py-20 text-center">
        <h2 className="mb-4 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          Start with a free 15-minute call
        </h2>
        <p className="mx-auto mb-6 max-w-xl text-muted">
          No commitment. I&apos;ll ask about your work, assess your tier, and
          recommend the exact next step — even if that step isn&apos;t one of my
          workshops.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link href="/contact" className="btn-primary">
            Book a free call
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link href="/ladder" className="btn-ghost">
            Take the ladder assessment
          </Link>
        </div>
      </section>
    </>
  );
}
