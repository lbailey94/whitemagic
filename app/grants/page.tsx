import Link from "next/link";
import { ArrowRight, ExternalLink, Calendar, Mail, Clock } from "lucide-react";
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
  badge?: "rolling" | "theme" | null;
}

const CURRENT: Opportunity[] = [
  {
    name: "Regrant Program",
    org: "Manifund",
    amount: "$5K–$50K",
    deadline: "Rolling",
    fit: "Fast, flexible grants for AI safety infrastructure and governance research. Ideal for scoped validation work such as benchmark harnesses, preprints, and mechanistic studies.",
    link: "https://manifund.org/",
    badge: "rolling",
  },
  {
    name: "Long-Term Future Fund (LTFF)",
    org: "EA Funds",
    amount: "$5K–$100K",
    deadline: "Rolling",
    fit: "Open-source governance infrastructure for multi-agent AI safety. Accessible to individual researchers without institutional affiliation.",
    link: "https://funds.effectivealtruism.org/apply-for-funding",
    badge: "rolling",
  },
  {
    name: "AI for Science & Safety Nodes",
    org: "Foresight Institute",
    amount: "$10K–$100K",
    deadline: "Last day of every month",
    fit: "Decentralized & Cooperative AI and AI for Security focus areas. Strong preference for in-person hub engagement in San Francisco or Berlin.",
    link: "https://foresight.org/grants/grants-ai-for-science-safety/",
    badge: "rolling",
  },
  {
    name: "Navigating Transformative AI Grants",
    org: "Coefficient Giving",
    amount: "$50K–$500K",
    deadline: "Rolling",
    fit: "Technical governance infrastructure for frontier AI. Independent researchers and labs are eligible.",
    link: "https://www.openphilanthropy.org/how-to-apply/",
    badge: "rolling",
  },
];

const PLANNED: Opportunity[] = [
  {
    name: "S-Process Theme Round — Human-AI Co-Intelligence",
    org: "Survival and Flourishing Fund (SFF)",
    amount: "$50K–$200K",
    deadline: "July 8, 2026",
    fit: "Cognitive infrastructure for human-AI co-intelligence. Requires supplemental application in addition to the rolling application.",
    link: "https://survivalandflourishing.fund/2026/application",
    badge: "theme",
  },
  {
    name: "S-Process Theme Round — Climate Change",
    org: "Survival and Flourishing Fund (SFF)",
    amount: "$50K–$200K",
    deadline: "June 10, 2026",
    fit: "Evaluate only if a concrete climate-AI use case emerges.",
    link: "https://survivalandflourishing.fund/2026/application",
    badge: "theme",
  },
  {
    name: "AI2050",
    org: "Schmidt Sciences",
    amount: "Up to $300K",
    deadline: "Annual CFP (watch site)",
    fit: "Civilization-scale AI infrastructure. Best pursued after at least one citable paper is published.",
    link: "https://www.schmidtsciences.org/",
    badge: null,
  },
  {
    name: "Long Now Research Fellowships",
    org: "Long Now Foundation",
    amount: "$10K–$40K",
    deadline: "Annual (check site)",
    fit: "Philosophical infrastructure with long-term framing.",
    link: "https://longnow.org/",
    badge: null,
  },
  {
    name: "SBIR Phase I — Trustworthy AI Memory Systems",
    org: "National Science Foundation (NSF)",
    amount: "$256K (6 months)",
    deadline: "Rolling via SBIR.gov",
    fit: "NSF's Safe Learning-Enabled Systems funds runtime verification. Phase II scales to $1M.",
    link: "https://www.nsf.gov/eng/iip/sbir/",
    badge: null,
  },
  {
    name: "SBIR Phase I — Energy-Efficient Edge Compute",
    org: "U.S. Department of Energy (DOE)",
    amount: "~$200K (6–12 months)",
    deadline: "Next solicitation: Q3 2026",
    fit: "Self-optimizing, energy-aware AI substrate for low-power edge compute.",
    link: "https://www.energy.gov/sbir",
    badge: null,
  },
  {
    name: "REAP — Rural Energy Infrastructure",
    org: "U.S. Department of Agriculture (USDA)",
    amount: "Up to $1M (25–50% cost share)",
    deadline: "Annual cycles (apply May 2027 after baseline)",
    fit: "Rural energy infrastructure with 12-month baseline requirement.",
    link: "https://www.rd.usda.gov/programs-services/energy-programs",
    badge: null,
  },
];

const PAST: Opportunity[] = [
  {
    name: "Astra Fellowship",
    org: "Constellation Institute",
    amount: "$8,400/mo + $15K/mo compute",
    deadline: "May 3, 2026 — CLOSED",
    fit: "5-month in-person fellowship for AI safety researchers.",
    link: "https://constellation.org/programs/astra",
    badge: null,
  },
  {
    name: "Generator Residency",
    org: "Constellation × Kairos",
    amount: "$6K/mo + housing + travel",
    deadline: "April 27, 2026 — CLOSED",
    fit: "3-month residency for builders and operators.",
    link: "https://generatorresidency.org/",
    badge: null,
  },
  {
    name: "MATS Research Fellowship",
    org: "MATS",
    amount: "Stipend + compute",
    deadline: "Summer 2026 cohort — CLOSED",
    fit: "Technical AI safety research mentorship program.",
    link: "https://www.matsprogram.org/",
    badge: null,
  },
  {
    name: "ARENA",
    org: "AI Safety Foundations",
    amount: "Stipend + compute",
    deadline: "Cohort 8.0 — CLOSED",
    fit: "Technical upskilling program for AI safety researchers.",
    link: "https://www.arena.education/",
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
              <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 font-medium text-green-700">
                <Clock className="mr-1 h-3 w-3" />
                Rolling / Open
              </span>
              <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 font-medium text-blue-700">
                <Calendar className="mr-1 h-3 w-3" />
                Theme / Planned
              </span>
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink flex items-center gap-2">
              <Clock className="h-5 w-5 text-green-500" />
              Current — open or rolling
            </h2>
            <div className="space-y-4">
              {CURRENT.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-500" />
              Planned — future cycles
            </h2>
            <div className="space-y-4">
              {PLANNED.map((o) => (
                <OpportunityCard key={o.name} opp={o} />
              ))}
            </div>
          </div>

          <div className="mb-10">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Past — closed for 2026
            </h2>
            <div className="space-y-4 opacity-70">
              {PAST.map((o) => (
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
