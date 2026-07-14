# model.verify

**Category**: security | **Safety**: read
**Gana**: `gana_roof`

## Description

Verify a model against its registered manifest

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model_name": {
      "type": "string",
      "description": "Name of the model to verify"
    },
    "current_sha256": {
      "type": "string",
      "description": "Current SHA-256 hash to verify against manifest",
      "default": ""
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
    "model_name"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "model.verify",
    {"model_name": "Name of the model to verify", "current_sha256": "Current SHA-256 hash to verify against manifest", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
