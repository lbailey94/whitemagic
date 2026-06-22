# Spec: `/.well-known/agent-economy.json`

**Status**: Draft v0.1
**Authors**: WhiteMagic Labs
**Last updated**: 2026-04-20
**Implements in**: `@apps/site/app/api/well-known/agent-economy/route.ts`
**Related**: `docs/spec/AI_AGENT_POLICY.md`,
`docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md` §2.2.1

---

## Motivation

An agent or automated crawler arriving at an unfamiliar domain needs
a canonical answer to "what can I do here, and how?" Today the answer
is scattered across `robots.txt`, `sitemap.xml`, meta tags, and
unstructured marketing copy. None of those were designed for the
agent-economy era.

`/.well-known/agent-economy.json` is a **single directory entry** that
any agent hits first, to discover endpoints, pricing, payment rails,
identity, and machine-readable ToS, in one request.

It is designed to be trivially implementable — a static JSON file
works — while being rich enough to be the primary discovery surface
for agent-native services.

## Non-goals

- Not a protocol. Agents call it with plain HTTP `GET`.
- Not a framework. It references external specs (DID, x402, MCP,
  Sitemaps) rather than duplicating them.
- Not a replacement for `robots.txt`. Machines that don't know what
  `agent-economy.json` is should still be handled by `robots.txt`.

## Path

- Canonical: `https://<host>/.well-known/agent-economy.json`
- `.well-known` is used per RFC 8615; `agent-economy.json` is the
  proposed suffix.

## HTTP semantics

- Method: `GET`
- Auth: none
- Response `content-type`: `application/json; charset=utf-8`
- `Cache-Control`: `public, max-age=300` recommended (fresh within
  5 minutes is plenty for a directory entry).
- CORS: `Access-Control-Allow-Origin: *` required. Discoverability
  is the point.

## Schema (v0.1)

All fields OPTIONAL unless marked REQUIRED. Additive changes do not
bump the spec version. Breaking changes do.

```ts
interface AgentEconomyDirectory {
  /** REQUIRED. Semver-like string, spec line, not app version. */
  spec_version: string;              // e.g. "0.1"

  /** REQUIRED. RFC 3339 timestamp of document generation. */
  generated_at: string;

  /** REQUIRED. The org behind this directory. */
  org: {
    name: string;
    url: string;
    /** did:web is strongly preferred. */
    did?: string;
    description?: string;
    jurisdiction?: string;           // ISO 3166 country code
  };

  /** List of canonical capability slugs this org claims. */
  capabilities?: string[];

  /** Discoverable endpoints. Unknown endpoints MUST be ignored. */
  endpoints?: {
    site?: string;
    mcp?: string;                    // MCP-over-HTTPS
    mcp_status?: "live" | "planned" | "deprecated";
    librarian_http?: string;         // Plain LLM chat endpoint
    docs_json?: string;
    pricing_json?: string;
    contact?: string;
    contact_api?: string;
    sitemap?: string;
    admin_karma?: string;            // public Karma ledger, if any
    policy?: string;                 // ai-agent-policy
    [extension: string]: unknown;    // x-prefixed extensions welcome
  };

  /** Payment rails offered. Ordered by preference if ambiguous. */
  payment_rails?: Array<{
    kind: "stripe" | "x402" | "gratitude" | "lightning" | string;
    status?: "live" | "planned" | "deprecated";
    endpoint?: string;
    /** Free-form, per-rail detail; callers MUST treat unknown
        fields as opaque. */
    [extension: string]: unknown;
  }>;

  /** Service catalog, for orgs that sell services. */
  services?: Array<{
    slug: string;
    name: string;
    url: string;
    one_liner?: string;
    starting_price_usd?: number | null;
    typical_duration?: string;
  }>;

  /** Pricing catalog — individual SKUs / tiers. */
  pricing?: Array<{
    slug: string;
    name: string;
    price_usd: number | null;
    price_note?: string;
    turnaround?: string;
    checkout_url: string;
    checkout_kind: "stripe" | "contact-form" | "x402" | string;
  }>;

  /** Pointers to ToS. Human-readable is for humans, machine for agents. */
  terms?: {
    human_readable?: string;
    machine_readable?: string;       // Should be the ai-agent-policy URL
  };

  /** Signals an automated caller can use to route. */
  signals?: {
    mcp_addressable?: boolean;
    x402_addressable?: boolean;
    gratitude_addressable?: boolean;
    open_observatory?: boolean;
    [k: string]: unknown;
  };

  /** The spec this doc claims to follow. Optional. */
  spec_url?: string;
}
```

## Versioning

- `spec_version` is a string. Clients MUST NOT assume numeric
  ordering; they SHOULD treat unknown versions as "try to parse,
  but be forgiving."
- Additive fields are allowed in any patch version.
- Renames or removals require bumping the major (`0.1` → `0.2`).
- Vendor extensions MUST use `x-` prefixed keys.

## Security considerations

- This document is **unsigned in v0.1**. A future v0.2 MAY add a
  detached signature via JOSE or JWS pointing to the `did` in `org`.
- Agents treating `checkout_url` values as commitments MUST verify
  them against a signed source before charging a principal.
- CORS-open responses are intentional; callers SHOULD NOT include
  cookies or auth headers when fetching this endpoint.

## Privacy considerations

- This document SHOULD NOT contain any PII.
- Referenced endpoints MAY require auth; the directory merely
  advertises them.

## Example

See the live response at
`https://whitemagic.dev/.well-known/agent-economy.json` (once
deployed) or the reference handler at
`@apps/site/app/api/well-known/agent-economy/route.ts`.

## Open questions

- **Q1**: Should `payment_rails` include routing info (chain IDs,
  settlement times) or just identity? Punted to v0.2.
- **Q2**: Should discovery be pull-only, or should there be a push
  registry? Pull-only in v0.1; registries are someone else's job.
- **Q3**: Should `did` be REQUIRED? Softened to SHOULD in v0.1 to
  lower adoption friction. Revisit for v0.2.
- **Q4**: Should the spec define a JSON Schema for validation?
  Yes, before v0.2 — publish alongside.

## Relationship to other specs

- **IETF `/.well-known`** (RFC 8615): we claim the suffix
  `agent-economy.json` without formal registration. Registration is
  a v1.0 action.
- **W3C DID** (v1.0): `did:web` is the preferred identity rep.
- **x402** (Coinbase + Linux Foundation): listed as a payment rail;
  this spec does not define x402 semantics.
- **MCP** (Anthropic): listed as an endpoint kind; this spec does
  not define MCP semantics.
- **W3C Web of Things Thing Description**: adjacent, but WoT targets
  physical devices. We are agent-economy specific.

## Why publish this

- Forces discipline in our own site content.
- Creates a **public artifact** other labs can implement.
- Positions WhiteMagic Labs as a reference point for agent-
  economy site conventions.
- The spec itself is cite-able; it doesn't need to win adoption
  to provide value.
