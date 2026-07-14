# codebase.find

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Find files by extension, tag, or path pattern in the codex galaxy. Faster than grep for 'what files exist with extension X' queries. Searches memory metadata, not the filesystem.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "extension": {
      "type": "string",
      "description": "File extension to filter by (e.g. 'py', 'rs')."
    },
    "path_pattern": {
      "type": "string",
      "description": "Path pattern to filter by (e.g. 'core/whitemagic')."
    },
    "tag": {
      "type": "string",
      "description": "Specific tag to filter by."
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of results.",
      "default": 50
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
    "codebase.find",
    {"extension": "File extension to filter by (e.g. 'py', 'rs').", "path_pattern": "Path pattern to filter by (e.g. 'core/whitemagic')", "tag": "Specific tag to filter by.", "limit": 50, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
