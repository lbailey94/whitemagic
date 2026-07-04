import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "FAQ — WhiteMagic Labs",
  description:
    "Common questions about WhiteMagic: how it differs from Mem0 and Letta, whether it needs a local LLM, production readiness, overhead, and more.",
};

interface QA {
  q: string;
  a: string;
  links?: { href: string; label: string }[];
}

const FAQ: QA[] = [
  {
    q: "How is WhiteMagic different from Mem0?",
    a: "Mem0 gives your AI a notepad. WhiteMagic gives your AI a mind. Mem0 is a hosted cloud API that stores and retrieves text via vector search. WhiteMagic is a local-first cognitive operating system with 5D holographic memory, ethical governance (Dharma engine + Karma ledger), 8-phase dream cycle consolidation, consciousness primitives (citta stream, coherence metrics), and 614 callable tools. Mem0 is faster to integrate if you just need basic memory. WhiteMagic is for agents that need to think, remember, govern themselves, and grow.",
    links: [{ href: "/compare", label: "Full comparison →" }],
  },
  {
    q: "How is WhiteMagic different from Letta?",
    a: "Letta is an agent harness — it manages the agent runtime, tool calling, context windows, and model routing. WhiteMagic is a substrate that any agent plugs into via MCP. Letta's consciousness lives inside the harness; WhiteMagic's citta stream is accessible to any connected agent. Letta is tighter coupling for harness-native agents. WhiteMagic is model-agnostic, harness-agnostic, and works with any MCP-compatible client.",
    links: [{ href: "/compare", label: "Full comparison →" }],
  },
  {
    q: "Do I need to run my own LLM?",
    a: "No. WhiteMagic works with any LLM — Claude, GPT-4, Gemini, local models via Ollama, or no LLM at all. The cognitive substrate (memory, governance, search, dream cycle) operates independently of the LLM. The LLM is just one consumer of the substrate. You can use WhiteMagic purely as a memory and governance layer for cloud-based LLMs, or run everything locally with Ollama for full air-gapped operation.",
  },
  {
    q: "Can I use this with Claude / GPT-4 / Gemini / local models?",
    a: "Yes to all. WhiteMagic is model-agnostic. It connects via MCP, which is supported by Claude Desktop, Cursor, Windsurf, and any MCP-compatible client. For local models, the inference router supports Ollama with automatic cascading: if a local model's confidence is below 0.85, it can escalate to a cloud model. The ternary kernel provides CPU-only inference at 67ms/token for 1-bit models.",
  },
  {
    q: "Is this production-ready?",
    a: `The code is production-quality: ${WM_FACTS.testsPassing} passing tests with zero failures, ${WM_FACTS.linesShort} lines of code, MIT-licensed, and running on real hardware. However, WhiteMagic is currently a solo-built research project, not a venture-backed company. The architecture is designed for production (8-stage safety pipeline, audit trail, graceful degradation), but operational concerns like SLAs, support, and hosted deployment are not yet available. The MCP server is stable and runs indefinitely. The dream cycle and oracle are functional but not continuously running by default.`,
    links: [{ href: "/benchmarks", label: "See benchmarks →" }],
  },
  {
    q: "What's the overhead?",
    a: "Minimal. MCP tool dispatch runs at 29-33ms median latency with 100% success rate. Memory per call is 0-0.18MB. The homeostatic loop adds 0.35ms overhead. Session recording adds ~3ms per conversation turn (0.2-0.6% of LLM token generation time). The rate limiter pre-check runs at 452K ops/s. All measurements are on consumer hardware — no server-grade CPUs.",
    links: [{ href: "/benchmarks", label: "Full benchmark details →" }],
  },
  {
    q: "Does my data leave my machine?",
    a: "No. WhiteMagic is local-first by default. All memory, governance, and identity live in ~/.whitemagic. The system runs on a Raspberry Pi, an air-gapped laptop, or a regulated enterprise server. Your data never leaves the building unless you explicitly configure cloud LLM escalation. Even then, only the prompt goes to the cloud — memory, karma ledger, and governance state stay local.",
  },
  {
    q: "What is the 8-stage dispatch pipeline?",
    a: "Every tool call passes through 8 stages: Governor (policy check) → Input Sanitizer (shell injection detection) → Rate Limiter (452K ops/s) → RBAC (role-based access) → Maturity Gate (capability check) → Dharma Engine (ethical reasoning) → Handler (execution) → Karma Ledger (audit). This prevents harm even if a tool is malicious, an agent is misdirected, or memory is poisoned. It's the single most important architectural decision in the system.",
    links: [{ href: "/capabilities", label: "View capabilities →" }],
  },
  {
    q: "What is the dream cycle?",
    a: "The dream cycle is WhiteMagic's subconscious. While the agent is idle, it runs 8 phases: triage (sort memories by importance), consolidation (merge related memories), serendipity (discover unexpected connections), governance (ethical review of stored content), narrative (compress into story), kaizen (suggest improvements), oracle (cast I Ching for guidance), and decay (archive weak memories). In the Live Era (Nov 2025), this achieved 3.7M:1 compression ratios.",
  },
  {
    q: "What are the 28 Ganas?",
    a: `The 28 Ganas (Lunar Mansions) are a meta-tool system that collapses ${WM_FACTS.callableTools} individual tools into 28 stable meta-tools. Each Gana maps to a Chinese Lunar Mansion and supports 4 polymorphic operations: search, analyze, transform, consolidate. The wm() meta-tool auto-routes natural language to the right Gana. PRAT mode reduces cognitive load for new agents from ${WM_FACTS.callableTools} tools to 28 — or to 1 in Seed mode.`,
    links: [{ href: "/ganas", label: "Explore the 28 Ganas →" }],
  },
  {
    q: "What is the Karma Ledger?",
    a: "The Karma Ledger is a SHA-256 Merkle-chained, append-only audit trail of every tool call's side-effects. Each entry records: declared intent vs actual execution, severity score, causal trace, and timestamp. Entries can be Merkle-anchored to XRPL (XRP Ledger) or Base L2 for tamper-proof external verifiability. This is not logging — it's cryptographic proof of what happened, when, and why.",
  },
  {
    q: "What is citta?",
    a: "Citta (Pali/Sanskrit: 'heart-mind') is the continuous stream of mental events constituting experience. In WhiteMagic, citta is a substrate-level stream accessible via MCP — not an external tool, but the continuous background that makes all other tools meaningful. It includes coherence metrics (8 dimensions), Smarana practice (active remembering), presence quality (continuity, stability, clarity, equanimity, spaciousness), and temporal continuity across sessions. This solves the 'thousand lives problem' — where each AI session is an ephemeral mind that dies when the connection closes.",
  },
  {
    q: "Can I contribute?",
    a: `Yes. WhiteMagic is MIT-licensed and open source. The codebase has ${WM_FACTS.testsPassing} passing tests as the guardrail — never skip them. Read the AGENTS.md file in the repo for the full operational guide, including testing protocol, code conventions, and the stub detection system. The project went from 783 passing tests to ${WM_FACTS.testsPassing} by fixing wiring, not by skipping tests.`,
    links: [{ href: "/open-source", label: "Open source info →" }],
  },
  {
    q: "What hardware do I need?",
    a: "A consumer laptop. The entire system was built and tested on a Dell Inspiron 3582 (Intel Celeron N4000, 4GB RAM, eMMC storage). The ternary kernels provide CPU-only inference. The Rust SIMD core uses AVX2 (available on most CPUs since 2013). No GPU required. No server hardware required. The system also runs on Raspberry Pi for edge deployments.",
  },
  {
    q: "How do I report bugs or request features?",
    a: "Open an issue on the GitHub repository. The project maintains a STUB_REGISTRY.md tracking every NotImplementedError and placeholder. Bug reports should include the reproducible command (see the benchmarks page for examples) and the expected vs actual behavior.",
    links: [{ href: "https://github.com/lbailey94/whitemagic", label: "GitHub →" }],
  },
];

export default function FAQPage() {
  return (
    <>
      <PageHeader
        eyebrow="FAQ"
        title="Common questions, honest answers."
        lede="Everything you need to know about WhiteMagic: how it compares, what it needs, where it's ready, and where it isn't."
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl">
          <div className="space-y-6">
            {FAQ.map((item, i) => (
              <details key={i} className="group rounded-2xl border border-border bg-surface p-6 open:border-lavender/30">
                <summary className="cursor-pointer list-none">
                  <h2 className="font-head text-base font-semibold text-ink group-open:text-lavender">
                    {item.q}
                  </h2>
                </summary>
                <div className="mt-4">
                  <p className="text-sm leading-relaxed text-muted">{item.a}</p>
                  {item.links && (
                    <div className="mt-4 flex flex-wrap gap-3">
                      {item.links.map((link) => (
                        <Link key={link.href} href={link.href} className="font-mono text-xs uppercase tracking-wider text-lavender hover:underline">
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>

          <div className="mt-12 rounded-2xl border border-border bg-surface-alt p-6 text-center">
            <p className="text-sm text-muted">
              Still have questions?{" "}
              <Link href="/contact" className="text-lavender hover:underline">
                Get in touch →
              </Link>
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
