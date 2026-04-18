import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AnimatedTriquetra } from "./AnimatedTriquetra";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border-light">
      <div className="container-site grid items-center gap-10 py-20 md:grid-cols-[1.1fr_0.9fr] md:py-28">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <ShieldCheck className="h-3.5 w-3.5 text-lavender" />
            Private AI · on your infrastructure
          </div>
          <h1 className="mb-6 font-head text-4xl font-semibold leading-[1.05] tracking-tight text-ink md:text-6xl">
            Private AI,<br />
            deployed on{" "}
            <span className="text-lavender">your infrastructure</span>.
          </h1>
          <p className="mb-8 max-w-prose text-lg leading-relaxed text-muted">
            Persistent memory, tool use, governance, and full audit — your
            data never leaves the building. Built for regulated teams in law,
            healthcare, and fintech.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/contact" className="btn-primary">
              Book a discovery call
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/services" className="btn-ghost">
              See the services
            </Link>
          </div>

          <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-border-light pt-8">
            <Stat label="Lines of OSS shipped" value="170K" />
            <Stat label="Tests passing" value="1,318" />
            <Stat label="MCP tools built" value="374" />
          </dl>
        </div>

        <div className="relative aspect-square w-full max-w-[480px] justify-self-center overflow-hidden rounded-2xl border border-border bg-surface-alt">
          <div className="absolute inset-0 bg-gradient-to-br from-lavender-bg via-surface-alt to-surface" />
          {/* Animated triquetra — the mark of WhiteMagic Labs. */}
          <div className="absolute inset-0 flex items-center justify-center p-12">
            <AnimatedTriquetra className="h-full w-full opacity-90" />
          </div>
          <div className="absolute inset-x-0 bottom-0 p-6 text-center">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
              WhiteMagic Labs · Private AI
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-dim">{label}</dt>
      <dd className="mt-1 font-head text-2xl font-semibold text-ink">
        {value}
      </dd>
    </div>
  );
}
