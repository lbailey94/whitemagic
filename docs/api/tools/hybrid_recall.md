# hybrid_recall

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Multi-hop graph-aware memory recall. Combines BM25 + embedding anchor search with graph walk expansion to discover memories connected via the association graph.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query for anchor memories",
      "default": "*"
    },
    "hops": {
      "type": "integer",
      "description": "Number of graph hops (default: 2)",
      "default": 2
    },
    "anchor_limit": {
      "type": "integer",
      "description": "Max anchor memories from initial search (default: 5)",
      "default": 5
    },
    "final_limit": {
      "type": "integer",
      "description": "Max total results to return (default: 10)",
      "default": 10
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
    "hybrid_recall",
    {"query": "Search query for anchor memories", "hops": 2, "anchor_limit": 5, "final_limit": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
