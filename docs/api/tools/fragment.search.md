# fragment.search

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Search a codebase index for relevant code chunks using Fragment (Rust). 100x faster than Python vector search with BM25+semantic scoring.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query text"
    },
    "path": {
      "type": "string",
      "description": "Path to the codebase root directory"
    },
    "top": {
      "type": "integer",
      "description": "Number of results to return",
      "default": 10
    },
    "index_dir": {
      "type": "string",
      "description": "Custom index directory path (default: <path>/.fragment)"
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
    "fragment.search",
    {"query": "Search query text", "path": "Path to the codebase root directory", "top": 10, "index_dir": "Custom index directory path (default: <path>/.frag", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
