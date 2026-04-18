import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight } from "lucide-react";

export const metadata = {
  title: "About — WhiteMagic Labs",
  description:
    "WhiteMagic Labs is Lucas — a self-taught engineer who built a 170K-line cognitive OS for AI agents before the market caught up.",
};

export default function AboutPage() {
  return (
    <>
      <PageHeader
        eyebrow="About"
        title="Self-taught. Already shipped."
        lede="WhiteMagic Labs is me, Lucas. No team, no VCs, no deck. Just the work, the repositories that prove it, and a preference for doing things honestly."
      />

      <section className="container-site py-16">
        <Prose className="mx-auto">
          <h2>The short version</h2>
          <p>
            I spent the last six months building <strong>WhiteMagic</strong>{" "}
            — a 170,000-line open-source cognitive operating system for AI
            agents. Persistent memory, 374 MCP tools across 28 categories,
            11-language polyglot architecture with Rust and Zig performance
            bridges, an 8-stage governance pipeline, 1,300+ passing tests.
            I designed it, wrote it, and shipped it solo.
          </p>
          <p>
            Along the way I independently invented several patterns that
            have since been shipped by larger organizations — tool
            compression, runtime agent governance, private AI memory
            layers. Some of that was prescient; some of it was just being
            willing to build what other people were still arguing about.
          </p>

          <h2>The longer version</h2>
          <p>
            No formal CS education. No prior job in tech or an office.
            I&apos;ve worked drones, construction, hospitality. In October
            2025 I started building on AI seriously — not as a product
            company, but as a lab. The goal was to push hard on the shape
            of what an agent memory system could look like, and to ship
            enough working code that the design trade-offs were real,
            not theoretical.
          </p>
          <p>
            WhiteMagic got to a place I&apos;m genuinely proud of. It
            also taught me something else: building the right thing in
            the right market at the right time is not the same as
            building the right thing in the right market. A solo developer
            shipping a 170K-line platform is a research project, not a
            product. I&apos;m making peace with that and turning the
            hard-won expertise into something that actually helps teams
            I can reach.
          </p>

          <h2>What I offer now</h2>
          <p>
            Services, not a product. Private AI deployment for regulated
            teams who can&apos;t send privileged material to hosted APIs.
            Agent governance for teams putting autonomous systems into
            production and feeling the OWASP Top 10 close in. MCP
            engineering for anyone serious about agent infrastructure.
          </p>
          <p>
            Every technique I deploy has been pressure-tested inside
            WhiteMagic first. You get an engineer who has already made
            the expensive mistakes on his own time.
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
              I run a drone business on the side (Seaglass Aerial &amp;
              Marine). I mention it because it&apos;s where I first
              started caring about the digital/physical verification
              gap that has since become part of my thinking on AI.
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
