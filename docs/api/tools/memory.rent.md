# memory.rent

**Category**: system | **Safety**: write
**Gana**: `gana_abundance`

## Description

Pay for temporary access to a specialized knowledge galaxy.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "galaxy_name": {
      "type": "string",
      "description": "Name of the galaxy to rent"
    },
    "agent_id": {
      "type": "string",
      "description": "ID of the agent requesting access"
    },
    "tx_hash": {
      "type": "string",
      "description": "XRPL transaction hash of the rental payment"
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
    "galaxy_name",
    "tx_hash"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "memory.rent",
    {"galaxy_name": "Name of the galaxy to rent", "agent_id": "ID of the agent requesting access", "tx_hash": "XRPL transaction hash of the rental payment", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
