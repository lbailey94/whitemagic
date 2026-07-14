# galaxy.search_multi

**Category**: memory | **Safety**: read
**Gana**: `gana_void`

## Description

Search across multiple galaxies in parallel. Executes FTS5 queries against each specified galaxy (or all galaxies if none specified) and merges results by importance. Enables cross-galaxy recall without switching the active galaxy.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "FTS5 search query (optional, browses all if omitted)"
    },
    "galaxies": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Galaxy names to search. If omitted, searches all galaxies."
    },
    "galaxy": {
      "type": "string",
      "description": "Single galaxy name to search (shorthand for galaxies=[name])."
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Optional tag filter (memories must have ALL listed tags)"
    },
    "min_importance": {
      "type": "number",
      "description": "Minimum importance threshold (0.0-1.0)",
      "default": 0.0
    },
    "limit": {
      "type": "integer",
      "description": "Maximum results per galaxy",
      "default": 20
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
    "galaxy.search_multi",
    {"query": "FTS5 search query (optional, browses all if omitte", "galaxies": [], "galaxy": "Single galaxy name to search (shorthand for galaxi", "tags": [], "min_importance": 0.0, "limit": 20, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
