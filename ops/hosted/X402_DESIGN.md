# x402 metered lane — phase 2 design (not yet code)

**Status:** spec. Implement after the free tier has real usage data.
**Standard:** x402 v2 (Linux Foundation / x402 Foundation), USDC on Base
(CAIP-2 `eip155:8453`). Re-verified 2026-09-14 against docs.x402.org and
Cloudflare's Agents SDK docs.

## Where it lives

The auth sidecar (`authd.py`) is the single enforcement point — x402 is a
branch inside `authorize()`, in this order:

1. **Identity first (401 before 402).** If a request carries
   `Authorization: Bearer <key>` → normal key path (free tier or invoiced).
   Anonymous request to a paid route falls through to the payment branch.
2. **Free discovery is never gated.** `initialize` and `tools/list` (and
   `/health`) stay free and unmetered — MCP directory probes (Glama, mcp.so,
   PulseMCP) must get a manifest, and agents must browse before they buy.
   Only `tools/call` on the metered route can return 402.
3. **Payment branch.** No key, no payment → respond **HTTP 402** with a
   `PAYMENT-REQUIRED` header (Base64 JSON: price, asset USDC, network,
   `payTo`, scheme). Client retries with `PAYMENT-SIGNATURE`; authd verifies
   via the facilitator and returns the result with a `PAYMENT-RESPONSE`
   receipt header.

Do **not** use the legacy `X-Payment` header (v1); the current spec is
`PAYMENT-REQUIRED` / `PAYMENT-SIGNATURE` / `PAYMENT-RESPONSE`.

Implementation options, in order of preference:

- **Python SDK** (`pip install "x402[fastapi]"` or `x402[flask]`): authd.py
  gains the middleware and a route config; least code, maintained spec parity.
- **Manual branch** in `authd.py`: only if the SDK cannot wrap the stdio/SSE
  relay shape; verify against `https://x402.org/facilitator` on testnet.
- **Edge offload (later):** Cloudflare Monetization Gateway (waitlist since
  2026-07-01) moves 402/x402 verification and settlement off the origin;
  adopted as the eventual front so the box never runs payment middleware.

## Schemes

- **`exact`** — launch scheme. Fixed $ per recall; simplest, all networks.
- **`upto`** — usage-based (authorize a max, settle actual; Permit2 on EVM).
  Use if a single recall call ever bills variable work (e.g. deep synthesis).
- **`batch-settlement`** — off-chain vouchers, on-chain batched settlement.
  Use when agent loops make one-tx-per-call wasteful.

## Facilitators

| Stage | Facilitator |
|---|---|
| Testnet (Base Sepolia `eip155:84532`) | `https://x402.org/facilitator` (free, testnet only) |
| Mainnet | Coinbase CDP `https://api.cdp.coinbase.com/platform/v2/x402` (default); PayAI `https://facilitator.payai.network` as alternate |
| Self-hosted (sovereignty option) | `x402-rs` facilitator binary + funded gas wallet |

Keep the facilitator URL a config value; never call the testnet facilitator
from mainnet routes.

## Pricing

- Launch at **$0.005/recall** — below the observed market median (reports run
  $0.01–$0.028/call across 2026); our marginal cost is fractions of a cent.
- Batch requests (multi-tool calls) price per tool call, not per HTTP round
  trip.
- Never price below settlement cost (Base gas < $0.001 — safe at any price we
  pick).
- Instrument from day one; raise the price only against measured demand.
- Tiered, not flat: free key cap → metered per recall → invoiced keys
  (enterprise flat). Keys are the reliable path; x402 is the long tail.

## Rules (from the economy plan, restated)

- x402 is an **optional lane**: invoiced keys remain the load-bearing path.
- Payments are irreversible (no dispute rail) — every settled call gets an
  audit line with the payment tx hash, mirrored into the Karma ledger story.
- **Idempotency:** fulfillment keyed on the payment credential, not the
  request — a retried payment serves the same result exactly once.
- **Verify server-side on every call** through the facilitator; no trusted
  bypass path.
- **Rate-limit paid callers too** — an agent loop must not run up a bill it
  will later contest.
- Wallet/key handling: the receiving wallet key lives only on the Hetzner box
  (`/var/lib/whitemagic-hosted/`, mode 600) — never in any repo, never on
  Vercel.

## Discovery

- Register the recall tool in the x402 **Bazaar** via the discovery extension
  (`declareDiscoveryExtension` / `createPaymentWrapper` for MCP) so buyers can
  find it without prior knowledge. Listing is free; cataloging only happens
  when a paying client echoes the extension in its payload — our first
  testnet paid call doubles as the listing trigger.
- Catalog behavior is facilitator-dependent (the spec guarantees nothing;
  third parties report inactive listings dropped around ~30 days). If the
  catalog drops us, add a small heartbeat (funded wallet, scheduled paid
  call) rather than assume permanence.
- Enable the **Signed Offers & Receipts** extension when it lands: signed
  offers on every 402, signed receipt on every 200 — portable,
  third-party-verifiable proof of service, which is exactly the Karma-ledger
  posture.

## Positioning (why this lane wins)

- **Receipts-first.** The Signed Offers & Receipts extension (signed offer on
  every 402, signed receipt on every 200) makes each paid call a portable,
  third-party-verifiable artifact — mapped into the Karma ledger story. The
  market sells raw calls; we sell auditable calls.
- **Two-sided.** Seller receipts + a governed buyer: port the Python-era
  Transaction Firewall (spend limits, recipient allowlist, Dharma sign-off)
  so `wm` agents can pay for x402 tools under policy. No competitor pairs
  agent payments with governed spend.
- **Tier map (one unit of value = recall):** free key cap → $0.005/recall
  metered → invoiced keys (enterprise flat). Tips stay a separate rail
  ($0.03 gate per PRICING_ETHICS).
- **Cost-base leverage:** a €5–11/mo lane means break-even is ~1–2k paid
  calls/month at $0.005 — the free tier can stay generous while trust
  (receipts, audit, SLA) becomes the eventual premium tier.
- **Rail neutrality:** CDP / PayAI / self-hosted facilitator, MPP (Stripe
  cards) later; invoiced keys remain load-bearing.

## What "shipping phase 2" means

- `authd.py`: 402 challenge generation, `PAYMENT-SIGNATURE` verification via
  facilitator, per-call pricing config, tx-hash audit lines, idempotency key.
- `server-card.json`: flip `x402.status` from "planned" to live.
- llms.txt / agent surfaces: document the metered endpoint so agents can
  self-serve (that's the whole point — no humans in the loop).
