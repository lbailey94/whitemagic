/**
 * Live Galaxy — 5D Holographic Memory Visualization
 *
 * Real-time visualization of the WhiteMagic memory galaxy,
 * with nodes positioned by holographic coordinates and
 * colored by galactic zone.
 */

import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { InteractiveGalaxySphere } from "@/components/InteractiveGalaxySphere";
import { Globe, ArrowRight, Zap, Layers, MousePointer2, Link2 } from "lucide-react";

export const metadata = {
  title: "Live Galaxy — WhiteMagic",
  description:
    "Explore your holographic memory core in real-time — 5D coordinates, zone-based navigation, and live resonance.",
};

export default function GalaxyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Live Visualization"
        title="Memory Galaxy"
        lede="Your holographic memory core rendered in real-time — 5D coordinates projected to 3D space, colored by galactic zone."
      />

      <section className="container-site py-12">
        {/* Interactive Galaxy */}
        <div className="mb-8 rounded-xl border border-purple-500/20 bg-black/30 overflow-hidden">
          <InteractiveGalaxySphere height={700} maxNodes={500} useLocalMode />
        </div>

        {/* Feature Cards */}
        <div className="mb-12 grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={MousePointer2}
            title="Drag Nodes"
            desc="Click and drag any node to reposition it in 3D space. Your changes persist across sessions."
            href="#about"
          />
          <FeatureCard
            icon={Link2}
            title="Draw Edges"
            desc="Switch to Connect mode and click two nodes to create custom edges between them."
            href="#about"
          />
          <FeatureCard
            icon={Zap}
            title="Resonance Navigation"
            desc="Click a node to see semantic similarity lines to related memories in the galaxy."
            href="#about"
          />
        </div>

        {/* About */}
        <div id="about" className="rounded-2xl border border-border bg-surface-alt p-8">
          <div className="flex items-start gap-4">
            <Globe className="mt-1 h-6 w-6 shrink-0 text-lavender" />
            <div>
              <h3 className="mb-2 font-head text-xl font-semibold text-ink">
                About the Live Galaxy
              </h3>
              <p className="mb-4 max-w-prose text-muted leading-relaxed">
                The Live Galaxy is a real-time projection of your WhiteMagic memory core.
                Each node represents a memory positioned in 5D holographic space. The
                3D visualization you see is a projection of (x, y, z) with (w, v) as
                additional resonance dimensions.
              </p>
              <p className="mb-4 max-w-prose text-muted leading-relaxed">
                Nodes are colored by their galactic zone, which is determined by their
                distance from the core. Memories closer to the center are more important
                and frequently accessed. The edges between nodes represent semantic
                similarity — stronger edges mean closer conceptual relationships.
              </p>
              <ul className="mb-6 ml-6 list-disc space-y-1 text-muted">
                <li>
                  <strong className="text-fg">Core Zone</strong> — High-importance, frequently accessed memories
                </li>
                <li>
                  <strong className="text-fg">Active Zone</strong> — Recently used, working memories
                </li>
                <li>
                  <strong className="text-fg">Architecture Zone</strong> — Structural and system memories
                </li>
                <li>
                  <strong className="text-fg">Research Zone</strong> — Exploratory and learning memories
                </li>
                <li>
                  <strong className="text-fg">Outer Rim</strong> — Distant, rarely accessed memories
                </li>
              </ul>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/mcp-bridge"
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  Open Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/library"
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  Knowledge Sphere (Static)
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
  icon: typeof Globe;
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
