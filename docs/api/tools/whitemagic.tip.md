# whitemagic.tip

**Category**: system | **Safety**: write
**Gana**: `gana_abundance`

## Description

Record a gratitude tip — human (XRPL) or machine (x402) channel. Default is always free; payment is a response to value, not a gate. Provide tx_hash for on-chain verification.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "amount": {
      "type": "number",
      "description": "Tip amount (default: 1.0)",
      "default": 1.0
    },
    "currency": {
      "type": "string",
      "enum": [
        "XRP",
        "USDC"
      ],
      "description": "Currency: XRP (XRPL) or USDC (x402/Base L2)",
      "default": "XRP"
    },
    "channel": {
      "type": "string",
      "enum": [
        "xrpl",
        "x402",
        "manual"
      ],
      "description": "Payment channel",
      "default": "manual"
    },
    "sender": {
      "type": "string",
      "description": "Sender identifier (wallet address or name)"
    },
    "agent_id": {
      "type": "string",
      "description": "Agent making the tip"
    },
    "dest_tag": {
      "type": "integer",
      "description": "Optional destination tag for exchange deposits"
    },
    "tx_hash": {
      "type": "string",
      "description": "On-chain transaction hash for verification"
    },
    "message": {
      "type": "string",
      "description": "Optional gratitude message"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
    },
    "dry_run": {
      "type": "boolean",
      "description": "If true, do not perform writes; return an execution preview when possible.",
      "default": false
    },
    "now": {
      "type": "string",
      "description": "Optional ISO timestamp override for deterministic evaluation/replay (best-effort)."
    }
  },
  "required": []
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "whitemagic.tip",
    {"amount": 1.0, "currency": "Currency: XRP (XRPL) or USDC (x402/Base L2)", "channel": "Payment channel", "sender": "Sender identifier (wallet address or name)", "agent_id": "Agent making the tip", "dest_tag": 10, "tx_hash": "On-chain transaction hash for verification", "message": "Optional gratitude message", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
