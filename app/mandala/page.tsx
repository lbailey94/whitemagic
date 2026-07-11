/**
 * /mandala — MandalaOS Dashboard
 *
 * Live visualization of the MandalaOS software layer:
 * - Active mandala compartments (radial diagram)
 * - Karma debt per mandala
 * - Effect type distribution
 * - Shelter templates
 * - Dharma profiles
 *
 * Data sources: mandala.status, karmic.debt, effect.visualize, mandala.templates
 */

import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { MandalaDashboard } from "@/components/MandalaDashboard";
import { WM_FACTS } from "@/lib/facts";

export const metadata: Metadata = {
  title: "MandalaOS — WhiteMagic Labs",
  description:
    `Live MandalaOS dashboard — isolated compartments, karmic effect tracking, Dharma profiles, and shelter templates. Part of the ${WM_FACTS.callableTools}-tool substrate.`,
};

export default function MandalaPage() {
  return (
    <>
      <PageHeader
        eyebrow="MandalaOS"
        title="Mandala Dashboard"
        lede="Live view of the MandalaOS software layer — isolated execution compartments with per-shelter Dharma profiles, karmic effect tracking, and typed effect signatures."
      />

      <section className="container-site py-12">
        <MandalaDashboard />
      </section>
    </>
  );
}
