# polyglot.search

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Convenience tool: encode a query text and find its nearest neighbors among a pool of texts in a single call. Routes through polyglot backend.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Query text to encode"
    },
    "texts": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Pool of texts to search against"
    },
    "k": {
      "type": "integer",
      "default": 5,
      "description": "Number of results"
    },
    "backend": {
      "type": "string",
      "enum": [
        "auto",
        "julia",
        "elixir",
        "haskell",
        "rust",
        "koka"
      ],
      "default": "auto",
      "description": "Backend to use"
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
    "query",
    "texts"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "polyglot.search",
    {"query": "Query text to encode", "texts": [], "k": 5, "backend": "Backend to use", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
