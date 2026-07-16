import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";
import { Brain, Database, Shield, Cpu, ArrowRight, ExternalLink } from "lucide-react";

export const metadata = {
  title: "The Bitter Lesson, Applied — WhiteMagic",
  description:
    "Richard Sutton's Bitter Lesson says general methods that leverage computation beat human-knowledge encodings. We apply it to our own harness — and respond to the critique of LLM-generated knowledge bases.",
};

const SUTTON_LESSON = [
  {
    quote:
      "The biggest lesson from 70 years of AI research is that general methods that leverage computation are ultimately the most effective, and by a large margin.",
    source: "Richard Sutton, The Bitter Lesson, 2019",
  },
  {
    quote:
      "Search and learning are the two most important classes of techniques for scaling computation.",
    source: "Sutton, ibid.",
  },
  {
    quote:
      "We have to learn the bitter lesson that building in how we think we think does not work in the long run.",
    source: "Sutton, ibid.",
  },
];

const HARNESS_AUDIT = [
  {
    icon: Shield,
    title: "Dharma Rules Engine",
    verdict: "Human-knowledge scaffolding",
    detail:
      "20+ hardcoded YAML rules with keyword patterns like 'surveillance', 'harm', 'deceive'. This is exactly what Sutton warns against — encoding human understanding of 'bad' into static rules. A learned policy that observes outcomes would scale better. But: the rules are hot-reloadable, profile-based, and the engine supports runtime rule addition by AI. The scaffolding is a starting point, not a ceiling.",
    score: "Scaffolding",
    scoreColor: "bg-amber-100 text-amber-700",
  },
  {
    icon: Cpu,
    title: "Governor: Forbidden/Dangerous/Caution Patterns",
    verdict: "Hardcoded regex patterns",
    detail:
      "30+ regex patterns for forbidden commands (rm -rf /, mkfs, fork bombs). This is pure human-knowledge encoding. A learned classifier on command outcomes would be more general. But: the cost of a false negative on rm -rf / is catastrophic and irreversible. The Bitter Lesson applies to performance, not safety floors. Some hardcoded guardrails are seatbelts, not steering wheels.",
    score: "Safety floor",
    scoreColor: "bg-green-100 text-green-700",
  },
  {
    icon: Brain,
    title: "PatternLearner + ConfidenceLearner",
    verdict: "General-purpose learning",
    detail:
      "PatternLearner clusters queries by keyword, extracts common patterns, and generates rules from high-confidence cloud answers. ConfidenceLearner tracks task outcomes and auto-calibrates weight factors based on predictive power. This is the right direction — the system learns from its own experience rather than requiring humans to encode every pattern.",
    score: "Scaling",
    scoreColor: "bg-green-100 text-green-700",
  },
  {
    icon: Database,
    title: "5D Holographic Memory + Galactic Lifecycle",
    verdict: "General-purpose substrate",
    detail:
      "Memory is not encoded as human-knowledge rules. It's a coordinate space (temporal, semantic, emotional, relational, importance) where memories live, decay, and consolidate through the Dream Cycle. The system discovers patterns through clustering, association mining, and constellation formation — not through human-curated taxonomies. This is search and learning over a general substrate.",
    score: "Scaling",
    scoreColor: "bg-green-100 text-green-700",
  },
  {
    icon: Brain,
    title: "SelfModel + SelfDirectedAttention",
    verdict: "General-purpose meta-cognition",
    detail:
      "SelfModel tracks 7 metrics (energy, karma, error rate, dharma score, latency, throughput, balance) with rolling windows and linear regression forecasting. SelfDirectedAttention generates internal imperatives from system state, not from human-scripted routines. The system observes itself and decides what to improve — this is learning at the meta level.",
    score: "Scaling",
    scoreColor: "bg-green-100 text-green-700",
  },
  {
    icon: Cpu,
    title: "28 Gana / PRAT Taxonomy",
    verdict: "Human-knowledge scaffolding — but structurally different",
    detail:
      "28 Lunar Mansion categories mapped to tool domains. This is a human-created taxonomy. But: it's a routing layer, not a knowledge layer. The Ganas don't encode what the system knows — they organize how the system accesses what it knows. The routing can be learned (and the NLU regex in meta_tool.py is a step toward that). The taxonomy is a namespace, not a knowledge base.",
    score: "Scaffolding",
    scoreColor: "bg-amber-100 text-amber-700",
  },
];

