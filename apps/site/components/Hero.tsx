import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AnimatedTriquetra } from "./AnimatedTriquetra";
import { WM_FACTS } from "@/lib/facts";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border-light">
      <div className="container-site grid items-center gap-10 py-20 md:grid-cols-[1.1fr_0.9fr] md:py-28">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <ShieldCheck className="h-3.5 w-3.5 text-lavender" />
            Open-source governance infrastructure
          </div>
          <h1 className="mb-6 font-head text-4xl font-semibold leading-[1.05] tracking-tight text-ink md:text-6xl">
            Governance infrastructure<br />
            for <span className="text-lavender">agentic AI</span>.
          </h1>
          <p className="mb-8 max-w-prose text-lg leading-relaxed text-muted">
            WhiteMagic Labs publishes research, tools, and reference
            implementations for memory, tool-use governance, and side-effect
            audit. Consulting is available where the work is directly useful.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/contact" className="btn-primary">
              Start a conversation
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/research" className="btn-ghost">
              Read the research
            </Link>
          </div>

          <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-border-light pt-8">
            <Stat label="Lines of OSS shipped" value={WM_FACTS.linesShort} />
            <Stat label="Tests passing" value={WM_FACTS.testsPassing} />
            <Stat label="MCP tools built" value={WM_FACTS.callableTools} />
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
              WhiteMagic Labs · Agent Governance
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
