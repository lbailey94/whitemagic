# code.path

**Category**: system | **Safety**: read
**Gana**: `gana_chariot`

## Description

Trace the call path between two symbols (A → B) in the code graph. Uses BFS on the edge graph. Returns the path, hop count, and node names.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "symbol_a": {
      "type": "string",
      "description": "Starting symbol name."
    },
    "symbol_b": {
      "type": "string",
      "description": "Target symbol name."
    },
    "max_hops": {
      "type": "integer",
      "description": "Maximum search depth.",
      "default": 5
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
    "symbol_a",
    "symbol_b"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "code.path",
    {"symbol_a": "Starting symbol name.", "symbol_b": "Target symbol name.", "max_hops": 5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