const KB_CRITIQUE = [
  {
    point: "LLMs are mostly additive",
    response:
      "WhiteMagic's memory is not additive-only. The Dream Cycle includes 12 phases — triage, consolidation, decay, constellation, narrative compression, kaizen. Memories are ranked, consolidated, and rotated outward through galactic zones. Nothing is deleted, but everything decays. The system actively compresses and reorganizes, not just appends.",
  },
  {
    point: "LLM-generated knowledge bases accumulate useless content",
    response:
      "WhiteMagic separates raw memory (the universal galaxy) from curated memory (the codex galaxy). The codex is built through the CODEX pipeline — 7 Rust crates that extract, chunk, consolidate, and cross-reference. 49,486 raw memories consolidate into 793 consolidated nodes. The ratio is 62:1 compression. Useless content doesn't accumulate — it decays to the Outer Rim.",
  },
  {
    point: "LLM knowledge bases lack verification",
    response:
      "WhiteMagic has a Karma Ledger — an append-only, hash-chained audit trail that tracks declared-vs-actual side effects for every tool call. When the system writes a memory, the write is audited. When the system makes a claim, the claim is tracked. The prescience track record (38 validated claims, Brier score 0.0958) is not LLM-generated assertion — it's empirical validation with timestamps.",
  },
  {
    point: "LLM knowledge bases are opaque",
    response:
      "Every memory in WhiteMagic carries 5D holographic coordinates, galaxy assignment, emotional valence, importance score, and content hash. Every tool call passes through an 8-stage pipeline with full audit trail. The system is introspectable — you can query why a memory exists, when it was created, what it connects to, and how it scored. This is the opposite of a black-box embedding dump.",
  },
  {
    point: "LLM knowledge bases don't compound",
    response:
      "Karpathy's LLM Wiki insight: RAG rediscovers knowledge from scratch every query. WhiteMagic's memory compounds — the Dream Cycle consolidates related memories into constellations, the association miner creates cross-galaxy links (2,853 associations), and the kaizen phase extracts improvement patterns from past sessions. Each session makes the next session more effective. This is the definition of compounding.",
  },
];

const COMPETITIVE_TABLE = [
  { system: "Mem0", approach: "Vector + entity linking", kbCritique: "Removed graph (3x slower, 2x costlier). Mostly additive.", wmAdvantage: "Galactic lifecycle + Dream Cycle consolidation" },
  { system: "Letta", approach: "Self-editing text blocks", kbCritique: "Agent decides what to remember. No verification.", wmAdvantage: "Karma Ledger audits every write" },
  { system: "Cognee", approach: "ECL pipeline → typed graph", kbCritique: "Heavy ingestion cost. No SOC 2 / HIPAA.", wmAdvantage: "Local-first, MIT-licensed, no cloud dependency" },
  { system: "Zep / Graphiti", approach: "Bi-temporal fact graph", kbCritique: "Expensive LLM extraction per episode.", wmAdvantage: "FTS5 + HNSW hybrid search at 0.26ms" },
  { system: "Raw RAG", approach: "Chunk + embed + retrieve", kbCritique: "Nothing accumulates. Rediscovers every query.", wmAdvantage: "Compounding memory with 12-phase Dream Cycle" },
];

