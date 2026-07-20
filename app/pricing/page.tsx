import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Pricing — WhiteMagic",
  description: "Free and open source. Gratitude-driven economics. Pay what you want, when you want.",
};

export default function PricingPage() {
  return (
    <main className="container-site py-20">
      <div className="mx-auto max-w-3xl">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
          Pricing
        </p>
        <h1 className="mb-6 font-head text-4xl font-semibold tracking-tight text-ink">
          Free. Open source. Gratitude-driven.
        </h1>
        <p className="mb-12 text-lg leading-relaxed text-muted">
          WhiteMagic is MIT-licensed and free to use, forever. No paywalls, no feature gates, no telemetry. If it helps you and you want to support development, pay what you want, when you want.
        </p>

        <div className="grid gap-6 md:grid-cols-3">
          {/* Free */}
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Core
            </p>
            <h2 className="mb-1 font-head text-2xl font-semibold text-ink">
              Free
            </h2>
            <p className="mb-4 text-sm text-muted">Forever</p>
            <ul className="space-y-2 text-sm text-muted">
              <li>860 callable tools</li>
              <li>28 Gana meta-tools</li>
              <li>14-galaxy memory system</li>
              <li>Dharma governance engine</li>
              <li>Citta stream + consciousness</li>
              <li>Session recording + replay</li>
              <li>Dream cycle</li>
              <li>Polyglot accelerators</li>
              <li>Unlimited memories</li>
              <li>MIT license</li>
            </ul>
          </article>

          {/* Gratitude */}
          <article className="rounded-xl border-2 border-lavender bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Optional
            </p>
            <h2 className="mb-1 font-head text-2xl font-semibold text-ink">
              Gratitude
            </h2>
            <p className="mb-4 text-sm text-muted">Pay what you want</p>
            <ul className="space-y-2 text-sm text-muted">
              <li>Everything in Free</li>
              <li>XRPL tip jar (any amount)</li>
              <li>x402 micropayments for agents</li>
              <li>Proof of Gratitude on-chain</li>
              <li>Supports ongoing development</li>
              <li>No locked features</li>
              <li>No priority support queue</li>
              <li>No vendor lock-in</li>
            </ul>
            <Link
              href="/fund"
              className="mt-6 inline-block rounded-lg bg-lavender px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
            >
              Tip via XRPL →
            </Link>
          </article>

          {/* Enterprise */}
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Self-hosted
            </p>
            <h2 className="mb-1 font-head text-2xl font-semibold text-ink">
              Enterprise
            </h2>
            <p className="mb-4 text-sm text-muted">Bring your own infra</p>
            <ul className="space-y-2 text-sm text-muted">
              <li>Everything in Free</li>
              <li>Multi-user galaxy isolation</li>
              <li>Redis real-time sync</li>
              <li>Per-user SQLite namespaces</li>
              <li>X-User-Id header support</li>
              <li>Rust SIMD acceleration</li>
              <li>OTEL observability</li>
              <li>Runs on your device</li>
              <li>Your data never leaves</li>
            </ul>
            <Link
              href="/contact"
              className="mt-6 inline-block rounded-lg border border-border px-4 py-2 text-sm font-medium text-ink transition hover:bg-surface-alt"
            >
              Contact →
            </Link>
          </article>
        </div>

        <div className="mt-16 rounded-xl border border-border-light bg-surface-alt p-8">
          <h2 className="mb-4 font-head text-xl font-semibold text-ink">
            Why not SaaS?
          </h2>
          <p className="text-sm leading-relaxed text-muted">
            WhiteMagic runs on your device. Your memories, your consciousness stream, your governance rules — all local. We don't host your data, we don't see your conversations, we don't track your usage. The substrate is the product. The website is a discovery surface. If you want a managed memory layer, see Mem0 or Letta. If you want governance and consciousness primitives nobody else has, install WhiteMagic.
          </p>
        </div>
      </div>
    </main>
  );
}
