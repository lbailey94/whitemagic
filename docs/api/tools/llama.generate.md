# llama.generate

**Category**: inference | **Safety**: read
**Gana**: `gana_roof`

## Description

Generate text with a local llama.cpp model. Supports context injection from WhiteMagic memories and optional Memory-Augmented Generation (store output as a memory).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "model": {
      "type": "string",
      "description": "llama.cpp model name"
    },
    "prompt": {
      "type": "string",
      "description": "Prompt text"
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
    "system": {
      "type": "string",
      "description": "System prompt override"
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
    "prompt"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "llama.generate",
    {"model": "llama.cpp model name", "prompt": "Prompt text", "context": true, "store": false, "system": "System prompt override", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
