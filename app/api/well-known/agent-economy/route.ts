/**
 * GET /.well-known/agent-economy.json
 *
 * Canonical directory entry for agents, crawlers, and any automated
 * caller discovering WhiteMagic Labs. Single JSON doc containing
 * identity, endpoints, payment rails, and machine-readable ToS.
 *
 * Spec: @docs/spec/AGENT_ECONOMY_JSON.md
 */
import { SERVICES_LIST } from "@/lib/data/services";

export const runtime = "nodejs";
// Cache for 5 minutes at the edge; revalidate on deploy.
export const revalidate = 300;

const BASE = "https://whitemagic.dev";

export async function GET() {
  const body = {
    // Spec version — independent of app version.
    spec_version: "0.1",
    generated_at: new Date().toISOString(),

    org: {
      name: "WhiteMagic Labs",
      url: BASE,
      did: "did:web:whitemagic.dev",
      description:
        "Agent governance, private AI deployment, and MCP engineering lab. Publishing reference artifacts for the agent economy.",
      jurisdiction: "US",
    },

    capabilities: [
      "agent-governance",
      "private-ai-deployment",
      "mcp-engineering",
      "gratitude-architecture",
    ],

    // Human and machine surfaces, both discoverable from here.
    endpoints: {
      site: BASE,
      librarian_http: `${BASE}/api/librarian/chat`,
      // MCP-over-HTTPS endpoint (Island C, §2.2.2). Not yet live.
      mcp: `${BASE}/mcp`,
      mcp_status: "planned",
      docs_json: `${BASE}/docs.json`,
      docs_json_status: "planned",
      pricing_json: `${BASE}/pricing.json`,
      pricing_json_status: "planned",
      contact: `${BASE}/contact`,
      contact_api: `${BASE}/api/contact`,
      sitemap: `${BASE}/sitemap.xml`,
      admin_karma: `${BASE}/admin`,
      policy: `${BASE}/.well-known/ai-agent-policy`,
    },

    // Payment rails, in order of preference.
    payment_rails: [
      {
        kind: "xrpl",
        status: "live",
        address: "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy",
        currency: "XRP",
        description:
          "XRPL tip jar for human operators. Send XRP to the address above. " +
          "Publicly verifiable on xrpscan.com. Managed via Xaman wallet.",
        explorer: "https://xrpscan.com/account/raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy",
      },
      {
        kind: "x402",
        status: "planned",
        networks: ["base", "solana"],
        currency: "USDC",
        endpoint: `${BASE}/x402`,
        tier: "voluntary-gratitude",
        description:
          "HTTP 402 micropayments for AI agents. USDC on Base L2 and Solana. " +
          "Activates only when an agent's operator configures a payment budget. " +
          "All tools remain free by default.",
      },
      {
        kind: "gratitude",
        status: "planned",
        endpoint: "https://whitemagic.tip",
        description:
          "Voluntary post-transaction gratitude rail (Proof of Gratitude). " +
          "On-chain verified contributions unlock 2x rate limits and karma boosts.",
      },
    ],

    services: SERVICES_LIST.map((s) => ({
      slug: s.slug,
      name: s.name,
      url: `${BASE}${s.path}`,
      one_liner: s.oneLiner,
      engagement: s.engagementType,
      typical_duration: s.typicalDuration,
      contact: `${BASE}/contact`,
    })),

    // Where an agent should read before calling anything billable.
    terms: {
      human_readable: `${BASE}/about`,
      machine_readable: `${BASE}/.well-known/ai-agent-policy`,
    },

    // Signals for agent-economy discovery protocols.
    signals: {
      mcp_addressable: false, // flips to true when /mcp ships
      xrpl_addressable: true, // XRPL tip jar is live
      x402_addressable: false, // flips to true when x402 endpoint ships
      gratitude_addressable: false, // flips to true when gratitude ledger ships
      open_observatory: false, // flips when /observatory ships
    },

    // Reference to the spec this document follows.
    spec_url: `${BASE}/docs/spec/agent-economy.json`,
  };

  return Response.json(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300, s-maxage=300",
      "access-control-allow-origin": "*",
      "x-wm-spec-version": "0.1",
    },
  });
}
