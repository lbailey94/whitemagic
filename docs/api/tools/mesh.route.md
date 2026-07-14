# mesh.route

**Category**: agent | **Safety**: read
**Gana**: `gana_chariot`

## Description

Route an inference request to the best available mesh node

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model": {
      "type": "string",
      "description": "Model name to route to"
    },
    "prompt": {
      "type": "string"
    },
    "max_tokens": {
      "type": "integer",
      "default": 128
    },
    "temperature": {
      "type": "number",
      "default": 0.7
    },
    "strategy": {
      "type": "string",
      "description": "fastest|round_robin|capacity|reputation|local_first"
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
    "model"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "mesh.route",
    {"model": "Model name to route to", "prompt": "example", "max_tokens": 128, "temperature": 0.7, "strategy": "fastest|round_robin|capacity|reputation|local_firs", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
