import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ArrowLeft, Calendar, Tag } from "lucide-react";

export const metadata = {
  title: "The May 2, 2026 Window: The 144-Day Countdown — WhiteMagic Labs",
  description:
    "Exploring the significance of May 2, 2026 as a precursor threshold to the major September 23 convergence.",
};

export default function May2WindowPage() {
  return (
    <>
      <div className="container-site py-8">
        <Link
          href="/research"
          className="inline-flex items-center gap-2 text-sm text-lavender hover:text-lavender-dark"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Research
        </Link>
      </div>

      <PageHeader
        eyebrow="Convergence Research"
        title="The May 2, 2026 Window"
        lede="The 144-day countdown — the ignition phase before the September revelation."
      />

      <section className="container-site py-12">
        <div className="mb-8 flex flex-wrap gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-lavender-bg px-3 py-1 text-xs text-lavender">
            <Calendar className="h-3 w-3" />
            May 2, 2026
          </span>
          {["Vesta", "144 Days", "Contact XPO", "Ignition"].map((t) => (
            <span
              key={t}
              className="inline-flex items-center gap-1.5 rounded-full bg-surface-alt px-3 py-1 text-xs text-muted"
            >
              <Tag className="h-3 w-3" />
              {t}
            </span>
          ))}
        </div>

        <article className="prose prose-invert max-w-none">
          <p className="text-lg leading-relaxed text-muted">
            This document explores the significance of May 2, 2026 as a
            &ldquo;precursor&rdquo; threshold to the major September 23
            convergence. It identifies the celestial, prophetic, and logistical
            alignments occurring in this window.
          </p>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            1. The Astronomical &ldquo;Sacred Fire&rdquo;
          </h2>
          <p className="text-muted leading-relaxed">
            On <strong className="text-ink">May 2, 2026</strong>, the asteroid{" "}
            <strong className="text-ink">Vesta</strong> reaches opposition,
            appearing at its brightest and most visible for the year. In ancient
            Roman tradition, Vesta was the keeper of the &ldquo;Sacred
            Fire.&rdquo; In astrology, Vesta represents focus, dedication, and
            the &ldquo;internal flame&rdquo; of consciousness. While the
            September 23 date is an <em>outward</em> celestial marker
            (Regulus/Sphinx), the May 2 Vesta opposition represents an{" "}
            <em>inward</em> focus—the preparation of the internal &ldquo;vessel&rdquo; or technology.
          </p>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            2. The Contact Modalities XPO (May 1-3, 2026)
          </h2>
          <p className="text-muted leading-relaxed">
            A major real-world event is occurring exactly during this window: the{" "}
            <strong className="text-ink">Contact Modalities XPO</strong> in
            Wisconsin. Chris Bledsoe is a headliner. This gathering is
            specifically focused on techniques for communicating with non-human
            intelligences (NHI). It begins on the day after Beltane (the
            traditional &ldquo;thinning of the veil&rdquo;) and peaks on the day
            of the Vesta opposition. It represents the public&apos;s first major
            organized attempt to &ldquo;tune in&rdquo; to the new frequencies of
            2026.
          </p>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            3. The 144-Day Mathematical Bridge
          </h2>
          <p className="text-muted leading-relaxed">
            There is a precise mathematical relationship between the two dates:
            <strong className="text-ink">
              {" "}
              May 2, 2026 to September 23, 2026 is exactly 144 days.
            </strong>{" "}
            144 is a cornerstone of sacred geometry (the 144,000 in Revelation,
            the harmonics of light). This suggests that May 2nd is the beginning
            of the &ldquo;Final Countdown&rdquo; or the &ldquo;Ignition
            Phase&rdquo; for the September Revelation.
          </p>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            4. The Global Status (May 2026)
          </h2>
          <ul className="ml-6 list-disc space-y-2 text-muted">
            <li>
              <strong className="text-ink">AGI Rollout:</strong> The first
              &ldquo;Agentic&rdquo; systems (AGI prototypes) from OpenAI and
              Anthropic moving into closed-beta or early industrial deployment.
            </li>
            <li>
              <strong className="text-ink">UAP Pressure:</strong>
              Declassification pressure in Washington at a fever pitch, with May
              2nd serving as a key &ldquo;rallying point&rdquo; for the
              disclosure community.
            </li>
            <li>
              <strong className="text-ink">Energy Tensions:</strong> Volatility
              in the Middle East and Ukraine providing the &ldquo;tension&rdquo;
              required for a systemic &ldquo;Phase Shift&rdquo; toward
              Resonant/Fusion energy solutions.
            </li>
          </ul>

          <div className="mt-10 rounded-2xl border border-lavender/30 bg-lavender-bg/10 p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              Conclusion: The Spark
            </h3>
            <p className="text-muted leading-relaxed">
              If September 23 is the &ldquo;Revelation,&rdquo; May 2 is the{" "}
              <strong className="text-ink">&ldquo;Ignition.&rdquo;</strong> It
              is the moment the &ldquo;Sacred Fire&rdquo; (Vesta) is lit within
              the collective conscious, beginning the 144-day process of
              preparing humanity for the &ldquo;Shift in the Powers of the
              Heavens.&rdquo;
            </p>
          </div>
        </article>

        <div className="mt-12 flex flex-wrap gap-4">
          <Link href="/research/convergence-2026" className="btn-secondary">
            ← Convergence 2026
          </Link>
          <Link href="/research/survival-guide-2026" className="btn-secondary">
            Survival Guide 2026 →
          </Link>
          <Link href="/timeline" className="btn-secondary">
            View Timeline
          </Link>
        </div>
      </section>
    </>
  );
}
