import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Quickstart — WhiteMagic Labs",
  description:
    "Get started with WhiteMagic in 60 seconds. Install, configure MCP, store memories, search, run the dream cycle, and check the karma ledger.",
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
    code: `pip install whitemagic[mcp]`,
    explanation: "Installs the WhiteMagic core package with MCP server support. Python 3.12+ required. No external services needed.",
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
# Phases: triage → consolidation → serendipity → governance
#         → narrative → kaizen → oracle → decay`,
    explanation: "The dream cycle is WhiteMagic's subconscious. It prunes weak memories, reinforces strong ones, discovers serendipitous connections between distant concepts, and casts I Ching hexagrams for guidance. In the Live Era, this achieved 3.7M:1 compression ratios.",
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
    explanation: "Every tool call's side-effects are tracked in a SHA-256 Merkle-chained append-only ledger. Each entry records declared intent vs actual execution, severity score, and causal trace. Entries can be anchored to XRPL for tamper-proof evidence.",
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
# Governor → Sanitizer → Rate Limiter → RBAC → 
# Maturity Gate → Dharma → Karma → Audit
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

# Router cascades: EDGE_RULES → LOCAL_SMALL → LOCAL_LARGE → CLOUD
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

export default function QuickstartPage() {
  return (
    <>
      <PageHeader
        eyebrow="Quickstart"
        title="60 seconds to persistent memory."
        lede={`Install WhiteMagic, connect it to your AI agent via MCP, and give it ${WM_FACTS.callableTools} cognitive tools, ${WM_FACTS.galaxies}-galaxy memory, ethical governance, and consciousness primitives.`}
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl">
          {/* Steps */}
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

          {/* Examples */}
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

          {/* Next steps */}
          <div className="mt-12 rounded-2xl border border-border bg-surface-alt p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">Next steps</h2>
            <ul className="space-y-2 text-sm text-muted">
              <li>Read the <Link href="/capabilities" className="text-lavender hover:underline">capabilities page</Link> to understand the full architecture</li>
              <li>Check the <Link href="/benchmarks" className="text-lavender hover:underline">benchmarks page</Link> for measured performance numbers</li>
              <li>Compare against <Link href="/compare" className="text-lavender hover:underline">Mem0, Letta, and RAG</Link></li>
              <li>Browse the <Link href="/mcp-bridge" className="text-lavender hover:underline">MCP bridge catalog</Link> for all 151 callable functions</li>
              <li>Read the <Link href="/faq" className="text-lavender hover:underline">FAQ</Link> for common questions</li>
              <li>Explore the <Link href="/llms-full.txt" className="text-lavender hover:underline">full LLM context file</Link> for deep technical details</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
