# warp.market.download

**Category**: agent | **Safety**: write
**Gana**: `gana_wall`

## Description

Download and import a warp from the marketplace

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "listing_id": {
      "type": "string"
    },
    "target_warp_name": {
      "type": "string",
      "description": "Override name for imported warp"
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
    "listing_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "warp.market.download",
    {"listing_id": "example", "target_warp_name": "Override name for imported warp", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
