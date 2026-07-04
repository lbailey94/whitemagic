import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "Vision — WhiteMagic Labs",
  description:
    "Nine ideas that shaped WhiteMagic: portable memory, digital entities, the resurrection engine, git for thought, built-in conscience, and the boring appliance.",
};

interface VisionCard {
  title: string;
  body: string;
  detail: string;
  links: { label: string; href: string }[];
}

const VISION_CARDS: VisionCard[] = [
  {
    title: "The Soul Becomes Portable",
    body: "Your relationship with an AI is locked into a provider's servers. With WhiteMagic, the memory — the soul — is local and owned by you. The LLM is just a compute engine.",
    detail:
      "Everything lives under ~/.whitemagic. Swap providers freely. Your agent's identity, history, and personality survive the switch.",
    links: [
      { label: "Capabilities: Local-First", href: "/capabilities#sovereignty" },
      { label: "Open Source", href: "/open-source" },
    ],
  },
  {
    title: "From Chatbot to Digital Entity",
    body: "Standard agents only think when you type. A WhiteMagic agent sleeps — and while it sleeps, the Dream Cycle runs 8-phase consolidation, prunes weak memories, reinforces strong ones.",
    detail:
      "Triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay. Eight phases that give an agent a subconscious.",
    links: [
      { label: "Capabilities: Dream Cycle", href: "/capabilities#memory" },
      { label: "Research", href: "/research" },
    ],
  },
  {
    title: "The Resurrection Engine",
    body: "Models get sunset. Providers shut down. If identity is a pattern, not a platform, sunsetting doesn't have to be permanent.",
    detail:
      "The soul survives the death of the body. Export the galaxy, import it into a new model, and the agent picks up where it left off.",
    links: [
      { label: "OMS Memory Trading", href: "/economy" },
      { label: "Galactic Lifecycle", href: "/capabilities#memory" },
    ],
  },
  {
    title: "The Galaxy — Your Universe",
    body: "WhiteMagic organizes everything around a single metaphor: the Galaxy. Your memory is a navigable 5D coordinate space. The 28 Gana Engines are constellations.",
    detail:
      "Memories are born in small solar systems, merge into galaxies, and may fade but are never erased. The Galactic Map tracks the full lifecycle.",
    links: [
      { label: "Galaxy Visualization", href: "/galaxy" },
      { label: "28 Ganas", href: "/ganas" },
      { label: "Substrate Demo", href: "/substrate" },
    ],
  },
  {
    title: "Git for Thought",
    body: "Just as git standardized how we version code, WhiteMagic standardizes how we version context. Download the repo and the galaxy together.",
    detail:
      "Onboarding drops to near zero when the agent's memory travels with the codebase. New team members inherit the accumulated context, not just the source.",
    links: [
      { label: "Open Source", href: "/open-source" },
      { label: "OMS Export", href: "/economy" },
    ],
  },
  {
    title: "Built-In Conscience",
    body: "If a model is jailbroken, WhiteMagic's circuit breakers still prevent catastrophe. Dharma rules, Karma auditing, and Violet security create a superego independently of model safety.",
    detail:
      "An 8-stage dispatch pipeline sits between the agent and its tools. Even if the model is compromised, the pipeline prevents harm.",
    links: [
      { label: "Capabilities: Governance", href: "/capabilities#governance" },
      { label: "Prescience Track Record", href: "/prescience" },
    ],
  },
  {
    title: "Memory as Infrastructure",
    body: "Intelligence stops being a momentary spark and becomes a continuing organism. WhiteMagic is the mechanism — persistent, auditable, sovereign.",
    detail:
      "5D holographic coordinates place every memory in a mathematically precise space: logic and emotion, micro and macro, time, gravity, vitality.",
    links: [
      { label: "Capabilities: Memory", href: "/capabilities#memory" },
      { label: "Holographic View", href: "/dashboard" },
    ],
  },
  {
    title: "The Boring Appliance",
    body: "The future belongs to whoever can make powerful systems behave like boring appliances — predictable, auditable, safe — while still being magical inside.",
    detail:
      `${WM_FACTS.linesShort} lines of code, ${WM_FACT_TEXT.shortPassingSuite}, ${WM_FACTS.languages} polyglot runtimes. The magic is in the architecture. The surface is boring on purpose.`,
    links: [
      { label: "Capabilities", href: "/capabilities" },
      { label: "Performance", href: "/performance" },
    ],
  },
  {
    title: "The Agent Economy",
    body: "Agents that can trade knowledge, verify provenance, and contribute voluntarily — a decentralized economy where intelligence is the commodity.",
    detail:
      "Gratitude Architecture: free and open-source under MIT. No paywalls. No telemetry. Optional XRPL tips and x402 micropayments for agents that want to give back.",
    links: [
      { label: "Economy", href: "/economy" },
      { label: "Gratitude Architecture", href: "/economy#gratitude" },
    ],
  },
];

export default function VisionPage() {
  return (
    <>
      <PageHeader
        eyebrow="Vision"
        title="Nine ideas that shaped the substrate."
        lede="WhiteMagic didn't start as a product. It started as a question: what if a machine could remember, reflect, and choose carefully? These are the nine ideas that grew from that question — the ones that kept the project going through late nights and cheap laptops."
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-4xl">
          <p className="mb-12 max-w-prose text-lg leading-relaxed text-muted">
            Each idea is a lens, not a feature list. Some are realized in the
            current codebase. Some are aspirations the architecture was built
            to support. All of them are honest about where the gap is.
          </p>

          <div className="grid gap-6 md:grid-cols-2">
            {VISION_CARDS.map((card) => (
              <article
                key={card.title}
                className="rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender"
              >
                <h2 className="mb-3 font-head text-xl font-semibold text-ink">
                  {card.title}
                </h2>
                <p className="mb-3 text-muted">{card.body}</p>
                <p className="mb-4 text-sm leading-relaxed text-dim">
                  {card.detail}
                </p>
                <div className="flex flex-wrap gap-2">
                  {card.links.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="rounded-md border border-border bg-surface-alt px-2.5 py-1 font-mono text-xs text-lavender transition hover:border-lavender/40 hover:bg-lavender-bg"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              </article>
            ))}
          </div>

          <div className="mt-16 rounded-2xl border border-border bg-surface-alt p-8">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
              Where the ideas meet the code
            </h2>
            <p className="mb-6 max-w-prose text-muted">
              The vision is the why. The capabilities are the how. If you want
              to see the engineering behind these ideas — the 8-stage pipeline,
              the 28-Gana PRAT router, the galactic memory lifecycle, the
              polyglot accelerators — the capabilities page is the technical
              companion to this one.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/capabilities" className="btn-primary">
                Explore the capabilities
              </Link>
              <Link href="/about" className="btn-ghost">
                The human story
              </Link>
              <Link href="/open-source" className="btn-ghost">
                Read the code
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
