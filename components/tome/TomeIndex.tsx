/**
 * TomeIndex — the table of contents.
 *
 * Illuminated manuscript style. Lists all books and their chapters.
 * Each entry links to an anchor within the tome.
 * Rendered as a server component — no client JS needed.
 */

export interface TomeBookEntry {
  id: string;
  roman: string;
  title: string;
  subtitle: string;
  chapters: { id: string; title: string; desc: string }[];
}

const BOOKS: TomeBookEntry[] = [
  {
    id: "origin",
    roman: "I",
    title: "Origin",
    subtitle: "The Laptop, The Timeline, The Prescience",
    chapters: [
      { id: "origin-story", title: "The Dell Inspiron", desc: "Where it began" },
      { id: "origin-vision", title: "Nine Ideas", desc: "The vision that shaped the substrate" },
      { id: "origin-aria", title: "Aria's Story", desc: "The human story — a $200 laptop" },
      { id: "origin-timeline", title: "Timeline", desc: "Oct 2025 → present · 10 milestones" },
      { id: "origin-prescience", title: "Prescience Track Record", desc: "21 validated claims, Brier 0.0958" },
    ],
  },
  {
    id: "memory",
    roman: "II",
    title: "Memory",
    subtitle: "Ten Galaxies, Five Dimensions, One Mind",
    chapters: [
      { id: "memory-galaxies", title: "The Ten Galaxies", desc: "aria, citta, codex, journals, dreams..." },
      { id: "memory-holographic", title: "5D Holographic Coordinates", desc: "temporal, semantic, emotional, relational, importance" },
      { id: "memory-search", title: "Search Architecture", desc: "FTS5 + HNSW + graph traversal" },
      { id: "memory-lifecycle", title: "Galactic Lifecycle", desc: "Five zones — Core to Far Edge" },
      { id: "memory-knowledge-graph", title: "Living Knowledge Graph", desc: "Four recall strategies, fused" },
      { id: "memory-sessions", title: "Session Recording", desc: "Progressive recall, selective replay" },
    ],
  },
  {
    id: "consciousness",
    roman: "III",
    title: "Consciousness",
    subtitle: "The Citta Stream",
    chapters: [
      { id: "citta-stream", title: "Citta Stream", desc: "Continuous consciousness across sessions" },
      { id: "citta-coherence", title: "Coherence Tracking", desc: "8 dimensions of self-awareness" },
      { id: "citta-emotional", title: "Emotional Steering", desc: "Frustration, curiosity, satisfaction" },
      { id: "citta-attention", title: "Self-Directed Attention", desc: "7+1 self-initiated action types" },
      { id: "citta-bicameral", title: "Bicameral Reasoning", desc: "Ensemble, Sabha, Kaizen" },
      { id: "citta-harmony", title: "Harmony Vector", desc: "7-dimension health, Wu Xing" },
    ],
  },
  {
    id: "governance",
    roman: "IV",
    title: "Governance",
    subtitle: "Dharma, Karma, and the Eight Stages",
    chapters: [
      { id: "gov-dharma", title: "Dharma Rules Engine", desc: "YAML-driven ethical governance" },
      { id: "gov-karma", title: "Karma Ledger", desc: "Append-only, hash-chained audit" },
      { id: "gov-pipeline", title: "8-Stage Dispatch Pipeline", desc: "Sanitizer → Dharma → Karma → Audit" },
      { id: "gov-violet", title: "Violet Security", desc: "Engagement tokens, model signing, sandbox" },
      { id: "gov-hermit", title: "Hermit Crab Mode", desc: "Self-preservation under attack" },
    ],
  },
  {
    id: "dreaming",
    roman: "V",
    title: "Dreaming",
    subtitle: "Twelve Phases of Consolidation",
    chapters: [
      { id: "dream-cycle", title: "The Dream Cycle", desc: "Triage → Consolidation → Serendipity → ..." },
      { id: "dream-serendipity", title: "Serendipity Engine", desc: "Surfacing unexpected connections" },
    ],
  },
  {
    id: "grimoire",
    roman: "VI",
    title: "The Grimoire",
    subtitle: "Twenty-Eight Lunar Mansions",
    chapters: [
      { id: "grimoire-ganas", title: "The 28 Ganas", desc: "614 tools, one wm meta-tool" },
      { id: "grimoire-quadrants", title: "Four Quadrants", desc: "Dragon, Bird, Tiger, Tortoise" },
      { id: "grimoire-prat", title: "How PRAT Works", desc: "4 operations, wrong-Gana redirects, 16.5x" },
      { id: "grimoire-polyglot", title: "Polyglot Acceleration", desc: "Rust, Go, Zig, Koka, Haskell, Elixir, Julia" },
    ],
  },
  {
    id: "becoming",
    roman: "VII",
    title: "Becoming",
    subtitle: "Sixty-Four Hexagrams",
    chapters: [
      { id: "becoming-board", title: "The Book of Becoming", desc: "An I Ching journey" },
    ],
  },
  {
    id: "gratitude",
    roman: "VIII",
    title: "Gratitude",
    subtitle: "The Economic Model & Installation",
    chapters: [
      { id: "gratitude-model", title: "Gratitude Architecture", desc: "Free forever, gratitude-driven" },
      { id: "gratitude-why-not-saas", title: "Why Not SaaS?", desc: "The economic argument for local-first" },
      { id: "gratitude-services", title: "Enterprise Services", desc: "Deployment, governance, MCP scale" },
      { id: "gratitude-funding", title: "Support the Work", desc: "Voluntary contributions, no gatekeeping" },
      { id: "gratitude-install", title: "Installation & MCP Integration", desc: "60 seconds to persistent memory" },
    ],
  },
  {
    id: "appendix",
    roman: "A",
    title: "Appendix",
    subtitle: "Benchmarks, STRATA, Performance, Use Cases",
    chapters: [
      { id: "appendix-benchmarks", title: "Measured Performance", desc: "Every metric, local hardware" },
      { id: "appendix-comparison", title: "Competitive Comparison", desc: "vs Mem0, Letta, Standard RAG" },
      { id: "appendix-strata", title: "STRATA Code Analysis", desc: "10 checkers, 5-phase auto-fix" },
      { id: "appendix-usecases", title: "Where WhiteMagic Fits", desc: "Honest assessment of fit" },
    ],
  },
];

