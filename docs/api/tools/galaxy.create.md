# galaxy.create

**Category**: system | **Safety**: write
**Gana**: `gana_void`

## Description

Create a new galaxy (project-scoped memory database). Each galaxy gets its own SQLite database and holographic index for isolated memory storage.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Galaxy name (alphanumeric, hyphens, underscores)",
      "default": "main"
    },
    "path": {
      "type": "string",
      "description": "Optional project directory this galaxy is associated with"
    },
    "description": {
      "type": "string",
      "description": "Human-readable description"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Tags for categorization"
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
    "galaxy.create",
    {"name": "Galaxy name (alphanumeric, hyphens, underscores)", "path": "Optional project directory this galaxy is associat", "description": "Human-readable description", "tags": [], "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
