import { NextResponse } from "next/server";

/**
 * Signal Detection API — Early-warning radar for AI/governance/research signals
 *
 * GET /api/signals — current watchlist and recent signals
 * POST /api/signals/scan — trigger a scan (returns fresh results)
 */

const WATCHLIST = [
  {
    name: "NIST AI Safety Institute",
    url: "https://www.nist.gov/artificial-intelligence",
    category: "Governance",
    focus: "AI standards, benchmarks, safety frameworks",
    check_frequency_hours: 72,
  },
  {
    name: "Anthropic Research",
    url: "https://www.anthropic.com/research",
    category: "Alignment",
    focus: "Constitutional AI, interpretability, safety",
    check_frequency_hours: 168,
  },
  {
    name: "OpenAI Research",
    url: "https://openai.com/research",
    category: "Frontier Models",
    focus: "Capabilities, benchmarks, governance",
    check_frequency_hours: 168,
  },
  {
    name: "DeepMind Research",
    url: "https://deepmind.google/research/",
    category: "Frontier Models",
    focus: "AGI, neuroscience, reinforcement learning",
    check_frequency_hours: 168,
  },
  {
    name: "arXiv cs.AI",
    url: "https://arxiv.org/list/cs.AI/recent",
    category: "Academic",
    focus: "Latest AI/ML paper submissions",
    check_frequency_hours: 24,
  },
  {
    name: "Foresight Institute",
    url: "https://foresight.org/",
    category: "Long-term",
    focus: "Molecular nanotechnology, safe AI, longevity",
    check_frequency_hours: 720,
  },
  {
    name: "Center for Humane Technology",
    url: "https://www.humanetech.com/",
    category: "Ethics",
    focus: "AI's impact on society, attention economy",
    check_frequency_hours: 336,
  },
  {
    name: "AI Now Institute",
    url: "https://ainowinstitute.org/",
    category: "Policy",
    focus: "AI accountability, labor impacts, regulation",
    check_frequency_hours: 336,
  },
  {
    name: "LessWrong / Alignment Forum",
    url: "https://www.alignmentforum.org/",
    category: "Alignment",
    focus: "AI alignment research discourse",
    check_frequency_hours: 48,
  },
  {
    name: "Hugging Face Daily Papers",
    url: "https://huggingface.co/papers",
    category: "Academic",
    focus: "Community-curated ML papers",
    check_frequency_hours: 24,
  },
  {
    name: "MCP Registry (Anthropic)",
    url: "https://github.com/modelcontextprotocol/servers",
    category: "Ecosystem",
    focus: "New MCP servers, protocol changes",
    check_frequency_hours: 72,
  },
  {
    name: "Federal Register — AI/ML Rules",
    url: "https://www.federalregister.gov/",
    category: "Regulation",
    focus: "US federal AI regulations, RFPs, executive orders",
    check_frequency_hours: 168,
  },
  {
    name: "EU AI Act Tracker",
    url: "https://artificialintelligenceact.eu/",
    category: "Regulation",
    focus: "EU AI Act implementation, compliance",
    check_frequency_hours: 168,
  },
  {
    name: "Schmidt Sciences",
    url: "https://www.schmidtsciences.org/",
    category: "Funding",
    focus: "Research grants, AI safety funding",
    check_frequency_hours: 720,
  },
  {
    name: "Open Philanthropy",
    url: "https://www.openphilanthropy.org/grants/",
    category: "Funding",
    focus: "AI risk grants, global catastrophic risks",
    check_frequency_hours: 720,
  },
  {
    name: "MCP Safety Research (MIT/Stanford)",
    url: "https://mcp-secbench.github.io/",
    category: "Ecosystem",
    focus: "MCP security research, benchmarks",
    check_frequency_hours: 168,
  },
  {
    name: "WhiteMagic Labs Site",
    url: "https://whitemagic.dev",
    category: "Internal",
    focus: "Releases, research updates, prescience log",
    check_frequency_hours: 72,
  },
  {
    name: "Research Inbox",
    url: "internal://research/feeds",
    category: "Internal",
    focus: "Research feeds, newsletters",
    check_frequency_hours: 72,
  },
  {
    name: "CODEX LIBRARY — New Additions",
    url: "/library",
    category: "Internal",
    focus: "New files added to the research library",
    check_frequency_hours: 24,
  },
  {
    name: "EFF Deeplinks — AI section",
    url: "https://www.eff.org/deeplinks",
    category: "Policy",
    focus: "Digital rights, AI policy, privacy",
    check_frequency_hours: 72,
  },
];

const INTEREST_AREAS = [
  "AI agent governance",
  "MCP safety and security",
  "Constitutional AI",
  "Karma-based economic systems",
  "Cognitive architecture",
  "Consciousness and computation",
  "Polyglot acceleration",
  "Holographic memory",
  "Grant opportunities (AI safety/governance)",
  "Foresight and long-term planning",
];

export async function GET() {
  const now = new Date();
  const sourcesByCategory: Record<string, number> = {};
  let totalSources = 0;
  let highFreqSources = 0;

  for (const src of WATCHLIST) {
    sourcesByCategory[src.category] =
      (sourcesByCategory[src.category] || 0) + 1;
    totalSources++;
    if (src.check_frequency_hours <= 72) highFreqSources++;
  }

  return NextResponse.json({
    watchlist_version: "1.0.0",
    total_sources: totalSources,
    high_frequency_sources: highFreqSources,
    categories: sourcesByCategory,
    interest_areas: INTEREST_AREAS,
    sources: WATCHLIST.map((s) => ({
      name: s.name,
      category: s.category,
      frequency: `${s.check_frequency_hours}h`,
      focus: s.focus,
    })),
    last_scan: null,
    next_scan_recommended: new Date(
      now.getTime() + 24 * 60 * 60 * 1000,
    ).toISOString(),
    notes: [
      "Signal detection is currently passive (watchlist only).",
      "Active scanning requires CODEX pipeline + Aria agent.",
      "Aria flags items matching interest areas within check frequency.",
      "Monthly 'Ahead of the Curve' digest to be automated.",
    ],
    timestamp: now.toISOString(),
  });
}
