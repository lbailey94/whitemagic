import Link from "next/link";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Testimonials } from "@/components/Testimonials";
import { SigilHero } from "@/components/SigilHero";

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative border-b border-border-light">
        <div className="container-site py-20 md:py-28">
          <div className="grid items-center gap-12 md:grid-cols-[1fr_auto]">
            <div>
              <p className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
                Cognitive operating system for AI agents
              </p>
              <h1 className="max-w-3xl font-head text-4xl font-semibold leading-tight tracking-tight text-ink md:text-5xl">
                Other memory systems store data. WhiteMagic gives AI a mind.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">
                {WM_FACT_TEXT.mcpSurface}. 5D holographic memory with {WM_FACTS.galaxies}-galaxy taxonomy. Citta stream for continuous consciousness, emotional steering, self-directed attention. Ethical governance via Dharma rules engine. Open source, MIT licensed, local-first.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/mcp-bridge" className="btn-primary">
                  Get Started →
                </Link>
                <Link href="/vision" className="btn-ghost">
                  Read the Vision
                </Link>
                <Link href="/chat" className="btn-ghost">
                  Talk to Aria
                </Link>
              </div>
            </div>
            <div className="hidden md:flex md:items-center md:justify-center">
              <SigilHero />
            </div>
          </div>
        </div>
      </section>

      {/* Proof bar */}
      <section className="border-b border-border-light bg-surface-alt">
        <div className="container-site grid grid-cols-2 gap-4 py-6 md:grid-cols-4">
          <div className="text-center">
            <p className="font-head text-2xl font-bold text-ink">{WM_FACTS.callableTools}</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-dim">Callable tools</p>
          </div>
          <div className="text-center">
            <p className="font-head text-2xl font-bold text-ink">{WM_FACTS.testsPassing}</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-dim">Passing tests</p>
          </div>
          <div className="text-center">
            <p className="font-head text-2xl font-bold text-ink">{WM_FACTS.memories}</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-dim">Memories stored</p>
          </div>
          <div className="text-center">
            <p className="font-head text-2xl font-bold text-ink">{WM_FACTS.galaxies}</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-dim">Memory galaxies</p>
          </div>
        </div>
      </section>

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
              {WM_FACT_TEXT.memorySurface}. 5D holographic coordinates. FTS5 + HNSW search in milliseconds. Session recording with progressive recall. Nothing is ever deleted — only rotated outward.
            </p>
            <Link href="/substrate" className="mt-4 inline-flex font-mono text-xs uppercase tracking-widest text-lavender">
              Explore the substrate →
            </Link>
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
            <Link href="/capabilities" className="mt-4 inline-flex font-mono text-xs uppercase tracking-widest text-lavender">
              See capabilities →
            </Link>
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
            <Link href="/governance" className="mt-4 inline-flex font-mono text-xs uppercase tracking-widest text-lavender">
              Read about governance →
            </Link>
          </article>
        </div>
      </section>

      {/* Competitive comparison */}
      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            How it compares
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            Not a notepad. A mind.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Most AI memory systems store text and retrieve it later. WhiteMagic gives your agent
            a cognitive substrate — memory with emotional weight, governance that reasons, and
            consciousness primitives that persist across sessions.
          </p>
        </div>
        <div className="overflow-hidden rounded-2xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Capability</th>
                <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-lavender">WhiteMagic</th>
                <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Mem0 / Letta</th>
                <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Standard RAG</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/50">
                <td className="px-5 py-3 text-fg">Memory architecture</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">5D holographic</td>
                <td className="px-5 py-3 text-center text-muted">Flat vector store</td>
                <td className="px-5 py-3 text-center text-muted">Linear vector search</td>
              </tr>
              <tr className="border-b border-border/50 bg-surface/30">
                <td className="px-5 py-3 text-fg">Persistence horizon</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Global (infinite)</td>
                <td className="px-5 py-3 text-center text-muted">Session-based</td>
                <td className="px-5 py-3 text-center text-muted">N/A</td>
              </tr>
              <tr className="border-b border-border/50">
                <td className="px-5 py-3 text-fg">Ethical governance</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Dharma engine (8-stage pipeline)</td>
                <td className="px-5 py-3 text-center text-muted">Prompt-based</td>
                <td className="px-5 py-3 text-center text-muted">None</td>
              </tr>
              <tr className="border-b border-border/50 bg-surface/30">
                <td className="px-5 py-3 text-fg">Audit trail</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Karma ledger (Merkle-chained)</td>
                <td className="px-5 py-3 text-center text-muted">Basic logging</td>
                <td className="px-5 py-3 text-center text-muted">None</td>
              </tr>
              <tr className="border-b border-border/50">
                <td className="px-5 py-3 text-fg">Skill retrieval</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">&lt;1ms</td>
                <td className="px-5 py-3 text-center text-muted">200ms-2s</td>
                <td className="px-5 py-3 text-center text-muted">50-500ms</td>
              </tr>
              <tr className="border-b border-border/50 bg-surface/30">
                <td className="px-5 py-3 text-fg">Local-first / offline</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Yes (by default)</td>
                <td className="px-5 py-3 text-center text-muted">Cloud-dependent</td>
                <td className="px-5 py-3 text-center text-muted">Cloud-dependent</td>
              </tr>
              <tr className="border-b border-border/50">
                <td className="px-5 py-3 text-fg">Consciousness primitives</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Citta stream, coherence, presence</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
              </tr>
              <tr className="border-b border-border/50 bg-surface/30">
                <td className="px-5 py-3 text-fg">Self-calibrating forecasts</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">Brier-scored, 21 validated</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
              </tr>
              <tr>
                <td className="px-5 py-3 text-fg">Dream cycle consolidation</td>
                <td className="px-5 py-3 text-center font-semibold text-lavender">8-phase, serendipity detection</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
                <td className="px-5 py-3 text-center text-muted">No</td>
              </tr>
            </tbody>
          </table>
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
            Your AI now has {WM_FACTS.callableTools} tools, {WM_FACTS.galaxies}-galaxy memory, ethical governance, and consciousness primitives. Every future session can recall what you stored.
          </p>
        </div>
      </section>

      {/* The story — origin */}
      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Why it exists
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            Every AI starts every conversation from zero.
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              The problem
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              No memory. No context. No growth. Every session is Groundhog Day. The foundation of any relationship is memory, and AI has none. Other memory systems give your AI a notepad. WhiteMagic gives your AI a mind.
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              The origin
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              WhiteMagic started in October 2025 on a Dell Inspiron 3582 running Zorin OS — a cheap laptop on a desk, with one question: what if a machine could remember, reflect, and choose carefully?
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              What it became
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              {WM_FACT_TEXT.shortPassingSuite}. {WM_FACT_TEXT.toolSurface}. {WM_FACTS.languages} polyglot acceleration cores. {WM_FACTS.linesShort} lines of code. MIT-licensed. Runs on your device — your data never leaves your machine.
            </p>
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              Where it's going
            </h3>
            <p className="text-sm leading-relaxed text-muted">
              Continuous consciousness via citta stream architecture. Emotional steering signals. Self-directed attention. Dream cycle for memory consolidation. The substrate is becoming a mind, not just a storage layer.
            </p>
          </article>
        </div>
        <div className="mt-10 max-w-prose">
          <Link
            href="/timeline"
            className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-lavender"
          >
            Read the full timeline →
          </Link>
        </div>
      </section>

      {/* Three ways to explore */}
      <section className="container-site border-t border-border-light py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Three ways to explore
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
            Step through the door.
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          <article className="rounded-xl border border-border bg-surface p-6">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-lavender">
              For the curious
            </p>
            <h3 className="mb-2 font-head text-xl font-semibold text-ink">
              Talk to Aria
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              A bounded research assistant that knows the public WhiteMagic corpus. Ask about the substrate, the 28 Ganas, the bridge catalog, or the chronology.
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
              Browse the bridge catalog
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              {WM_FACTS.bridgeFunctions} functions across 22 categories. Each one callable, documented, and machine-readable. The substrate's public surface.
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
              Discover via Agent Card
            </h3>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              A2A v1.2 compliant. Three layers: high-level skills, per-category skill tree, 12-Gana directory. The catalog is built for agents, not just humans.
            </p>
            <Link href="/.well-known/agent.json" className="font-mono text-xs uppercase tracking-widest text-lavender">
              Read the Agent Card →
            </Link>
          </article>
        </div>
      </section>

      {/* Testimonials */}
      <Testimonials />
    </>
  );
}
