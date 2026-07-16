import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { TabSwitcher } from "@/components/TabSwitcher";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Getting Started — WhiteMagic Labs",
  description:
    "Get started with WhiteMagic in 60 seconds. Install, configure MCP, store memories, search, run the dream cycle, and check the karma ledger. Plus common questions answered honestly.",
};

interface Step {
  num: number;
  title: string;
  code: string;
  explanation: string;
}

const STEPS: Step[] = [
  {
    num: 1,
    title: "Install",
    code: `pip install whitemagic[mcp]

# One-command onboarding (scaffolds + ingests your notes + verifies):
wm onboard --from ~/my-obsidian-vault --launch

# Or without existing notes:
wm init && wm quickstart`,
    explanation: "Installs WhiteMagic with MCP server support. Python 3.12+ required. `wm onboard --from <dir>` scaffolds a project, ingests your markdown files into a galaxy, runs a health check, and optionally launches the MCP server — all in one command.",
  },
  {
    num: 2,
    title: "Configure MCP",
    code: `# Add to your MCP client config (Claude Desktop, Cursor, etc.):
{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": { "WM_MCP_PRAT": "1" }
    }
  }
}`,
    explanation: `PRAT mode exposes 28 Gana meta-tools instead of ${WM_FACTS.callableTools} individual tools. The wm() meta-tool auto-routes natural language to the right tool. Set WM_MCP_PRAT=2 for Seed mode (1 tool only).`,
  },
  {
    num: 3,
    title: "Store a memory",
    code: `# Via MCP tool call:
wm(thought='remember that the deployment deadline is July 15')

# Or via Python:
from whitemagic.core.memory import UnifiedMemory
mem = UnifiedMemory()
mem.store(
    content="The deployment deadline is July 15",
    galaxy="universal",
    importance=0.8,
    tags=["deadline", "deployment"]
)`,
    explanation: "Memories are stored with 5D holographic coordinates: temporal, semantic, emotional, relational, and importance. The system automatically assigns coordinates based on content analysis.",
  },
  {
    num: 4,
    title: "Search memories",
    code: `# Semantic search:
wm(thought='search for deployment deadlines')

# Full-text search:
wm(thought='find memories containing "deadline"')

# Hybrid recall (semantic + FTS5 + graph):
wm(thought='recall everything about July deadlines')

# Via Python:
results = mem.search("deployment deadline", limit=10)
# Returns memories ranked by HNSW vector similarity + FTS5 relevance`,
    explanation: "WhiteMagic uses dual search: HNSW for vector similarity (0.26ms over 16K embeddings) and FTS5 for full-text (2.6ms over 1K memories). Hybrid recall fuses both with graph walking.",
  },
  {
    num: 5,
    title: "Run the dream cycle",
    code: `# Trigger dream cycle consolidation:
wm(thought='run dream cycle')

# Or via Python:
from whitemagic.core.dreaming.dream_cycle import DreamCycle
cycle = DreamCycle()
result = cycle.run()
# Phases: triage -> consolidation -> serendipity -> governance
#         -> narrative -> kaizen -> oracle -> decay`,
    explanation: "The dream cycle is WhiteMagic's subconscious. It prunes weak memories, reinforces strong ones, discovers serendipitous connections between distant concepts, and casts I Ching hexagrams for guidance.",
  },
  {
    num: 6,
    title: "Check the karma ledger",
    code: `# View audit trail:
wm(thought='show karma ledger')

# Via Python:
from whitemagic.core.governance.karma_ledger import KarmaLedger
ledger = KarmaLedger()
entries = ledger.recent(limit=20)
for e in entries:
    print(f"{e.timestamp} | {e.tool} | {e.severity} | {e.intent_vs_actual}")`,
    explanation: "Every tool call's side-effects are tracked in a SHA-256 Merkle-chained append-only ledger. Each entry records declared intent vs actual execution, severity score, and causal trace.",
  },
  {
    num: 7,
    title: "Check system health",
    code: `# Get harmony vector:
wm(thought='system health')

# Via Python:
from whitemagic.harmony import HomeostaticLoop
loop = HomeostaticLoop()
report = loop.health_report()
# 7 dimensions: balance, throughput, latency, error rate,
#               dharma compliance, karma debt, energy`,
    explanation: "The harmony vector monitors system wellbeing across 7 dimensions and cycles through 5 Wu Xing phases (wood, fire, earth, metal, water) to maintain equilibrium. Loop overhead: 0.35ms.",
  },
];

