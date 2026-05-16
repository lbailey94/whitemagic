import Link from "next/link";
import { KnowledgeSphereWrapper } from "@/components/KnowledgeSphereWrapper";
import { SemanticSearch } from "@/components/SemanticSearch";

const DOMAINS = [
  {
    slug: "intelligence",
    title: "Intelligence",
    description:
      "AI architecture, agent design, machine consciousness, and the engineering of cognition.",
  },
  {
    slug: "horizons",
    title: "Horizons",
    description:
      "Emerging technology frontiers — from brain-computer interfaces to space economy to energy infrastructure.",
  },
  {
    slug: "worldbuilding",
    title: "Worldbuilding",
    description:
      "Civilizational design, speculative futures, and the Sci-Fi World 2.0 narrative layer.",
  },
  {
    slug: "philosophy",
    title: "Philosophy",
    description:
      "Ethics, governance, epistemic rigor, and the frameworks that guide what we build and why.",
  },
];

export default function EssaysIndex() {
  return (
    <main className="container-site py-16">
      <header className="mb-12">
        <p className="font-mono text-sm uppercase tracking-wider text-lavender">
          Essays
        </p>
        <h1 className="mt-2 font-head text-4xl font-semibold text-ink">
          Four domains. One epistemic standard.
        </h1>
        <p className="mt-4 max-w-prose text-lg text-muted">
          Every essay carries an epistemic tag — [Proven], [Promising],
          [Contested], [Speculative], or [Mythopoetic] — so you know exactly
          what kind of claim you&apos;re reading. Evidence is linked.
          Uncertainty is labeled. Speculation is marked as such.
        </p>
      </header>

      <ul className="grid gap-6 sm:grid-cols-2">
        {DOMAINS.map((domain) => (
          <li key={domain.slug}>
            <Link
              href={`/essays/${domain.slug}`}
              className="block rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
            >
              <h2 className="font-head text-xl font-semibold text-ink">
                {domain.title}
              </h2>
              <p className="mt-2 text-muted">{domain.description}</p>
            </Link>
          </li>
        ))}
      </ul>

      <section className="mt-16">
        <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
          Knowledge Sphere
        </h2>
        <p className="mb-4 max-w-prose text-muted">
          {`10,768 semantic nodes from the CODEX pipeline — library documents,
          conversations, and research — positioned on a Fibonacci sphere by
          similarity. Hover to see content. Drag to explore.`}
        </p>
        <SemanticSearch />
        <div className="mb-8" />
        <KnowledgeSphereWrapper />
      </section>
    </main>
  );
}
