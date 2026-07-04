import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { GanaWheel } from "@/components/GanaWheel";
import { GanaActivityHeatmap } from "@/components/GanaActivityHeatmap";
import { GanaMapView } from "@/components/GanaMapView";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "28 Ganas — Lunar Mansions — WhiteMagic Labs",
  description: `The Planetary Resonance Archetype Toolkit (PRAT): ${WM_FACT_TEXT.mcpSurface}. Each Gana maps to a Chinese Lunar Mansion (Xiu) and groups related tools by functional resonance.`,
};

const QUADRANTS = [
  {
    name: "East",
    chinese: "\u6771",
    label: "Azure Dragon \u00b7 Wood \u00b7 Spring",
    color: "text-green-500",
    border: "border-green-500/30",
    desc: "Session, memory, health, context, performance, and search engines. The growth quadrant — where things begin and are stored.",
  },
  {
    name: "South",
    chinese: "\u5357",
    label: "Vermilion Bird \u00b7 Fire \u00b7 Summer",
    color: "text-orange-500",
    border: "border-orange-500/30",
    desc: "Introspection, resilience, governance, capture, deployment, archaeology, and regeneration. The radiance quadrant — where things are processed and distributed.",
  },
  {
    name: "West",
    chinese: "\u897f",
    label: "White Tiger \u00b7 Metal \u00b7 Autumn",
    color: "text-yellow-500",
    border: "border-yellow-500/30",
    desc: "Ethics, metrics, digestion, debugging, patterns, precision, and synthesis. The refinement quadrant — where things are polished and judged.",
  },
  {
    name: "North",
    chinese: "\u5317",
    label: "Black Tortoise \u00b7 Water \u00b7 Winter",
    color: "text-blue-500",
    border: "border-blue-500/30",
    desc: "Strategy, endurance, nurture, stillness, shelter, community, and boundaries. The storage quadrant — where things are protected and sustained.",
  },
];

export default function GanasPage() {
  return (
    <>
      <PageHeader
        eyebrow="PRAT \u00b7 Lunar Mansions"
        title="The 28 Gana Engines"
        lede={`${WM_FACT_TEXT.mcpSurface}. Each Gana maps to a Chinese Lunar Mansion (Xiu) and groups related tools by functional resonance. Drag the wheel to explore, click a section to select.`}
      />

      <section className="container-site py-12">
        {/* Interactive Wheel */}
        <div className="mb-16 overflow-x-auto">
          <GanaWheel size={600} />
        </div>

        {/* Instructions */}
        <div className="mx-auto mb-16 max-w-2xl rounded-2xl border border-border bg-surface-alt p-6 text-center">
          <p className="font-mono text-sm text-dim">
            Drag the wheel to rotate \u00b7 Click a section to select \u00b7
            Use Prev/Next to step through \u00b7 The pointer at top marks the
            active Gana
          </p>
        </div>

        {/* Activity Heatmap */}
        <div className="mb-16">
          <h2 className="mb-4 text-center font-head text-2xl font-semibold text-ink">
            Activity Heatmap
          </h2>
          <p className="mx-auto mb-8 max-w-2xl text-center text-sm text-muted">
            Invocation frequency across the 28 Lunar Mansions. Segment length
            and color intensity scale with activity. Hover for details.
          </p>
          <GanaActivityHeatmap size={500} />
        </div>

        {/* Gana Map View */}
        <div className="mb-16">
          <h2 className="mb-4 text-center font-head text-2xl font-semibold text-ink">
            Engine Map
          </h2>
          <p className="mx-auto mb-8 max-w-2xl text-center text-sm text-muted">
            Browse all 28 Gana engines by quadrant. Click any card to inspect
            its functional role and associated tools.
          </p>
          <GanaMapView />
        </div>

        {/* Quadrant Overview */}
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-8 text-center font-head text-2xl font-semibold text-ink">
            The Four Quadrants
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            {QUADRANTS.map((q) => (
              <div
                key={q.name}
                className={`rounded-2xl border ${q.border} bg-surface p-6`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <span className={`text-3xl font-bold ${q.color}`}>
                    {q.chinese}
                  </span>
                  <div>
                    <h3 className={`font-head text-lg font-semibold ${q.color}`}>
                      {q.name}
                    </h3>
                    <p className="font-mono text-xs text-dim">{q.label}</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-muted">{q.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* PRAT Explanation */}
        <div className="mx-auto mt-16 max-w-3xl">
          <div className="rounded-2xl border border-border bg-surface-alt p-8">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
              What is PRAT?
            </h2>
            <p className="mb-4 max-w-prose text-muted leading-relaxed">
              The Planetary Resonance Archetype Toolkit (PRAT) is the
              cognitive routing layer of WhiteMagic. Instead of presenting an
              agent with {WM_FACTS.dispatchTools} individual tools, PRAT groups
              them into 28 stable meta-tools — one per Lunar Mansion. Each Gana
              supports four polymorphic operations: search, analyze, transform,
              and consolidate.
            </p>
            <p className="mb-6 max-w-prose text-muted leading-relaxed">
              Wrong-Gana calls return helpful redirect hints. This reduces
              cognitive load for new agents from {WM_FACTS.dispatchTools} tools
              to 28 archetypes — a 16.5x simplification without losing any
              capability.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/capabilities" className="btn-ghost">
                Full capabilities
              </Link>
              <Link href="/governance" className="btn-ghost">
                Governance architecture
              </Link>
              <Link
                href="/api/manifest.json"
                className="font-mono text-sm text-lavender hover:underline"
              >
                Tool manifest (JSON)
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