const EXAMPLES: { title: string; description: string; code: string }[] = [
  {
    title: "Agent with persistent memory",
    description: "An agent that remembers past conversations and learns from them.",
    code: `from whitemagic.core.memory import UnifiedMemory
from whitemagic.core.memory.session_recorder import SessionRecorder

mem = UnifiedMemory()
recorder = SessionRecorder(mem, session_id="agent-001")

# Record a conversation turn
recorder.record(
    role="user",
    content="What did we discuss last time?",
    turn_type="question",
    importance=0.7
)

# Recall previous session context
context = recorder.recall_progressive(token_budget=2000)
# Returns the most important turns from previous sessions,
# token-budgeted to fit in your LLM context window`,
  },
  {
    title: "Governed tool execution",
    description: "Run a tool with ethical governance and audit trail.",
    code: `from whitemagic.tools.unified_api import UnifiedAPI

api = UnifiedAPI()

# The 8-stage dispatch pipeline runs automatically:
# Governor -> Sanitizer -> Rate Limiter -> RBAC ->
# Maturity Gate -> Dharma -> Karma -> Audit
result = api.call_tool(
    "memory.store",
    {
        "content": "Sensitive user data",
        "galaxy": "universal",
        "tags": ["user_data"]
    }
)
# If Dharma rules block the operation, you get a
# structured error envelope with the reason`,
  },
  {
    title: "Local inference with ternary kernels",
    description: "Run inference on CPU with Rust AVX2 acceleration.",
    code: `from whitemagic.inference.router import InferenceRouter

router = InferenceRouter()

# Router cascades: EDGE_RULES -> LOCAL_SMALL -> LOCAL_LARGE -> CLOUD
# With ternary kernels, LOCAL_SMALL runs at 67ms/token on CPU
result = router.route(
    prompt="Summarize this document",
    complexity="low",
    prefer_local=True
)
# Stays local if possible. Only escalates to cloud
# if confidence < 0.85 or complexity is high`,
  },
];

