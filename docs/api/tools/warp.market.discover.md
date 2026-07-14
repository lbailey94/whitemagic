# warp.market.discover

**Category**: agent | **Safety**: read
**Gana**: `gana_wall`

## Description

Discover warp presets on the marketplace

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string"
    },
    "capability": {
      "type": "string"
    },
    "domain": {
      "type": "string"
    },
    "inference_tier": {
      "type": "string"
    },
    "max_price": {
      "type": "number",
      "default": 0.0
    },
    "limit": {
      "type": "integer",
      "default": 20
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
  }
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "warp.market.discover",
    {"query": "example", "capability": "example", "domain": "example", "inference_tier": "example", "max_price": 0.0, "limit": 20, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
