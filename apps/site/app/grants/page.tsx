import Link from "next/link";
import { ArrowRight, ExternalLink, FileText, Calendar, Mail, AlertTriangle, Clock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "Grants & Fellowships — WhiteMagic Labs",
  description:
    "Non-dilutive funding and research affiliations that fit the lab posture. Verified deadlines, direct application links, and fit assessments updated weekly.",
};

interface Opportunity {
  name: string;
  org: string;
  amount: string;
  deadline: string;
  fit: string;
  link: string;
  notes?: string;
  badge?: "urgent" | "rolling" | "theme" | null;
}

const URGENT: Opportunity[] = [
  {
    name: "Science of Trustworthy AI RFP",
    org: "Schmidt Sciences",
    amount: "$300K–$1M (Tier 1)",
    deadline: "May 17, 2026 (11:59pm AoE)",
    fit: "Direct fit for Aim 2 (measurements & interventions) and Aim 3 (oversight / multi-agent). Karma Ledger = runtime measurement of declared-vs-actual side-effects. Bicameral Reasoner + Voice Audit = oversight under capability gaps.",
    link: "https://www.schmidtsciences.org/opportunity/2026-science-of-trustworthy-ai-rfp/",
    notes: "Tier 1 is feasible for a solo PI with strong prior art. Tier 2 requires multi-PI collaboration. Indirect costs ≤10%. Webinars recorded (Mar 11, Apr 15).",
    badge: "urgent",
  },
  {
    name: "AI for Science & Safety Nodes",
    org: "Foresight Institute",
    amount: "$10K–$100K",
    deadline: "Last day of every month (next: Apr 30 / May 31)",
    fit: "Strong fit for 'Decentralized & Cooperative AI' and 'AI for Security' focus areas. Karma Ledger provides verifiable agent identity chains; Dharma Rules enforce cooperative boundaries.",
    link: "https://foresight.org/grants/grants-ai-for-science-safety/",
    notes: "Monthly deadlines = iterative application possible. Physical presence in SF/Berlin preferred but remote participation acceptable. Review time ~2 months.",
    badge: "rolling",
  },
];

const ACTIVE: Opportunity[] = [
  {
    name: "Rolling Application — Main & Freedom Tracks",
    org: "Survival and Flourishing Fund (SFF)",
    amount: "$50K–$200K",
    deadline: "Rolling (submissions after Apr 22 deferred to next round, likely 2027)",
    fit: "Freedom Track is an excellent fit: locally-runnable, vendor-neutral governance substrate preserves user sovereignty and prevents authority concentration. Default open-source IP policy (MIT + CC-BY) already matches ours.",
    link: "https://survivalandflourishing.fund/rolling-application",
    notes: "Requires incorporation or fiscal sponsor (SFF does not fund individuals directly). Auto-submits Speculation Grant request (95%+ approval). S-Process evaluation takes 6–8 months.",
    badge: "rolling",
  },
  {
    name: "Regrant Program",
    org: "Manifund",
    amount: "$5K–$50K",
    deadline: "Rolling",
    fit: "Fast, flexible, personal decisions by regrantors. Ideal for scoped validation work: LoCoMo benchmark, arxiv preprint, or Voice Audit mechanistic study.",
    link: "https://manifund.org/",
    notes: "Target regrantors: Joel Becker (AI safety infrastructure), Neel Nanda (interpretability), Gavin Leech (forecasting). Decision in 2–4 weeks. No incorporation required.",
    badge: "rolling",
  },
  {
    name: "Rapid Grants",
    org: "BlueDot Impact",
    amount: "$50–$10K",
    deadline: "Rolling (~5 working days decision)",
    fit: "Removes compute/API bottlenecks for benchmark runs. Fastest turnaround of any source here.",
    link: "https://bluedot.org/programs/rapid-grants",
    notes: "Eligibility: BlueDot course participants, alumni, facilitators, or active community members. Upfront payment by default.",
    badge: "rolling",
  },
  {
    name: "Navigating Transformative AI Grants",
    org: "Coefficient Giving (formerly Open Philanthropy)",
    amount: "$50K–$500K",
    deadline: "Rolling",
    fit: "Direct fit for technical governance infrastructure (Karma Ledger, Dharma Rules, Voice Audit). Accepts independent researchers and labs.",
    link: "https://www.openphilanthropy.org/how-to-apply/",
    notes: "Strongest fit for the governance substrate work. No equity. Can apply as 'WhiteMagic Labs'.",
    badge: "rolling",
  },
];