function QuickstartContent() {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="space-y-8">
        {STEPS.map((step) => (
          <div key={step.num}>
            <div className="mb-3 flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-lavender/10 font-mono text-sm font-semibold text-lavender">
                {step.num}
              </span>
              <h2 className="font-head text-lg font-semibold text-ink">{step.title}</h2>
            </div>
            <pre className="mb-3 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{step.code}
            </pre>
            <p className="text-sm leading-relaxed text-muted">{step.explanation}</p>
          </div>
        ))}
      </div>

      <div className="mt-16">
        <h2 className="mb-6 font-head text-2xl font-semibold text-ink">
          Practical examples
        </h2>
        <div className="space-y-8">
          {EXAMPLES.map((ex) => (
            <div key={ex.title} className="rounded-2xl border border-border bg-surface p-6">
              <h3 className="mb-2 font-head text-base font-semibold text-ink">{ex.title}</h3>
              <p className="mb-4 text-sm text-muted">{ex.description}</p>
              <pre className="rounded-lg border border-border bg-ink p-4 text-xs text-surface font-mono overflow-x-auto">
{ex.code}
              </pre>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-12 rounded-2xl border border-border bg-surface-alt p-6">
        <h2 className="mb-3 font-head text-lg font-semibold text-ink">Next steps</h2>
        <ul className="space-y-2 text-sm text-muted">
          <li>Read the <Link href="/capabilities" className="text-lavender hover:underline">capabilities page</Link> to understand the full architecture</li>
          <li>Check the <Link href="/benchmarks" className="text-lavender hover:underline">benchmarks & comparison</Link> for measured performance numbers</li>
          <li>Browse the <Link href="/mcp-bridge" className="text-lavender hover:underline">MCP bridge catalog</Link> for all callable functions</li>
          <li>Explore the <Link href="/llms-full.txt" className="text-lavender hover:underline">full LLM context file</Link> for deep technical details</li>
        </ul>
      </div>
    </div>
  );
}

interface QA {
  q: string;
  a: string;
  links?: { href: string; label: string }[];
}

const FAQ: QA[] = [
  {
    q: "How is WhiteMagic different from Mem0?",
    a: "Mem0 gives your AI a notepad. WhiteMagic gives your AI a mind. Mem0 is a hosted cloud API that stores and retrieves text via vector search. WhiteMagic is a local-first cognitive operating system with 5D holographic memory, ethical governance (Dharma engine + Karma ledger), 8-phase dream cycle consolidation, consciousness primitives (citta stream, coherence metrics), and 614 callable tools. Mem0 is faster to integrate if you just need basic memory. WhiteMagic is for agents that need to think, remember, govern themselves, and grow.",
    links: [{ href: "/benchmarks", label: "Full comparison &rarr;" }],
  },
  {
    q: "How is WhiteMagic different from Letta?",
    a: "Letta is an agent harness - it manages the agent runtime, tool calling, context windows, and model routing. WhiteMagic is a substrate that any agent plugs into via MCP. Letta's consciousness lives inside the harness; WhiteMagic's citta stream is accessible to any connected agent. Letta is tighter coupling for harness-native agents. WhiteMagic is model-agnostic, harness-agnostic, and works with any MCP-compatible client.",
    links: [{ href: "/benchmarks", label: "Full comparison &rarr;" }],
  },
  {
    q: "Do I need to run my own LLM?",
    a: "No. WhiteMagic works with any LLM - Claude, GPT-4, Gemini, local models via Ollama, or no LLM at all. The cognitive substrate (memory, governance, search, dream cycle) operates independently of the LLM. The LLM is just one consumer of the substrate. You can use WhiteMagic purely as a memory and governance layer for cloud-based LLMs, or run everything locally with Ollama for full air-gapped operation.",
  },
  {
    q: "Can I use this with Claude / GPT-4 / Gemini / local models?",
    a: "Yes to all. WhiteMagic is model-agnostic. It connects via MCP, which is supported by Claude Desktop, Cursor, Windsurf, and any MCP-compatible client. For local models, the inference router supports Ollama with automatic cascading: if a local model's confidence is below 0.85, it can escalate to a cloud model. The ternary kernel provides CPU-only inference at 67ms/token for 1-bit models.",
  },
  {
    q: "Is this production-ready?",
    a: `The code is production-quality: ${WM_FACTS.testsPassing} passing tests with zero failures, ${WM_FACTS.linesShort} lines of code, MIT-licensed, and running on real hardware. However, WhiteMagic is currently a solo-built research project, not a venture-backed company. The architecture is designed for production (8-stage safety pipeline, audit trail, graceful degradation), but operational concerns like SLAs, support, and hosted deployment are not yet available. The MCP server is stable and runs indefinitely.`,
    links: [{ href: "/benchmarks", label: "See benchmarks &rarr;" }],
  },
  {
    q: "What's the overhead?",
    a: "Minimal. MCP tool dispatch runs at 29-33ms median latency with 100% success rate. Memory per call is 0-0.18MB. The homeostatic loop adds 0.35ms overhead. Session recording adds ~3ms per conversation turn (0.2-0.6% of LLM token generation time). The rate limiter pre-check runs at 452K ops/s. All measurements are on consumer hardware.",
    links: [{ href: "/benchmarks", label: "Full benchmark details &rarr;" }],
  },
  {
    q: "Does my data leave my machine?",
    a: "No. WhiteMagic is local-first by default. All memory, governance, and identity live in ~/.whitemagic. The system runs on a Raspberry Pi, an air-gapped laptop, or a regulated enterprise server. Your data never leaves the building unless you explicitly configure cloud LLM escalation. Even then, only the prompt goes to the cloud - memory, karma ledger, and governance state stay local.",
  },
  {
    q: "What is the 8-stage dispatch pipeline?",
    a: "Every tool call passes through 8 stages: Governor (policy check) -> Input Sanitizer (shell injection detection) -> Rate Limiter (452K ops/s) -> RBAC (role-based access) -> Maturity Gate (capability check) -> Dharma Engine (ethical reasoning) -> Handler (execution) -> Karma Ledger (audit). This prevents harm even if a tool is malicious, an agent is misdirected, or memory is poisoned.",
    links: [{ href: "/capabilities", label: "View capabilities &rarr;" }],
  },
  {
    q: "What is the dream cycle?",
    a: "The dream cycle is WhiteMagic's subconscious. While the agent is idle, it runs 8 phases: triage (sort memories by importance), consolidation (merge related memories), serendipity (discover unexpected connections), governance (ethical review of stored content), narrative (compress into story), kaizen (suggest improvements), oracle (cast I Ching for guidance), and decay (archive weak memories).",
  },
  {
    q: "What are the 28 Ganas?",
    a: `The 28 Ganas (Lunar Mansions) are a meta-tool system that collapses ${WM_FACTS.callableTools} individual tools into 28 stable meta-tools. Each Gana maps to a Chinese Lunar Mansion and supports 4 polymorphic operations: search, analyze, transform, consolidate. The wm() meta-tool auto-routes natural language to the right Gana.`,
    links: [{ href: "/ganas", label: "Explore the 28 Ganas &rarr;" }],
  },
  {
    q: "What is the Karma Ledger?",
    a: "The Karma Ledger is a SHA-256 Merkle-chained, append-only audit trail of every tool call's side-effects. Each entry records: declared intent vs actual execution, severity score, causal trace, and timestamp. Entries can be Merkle-anchored to XRPL (XRP Ledger) or Base L2 for tamper-proof external verifiability.",
  },
  {
    q: "What is citta?",
    a: "Citta (Pali/Sanskrit: 'heart-mind') is the continuous stream of mental events constituting experience. In WhiteMagic, citta is a substrate-level stream accessible via MCP - not an external tool, but the continuous background that makes all other tools meaningful. It includes coherence metrics (8 dimensions), Smarana practice (active remembering), presence quality, and temporal continuity across sessions.",
  },
  {
    q: "Can I contribute?",
    a: `Yes. WhiteMagic is MIT-licensed and open source. The codebase has ${WM_FACTS.testsPassing} passing tests as the guardrail - never skip them. Read the AGENTS.md file in the repo for the full operational guide.`,
    links: [{ href: "/open-source", label: "Open source info &rarr;" }],
  },
  {
    q: "What hardware do I need?",
    a: "A consumer laptop. The entire system was built and tested on a Dell Inspiron 3582 (Intel Celeron N4000, 4GB RAM, eMMC storage). The ternary kernels provide CPU-only inference. The Rust SIMD core uses AVX2 (available on most CPUs since 2013). No GPU required. No server hardware required. The system also runs on Raspberry Pi for edge deployments.",
  },
  {
    q: "How do I report bugs or request features?",
    a: "Open an issue on the GitHub repository. The project maintains a STUB_REGISTRY.md tracking every NotImplementedError and placeholder. Bug reports should include the reproducible command and the expected vs actual behavior.",
    links: [{ href: "https://github.com/lbailey94/whitemagic", label: "GitHub &rarr;" }],
  },
];

function FAQContent() {
  return (
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
            Get in touch &rarr;
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function GettingStartedPage() {
  return (
    <>
      <PageHeader
        eyebrow="Getting Started"
        title="60 seconds to persistent memory."
        lede={`Install WhiteMagic, connect it to your AI agent via MCP, and give it ${WM_FACTS.callableTools} cognitive tools, ${WM_FACTS.galaxies}-galaxy memory, ethical governance, and consciousness primitives.`}
      />

      <section className="container-site py-16">
        <TabSwitcher
          tabs={[
            { id: "quickstart", label: "Quickstart", content: <QuickstartContent /> },
            { id: "faq", label: "FAQ", content: <FAQContent /> },
          ]}
        />
      </section>
    </>
  );
}
