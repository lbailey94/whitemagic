# working_memory.attend

**Category**: memory | **Safety**: write
**Gana**: `gana_heart`

## Description

Bring a memory into working memory focus. LRU eviction when at capacity (7±2 chunks).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "memory_id": {
      "type": "string",
      "description": "Memory ID to attend to"
    },
    "content": {
      "type": "string",
      "description": "Memory content"
    },
    "title": {
      "type": "string",
      "description": "Optional title"
    },
    "importance": {
      "type": "number",
      "description": "0.0-1.0 importance weight",
      "default": 0.5
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
    "memory_id",
    "content"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "working_memory.attend",
    {"memory_id": "Memory ID to attend to", "content": "Memory content", "title": "Optional title", "importance": 0.5, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