const DEFERRED: Opportunity[] = [
  {
    name: "S-Process Theme Round — HSEE",
    org: "Survival and Flourishing Fund (SFF)",
    amount: "$50K–$200K",
    deadline: "July 8, 2026",
    fit: "Moderate — requires reframing WhiteMagic as 'cognitive infrastructure for human-AI co-intelligence.' Defer until after Schmidt/Manifund outcomes.",
    link: "https://survivalandflourishing.fund/2026/application",
    notes: "Requires supplemental application in addition to Rolling Application. Cannot apply to multiple theme rounds. Activate by May 15 if Schmidt is rejected.",
    badge: "theme",
  },
  {
    name: "S-Process Theme Round — Climate Change",
    org: "Survival and Flourishing Fund (SFF)",
    amount: "$50K–$200K",
    deadline: "June 10, 2026",
    fit: "Weak — not our lane unless a specific climate-AI use case emerges. Likely skip.",
    link: "https://survivalandflourishing.fund/2026/application",
    notes: "Supplemental application required. Evaluate only if a concrete climate-AI project emerges.",
    badge: "theme",
  },
  {
    name: "AI2050",
    org: "Schmidt Sciences",
    amount: "Up to $300K",
    deadline: "Annual CFP (watch site)",
    fit: "Civilization-scale AI infrastructure. Apply after at least one citable paper is live.",
    link: "https://www.schmidtsciences.org/",
    notes: "Highly competitive. Strengthen application with a LoCoMo benchmark number + arxiv preprint.",
    badge: null,
  },
  {
    name: "Long Now Research Fellowships",
    org: "Long Now Foundation",
    amount: "$10K–$40K",
    deadline: "Annual (check site)",
    fit: "Philosophical infrastructure with 10,000-year framing. MandalaOS / cognitive-architecture longevity maps cleanly.",
    link: "https://longnow.org/",
    notes: "Credibility signal for regulated buyers. Stipend + public talk requirement.",
    badge: null,
  },
  {
    name: "SBIR Phase I",
    org: "NSF / DoD / NIH",
    amount: "~$275K",
    deadline: "Periodic solicitations",
    fit: "EU AI Act compliance tooling, audit substrate for agentic systems. No equity. US-incorporated required.",
    link: "https://www.sbir.gov/",
    notes: "Requires a lightweight LLC or S-Corp. High effort, but non-dilutive and government-validating.",
    badge: null,
  },
];

const WATCHLIST: Opportunity[] = [
  {
    name: "Astra Fellowship",
    org: "Constellation Institute",
    amount: "$8,400/mo + $15K/mo compute",
    deadline: "May 3, 2026 — CLOSED",
    fit: "5-month in-person fellowship for AI safety researchers. 80%+ of first cohort now in full-time AI safety roles.",
    link: "https://constellation.org/programs/astra",
    notes: "Missed deadline. Collect expression of interest for Fall 2026 or Spring 2027 cohorts.",
    badge: null,
  },
  {
    name: "Generator Residency",
    org: "Constellation × Kairos",
    amount: "$6K/mo + housing + travel",
    deadline: "April 27, 2026 — CLOSED",
    fit: "3-month residency for builders/operators. Missed by hours.",
    link: "https://generatorresidency.org/",
    notes: "Collect EOI for future cohorts. Applications closed end-of-day AoE.",
    badge: null,
  },
  {
    name: "MATS Research Fellowship",
    org: "MATS",
    amount: "Stipend + compute",
    deadline: "Summer 2026 cohort — CLOSED",
    fit: "Technical AI safety research mentorship program.",
    link: "https://www.matsprogram.org/",
    notes: "Collect EOI for future cohorts.",
    badge: null,
  },
  {
    name: "ARENA",
    org: "AI Safety Foundations",
    amount: "Stipend + compute",
    deadline: "Cohort 8.0 — CLOSED",
    fit: "Technical upskilling program for AI safety researchers.",
    link: "https://www.arena.education/",
    notes: "Collect EOI for future cohorts.",
    badge: null,
  },
];

export default function GrantsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Funding"
        title="Grants & Fellowships"
        lede="Verified 2026 opportunities with direct application links, deadline badges, and fit assessments. Updated after every research cycle."
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
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 font-medium text-red-700">
                <AlertTriangle className="mr-1 h-3 w-3" />
                Urgent (&lt; 30 days)
              </span>
              <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 font-medium text-green-700">
                <Clock className="mr-1 h-3 w-3" />
                Rolling / Open
              </span>
              <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 font-medium text-blue-700">
                <Calendar className="mr-1 h-3 w-3" />
                Theme / Deferred
              </span>
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Urgent — deadline within 30 days
            </h2>
            <div className="space-y-4">
              {URGENT.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink flex items-center gap-2">
              <Clock className="h-5 w-5 text-green-500" />
              Active — apply now
            </h2>
            <div className="space-y-4">
              {ACTIVE.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-500" />
              Deferred — apply after validation
            </h2>
            <div className="space-y-4">
              {DEFERRED.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Watchlist — closed for 2026
            </h2>
            <div className="space-y-4 opacity-70">
              {WATCHLIST.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border-light bg-surface-alt p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">
              Internal strategy docs
            </h2>
            <p className="mb-4 text-sm text-muted">
              WhiteMagic Labs maintains detailed grant strategy documentation
              including mathematical likelihood estimates, tailored application
              strategies, prerequisite checklists, and fund-usage implications.
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
        <div className="flex items-center gap-2">
          <h3 className="font-head text-base font-semibold text-ink">
            {opp.name}
          </h3>
          {opp.badge === "urgent" && (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              <AlertTriangle className="mr-1 h-3 w-3" />
              Urgent
            </span>
          )}
          {opp.badge === "rolling" && (
            <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              <Clock className="mr-1 h-3 w-3" />
              Rolling
            </span>
          )}
          {opp.badge === "theme" && (
            <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
              <Calendar className="mr-1 h-3 w-3" />
              Theme
            </span>
          )}
        </div>
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
