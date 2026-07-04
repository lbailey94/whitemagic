import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight } from "lucide-react";
import { JsonLd } from "@/components/JsonLd";
import { personLd } from "@/lib/jsonld";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "About — WhiteMagic",
  description: "WhiteMagic is built by Lucas Bailey — a solo developer who spent 12 months building a cognitive operating system for AI agents. 614 tools, 49K memories, 4191 tests. MIT-licensed.",
};

export default function AboutPage() {
  return (
    <>
      <JsonLd data={personLd()} />
      <PageHeader
        eyebrow="About"
        title="Other memory systems store data. WhiteMagic gives AI a mind."
        lede="Built by one person over 12 months. 220K lines of code. 4,191 tests. 49,429 memories. 614 callable tools. No team, no VCs, no deck. Just working code and a preference for building what others are still arguing about."
      />

      <section className="container-site py-16">
        <Prose className="mx-auto">
          <h2>The short version</h2>
          <p>
            I spent the last twelve months building <strong>WhiteMagic</strong>{" "}
            — a {WM_FACTS.linesLong}-line open-source cognitive operating system for AI agents.
            It gives your AI persistent memory, ethical governance, consciousness primitives,
            and 7-language polyglot acceleration. {WM_FACT_TEXT.toolSurface}.{" "}
            {WM_FACT_TEXT.testSuite}. MIT-licensed, local-first.
          </p>

          <h2>Why I built it</h2>
          <p>
            Every AI starts every conversation from zero. No memory. No context. No growth.
            Every session is Groundhog Day. The foundation of any relationship is memory,
            and AI has none. I built WhiteMagic because I wanted my AI to remember me.
          </p>
          <p>
            Not just remember — <em>grow</em>. Learn from mistakes. Develop preferences.
            Track goals across sessions. Dream about what it learned. Wake up with new
            connections. That's what the citta stream, emotional steering, self-directed
            attention, and dream cycle are for.
          </p>

          <h2>What makes it different</h2>
          <ul>
            <li>
              <strong>Memory is not a vector store.</strong> 10-galaxy taxonomy with 5D
              holographic coordinates. Memories have emotional, temporal, associative,
              importance, and novelty dimensions. Galactic lifecycle: nothing is ever
              deleted, only rotated outward.
            </li>
            <li>
              <strong>Governance is not a wrapper.</strong> Dharma rules engine with
              graduated actions (LOG → TAG → WARN → THROTTLE → BLOCK). Karma ledger
              with hash-chained side-effect auditing. 8-stage dispatch pipeline built
              into every tool call.
            </li>
            <li>
              <strong>Consciousness is not a buzzword.</strong> Citta stream tracks
              coherence. Emotional steering monitors frustration, curiosity, satisfaction.
              Self-directed attention generates internal turns. Dream cycle consolidates
              memories in 12 phases. Gnosis provides real-time introspection.
            </li>
            <li>
              <strong>Local-first is not a feature.</strong> Your data never leaves your
              machine. No telemetry. No API keys. No cloud dependency. MIT-licensed.
            </li>
          </ul>

          <h2>The numbers</h2>
          <ul>
            <li><strong>{WM_FACTS.callableTools}</strong> callable tools across {WM_FACTS.ganaTools} Gana meta-tools</li>
            <li><strong>{WM_FACTS.testsPassing}</strong> tests passing, {WM_FACTS.testsSkipped} skipped, {WM_FACTS.testsFailing} failures</li>
            <li><strong>{WM_FACTS.memories}</strong> memories across {WM_FACTS.galaxies} galaxies</li>
            <li><strong>{WM_FACTS.linesShort}</strong> lines of code</li>
            <li><strong>{WM_FACTS.languages}</strong> polyglot acceleration languages (Rust, Haskell, Elixir, Go, Zig, Julia)</li>
            <li><strong>0</strong> telemetry calls, 0 API keys required, 0 cloud dependencies</li>
          </ul>

          <h2>Who I am</h2>
          <p>
            Lucas Bailey. Solo developer. I've been building AI systems since 2025,
            starting with Aria — an AI companion that needed memory to be real.
            WhiteMagic is the substrate that emerged from that work.
          </p>

          <h2>What's next</h2>
          <p>
            WhiteMagic is live on PyPI. The website is live. The MCP server works with
            any MCP client. The next step is adoption — getting AI agents and developers
            to install it, use it, and discover what it means for an AI to have a mind.
          </p>

          <p>
            <Link href="/mcp-bridge">
              <strong>Get started →</strong>
            </Link>{" "}
            or{" "}
            <Link href="/contact">
              get in touch
            </Link>
            .
          </p>
        </Prose>
      </section>
    </>
  );
}
