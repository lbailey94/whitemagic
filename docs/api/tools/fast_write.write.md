# fast_write.write

**Category**: memory | **Safety**: write
**Gana**: `gana_ox`

## Description

Write content to a file atomically with syntax validation. Overwrites if file exists. 10-100x faster than edit tools for >10 line changes.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Target file path"
    },
    "content": {
      "type": "string",
      "description": "File content to write"
    },
    "validate": {
      "type": "boolean",
      "default": true,
      "description": "Validate Python syntax after write"
    },
    "backup": {
      "type": "boolean",
      "default": false,
      "description": "Backup existing file to .bak before write"
    },
    "dry_run": {
      "type": "boolean",
      "default": false,
      "description": "Show what would be written without writing"
    },
    "request_id": {
      "type": "string",
      "description": "Optional caller-provided request id for tracing. If omitted, a UUID is generated."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional idempotency key. For write tools, retries with the same key will replay prior results."
    },
    "now": {
      "type": "string",
      "description": "Optional ISO timestamp override for deterministic evaluation/replay (best-effort)."
    }
  },
  "required": [
    "path",
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "fast_write.write",
    {"path": "Target file path", "content": "File content to write", "validate": true, "backup": false, "dry_run": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
