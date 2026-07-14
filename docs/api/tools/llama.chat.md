# llama.chat

**Category**: inference | **Safety**: read
**Gana**: `gana_roof`

## Description

Chat with a local llama.cpp model using message history. Supports context injection and optional memory storage.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model": {
      "type": "string",
      "description": "llama.cpp model name"
    },
    "messages": {
      "type": "array",
      "description": "List of {role, content} messages"
    },
    "context": {
      "type": "boolean",
      "default": true,
      "description": "Inject relevant memories"
    },
    "store": {
      "type": "boolean",
      "default": false,
      "description": "Store output as memory"
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
    "model",
    "messages"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "llama.chat",
    {"model": "llama.cpp model name", "messages": [], "context": true, "store": false, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
