# x402 metered lane — phase 2 design (not yet code)

**Status:** spec. Implement after the free tier has real usage data.
**Standard:** x402 (Linux Foundation / x402 Foundation), USDC on Base
(chain 8453). Verified live Sep 9 2026: ~4,800 mainnet endpoints, market
median price $0.01/call, facilitator-verified settlement (no chain node
needed on our side).

## Where it lives

The auth sidecar (`authd.py`) is the single enforcement point — x402 is a
new branch in `authorize()`:

1. Request arrives with `Authorization: Bearer <key>` → normal path.
2. Request arrives **without** a key but **with** `X-Payment` → verify
   the payment proof against the facilitator, then relay (metered path).
3. Request arrives with neither → respond **HTTP 402** with the payment
   requirements JSON: price per recall, USDC, our Base address, scheme
   `exact`, network chain id. No session, no signup — "money without humans."

## Pricing

- Start at **$0.005/recall** (half the market median — structurally
  sustainable: our marginal cost is fractions of a cent).
- Batch requests (multi-tool calls) price per tool call, not per HTTP round trip.
- Never price below settlement cost (Base gas <$0.001 — safe at any price we pick).

## Rules (from the economy plan, restated)

- x402 is an **optional lane**: invoiced keys remain the reliable path.
- Payments are irreversible (no dispute rail) — accounting must be honest
  and visible: every settled call gets an audit line with the payment tx hash.
- Wallet/key handling: the receiving wallet key lives only on the Hetzner
  box (`/var/lib/whitemagic-hosted/`, mode 600) — never in any repo, never
  on Vercel.
- Facilitator choice: start with Coinbase CDP facilitator (institutional
  credibility); the design keeps facilitator swappable.

## What "shipping phase 2" means

- `authd.py` gains: 402 challenge generation, X-Payment verification call
  to the facilitator, per-call pricing config, tx-hash audit lines.
- `server-card.json`: flip `x402.status` from "planned" to live.
- llms.txt / agent surfaces: document the metered endpoint so agents can
  self-serve (that's the whole point — no humans in the loop).
