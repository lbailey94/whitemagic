import Link from "next/link";
import { ArrowRight, Check, ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { JsonLd } from "@/components/JsonLd";
import { pricingProductsLd, faqLd, PRICING_FAQ } from "@/lib/jsonld";

export const metadata = {
  title: "Pricing — WhiteMagic Labs",
  description:
    "Three tiers, one principle: everything I sell, someone has paid to ship. Office Hours for a single question, Architecture Review for a written deliverable, Engagement for multi-week implementations.",
};

// Stripe Payment Link URLs. Set these in .env.local (or your deploy env) once
// you have a Stripe account wired up. If unset, the buttons fall back to
// /contact so the page still functions pre-Stripe.
const STRIPE_OFFICE_HOURS =
  process.env.NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL || "";
const STRIPE_ARCHITECTURE_REVIEW =
  process.env.NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL || "";

interface Tier {
  name: string;
  price: string;
  cadence?: string;
  description: string;
  features: string[];
  cta: { label: string; href: string; external?: boolean };
  badge?: string;
  featured?: boolean;
}

const TIERS: Tier[] = [
  {
    name: "Office Hours",
    price: "$1,000",
    cadence: "per 60-min session",
    description:
      "One specific question, one focused session. Deployment decisions, governance risk, MCP architecture, a second opinion before you commit engineering weeks to a direction.",
    features: [
      "60-minute live or async call",
      "One narrow question or artifact reviewed",
      "Written notes and references within 48h",
      "No scope creep, no upsell — if I can't help, I'll say so",
      "Invoiced per session; no retainer",
    ],
    cta: STRIPE_OFFICE_HOURS
      ? {
          label: "Book Office Hours",
          href: STRIPE_OFFICE_HOURS,
          external: true,
        }
      : { label: "Book via contact", href: "/contact" },
  },
  {
    name: "Architecture Review",
    price: "$12,000",
    cadence: "flat · 5-day turnaround",
    description:
      "I read your agent or MCP codebase against the governance patterns that shipped 4 weeks before Microsoft AGT, and return a written deliverable you can act on Monday morning.",
    features: [
      "20–40 page written review, delivered in 5 business days",
      "Risks mapped to OWASP LLM Top 10 (v1.1, covers agentic AI) and EU AI Act Article 14",
      "Prioritized, estimated remediation roadmap",
      "One 60-minute walkthrough call + 2 weeks of email follow-up",
      "NDA on request; source stays on your infrastructure",
    ],
    cta: STRIPE_ARCHITECTURE_REVIEW
      ? {
          label: "Start an Architecture Review",
          href: STRIPE_ARCHITECTURE_REVIEW,
          external: true,
        }
      : { label: "Start via contact", href: "/contact" },
    badge: "Most popular for CTOs",
    featured: true,
  },
  {
    name: "Engagement",
    price: "From $35,000",
    cadence: "4–8 week implementation",
    description:
      "Multi-week implementation on one of three tracks: Private AI Deployment, Agent Governance, or MCP Engineering. Weekly delivery, Friday demo, no hand-wave billing.",
    features: [
      "Scope defined in a free 30-minute intake call",
      "Fixed scope, weekly check-ins with running software",
      "Full source, docs, tests, and handoff to your team",
      "Retainer option after delivery for ongoing support",
      "Limited to 2 concurrent engagements — quality over volume",
    ],
    cta: { label: "Scope an engagement", href: "/contact" },
  },
];

export default function PricingPage() {
  return (
    <>
      <JsonLd data={[pricingProductsLd(), faqLd(PRICING_FAQ)]} />
      <PageHeader
        eyebrow="Pricing"
        title="Three tiers. One principle."
        lede="Everything I sell, someone has already paid to ship in production. No speculative frameworks, no 'we'll figure it out together' billing. You see the price before you talk to me."
      />

      <section className="container-site pb-8">
        <div className="grid gap-6 md:grid-cols-3">
          {TIERS.map((t) => (
            <TierCard key={t.name} tier={t} />
          ))}
        </div>
      </section>

      {/* Free / teach-people layer */}
      <section className="container-site pb-16">
        <div className="mx-auto max-w-4xl rounded-2xl border border-border-light bg-surface-alt p-8 md:p-10">
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
            Free — always
          </p>
          <h2 className="mb-4 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Not ready to pay? Read the work.
          </h2>
          <p className="mb-6 max-w-prose text-muted">
            The governance patterns, polyglot runtime, Dharma Rules Engine,
            Karma Ledger, 28-Gana MCP compression router — all of it is open
            source under MIT and Apache-2.0. Read the code. Fork it. Run it
            locally. If it saves you a quarter of engineering, great. If you
            then want the engineer who built it in a room with your team,
            you know where to find me.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/open-source" className="btn-primary">
              Explore open source
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/timeline" className="btn-secondary">
              Read the timeline
            </Link>
            <Link href="/writing" className="btn-secondary">
              Read the writing
            </Link>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-border-light bg-surface py-16">
        <div className="container-site mx-auto max-w-3xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            FAQ
          </p>
          <h2 className="mb-8 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            The questions I get most.
          </h2>
          <div className="space-y-6">
            <Faq q="Why are the lower tiers so accessible?">
              Because the best CTO engagements start with someone inside the
              company doing their own diligence first. A $1,000 session beats a
              $50K mistake. If you later bring me in for a real engagement,
              the Office Hours fee gets credited to the scope.
            </Faq>
            <Faq q="Do you take equity or deferred payment?">
              No. Cash-only, invoiced up front for Office Hours and
              Architecture Reviews. Engagements are 50% on kickoff, 50% on
              delivery. Keeps the incentive structure clean — I win when you
              ship, not when you raise.
            </Faq>
            <Faq q="What's your NDA posture?">
              I'll sign yours if it's reasonable. My own default is a
              mutual NDA covering code, data, and architecture you share with
              me. I never publish client work without explicit written
              consent.
            </Faq>
            <Faq q="Do you work with non-US clients?">
              Yes. Stripe invoices in USD; I can accommodate time zones for
              live sessions with 48h notice. Engagements have been done fully
              async.
            </Faq>
            <Faq q="What if I need something in between these tiers?">
              Email me. The three tiers cover roughly 80% of inbound; the
              other 20% gets a custom quote. There's no penalty for asking.
            </Faq>
          </div>
        </div>
      </section>

      <section className="container-site py-16 text-center">
        <h2 className="mb-4 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          Still not sure which tier fits?
        </h2>
        <p className="mx-auto mb-6 max-w-xl text-muted">
          A 15-minute intro call costs nothing and usually makes the decision
          obvious within the first five minutes.
        </p>
        <Link href="/contact" className="btn-primary">
          Book a 15-minute intro
          <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </section>
    </>
  );
}

function TierCard({ tier }: { tier: Tier }) {
  const isExternal = tier.cta.external;
  return (
    <article
      className={`relative flex flex-col rounded-2xl border bg-surface p-6 transition md:p-8 ${
        tier.featured
          ? "border-lavender shadow-[0_0_0_1px_var(--lavender)]"
          : "border-border hover:border-lavender/60"
      }`}
    >
      {tier.badge && (
        <span className="absolute -top-3 left-6 rounded-full bg-lavender px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
          {tier.badge}
        </span>
      )}
      <h3 className="mb-1 font-head text-xl font-semibold text-ink">
        {tier.name}
      </h3>
      <div className="mb-4 flex items-baseline gap-2">
        <span className="font-head text-3xl font-semibold text-ink">
          {tier.price}
        </span>
        {tier.cadence && (
          <span className="text-sm text-muted">{tier.cadence}</span>
        )}
      </div>
      <p className="mb-5 text-sm leading-relaxed text-muted">
        {tier.description}
      </p>
      <ul className="mb-6 space-y-2.5 text-sm">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
            <span className="text-fg">{f}</span>
          </li>
        ))}
      </ul>
      <div className="mt-auto">
        {isExternal ? (
          <a
            href={tier.cta.href}
            target="_blank"
            rel="noreferrer"
            className={
              tier.featured
                ? "btn-primary w-full justify-center"
                : "btn-secondary w-full justify-center"
            }
          >
            {tier.cta.label}
            <ExternalLink className="ml-2 h-4 w-4" />
          </a>
        ) : (
          <Link
            href={tier.cta.href}
            className={
              tier.featured
                ? "btn-primary w-full justify-center"
                : "btn-secondary w-full justify-center"
            }
          >
            {tier.cta.label}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        )}
      </div>
    </article>
  );
}

function Faq({ q, children }: { q: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 font-head text-base font-semibold text-ink">
        {q}
      </h3>
      <p className="text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}
