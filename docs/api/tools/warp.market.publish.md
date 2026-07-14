# warp.market.publish

**Category**: agent | **Safety**: write
**Gana**: `gana_wall`

## Description

Publish a warp preset to the P2P marketplace

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "warp_name": {
      "type": "string"
    },
    "warp_data": {
      "type": "object",
      "description": "Serialized Warp.to_dict()"
    },
    "author_id": {
      "type": "string"
    },
    "author_name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "price_xrp": {
      "type": "number",
      "default": 0.0
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
    "warp_name",
    "warp_data"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "warp.market.publish",
    {"warp_name": "example", "author_id": "example", "author_name": "example", "description": "example", "price_xrp": 0.0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