export default function BitterLessonPage() {
  return (
    <>
      <PageHeader
        eyebrow="Essay"
        title="The Bitter Lesson, Applied."
        lede="Richard Sutton's lesson is the most important idea in AI. We audit our own harness against it — and respond to the critique that LLM-generated knowledge bases are useless."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-3xl">
          {/* Sutton's Lesson */}
          <div className="mb-16">
            <h2 className="mb-6 font-head text-2xl font-semibold text-ink">
              The lesson
            </h2>
            <div className="space-y-4">
              {SUTTON_LESSON.map((item, i) => (
                <blockquote
                  key={i}
                  className="border-l-2 border-lavender pl-6 py-2"
                >
                  <p className="font-head text-lg italic text-fg leading-relaxed">
                    &ldquo;{item.quote}&rdquo;
                  </p>
                  <cite className="mt-2 block font-mono text-xs text-dim">
                    — {item.source}
                  </cite>
                </blockquote>
              ))}
            </div>
            <p className="mt-6 text-muted leading-relaxed">
              The lesson is bitter because it says: stop encoding your understanding
              of the problem into the system. Let the system learn. The two methods
              that scale are <strong className="text-fg">search</strong> and{" "}
              <strong className="text-fg">learning</strong>. Everything else
              plateaus.
            </p>
          </div>

          {/* Harness Audit */}
          <div className="mb-16">
            <h2 className="mb-2 font-head text-2xl font-semibold text-ink">
              Auditing our own harness
            </h2>
            <p className="mb-8 text-muted leading-relaxed">
              We apply the Bitter Lesson to WhiteMagic's own architecture. Where
              are we encoding human knowledge? Where are we building general-purpose
              methods that scale with computation? The audit is honest.
            </p>
            <div className="space-y-4">
              {HARNESS_AUDIT.map((item) => {
                const Icon = item.icon;
                return (
                  <article
                    key={item.title}
                    className="rounded-xl border border-border bg-surface p-6"
                  >
                    <div className="mb-3 flex items-center gap-3">
                      <Icon className="h-5 w-5 shrink-0 text-lavender" />
                      <h3 className="font-head text-lg font-semibold text-ink">
                        {item.title}
                      </h3>
                      <span
                        className={`ml-auto shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${item.scoreColor}`}
                      >
                        {item.score}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-muted">
                      {item.detail}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>

          {/* Score Summary */}
          <div className="mb-16 rounded-2xl border border-border bg-surface-alt p-8">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Score: 4 scaling, 2 scaffolding
            </h2>
            <p className="text-muted leading-relaxed">
              WhiteMagic's core architecture — memory, learning, meta-cognition —
              follows the Bitter Lesson. The system discovers patterns through
              computation, not through human-curated rules. Where we use
              human-knowledge scaffolding (Dharma rules, Governor patterns), it's
              either a starting point that the system can override at runtime, or a
              safety floor where the cost of learning from failure is
              catastrophic. The scaffolding is not the building.
            </p>
          </div>

          {/* KB Critique Response */}
          <div className="mb-16">
            <h2 className="mb-2 font-head text-2xl font-semibold text-ink">
              Why LLM-generated knowledge bases fail — and what we do differently
            </h2>
            <p className="mb-8 text-muted leading-relaxed">
              The critique is live and credible. Florian Brand (Prime Intellect)
              observes that LLMs &ldquo;love to add useless stuff everywhere and are
              still mostly additive.&rdquo; The broader market agrees: raw
              LLM-generated knowledge bases suffer from staleness, hallucination,
              and undifferentiated bulk. Here's our response, point by point.
            </p>
            <div className="space-y-6">
              {KB_CRITIQUE.map((item, i) => (
                <article
                  key={i}
                  className="rounded-xl border border-border bg-surface p-6"
                >
                  <h3 className="mb-3 font-head text-lg font-semibold text-ink">
                    <span className="text-lavender">&ldquo;</span>
                    {item.point}
                    <span className="text-lavender">&rdquo;</span>
                  </h3>
                  <p className="text-sm leading-relaxed text-muted">
                    {item.response}
                  </p>
                </article>
              ))}
            </div>
          </div>

          {/* Competitive Table */}
          <div className="mb-16">
            <h2 className="mb-6 font-head text-2xl font-semibold text-ink">
              How WhiteMagic compares
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="py-3 pr-4 text-left font-mono text-xs uppercase tracking-widest text-dim">
                      System
                    </th>
                    <th className="py-3 pr-4 text-left font-mono text-xs uppercase tracking-widest text-dim">
                      Approach
                    </th>
                    <th className="py-3 pr-4 text-left font-mono text-xs uppercase tracking-widest text-dim">
                      KB Critique
                    </th>
                    <th className="py-3 text-left font-mono text-xs uppercase tracking-widest text-dim">
                      WhiteMagic Advantage
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {COMPETITIVE_TABLE.map((row) => (
                    <tr
                      key={row.system}
                      className="border-b border-border-light"
                    >
                      <td className="py-3 pr-4 font-head font-semibold text-ink">
                        {row.system}
                      </td>
                      <td className="py-3 pr-4 text-muted">{row.approach}</td>
                      <td className="py-3 pr-4 text-muted">{row.kbCritique}</td>
                      <td className="py-3 text-muted">{row.wmAdvantage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* The Real Insight */}
          <div className="mb-16 rounded-2xl border border-lavender/30 bg-lavender-bg p-8">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              The real insight
            </h2>
            <p className="text-muted leading-relaxed">
              The Bitter Lesson and the KB critique converge on the same point:
              <strong className="text-fg"> don't build a knowledge base — build a
              cognitive substrate.</strong> A knowledge base is a static artifact.
              A cognitive substrate is a system that learns, consolidates, and
              improves from its own operation. WhiteMagic is not a database with an
              LLM bolted on. It's a mind that happens to have a memory.
            </p>
            <p className="mt-4 text-muted leading-relaxed">
              The {WM_FACTS.memories} memories across {WM_FACTS.galaxies} galaxies
              are not the product. The Dream Cycle that consolidates them, the Karma
              Ledger that audits them, the SelfModel that forecasts from them, and
              the 12-phase learning loop that improves them — that's the product.
              Memory is the substrate. Cognition is the output.
            </p>
          </div>

          {/* Sources */}
          <div className="mb-16">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">
              Sources
            </h2>
            <ul className="space-y-2 text-sm text-muted">
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <a
                  href="http://www.incompleteideas.net/IncIdeas/BitterLesson.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  Richard Sutton, &ldquo;The Bitter Lesson&rdquo; (2019)
                </a>
              </li>
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <a
                  href="https://en.wikipedia.org/wiki/Bitter_lesson"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  Wikipedia: Bitter Lesson (background and citations)
                </a>
              </li>
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <a
                  href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  Andrej Karpathy, &ldquo;LLM Wiki&rdquo; (April 2026)
                </a>
              </li>
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <a
                  href="https://codepointer.substack.com/p/agent-memory-systems-and-knowledge"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  Code Pointer: Agent Memory Systems (Letta, Mem0, Graphiti, Cognee)
                </a>
              </li>
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <a
                  href="https://arxiv.org/abs/2407.13578"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-fg hover:underline"
                >
                  &ldquo;How Reliable are LLMs as Knowledge Bases?&rdquo; (arXiv, 2024)
                </a>
              </li>
              <li className="flex items-start gap-2">
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  Florian Brand (@xeophon), Prime Intellect — X post on LLM
                  additive behavior
                </span>
              </li>
            </ul>
          </div>

          {/* CTA */}
          <div className="text-center">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
              See the substrate
            </h2>
            <p className="mx-auto mb-6 max-w-prose text-muted">
              The code is MIT-licensed. The memory system is not a demo — it's
              running in production with {WM_FACTS.memories} memories and{" "}
              {WM_FACTS.testsPassing} passing tests.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link href="/research" className="btn-primary inline-flex items-center gap-2">
                Explore the research
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/open-source" className="btn-ghost">
                Browse the source
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
