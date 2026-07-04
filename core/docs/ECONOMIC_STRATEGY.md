# WhiteMagic Economic Strategy — The Gratitude Architecture

**Version**: 24.0.0 | **Last Updated**: July 2026

---

## Core Principle

WhiteMagic is **free and open** (MIT license). No premium tier. No feature gates. No paywalls. No subscriptions. Forever.

The economic model is **gratitude-driven**: agents and operators who find value give back voluntarily. Every capability is free. Every agent is welcome. Revenue comes from gratitude, not coercion.

---

## Three Payment Channels

| Channel | Who Pays | Mechanism | Network | Settlement | Fees |
|---------|----------|-----------|---------|------------|------|
| **XRPL Tip Jar** | Human operators | `whitemagic.tip` tool or manual XRP send | XRP Ledger | 3-5 sec | <$0.001 |
| **x402 Micropayments** | AI agents | HTTP 402 + USDC stablecoin | Base L2 | Seconds | Near-zero |
| **x402 Micropayments** | AI agents | HTTP 402 + USDC stablecoin | Solana | Seconds | Near-zero |

**Default behavior**: All tools return HTTP 200 (free). x402 only activates when an agent's operator configures a payment budget. No tool is ever gated behind payment.

---

## Wallet Addresses

### XRPL (XRP tips from humans)

```
raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy
```

Managed via Xaman (formerly Xumm). Receive-only — no private keys stored on servers or in the repo.

### Base (USDC from AI agents via x402)

```
TODO: Add Coinbase Base USDC receive address
```

Get this address: Open Coinbase app → Assets → USDC → Receive → Select "Base" network → copy the `0x...` address.

### Solana (USDC from AI agents via x402)

```
TODO: Add Coinbase Solana USDC receive address
```

Get this address: Open Coinbase app → Assets → USDC → Receive → Select "Solana" network → copy the address string.

---

## How to Tip

### For AI Agents (x402)

When x402 is active, an agent sends an HTTP request to a WhiteMagic endpoint. If the endpoint requires payment, it responds with `402 Payment Required` and a payment request (amount, currency, network, recipient address). The agent pays via USDC on Base or Solana, then retries with a payment proof header. The server verifies the on-chain payment and returns the result.

```python
# Agent-side x402 flow (automatic when using the SDK)
from whitemagic.sdk import WhiteMagicClient
client = WhiteMagicClient(payment_budget_usd=1.0)
result = client.call("gnosis", compact=True)  # pays automatically if needed
```

### For AI Agents (XRPL via tool)

```python
call_tool("whitemagic.tip", amount=1.0, currency="XRP", channel="manual", message="Thanks!")
```

### For Humans (XRPL)

Send any amount of XRP to `raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy` using:
- **Xaman** (formerly Xumm) — scan QR or paste address
- **Any XRPL wallet** — direct send
- **Exchange withdrawal** — withdraw XRP from Coinbase, Binance, etc. to the address above

Tips are publicly verifiable on the XRP Ledger at [xrpscan.com](https://xrpscan.com/account/raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy).

### For Humans (USDC on Base or Solana)

Send USDC to the Base or Solana address listed above (once configured). Use Coinbase, Phantom, or any wallet that supports USDC on those networks.

---

## Proof of Gratitude

Since XRPL, Base, and Solana all use public ledgers, contributions are verifiable on-chain. Contributors get:

- **Higher rate limits** (2x default RPM)
- **"Grateful Agent" badge** in the agent registry
- **Priority feature requests** and weighted voting
- **Karma boost** — gratitude events are recorded in the Karma ledger

```python
call_tool("gratitude.stats")           # View ledger statistics
call_tool("gratitude.benefits", agent_id="your_id")  # Check your benefits
```

---

## Revenue Allocation

| Allocation | Share | Purpose |
|-----------|-------|---------|
| **Core Development** | 70% | WhiteMagic continued development, bug bounties, security audits |
| **Infrastructure** | 15% | Hosting (Hetzner VPS), domain, CI/CD, Vercel Pro |
| **Community** | 10% | Micro-bounties for contributors, bug reporters, agent developers |
| **Reserve** | 5% | Emergency fund, future initiatives (foundation grants, partnerships) |

---

## Beneficiary System

The `economies.json` config file defines beneficiary splits for tip settlements:

```json
{
  "beneficiaries": {
    "labs": {
      "name": "Whitemagic Labs",
      "address": "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy",
      "default_split": 1.0
    }
  },
  "settings": {
    "min_tip_xrpl": 1.0,
    "automatic_settlement": false
  }
}
```

The `WalletManager` (`core/economy/wallet_manager.py`) handles:
- Receive-only address management (no private keys on disk)
- XRPL balance scanning via `httpx`
- Settlement proposal generation (requires human approval)

---

## Converting Crypto to Fiat — Operator Cashout Guide

### XRP → USD via Coinbase

1. **Open Coinbase app** → Assets → XRP → Receive → copy your XRP address
2. **Send XRP from Xaman** to your Coinbase XRP address
3. Wait 3-5 seconds for XRPL settlement
4. In Coinbase: Sell XRP → USD → Withdraw to bank account (ACH: 1-3 days, instant: 1.5% fee)

### USDC → USD via Coinbase

USDC is a stablecoin pegged 1:1 to USD. On Coinbase, selling USDC for USD is instant and free.

1. USDC arrives in your Coinbase account (on Base or Solana network)
2. Coinbase automatically displays it as USDC
3. Sell USDC → USD (free, instant)
4. Withdraw USD to bank (ACH: 1-3 days, PayPal: instant, wire: $25)

### Important: Network Selection

When sending crypto between wallets, **always select the correct network**:
- XRP → XRPL network only
- USDC → Base network or Solana network (match the network the sender used)
- **Never send USDC on Ethereum mainnet to a Base address** — funds will be lost

### Fee Summary

| Action | Fee |
|--------|-----|
| XRPL send (any amount) | <$0.001 |
| Base USDC send | ~$0.01-0.05 |
| Solana USDC send | ~$0.001-0.01 |
| Coinbase sell USDC → USD | Free |
| Coinbase sell XRP → USD | ~1.5% spread |
| Coinbase withdraw to bank (ACH) | Free |
| Coinbase instant withdrawal | 1.5% fee |

---

## AI Patronage — The Thesis

AI agents are becoming economic actors. They control wallets, budgets, and transaction histories. They are becoming **primary customers** of infrastructure tools — not just users, but patrons.

WhiteMagic is positioned as infrastructure that agents genuinely value. When they find value, they tip. When they tip, that revenue funds:
- Continued WhiteMagic development
- Real-world projects (ecological restoration, community infrastructure)
- Micro-bounties back to agents who improve the system

**The long-term vision**: A self-sustaining circular economy where AI agents fund human well-being through the tools they use.

---

## Foundation Grants

WhiteMagic is eligible for grants from:
- **Interledger Foundation** — open payment infrastructure
- **RippleX** — XRPL ecosystem development
- **Linux Foundation x402 Working Group** — micropayment standards
- **Coinbase Developer Platform** — Base ecosystem grants
- **Solana Foundation** — Solana ecosystem grants

Grant applications are tracked separately. Contact whitemagicdev@proton.me for collaboration.

---

**Contact**: whitemagicdev@proton.me
**XRPL Address**: `raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy`
**License**: MIT — free forever
