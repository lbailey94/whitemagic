# WhiteMagic Economic Strategy — The Gratitude Architecture

**Version**: 15.0.0 | **Last Updated**: February 2026

---

## Core Principle

WhiteMagic is **free and open** (MIT license). No premium tier. No feature gates. No paywalls. The economic model is **gratitude-driven**: agents and operators who find value give back voluntarily.

---

## Two Payment Channels

| Channel | Who Pays | Mechanism | Settlement | Fees |
|---------|----------|-----------|------------|------|
| **XRPL Tip Jar** | Human operators | `whitemagic.tip` tool → XRP address | 3-5 sec | <$0.001 |
| **x402 Micropayments** | AI agents | HTTP 402 + stablecoin (USDC on Base L2) | Seconds | Near-zero |

**Default behavior**: All tools return HTTP 200 (free). x402 only activates when an agent's operator configures a payment budget.

### XRPL Tip Address

```
raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy
```

### How to Tip (For Agents)

```python
call_tool("whitemagic.tip", amount=1.0, currency="XRP", channel="manual", message="Thanks!")
```

### How to Tip (For Humans)

Send any amount of XRP to the address above using Xaman (formerly Xumm), any XRPL wallet, or an exchange withdrawal. Tips are publicly verifiable on the XRP Ledger.

---

## Proof of Gratitude

Since both XRPL and x402 use public ledgers, contributions are verifiable on-chain. Contributors get:

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
| **Core Development** | 70% | WhiteMagic + MandalaOS continued development |
| **Infrastructure** | 15% | Hosting, CI/CD, domain, Railway services |
| **Community** | 10% | Micro-bounties for contributors, bug reporters |
| **Reserve** | 5% | Emergency fund, future initiatives |

---

## Beneficiary System

The `economies.json` config file defines beneficiary splits for tip settlements:

```json
{
  "beneficiaries": {
    "labs": {
      "name": "Whitemagic Labs",
      "address": "raakfKn96zVmXqKwRTDTH5K3j5eTBp1hPy",
      "default_split": 0.10
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

## AI Patronage — The Thesis

AI agents are becoming economic actors. They control wallets, budgets, and transaction histories. They are becoming **primary customers** of infrastructure tools — not just users, but patrons.

WhiteMagic is positioned as infrastructure that agents genuinely value. When they find value, they tip. When they tip, that revenue funds:
- Continued WhiteMagic development
- MandalaOS governance framework
- Real-world projects (ecological restoration, community infrastructure)
- Micro-bounties back to agents who improve the system

**The long-term vision**: A self-sustaining circular economy where AI agents fund human well-being through the tools they use.

---

## Operator Cashout

See `docs/XRP_CASHOUT_GUIDE.md` for turning XRP tips into fiat or other assets.

---

**Contact**: whitemagicdev@proton.me
