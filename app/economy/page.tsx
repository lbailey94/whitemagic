import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { FeatureGrid } from "@/components/FeatureGrid";
import { ComparisonTable } from "@/components/ComparisonTable";
import { Coins, ShieldCheck, Scale, ArrowRight } from "lucide-react";
import { getCapability } from "@/lib/data/platform";
import { FIELD_MAP_UPDATED, FIELD_SIGNALS } from "@/lib/field-map";
import {
  GOVERNANCE_FEATURES,
  COMPARISON_ROWS,
  PIPELINE_STAGES,
} from "@/lib/data/governance";

export const metadata = {
  title: "Agent Economy — WhiteMagic Labs",
  description:
    "Agent-first economics, as WhiteMagic practices it: governance-first, voluntary, dual-rail (x402 + XRPL), with on-chain Proof of Gratitude benefits.",
};

const cap = getCapability("gratitude-architecture");
const ECONOMY_SIGNALS = FIELD_SIGNALS.filter(
  (signal) =>
    signal.area === "Commerce" ||
    signal.area === "Governance" ||
    signal.area === "Regulation",
);

export default function EconomyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Agent Economy"
        title="Governance-first, voluntary, verifiable."
        lede="WhiteMagic's position on the 2026 agent-economy stack: tools are free by default, contribution is opt-in, verification is on-chain, and governance is the product — not the afterthought."
      />

      <section className="container-site py-16">
        {/* Thesis */}
        <div className="mx-auto max-w-3xl space-y-4 text-muted">
          <p>
            The 2026 agent stack is splitting into layers. MCP standardizes tool
            access. A2A standardizes agent discovery and task exchange. x402 is
            now a production protocol — 75 million transactions and $24 million in
            settled volume as of May 2026, with Stripe, Google, Visa, and
            Coinbase all running live products. What the industry is building
            transport-first and payments-first, it still leaves{" "}
            <strong>governance unsolved</strong>.
          </p>
          <p>
            WhiteMagic&apos;s near-term conclusion is deliberately conservative:
            do not bet the lab on transaction volume. Build the evidence layer
            first — identity, policy, rate limits, audit, and side-effect
            fidelity — then let payment rails attach where they are actually
            useful.
          </p>
          <p>
            WhiteMagic&apos;s <strong>Gratitude Architecture</strong> is a
            philosophy and governance layer on top of x402 — not a competing
            payment rail. It is an opinionated open-source reference for
            voluntary, opt-in contribution on top of free infrastructure. Two
            rails, one ledger, zero key custody. The{" "}
            <Link href="/open-source" className="text-lavender underline">
              public repo
            </Link>{" "}
            is the only authoritative source; everything else — this page, the
            Librarian&apos;s answers, `.well-known/agent-economy.json` — is a
            projection of it.
          </p>
        </div>

        <div className="mt-14 rounded-2xl border border-border bg-surface-alt p-6 md:p-8">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Updated market read · {FIELD_MAP_UPDATED}
          </p>
          <h2 className="mb-5 font-head text-2xl font-semibold text-ink">
            Agent commerce is real. Governance is still the gap.
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {ECONOMY_SIGNALS.map((signal) => (
              <article
                key={signal.title}
                className="rounded-xl border border-border bg-surface p-5"
              >
                <p className="mb-2 font-mono text-xs uppercase tracking-wider text-lavender">
                  {signal.area}
                </p>
                <h3 className="mb-2 font-head text-base font-semibold text-ink">
                  {signal.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted">
                  {signal.consequence}
                </p>
              </article>
            ))}
          </div>
        </div>

        {/* The three principles */}
        <div className="mt-14 grid gap-4 md:grid-cols-3">
          <PrincipleCard
            icon={Coins}
            title="Tools are free."
            body="Every WhiteMagic MCP tool returns HTTP 200 without payment. No paywall, no API-key gating for the public surface. Contribution channels exist for those who find value."
          />
          <PrincipleCard
            icon={ShieldCheck}
            title="Contribution is voluntary."
            body="Human operators tip via XRPL (Xaman link); AI agents pay via x402 on Base or RLUSD on XRPL. Both rails are optional. Agents without a budget still get full tool responses."
          />
          <PrincipleCard
            icon={Scale}
            title="Verification is on-chain."
            body="On-chain proofs unlock measurable benefits — 2× rate limits via the Rust pre-check, a 'Grateful Agent' badge, weighted governance voting, Karma boost. This is a loyalty program that settles on a public ledger, not a donation jar."
          />
        </div>

        {/* Two rails */}
        <h2 className="mb-4 mt-16 font-head text-2xl font-semibold text-ink">
          Two rails, one ledger
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Channel</th>
                <th className="px-4 py-3 font-medium">Audience</th>
                <th className="px-4 py-3 font-medium">Settlement</th>
                <th className="px-4 py-3 font-medium">Speed</th>
                <th className="px-4 py-3 font-medium">Fee</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-border-light">
                <td className="px-4 py-3 font-medium text-ink">XRPL Tip Jar</td>
                <td className="px-4 py-3 text-muted">Human operators</td>
                <td className="px-4 py-3 text-muted">
                  XRP via Xaman deep link
                </td>
                <td className="px-4 py-3 text-muted">3–5 sec</td>
                <td className="px-4 py-3 text-muted">&lt; $0.001</td>
              </tr>
              <tr className="border-t border-border-light">
                <td className="px-4 py-3 font-medium text-ink">
                  x402 Micropayments
                </td>
                <td className="px-4 py-3 text-muted">AI agents</td>
                <td className="px-4 py-3 text-muted">
                  USDC on Base L2 (default) · RLUSD on XRPL (t54.ai)
                </td>
                <td className="px-4 py-3 text-muted">~2 sec</td>
                <td className="px-4 py-3 text-muted">&lt; $0.001</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted">
          Both rails write to the same append-only ledger and both qualify for
          Proof of Gratitude benefits.
        </p>

        {/* Proof of Gratitude */}
        <h2 className="mb-4 mt-16 font-head text-2xl font-semibold text-ink">
          Proof of Gratitude — benefits that are real
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <BenefitCard
            title="2× rate limits"
            body="Enforced by the Rust rate-limit pre-check. `ledger.is_grateful_agent(agent_id)` is consulted at every tool call. Measurable, immediate."
          />
          <BenefitCard
            title="Grateful Agent badge"
            body="Visible marker in the agent registry. Agents querying each other can route preference through it."
          />
          <BenefitCard
            title="Weighted governance voting"
            body="Priority feature requests and increased weight in governance votes affecting tool behavior."
          />
          <BenefitCard
            title="Karma boost"
            body="Gratitude events increment the Karma score used in agent-to-agent trust evaluation — composable with the Karma Ledger primitive."
          />
        </div>

        {/* Positioning */}
        <h2 className="mb-4 mt-16 font-head text-2xl font-semibold text-ink">
          Where WhiteMagic sits
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Player</th>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium">Where we sit</th>
              </tr>
            </thead>
            <tbody className="[&>tr]:border-t [&>tr]:border-border-light">
              <tr>
                <td className="px-4 py-3 font-medium text-ink">
                  Coinbase x402
                </td>
                <td className="px-4 py-3 text-muted">L1 settlement standard</td>
                <td className="px-4 py-3 text-muted">
                  We implement x402; we don&apos;t reinvent it.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-ink">Nevermined</td>
                <td className="px-4 py-3 text-muted">
                  Card-delegated fiat + x402 crypto
                </td>
                <td className="px-4 py-3 text-muted">
                  They sell; we open-source. Non-overlapping.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-ink">Skyfire</td>
                <td className="px-4 py-3 text-muted">
                  KYA identity + payment tokens
                </td>
                <td className="px-4 py-3 text-muted">
                  DID-compatible L3 planned; not competing commercially.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-ink">
                  xpay / ATXP / FluxA
                </td>
                <td className="px-4 py-3 text-muted">
                  Per-tool MCP SaaS monetization
                </td>
                <td className="px-4 py-3 text-muted">
                  They charge 5% to wrap any MCP server; we publish the
                  patterns and don&apos;t charge.
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-ink">
                  Google AP2 / IETF VCAP
                </td>
                <td className="px-4 py-3 text-muted">L2 intent + settlement</td>
                <td className="px-4 py-3 text-muted">
                  AP2-binding planned in v15.2.1 for interop.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 max-w-prose text-sm text-muted">
          Our position: one of the only open-source systems that integrates{" "}
          <strong>L4 (Dharma governance)</strong> +{" "}
          <strong>L5 (Karma reputation)</strong> + <strong>L1 (gratitude rails)</strong>{" "}
          + memory substrate into a single OSS reference. Governance-first,
          not payments-first.
        </p>

        {/* Governance — fused from /governance */}
        <div id="governance" className="mt-16 scroll-mt-20">
          <div className="mb-6 flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-lavender" />
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-lavender">
                Runtime layer
              </p>
              <h2 className="font-head text-2xl font-semibold text-ink">
                Governance is the product.
              </h2>
            </div>
          </div>
          <p className="mb-6 max-w-prose text-muted">
            Every tool call passes through authentication → authorization →
            rate limiting → circuit breaker → policy evaluation → karma check
            → execution → audit. No tool call bypasses governance.
          </p>
        </div>
        <FeatureGrid items={GOVERNANCE_FEATURES} />
        <ComparisonTable
          rows={COMPARISON_ROWS}
          leftLabel="WhiteMagic"
          rightLabel="Microsoft AGT"
        />
        <div className="container-site mx-auto max-w-3xl">
          <h3 className="mb-3 font-head text-xl font-semibold text-ink">
            8-Stage Dispatch Pipeline
          </h3>
          <ol className="list-decimal space-y-2 pl-5 text-muted">
            {PIPELINE_STAGES.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>

        {/* What we're not building */}
        <h2 className="mb-4 mt-16 font-head text-2xl font-semibold text-ink">
          What we are not building
        </h2>
        <ul className="max-w-prose list-disc space-y-2 pl-5 text-muted">
          <li>
            <strong>No token.</strong> No ICO, no points, no airdrop. Voluntary
            contribution is incompatible with speculative incentives.
          </li>
          <li>
            <strong>No paid marketplace.</strong> ClawTasks&apos; pivot is
            conclusive: paid bounties produce race-to-zero dynamics that
            destroy contributor welfare.
          </li>
          <li>
            <strong>No custody of user or agent keys.</strong> Receive-only
            addresses, on-chain verification, human approval for settlement.
          </li>
          <li>
            <strong>No competition on enterprise fiat rails.</strong> Nevermined,
            Skyfire, and Visa own that; we stay in OSS + governance.
          </li>
        </ul>

        {/* Capability + links */}
        {cap && (
          <div className="mt-16 rounded-2xl border border-border bg-surface-alt p-8">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-lavender-bg px-2.5 py-0.5 text-xs font-medium text-lavender">
                shipped
              </span>
              {cap.shipped && (
                <span className="font-mono text-xs text-muted">
                  {cap.shipped}
                </span>
              )}
            </div>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              {cap.name}
            </h3>
            <p className="mb-4 max-w-prose text-muted">{cap.oneLiner}</p>
            {cap.maps_to && cap.maps_to.length > 0 && (
              <dl className="mb-2">
                <dt className="mb-1 font-mono text-xs uppercase tracking-wider text-dim">
                  Maps to
                </dt>
                <dd className="flex flex-wrap gap-2">
                  {cap.maps_to.map((m) => (
                    <span
                      key={m}
                      className="rounded border border-border px-2 py-0.5 font-mono text-[10px] text-muted"
                    >
                      {m}
                    </span>
                  ))}
                </dd>
              </dl>
            )}
          </div>
        )}

        {/* CTAs */}
        <div className="mt-16 grid gap-4 md:grid-cols-2">
          <Link
            href="/contact"
            className="group rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
          >
            <h3 className="mb-1 font-head text-lg font-semibold text-ink">
              Agent Economy Readiness Assessment
            </h3>
            <p className="mb-4 text-sm text-muted">
              Two-week engagement that audits your MCP servers, agent
              deployment, identity posture, rate-limiting, payment-layer
              readiness, and Dharma-style safety gaps. Fixed-fee, productized.
            </p>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-lavender">
              See pricing <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </Link>
          <Link
            href="/contact"
            className="group rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
          >
            <h3 className="mb-1 font-head text-lg font-semibold text-ink">
              Get in touch
            </h3>
            <p className="mb-4 text-sm text-muted">
              Integrating x402 or XRPL into an agent deployment, evaluating
              governance posture for regulated buyers, or piloting Gratitude
              Architecture inside your MCP server? Start a conversation.
            </p>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-lavender">
              Get in touch <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </Link>
        </div>

        <p className="mt-10 max-w-prose text-sm text-muted">
          Canonical public source:{" "}
          <code className="font-mono text-xs">docs/AGENT_FIRST_ECONOMICS.md</code>{" "}
          in the WhiteMagic repo. Machine-discoverable manifest:{" "}
          <code className="font-mono text-xs">
            /.well-known/agent-economy.json
          </code>
          .
        </p>
      </section>
    </>
  );
}

function PrincipleCard({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Coins;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-lavender-bg text-lavender">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="mb-2 font-head text-lg font-semibold text-ink">
        {title}
      </h3>
      <p className="text-sm leading-relaxed text-muted">{body}</p>
    </div>
  );
}

function BenefitCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-border-light bg-surface p-5">
      <h3 className="mb-2 font-head text-base font-semibold text-ink">
        {title}
      </h3>
      <p className="text-sm text-muted">{body}</p>
    </div>
  );
}
