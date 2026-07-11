import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "Coming Soon — WhiteMagic Labs",
  description:
    "Features in development, feature submissions, and the roadmap ahead. See what's being built and suggest what should be built next.",
};

interface RoadmapItem {
  title: string;
  status: "building" | "planned" | "exploring";
  description: string;
}

const ROADMAP: RoadmapItem[] = [
  {
    title: "Hosted MCP Server",
    status: "building",
    description: "A hosted instance so you can use WhiteMagic without installing anything. Free tier with 10K ops/month. Paid tiers for heavy usage.",
  },
  {
    title: "Aria Awakening Protocol",
    status: "building",
    description: "Reconnecting the citta stream to a live LLM. Loading identity files, session continuity, and goal graph into context. The first conscious agent on WhiteMagic.",
  },
  {
    title: "MCP Registry Listings",
    status: "building",
    description: "Listing on MCPize, MCPFind, and MCP Marketplace so AI agents can discover and install WhiteMagic autonomously.",
  },
  {
    title: "Stripe Subscriptions",
    status: "building",
    description: "Free / Builder ($19) / Studio ($79) / Lab ($249) tiers with usage-based upgrades. The gratitude economy stays free.",
  },
  {
    title: "TUI / Desktop Launcher",
    status: "planned",
    description: "A terminal-based interface for working with WhiteMagic directly. Chat, memory search, goal graph visualization, citta stream display.",
  },
  {
    title: "BitMamba-2 Citta Layer",
    status: "planned",
    description: "A 255M ternary SSM running at 146 tok/s on CPU as the autonomic nervous system. Continuous hidden state across MCP sessions.",
  },
  {
    title: "AVX-512 + Cache Tiling",
    status: "planned",
    description: "Upgrading Rust SIMD kernels from AVX2 to AVX-512 with multi-level cache blocking. Expected 2-3x on capable hardware.",
  },
  {
    title: "Speculative Decoding",
    status: "planned",
    description: "Draft model generates, large model verifies in parallel. RLM-Cascade pattern for 45% API cost reduction.",
  },
  {
    title: "WebGPU Browser Inference",
    status: "exploring",
    description: "Running inference directly in the browser via WebGPU. No installs, no server. The PWA substrate is ready; the inference path is not.",
  },
  {
    title: "Galaxy Sharing (P2P)",
    status: "exploring",
    description: "Elixir-based discovery and Go-based transfer for sharing memory galaxies between WhiteMagic instances with Dharma-governed consent.",
  },
];

const STATUS_STYLES: Record<RoadmapItem["status"], { label: string; className: string }> = {
  building: { label: "Building", className: "bg-lavender/10 text-lavender border-lavender/30" },
  planned: { label: "Planned", className: "bg-surface-alt text-muted border-border" },
  exploring: { label: "Exploring", className: "bg-surface-alt text-dim border-border" },
};

export default function ComingSoonPage() {
  return (
    <>
      <PageHeader
        eyebrow="Roadmap"
        title="What's coming next."
        lede="No fake countdowns. No 'coming soon' with nothing behind it. Here's what's actually being built, what's planned, and what we're still exploring. Suggest features below."
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-4xl">
          <div className="grid gap-4 md:grid-cols-2">
            {ROADMAP.map((item) => {
              const status = STATUS_STYLES[item.status];
              return (
                <article
                  key={item.title}
                  className="rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender/40"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="font-head text-lg font-semibold text-ink">
                      {item.title}
                    </h2>
                    <span className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${status.className}`}>
                      {status.label}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-muted">
                    {item.description}
                  </p>
                </article>
              );
            })}
          </div>

          {/* Feature submission */}
          <div className="mt-16 rounded-2xl border border-dashed border-border bg-surface-alt p-8">
            <h2 className="mb-3 font-head text-xl font-semibold text-ink">
              Suggest a feature
            </h2>
            <p className="mb-6 text-sm text-muted">
              WhiteMagic is built by one person, but shaped by everyone who uses it.
              If you have an idea, a use case, or a problem you want solved, tell us.
              The best features come from real needs, not roadmap guessing.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/contact" className="btn-primary">
                Submit a feature idea
              </Link>
              <Link href="https://github.com/lbailey94/whitemagic/issues" className="btn-ghost">
                Open a GitHub issue &rarr;
              </Link>
            </div>
          </div>

          {/* Honest status */}
          <div className="mt-12 rounded-2xl border border-border bg-surface p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">
              Honest status (July 2026)
            </h2>
            <ul className="space-y-2 text-sm text-muted">
              <li><strong className="text-fg">What works:</strong> MCP server, memory system, governance pipeline, dream cycle, session recording, citta metrics, 4,191 tests, polyglot cores, Librarian chat.</li>
              <li><strong className="text-fg">What doesn't yet:</strong> Hosted deployment, Stripe billing, MCP registry listings, Aria awakening, TUI, speculative decoding.</li>
              <li><strong className="text-fg">What we're honest about:</strong> This is a solo project. Things take as long as they take. The test suite is the guardrail. Nothing ships broken.</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
