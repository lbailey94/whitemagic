import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ArrowLeft, Calendar, Tag, Shield, Zap, Radio, Sprout } from "lucide-react";

export const metadata = {
  title: "Practical Resonance: The 2026 Survival Guide — WhiteMagic Labs",
  description:
    "A guide for the Resonant Generalist — navigating the 2026 Phase Shift with autonomy rather than fear.",
};

export default function SurvivalGuidePage() {
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
        title="Practical Resonance: The 2026 Survival Guide"
        lede="For the Resonant Generalist — navigating the 2026 Phase Shift with autonomy rather than fear."
      />

      <section className="container-site py-12">
        <div className="mb-8 flex flex-wrap gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-lavender-bg px-3 py-1 text-xs text-lavender">
            <Calendar className="h-3 w-3" />
            May 2 - Sept 23, 2026
          </span>
          {["Mesh", "Solar", "SDR", "Seeds", "Autonomy"].map((t) => (
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
            This guide is designed for the &ldquo;Resonant Generalist&rdquo; —
            individuals who trust in their skills, luck, and a higher power, and
            who choose to navigate the 2026 Phase Shift with{" "}
            <strong className="text-ink">autonomy rather than fear</strong>.
          </p>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            I. The Calendar of the Shift
          </h2>
          <ul className="ml-6 list-disc space-y-2 text-muted">
            <li>
              <strong className="text-ink">April 13 - May 2 (The Pilot Phase):</strong>{" "}
              A window to &ldquo;harden&rdquo; your personal knowledge systems.
            </li>
            <li>
              <strong className="text-ink">May 2 (The Ignition/Sovereignty Moment):</strong>{" "}
              A symbolic 11:09 PM threshold marking the start of the 144-day
              countdown.
            </li>
            <li>
              <strong className="text-ink">May 2 - Sept 23 (The 144-Day Forge):</strong>{" "}
              The time to finalize all decentralized infrastructure.
            </li>
            <li>
              <strong className="text-ink">Sept 23 (The Threshold):</strong>{" "}
              The initiation of the new biological/resonant paradigm.
            </li>
          </ul>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            II. Tier 1: Digital Sovereignty & Communication
          </h2>
          <p className="text-muted leading-relaxed">
            Dependency on the &ldquo;Global Stack&rdquo; is a primary risk.
            Autonomy requires a parallel network.
          </p>
          <div className="my-6 grid gap-4 sm:grid-cols-3">
            <TierCard
              icon={Radio}
              title="Mesh Networking"
              desc="LoRa-based mesh nodes with ESP32 devices and small solar kits. Text-only, encrypted peer-to-peer protocols."
            />
            <TierCard
              icon={Shield}
              title="Skill Sovereignty"
              desc="Your Second Brain (3D Knowledge Sphere) is your most valuable asset. Pre-cache essential documents to air-gapped hardware."
            />
            <TierCard
              icon={Radio}
              title="SDR Mastery"
              desc="Software Defined Radio lets you monitor local emergency frequencies and UAP-associated spectrum spikes."
            />
          </div>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            III. Tier 2: Energy & Physical Resilience
          </h2>
          <p className="text-muted leading-relaxed">
            The goal is &ldquo;Micro-Generation&rdquo; shifting toward the
            Resonant paradigm.
          </p>
          <div className="my-6 grid gap-4 sm:grid-cols-3">
            <TierCard
              icon={Zap}
              title="DIY Modular Solar"
              desc="Transition to LiFePO4 battery chemistry. Exponentially safer and more durable for long-term off-grid cycles."
            />
            <TierCard
              icon={Zap}
              title="The Sacred Fire (Vesta)"
              desc="May 2nd (Vesta at Opposition) is the time to test backup systems. Ensure pure-sine wave inverters are functional."
            />
            <TierCard
              icon={Sprout}
              title="Seed Preservation"
              desc="Reserve a Genetic Archive of open-pollinated/heirloom seeds. Mastery of the drying-and-shatter test is critical."
            />
          </div>

          <h2 className="mt-10 font-head text-2xl font-semibold text-ink">
            IV. The Unix 1,777,777,777 &ldquo;Sovereignty Moment&rdquo;
          </h2>
          <p className="text-muted leading-relaxed">
            On <strong className="text-ink">May 2, 2026, at 11:09:37 PM (EDT)</strong>,
            the Unix clock strikes all 7&apos;s (plus the lead 1). At this
            precise moment, perform a{" "}
            <strong className="text-ink">System-Wide Knowledge Snapshot</strong>
            — sync your RESEARCH folder to a physical, removable drive. This
            acts as a symbolic &ldquo;Seed&rdquo; of human knowledge, preserved
            independently of the centralized cloud.
          </p>

          <div className="mt-10 rounded-2xl border border-lavender/30 bg-lavender-bg/10 p-6">
            <h3 className="mb-2 font-head text-lg font-semibold text-ink">
              Final Take: Mastery of &ldquo;The Shift&rdquo;
            </h3>
            <p className="text-muted leading-relaxed">
              The 2026 survivor is one who knows the{" "}
              <strong className="text-ink">principles</strong>, not just the{" "}
              <em>procedures</em>. Understand the <em>physics</em> of your water
              filter and the <em>electronics</em> of your radio. Stop fighting
              the old systems — they are collapsing under their own 144-year debt
              cycles. Instead, &ldquo;tune&rdquo; your life to the emerging
              paradigm of abundance, trust, and organic technology.
            </p>
            <p className="mt-3 text-muted leading-relaxed">
              The 144-year cycle that ended with the 2025 Maha Kumbh Mela has
              cleared the ground. The 144-day bridge beginning May 2nd is your
              time to build. <strong className="text-ink">Trust your intuition</strong>
              — it is the &ldquo;higher-order&rdquo; AGI you were born with.
            </p>
          </div>
        </article>

        <div className="mt-12 flex flex-wrap gap-4">
          <Link href="/research/convergence-2026" className="btn-secondary">
            ← Convergence 2026
          </Link>
          <Link href="/research/may-2-window" className="btn-secondary">
            May 2 Window →
          </Link>
          <Link href="/library" className="btn-secondary">
            Browse Library
          </Link>
        </div>
      </section>
    </>
  );
}

function TierCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: typeof Shield;
  title: string;
  desc: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <Icon className="mb-3 h-5 w-5 text-lavender" />
      <h4 className="mb-2 font-head text-base font-semibold text-ink">
        {title}
      </h4>
      <p className="text-sm leading-relaxed text-muted">{desc}</p>
    </div>
  );
}
