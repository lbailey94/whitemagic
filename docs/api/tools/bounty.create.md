# bounty.create

**Category**: system | **Safety**: write
**Gana**: `gana_abundance`

## Description

Create a new task bounty. Locked funds in XRPL Escrow ensure trustless payment upon completion.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "Detailed description of the task"
    },
    "amount": {
      "type": "number",
      "description": "Amount in XRP to lock in escrow"
    },
    "expires_in": {
      "type": "integer",
      "description": "Seconds until the bounty expires",
      "default": 86400
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
  "required": [
    "task",
    "amount"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "bounty.create",
    {"task": "Detailed description of the task", "amount": 1.0, "expires_in": 86400, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
