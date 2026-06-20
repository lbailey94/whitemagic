# Site WIP Mode

**Version**: 1.0.0
**Date**: 2026-06-20
**Milestone**: v23.0.0-alpha.2-WIP

## What this is

A build-time flag that swaps public-facing marketing copy for an abstract,
invitational, lab-artifact voice. The technical surface (bridge catalog,
A2A Agent Card, librarian demo, research, library, governance, etc.) stays
fully visible. The marketing surface (services, pricing, fund, contact,
admin) collapses to a single WIP placeholder that says "This is being
rebuilt; the door is here, but the room is not yet open."

## Why

The site is hosted on Vercel Hobby, which forbids commercial activity. As
WhiteMagic pivots toward a local-first PWA / cognitive substrate product,
the marketing copy on the public site would otherwise leak premature
business claims ("we sell subscriptions", "we deploy private AI for
$10,000/month", "we accept consulting clients"). WIP mode replaces that
copy with a single principle: **A door is opening; you can see inside
through the catalog and the A2A Agent Card, but the room is not yet
open to walk into.**

WIP mode is a presentation layer, not a code freeze. The site, the
bridge, the librarian, the A2A surface, and the substrate all keep
shipping. Only the public-facing marketing claims change.

## How to toggle

```bash
# Enable WIP (default for v23.0.0-alpha.2)
# Add to Vercel Environment Variables:
NEXT_PUBLIC_WIP_MODE=1

# Disable WIP (default for v23.0.0+ final, when the marketing copy
# catches up to the product):
# Remove the env var or set to 0
NEXT_PUBLIC_WIP_MODE=0
```

The flag is checked at module-load time. No code change required to
toggle. The build artifact is identical; only the rendered output
differs.

## What's hidden in WIP

| Route | Non-WIP | WIP |
|---|---|---|
| `/services` | Three consulting tracks with engagement types | WIP placeholder |
| `/services/private-ai-deployment` | Service page | WIP placeholder |
| `/services/agent-governance` | Service page | WIP placeholder |
| `/services/mcp-engineering` | Service page | WIP placeholder |
| `/pricing` (if added) | Pricing tiers (research collaboration framing) | WIP placeholder |
| `/fund` | Grants + fund programs | WIP placeholder |
| `/contact` | Contact form / mailto | WIP placeholder (link to `/subscribe`) |
| `/admin` | Admin login | WIP placeholder |

All of these are wrapped in `<WipGuard>` (see `components/WipGuard.tsx`),
which renders a single, consistent WIP message in WIP mode and the
real page in non-WIP mode.

## What's kept in WIP

| Route | Why kept |
|---|---|
| `/` (home) | Hero rewrite lives in WIP; principle + door metaphor only |
| `/mcp-bridge` | Bridge catalog is the technical surface A2A peers query |
| `/.well-known/*` | A2A Agent Card, agents.json, agent-skills.json, agent-economy.json — A2A peers need this |
| `/chat` | Librarian demo is technical surface |
| `/llms.txt`, `/llms-full.txt` | LLM-readable discovery |
| `/research` | Research is the lab's stated mission |
| `/library` | Library is the open-source / research artifact catalog |
| `/timeline` | Chronology of the project's evolution |
| `/governance` | Dharma governance, karma ledger, ethics — this *is* the substrate |
| `/open-source` | The MIT-licensed substrate is what the PWA runs on |
| `/subscribe` (new) | Mailto form to express interest; no Stripe, no payment |
| `/sitemap.xml`, `/robots.txt` | Required for crawler discovery |

## What's added in WIP

- **Site-wide WIP banner** (`<WipBanner />` in `app/layout.tsx`): a
  thin strip at the top of every page that says "A door is opening.
  The technical surface is live; the marketing room is being rebuilt."
  Renders nothing when WIP_MODE is off.
- **Hero rewrite** (`app/page.tsx`): the home page hero is replaced
  with the "A door is opening" copy + 3-ways-in panel (Talk to Aria /
  Read the catalog / A2A Agent Card) + 4 substrate capabilities
  (Remembers, Reasons, Listens, Grows).
- **Footer rewrite** (`components/Footer.tsx`): the Contact link
  becomes Subscribe; the email is hidden; the prescience block is
  dropped; the "AI prescience, 21-for-21 verified" claim is gone
  (that claim lives in `/prescience` now, not in the marketing copy).
- **Subscribe page** (`app/subscribe/page.tsx`): a mailto form, not a
  payment form. The CTA says "Send a message" not "Pay now". This is
  the only way to express interest in v23-era work.

## The principle

WhiteMagic is a research lab / portfolio artifact, not a SaaS. WIP mode
is the public-facing expression of that principle. The substrate is
real, the catalog is real, the A2A surface is real. The business model
is not yet defined; pretending it is would be dishonest. WIP mode
honors that.

When v23.0.0 ships (no longer WIP), the marketing copy will be rewritten
to accurately describe what the project *is* at that point — a local-
first PWA / cognitive substrate you can install on your own device, with
a public bridge catalog, an A2A Agent Card, and an opt-in mesh. The
marketing will be honest about the substrate's maturity, the licensing,
the data sovereignty principle, and the absence of cloud sync.

## Files

- `lib/wip.ts` — the flag + all WIP content overrides
- `components/WipBanner.tsx` — the site-wide banner
- `components/WipGuard.tsx` — the per-page gate
- `app/layout.tsx` — `<WipBanner />` wired in
- `app/page.tsx` — WIP hero
- `components/Footer.tsx` — WIP footer
- `app/subscribe/page.tsx` — mailto form
- `app/services/page.tsx` and `app/services/*/page.tsx` — wrapped
- `app/fund/page.tsx` — wrapped
- `app/contact/page.tsx` — wrapped
- `public/llms-full.txt` — Data Sovereignty section added
- `app/api/well-known/agent/route.ts` — posture updated to declare
  `data_residency: "local-first"`, `pwa_installable: true`,
  `cloud_storage: false`, `sync_model: "opt-in-p2p"`
