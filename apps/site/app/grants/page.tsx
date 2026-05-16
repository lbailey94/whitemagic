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
    name: "Science of Trustworthy AI RFP (Tier 1)",
    org: "Schmidt Sciences",
    amount: "Up to $1M (1–3 years)",
    deadline: "May 17, 2026",
    fit: "Strong fit for Aims 2 & 3: Karma Ledger is a 'model organism for evaluation science' with construct validity (side-effect fidelity measurement). Dharma Rules Engine provides generalizable interventions (LOG → TAG → WARN → THROTTLE → BLOCK). Bicameral Reasoner + Voice Audit address multi-agent oversight.",
    link: "https://schmidtsciences.smapply.io/prog/science_of_trustworthy_ai_rfp_2026/",
    notes: "Solo applicants eligible but at a 6–10% win rate. Co-PI or institutional affiliation preferred (15–22%). 10% indirect cost cap. Compute + API credits available from Schmidt.",
    badge: "urgent",
  },
  {
    name: "AI for Science & Safety Nodes",
    org: "Foresight Institute",
    amount: "$10K–$100K",
    deadline: "Last day of every month (target: May 31)",
    fit: "Strong fit for 'Decentralized & Cooperative AI' and 'AI for Security' focus areas. CyberBrain architecture (44K tokens CODEX prior art) + Karma Ledger angle is unique.",
    link: "https://foresight.org/grants/grants-ai-for-science-safety/",
    notes: "Monthly deadlines = iterative application possible. 2-month review. Physical presence in SF/Berlin preferred but remote participation acceptable. Recommended ask: $75K–$125K.",
    badge: "urgent",
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
    name: "Long-Term Future Fund (LTFF)",
    org: "EA Funds / Effective Altruism",
    amount: "$5K–$100K",
    deadline: "Rolling (quarterly decisions)",
    fit: "Open-source governance infrastructure for multi-agent AI safety. Public good framing fits LTFF's hits-based giving model. Funds individuals — no incorporation required.",
    link: "https://funds.effectivealtruism.org/apply-for-funding",
    notes: "Submit via Paperform. Fund managers: Linchuan Zhang, Oliver Habryka, Daniel Eth. Recommendation: $35K ask for Karma Ledger benchmark + Voice Audit validation.",
    badge: "rolling",
  },
  {
    name: "Rapid Grants",
    org: "BlueDot Impact",
    amount: "$50–$10K",
    deadline: "Rolling (~5 working days decision)",
    fit: "Fastest turnaround of any source — BUT eligibility requires BlueDot course alumni / community membership. Currently not in network.",
    link: "https://bluedot.org/programs/rapid-grants",
    notes: "⏸️ SKIP — not in BlueDot network. Reactivate only if eligibility confirmed with zero effort.",
    badge: null,
  },
  {
    name: "Navigating Transformative AI Grants",
    org: "Coefficient Giving (formerly Open Philanthropy)",
    amount: "$50K–$500K",
    deadline: "Rolling",
    fit: "Direct fit for technical governance infrastructure (Karma Ledger, Dharma Rules, Voice Audit). Accepts independent researchers and labs.",
    link: "https://www.openphilanthropy.org/how-to-apply/",
    notes: "Activate after first credibility signal (Manifund/Foresight win). Cold applications rarely funded.",
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
    name: "SBIR Phase I — Trustworthy AI Memory Systems",
    org: "National Science Foundation (NSF)",
    amount: "$256K (6 months)",
    deadline: "Rolling via SBIR.gov",
    fit: "NSF's 'Safe Learning-Enabled Systems' funds runtime verification. Karma Ledger + PRAT are novel. Phase II scales to $1M. LLC + SAM.gov required.",
    link: "https://www.nsf.gov/eng/iip/sbir/",
    notes: "⚠️ NSF project pitches currently paused (Apr 2026). Monitor reopening. Draft proposal in background.",
    badge: null,
  },
  {
    name: "SBIR Phase I — Energy-Efficient Edge Compute",
    org: "U.S. Department of Energy (DOE)",
    amount: "~$200K (6–12 months)",
    deadline: "Next solicitation: Q3 2026",
    fit: "Self-optimizing, energy-aware AI substrate for low-power edge compute. WhiteMagic's tiered memory + local-first architecture is a good match.",
    link: "https://www.energy.gov/sbir",
    notes: "LLC + SAM.gov required. Phase II scales to $1.1M. Draft proposal now; submit at next solicitation window.",
    badge: null,
  },
  {
    name: "REAP — Rural Energy Infrastructure",
    org: "U.S. Department of Agriculture (USDA)",
    amount: "Up to $1M (25–50% cost share)",
    deadline: "Annual cycles (apply May 2027 after baseline)",
    fit: "40–60% win rate with certified energy audit + 12-month baseline. Funds solar/battery/microgrid infrastructure.",
    link: "https://www.rd.usda.gov/programs-services/energy-programs",
    notes: "Start energy monitoring Day 1. Requires 12-month baseline data + certified energy audit ($500–$2K). Apply after baseline established.",
    badge: null,
  },
  {
    name: "SBIR Phase I — General",
    org: "NSF / DoD / NIH",
    amount: "~$275K",
    deadline: "Periodic solicitations",
    fit: "Broad SBIR pipeline — backup for DOE/NSF-specific solicitations.",
    link: "https://www.sbir.gov/",
    notes: "Requires LLC + SAM.gov registration. High effort, long timeline (6–12 months), transformative capital if won.",
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
