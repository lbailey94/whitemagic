# context.pack

**Category**: system | **Safety**: read
**Gana**: `gana_heart`

## Description

Pack memories into an optimized context window for LLM calls — salience scoring + primacy/recency reorder

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query to find and score relevant memories",
      "default": "*"
    },
    "token_budget": {
      "type": "integer",
      "default": 8000,
      "description": "Maximum tokens for the context window"
    },
    "limit": {
      "type": "integer",
      "default": 50,
      "description": "Max memories to consider"
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
    "context.pack",
    {"query": "Search query to find and score relevant memories", "token_budget": 8000, "limit": 50, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
