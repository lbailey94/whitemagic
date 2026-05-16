import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { TimelineHorizontal } from "@/components/TimelineHorizontal";
import { FIELD_CONCLUSIONS, FIELD_MAP_UPDATED } from "@/lib/field-map";

export const metadata = {
  title: "Timeline — WhiteMagic Labs",
  description:
    "A month-by-month record of what WhiteMagic shipped and when the industry standardized the same patterns. Every date is verifiable against public sources.",
};

export default function TimelinePage() {
  return (
    <>
      <PageHeader
        eyebrow="Timeline"
        title="What I shipped, and when the industry caught up."
        lede="A chronological record of WhiteMagic releases, industry milestones, and regulatory events. Filter by category. Click through the sources."
      />

      <section className="border-b border-border-light bg-surface-alt py-10">
        <div className="container-site mx-auto max-w-3xl space-y-4 text-muted">
          <p>
            Every WhiteMagic entry below has a{" "}
            <strong className="text-fg">ship date</strong> from{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-sm">
              CHANGELOG.md
            </code>
            . Every industry entry links to a{" "}
            <strong className="text-fg">verifiable public source</strong> —
            Microsoft&apos;s blog, Anthropic&apos;s releases, the OWASP Top 10 PDF,
            the MCP roadmap document, and current protocol documentation.
          </p>
          <p>
            I&apos;m not claiming to have invented everything first. Several
            of these I shipped in <em>parallel</em> with much larger teams. A
            few I was genuinely ahead on. A few were downstream of ideas that
            were already in the water. The pattern is what matters:{" "}
            <strong className="text-fg">
              shipping working code, not decks, while the rest of the industry
              was still writing position papers.
            </strong>
          </p>
          <p>
            The purple curve behind the timeline is the{" "}
            <strong className="text-fg">technological singularity</strong> — the
            exponential ramp in AI capability that began trending upward in the
            early 2020s (GPT-3 → ChatGPT → GPT-4 → Claude 3) and accelerated
            through 2025 and 2026. The events below aren&apos;t a flat
            sequence; they&apos;re nodes on that curve. WhiteMagic shipped at
            the inflection points — when the slope was steepest and most
            people were still arguing whether the slope existed at all.
          </p>
          <div className="rounded-2xl border border-border bg-surface p-5">
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
              Current conclusion · updated {FIELD_MAP_UPDATED}
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {FIELD_CONCLUSIONS.map((item) => (
                <article key={item.title}>
                  <h2 className="mb-1 font-head text-base font-semibold text-ink">
                    {item.title}
                  </h2>
                  <p className="text-sm leading-relaxed text-muted">
                    {item.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
          <p className="flex flex-wrap gap-4 pt-2 text-sm">
            <LegendDot label="WhiteMagic" color="bg-lavender" />
            <LegendDot label="Industry & standards" color="bg-muted" />
            <LegendDot
              label="Regulatory"
              color="bg-lavender-dark dark:bg-lavender-light"
            />
            <span className="flex items-center gap-2 text-muted">
              <span
                className="h-3 w-3 rounded-full border-2 border-lavender"
                aria-hidden="true"
              />
              <span>Highlighted / key event</span>
            </span>
          </p>
        </div>
      </section>

      <TimelineHorizontal />

      <section className="border-y border-border-light bg-surface-alt py-16">
        <div className="container-site mx-auto max-w-3xl">
          <p className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
            Honest misses
          </p>
          <h2 className="mb-5 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Where I was wrong, or wrong on timing.
          </h2>
          <p className="mb-6 max-w-prose text-muted">
            Every prescience list is suspect without its counterpart. Three bets
            from the same period that didn&apos;t play out — or haven&apos;t
            yet:
          </p>
          <ul className="space-y-4">
            <Miss
              title="Memory-as-a-service as a standalone business"
              body="I assumed there was a durable independent category here. Instead, platforms (Anthropic, Microsoft, OpenAI) absorbed memory as a first-party feature. The technique still has value; the standalone-business thesis does not."
            />
            <Miss
              title="Governance as a defensible solo-developer moat"
              body="I believed 'no one else is emphasizing governance-first' in late 2025. By April 2026, TrueFoundry, agentregistry, Smithery, and the AAIF working group were all in the lane — and Microsoft shipped essentially the same architecture under their brand. The technique is still valuable as a service; the moat thesis was wrong."
            />
            <Miss
              title="Agent marketplaces and micropayments at 2026 scale"
              body="I built OMS (.mem portable packages) and XRPL integration on a thesis that agent-to-agent payment rails would mature quickly enough to become a near-term business center. The rails are real; the better near-term posture is readiness, audit, and voluntary contribution infrastructure."
            />
          </ul>
        </div>
      </section>

      <section className="container-site py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-5 font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            What this means for you.
          </h2>
          <p className="mb-8 text-lg text-muted">
            When I show up to an engagement, the patterns I deploy aren&apos;t
            speculation — they&apos;re the same ones I was shipping while the
            rest of the industry was still writing position papers. You get a
            consultant who has already walked the design trade-offs on his own
            time, on his own dime.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/contact" className="btn-primary">
              Book a discovery call
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/services" className="btn-ghost">
              See the services
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function LegendDot({ label, color }: { label: string; color: string }) {
  return (
    <span className="flex items-center gap-2 text-muted">
      <span className={`h-3 w-3 rounded-full ${color}`} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

function Miss({ title, body }: { title: string; body: string }) {
  return (
    <li className="rounded-2xl border border-dashed border-border bg-surface p-5">
      <h3 className="mb-1.5 font-head text-lg font-semibold text-ink">
        {title}
      </h3>
      <p className="text-muted">{body}</p>
    </li>
  );
}
