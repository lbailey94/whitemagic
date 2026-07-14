# codebase.recall

**Category**: memory | **Safety**: read
**Gana**: `gana_chariot`

## Description

Semantic recall from the codex galaxy. Searches file and chunk content memories using semantic embedding search, Rust BM25, or FTS5 fallback. Returns matching files with path, content preview, and recall type. This replaces grep for conceptual queries like 'where do we handle auth failures'.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query \u2014 natural language or keywords."
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of results.",
      "default": 20
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Additional tags to filter by."
    },
    "min_importance": {
      "type": "number",
      "description": "Minimum importance score (0.0-1.0).",
      "default": 0.0
    },
    "semantic": {
      "type": "boolean",
      "description": "If true, use semantic embedding search when available.",
      "default": true
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
    "query"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "codebase.recall",
    {"query": "Search query \u2014 natural language or keywords.", "limit": 20, "tags": [], "min_importance": 0.0, "semantic": true, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
