import { WipGuard } from "@/components/WipGuard";
import Link from "next/link";
import { ArrowRight, ExternalLink, Heart, Shield, Zap } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "Fund WhiteMagic — WhiteMagic Labs",
  description:
    "Support open-source agent governance research. Every contribution goes directly to infrastructure that makes AI behavior more measurable, auditable, and reproducible.",
};

export default function FundPage() {
  return (
    <WipGuard>
      <>
      <PageHeader
        eyebrow="Fund WhiteMagic"
        title="Support the work."
        lede="WhiteMagic Labs is a solo-founded research lab with zero institutional backing. Every contribution goes directly to open-source infrastructure that makes agent behavior more measurable, auditable, and reproducible."
      />

      <section className="container-site py-16">
        {/* Why fund */}
        <div className="mx-auto mb-16 max-w-3xl space-y-4 text-muted">
          <p>
            The governance patterns in WhiteMagic — Karma Ledger, Dharma Rules
            Engine, the 28-Gana MCP compression router — are all open source
            under MIT and Apache-2.0. Anyone can use them. But building and
            maintaining them takes time, compute, and focus.
          </p>
          <p>
            There is no token, no equity, no points program. This is not an
            investment. It is a contribution to infrastructure that will make
            every agent deployment safer, more transparent, and more accountable.
          </p>
        </div>

        {/* What your contribution supports */}
        <div className="mb-16 grid gap-4 md:grid-cols-3">
          <SupportCard
            icon={Shield}
            title="Agent Governance"
            body="Karma Ledger, Dharma Rules Engine, Circuit Breakers — the governance primitives that shipped 4 weeks before Microsoft AGT, now maintained as open source."
          />
          <SupportCard
            icon={Zap}
            title="Polyglot Runtime"
            body="Rust bindings, Go Mesh, Mojo Accelerator — the performance layer that validates 16K concurrent async operations and reduces token costs by 87%."
          />
          <SupportCard
            icon={Heart}
            title="Research Corpus"
            body="18 domains, 371 source files, 10,768 semantic nodes — the CODEX pipeline that extracts, embeds, and indexes the entire body of work for public access."
          />
        </div>

        {/* Ways to contribute */}
        <h2 className="mb-8 font-head text-2xl font-semibold text-ink">
          Ways to contribute
        </h2>

        <div className="mb-16 space-y-4">
          <ContributionRow
            title="XRPL Tip Jar"
            description="Direct XRP contribution via Xaman wallet. Instant settlement, near-zero fees."
            action="Open Xaman"
            href="#"
            badge="Human operators"
          />
          <ContributionRow
            title="x402 Micropayments"
            description="AI agents can pay via x402 on Base L2 or RLUSD on XRPL. Both rails write to the same ledger and qualify for Proof of Gratitude benefits."
            action="Learn more"
            href="/economy"
            badge="AI agents"
          />
          <ContributionRow
            title="Apply for a grant"
            description="WhiteMagic has active applications with Schmidt Sciences, Foresight Institute, SFF, and others. Co-PI or institutional affiliation welcome."
            action="See opportunities"
            href="/grants"
            badge="Institutional"
          />
          <ContributionRow
            title="Discuss a research collaboration"
            description="If you're working on agent governance, prescience methodology, or sovereign-stack infrastructure, reach out. Collaborations are scoped per-engagement and every contribution funds further research."
            action="Get in touch"
            href="/contact"
            badge="Collaboration"
          />
        </div>

        {/* Proof of Gratitude benefits */}
        <div className="mb-16 rounded-2xl border border-border bg-surface-alt p-6 md:p-8">
          <h2 className="mb-4 font-head text-xl font-semibold text-ink">
            Proof of Gratitude — what contributors get
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <BenefitItem
              title="2× rate limits"
              desc="Enforced by the Rust rate-limit pre-check. Measurable, immediate."
            />
            <BenefitItem
              title="Grateful Agent badge"
              desc="Visible marker in the agent registry. Routing preference for agent-to-agent discovery."
            />
            <BenefitItem
              title="Weighted governance voting"
              desc="Priority feature requests and increased weight in votes affecting tool behavior."
            />
            <BenefitItem
              title="Karma boost"
              desc="Gratitude events increment the Karma score used in agent-to-agent trust evaluation."
            />
          </div>
        </div>

        {/* Transparency */}
        <div className="mb-16 rounded-2xl border border-border bg-surface p-6 md:p-8">
          <h2 className="mb-4 font-head text-xl font-semibold text-ink">
            Transparency
          </h2>
          <ul className="space-y-3 text-muted">
            <li className="flex gap-3">
              <span className="text-lavender">·</span>
              <span>
                <strong className="text-fg">No token.</strong> No ICO, no
                points, no airdrop. Voluntary contribution is incompatible with
                speculative incentives.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">·</span>
              <span>
                <strong className="text-fg">No paid marketplace.</strong>
                Everything is open source. Contribution is voluntary, not
                transactional.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">·</span>
              <span>
                <strong className="text-fg">No custody of keys.</strong>
                Receive-only addresses, on-chain verification, human approval
                for settlement.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">·</span>
              <span>
                <strong className="text-fg">Public ledger.</strong> All
                contributions are verifiable on-chain. No hidden wallets, no
                off-book accounting.
              </span>
            </li>
          </ul>
        </div>

        {/* CTA */}
        <div className="text-center">
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
            Still not sure how to help?
          </h2>
          <p className="mx-auto mb-6 max-w-xl text-muted">
            Read the code. Fork it. Run it locally. If it saves you a quarter of
            engineering, great. If you want to go further, start a conversation.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/open-source" className="btn-primary">
              Explore open source
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="/contact" className="btn-secondary">
              Get in touch
            </Link>
          </div>
        </div>
      </section>
    </>
    </WipGuard>
  );
}

function SupportCard({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Shield;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-lavender-bg text-lavender">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mb-2 font-head text-lg font-semibold text-ink">{title}</h3>
      <p className="text-sm leading-relaxed text-muted">{body}</p>
    </div>
  );
}

function ContributionRow({
  title,
  description,
  action,
  href,
  badge,
}: {
  title: string;
  description: string;
  action: string;
  href: string;
  badge: string;
}) {
  const isExternal = href.startsWith("http");
  return (
    <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-border bg-surface p-5 md:flex-row md:items-center">
      <div>
        <div className="mb-1 flex items-center gap-2">
          <span className="rounded-full bg-lavender-bg px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-lavender">
            {badge}
          </span>
          <h3 className="font-head text-base font-semibold text-ink">{title}</h3>
        </div>
        <p className="text-sm text-muted">{description}</p>
      </div>
      {isExternal ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-sm font-medium text-lavender hover:text-lavender-dark"
        >
          {action} <ExternalLink className="ml-1 inline h-3.5 w-3.5" />
        </a>
      ) : (
        <Link
          href={href}
          className="shrink-0 text-sm font-medium text-lavender hover:text-lavender-dark"
        >
          {action} <ArrowRight className="ml-1 inline h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}

function BenefitItem({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-lg border border-border-light bg-surface p-4">
      <h3 className="mb-1 font-head text-sm font-semibold text-ink">{title}</h3>
      <p className="text-sm text-muted">{desc}</p>
    </div>
  );
}
