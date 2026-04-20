/**
 * GET /.well-known/ai-agent-policy   (also .json)
 *
 * robots.txt for agents. Declares which endpoints are agent-accessible,
 * rate limits, preferred payment rails, contact for abuse, and
 * pointers to machine-readable ToS.
 *
 * Spec: @docs/spec/AI_AGENT_POLICY.md
 */
export const runtime = "nodejs";
export const revalidate = 600;

const BASE = "https://whitemagic.dev";

export async function GET() {
  const body = {
    spec_version: "0.1",
    spec_url: `${BASE}/docs/spec/ai-agent-policy`,
    generated_at: new Date().toISOString(),

    org: {
      name: "WhiteMagic Labs",
      did: "did:web:whitemagic.dev",
      contact: `${BASE}/contact`,
      abuse_contact: "abuse@whitemagic.dev",
    },

    // Per-surface declarations. Order matters: more specific first.
    surfaces: [
      {
        path: "/.well-known/*",
        allow: ["*"],
        rate_limit: { requests_per_hour: 600, per: "ip" },
        auth: "none",
        notes: "Discovery. Unrestricted. Cache for 5 minutes.",
      },
      {
        path: "/sitemap.xml",
        allow: ["*"],
        rate_limit: { requests_per_hour: 60, per: "ip" },
        auth: "none",
      },
      {
        path: "/docs.json",
        allow: ["*"],
        rate_limit: { requests_per_hour: 120, per: "ip" },
        auth: "none",
        status: "planned",
      },
      {
        path: "/pricing.json",
        allow: ["*"],
        rate_limit: { requests_per_hour: 120, per: "ip" },
        auth: "none",
        status: "planned",
      },
      {
        path: "/mcp",
        allow: ["mcp-client/*"],
        rate_limit: { requests_per_hour: 120, per: "session" },
        auth: "none-for-read; did-web-for-billable",
        payment_rail: "x402",
        status: "planned",
      },
      {
        path: "/api/librarian/chat",
        allow: ["*"],
        rate_limit: {
          requests_per_day: 30,
          per: "ip",
          concurrent_sessions_per_ip: 2,
        },
        auth: "none",
        budget_cap_usd_monthly: 25,
        notes:
          "Human-oriented; agents are permitted but are asked to identify themselves via User-Agent and X-Agent-DID.",
      },
      {
        path: "/api/contact",
        allow: ["*"],
        rate_limit: { requests_per_day: 5, per: "ip" },
        auth: "none",
        notes: "Honeypot-protected. Agents may submit on behalf of principals.",
      },
      {
        path: "/admin",
        allow: [],
        auth: "basic-auth",
        notes: "Private. Do not attempt.",
      },
    ],

    // Preferred payment rails for any billable interaction.
    payment_rails: [
      { kind: "stripe", role: "human-facing checkout" },
      { kind: "x402", role: "agent-to-agent micropayments", status: "planned" },
      {
        kind: "gratitude",
        role: "voluntary post-transaction tipping (Proof of Gratitude)",
        status: "planned",
      },
    ],

    // Identity expectations from calling agents.
    identity: {
      preferred: "did:web",
      accepted: ["did:web", "did:key", "ua-string-only"],
      headers: {
        agent_did: "X-Agent-DID",
        principal_did: "X-Principal-DID",
        credential: "X-Agent-Credential",
      },
      notes:
        "Credentials are not yet verified — signing when received is optional. When /mcp ships, did:web will be required for billable endpoints.",
    },

    // How we treat agent traffic in our own systems.
    transparency: {
      karma_ledger_public: `${BASE}/admin`,
      dharma_rules_public: true,
      logs_retention_days: 90,
      pii_policy:
        "Submissions are kept as-provided. No enrichment, no resale, no third-party analytics.",
    },

    // Pointers for the curious.
    references: [
      {
        rel: "agent-economy",
        href: `${BASE}/.well-known/agent-economy.json`,
      },
      { rel: "sitemap", href: `${BASE}/sitemap.xml` },
      { rel: "robots", href: `${BASE}/robots.txt` },
    ],
  };

  return Response.json(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=600, s-maxage=600",
      "access-control-allow-origin": "*",
      "x-wm-spec-version": "0.1",
    },
  });
}
