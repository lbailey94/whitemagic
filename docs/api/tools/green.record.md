# green.record

**Category**: system | **Safety**: write
**Gana**: `gana_mound`

## Description

Record an inference operation for green score tracking.

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "locality": {
      "type": "string",
      "enum": [
        "edge",
        "local_llm",
        "local_net",
        "cloud"
      ],
      "description": "Where inference ran.",
      "default": "edge"
    },
    "tokens_used": {
      "type": "integer",
      "description": "Tokens consumed.",
      "default": 0
    },
    "tokens_saved": {
      "type": "integer",
      "description": "Tokens avoided via caching/compression.",
      "default": 0
    },
    "model": {
      "type": "string",
      "description": "Model name if applicable."
    },
    "tool": {
      "type": "string",
      "description": "Tool that triggered the inference."
    },
    "duration_ms": {
      "type": "number",
      "description": "Operation duration in ms.",
      "default": 0
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
    "green.record",
    {"locality": "Where inference ran.", "tokens_used": 0, "tokens_saved": 0, "model": "Model name if applicable.", "tool": "Tool that triggered the inference.", "duration_ms": 0, "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
