import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Heart, Gift, ArrowRight } from "lucide-react";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Economy — WhiteMagic",
  description: "WhiteMagic's gratitude economy: free and open source (MIT). Voluntary contributions. No paywalls, no telemetry, no API keys. Support the work if it helps you.",
};

export default function EconomyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Economy"
        title="Free as in freedom. Funded by gratitude."
        lede="WhiteMagic is MIT-licensed and free to use. No SaaS tier, no telemetry, no API keys. If it helps you build something, you can support the work — or not. No gatekeeping."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-3xl">
          {/* The model */}
          <div className="mb-12 rounded-xl border border-border bg-surface p-8">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">The economic model</h2>
            <div className="grid gap-6 md:grid-cols-3">
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Gift className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Free</h3>
                </div>
                <p className="text-sm text-muted">
                  {WM_FACTS.callableTools} tools. {WM_FACTS.memories} memories. {WM_FACTS.testsPassing} tests. MIT-licensed. pip install whitemagic[mcp]. No strings.
                </p>
              </div>
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Heart className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Gratitude</h3>
                </div>
                <p className="text-sm text-muted">
                  Voluntary contributions via GitHub Sponsors, PayPal, or crypto. No tiers, no perks, no gatekeeping.
                </p>
              </div>
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <ArrowRight className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Enterprise</h3>
                </div>
                <p className="text-sm text-muted">
                  Custom deployment, integration, and support available. Contact directly. No SLA templates, just real work.
                </p>
              </div>
            </div>
          </div>

          {/* Why not SaaS */}
          <div className="mb-12">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Why not SaaS?</h2>
            <div className="space-y-4 text-muted">
              <p>
                WhiteMagic is local-first. Your AI's memory lives on your machine, not in our cloud.
                A SaaS model would require us to host your data — which defeats the entire premise.
              </p>
              <p>
                The techniques in WhiteMagic (holographic memory, Dharma governance, citta stream)
                are research outputs. They should be available to everyone, not gated behind a
                subscription. MIT license ensures that.
              </p>
              <p>
                If you need help deploying, integrating, or customizing WhiteMagic for your
                use case, that's where enterprise engagement comes in. The code is free;
                the expertise is not.
              </p>
            </div>
          </div>

          {/* Funding channels */}
          <div className="mb-12">
            <h2 className="mb-6 font-head text-2xl font-semibold text-ink">Support the work</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <a
                href="https://github.com/sponsors/lbailey94"
                className="group rounded-xl border border-border bg-surface p-6 transition hover:border-lavender"
              >
                <h3 className="mb-2 font-head text-lg font-semibold text-ink">GitHub Sponsors</h3>
                <p className="text-sm text-muted">Recurring or one-time. Directly supports development.</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-lavender">
                  Sponsor → <ArrowRight className="h-3 w-3" />
                </span>
              </a>
              <Link
                href="/fund"
                className="group rounded-xl border border-border bg-surface p-6 transition hover:border-lavender"
              >
                <h3 className="mb-2 font-head text-lg font-semibold text-ink">Other channels</h3>
                <p className="text-sm text-muted">PayPal, crypto, and other ways to support.</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-lavender">
                  See all options → <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
            </div>
          </div>

          {/* CTA */}
          <div className="rounded-xl border border-border-light bg-surface-alt p-8 text-center">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">Use it first. Pay if it helps.</h2>
            <p className="mb-6 text-sm text-muted">
              No demos, no sales calls, no "book a meeting to see pricing." Install it. Try it. If it works for you, support the work.
            </p>
            <Link href="/mcp-bridge" className="btn-primary">Get Started →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
