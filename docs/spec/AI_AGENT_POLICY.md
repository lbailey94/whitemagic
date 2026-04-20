# Spec: `/.well-known/ai-agent-policy`

**Status**: Draft v0.1
**Authors**: WhiteMagic Labs
**Last updated**: 2026-04-20
**Implements in**: `@apps/site/app/api/well-known/ai-agent-policy/route.ts`
**Related**: `docs/spec/AGENT_ECONOMY_JSON.md`,
`docs/strategy_manifestos/AGENT_FIRST_LAB_STRATEGY.md` §2.2.3

---

## Motivation

`robots.txt` (1994) assumed a world of crawlers that either obeyed
or didn't — a binary good-bot / bad-bot model. It does not express
rate limits per surface, identity expectations, payment rails, or
machine-readable ToS.

`ai-agent-policy` fills those gaps in a JSON format that is
human-editable, machine-consumable, and **additive** to `robots.txt`
(not a replacement). Agents SHOULD fetch both and honor the
intersection.

## Non-goals

- Not a substitute for `robots.txt`. Both SHOULD be served.
- Not a DRM system. Agents that ignore policy face the same social
  and legal consequences they always have.
- Not a payment protocol. It advertises which rails are accepted;
  the rails themselves are specified elsewhere.

## Path

- `https://<host>/.well-known/ai-agent-policy` (no suffix)
- `https://<host>/.well-known/ai-agent-policy.json` (alias, same
  response)

## HTTP semantics

- Method: `GET`
- Auth: none
- Response `content-type`: `application/json; charset=utf-8`
- `Cache-Control`: `public, max-age=600` recommended
- CORS: open

## Schema (v0.1)

```ts
interface AiAgentPolicy {
  spec_version: string;              // REQUIRED. e.g. "0.1"
  spec_url?: string;
  generated_at: string;              // REQUIRED. RFC 3339.

  org: {                             // REQUIRED.
    name: string;
    did?: string;
    contact: string;                 // URL to contact form or mailto
    abuse_contact?: string;          // email or URL
  };

  /** Ordered most-specific-first. Agents MUST use the FIRST match. */
  surfaces: Array<{
    path: string;                    // Exact or glob (*-suffix supported)
    allow: string[];                 // Agent identifiers; ["*"] = all
    deny?: string[];                 // explicit deny list
    auth?:
      | "none"
      | "basic-auth"
      | "bearer"
      | "did-web"
      | "x402"
      | string;                      // per-surface auth hint
    rate_limit?: {
      requests_per_hour?: number;
      requests_per_day?: number;
      concurrent_sessions_per_ip?: number;
      per?: "ip" | "session" | "did";
    };
    budget_cap_usd_monthly?: number; // total budget across all callers
    payment_rail?: string;           // kind from agent-economy.json
    status?: "live" | "planned" | "deprecated";
    notes?: string;
  }>;

  /** Payment rails accepted anywhere on this host. */
  payment_rails?: Array<{
    kind: string;                    // stripe | x402 | gratitude | …
    role?: string;                   // human-readable
    status?: "live" | "planned" | "deprecated";
  }>;

  /** Identity expectations. */
  identity?: {
    /** did:web | did:key | ua-string-only */
    preferred?: string;
    accepted?: string[];
    /** Header names agents SHOULD use when identifying. */
    headers?: {
      agent_did?: string;            // default: X-Agent-DID
      principal_did?: string;        // default: X-Principal-DID
      credential?: string;           // default: X-Agent-Credential
    };
    notes?: string;
  };

  /** What the site itself promises about its own behavior. */
  transparency?: {
    karma_ledger_public?: string;    // URL
    dharma_rules_public?: boolean;
    logs_retention_days?: number;
    pii_policy?: string;             // free-form statement
  };

  /** Related documents. */
  references?: Array<{
    rel: "agent-economy" | "sitemap" | "robots" | "tos" | string;
    href: string;
  }>;
}
```

## Matching semantics

1. Agents match the request path against each entry's `path` in
   declared order. First match wins.
2. `path` MAY end with `*` for prefix match; otherwise exact.
3. `allow` is an array of identifier globs matched against the
   agent's self-declared User-Agent or `X-Agent-DID`. `["*"]` means
   unrestricted.
4. If no entry matches, the default is **allow with best-effort
   rate limit** — this is a friendly spec, not a hostile one.

## Identity

Agents SHOULD identify themselves with at least one of:
- A descriptive `User-Agent` (e.g. `claude-agent/1.0 (did:web:example.com)`)
- A `did:web` or `did:key` in the `X-Agent-DID` header
- A principal DID in `X-Principal-DID` when acting on behalf of a
  human or org

Hosts MAY refuse service to unidentified agents at their discretion.
In v0.1, WhiteMagic's own implementation accepts unidentified
traffic everywhere except `/admin`.

## Rate limits

Hosts declare, not enforce. Agents SHOULD self-limit to the stated
rate. Hosts retain the right to block abusive callers at any layer.

`per: "ip"`, `per: "session"`, and `per: "did"` define the
quantization unit. Hosts MAY apply multiple unit caps
simultaneously (e.g. per-IP AND per-DID). In that case, the
stricter limit wins.

## Payment rails

`payment_rail` on a surface indicates the preferred rail **when that
surface becomes billable**. Free surfaces SHOULD omit the field.
When a rail is listed but `status: "planned"`, agents SHOULD treat
the surface as currently free and not attempt payment.

## Security considerations

- The document is unsigned in v0.1. Downstream callers MAY cache
  copies; hosts SHOULD serve fresh versions on material changes.
- Hosts MUST NOT rely on this document for access control. It is
  an advisory contract, not an enforcement mechanism.

## Privacy considerations

- The document MUST NOT contain PII or secrets.
- The `transparency` block is the host's self-disclosure, not an
  obligation on the caller.

## Relationship to `robots.txt`

- `robots.txt` continues to exist and remains authoritative for
  legacy crawlers.
- `ai-agent-policy` is **additive**. An agent that reads both
  SHOULD honor the *intersection* of the two.
- Future work: a cross-reference header in `robots.txt` pointing
  to the policy URL. Not required in v0.1.

## Open questions

- **Q1**: Should surfaces support structured conditions (time-of-
  day, geography, agent class)? Deferred to v0.2.
- **Q2**: Should the format define a way to advertise **cost per
  request**? Likely yes in v0.2 alongside x402 integration.
- **Q3**: Should hosts publish a cryptographic commitment to the
  policy (e.g. a signed manifest)? v0.2 candidate.
- **Q4**: Registration with IANA well-known? v1.0 action.

## Why publish this

- Other sites can copy the format immediately.
- Creates a shared vocabulary around agent-facing rate limits and
  identity.
- Positions us as the source for this particular primitive.
- Submittable as an RFC to OWASP (for the Agentic Top 10 guidance
  section on "server-side controls") and to the MCP working group
  (for the "how should MCP servers declare policy" question).
