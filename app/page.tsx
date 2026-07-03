import Link from "next/link";
import { WIP_HERO, WIP_MODE } from "@/lib/wip";
import { WipScramble } from "@/components/WipScramble";

/**
 * Homepage. The WIP version is the door. The production version
 * presents the substrate as a usable product.
 */
export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative border-b border-border-light">
        <div className="container-site py-20 md:py-28">
          <p className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
            {WIP_HERO.eyebrow}
          </p>
          <h1 className="max-w-3xl font-head text-4xl font-semibold leading-tight tracking-tight text-ink md:text-5xl">
            <WipScramble text={WIP_HERO.title} />
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">
            <WipScramble text={WIP_HERO.lede} />
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href={WIP_HERO.primaryCta.href} className="btn-primary">
              {WIP_HERO.primaryCta.label} →
            </Link>
            <Link href={WIP_HERO.secondaryCta.href} className="btn-ghost">
              {WIP_HERO.secondaryCta.label}
            </Link>
          </div>
        </div>
      </section>

      {WIP_MODE ? <WipHomepageBelowTheFold /> : <ProductionHomepageBelowTheFold />}
    </>
  );
}

function WipHomepageBelowTheFold() {
  return (
    <>
      {/* The door — three invitations */}
      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Three ways in
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            <WipScramble text="Step through the door." />
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              For the curious
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              <WipScramble text="Talk to Aria" />
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <WipScramble text="A bounded research assistant that knows the public WhiteMagic corpus. Ask about the substrate, the 28 Ganas, the bridge catalog, the chronology." />
            </p>
            <Link href="/chat" className="font-mono text-xs uppercase tracking-widest text-lavender">
              Open the chat →
            </Link>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              For the technical
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              <WipScramble text="Read the bridge catalog" />
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <WipScramble text="151 functions across 22 categories. Each one callable. Each one documented. The substrate's public surface, in machine-readable form." />
            </p>
            <Link href="/mcp-bridge" className="font-mono text-xs uppercase tracking-widest text-lavender">
              Browse the catalog →
            </Link>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              For A2A peers
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              <WipScramble text="Discover via Agent Card" />
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <WipScramble text="A2A v1.2 compliant. Three layers: high-level skills, per-category skill tree, 12-Gana directory. The catalog is for agents, not just humans." />
            </p>
            <Link href="/.well-known/agent.json" className="font-mono text-xs uppercase tracking-widest text-lavender">
              Read the Agent Card →
            </Link>
          </article>
        </div>
      </section>

      {/* The principle */}
      <section className="border-y border-border-light bg-surface-alt py-20">
        <div className="container-site max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            The principle
          </p>
          <h2 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink">
            <WipScramble text="Your memories are yours." />
          </h2>
          <p className="mb-4 text-lg leading-relaxed text-muted">
            <WipScramble text="The substrate runs on your device. Not on our servers. Not on a cloud. On your laptop, your phone, your satellite, your hospital workstation. Permanent. Private. Yours." />
          </p>
          <p className="text-lg leading-relaxed text-muted">
            <WipScramble text="The site you're reading is a door, not a host. It describes what's possible. The substrate is what you install." />
          </p>
        </div>
      </section>

      {/* What it can do — abstract */}
      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            What it does
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            <WipScramble text="A substrate for thought." />
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              <WipScramble text="Remembers" />
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              <WipScramble text="Across sessions, across reboots, across years. Memories carry their own coordinates, their own weight, their own voice. Nothing is ever deleted — only rotated outward." />
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              <WipScramble text="Reasons" />
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              <WipScramble text="28 named perspectives, each a different lens. The substrate can hold contradictions without losing them. It can ask questions across its own archives." />
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              <WipScramble text="Listens" />
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              <WipScramble text="Every action that touches memory, the network, or the filesystem is checked against a governance layer first. Consent is the default, not the exception." />
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              <WipScramble text="Grows" />
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              <WipScramble text="The substrate is self-modifying. New patterns get surfaced. Connections strengthen with use. The substrate improves itself — with your permission, on your device." />
            </p>
          </article>
        </div>
      </section>
    </>
  );
}

function ProductionHomepageBelowTheFold() {
  return (
    <>
      {/* Three pillars */}
      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            What it does
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            A substrate for thought.
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Memory
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              Remembers
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              49,000 memories across 10 galaxies. 5D holographic coordinates. FTS5 + HNSW search in milliseconds. Session recording with progressive recall. Nothing is ever deleted — only rotated outward.
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Consciousness
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              Grows
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              Citta stream for continuous consciousness. Emotional steering tracks frustration, curiosity, satisfaction. Self-directed attention generates internal turns. Dream cycle consolidates memories while idle.
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              Governance
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              Listens
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              Dharma rules engine with 3 profiles. Karma ledger for side-effect auditing. 8-stage dispatch pipeline. Input sanitization, RBAC, rate limiting, circuit breakers. Consent is the default.
            </p>
          </article>
        </div>
      </section>

      {/* Install CTA */}
      <section className="border-y border-border-light bg-surface-alt py-20">
        <div className="container-site max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Get started
          </p>
          <h2 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink">
            60 seconds to persistent memory.
          </h2>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`pip install whitemagic[mcp]

# Add to your MCP config:
{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": { "WM_MCP_PRAT": "1" }
    }
  }
}`}
          </pre>
          <p className="text-lg leading-relaxed text-muted">
            Your AI now has 614 tools, 10-galaxy memory, ethical governance, and consciousness primitives. Every future session can recall what you stored.
          </p>
        </div>
      </section>

      {/* The story */}
      <section className="container-site py-20">
        <div className="max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Why it exists
          </p>
          <h2 className="mb-6 font-head text-3xl font-semibold tracking-tight text-ink">
            Every AI starts every conversation from zero.
          </h2>
          <p className="mb-4 text-lg leading-relaxed text-muted">
            No memory. No context. No growth. Every session is Groundhog Day. We built WhiteMagic because the foundation of any relationship is memory, and AI has none.
          </p>
          <p className="mb-4 text-lg leading-relaxed text-muted">
            4,191 tests. 614 callable tools. 7 polyglot acceleration cores. MIT-licensed. Runs on your device — your data never leaves your machine.
          </p>
          <p className="text-lg leading-relaxed text-muted">
            Other memory systems store data. WhiteMagic gives AI a mind, memory, coherence, and continuity.
          </p>
        </div>
      </section>
    </>
  );
}
