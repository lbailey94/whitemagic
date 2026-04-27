import Link from "next/link";
import { ArrowRight, ExternalLink, FileText, Calendar, Mail } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "Grants & Fellowships — WhiteMagic Labs",
  description:
    "Non-dilutive funding and research affiliations that fit the lab posture. Open applications, no founder-mode visibility required.",
};

interface Opportunity {
  name: string;
  org: string;
  amount: string;
  deadline: string;
  fit: string;
  link: string;
  notes?: string;
}

const ACTIVE: Opportunity[] = [
  {
    name: "AI Governance Grants",
    org: "Open Philanthropy",
    amount: "$50K–$500K",
    deadline: "Rolling",
    fit: "Direct fit: technical governance infrastructure (Karma Ledger, Dharma Rules, Voice Audit). Accepts independent researchers and labs.",
    link: "https://www.openphilanthropy.org/how-to-apply/",
    notes: "Strongest fit for the governance substrate work. No equity. Can apply as 'WhiteMagic Labs'.",
  },
  {
    name: "Long Now Research Fellowships",
    org: "Long Now Foundation",
    amount: "$10K–$40K",
    deadline: "Annual (check site)",
    fit: "Philosophical infrastructure with 10,000-year framing. MandalaOS / cognitive-architecture longevity maps cleanly.",
    link: "https://longnow.org/",
    notes: "Credibility signal for regulated buyers. Stipend + public talk requirement.",
  },
  {
    name: "SBIR Phase I",
    org: "NSF / DoD / NIH",
    amount: "~$275K",
    deadline: "Periodic solicitations",
    fit: "EU AI Act compliance tooling, audit substrate for agentic systems. No equity. US-incorporated required.",
    link: "https://www.sbir.gov/",
    notes: "Requires a lightweight LLC or S-Corp. High effort, but non-dilutive and government-validating.",
  },
  {
    name: "External Research Grants",
    org: "Anthropic / OpenAI / DeepMind",
    amount: "$25K–$150K",
    deadline: "Rolling / quarterly",
    fit: "Constitutional AI, interpretability, agent safety. Karma Ledger side-effect auditing is a direct pitch.",
    link: "https://www.anthropic.com/research",
    notes: "Requires a published paper or strong prior-art documentation. Do after arxiv preprint.",
  },
  {
    name: "EA Infrastructure Fund",
    org: "Centre for Effective Altruism",
    amount: "$5K–$100K",
    deadline: "Quarterly",
    fit: "Open-source governance tooling with broad externalities. Accepts pseudonymous / lab-named applications.",
    link: "https://www.effectivealtruism.org/",
  },
  {
    name: "Manifund Regrants",
    org: "Manifund",
    amount: "$5K–$50K",
    deadline: "Rolling",
    fit: "Prediction-market-shaped grants for speculative research. Good for the LoCoMo benchmark run or polyglot acceleration work.",
    link: "https://manifund.org/",
    notes: "Fast decision cycle (~2–4 weeks). Good for smaller, scoped experiments.",
  },
];

const PENDING: Opportunity[] = [
  {
    name: "Schmidt Sciences AI2050",
    org: "Schmidt Sciences",
    amount: "Up to $300K",
    deadline: "Annual CFP (watch site)",
    fit: "Civilization-scale AI infrastructure. The MandalaOS / WhiteMagic stack fits the 'public interest' framing.",
    link: "https://www.schmidtsciences.org/",
    notes: "Highly competitive. Apply only after at least one citable paper is live.",
  },
  {
    name: "Survival and Flourishing Fund",
    org: "SFF",
    amount: "$10K–$200K",
    deadline: "Invitation-only mostly",
    fit: "Long-term governance and coordination infrastructure. Requires a warm intro or strong public signal.",
    link: "https://survivalandflourishing.fund/",
    notes: "Best approached through a referral from an existing grantee or researcher.",
  },
];

export default function GrantsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Funding"
        title="Grants & Fellowships"
        lede="Non-dilutive income that doesn't require founder-mode visibility. Most of these accept lab-named or pseudonymous applications."
      />

      <section className="container-site pb-12">
        <div className="mx-auto max-w-3xl">
          <div className="mb-8 rounded-xl border border-border-light bg-surface-alt p-6">
            <h2 className="mb-2 font-head text-lg font-semibold text-ink">
              How this page works
            </h2>
            <p className="text-sm text-muted">
              This is a living list of funding sources that fit the
              research-practitioner shape — not VC, not revenue, just runway
              for rigorous artifact publication. Each entry includes amount,
              deadline, fit rationale, and a direct link. I update this as
              deadlines pass and new CFPs open.
            </p>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Active applications — ready now
            </h2>
            <div className="space-y-4">
              {ACTIVE.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Pending — apply after paper / benchmark
            </h2>
            <div className="space-y-4">
              {PENDING.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border-light bg-surface-alt p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">
              Need a template?
            </h2>
            <p className="mb-4 text-sm text-muted">
              Most of these funders want the same three things: (1) a concise
              problem statement, (2) evidence you can ship (code, tests,
              docs), and (3) a clear theory of change. WhiteMagic already has
              (2) in spades. I keep a private grant-application template that
              maps each funder's intake form to our existing artifacts.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/contact" className="btn-primary">
                <Mail className="mr-2 h-4 w-4" />
                Request the template
              </Link>
              <Link href="/pricing" className="btn-secondary">
                See consultancy tiers
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function OpportunityCard({ opp }: { opp: Opportunity }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-5 transition hover:border-lavender/60">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-head text-base font-semibold text-ink">
          {opp.name}
        </h3>
        <span className="font-mono text-xs uppercase tracking-wider text-lavender">
          {opp.amount}
        </span>
      </div>
      <p className="mb-3 text-sm text-muted">
        <span className="font-medium text-fg">{opp.org}</span> · Deadline:{" "}
        {opp.deadline}
      </p>
      <p className="mb-3 text-sm leading-relaxed text-muted">
        <span className="font-medium text-fg">Fit:</span> {opp.fit}
      </p>
      {opp.notes && (
        <p className="mb-3 text-sm leading-relaxed text-muted">
          <span className="font-medium text-fg">Notes:</span> {opp.notes}
        </p>
      )}
      <a
        href={opp.link}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center text-sm font-medium text-lavender hover:underline"
      >
        Apply
        <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
      </a>
    </article>
  );
}
