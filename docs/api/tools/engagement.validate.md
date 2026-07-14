# engagement.validate

**Category**: security | **Safety**: read
**Gana**: `gana_wall`

## Description

Validate an engagement token for a tool/target combination

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "token_id": {
      "type": "string",
      "description": "Token ID to validate"
    },
    "tool": {
      "type": "string",
      "description": "Tool name to check authorization for",
      "default": ""
    },
    "target": {
      "type": "string",
      "description": "Target to check scope against",
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
    "token_id"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "engagement.validate",
    {"token_id": "Token ID to validate", "tool": "Tool name to check authorization for", "target": "Target to check scope against", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
