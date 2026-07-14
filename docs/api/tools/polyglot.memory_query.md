# polyglot.memory_query

**Category**: memory | **Safety**: read
**Gana**: `gana_tail`

## Description

Execute a holographic memory query through an available polyglot backend (Julia, Elixir, Haskell, or Rust). Supports encode, nearest_neighbors, constellation_detect, and coherence_score. Falls back through backends automatically if one is unavailable.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": [
        "encode",
        "nearest_neighbors",
        "constellation_detect",
        "coherence_score"
      ],
      "description": "Holographic memory operation to execute"
    },
    "text": {
      "type": "string",
      "description": "Text to encode (for encode operation)"
    },
    "query": {
      "type": "string",
      "description": "Query text (for nearest_neighbors)"
    },
    "texts": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of texts to search against (for nearest_neighbors)"
    },
    "coords": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number"
        }
      },
      "description": "List of 5D coordinates (for constellation_detect, coherence_score)"
    },
    "k": {
      "type": "integer",
      "default": 5,
      "description": "Number of nearest neighbors to return"
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
      "description": "Backend to use (auto = first available)"
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
    "operation"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "polyglot.memory_query",
    {"operation": "Holographic memory operation to execute", "text": "Text to encode (for encode operation)", "query": "Query text (for nearest_neighbors)", "texts": [], "coords": [], "k": 5, "backend": "Backend to use (auto = first available)", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
