# fragment.index

**Category**: memory | **Safety**: write
**Gana**: `gana_winnowing_basket`

## Description

Build or update a Fragment index for a codebase. Supports quick (BM25 only) and deep (hybrid+semantic) modes.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to the codebase to index"
    },
    "mode": {
      "type": "string",
      "enum": [
        "quick",
        "deep"
      ],
      "default": "quick"
    },
    "force": {
      "type": "boolean",
      "default": false,
      "description": "Force rebuild from scratch"
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
    "path"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "fragment.index",
    {"path": "Path to the codebase to index", "mode": "example", "force": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
