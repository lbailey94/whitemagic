# learning.suggest

**Category**: introspection | **Safety**: read
**Gana**: `gana_extended_net`

## Description

Suggest next tools based on learned cross-session sequences

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "current_tool": {
      "type": "string",
      "description": "Tool you just used \u2014 suggestions based on what typically follows"
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
    "current_tool"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "learning.suggest",
    {"current_tool": "Tool you just used \u2014 suggestions based on what typ", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
