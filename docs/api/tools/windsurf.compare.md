# windsurf.compare

**Category**: archaeology | **Safety**: read
**Gana**: `gana_chariot`

## Description

Compare exports across dates to find new, changed, and missing sessions. Uses cascade ID, transcript length, step count, and content hash for comparison.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "new_dir": {
      "type": "string",
      "description": "New export directory to compare"
    },
    "old_dirs": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Old export directories to compare against"
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
    "new_dir"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "windsurf.compare",
    {"new_dir": "New export directory to compare", "old_dirs": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