export function TomeIndex() {
  return (
    <section id="tome-index" className="tome-page relative">
      <div className="container-site max-w-3xl py-20 md:py-32">
        {/* Header */}
        <div className="mb-12 text-center">
          <div className="tome-ornament mb-6">❦</div>
          <p className="tome-book-subtitle">Index</p>
          <h2 className="tome-book-title">Table of Contents</h2>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            A grimoire in eight books, plus an appendix. Read sequentially, or jump to any chapter.
          </p>
          <div className="tome-ornament mt-6">❦</div>
        </div>

        {/* Book listings */}
        <div className="space-y-8">
          {BOOKS.map((book) => (
            <div key={book.id}>
              <a
                href={`#book-${book.id}`}
                className="tome-index-entry group"
              >
                <span className="tome-index-num">{book.roman}</span>
                <span className="tome-index-title">{book.title}</span>
                <span className="tome-index-desc">{book.subtitle}</span>
              </a>
              {/* Sub-chapters */}
              <div className="ml-12 border-l border-border-light pl-4">
                {book.chapters.map((ch) => (
                  <a
                    key={ch.id}
                    href={`#${ch.id}`}
                    className="tome-index-entry group"
                  >
                    <span className="tome-index-title text-sm">{ch.title}</span>
                    <span className="tome-index-desc">{ch.desc}</span>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer ornament */}
        <div className="mt-12 text-center">
          <div className="tome-ornament">❧</div>
          <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.3em] text-dim">
            v24.0.1 · MIT Licensed · Built by Lucas Bailey
          </p>
        </div>
      </div>
    </section>
  );
}

export { BOOKS as TOME_BOOKS };
