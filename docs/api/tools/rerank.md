# rerank

**Category**: synthesis | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Rerank search results using cross-encoder model or BM25 lexical fallback for higher precision.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The search query"
    },
    "results": {
      "type": "array",
      "description": "List of result dicts with id, title, content, score"
    },
    "top_k": {
      "type": "integer",
      "description": "Number of results to return",
      "default": 10
    },
    "strategy": {
      "type": "string",
      "enum": [
        "auto",
        "cross_encoder",
        "lexical"
      ],
      "default": "auto"
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
    "results"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "rerank",
    {"query": "The search query", "results": [], "top_k": 10, "strategy": "example", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
