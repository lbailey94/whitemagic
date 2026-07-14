# mesh.route.register

**Category**: agent | **Safety**: write
**Gana**: `gana_chariot`

## Description

Register a mesh inference node

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "node_id": {
      "type": "string"
    },
    "address": {
      "type": "string"
    },
    "models": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "reputation": {
      "type": "number",
      "default": 0.5
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
    "node_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "mesh.route.register",
    {"node_id": "example", "address": "example", "models": [], "reputation": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
