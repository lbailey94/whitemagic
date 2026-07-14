# gating.set_context

**Category**: memory | **Safety**: read
**Gana**: `gana_dipper`

## Description

Set the current cognitive context for galaxy gating (introspection, coding, research, creative, session, default).

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "context": {
      "type": "string",
      "enum": [
        "introspection",
        "coding",
        "research",
        "creative",
        "session",
        "default"
      ],
      "description": "Cognitive context name"
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
    "context"
  ]
}
```

## Example Invocation

```python
from whitemagic.tools.unified_api import call_tool

result = call_tool(
    "gating.set_context",
    {"context": "Cognitive context name", "request_id": "Optional caller-provided request id for tracing. I", "idempotency_key": "Optional idempotency key. For write tools, retries", "dry_run": false, "now": "Optional ISO timestamp override for deterministic "}
)
```

## Example Output

```json
{
  "status": "success",
  "data": "..."
}
```
