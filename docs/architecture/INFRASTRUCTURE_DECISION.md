# Infrastructure Decision — Where to Host whitemagic.dev

**Created**: 2026-04-19 (late session)
**Decision owner**: Lucas
**Current status**: **Planning for Hetzner VPS**. Not yet committed; deploy doc written, awaiting execution.
**Revisit trigger**: Hetzner operational cost exceeds the narrative benefit, OR Vercel ships post-incident hardening that changes the calculus.

---

## Context

The original scoping (`@apps/SCOPING_BROWSER_FIRST_DECIDED.md`) assumed
Vercel as the host for `whitemagic.dev`. Vercel is the Next.js reference
deployment target and has the best DX.

On **April 19, 2026** — the same day this decision was made — Vercel
disclosed a security incident:

> "We've identified a security incident that involved unauthorized access
> to certain internal Vercel systems, impacting a limited subset of
> customers. ... We recommend that all of our customers follow best
> practices by reviewing environment variables and taking advantage of
> Vercel's sensitive environment variable feature."
> — Vercel security bulletin, April 19, 2026

The threat actor ShinyHunters (credible, with track record of real
breaches and partial exaggerations) claimed a $2M sale on BreachForums
including access keys, source code, NPM tokens, GitHub tokens, and
internal project-management data (Linear).

Vercel also had two high-severity CVEs earlier in 2026 (January's
SvelteKit cache deception, April 8's CVE-2026-23869 React Server
Components DoS) and handled the March axios supply-chain incident.
Pattern is: Vercel is a high-value target and remains one.

## Options evaluated

| Option | Ops cost | Narrative fit | Platform risk | Verdict |
|---|---|---|---|---|
| **Vercel as planned** | Low (setup done in minutes) | Weak — undermines "private AI, your infrastructure" pitch while the breach is in the news | Low for our specific env var inventory | Ship here only if time-to-launch is paramount |
| **Hetzner VPS** | Moderate — 3–4 hr initial setup, low ongoing | **Strong** — "I run my own infrastructure, like I advise you to" | Low (self-controlled stack) | **Chosen** |
| **Cloudflare Pages** | Low | Moderate — managed platform but no breach record | Low | Acceptable fallback if Hetzner proves too slow |
| **Hybrid: Hetzner + Upstash** | Moderate | Strong | Low | Practical — already what we're doing; Upstash is a KV provider, not a deploy target |

## Our specific blast radius on Vercel

For completeness — the technical risk of Vercel for *our* workload is
low. Environment variables we'd store:

| Secret | If leaked |
|---|---|
| `OPENROUTER_API_KEY` | Attacker drains monthly budget. $25/month hard cap limits loss. |
| `UPSTASH_REDIS_REST_TOKEN` | Attacker reads/writes KV: rate limits, karma ledger, budget counter. No user PII. |
| `NEXT_PUBLIC_STRIPE_*_URL` | Public by design (Stripe payment links are meant to be shareable). |
| `RESEND_API_KEY` (future) | Spam email "from Lucas" — reputational, not financial. |

Worst case: ~$25 loss + credential rotation. No customer PII, no
payment data, no proprietary code (OSS repo is public).

So the decision is **not** primarily driven by technical risk. It's
driven by narrative integrity.

## Decision

**Self-host on Hetzner VPS.** Reasons, ranked:

1. **Narrative integrity** (highest weight). The consultancy's pitch is
   that private AI deployment, local-first architecture, and not
   depending on third-party managed platforms produces better outcomes
   for regulated clients. Deploying the marketing site itself on a
   platform that just had its access keys auctioned would undermine
   every sales conversation for months. Clients notice.
2. **Data locality**. Hetzner (Germany) is inside the EU, which
   strengthens the EU AI Act positioning ("we practice what we preach
   about data sovereignty").
3. **Control**. Full stack visibility. Own logs. Own incident response.
   No vendor-timed disclosure windows.
4. **Cost**. €4–8/month for CX22-class VPS vs Vercel's pricing ramping
   up as traffic grows.
5. **The ops cost is bounded**. 3–4 hours initial setup; subsequent
   deploys are `git push` + GitHub Action. This is acceptable friction
   for a one-page marketing site.

## What we lose

- **Preview deployments per PR** — recoverable via branch-based GitHub
  Actions with staging subdomain (documented in
  `@docs/deploy/HETZNER_DEPLOY.md` as optional).
- **Image optimization at the edge** — replaceable with Cloudflare
  Images (free tier adequate) or pre-optimized assets at build time.
- **Zero-config ISR / Edge Middleware** — not used by this site; marketing
  pages are static; Librarian runs in Node at the origin.
- **Vercel analytics** — never wanted them anyway; plan is Plausible or
  self-hosted Umami.

## What we keep from Upstash

Upstash stays. It's a managed Redis provider, not a deploy platform, and
has had no comparable incidents. The KV layer (rate limits, karma
ledger, budget) working against Upstash from Hetzner is fine — one
outbound HTTPS call per request. If Upstash ever had an outage or
incident, our in-memory fallback class `InMemoryKV` in
`@apps/site/lib/librarian/rate-limit.ts` keeps the site functional
(with rate limits reset on restart — acceptable for an outage window).

## What we keep from Cloudflare

Cloudflare in front of the Hetzner VPS:

- DNS + DDoS protection (free tier)
- Global CDN for static assets
- WAF rules (free tier: basic; paid tier: full — not yet needed)
- TLS termination can happen at Cloudflare OR at Caddy on the VPS (we
  use Caddy for end-to-end TLS with origin certificates for defense in depth)

## Re-examination triggers

Revisit this decision if:

- Hetzner ships more than one security incident of comparable severity in a 12-month window.
- The Hetzner VPS setup consumes > 4 hours/month of ops time steady-state.
- A paying client specifically requests the site be on a non-German host.
- Vercel publishes a detailed post-mortem + hardening report that materially changes their security posture.

None of these are currently true.

## Related documents

- `@docs/deploy/HETZNER_DEPLOY.md` — step-by-step walkthrough.
- `@apps/SCOPING_BROWSER_FIRST_DECIDED.md` §5 — repo strategy (was written pre-Hetzner pivot; update §5 "three private repos" to reflect the deploy source repo is named `whitemagic-site-private` and gets Hetzner-deployed, not Vercel-deployed).
- `@docs/architecture/MONOREPO_VS_MULTIREPO.md` — why the site lives in a dedicated deploy repo (Vercel preference was a minor factor; Hetzner has the same preference — clean repo roots make deploys simpler).
