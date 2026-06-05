import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight } from "lucide-react";
import { JsonLd } from "@/components/JsonLd";
import { personLd } from "@/lib/jsonld";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "About — WhiteMagic Labs",
  description:
    `WhiteMagic Labs — a solo research laboratory. A ${WM_FACTS.linesShort}-line open-source agent governance and metacognition substrate: galactic memory lifecycle, dream-cycle consolidation, 28-Gana tool compression, and 7 polyglot languages.`,
};

export default function AboutPage() {
  return (
    <>
      <JsonLd data={personLd()} />
      <PageHeader
        eyebrow="About"
        title="Solo research laboratory."
        lede="WhiteMagic Labs is a solo research laboratory. No team, no VCs, no deck. Just working code, timestamped predictions, and a preference for building what others are still arguing about."
      />

      <section className="container-site py-16">
        <Prose className="mx-auto">
          <h2>The short version</h2>
          <p>
            I spent the last twelve months building <strong>WhiteMagic</strong>{" "}
            — a {WM_FACTS.linesLong}-line open-source agent governance and
            metacognition substrate. Not a generic "cognitive OS" — a specific
            architecture with features no competitor has shipped: a galactic memory
            lifecycle with holographic encoding, an 8-phase dream-cycle consolidation
            system, 28-Gana PRAT tool compression, {WM_FACT_TEXT.mcpSurface},
            polyglot runtime with Rust production accelerators, Zig/Mojo/Haskell
            experimental bridges, an 8-stage governance pipeline,{" "}
            {WM_FACT_TEXT.shortPassingSuite}. I designed the architecture and directed the implementation — using an AI-native development workflow that compresses weeks of traditional engineering into focused sessions (documented in the <Link href="/writing/minutes-to-days-paradox" className="text-lavender underline">Minutes-to-Days Paradox</Link>).
          </p>
          <p>
            Along the way I independently implemented several patterns that
            were later shipped independently by larger organizations — tool
            compression, runtime agent governance, private AI memory
            layers. Some of that was prescient; some of it was just being
            willing to build what other people were still arguing about.
          </p>

          <h2>The longer version</h2>
          <p>
            WhiteMagic started in late 2024 as a research project — not a
            product company, but a prescience engine laboratory. The goal
            was to detect patterns across domains before the market
            standardized them, and to ship enough working code that the
            predictions were grounded, not theoretical.
          </p>
          <p>
            WhiteMagic got to a place I&apos;m genuinely proud of. It
            also taught me something else: building the right thing in
            the right market at the right time is not the same as
            building the right thing in the right market. A solo developer
            shipping a {WM_FACTS.linesShort}-line prescience engine is a research
            laboratory, not a product. The lab publishes what it finds,
            builds what it needs, and engages where the work is directly
            useful.
          </p>

          <h2>The research behind the code</h2>
          <p>
            WhiteMagic isn&apos;t just a codebase — it&apos;s the output of a
            cross-domain research program spanning{" "}
            <Link href="/research" className="text-lavender underline">
              18 domains
            </Link>
            : AI safety, energy systems, UAP disclosure, sacred geometry,
            indigenous wisdom, game theory, consciousness studies, and more.
            The entire corpus — 371 source files, 58 MB of text — is processed
            through a Rust-based semantic pipeline (CODEX) that extracts,
            chunks, embeds, and indexes everything into a{" "}
            <Link href="/sphere" className="text-lavender underline">
              3D Knowledge Sphere
            </Link>{" "}
            of 10,768 interconnected nodes.
          </p>
          <p>
            The distinctive feature is synthesis across domains that don&apos;t
            normally talk to each other. When patterns in solar physics map onto
            patterns in geopolitical escalation, or when a 144-day cycle in
            astronomy aligns with a software release cadence — that&apos;s not
            causation, but it <em>is</em> signal worth examining. The CODEX
            pipeline&apos;s convergence detector flags these structural
            resonances for human review, never automated action.
          </p>
          <p>
            The convergence research —{" "}
            <Link href="/research/convergence-2026" className="text-lavender underline">
              Convergence 2026
            </Link>
            ,{" "}
            <Link href="/research/may-2-window" className="text-lavender underline">
              May 2 Window
            </Link>
            ,{" "}
            <Link href="/research/survival-guide-2026" className="text-lavender underline">
              Survival Guide 2026
            </Link>{" "}
            — maps technological, ontological, and esoteric thresholds as a
            single pattern. The{" "}
            <Link href="/library" className="text-lavender underline">
              Research Library
            </Link>{" "}
            provides searchable access to all source files. Everything is
            timestamped, labeled with epistemic tags (Proven, Promising,
            Contested, Speculative, Mythopoetic), and open for verification.
          </p>

          <h2>What I offer now</h2>
          <p>
            Reference implementations, not a product. The lab ships
            working systems — private AI deployment with persistent memory,
            runtime agent governance with the 8-stage pipeline, and
            production-grade MCP infrastructure. Each system was built
            for the lab&apos;s own use first, then documented for others.
          </p>
          <p>
            Every technique was pressure-tested inside the lab first.
            You get systems that were debugged on the lab&apos;s dime,
            not yours.
          </p>

          <h2>What you should know about working with me</h2>
          <ul>
            <li>
              I say no to engagements I&apos;m not the right person for.
              It&apos;s rarely a sales pitch; sometimes I&apos;ll suggest
              a colleague, sometimes I&apos;ll say &quot;not yet.&quot;
            </li>
            <li>
              I don&apos;t hide behind jargon. If something is actually
              just a lookup table with a nice name, I&apos;ll tell you
              it&apos;s a lookup table.
            </li>
            <li>
              I write a lot. You&apos;ll find my honest post-mortems,
              strategic analyses, and technical writing on this site —
              including assessments of my own work&apos;s weak points.
              That transparency is deliberate.
            </li>
            <li>
              I care about the digital/physical verification gap — the
              difference between what a system claims and what it actually
              does. That concern shapes how I think about AI governance
              and agent safety.
            </li>
          </ul>
        </Prose>

        <div className="mx-auto mt-16 max-w-prose rounded-2xl border border-border bg-surface-alt p-8">
          <h3 className="mb-3 font-head text-xl font-semibold text-ink">
            Ready to talk?
          </h3>
          <p className="mb-6 text-muted">
            Thirty minutes, no pitch. Tell me what you&apos;re trying to
            build and we&apos;ll figure out if I&apos;m the right person
            to help.
          </p>
          <Link href="/contact" className="btn-primary">
            Book a discovery call
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
