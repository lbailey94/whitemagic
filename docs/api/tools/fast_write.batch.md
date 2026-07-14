# fast_write.batch

**Category**: memory | **Safety**: write
**Gana**: `gana_ox`

## Description

Write multiple files in one operation with syntax validation.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "files": {
      "type": "object",
      "description": "Dict of {path: content} pairs"
    },
    "validate": {
      "type": "boolean",
      "default": true
    },
    "backup": {
      "type": "boolean",
      "default": false
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
    "files"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "fast_write.batch",
    {"validate": true, "backup": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
