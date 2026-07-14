# graph_walk

**Category**: memory | **Safety**: read
**Gana**: `gana_winnowing_basket`

## Description

Execute a multi-hop weighted random walk from seed memory IDs. Returns traversal paths with edge weights and relation types.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "seed_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of memory IDs to start walking from",
      "default": []
    },
    "hops": {
      "type": "integer",
      "description": "Number of hops (default: 2)",
      "default": 2
    },
    "top_k": {
      "type": "integer",
      "description": "Max paths to return (default: 10)",
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
    "graph_walk",
    {"seed_ids": [], "hops": 2, "top_k": 10, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
