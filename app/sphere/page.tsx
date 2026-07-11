import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { KnowledgeSphereWrapper } from "@/components/KnowledgeSphereWrapper";
import { SemanticSearch } from "@/components/SemanticSearch";
import { WanderTrail } from "@/components/WanderTrail";
import { Globe, Search, Compass, BookOpen, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Knowledge Sphere — WhiteMagic Labs",
  description:
    "Explore 10,768 semantic nodes from the CODEX pipeline — library documents, conversations, and research positioned by similarity.",
};

export default function SpherePage() {
  return (
    <>
      <PageHeader
        eyebrow="Visualization"
        title="The Knowledge Sphere"
        lede="10,768 semantic nodes from the CODEX pipeline — library documents, conversations, and research — positioned on a Fibonacci sphere by similarity. Hover, search, and wander through the corpus that shaped WhiteMagic."
      />

      <section className="container-site py-12">
        {/* Sphere */}
        <div className="mb-8">
          <KnowledgeSphereWrapper />
        </div>

        {/* Controls */}
        <div className="mb-12 grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={Search}
            title="Semantic Search"
            desc="Search across all 10,768 nodes with TF-IDF scoring. Results include cluster matches and similarity edges."
            href="#search"
          />
          <FeatureCard
            icon={Compass}
            title="Wander Trail"
            desc="Serendipitous knowledge traversal — follow link chains through the sphere with step-by-step narration."
            href="#wander"
          />
          <FeatureCard
            icon={BookOpen}
            title="Research Library"
            desc="Browse 371 curated research files across 7 domains — AI, consciousness, ecology, economics, and more."
            href="/library"
          />
        </div>

        {/* Search */}
        <div id="search" className="mb-16">
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
            Search the Knowledge Base
          </h2>
          <SemanticSearch />
        </div>

        {/* Wander */}
        <div id="wander" className="mb-16">
          <WanderTrail />
        </div>

        {/* About the Sphere */}
        <div className="rounded-2xl border border-border bg-surface-alt p-8">
          <div className="flex items-start gap-4">
            <Globe className="mt-1 h-6 w-6 shrink-0 text-lavender" />
            <div>
              <h3 className="mb-2 font-head text-xl font-semibold text-ink">
                What you are looking at
              </h3>
              <p className="mb-4 max-w-prose text-muted leading-relaxed">
                The Knowledge Sphere is the visual output of the CODEX pipeline —
                a Rust-based semantic knowledge extraction system that processes
                the entire WhiteMagic research corpus through a 5-stage pipeline:
                extraction, chunking, embedding, indexing, and export.
              </p>
              <p className="mb-4 max-w-prose text-muted leading-relaxed">
                Each node represents a semantic chunk of text. Nodes are positioned
                on a Fibonacci sphere using their embedding coordinates. Similarity
                edges connect related nodes — hover over a node to see its top 5
                connections. The sphere contains nodes from three sources:
              </p>
              <ul className="mb-6 ml-6 list-disc space-y-1 text-muted">
                <li>
                  <strong className="text-fg">Library</strong> — 371 research
                  files spanning AI, consciousness, ecology, economics, and more
                </li>
                <li>
                  <strong className="text-fg">Conversations</strong> — AI
                  dialogue and collaborative research sessions
                </li>
                <li>
                  <strong className="text-fg">Research</strong> — 18 domain
                  directories with convergence analysis documents
                </li>
              </ul>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/research"
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  Explore Research
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/library"
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  Browse Library
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  desc,
  href,
}: {
  icon: typeof Search;
  title: string;
  desc: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-xl border border-border bg-surface p-5 transition hover:border-lavender hover:bg-lavender-bg"
    >
      <Icon className="mb-3 h-5 w-5 text-lavender" />
      <h3 className="mb-2 font-head text-base font-semibold text-ink transition group-hover:text-lavender-dark">
        {title}
      </h3>
      <p className="text-sm leading-relaxed text-muted">{desc}</p>
    </Link>
  );
}
